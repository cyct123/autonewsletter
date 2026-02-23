from app.services.whisper import transcribe as whisper_transcribe


async def transcribe(url: str) -> dict:
    """Transcribe audio/video content from URL"""
    return await whisper_transcribe(url)
