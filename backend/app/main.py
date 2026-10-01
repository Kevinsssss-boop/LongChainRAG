from fastapi import FastAPI
from fastapi.responses import JSONResponse
import secrets
from app.api import auth, session, chat, knowledge
from app.middleware.cors import setup_cors
from app.middleware.rate_limit import rate_limit_middleware
from app.db.database import engine, Base
from app.config import settings
from app.models import User
from app.core.security import hash_password


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Setup CORS
    setup_cors(app)

    # Setup rate limiting
    app.middleware("http")(rate_limit_middleware)

    # Register routers
    app.include_router(auth.router)
    app.include_router(session.router)
    app.include_router(chat.router)
    app.include_router(knowledge.router)
    # 这里原本还注册了一个 /api/debug 路由，本次删除，原因有二：
    #   1. debug.py 里硬编码了一把真实的 DashScope API Key（已随公开仓库泄露，
    #      需到阿里云控制台吊销）。密钥不该出现在源码里，更不该进 git 历史。
    #   2. 那个 /api/debug/test-llm 接口没有任何鉴权，等于一个公开的免费 LLM 代理：
    #      凭它就能拿别人的额度刷任意 prompt。
    # 它提供的 /health2 与下面正式的 /api/health 重复，没有保留价值。

    @app.get("/api/health")
    def health_check():
        return {"status": "ok", "version": settings.APP_VERSION}

    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        return JSONResponse(
            status_code=500,
            content={"detail": f"服务器内部错误: {str(exc)}"},
        )

    return app


def init_db():
    """Initialize database tables and seed admin user."""
    Base.metadata.create_all(bind=engine)

    from sqlalchemy.orm import Session
    from app.db.database import SessionLocal

    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == settings.ADMIN_USERNAME).first()
        if not admin:
            # 密码不再有默认值。此前默认是 "123456"，启动时自动建号 ——
            # 任何人克隆后部署都会得到一个口令公开的管理员，而 start.bat
            # 还把这个口令印在启动横幅上。
            # 现在：没配就随机生成一个，只在创建这一次打印出来。
            password = settings.ADMIN_PASSWORD.strip()
            generated = not password
            if generated:
                password = secrets.token_urlsafe(12)

            admin = User(
                username=settings.ADMIN_USERNAME,
                hashed_password=hash_password(password),
                is_admin=True,
            )
            db.add(admin)
            db.commit()

            if generated:
                line = "=" * 62
                print(f"\n{line}")
                print(f"  已创建管理员账号：{settings.ADMIN_USERNAME}")
                print(f"  初始密码（只显示这一次，请立即保存）：{password}")
                print(f"  想指定固定密码，就在 backend/.env 里配置 ADMIN_PASSWORD")
                print(f"{line}\n")
            else:
                print(f"Admin user created: {settings.ADMIN_USERNAME}（密码取自 ADMIN_PASSWORD）")
    finally:
        db.close()


app = create_app()

# Initialize database on startup
@app.on_event("startup")
def on_startup():
    init_db()
    print(f"{settings.APP_NAME} v{settings.APP_VERSION} started")
    print(f"API docs: http://localhost:8000/docs")