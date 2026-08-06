import hashlib
import numpy as np
from typing import Optional
from collections import OrderedDict
from app.rag.embedder import EmbeddingService
from app.config import settings


class SemanticCache:
    """LRU cache with embedding similarity for semantic deduplication."""

    def __init__(self):
        self.cache = OrderedDict()
        self.embedder = EmbeddingService()

    def lookup(self, question: str) -> Optional[dict]:
        """Check if a semantically similar question has been cached."""
        if not self.cache:
            return None

        try:
            question_embedding = self.embedder.embed_query(question)

            for key, value in self.cache.items():
                cached_embedding = value.get("embedding")
                if cached_embedding is None:
                    continue
                similarity = self._cosine_similarity(question_embedding, cached_embedding)
                if similarity >= settings.CACHE_SIMILARITY_THRESHOLD:
                    # Move to end (LRU)
                    self.cache.move_to_end(key)
                    return {"response": value["response"], "citations": value["citations"]}
        except Exception:
            pass

        return None

    def store(self, question: str, response: str, citations: list):
        """Store a response in the cache."""
        key = hashlib.md5(question.encode()).hexdigest()
        try:
            embedding = self.embedder.embed_query(question)
        except Exception:
            embedding = None

        self.cache[key] = {
            "question": question,
            "response": response,
            "citations": citations,
            "embedding": embedding,
        }

        # Evict oldest if over capacity
        while len(self.cache) > settings.CACHE_MAX_SIZE:
            self.cache.popitem(last=False)

    @staticmethod
    def _cosine_similarity(a, b):
        a = np.array(a)
        b = np.array(b)
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))