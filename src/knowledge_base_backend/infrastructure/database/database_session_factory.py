from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from src.knowledge_base_backend.configuration.application_settings import settings

engine = create_async_engine(
    settings.database_connection_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_timeout=settings.database_connection_timeout_seconds,
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)
