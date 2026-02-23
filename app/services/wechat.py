import httpx
from app.config import settings
from app.utils.logger import logger


async def send_wechat(content: str, title: str = "每周Newsletter") -> dict:
    """Send notification via WeChat webhook"""
    webhooks = [w.strip() for w in settings.wechat_webhook_urls.split(",") if w.strip()]

    if not webhooks:
        logger.warning("wechat_no_webhooks")
        return {"ok": False, "error": "No WeChat webhooks configured"}

    results = []
    for webhook in webhooks:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    webhook,
                    json={
                        "msgtype": "markdown",
                        "markdown": {
                            "content": f"# {title}\n\n{content}"
                        }
                    }
                )
                response.raise_for_status()
                results.append({"ok": True})
                logger.info("wechat_sent", webhook=webhook[:30])
        except Exception as e:
            logger.error("wechat_failed", webhook=webhook[:30], error=str(e))
            results.append({"ok": False, "error": str(e)})

    return {"ok": all(r["ok"] for r in results), "results": results}
