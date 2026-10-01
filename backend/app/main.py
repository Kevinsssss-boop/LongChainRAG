from fastapi import FastAPI
from fastapi.responses import JSONResponse
import secrets
from pathlib import Path

from alembic import command
from alembic.config import Config

from app.api import auth, session, chat, knowledge
from app.middleware.cors import setup_cors
from app.middleware.rate_limit import rate_limit_middleware
from app.db.database import SessionLocal
from app.config import settings
from app.models import User
from app.core.security import hash_password

# backend/ 目录，用来定位 alembic.ini 与 alembic/（main.py 在 backend/app/ 下）
BACKEND_DIR = Path(__file__).resolve().parents[1]


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # 注册顺序 = 嵌套顺序，**后注册的在更外层**。
    # 限流必须先注册，这样 CORSMiddleware 才是最外层：限流直接返回的 429
    # 才会带上 Access-Control-Allow-Origin。反过来的话浏览器只会报
    # 「网络错误」，前端既看不到 429 也看不到那句提示文案。
    app.middleware("http")(rate_limit_middleware)
    setup_cors(app)

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


def run_migrations() -> None:
    """把数据库结构升到最新（alembic upgrade head）。

    用 alembic 而不是 Base.metadata.create_all()，原因是 create_all 只建
    「缺失的表」，对**已存在的表不加列**：给 Message 加一个字段后，老库不会
    有任何变化，接着所有查询都会报 "no such column: messages.feedback"。
    迁移则是就地升级，不用删库重来。
    """
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    # alembic.ini 里写的是相对路径 alembic，这里换成绝对路径，
    # 这样不管从哪个目录启动 uvicorn 都能找到迁移脚本。
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
    command.upgrade(cfg, "head")


def init_db():
    """Initialize database tables and seed admin user."""
    run_migrations()

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