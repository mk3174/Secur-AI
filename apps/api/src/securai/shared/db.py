"""Async SQLAlchemy engine/session management and declarative base.

Works with SQLite (dev/tests) and PostgreSQL (prod) via the async drivers
declared in the database URL.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class Database:
    def __init__(self, url: str, *, echo: bool = False) -> None:
        connect_args = {}
        if url.startswith("sqlite"):
            connect_args = {"check_same_thread": False}
        self._engine: AsyncEngine = create_async_engine(
            url, echo=echo, future=True, connect_args=connect_args
        )
        self._sessionmaker = async_sessionmaker(
            self._engine, expire_on_commit=False, class_=AsyncSession
        )

    @property
    def engine(self) -> AsyncEngine:
        return self._engine

    async def create_all(self) -> None:
        # Import models so they register on Base.metadata before create_all.
        from securai.shared import models  # noqa: F401

        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def dispose(self) -> None:
        await self._engine.dispose()

    async def session(self) -> AsyncIterator[AsyncSession]:
        async with self._sessionmaker() as session:
            yield session
