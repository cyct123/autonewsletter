import httpx
from app.utils.logger import logger


async def transcribe(url: str) -> dict:
    """Transcribe audio/video from URL using Whisper service"""
    try:
        # For now, return empty transcript as Whisper service needs separate setup
        # This maintains compatibility with the existing Python Whisper service
        logger.info("transcription_skipped", url=url, reason="whisper_service_not_configured")
        return {"text": "", "success": False}
    except Exception as e:
        logger.error("transcription_failed", url=url, error=str(e))
        return {"text": "", "success": False}
