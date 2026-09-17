from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings
import os

# Ensure data directory exists
data_path = settings.DATABASE_URL.replace("sqlite:///", "")
if not os.path.isabs(data_path):
    data_path = os.path.join(os.getcwd(), data_path)
os.makedirs(os.path.dirname(data_path), exist_ok=True)

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    echo=settings.DEBUG,
    pool_size=60,           # 60 base connections for concurrent users
    max_overflow=40,        # +40 under peak = 100 total (matches max test users)
    pool_pre_ping=True,     # Verify connections are alive before use
    pool_recycle=300,       # Recycle connections after 5 minutes
)

# Enable SQLite WAL mode for better concurrent read/write performance
if "sqlite" in settings.DATABASE_URL:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency that provides a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()