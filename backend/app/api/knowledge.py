from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models import User, KnowledgeDocument
from app.schemas import DocumentResponse, DocumentListResponse, PaginationParams
from app.core.dependencies import get_admin_user
from app.services.kb_service import KnowledgeBaseService
from app.config import settings

router = APIRouter(prefix="/api/knowledge", tags=["知识库"])


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

    # Validate file type
    file_type = kb_service.get_file_type(file.filename)
    if file_type not in ("pdf", "txt", "csv", "md"):
        raise HTTPException(status_code=400, detail="不支持的文件类型，仅支持 PDF/TXT/CSV/MD")

    # Validate file size
    content = await file.read()
    file_size = len(content)
    if file_size > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"文件大小超过限制 ({settings.MAX_UPLOAD_SIZE_MB}MB)")

    # Process document
    doc = await kb_service.process_document(
        filename=file.filename,
        content=content,
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