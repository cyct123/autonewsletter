# tests/test_system_config_repo.py
import pytest
import pytest_asyncio
from app.repositories.system_config import get_system_config, get_or_create_system_config

pytestmark = pytest.mark.asyncio


async def test_get_or_create_creates_row(db):
    # Patch settings so the test doesn't depend on the real .env value
    from unittest.mock import patch
    with patch("app.repositories.system_config.settings") as mock_settings:
        mock_settings.weekly_cron = "0 9 * * 3"
        mock_settings.force_recent = False
        config = await get_or_create_system_config(db)
    assert config.id == 1
    assert config.weekly_cron == "0 9 * * 3"
    assert config.ai_model == "deepseek"
    assert config.default_max_items_per_run == 5
    assert config.force_recent is False


async def test_get_or_create_idempotent(db):
    first = await get_or_create_system_config(db)
    second = await get_or_create_system_config(db)
    assert first.id == second.id


async def test_get_system_config_after_create(db):
    await get_or_create_system_config(db)
    config = await get_system_config(db)
    assert config.id == 1


async def test_get_system_config_fallback_creates(db):
    # get_system_config with no existing row should auto-create
    config = await get_system_config(db)
    assert config.id == 1
