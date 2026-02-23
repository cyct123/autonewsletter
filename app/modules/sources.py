from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.source import list_sources as repo_list_sources
from app.config import settings
from typing import List


async def list_sources(db: AsyncSession) -> List[dict]:
    """Get active sources from DB or fallback to RSS_FEEDS env var"""
    sources = await repo_list_sources(db)

    if sources:
        return [
            {
                "id": str(source.id),
                "name": source.name,
                "url": source.url,
                "type": source.type,
                "active": source.active,
                "max_items_per_run": source.max_items_per_run
            }
            for source in sources
        ]

    # Fallback to RSS_FEEDS env var
    if settings.rss_feeds:
        feeds = [f.strip() for f in settings.rss_feeds.split(",") if f.strip()]
        return [
            {
                "id": None,
                "name": f"RSS Feed {i+1}",
                "url": url,
                "type": "rss",
                "active": True,
                "max_items_per_run": 5
            }
            for i, url in enumerate(feeds)
        ]

    return []
