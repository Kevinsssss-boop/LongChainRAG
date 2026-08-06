from typing import List
from langchain_core.documents import Document
from app.rag.vectorstore import VectorStoreService
from app.config import settings

try:
    from rank_bm25 import BM25Okapi

    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False


class HybridRetriever:
    """Hybrid retriever combining semantic search and BM25 keyword search."""

    def __init__(self):
        self.vectorstore = VectorStoreService()

    def retrieve(self, query: str, top_k: int = None) -> List[Document]:
        if top_k is None:
            top_k = settings.RETRIEVAL_TOP_K

        # Semantic search
        semantic_results = self.vectorstore.similarity_search_with_score(query, k=top_k)

        # Store original semantic similarity scores in metadata
        for doc, sim_score in semantic_results:
            doc.metadata["semantic_score"] = float(sim_score)

        # BM25 keyword search
        bm25_results = self._bm25_search(query, top_k=top_k) if BM25_AVAILABLE else []

        # Reciprocal Rank Fusion
        merged = self._rrf_fusion(semantic_results, bm25_results, k=60)

        # Sort by fused score and return top_k
        merged.sort(key=lambda x: x[1], reverse=True)
        # Attach score to document metadata (use semantic similarity for display)
        result = []
        for doc, fused_score in merged[:top_k]:
            # Use semantic_score if available, otherwise fall back to fused score
            display_score = doc.metadata.get("semantic_score", float(fused_score))
            doc.metadata["score"] = display_score
            doc.metadata["rrf_score"] = float(fused_score)
            result.append(doc)
        return result

    def _bm25_search(self, query: str, top_k: int = 4) -> List[tuple[Document, float]]:
        """BM25 keyword-based search."""
        try:
            all_docs = self.vectorstore.get_all_documents()
            if not all_docs:
                return []

            corpus = [doc.page_content for doc in all_docs]
            tokenized_corpus = [self._tokenize(text) for text in corpus]
            tokenized_query = self._tokenize(query)

            bm25 = BM25Okapi(tokenized_corpus)
            scores = bm25.get_scores(tokenized_query)

            # Normalize scores
            max_score = max(scores) if max(scores) > 0 else 1
            normalized_scores = [s / max_score for s in scores]

            # Get top_k
            indexed_scores = list(enumerate(normalized_scores))
            indexed_scores.sort(key=lambda x: x[1], reverse=True)

            return [(all_docs[i], score) for i, score in indexed_scores[:top_k]]
        except Exception:
            return []

    def _rrf_fusion(
        self,
        semantic: List[tuple[Document, float]],
        bm25: List[tuple[Document, float]],
        k: int = 60,
    ) -> List[tuple[Document, float]]:
        """Reciprocal Rank Fusion for combining search results."""
        doc_scores = {}

        # Add semantic results
        for rank, (doc, score) in enumerate(semantic):
            doc_key = doc.page_content[:100]
            doc_scores[doc_key] = doc_scores.get(doc_key, 0) + 1 / (k + rank + 1)

        # Add BM25 results
        for rank, (doc, score) in enumerate(bm25):
            doc_key = doc.page_content[:100]
            doc_scores[doc_key] = doc_scores.get(doc_key, 0) + 1 / (k + rank + 1)

        # Reconstruct document list
        all_results = {doc.page_content[:100]: doc for doc, _ in semantic}
        for doc, _ in bm25:
            key = doc.page_content[:100]
            if key not in all_results:
                all_results[key] = doc

        return [(all_results[key], score) for key, score in doc_scores.items()]

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Simple tokenizer for BM25."""
        return text.lower().split()