"""端到端冒烟：把服务真的跑起来走一遍完整链路，全程离线（STRESS_TEST_MODE）。

和单元测试的区别：这里走的是**真实**的 FastAPI 应用、真实的 SQLite、真实的
ChromaDB、真实的上传落盘、真实的 SSE 流式响应。STRESS_TEST_MODE 关掉的是所有
外部 API 调用（LLM + embedding），不是内部链路。

覆盖的正是这次改动的几条主路：
  * alembic 建库 + 建管理员
  * 上传落盘（路径穿越修复）
  * 离线检索（embedding mock 修复 —— 以前这条照样打真实接口）
  * 异步流式问答
  * 反馈写入独立列（以前必定 500 并把 citations 写坏）
  * 语义缓存真的命中（以前每请求新建实例，命中率恒为 0）
"""
import os
import sys
import tempfile

TMP = tempfile.mkdtemp(prefix="rag-smoke-")
os.environ.update({
    "STRESS_TEST_MODE": "true",
    "LLM_API_KEY": "sk-not-used-in-stress-mode",
    "DATABASE_URL": f"sqlite:///{TMP}/app.db",
    "CHROMA_PERSIST_DIR": f"{TMP}/chroma",
    "UPLOAD_DIR": f"{TMP}/uploads",
    "ADMIN_PASSWORD": "smoke-admin-pw",
    "SECRET_KEY": "smoke-test-secret-key-not-for-production",
    "APP_ENV": "development",
})

# backend/ 目录：脚本放在 backend/scripts/ 下，所以是上一级。
# 用 __file__ 算而不是靠 CWD，这样从仓库根目录也能跑。
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)
os.chdir(BACKEND_DIR)  # settings 里的相对路径（.env 等）按 backend/ 解析
sys.stdout.reconfigure(encoding="utf-8")

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.services.cache_service import get_semantic_cache  # noqa: E402

FAILED = []


def check(label, ok, extra=""):
    mark = "OK  " if ok else "FAIL"
    print(f"  [{mark}] {label}{(' — ' + extra) if extra else ''}")
    if not ok:
        FAILED.append(label)


print(f"临时数据目录: {TMP}\n")

