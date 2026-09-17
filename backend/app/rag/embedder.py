"""Embedding service using direct httpx calls to DashScope API."""
import hashlib
import random as _random
import httpx
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from app.config import settings


class EmbeddingService:
    """Service for generating embeddings and storing to vector store."""

    def __init__(self):
        self.api_key = settings.LLM_API_KEY
        self.api_url = "https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings"
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
        """Call DashScope embedding API for a single text."""
        if settings.STRESS_TEST_MODE:
            return self._mock_embed(text)

        with httpx.Client(timeout=60) as client:
            resp = client.post(
                self.api_url,
                json={"model": self.model, "input": text},
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            if resp.status_code != 200:
                raise Exception(f"Embedding error {resp.status_code}: {resp.text[:300]}")
            return resp.json()["data"][0]["embedding"]

    @staticmethod
    def _mock_embed(text: str) -> list[float]:
        """Deterministic fake embedding: same text always produces same vector.
        Uses MD5 hash of text as seed for reproducible 1024-dim vectors."""
        seed = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
        rng = _random.Random(seed)
        return [rng.random() for _ in range(1024)]


class _DashScopeEmbeddings(Embeddings):
    """LangChain-compatible embeddings wrapper for DashScope."""

    def __init__(self, api_key: str, api_url: str, model: str):
        self.api_key = api_key
        self.api_url = api_url
        self.model = model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of documents (one at a time for compatibility)."""
        results = []
        with httpx.Client(timeout=120) as client:
            for text in texts:
                resp = client.post(
                    self.api_url,
                    json={"model": self.model, "input": text},
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                if resp.status_code != 200:
                    raise Exception(f"Embedding error {resp.status_code}: {resp.text[:200]}")
                results.append(resp.json()["data"][0]["embedding"])
        return results

    def embed_query(self, text: str) -> list[float]:
        """Embed a single query."""
        with httpx.Client(timeout=60) as client:
            resp = client.post(
                self.api_url,
                json={"model": self.model, "input": text},
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            if resp.status_code != 200:
                raise Exception(f"Embedding error {resp.status_code}: {resp.text[:200]}")
            return resp.json()["data"][0]["embedding"]
