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
    """Record feedback for a message.

    原来这个接口同时有三个问题，一次都没跑通过：

    1. **写坏数据。** 评价被塞进 message.citations["feedback"]，但 citations
       是 JSON **数组**（见 models 与 chat_service 里的 citations[0]["source"]）。
       对数组取字符串下标直接 TypeError —— 凡是带引用的消息，评价必定 500；
       而 citations 为 None 时它先把字段赋成 {}，等于把这条消息的引用整个
       覆盖掉，那条消息从此渲染不出来。现在存进独立的 messages.feedback 列。
    2. **越权。** 原来只按 message_id 查，不校验消息属不属于当前用户 ——
       拿任意 ID 就能给别人的对话打分。
    3. **不校验会话归属。** URL 里的 session_id 与消息实际所属的会话可以
       对不上，现在一并校验。
    """
    message = (
        db.query(Message)
        .join(ChatSession, Message.session_id == ChatSession.id)
        .filter(
            Message.id == feedback.message_id,
            Message.session_id == session_id,
            ChatSession.user_id == current_user.id,
        )
        .first()
    )
    if message is None:
        # 故意不区分「消息不存在」和「消息不属于你」：区分了就等于提供了
        # 一个探测别人消息 ID 是否存在的接口。
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="消息不存在")

    if message.role != "assistant":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="只能对助手回复评价")

    message.feedback = feedback.rating
    db.commit()

    return {"message": "反馈已记录", "message_id": message.id, "rating": message.feedback}