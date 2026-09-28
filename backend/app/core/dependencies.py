"""
Sentinel — FastAPI Dependency Providers.

Yields database sessions and other shared resources to route handlers.
"""

from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionFactory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session, ensuring it is closed after use."""
    async with AsyncSessionFactory() as session:
        try:
            yield session
        finally:
            await session.close()
