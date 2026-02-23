from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.source import Source
from typing import List


async def list_sources(db: AsyncSession) -> List[Source]:
    """Get all sources from database"""
    result = await db.execute(select(Source))
    return result.scalars().all()


async def get_source_by_url(db: AsyncSession, url: str) -> Source | None:
    """Get source by URL"""
    result = await db.execute(select(Source).where(Source.url == url))
    return result.scalar_one_or_none()


async def create_source(db: AsyncSession, name: str, url: str, source_type: str = "rss", max_items: int = 5) -> Source:
    """Create a new source"""
    source = Source(
        name=name,
        url=url,
        type=source_type,
        max_items_per_run=max_items
    )
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return source
