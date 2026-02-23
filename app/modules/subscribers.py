from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.subscriber import Subscriber
from typing import List


async def list_active(db: AsyncSession) -> List[dict]:
    """Get all active subscribers"""
    result = await db.execute(
        select(Subscriber).where(Subscriber.active == True)
    )
    subscribers = result.scalars().all()

    return [
        {
            "id": str(sub.id),
            "identifier": sub.identifier,
            "channelType": sub.channel_type,
            "preferences": sub.preferences or {}
        }
        for sub in subscribers
    ]
