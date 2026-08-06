import json
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models import User, ChatSession, Message
from app.schemas import ChatRequest, ChatFeedback
from app.core.dependencies import get_current_user
from app.services.chat_service import ChatService

router = APIRouter(prefix="/api/chat", tags=["问答"])


@router.post("/{session_id}")
async def chat(
    session_id: str,
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Send a message and get streaming response."""
    # Verify session ownership
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    if session.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问此会话")

    chat_service = ChatService(db)

    async def generate():
        full_response = ""
        citations = []

        async for chunk in chat_service.generate_stream(session_id, request.message):
            chunk_type = chunk.get("type")

            if chunk_type == "token":
                full_response += chunk["content"]
                yield f"data: {json.dumps({'type': 'token', 'content': chunk['content']}, ensure_ascii=False)}\n\n"

            elif chunk_type == "citations":
                citations = chunk["data"]
                yield f"data: {json.dumps({'type': 'citations', 'data': citations}, ensure_ascii=False)}\n\n"

            elif chunk_type == "error":
                yield f"data: {json.dumps({'type': 'error', 'content': chunk['content']}, ensure_ascii=False)}\n\n"

        yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{session_id}/feedback")
def send_feedback(
    session_id: str,
    feedback: ChatFeedback,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Record feedback for a message."""
    message = db.query(Message).filter(Message.id == feedback.message_id).first()
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="消息不存在")

    # Store feedback in metadata (simple approach)
    if message.citations is None:
        message.citations = {}
    message.citations["feedback"] = feedback.rating
    db.commit()

    return {"message": "反馈已记录"}