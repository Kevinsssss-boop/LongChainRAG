import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from app.config import settings
from app.rag.embedder import EmbeddingService


class VectorStoreService:
    """Service for ChromaDB vector store operations."""

    def __init__(self):
        self.client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self.embedder = EmbeddingService()
        self.vectorstore = Chroma(
            client=self.client,
            collection_name="knowledge_base",
            embedding_function=self.embedder.embeddings,
        )

    def add_documents(self, documents: list[Document], doc_id: str):
        """Add documents to vector store with metadata."""
        # Add doc_id to each document's metadata
        for doc in documents:
            if doc.metadata is None:
                doc.metadata = {}
            doc.metadata["doc_id"] = doc_id

        self.vectorstore.add_documents(documents)

    def similarity_search(self, query: str, k: int = 4) -> list[Document]:
        """Semantic similarity search."""
        return self.vectorstore.similarity_search(query, k=k)

    def similarity_search_with_score(self, query: str, k: int = 4) -> list[tuple[Document, float]]:
        """Semantic similarity search with relevance scores."""
        return self.vectorstore.similarity_search_with_score(query, k=k)

    def delete_by_document_id(self, doc_id: str):
        """Delete all chunks belonging to a document."""
        collection = self.client.get_collection("knowledge_base")
        try:
            # Fetch matching chunk IDs
            result = collection.get(where={"doc_id": doc_id})
            if result and result["ids"]:
                collection.delete(ids=result["ids"])
            else:
                # Fallback: try where filter directly
                collection.delete(where={"doc_id": doc_id})
        except Exception:
            # Last resort: delete all and re-index will be needed
            collection.delete(where={"doc_id": doc_id})

    def get_chunks_by_document_id(self, doc_id: str) -> list[dict]:
        """Get all chunks for a document."""
        collection = self.client.get_collection("knowledge_base")
        result = collection.get(where={"doc_id": doc_id})
        chunks = []
        for i, (content, metadata) in enumerate(zip(result["documents"], result["metadatas"])):
            chunks.append({
                "chunk_index": i,
                "content": content,
                "metadata": metadata,
            })
        return chunks

    def get_all_documents(self) -> list[Document]:
        """Get all documents in the vector store."""
        collection = self.client.get_collection("knowledge_base")
        result = collection.get()
        docs = []
        for content, metadata in zip(result["documents"], result["metadatas"]):
            docs.append(Document(page_content=content, metadata=metadata))
        return docs

    def get_collection_count(self) -> int:
        """Get the number of documents in the collection."""
        collection = self.client.get_collection("knowledge_base")
        return collection.count()