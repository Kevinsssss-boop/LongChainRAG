"""共用测试夹具。

要点：每个测试用独立的内存 SQLite，绝不碰 backend/data/app.db。
`TestClient(app)` **不**用 with 语句 —— 用了会触发 lifespan，进而跑
init_db() 里的 alembic upgrade，那会去改真实的开发库。
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token, hash_password
from app.db.database import Base, get_db
from app.main import app
from app.middleware.rate_limit import rate_limiter
from app.models import User


@pytest.fixture
def db_engine():
    # StaticPool + sqlite:// 让整个测试共用同一个内存连接，
    # 否则每个连接都是一个全新的空库。
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db(db_engine):
    session = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)()
    yield session
    session.close()


@pytest.fixture
def admin_user(db):
    user = User(
        username="test_admin",
        hashed_password=hash_password("pw-123456"),
        is_admin=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def other_user(db):
    user = User(
        username="test_other",
        hashed_password=hash_password("pw-123456"),
        is_admin=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def auth_headers(admin_user):
    return {"Authorization": f"Bearer {create_access_token({'sub': admin_user.id})}"}


@pytest.fixture
def other_auth_headers(other_user):
    return {"Authorization": f"Bearer {create_access_token({'sub': other_user.id})}"}


@pytest.fixture
def client(db):
    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    # 不加 with：避免触发 lifespan（那会跑 alembic 迁移改到真实开发库）
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """限流器是模块级单例，会在测试之间串味（上一个测试打满配额，
    下一个测试直接吃 429）。每个测试前清空。"""
    rate_limiter.buckets.clear()
    yield
    rate_limiter.buckets.clear()