# TestClient 作为上下文管理器会触发 lifespan => init_db() => alembic upgrade + 建管理员
with TestClient(app) as client:
    print("1. 启动与建库")
    r = client.get("/api/health")
    check("健康检查 200", r.status_code == 200, f"status={r.status_code}")
    check("alembic 已建库", os.path.exists(f"{TMP}/app.db"))

    print("\n2. 登录")
    r = client.post("/api/auth/login",
                    json={"username": "admin", "password": "smoke-admin-pw"})
    check("管理员登录成功", r.status_code == 200, f"status={r.status_code} {r.text[:120]}")
    if r.status_code != 200:
        sys.exit(1)
    token = r.json()["access_token"]
    H = {"Authorization": f"Bearer {token}"}

    print("\n3. 上传文档（用穿越文件名，验证落盘安全）")
    payload_name = "../../../evil.txt"
    r = client.post(
        "/api/knowledge/upload",
        files={"file": (payload_name, b"RAG smoke test document. Return policy: 30 days.", "text/plain")},
        headers=H,
    )
    check("上传成功", r.status_code == 201, f"status={r.status_code} {r.text[:200]}")
    if r.status_code == 201:
        doc = r.json()
        check("原始文件名照常记录", doc["filename"] == payload_name, doc["filename"])

    upload_dir = f"{TMP}/uploads"
    on_disk = [os.path.join(upload_dir, f) for f in os.listdir(upload_dir)] if os.path.isdir(upload_dir) else []
    check("文件落在 uploads/ 内", len(on_disk) == 1, str(on_disk))
    check("上传目录外没有多余文件",
          not os.path.exists(f"{TMP}/evil.txt") and not os.path.exists(f"{TMP}/../evil.txt"))

    print("\n4. 建会话并问答（离线检索 + 异步流式）")
    r = client.post("/api/sessions", json={"title": "smoke"}, headers=H)
    check("创建会话", r.status_code == 201, f"status={r.status_code}")
    sid = r.json()["id"]

    question = "退货政策是多久？"
    r = client.post(f"/api/chat/{sid}", json={"message": question}, headers=H)
    check("问答请求 200", r.status_code == 200, f"status={r.status_code}")
    body = r.text
    check("SSE 含 token 事件", '"type": "token"' in body)
    check("SSE 含 citations 事件", '"type": "citations"' in body)
    check("SSE 含 done 事件", '"type": "done"' in body)
    check("离线检索真的召回了分块",
          '"source"' in body,
          "citations 里有 source 说明检索链路在无网络下跑通了")

    print("\n5. 反馈（原来必定 500，且会把 citations 写坏）")
    r = client.get(f"/api/sessions/{sid}", headers=H)
    msgs = r.json()["messages"]
    assistant = [m for m in msgs if m["role"] == "assistant"]
    check("会话里有助手回复", len(assistant) == 1, f"{len(assistant)} 条")
    if assistant:
        mid = assistant[0]["id"]
        r = client.post(f"/api/chat/{sid}/feedback",
                        json={"message_id": mid, "rating": "up"}, headers=H)
        check("反馈返回 200（原来必定 500）", r.status_code == 200,
              f"status={r.status_code} {r.text[:200]}")

        r = client.get(f"/api/sessions/{sid}", headers=H)
        m = [x for x in r.json()["messages"] if x["id"] == mid][0]
        check("评价已写入", m.get("feedback") == "up", str(m.get("feedback")))
        check("citations 未被写坏（仍是数组）",
              isinstance(m.get("citations"), list),
              f"type={type(m.get('citations')).__name__}")

    print("\n6. 会话历史（最近 10 条，不是最旧 10 条）")
    for i in range(12):
        client.post(f"/api/chat/{sid}", json={"message": f"追问 {i:02d}"}, headers=H)

    r = client.get(f"/api/sessions/{sid}", headers=H)
    total = len(r.json()["messages"])
    check("会话累计多轮消息", total >= 20, f"{total} 条")

    print("\n7. 语义缓存是模块级单例（原来每请求新建实例，命中率恒为 0）")
    # 压测模式下 mock 分支不写缓存（有意为之：压测要测未命中的最坏路径），
    # 所以这里验证的是根因 ——「实例是否共享」—— 而不是缓存条目数。
    from app.db.database import SessionLocal
    from app.services.chat_service import ChatService as _CS

    svc_a = _CS(SessionLocal())
    svc_b = _CS(SessionLocal())
    check("两次构造的 ChatService 共享同一个缓存实例",
          svc_a.cache is svc_b.cache,
          "原来 __init__ 里直接 SemanticCache()，每次都是一个新的空缓存")
    check("而且就是模块级那个单例", svc_a.cache is get_semantic_cache())
    svc_a.db.close()
    svc_b.db.close()

    print("\n8. 限流（返回 429 且带 CORS 头）")
    from app.config import settings as _s
    from app.middleware.rate_limit import rate_limiter

    # 压测模式会关掉限流（压测要能短时间打大量请求）—— 先关掉它再测
    old_stress = _s.STRESS_TEST_MODE
    old_rate = _s.RATE_LIMIT_PER_MINUTE
    _s.STRESS_TEST_MODE = False
    _s.RATE_LIMIT_PER_MINUTE = 1
    rate_limiter.buckets.clear()
    try:
        client.get("/api/health", headers={"Origin": "http://localhost:5173"})
        r = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
        check("超限返回 429 而不是 500", r.status_code == 429, f"status={r.status_code}")
        check("429 带 CORS 头",
              r.headers.get("access-control-allow-origin") == "http://localhost:5173",
              str(r.headers.get("access-control-allow-origin")))
    finally:
        _s.STRESS_TEST_MODE = old_stress
        _s.RATE_LIMIT_PER_MINUTE = old_rate
        rate_limiter.buckets.clear()

print("\n" + "=" * 60)
if FAILED:
    print(f"失败 {len(FAILED)} 项：")
    for f in FAILED:
        print(f"  - {f}")
    sys.exit(1)
print("全部通过")
