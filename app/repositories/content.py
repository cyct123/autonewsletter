from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.content import Content
from typing import List
from datetime import datetime


async def exists_by_url(db: AsyncSession, url: str) -> bool:
    """Check if content exists by URL"""
    result = await db.execute(select(Content).where(Content.original_url == url))
    return result.scalar_one_or_none() is not None


async def insert_content(db: AsyncSession, content_data: dict) -> None:
    """Insert new content, skip on duplicate original_url"""
    stmt = insert(Content).values(
        source_id=content_data["source_id"],
        title=content_data["title"],
        original_url=content_data["original_url"],
        transcript=content_data.get("transcript"),
        summary=content_data.get("summary"),
        key_points=content_data.get("key_points", []),
        quality_score=content_data.get("quality_score", 0.0),
        status=content_data.get("status", "pending"),
        processed_at=datetime.utcnow()
    ).on_conflict_do_nothing(index_elements=["original_url"])
    await db.execute(stmt)
    await db.commit()


async def list_recent_contents(db: AsyncSession, limit: int = 100) -> List[Content]:
    """Get recent contents"""
    result = await db.execute(
        select(Content)
        .order_by(Content.processed_at.desc())
        .limit(limit)
    )
    return result.scalars().all()
