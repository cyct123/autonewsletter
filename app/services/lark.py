import httpx
from app.config import settings
from app.utils.logger import logger


async def send_lark(content: str, title: str = "每周Newsletter") -> dict:
    """Send notification via Lark (Feishu) webhook"""
    url = settings.lark_webhook_url
    if not url:
        logger.warning("lark_not_configured")
        return {"ok": False, "error": "Lark webhook URL not configured"}
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json={
                "msg_type": "text",
                "content": {"text": f"{title}\n\n{content}"}
            })
            resp.raise_for_status()
            logger.info("lark_sent")
            return {"ok": True}
    except Exception as e:
        logger.error("lark_failed", error=str(e))
        return {"ok": False, "error": str(e)}
