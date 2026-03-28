# app/modules/sources.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.repositories.source import list_sources as repo_list_sources, create_source
from app.models.source import Source
from app.config import settings
from typing import List


async def list_sources(db: AsyncSession) -> List[dict]:
    """Get active sources from DB. Returns empty list if no sources configured.
    RSS_FEEDS env var is only used at startup for initial import (see init_sources_from_env).
    """
    sources = await repo_list_sources(db)
    return [
        {
            "id": str(source.id),
            "name": source.name,
            "url": source.url,
            "type": source.type,
            "active": source.active,
            "max_items_per_run": source.max_items_per_run,
        }
        for source in sources
    ]


async def init_sources_from_env(db: AsyncSession) -> None:
    """One-time import: populate sources table from RSS_FEEDS env var if table is empty.
    Called once at application startup before scheduler starts.
    """
    if not settings.rss_feeds:
        return
    count = await db.scalar(select(func.count()).select_from(Source))
    if count > 0:
        return
    for url in settings.rss_feeds.split(","):
        url = url.strip()
        if url:
            await create_source(db, name=url, url=url)
