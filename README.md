# RAG 企业级知识库问答系统

基于 LangChain + FastAPI + React 构建的智能知识库问答系统，面向电商商品知识库场景。

## 功能特性

- 🤖 **智能问答**：基于知识库内容的精准回答，支持流式输出打字机效果
- 📚 **知识库管理**：支持 PDF/TXT/CSV/Markdown 文档上传、分块、向量化存储
- 📌 **引用来源**：回答中自动标注知识库引用，可点击查看原文片段
- 👥 **多用户体系**：注册/登录/JWT 认证，独立会话管理
- 🔐 **权限控制**：管理员可管理知识库，普通用户仅可问答
- 💬 **会话管理**：多轮对话、历史会话保存与恢复
- ⚡ **性能优化**：语义缓存、混合检索、重排序、限流保护
- 📖 **API 文档**：FastAPI 自动生成 Swagger 文档

> 这两条原来写在上面：「🌓 暗色模式」和「📝 对话导出」。实际代码里都没有 ——
> 主题在 `main.tsx` 里写死了 `theme.defaultAlgorithm`，导出功能前后端都搜不到。
> 已删除。功能列表上写着不存在的东西，比少写几条糟得多。

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI + Python 3.11+ |
| RAG 框架 | LangChain + LangChain Community |
| 向量数据库 | ChromaDB |
| 关系数据库 | SQLite + SQLAlchemy |
| 前端框架 | React 18 + TypeScript + Vite |
| UI 组件 | Ant Design 5 |
| LLM | OpenAI 兼容 API（可配置） |

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- OpenAI 兼容 API Key

### 配置

复制 `backend/.env.example` 成 **`backend/.env`**，再填自己的值。

> ⚠️ 路径是 `backend/.env`，**不是仓库根目录**。`config.py` 里的
> `env_file = ".env"` 是相对**进程工作目录**解析的，而 uvicorn 在 `backend/`
> 下启动。放在根目录会被静默忽略 —— 程序不报错，继续用默认值，
> 表现为「embedding 401」这类看起来毫不相干的错误。

```bash
LLM_API_KEY=sk-your-api-key
SECRET_KEY=            # 留空则开发态随机生成；生产环境必须显式配置
LLM_BASE_URL=          # 可选，默认阿里云百炼；换别的 OpenAI 兼容服务时填
LLM_MODEL_NAME=qwen-plus
```

### 启动方式一：Docker

```bash
docker compose up --build
```

一条命令起前后端，不依赖本机装了什么 Python / Node。想先不接大模型、
不花钱跑通全链路：

```bash
STRESS_TEST_MODE=true docker compose up --build
```

### 启动方式二：一键启动（Windows）

双击项目根目录 `start.bat`。它会在 `backend/.venv` 里按 `requirements.lock`
装精确版本（不污染全局 Python），然后拉起前后端。

### 启动方式三：手动启动

**后端**：
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows；Linux/macOS 用 source .venv/bin/activate
pip install -r requirements.lock   # 精确版本；想跟着上游升级用 requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**前端**：
```bash
cd frontend
npm ci        # 严格按 package-lock.json 装，比 npm install 可复现
npm run dev
```

### 访问地址

- 前端页面：http://localhost:5173
- API 文档（Swagger）：http://localhost:8000/docs
- 健康检查：http://localhost:8000/api/health

### 管理员账号

**没有默认密码。** 用户名是 `admin`，密码分两种情况：

- `backend/.env` 里配了 `ADMIN_PASSWORD` → 用它
- 没配 → 首次启动时随机生成，并**只在那一屏日志里打印一次**，
  注意看后端窗口（`start.bat` 起的那个 "RAG-Backend" 窗口）

> 此前默认密码是 `123456` 并且就写在上面这段文档里 —— 等于给每一个部署实例
> 发了一张公开的万能钥匙。已移除。

### 数据库

