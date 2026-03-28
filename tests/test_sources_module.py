# tests/test_sources_module.py
import pytest
from unittest.mock import patch, AsyncMock
from app.modules.sources import list_sources, init_sources_from_env

pytestmark = pytest.mark.asyncio


async def test_list_sources_returns_db_rows(db):
    """list_sources returns DB rows; no fallback to .env"""
    from app.repositories.source import create_source
    await create_source(db, name="Test Feed", url="https://example.com/feed.xml")

    sources = await list_sources(db)
    assert len(sources) == 1
    assert sources[0]["url"] == "https://example.com/feed.xml"


async def test_list_sources_empty_returns_empty_not_env(db):
    """When DB is empty, list_sources returns [] — never falls back to .env"""
    with patch("app.modules.sources.settings") as mock_settings:
        mock_settings.rss_feeds = "https://should-not-appear.com/feed"
        sources = await list_sources(db)
    assert sources == []


async def test_init_sources_from_env_imports_when_empty(db):
    """init_sources_from_env populates DB from RSS_FEEDS when sources table is empty"""
    with patch("app.modules.sources.settings") as mock_settings:
        mock_settings.rss_feeds = "https://feed1.com/rss,https://feed2.com/rss"
        await init_sources_from_env(db)

    sources = await list_sources(db)
    assert len(sources) == 2


async def test_init_sources_from_env_noop_when_not_empty(db):
    """init_sources_from_env does nothing when DB already has sources"""
    from app.repositories.source import create_source
    await create_source(db, name="Existing", url="https://existing.com/feed")

    with patch("app.modules.sources.settings") as mock_settings:
        mock_settings.rss_feeds = "https://new-feed.com/rss"
        await init_sources_from_env(db)

    sources = await list_sources(db)
    assert len(sources) == 1  # still only 1, no new imports


async def test_init_sources_from_env_noop_when_no_env_feeds(db):
    """init_sources_from_env does nothing when RSS_FEEDS is empty"""
    with patch("app.modules.sources.settings") as mock_settings:
        mock_settings.rss_feeds = ""
        await init_sources_from_env(db)

    sources = await list_sources(db)
    assert sources == []
