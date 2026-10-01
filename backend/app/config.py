import logging
import secrets
from typing import Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings

_log = logging.getLogger(__name__)

# 这些值一律视为「没有配置」。
# 它们曾经是源码里的默认值 —— 那意味着任何人克隆下来直接部署，
# JWT 签名密钥就是公开仓库里写死的那一串，等同于没有鉴权。
_INSECURE_SECRETS = {
    "",
    "change-me-to-a-random-secret-key-in-production",
    "changeme",
    "secret",
    "your-secret-key",
}


class Settings(BaseSettings):
    # App
    APP_NAME: str = "RAG 知识库问答系统"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    STRESS_TEST_MODE: bool = False  # When True, all external API calls are mocked
    # 运行环境：development / production。生产环境下缺失密钥会拒绝启动，而不是悄悄用默认值。
    APP_ENV: str = "development"
    SECRET_KEY: str = ""
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
    # 密码**不留默认值**。此前默认是 "123456"，而 init_db() 会在首次启动时
    # 用这个口令创建管理员 —— 等于给每个部署实例发了一张公开的万能钥匙，
    # start.bat 还把它印在启动横幅上。
    # 留空时改为首次创建账号时随机生成并打印一次（见 main.init_db）。
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = ""

    # Upload
    UPLOAD_DIR: str = "./data/uploads"
    MAX_UPLOAD_SIZE_MB: int = 50

    @model_validator(mode="after")
    def _resolve_secret_key(self):
        """缺密钥时：开发环境随机生成并告警，生产环境直接拒绝启动。

        绝不像以前那样静默用一个写在源码里的常量当签名密钥 ——
        那等于没有鉴权：任何人克隆了仓库就能离线伪造 token。
        """
        if self.SECRET_KEY.strip() in _INSECURE_SECRETS:
            if self.APP_ENV == "production":
                raise ValueError(
                    "生产环境（APP_ENV=production）必须显式配置 SECRET_KEY。\n"
                    "生成一个：python -c \"import secrets; print(secrets.token_urlsafe(48))\"\n"
                    "然后写进 backend/.env（注意是 backend 目录下，不是仓库根目录）。"
                )
            self.SECRET_KEY = secrets.token_urlsafe(48)
            _log.warning(
                "SECRET_KEY 未配置，已生成一次性随机密钥（仅开发环境）。"
                "进程重启后所有已签发的 token 会失效。生产环境请显式配置。"
            )
        return self

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()