表结构由 Alembic 管理（`backend/alembic/`），启动时自动 `upgrade head`。
改完 `models/` 里的模型后生成一次迁移：

```bash
cd backend
python -m alembic revision --autogenerate -m "描述这次改动"
```

> 不要用 `Base.metadata.create_all()`：它只建缺失的表，**对已存在的表不加列**。
> 给已有表加字段后老库不会变化，接着所有查询都会报 `no such column`。

## 测试

```bash
cd backend
pip install -r requirements-dev.txt
pytest -q                       # 99 个用例
python scripts/smoke_test.py    # 离线端到端冒烟，18 项检查
```

```bash
cd frontend
npm test                        # 34 个用例
```

`smoke_test.py` 走的是**完整真实链路**（登录 → 上传文档 → 问答 → 反馈 → 限流），
只把外部 API 调用换成确定性 mock，所以既不花钱也不联网，就能验证整个系统是通的。
用 `STRESS_TEST_MODE` 让检索链路也离线可跑。

## 项目结构

```
LongChainRAG/
├── docker-compose.yml        # 一条命令起前后端
├── start.bat                 # Windows 一键启动脚本
├── README.md
├── backend/                  # FastAPI 后端
│   ├── Dockerfile
│   ├── requirements.txt      # 顶层依赖 + 版本区间
│   ├── requirements.lock     # 精确版本（可复现安装用），由 scripts/gen_lock.py 生成
│   ├── requirements-dev.txt  # 测试依赖
│   ├── alembic/              # 表结构迁移（启动时自动 upgrade head）
│   ├── scripts/
│   │   ├── smoke_test.py          # 离线端到端冒烟，不需要 API Key
│   │   ├── check_requirements.py  # 校验「代码 import 的包」都被声明了
│   │   └── gen_lock.py            # 重新生成 requirements.lock
│   ├── tests/                # pytest，99 个用例
│   └── app/
│       ├── main.py           # 应用入口
│       ├── config.py         # 配置管理
│       ├── api/              # API 路由
│       │   ├── auth.py       # 认证接口
│       │   ├── chat.py       # 问答接口（SSE 流式）
│       │   ├── session.py    # 会话管理
│       │   └── knowledge.py  # 知识库管理
│       ├── core/             # 核心模块
│       │   ├── security.py   # JWT + 密码哈希
│       │   └── dependencies.py
│       ├── models/           # 数据库模型
│       ├── schemas/          # Pydantic 模型
│       ├── rag/              # RAG 核心
│       │   ├── loader.py     # 文档加载
│       │   ├── splitter.py   # 文本分块
│       │   ├── embedder.py   # 向量化
│       │   ├── vectorstore.py# ChromaDB
│       │   ├── retriever.py  # 混合检索
│       │   └── reranker.py   # 重排序
│       ├── services/         # 业务逻辑
│       └── middleware/       # 中间件（CORS、限流）
└── frontend/                 # React 前端
    ├── Dockerfile
    ├── nginx.conf            # 生产镜像：托管静态文件 + 反代 /api
    └── src/
        ├── pages/            # 页面组件
        ├── components/       # UI 组件
        ├── store/            # Zustand 状态
        └── api/              # API 调用
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/register` | 用户注册 |
| POST | `/api/auth/login` | 用户登录 |
| PUT | `/api/auth/password` | 修改密码 |
| GET | `/api/auth/me` | 获取当前用户 |
| GET | `/api/sessions` | 会话列表 |
| POST | `/api/sessions` | 创建会话 |
| DELETE | `/api/sessions/{id}` | 删除会话 |
| POST | `/api/chat/{session_id}` | 发送消息（SSE 流式） |
| GET | `/api/knowledge/documents` | 文档列表（管理员） |
| POST | `/api/knowledge/upload` | 上传文档（管理员） |
| DELETE | `/api/knowledge/documents/{id}` | 删除文档（管理员） |