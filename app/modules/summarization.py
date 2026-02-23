from app.services.ai import summarize, translate_title


async def summarize_transcript(text: str) -> dict:
    """Generate summary from transcript"""
    return await summarize(text)


async def translate_title_to_chinese(title: str) -> str:
    """Translate title to Chinese if needed"""
    return await translate_title(title)
