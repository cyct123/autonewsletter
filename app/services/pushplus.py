import httpx
from app.config import settings
from app.utils.logger import logger


async def send_pushplus(content: str, title: str = "每周Newsletter") -> dict:
    """Send notification via PushPlus"""
    tokens = [t.strip() for t in settings.pushplus_tokens.split(",") if t.strip()]

    if not tokens:
        logger.warning("pushplus_no_tokens")
        return {"ok": False, "error": "No PushPlus tokens configured"}

    results = []
    for token in tokens:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "http://www.pushplus.plus/send",
                    json={
                        "token": token,
                        "title": title,
                        "content": content,
                        "template": "html"
                    }
                )
                response.raise_for_status()
                results.append({"ok": True, "token": token[:8]})
                logger.info("pushplus_sent", token=token[:8])
        except Exception as e:
            logger.error("pushplus_failed", token=token[:8], error=str(e))
            results.append({"ok": False, "error": str(e)})

    return {"ok": all(r["ok"] for r in results), "results": results}
