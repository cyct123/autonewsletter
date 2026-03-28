# app/repositories/system_config.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.system_config import SystemConfig
from app.config import settings


async def get_system_config(db: AsyncSession) -> SystemConfig:
    """Get system_config row. Falls back to get_or_create if row missing (defensive)."""
    result = await db.execute(select(SystemConfig).where(SystemConfig.id == 1))
    config = result.scalar_one_or_none()
    if config is None:
        return await get_or_create_system_config(db)
    return config


async def get_or_create_system_config(db: AsyncSession) -> SystemConfig:
    """Called at startup — guarantees the id=1 row exists and returns it."""
    result = await db.execute(select(SystemConfig).where(SystemConfig.id == 1))
    config = result.scalar_one_or_none()
    if config is None:
        config = SystemConfig(
            id=1,
            weekly_cron=settings.weekly_cron,
            ai_model="deepseek",
            default_max_items_per_run=5,
            force_recent=settings.force_recent,
        )
        db.add(config)
        await db.commit()
        await db.refresh(config)
    return config
