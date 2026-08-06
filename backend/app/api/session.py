from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from app.db.database import get_db
from app.models import User, ChatSession, Message
from app.schemas import SessionCreate, SessionUpdate, SessionResponse, SessionDetailResponse, MessageResponse
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/api/sessions", tags=["会话"])


@router.get("", response_model=list[SessionResponse])
def list_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all sessions for current user, ordered by last activity."""
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == current_user.id)
        .order_by(desc(ChatSession.updated_at))
        .all()
    )
    result = []
    for s in sessions:
        msg_count = db.query(func.count(Message.id)).filter(Message.session_id == s.id).scalar()
        sr = SessionResponse(
            id=s.id,
            title=s.title,
            is_active=s.is_active,
            created_at=s.created_at,
            updated_at=s.updated_at,
            message_count=msg_count or 0,
        )
        result.append(sr)
    return result


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    data: SessionCreate = SessionCreate(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new chat session."""
    session = ChatSession(user_id=current_user.id, title=data.title)
    db.add(session)
    db.commit()
    db.refresh(session)
    return SessionResponse(
        id=session.id,
        title=session.title,
        is_active=session.is_active,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=0,
    )


@router.get("/{session_id}", response_model=SessionDetailResponse)
def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get session details including messages."""
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    if session.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问此会话")

    messages = db.query(Message).filter(Message.session_id == session_id).order_by(Message.created_at).all()
    return SessionDetailResponse(
        id=session.id,
        title=session.title,
        is_active=session.is_active,
        created_at=session.created_at,
        updated_at=session.updated_at,
        messages=[MessageResponse.model_validate(m) for m in messages],
    )


@router.delete("/{session_id}")
def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a session and all its messages."""
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    if session.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权删除此会话")

    db.delete(session)
    db.commit()
    return {"message": "会话已删除"}


@router.put("/{session_id}", response_model=SessionResponse)
def update_session(
    session_id: str,
    data: SessionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update session title."""
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    if session.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权修改此会话")

    if data.title is not None:
        session.title = data.title
    db.commit()
    db.refresh(session)

    msg_count = db.query(func.count(Message.id)).filter(Message.session_id == session.id).scalar()
    return SessionResponse(
        id=session.id,
        title=session.title,
        is_active=session.is_active,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=msg_count or 0,
    )