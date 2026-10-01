"""Tests for RAG core modules — Splitter, Retriever, Reranker."""
import pytest
from unittest.mock import patch, MagicMock
import sys
sys.path.insert(0, '.')

from langchain_core.documents import Document


class TestTextSplitter:
    """Test document text splitting."""

    def setup_method(self):
        from app.rag.splitter import TextSplitter
        self.splitter = TextSplitter()

    def test_split_single_short_document(self):
        docs = [Document(page_content="This is a short text.")]
        chunks = self.splitter.split(docs)
        assert len(chunks) >= 1
        assert "short text" in chunks[0].page_content

    def test_split_long_document(self):
        long_text = "This is sentence one. " * 50  # ~1000 chars
        docs = [Document(page_content=long_text)]
        chunks = self.splitter.split(docs)
        assert len(chunks) >= 2  # Should be split into multiple chunks

    def test_split_preserves_metadata(self):
        docs = [Document(page_content="content", metadata={"source": "test.pdf"})]
        chunks = self.splitter.split(docs)
        assert all(chunk.metadata.get("source") == "test.pdf" for chunk in chunks)

    def test_split_empty_list(self):
        chunks = self.splitter.split([])
        assert chunks == []

    def test_split_multiple_documents(self):
        docs = [
            Document(page_content="First document content."),
            Document(page_content="Second document content."),
        ]
        chunks = self.splitter.split(docs)
        total_content = "".join(c.page_content for c in chunks)
        assert "First document" in total_content
        assert "Second document" in total_content


class TestHybridRetriever_Tokenize:
    """Test BM25 tokenizer."""

    def test_tokenize_basic(self):
        from app.rag.retriever import HybridRetriever
        tokens = HybridRetriever._tokenize("hello world foo bar")
        assert tokens == ["hello", "world", "foo", "bar"]

    def test_tokenize_lowercases(self):
        from app.rag.retriever import HybridRetriever
        tokens = HybridRetriever._tokenize("HELLO World")
        assert tokens == ["hello", "world"]

    def test_tokenize_empty(self):
        from app.rag.retriever import HybridRetriever
        tokens = HybridRetriever._tokenize("")
        assert tokens == []


class TestReranker:
    """Test document re-ranking."""

    def setup_method(self):
        from app.rag.reranker import Reranker
        self.reranker = Reranker()

    def test_rerank_fewer_docs_than_top_k(self):
        docs = [
            Document(page_content="doc A", metadata={"score": 0.9}),
            Document(page_content="doc B", metadata={"score": 0.5}),
        ]
        result = self.reranker.rerank("query", docs, top_k=4)
        assert len(result) == 2  # Returns as-is when fewer than top_k

    def test_rerank_sorts_by_distance_ascending(self):
        """metadata["score"] 是**距离**，越小越相关 —— 升序才是对的。

        这个语义来自 retriever.py：它把 Chroma similarity_search_with_score
        的返回值（L2 距离，越小越相似）写进 doc.metadata["score"]，chat_service
        再按 1/(1+distance) 换算成界面上显示的相似度百分比。

        所以下面 0.3 比 0.9 更相关，应当排在前面。

        原来的测试把这个字段当成「分数越大越好」，与代码契约正好相反，
        所以它从加进来那天起就是红的（已核实：在未做任何改动的原始代码上
        同样失败）。断言写错方向比不写测试更糟——它会诱导人「修」好代码。
        """
        docs = [
            Document(page_content="far", metadata={"score": 0.9}),
            Document(page_content="near", metadata={"score": 0.3}),
            Document(page_content="mid", metadata={"score": 0.6}),
        ]
        result = self.reranker.rerank("query", docs, top_k=2)

        assert len(result) == 2
        assert result[0].page_content == "near"
        assert result[1].page_content == "mid"

    def test_rerank_guarantees_one_chunk_per_source(self):
        """来源多样性：同一份文档的相邻片段不能把上下文位置占满。

        这是 reranker 存在的唯一理由（见作品集页面的「技术架构」一节），
        但它此前完全没有测试覆盖。
        """
        docs = [
            Document(page_content="a1", metadata={"score": 0.1, "source": "a.pdf"}),
            Document(page_content="a2", metadata={"score": 0.2, "source": "a.pdf"}),
            Document(page_content="a3", metadata={"score": 0.3, "source": "a.pdf"}),
            Document(page_content="b1", metadata={"score": 0.9, "source": "b.pdf"}),
        ]
        result = self.reranker.rerank("query", docs, top_k=2)

        sources = [d.metadata["source"] for d in result]
        assert "b.pdf" in sources, (
            "b.pdf 唯一的那个片段应当挤进前 2 —— 否则 a.pdf 的三条相邻片段"
            "会把上下文窗口占满，这正是重排序要解决的问题"
        )

    def test_rerank_missing_score_defaults(self):
        docs = [
            Document(page_content="no score"),
            Document(page_content="has score", metadata={"score": 0.8}),
        ]
        result = self.reranker.rerank("query", docs, top_k=2)
        assert len(result) == 2


class TestRRFFusion:
    """Test Reciprocal Rank Fusion algorithm."""

    def setup_method(self):
        from app.rag.retriever import HybridRetriever
        self.retriever = HybridRetriever()

    def test_rrf_merges_results(self):
        semantic = [
            (Document(page_content="A"), 0.9),
            (Document(page_content="B"), 0.7),
        ]
        bm25 = [
            (Document(page_content="B"), 0.8),
            (Document(page_content="C"), 0.6),
        ]
        merged = self.retriever._rrf_fusion(semantic, bm25, k=60)
        # B appears in both lists, should have highest fused score
        merged.sort(key=lambda x: x[1], reverse=True)
        assert merged[0][0].page_content == "B"

    def test_rrf_empty_lists(self):
        merged = self.retriever._rrf_fusion([], [], k=60)
        assert merged == []


class TestDocumentLoader:
    """Test file type detection and loading."""

    def test_get_file_type_pdf(self):
        from app.services.kb_service import KnowledgeBaseService
        kb = KnowledgeBaseService(None)
        assert kb.get_file_type("report.pdf") == "pdf"

    def test_get_file_type_txt(self):
        from app.services.kb_service import KnowledgeBaseService
        kb = KnowledgeBaseService(None)
        assert kb.get_file_type("notes.txt") == "txt"

    def test_get_file_type_csv(self):
        from app.services.kb_service import KnowledgeBaseService
        kb = KnowledgeBaseService(None)
        assert kb.get_file_type("data.csv") == "csv"

    def test_get_file_type_md(self):
        from app.services.kb_service import KnowledgeBaseService
        kb = KnowledgeBaseService(None)
        assert kb.get_file_type("README.md") == "md"

    def test_get_file_type_unknown(self):
        from app.services.kb_service import KnowledgeBaseService
        kb = KnowledgeBaseService(None)
        assert kb.get_file_type("image.png") == "unknown"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
