from sqlalchemy.ext.asyncio import AsyncSession
from app.models.send_log import SendLog


async def record_send(
    db: AsyncSession,
    subscriber_id: str,
    channel_type: str,
    success: bool,
    error_message: str | None = None,
) -> None:
    db.add(SendLog(
        subscriber_id=subscriber_id,
        channel_type=channel_type,
        success=success,
        error_message=error_message,
    ))
    await db.commit()
