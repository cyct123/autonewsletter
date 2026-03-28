# app/modules/summarization.py
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.ai import summarize, translate_title


async def summarize_transcript(text: str, db: AsyncSession) -> dict:
    """Generate summary from transcript"""
    return await summarize(text, db)


async def translate_title_to_chinese(title: str, db: AsyncSession) -> str:
    """Translate title to Chinese if needed"""
    return await translate_title(title, db)
