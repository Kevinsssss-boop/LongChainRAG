from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ── Auth ──
class UserRegister(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)
    email: Optional[str] = None


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: str
    username: str
    email: Optional[str] = None
    is_admin: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class PasswordChange(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6, max_length=100)


# ── Session ──
class SessionCreate(BaseModel):
    title: Optional[str] = "新对话"


class SessionUpdate(BaseModel):
    title: Optional[str] = None


class SessionResponse(BaseModel):
    id: str
    title: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    class Config:
        from_attributes = True


class SessionDetailResponse(BaseModel):
    id: str
    title: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    messages: list["MessageResponse"] = []

    class Config:
        from_attributes = True


# ── Message ──
class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    citations: Optional[list] = None
    token_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class Citation(BaseModel):
    content: str
    source: str
    score: float = 0.0


# ── Chat ──
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)


class ChatFeedback(BaseModel):
    message_id: str
    rating: str  # "up" or "down"


# ── Knowledge ──
class DocumentResponse(BaseModel):
    id: str
    filename: str
    file_type: str
    file_size: int
    chunk_count: int
    status: str
    uploaded_by: str
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    total: int
    items: list[DocumentResponse]


class ChunkResponse(BaseModel):
    content: str
    metadata: dict
    chunk_index: int


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)