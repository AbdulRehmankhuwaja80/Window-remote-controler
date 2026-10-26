from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from backend.app.config import settings

# Engine configuration
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args=connect_args,
)

async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Automatic column migration for existing SQLite database
        if settings.DATABASE_URL.startswith("sqlite"):
            def migrate_sqlite_columns(connection):
                cursor = connection.connection.cursor()
                cursor.execute("PRAGMA table_info(users)")
                columns = [col[1] for col in cursor.fetchall()]
                if "is_verified" not in columns:
                    cursor.execute("ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT 0")
                if "verification_code" not in columns:
                    cursor.execute("ALTER TABLE users ADD COLUMN verification_code VARCHAR(32)")
                if "verification_expires_at" not in columns:
                    cursor.execute("ALTER TABLE users ADD COLUMN verification_expires_at DATETIME")
                if "reset_token" not in columns:
                    cursor.execute("ALTER TABLE users ADD COLUMN reset_token VARCHAR(64)")
                if "reset_expires_at" not in columns:
                    cursor.execute("ALTER TABLE users ADD COLUMN reset_expires_at DATETIME")
            await conn.run_sync(migrate_sqlite_columns)
