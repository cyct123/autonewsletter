import httpx
from app.config import settings
from app.utils.logger import logger


async def send_lark(content: str, title: str = "每周Newsletter") -> dict:
    """Send notification via Lark (Feishu) webhook"""
    # Lark webhook URL should be configured via environment variable
    # For now, return not configured
    logger.warning("lark_not_configured")
    return {"ok": False, "error": "Lark webhook not configured"}
