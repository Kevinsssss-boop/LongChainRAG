import json
from datetime import datetime
from typing import AsyncGenerator
from sqlalchemy.orm import Session
import httpx
from starlette.concurrency import run_in_threadpool
from app.config import DEFAULT_LLM_BASE_URL, settings
from app.models import ChatSession, Message
from app.rag.retriever import HybridRetriever
from app.rag.reranker import Reranker
from app.services.cache_service import get_semantic_cache

RAG_SYSTEM_PROMPT = """你是一个专业的电商商品知识库问答助手，基于提供的知识库内容和自身知识，准确、详细地回答用户的问题。

请遵循以下规则：
1. 如果知识库中有相关信息，必须优先使用并标注引用来源 [1]、[2] 等
2. 如果知识库中没有相关信息，则基于自身知识直接回答，不需要强行引用
3. 不要编造不存在于知识库中的商品信息
4. 回答要结构化、清晰，使用 Markdown 格式

当前知识库内容：
{context}

对话历史：
{chat_history}

用户问题：{question}
请回答："""


class ChatService:
    def __init__(self, db: Session):
        self.db = db
        self.retriever = HybridRetriever()
        self.reranker = Reranker()
        # 模块级单例。原来这里是 SemanticCache()，也就是每次请求 new 一个
        # 空缓存 —— 存进去的东西随请求结束一起丢掉，命中率恒为 0。README 却
        # 把「语义缓存」列为已完成特性。
        self.cache = get_semantic_cache()
        self.api_key = settings.LLM_API_KEY
        # 让 LLM_BASE_URL 真正生效：.env.example 把它写成可配置项，
        # 但原来这里硬编码了 DashScope 地址，那个配置从来没被读过。
        base = (settings.LLM_BASE_URL or DEFAULT_LLM_BASE_URL).rstrip("/")
        self.api_url = f"{base}/chat/completions"
        self.model = settings.LLM_MODEL_NAME

    async def generate_stream(self, session_id: str, user_message: str) -> AsyncGenerator[dict, None]:
        # Save user message + update session timestamp in ONE commit
        user_msg = Message(session_id=session_id, role="user", content=user_message)
        self.db.add(user_msg)
        session = self.db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if session:
            session.updated_at = datetime.utcnow()
        self.db.commit()

        # Check semantic cache.
        # 丢进线程池：lookup 内部要调一次 embedding 接口（同步 httpx），
        # 直接在事件循环里跑同样会卡住整个服务。
        cached = await run_in_threadpool(self.cache.lookup, user_message)
        if cached:
            assistant_msg = Message(
                session_id=session_id, role="assistant",
                content=cached["response"], citations=cached["citations"], token_count=0,
            )
            self.db.add(assistant_msg)
            self.db.commit()
            yield {"type": "token", "content": cached["response"]}
            yield {"type": "citations", "data": cached["citations"]}
            return

        try:
            # Retrieve relevant documents.
            # 必须离开事件循环：ChromaDB 查询与 BM25 建索引都是同步阻塞的，
            # 而 retriever 目前每次请求都会把整个语料重新 tokenize 一遍来建
            # BM25 索引 —— 语料一大，直接卡死所有人。
            docs = await run_in_threadpool(
                self.retriever.retrieve, user_message, settings.RETRIEVAL_TOP_K
            )

            # Re-rank
            docs = self.reranker.rerank(user_message, docs, top_k=settings.FINAL_TOP_K)

            # Build context and citations
            if docs:
                context_parts = []
                citations = []
                for i, doc in enumerate(docs):
                    source = doc.metadata.get("source", "未知来源")
                    context_parts.append(f"[{i+1}] 来源: {source}\n{doc.page_content}")
                    raw_score = doc.metadata.get("score", 0)
                    # ChromaDB returns L2 distance (lower = more similar),
                    # convert to similarity percentage (higher = more relevant)
                    similarity = 1.0 / (1.0 + float(raw_score))
                    citations.append({
                        "index": i + 1,
                        "content": doc.page_content[:300],
                        "source": source,
                        "score": round(similarity, 3),
                    })
                context = "\n\n".join(context_parts)
            else:
                context = "（知识库为空，请直接基于你的知识回答）"
                citations = []

            # --- Stress Test Mock Path ---
            # 注意这里**不写缓存**，是有意的：压测要测的就是「每次都走完整
            # 检索 + 生成」的最坏路径。写进去反而会让第二轮压测变成打缓存，
            # 测出来的数字没有意义。
            if settings.STRESS_TEST_MODE:
                source_info = citations[0]["source"] if citations else "N/A"
                mock_response = (
                    f"[STRESS TEST MOCK] Answer to: {user_message}\n\n"
                    f"Retrieved {len(docs)} chunks from knowledge base. "
                    f"Top source: {source_info}.\n\n"
                    f"This is a mock response for stress testing. "
                    f"In production, this would be a detailed RAG answer "
                    f"with citations and product information."
                )
                yield {"type": "token", "content": mock_response}
                yield {"type": "citations", "data": citations}

                assistant_msg = Message(
                    session_id=session_id, role="assistant",
                    content=mock_response, citations=citations, token_count=0,
                )
                self.db.add(assistant_msg)
                self._auto_title(session_id, commit=False)
                self.db.commit()
                return
            # --- End Mock Path ---

            chat_history = self._get_chat_history(session_id, exclude_message_id=user_msg.id)

            # Build messages
            system_content = RAG_SYSTEM_PROMPT.format(
                context=context, chat_history=chat_history, question=user_message,
            )
            messages = [
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_message},
            ]

            # Call LLM.
            # 必须是 AsyncClient：这里跑在事件循环上。原来用的是同步
            # httpx.Client，而一次大模型调用最长要挂 120 秒 —— 这期间整个
            # 进程对**所有**用户都不响应。不是「慢一点」，是一个人提问全站卡死。
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(
                    self.api_url,
                    json={"model": self.model, "messages": messages},
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                if resp.status_code != 200:
                    raise Exception(f"LLM error {resp.status_code}: {resp.text[:300]}")
                full_response = resp.json()["choices"][0]["message"]["content"]

            yield {"type": "token", "content": full_response}

            # Yield citations
            yield {"type": "citations", "data": citations}

            # Save assistant message
            assistant_msg = Message(
                session_id=session_id, role="assistant",
                content=full_response, citations=citations, token_count=0,
            )
            self.db.add(assistant_msg)
            self._auto_title(session_id, commit=False)
            self.db.commit()

            # Store in cache（同样会调 embedding 接口，放线程池）
            await run_in_threadpool(self.cache.store, user_message, full_response, citations)

        except Exception as e:
            yield {"type": "error", "content": str(e)}

    def _get_chat_history(
        self,
        session_id: str,
        exclude_message_id: str | None = None,
        limit: int = 10,
    ) -> str:
        """取**最近** limit 条消息，按时间正序拼成一段文本。

        原来写的是 .order_by(Message.created_at).limit(10) —— 升序 + limit
        拿到的是这个会话里**最旧**的 10 条。对话一旦超过 10 条，模型看到的
        历史就永久冻在开头，之后说的每一句话它都看不见，「多轮对话」从第
        11 条消息起就是摆设。要取最近的，必须先 desc 再 limit，取完翻回正序。

        exclude_message_id 排掉「本轮正在问的这一条」：调用方在进入生成流程时
        已经把用户消息写库了，不排掉的话它会在提示词里出现两次（历史里一次、
        末尾「用户问题」又一次）。
        """
        query = self.db.query(Message).filter(Message.session_id == session_id)
        if exclude_message_id is not None:
            query = query.filter(Message.id != exclude_message_id)

        messages = query.order_by(Message.created_at.desc()).limit(limit).all()
        if not messages:
            return "（无历史对话）"

        parts = []
        for msg in reversed(messages):  # 翻回时间正序
            role_label = "用户" if msg.role == "user" else "助手"
            parts.append(f"{role_label}: {msg.content[:200]}")
        return "\n".join(parts)

    def _auto_title(self, session_id: str, commit: bool = True):
        session = self.db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not session or session.title != "新对话":
            if commit:
                self.db.commit()
            return
        messages = (
            self.db.query(Message)
            .filter(Message.session_id == session_id, Message.role == "user")
            .order_by(Message.created_at)
            .first()
        )
        if messages and len(messages.content) > 6:
            session.title = messages.content[:20]
        elif messages:
            session.title = messages.content[:6]
        if commit:
            self.db.commit()
