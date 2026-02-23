from app.services.pushplus import send_pushplus
from app.services.wechat import send_wechat
from app.services.email import send_email
from app.services.lark import send_lark
from app.utils.logger import logger


async def distribute(newsletter: dict, subscriber: dict) -> dict:
    """Distribute newsletter to subscriber via their channel"""
    channel = subscriber["channel"]
    title = newsletter["title"]
    content = newsletter["html"]
    address = subscriber.get("address", "")

    try:
        if channel == "pushplus":
            return await send_pushplus(content, title)
        elif channel == "wechat":
            return await send_wechat(content, title)
        elif channel == "email":
            return await send_email(address, content, title)
        elif channel == "lark":
            return await send_lark(content, title)
        else:
            logger.warning("unsupported_channel", channel=channel)
            return {"ok": False, "error": f"Unsupported channel: {channel}"}
    except Exception as e:
        logger.error("distribution_failed", channel=channel, error=str(e))
        return {"ok": False, "error": str(e)}
