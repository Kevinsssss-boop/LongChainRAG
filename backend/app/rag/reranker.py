from typing import List
from langchain_core.documents import Document
from app.config import settings


class Reranker:
    """Re-rank retrieved documents with source diversity."""

    def __init__(self):
        pass  # No LLM needed for score-based reranking

    def rerank(self, query: str, documents: List[Document], top_k: int = 4) -> List[Document]:
        """Re-rank documents by relevance, ensuring source diversity."""
        if not documents:
            return documents

        # Sort by semantic score (lower distance = more relevant)
        # For display: similarity = 1/(1+distance), higher = more relevant
        # For sorting: sort by distance ascending
        docs_with_scores = sorted(
            [(doc, doc.metadata.get("score", 0.5)) for doc in documents],
            key=lambda x: x[1],  # lower distance first
        )

        # Ensure at least one chunk from each source document
        seen_sources = set()
        diverse_results = []
        remaining = []

        for doc, score in docs_with_scores:
            source = doc.metadata.get("source", "unknown")
            if source not in seen_sources:
                diverse_results.append(doc)
                seen_sources.add(source)
            else:
                remaining.append(doc)

        # Fill remaining slots with next best matches
        for doc in remaining:
            if len(diverse_results) >= top_k:
                break
            diverse_results.append(doc)

        # Final sort: lowest distance (= most relevant) first
        diverse_results.sort(
            key=lambda d: d.metadata.get("score", 1.0),
        )

        return diverse_results[:top_k]