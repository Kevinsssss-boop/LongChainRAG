import json
from datetime import datetime
from typing import AsyncGenerator
from sqlalchemy.orm import Session
import httpx
from app.config import settings
from app.models import ChatSession, Message
from app.rag.retriever import HybridRetriever
from app.rag.reranker import Reranker
from app.services.cache_service import SemanticCache

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
        self.cache = SemanticCache()
        self.api_key = settings.LLM_API_KEY
        self.api_url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        self.model = settings.LLM_MODEL_NAME

    async def generate_stream(self, session_id: str, user_message: str) -> AsyncGenerator[dict, None]:
        # Save user message + update session timestamp in ONE commit
        user_msg = Message(session_id=session_id, role="user", content=user_message)
        self.db.add(user_msg)
        session = self.db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if session:
            session.updated_at = datetime.utcnow()
        self.db.commit()

        # Check semantic cache
        cached = self.cache.lookup(user_message)
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
            # Retrieve relevant documents
            docs = self.retriever.retrieve(user_message, top_k=settings.RETRIEVAL_TOP_K)

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

            chat_history = self._get_chat_history(session_id)

            # Build messages
            system_content = RAG_SYSTEM_PROMPT.format(
                context=context, chat_history=chat_history, question=user_message,
            )
            messages = [
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_message},
            ]

            # Call LLM (sync httpx — works reliably with DashScope)
            with httpx.Client(timeout=120) as client:
                resp = client.post(
                    self.api_url,
                    json={"model": self.model, "messages": messages},
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                if resp.status_code != 200:
                    raise Exception(f"LLM error {resp.status_code}: {resp.text[:300]}")
                data = resp.json()
                full_response = data["choices"][0]["message"]["content"]
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

            # Store in cache
            self.cache.store(user_message, full_response, citations)

        except Exception as e:
            yield {"type": "error", "content": str(e)}

    def _get_chat_history(self, session_id: str) -> str:
        messages = (
            self.db.query(Message)
            .filter(Message.session_id == session_id)
            .order_by(Message.created_at)
            .limit(10)
            .all()
        )
        if not messages:
            return "（无历史对话）"
        parts = []
        for msg in messages[-10:]:
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
