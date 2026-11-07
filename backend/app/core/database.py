"""
CloudSage Database Session & Base Engine.
Provides asynchronous and synchronous SQLAlchemy 2.0 sessions and declarative base class.
"""

from typing import AsyncGenerator, Generator, Optional
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from backend.app.core.config import settings


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy ORM models."""
    pass


# Check for greenlet / asyncio support
try:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    HAS_ASYNC = True
except ImportError:
    HAS_ASYNC = False
    AsyncSession = None
    async_sessionmaker = None
    create_async_engine = None


_sync_engine: Optional[Engine] = None
_sync_session_factory = None


def get_sync_engine() -> Engine:
    """Lazily initialize synchronous engine."""
    global _sync_engine, _sync_session_factory
    if _sync_engine is None:
        url = settings.get_sync_database_url()
        _sync_engine = create_engine(
            url,
            echo=False,
            future=True,
            pool_pre_ping=True
        )
        _sync_session_factory = sessionmaker(
            bind=_sync_engine,
            autocommit=False,
            autoflush=False
        )
    return _sync_engine


def get_sync_db() -> Generator:
    """Dependency for yielding a synchronous database session."""
    get_sync_engine()
    session = _sync_session_factory()
    try:
        yield session
    finally:
        session.close()


async def get_db() -> AsyncGenerator:
    """Dependency for yielding an async database session."""
    if not HAS_ASYNC:
        raise RuntimeError("SQLAlchemy asyncio extension requires 'greenlet' package.")
    # Implementation for async session
    async_url = settings.get_async_database_url()
    if async_url.startswith("sqlite://"):
        async_url = async_url.replace("sqlite://", "sqlite+aiosqlite://")
    
    engine = create_async_engine(
        async_url,
        echo=False,
        future=True,
        pool_pre_ping=True
    )
    factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False
    )
    async with factory() as session:
        try:
            yield session
        finally:
            await session.close()
