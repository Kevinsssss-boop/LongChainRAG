"""Embedding service using direct httpx calls to DashScope API."""
import hashlib
import random as _random

import httpx
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from app.config import DEFAULT_LLM_BASE_URL, settings


def _request_embedding(
    client: httpx.Client, api_url: str, api_key: str, model: str, text: str
) -> list[float]:
    """向 OpenAI 兼容网关要一条 embedding。三处调用共用这一份请求逻辑。"""
    resp = client.post(
        api_url,
        json={"model": model, "input": text},
        headers={"Authorization": f"Bearer {api_key}"},
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Embedding error {resp.status_code}: {resp.text[:300]}")
    return resp.json()["data"][0]["embedding"]


class EmbeddingService:
    """Service for generating embeddings and storing to vector store."""

    def __init__(self):
        self.api_key = settings.LLM_API_KEY
        # 让 LLM_BASE_URL 真正生效（原来硬编码了 DashScope 地址）
        base = (settings.LLM_BASE_URL or DEFAULT_LLM_BASE_URL).rstrip("/")
        self.api_url = f"{base}/embeddings"
        self.model = settings.EMBEDDING_MODEL_NAME

        # Create a custom embeddings class for LangChain ChromaDB
        self.embeddings = _DashScopeEmbeddings(self.api_key, self.api_url, self.model)

    def embed_query(self, text: str) -> list[float]:
        return self._call_api(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._call_api(t) for t in texts]

    def embed_and_store(self, documents: list[Document], doc_id: str):
        """Embed documents and store in ChromaDB."""
        from app.rag.vectorstore import VectorStoreService

        vectorstore = VectorStoreService()
        vectorstore.add_documents(documents, doc_id)

    def _call_api(self, text: str) -> list[float]:
        """Call the embedding API for a single text."""
        if settings.STRESS_TEST_MODE:
            return self._mock_embed(text)

        with httpx.Client(timeout=60) as client:
            return _request_embedding(client, self.api_url, self.api_key, self.model, text)

    @staticmethod
    def _mock_embed(text: str) -> list[float]:
        """Deterministic fake embedding: same text always produces same vector.

        Uses an MD5 hash of the text as the RNG seed, so a given string maps to
        the same 1024-dim vector on every run — which is what makes the
        stress-test and offline-test paths reproducible.
        """
        seed = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
        rng = _random.Random(seed)
        return [rng.random() for _ in range(1024)]


class _DashScopeEmbeddings(Embeddings):
    """LangChain-compatible embeddings wrapper.

    **这条路径才是检索真正走的。** Chroma 的 `embedding_function` 指向它，
    所以每次 similarity_search 都会经过这里 —— 而不是经过上面
    EmbeddingService._call_api。

    原来这里两个方法都无条件发真实请求，压根没看 STRESS_TEST_MODE，于是
    「压测模式不发任何外部请求」是假的：/api/chat 先检索再进 mock 分支，
    而检索这一步已经在打 embedding 接口了。压测数据因此既不完全离线、
    也不可复现（真实 embedding 受服务端版本影响）。
    """

    def __init__(self, api_key: str, api_url: str, model: str):
        self.api_key = api_key
        self.api_url = api_url
        self.model = model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if settings.STRESS_TEST_MODE:
            return [EmbeddingService._mock_embed(t) for t in texts]

        results = []
        # 整批复用一个 client，省掉每条一次 TCP + TLS 握手
        with httpx.Client(timeout=120) as client:
            for text in texts:
                results.append(
                    _request_embedding(client, self.api_url, self.api_key, self.model, text)
                )
        return results

    def embed_query(self, text: str) -> list[float]:
        if settings.STRESS_TEST_MODE:
            return EmbeddingService._mock_embed(text)

        with httpx.Client(timeout=60) as client:
            return _request_embedding(client, self.api_url, self.api_key, self.model, text)
