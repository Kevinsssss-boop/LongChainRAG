from fastapi import FastAPI
from fastapi.responses import JSONResponse
from app.api import auth, session, chat, knowledge, debug
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
    app.include_router(debug.router)  # Debug endpoint

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
            admin = User(
                username=settings.ADMIN_USERNAME,
                hashed_password=hash_password(settings.ADMIN_PASSWORD),
                is_admin=True,
            )
            db.add(admin)
            db.commit()
            print(f"Admin user created: {settings.ADMIN_USERNAME}")
    finally:
        db.close()


app = create_app()

# Initialize database on startup
@app.on_event("startup")
def on_startup():
    init_db()
    print(f"{settings.APP_NAME} v{settings.APP_VERSION} started")
    print(f"API docs: http://localhost:8000/docs")