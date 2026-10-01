from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models import User, KnowledgeDocument
from app.schemas import DocumentResponse, DocumentListResponse, PaginationParams
from app.core.dependencies import get_admin_user
from app.services.kb_service import KnowledgeBaseService
from app.config import settings

router = APIRouter(prefix="/api/knowledge", tags=["知识库"])

# 上传时每次从请求体读多少字节。见 upload_document 里的说明。
_UPLOAD_CHUNK_SIZE = 1024 * 1024  # 1MB


@router.get("/documents", response_model=DocumentListResponse)
def list_documents(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """List all knowledge documents (admin only)."""
    query = db.query(KnowledgeDocument).order_by(KnowledgeDocument.created_at.desc())
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return DocumentListResponse(
        total=total,
        items=[DocumentResponse.model_validate(doc) for doc in items],
    )


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Upload a document to the knowledge base (admin only)."""
    kb_service = KnowledgeBaseService(db)

    # file.filename 的类型是 str | None，缺了直接 500，这里挡掉
    if not file.filename:
        raise HTTPException(status_code=400, detail="缺少文件名")

    # Validate file type
    file_type = kb_service.get_file_type(file.filename)
    if file_type not in ("pdf", "txt", "csv", "md"):
        raise HTTPException(status_code=400, detail="不支持的文件类型，仅支持 PDF/TXT/CSV/MD")

    # Validate file size —— 边读边判，超限立刻中断。
    # 原来是 `content = await file.read()`：一口气读完整个文件才比大小。
    # 而前端 Dragger 没有做任何大小校验，所以一个 2GB 的文件会先把内存
    # 吃满，然后才回一句「超过限制」。现在内存里最多留 max_bytes + 一个分片。
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    content = bytearray()
    while chunk := await file.read(_UPLOAD_CHUNK_SIZE):
        content.extend(chunk)
        if len(content) > max_bytes:
            # 413 而不是 400：语义上是「实体太大」，而且前端只读 detail 文案，
            # 不依赖状态码。用字面量 413 是因为 Starlette 在 0.47 前后改过
            # 这个名字（REQUEST_ENTITY_TOO_LARGE → CONTENT_TOO_LARGE）。
            raise HTTPException(
                status_code=413,
                detail=f"文件大小超过限制 ({settings.MAX_UPLOAD_SIZE_MB}MB)",
            )

    # Process document
    doc = await kb_service.process_document(
        filename=file.filename,
        content=bytes(content),
        file_type=file_type,
        uploaded_by=current_user.id,
    )

    return DocumentResponse.model_validate(doc)


@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Delete a document and its vectors (admin only)."""
    kb_service = KnowledgeBaseService(db)
    await kb_service.delete_document(doc_id)
    return {"message": "文档已删除"}


@router.get("/documents/{doc_id}/chunks")
def get_document_chunks(
    doc_id: str,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Get document chunks (admin only)."""
    kb_service = KnowledgeBaseService(db)
    chunks = kb_service.get_document_chunks(doc_id)
    return {"chunks": chunks}