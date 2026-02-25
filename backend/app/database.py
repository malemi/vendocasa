from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

# Convert sync URL to async: postgresql+psycopg -> postgresql+psycopg (psycopg3 supports async natively)
_db_url = settings.database_url
if "+psycopg://" in _db_url and "+psycopg_async://" not in _db_url:
    _db_url = _db_url.replace("+psycopg://", "+psycopg_async://")
elif "postgresql://" in _db_url and "+psycopg" not in _db_url:
    _db_url = _db_url.replace("postgresql://", "postgresql+psycopg_async://")

engine = create_async_engine(_db_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
