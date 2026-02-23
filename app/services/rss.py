import httpx
import feedparser
from typing import List, Dict
from app.utils.logger import logger


async def fetch_rss_items(url: str, max_items: int = 5) -> List[Dict]:
    """Fetch RSS feed items"""
    try:
        logger.info("rss_fetch_starting", url=url, max_items=max_items)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()

            logger.info("rss_response_received", url=url, status_code=response.status_code, content_length=len(response.text))

            feed = feedparser.parse(response.text)

            logger.info("rss_parsed", url=url, feed_title=feed.feed.get("title", ""), entry_count=len(feed.entries))

            items = []
            for idx, entry in enumerate(feed.entries[:max_items], 1):
                snippet = entry.get("summary", "")[:500]
                item = {
                    "title": entry.get("title", ""),
                    "url": entry.get("link", ""),
                    "snippet": snippet,
                    "published": entry.get("published", "")
                }
                items.append(item)
                logger.info("rss_item_extracted", item_num=idx, title=item["title"][:100], url=item["url"], snippet_length=len(snippet), snippet_preview=snippet[:100])

            logger.info("rss_fetched", url=url, count=len(items))
            return items

    except Exception as e:
        logger.error("rss_fetch_failed", url=url, error=str(e), error_type=type(e).__name__, exc_info=True)
        return []
