"""Tests for SemanticCache — LRU + embedding similarity."""
from unittest.mock import MagicMock, patch

import pytest

import app.services.cache_service as cache_module
from app.config import settings
from app.services.cache_service import SemanticCache, get_semantic_cache


@pytest.fixture
def cache():
    """一个干净的缓存，embedder 换成假的（不发网络请求）。

    注意这里不再用 `@patch.object(SemanticCache, '__init__', lambda self: None)`
    绕过构造函数。绕过之后 `self._lock` 不存在，而现在它必须有 —— 缓存已经
    改成模块级单例，会被多个请求线程同时读写。
    """
    with patch('app.services.cache_service.EmbeddingService'):
        c = SemanticCache()
    c.embedder = MagicMock()
    c.embedder.embed_query.return_value = [1.0, 0.0]
    c.invalidate()
    return c


class TestCosineSimilarity:
    """余弦相似度的边界行为。"""

    def test_identical_vectors(self):
        assert SemanticCache._cosine_similarity([1.0, 0.0, 0.0], [1.0, 0.0, 0.0]) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        assert SemanticCache._cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)

    def test_opposite_vectors(self):
        assert SemanticCache._cosine_similarity([1.0, 0.0], [-1.0, 0.0]) == pytest.approx(-1.0)

    def test_zero_vector_returns_zero_not_nan(self):
        """零向量返回 0.0 而不是 nan。

        原来的实现是 np.dot(a,b) / (norm(a)*norm(b))，零向量会 0 除 0 得到 nan。
        比较时 `nan > best` 恒为 False，行为上碰巧安全，但会一路带出
        RuntimeWarning，而且让调用方无法推理。现在显式返回 0.0。
        """
        result = SemanticCache._cosine_similarity([0.0, 0.0], [1.0, 0.0])
        assert result == 0.0
        assert result == result  # 自反 => 不是 nan


class TestCacheStore:
    """写入与淘汰。"""

    def test_store_adds_entry(self, cache):
        cache.store("question1", "answer1", [])
        assert len(cache) == 1

    def test_store_evicts_oldest_when_full(self, cache, monkeypatch):
        monkeypatch.setattr(settings, 'CACHE_MAX_SIZE', 2)

        cache.store("q1", "a1", [])
        cache.store("q2", "a2", [])
        assert len(cache) == 2

        cache.store("q3", "a3", [])  # 应该淘汰最久未使用的 q1
        assert len(cache) == 2
        remaining = {entry["question"] for entry in cache.cache.values()}
        assert remaining == {"q2", "q3"}

    def test_store_survives_embedding_failure(self, cache):
        """embedding 服务挂了也要能存 —— 只是永远命中不了语义匹配。

        缓存是加速手段，不该成为问答的失败点。
        """
        cache.embedder.embed_query.side_effect = RuntimeError("embedding 服务不可用")
        cache.store("q", "a", [])

        assert len(cache) == 1
        assert cache.lookup("q") is None  # embedder 仍然在抛，lookup 应安静返回 None


class TestCacheLookup:
    """语义查找。"""

    def test_empty_cache_returns_none(self, cache):
        assert cache.lookup("any question") is None

    def test_lookup_hit_above_threshold(self, cache):
        cache.embedder.embed_query.return_value = [1.0, 0.0]
        cache.store("原始问题", "cached answer", [{"source": "a.pdf"}])

        # 完全相同的问题 => 相似度 1.0，高于阈值 0.92
        hit = cache.lookup("换一种说法的同一个问题")

        assert hit is not None, "相同向量应当命中缓存"
        assert hit["response"] == "cached answer"
        assert hit["citations"] == [{"source": "a.pdf"}]

    def test_lookup_miss_below_threshold(self, cache):
        cache.embedder.embed_query.return_value = [1.0, 0.0]
        cache.store("q", "a", [])

        cache.embedder.embed_query.return_value = [0.0, 1.0]  # 正交 => 相似度 0
        assert cache.lookup("完全无关的问题") is None

    def test_lookup_picks_most_similar_not_first_match(self, cache):
        """命中的应当是相似度最高的那条，而不是第一条达标的。

        旧实现是「从头扫，碰到第一个 similarity >= 阈值就 return」。
        下面两条都超过阈值，旧实现会返回先插入的那条（相似度更低）。
        """
        # sim([1,0],[1,0.4]) = 1/sqrt(1.16) ≈ 0.928  > 0.92
        cache.cache["first"] = {
            "question": "x", "response": "first but less similar",
            "citations": [], "embedding": [1.0, 0.4],
        }
        # sim([1,0],[1,0.01]) ≈ 0.99995
        cache.cache["second"] = {
            "question": "y", "response": "second but closest",
            "citations": [], "embedding": [1.0, 0.01],
        }
        cache.embedder.embed_query.return_value = [1.0, 0.0]

        hit = cache.lookup("q")

        assert hit is not None
        assert hit["response"] == "second but closest"

    def test_lookup_ignores_entries_without_embedding(self, cache):
        cache.cache["no_embedding"] = {
            "question": "x", "response": "a", "citations": [], "embedding": None,
        }
        cache.embedder.embed_query.return_value = [1.0, 0.0]
        assert cache.lookup("q") is None

    def test_lookup_survives_embedding_failure(self, cache):
        cache.store("q", "a", [])
        cache.embedder.embed_query.side_effect = RuntimeError("embedding 服务不可用")
        assert cache.lookup("q") is None


class TestInvalidate:
    """知识库变动后必须清空缓存。

    不清的话，管理员删掉某篇文档后，缓存里那些带着旧文件名的回答还会继续
    被返回 —— 引用指向一个已经不存在的来源。
    """

    def test_invalidate_clears_entries(self, cache):
        cache.store("q1", "a1", [])
        cache.store("q2", "a2", [])
        assert len(cache) == 2

        removed = cache.invalidate()

        assert removed == 2
        assert len(cache) == 0
        assert cache.lookup("q1") is None


class TestSingleton:
    """缓存必须是模块级单例 —— 这正是「语义缓存从未生效」的根因。

    原来是 ChatService.__init__ 里直接 SemanticCache()，也就是每个请求 new
    一个空缓存，存进去的条目随请求结束一起消失，命中率恒为 0。
    """

    @pytest.fixture(autouse=True)
    def _reset_singleton(self):
        with patch('app.services.cache_service.EmbeddingService'):
            cache_module._cache_instance = None
            yield
            cache_module._cache_instance = None

    def test_returns_same_instance(self):
        assert get_semantic_cache() is get_semantic_cache()

    def test_entries_survive_a_fresh_handle(self):
        """通过单例存进去的条目，下一次取单例时还在。"""
        first = get_semantic_cache()
        first.embedder = MagicMock()
        first.embedder.embed_query.return_value = [1.0, 0.0]
        first.store("q", "a", [])

        # 模拟「下一个请求」：重新取一次单例
        second = get_semantic_cache()

        assert second is first
        assert second.lookup("q") is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
