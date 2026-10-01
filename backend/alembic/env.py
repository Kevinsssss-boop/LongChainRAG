"""Alembic 运行环境。

两个容易踩空的点，都踩过了：

1. **alembic 是独立进程，不认识 app 包。** alembic.ini 里的
   `prepend_sys_path = .` 只在从 backend/ 目录执行时成立。下面再显式把
   backend/ 插进 sys.path，从仓库根目录执行也能跑。

2. **不 import 模型 = 生成一个「删掉所有表」的迁移。**
   autogenerate 比较的是「Base.metadata 里有什么」和「数据库里有什么」。
   模型没被 import 过，metadata 就是空的，alembic 会认为所有表都是多余的，
   生成一堆 drop_table。所以下面必须显式 import 模型模块。
"""

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings  # noqa: E402
from app.db.database import Base  # noqa: E402
from app import models  # noqa: E402,F401  ← 别删：autogenerate 靠它认表

config = context.config

# 数据库地址只有一个来源：app.config.settings（它自己读 backend/.env）。
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# SQLite 的 ALTER TABLE 能力极弱：改列类型、加/删约束都得重建整张表。
# 开 batch 模式后 alembic 自动做「建新表 → 拷数据 → 原子换名」。
# 现在只有 SQLite 一个后端，但以后换 Postgres 也不会因此出问题。
RENDER_AS_BATCH = True


def run_migrations_offline() -> None:
    """离线模式：只把 SQL 打到标准输出，不连数据库。"""
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=RENDER_AS_BATCH,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线模式：连上数据库直接执行。"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=RENDER_AS_BATCH,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
