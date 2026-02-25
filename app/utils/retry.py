import asyncio
from app.utils.logger import logger


async def retry_async(fn, retries=3, delay=2.0):
    result = None
    for attempt in range(retries):
        result = await fn()
        if result.get("ok"):
            return result
        if attempt < retries - 1:
            logger.warning("retry_attempt", attempt=attempt + 1)
            await asyncio.sleep(delay * (2 ** attempt))
    return result
