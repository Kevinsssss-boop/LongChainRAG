import os
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from app.models import KnowledgeDocument
from app.config import settings
from app.rag.loader import DocumentLoader
from app.rag.splitter import TextSplitter
from app.rag.embedder import EmbeddingService
from app.rag.vectorstore import VectorStoreService


class KnowledgeBaseService:
    def __init__(self, db: Session):
        self.db = db
        self.loader = DocumentLoader()
        self.splitter = TextSplitter()
        self.embedder = EmbeddingService()
        self.vectorstore = VectorStoreService()

    def get_file_type(self, filename: str) -> str:
        ext = os.path.splitext(filename)[1].lower()
        mapping = {".pdf": "pdf", ".txt": "txt", ".csv": "csv", ".md": "md"}
        return mapping.get(ext, "unknown")

    async def process_document(
        self, filename: str, content: bytes, file_type: str, uploaded_by: str
    ) -> KnowledgeDocument:
        # Save file to disk
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        file_path = os.path.join(settings.UPLOAD_DIR, f"{uuid.uuid4()}_{filename}")
        with open(file_path, "wb") as f:
            f.write(content)

        # Create DB record
        doc = KnowledgeDocument(
            filename=filename,
            file_type=file_type,
            file_size=len(content),
            status="processing",
            uploaded_by=uploaded_by,
        )
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)

        try:
            # Load document
            docs = self.loader.load(file_path, file_type)

            # Split into chunks
            chunks = self.splitter.split(docs)

            # Generate embeddings and store in ChromaDB
            self.embedder.embed_and_store(chunks, doc_id=doc.id)

            # Update document status
            doc.chunk_count = len(chunks)
            doc.status = "completed"
            self.db.commit()
            self.db.refresh(doc)

        except Exception as e:
            doc.status = "failed"
            self.db.commit()
            raise e

        return doc

    async def delete_document(self, doc_id: str):
        doc = self.db.query(KnowledgeDocument).filter(KnowledgeDocument.id == doc_id).first()
        if not doc:
            return

        # Delete from ChromaDB
        self.vectorstore.delete_by_document_id(doc_id)

        # Delete from DB
        self.db.delete(doc)
        self.db.commit()

    def get_document_chunks(self, doc_id: str) -> list:
        return self.vectorstore.get_chunks_by_document_id(doc_id)