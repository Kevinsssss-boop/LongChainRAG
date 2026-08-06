from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "RAG 知识库问答系统"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    SECRET_KEY: str = "change-me-to-a-random-secret-key-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # Database
    DATABASE_URL: str = "sqlite:///./data/app.db"

    # LLM
    LLM_API_KEY: str = "sk-your-api-key"
    LLM_BASE_URL: Optional[str] = None  # For OpenAI-compatible providers
    LLM_MODEL_NAME: str = "gpt-4o"
    EMBEDDING_MODEL_NAME: str = "text-embedding-3-small"

    # ChromaDB
    CHROMA_PERSIST_DIR: str = "./data/chroma"

    # RAG
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    RETRIEVAL_TOP_K: int = 10
    FINAL_TOP_K: int = 6

    # Cache
    CACHE_SIMILARITY_THRESHOLD: float = 0.92
    CACHE_MAX_SIZE: int = 1000

    # Rate Limit
    RATE_LIMIT_PER_MINUTE: int = 30

    # Admin
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "123456"

    # Upload
    UPLOAD_DIR: str = "./data/uploads"
    MAX_UPLOAD_SIZE_MB: int = 50

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()