"""
SQLAlchemy async engine and session factory.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from config.settings import get_settings

_settings = get_settings()

engine = create_async_engine(
    _settings.database_url,
    echo    = _settings.api_debug,
    connect_args={"check_same_thread": False},   # SQLite only
)

AsyncSessionLocal = async_sessionmaker(
    bind           = engine,
    class_         = AsyncSession,
    expire_on_commit=False,
    autoflush      = False,
)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


async def init_db() -> None:
    """Create all tables (idempotent)."""
    from persistence import models  # noqa: F401 – triggers model registration
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    """Async context manager for a DB session with automatic rollback on error."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
