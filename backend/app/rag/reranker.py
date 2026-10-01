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

        # 按距离升序：metadata["score"] 是 Chroma 的 L2 距离，越小越相关
        # （见 retriever.py 写入该字段的位置）。
        # 缺字段的按 1.0 当作「最不相关」—— 下面最终排序用的也是 1.0，
        # 原来这里写 0.5、那里写 1.0，同一个字段两处默认值不一致。
        docs_with_scores = sorted(
            [(doc, doc.metadata.get("score", 1.0)) for doc in documents],
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