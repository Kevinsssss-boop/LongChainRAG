import os
import uuid
from sqlalchemy.orm import Session
from app.models import KnowledgeDocument
from app.config import settings
from app.rag.loader import DocumentLoader
from app.rag.splitter import TextSplitter
from app.rag.embedder import EmbeddingService
from app.rag.vectorstore import VectorStoreService
from app.services.cache_service import get_semantic_cache

# 允许上传的类型。file_type 同时被用作落盘文件的扩展名，所以它是白名单 ——
# 任何不在这个集合里的值都不该拼进路径。
_ALLOWED_FILE_TYPES = {"pdf", "txt", "csv", "md"}


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

    @staticmethod
    def build_storage_path(file_type: str) -> str:
        """给上传的文件算一个安全的落盘路径。

        **绝不能拿客户端传来的 filename 去拼路径。** 原来的写法是
        `os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{filename}")` —— 看着有
        一个 uuid 前缀就安全了，其实不然：Windows 在打开文件前会先做一次
        **纯词法**的路径折叠，`<uuid>_..` 这个路径段会被紧跟其后的 `..`
        直接吃掉，前缀等于没加。实测 filename = "../../../evil.txt" 会真的
        写到 UPLOAD_DIR 之外（回归用例见 tests/test_kb_service.py）。

        现在落盘名完全由服务端生成：uuid 十六进制 + 已白名单校验的类型。
        客户端文件名只进数据库、只用于界面展示。
        """
        if file_type not in _ALLOWED_FILE_TYPES:
            raise ValueError(f"不支持的文件类型: {file_type!r}")
        return os.path.join(settings.UPLOAD_DIR, f"{uuid.uuid4().hex}.{file_type}")

    async def process_document(
        self, filename: str, content: bytes, file_type: str, uploaded_by: str
    ) -> KnowledgeDocument:
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        file_path = self.build_storage_path(file_type)
        with open(file_path, "wb") as f:
            f.write(content)

        # Create DB record
        doc = KnowledgeDocument(
            filename=filename,
            file_type=file_type,
            file_size=len(content),
            status="processing",
            uploaded_by=uploaded_by,
            stored_path=file_path,
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

        except Exception:
            doc.status = "failed"
            self.db.commit()
            raise

        # 知识库变了，语义缓存里那些引用旧文档的回答立刻作废。
        # 不做这一步，管理员删掉文档后，缓存还会把已经不存在的文件当来源返回。
        get_semantic_cache().invalidate()
        return doc

    async def delete_document(self, doc_id: str):
        doc = self.db.query(KnowledgeDocument).filter(KnowledgeDocument.id == doc_id).first()
        if not doc:
            return

        # Delete from ChromaDB
        self.vectorstore.delete_by_document_id(doc_id)

        # Delete the file from disk too. 原来只删数据库记录，文件永远留在
        # data/uploads/ 里，谁也找不到、谁也不会清理。
        stored_path = doc.stored_path
        if stored_path and os.path.isfile(stored_path):
            try:
                os.remove(stored_path)
            except OSError:
                # 文件删不掉不该让整个删除操作失败 —— 数据库记录才是真源，
                # 留一个孤儿文件比留一条指向已删文档的记录好。
                pass

        # Delete from DB
        self.db.delete(doc)
        self.db.commit()

        get_semantic_cache().invalidate()

    def get_document_chunks(self, doc_id: str) -> list:
        return self.vectorstore.get_chunks_by_document_id(doc_id)
