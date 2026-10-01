"""上传：落盘路径穿越 + 体积校验。

背景 —— 这条穿越是**实测出来**的，不是推断：

kb_service 原来的写法是
    os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{filename}")
看着有 uuid 前缀就安全了，其实不然。Windows 在打开文件前会先做一次**纯词法**
的路径折叠，`<uuid>_..` 这个路径段会被紧跟其后的 `..` 直接吃掉，前缀等于没加：

    data/uploads/<uuid>_../../../evil.txt
      → data/uploads/<uuid>_.. / .. / .. / evil.txt
      → data/uploads / .. / evil.txt          ← <uuid>_.. 被吃掉了
      → data/evil.txt                          ← 逃出去了

实测 filename="../../../evil.txt" 确实会把文件写到 UPLOAD_DIR 之外。
（Linux 是逐段解析、要求每段真实存在，这个向量在那里不成立；但开发环境是
Windows，而且修法一样。）
"""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.config import settings
from app.services.kb_service import KnowledgeBaseService

# 全部是实测过的穿越形态
TRAVERSAL_PAYLOADS = [
    "../../../evil.txt",
    "..\\..\\..\\evil.txt",
    "/../../evil.txt",
    "\\..\\..\\evil.txt",
    "....//....//evil.txt",
    "a/b/c.txt",
    "..",
    ".",
    "",
    "normal.pdf",
]


@pytest.fixture(autouse=True)
def _no_vectorstore_or_embedder():
    """别让测试去碰真实的 Chroma 目录和 embedding 接口。"""
    with patch('app.services.kb_service.VectorStoreService'), \
         patch('app.services.kb_service.EmbeddingService'):
        yield


class TestBuildStoragePath:
    """落盘路径必须完全由服务端生成。"""

    def test_never_contains_client_filename(self, monkeypatch, tmp_path):
        monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))

        for payload in TRAVERSAL_PAYLOADS:
            path = KnowledgeBaseService.build_storage_path("pdf")
            resolved = Path(path).resolve()

            assert resolved.parent == tmp_path.resolve(), (
                f"{payload!r} 让落盘路径跑出了上传目录: {resolved}"
            )
            assert "evil" not in path
            assert resolved.suffix == ".pdf"

    def test_rejects_type_outside_whitelist(self):
        """file_type 会被拼进文件名，所以它必须来自白名单。"""
        with pytest.raises(ValueError):
            KnowledgeBaseService.build_storage_path("../../etc/passwd")


class TestProcessDocumentStaysInUploadDir:
    """端到端：拿穿越文件名走一遍 process_document。

    修复前这条会失败 —— 文件会落到 UPLOAD_DIR 之外。
    """

    @pytest.mark.parametrize("payload", TRAVERSAL_PAYLOADS)
    async def test_file_lands_inside_upload_dir(
        self, db, tmp_path, monkeypatch, admin_user, payload
    ):
        upload_dir = tmp_path / "uploads"
        upload_dir.mkdir()
        monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload_dir))

        with patch('app.services.kb_service.get_semantic_cache') as cache:
            service = KnowledgeBaseService(db)
            service.loader = MagicMock()
            service.loader.load.return_value = []
            service.splitter = MagicMock()
            service.splitter.split.return_value = []

            await service.process_document(
                filename=payload,
                content=b"probe",
                file_type="pdf",
                uploaded_by=admin_user.id,
            )

            # 知识库变动后必须让语义缓存作废
            cache.return_value.invalidate.assert_called_once()

        produced = [p for p in tmp_path.rglob("*") if p.is_file()]
        assert produced, (
            f"{payload!r}: uploads/ 里没有文件 —— 落盘路径跑到上传目录之外了"
        )
        assert len(produced) == 1, f"{payload!r} 产生了预期外的文件: {produced}"
        assert produced[0].parent == upload_dir

    async def test_client_filename_is_still_recorded_for_display(
        self, db, tmp_path, monkeypatch, admin_user
    ):
        """落盘名被替换了，但原始文件名仍要存进数据库供界面展示。"""
        upload_dir = tmp_path / "uploads"
        upload_dir.mkdir()
        monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload_dir))

        with patch('app.services.kb_service.get_semantic_cache'):
            service = KnowledgeBaseService(db)
            service.loader = MagicMock()
            service.loader.load.return_value = []
            service.splitter = MagicMock()
            service.splitter.split.return_value = []

            doc = await service.process_document(
                filename="2024年度报销制度.pdf",
                content=b"probe",
                file_type="pdf",
                uploaded_by=admin_user.id,
            )

        assert doc.filename == "2024年度报销制度.pdf"
        assert doc.stored_path != doc.filename
        assert "2024年度报销制度" not in doc.stored_path


class TestUploadSizeLimit:
    def test_oversized_upload_returns_413(self, client, auth_headers, monkeypatch):
        """超过上限返回 413。

        现在的实现是边读边判，超限立刻中断。原来是 `content = await file.read()`
        一口气读完整个文件才比大小 —— 而前端 Dragger 没做任何大小校验，
        一个 2GB 的文件会先把内存吃满，然后才回一句「超过限制」。
        """
        monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_MB", 0)

        resp = client.post(
            "/api/knowledge/upload",
            files={"file": ("big.txt", b"x" * 4096, "text/plain")},
            headers=auth_headers,
        )

        assert resp.status_code == 413
        assert "超过限制" in resp.json()["detail"]

    def test_unsupported_type_rejected_before_reading(self, client, auth_headers):
        resp = client.post(
            "/api/knowledge/upload",
            files={"file": ("malware.exe", b"x" * 16, "application/octet-stream")},
            headers=auth_headers,
        )

        assert resp.status_code == 400

    def test_non_admin_cannot_upload(self, client, other_auth_headers):
        resp = client.post(
            "/api/knowledge/upload",
            files={"file": ("a.txt", b"hello", "text/plain")},
            headers=other_auth_headers,
        )

        assert resp.status_code == 403
