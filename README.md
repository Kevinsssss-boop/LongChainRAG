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
- 🌓 **暗色模式**：支持亮色/暗色主题切换
- 📝 **对话导出**：支持导出对话为 Markdown 文件
- 📖 **API 文档**：FastAPI 自动生成 Swagger 文档

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

1. 编辑 `.env` 文件，填入你的 API Key：

```bash
LLM_API_KEY=sk-your-api-key
LLM_BASE_URL=          # 可选，使用其他兼容 API 时填写
LLM_MODEL_NAME=gpt-4o
```

### 一键启动（Windows）

双击项目根目录 `start.bat`，自动安装依赖并启动前后端服务。

### 手动启动

**后端**：
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**前端**：
```bash
cd frontend
npm install
npm run dev
```

### 访问地址

- 前端页面：http://localhost:5173
- API 文档（Swagger）：http://localhost:8000/docs
- 健康检查：http://localhost:8000/api/health

### 默认管理员账号

- 用户名：`admin`
- 密码：`123456`

## 项目结构

```
LongChainRAG/
├── start.bat                 # Windows 一键启动脚本
├── .env                      # 环境变量配置
├── README.md
├── backend/                  # FastAPI 后端
│   ├── requirements.txt
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
│       └── middleware/       # 中间件
└── frontend/                 # React 前端
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