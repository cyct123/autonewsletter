import httpx
from app.config import settings
from app.utils.logger import logger


async def transcribe(url: str) -> dict:
    """Transcribe audio/video from URL using self-hosted Whisper HTTP endpoint"""
    if not settings.whisper_url:
        logger.info("transcription_skipped", url=url, reason="whisper_url_not_configured")
        return {"text": "", "success": False}
    try:
        async with httpx.AsyncClient(timeout=settings.whisper_timeout) as client:
            audio_resp = await client.get(url)
            audio_resp.raise_for_status()
            files = {"file": ("audio", audio_resp.content,
                     audio_resp.headers.get("content-type", "audio/mpeg"))}
            whisper_resp = await client.post(settings.whisper_url, files=files)
            whisper_resp.raise_for_status()
            text = whisper_resp.json().get("text", "")
            logger.info("transcription_success", url=url, text_length=len(text))
            return {"text": text, "success": bool(text)}
    except Exception as e:
        logger.error("transcription_failed", url=url, error=str(e))
        return {"text": "", "success": False}
