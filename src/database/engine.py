"""Motor de la base de datos."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from database.config import DatabaseConfig
from database.models import Base

engine = create_async_engine(
    DatabaseConfig.url(),
    echo=DatabaseConfig.echo(),
    pool_pre_ping=True,
)

ASYNCSESSIONLOCAL = async_sessionmaker[AsyncSession](bind=engine, expire_on_commit=False)


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    """Obtiene una sesión de la base de datos."""
    async with ASYNCSESSIONLOCAL() as session:
        yield session


async def close_engine() -> None:
    """Cierra el motor de la base de datos."""
    await engine.dispose()


async def ensure_schema() -> None:
    """Crea el esquema si no existe (útil en dev y como fallback)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
