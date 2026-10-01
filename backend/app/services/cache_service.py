import hashlib
import threading
from collections import OrderedDict
from typing import Optional

import numpy as np

from app.config import settings
from app.rag.embedder import EmbeddingService


class SemanticCache:
    """LRU + 向量相似度的语义缓存。

    作用：语义相近的问题直接复用上一次的回答，省掉一整轮检索 + 生成。

    两点注意：

    * **它现在会被并发访问**（模块级单例 + 请求跑在线程池里），而
      OrderedDict 的 move_to_end / popitem 不是原子操作，所以读写都得加锁。
    * **知识库变动后必须 invalidate()**。缓存里的回答带着引用（文件名 + 片段），
      管理员删掉某篇文档后，缓存还会继续把已经不存在的文档当来源返回。
      这是这个缓存真正的风险 —— 而不是「A 用户的回答被 B 用户命中」：
      本项目的知识库是全局共享的（单一 Chroma collection，没有按用户分区），
      B 拿到的本来就是同一份语料给出的同一个答案。
      如果以后知识库改成按用户隔离，这个缓存必须同步改成按用户分桶。
    """

    def __init__(self):
        self.cache: OrderedDict[str, dict] = OrderedDict()
        self.embedder = EmbeddingService()
        self._lock = threading.Lock()

    @staticmethod
    def _cosine_similarity(a, b) -> float:
        """余弦相似度。任一向量为零向量时返回 0.0，而不是 nan。

        （返回 nan 的话，后面的 `nan > best` 恒为 False，调用方拿到的行为
        虽然碰巧是对的，但会一路带着 RuntimeWarning。）
        """
        vec_a = np.asarray(a, dtype=np.float64)
        vec_b = np.asarray(b, dtype=np.float64)
        denom = float(np.linalg.norm(vec_a) * np.linalg.norm(vec_b))
        if denom == 0:
            return 0.0
        return float(np.dot(vec_a, vec_b) / denom)

    def lookup(self, question: str) -> Optional[dict]:
        """查出语义最接近的一条缓存，相似度不足则返回 None。"""
        with self._lock:
            if not self.cache:
                return None
            entries = list(self.cache.items())

        try:
            query_vec = self.embedder.embed_query(question)
        except Exception:
            # 缓存是加速手段，不是依赖。embedding 服务不可用不该让问答整体失败。
            return None

        # 取相似度最高的那条，而不是第一条达标的。
        # 原来是从头扫、碰到第一个超过阈值就返回，可能返回一条次优的匹配 ——
        # 排序在前的条目语义上未必更接近。
        best_key: Optional[str] = None
        best_similarity = 0.0
        for key, value in entries:
            cached_embedding = value.get("embedding")
            if cached_embedding is None:
                continue
            similarity = self._cosine_similarity(query_vec, cached_embedding)
            if similarity > best_similarity:
                best_similarity = similarity
                best_key = key

        if best_key is None or best_similarity < settings.CACHE_SIMILARITY_THRESHOLD:
            return None

        with self._lock:
            # 两段加锁之间可能已经被 invalidate / 淘汰掉
            if best_key not in self.cache:
                return None
            self.cache.move_to_end(best_key)  # LRU：命中即置为最近使用
            entry = self.cache[best_key]
            return {"response": entry["response"], "citations": entry["citations"]}

    def store(self, question: str, response: str, citations: list):
        """存入一条回答。embedding 失败也存（只是永远不会被语义命中）。"""
        try:
            embedding = self.embedder.embed_query(question)
        except Exception:
            embedding = None

        key = hashlib.md5(question.encode()).hexdigest()
        with self._lock:
            self.cache[key] = {
                "question": question,
                "response": response,
                "citations": citations,
                "embedding": embedding,
            }
            self.cache.move_to_end(key)
            # 超出容量就淘汰最久未使用的
            while len(self.cache) > settings.CACHE_MAX_SIZE:
                self.cache.popitem(last=False)

    def invalidate(self) -> int:
        """清空缓存，返回清掉的条数。知识库有任何变动后都要调。"""
        with self._lock:
            count = len(self.cache)
            self.cache.clear()
        return count

    def __len__(self) -> int:
        with self._lock:
            return len(self.cache)


_cache_instance: Optional[SemanticCache] = None
_cache_instance_lock = threading.Lock()


def get_semantic_cache() -> SemanticCache:
    """取模块级单例。

    原来是 `ChatService.__init__` 里直接 `SemanticCache()`，也就是每个请求
    new 一个空缓存 —— 存进去的条目随请求结束一起消失，命中率恒为 0。
    README 却把「语义缓存」列为已完成特性。
    """
    global _cache_instance
    if _cache_instance is None:
        with _cache_instance_lock:
            if _cache_instance is None:
                _cache_instance = SemanticCache()
    return _cache_instance
