from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.infrastructure.config.settings import settings

def get_connect_args() -> dict:
    """Neon exige TLS: con DB_SSL=true se negocia SSL en asyncpg."""
    return {"ssl": True} if settings.DB_SSL else {}


engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True, connect_args=get_connect_args())
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
