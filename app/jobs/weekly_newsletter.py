from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.config import settings
from app.utils.logger import logger
from app.database import AsyncSessionLocal
from app.modules.sources import list_sources
from app.services.rss import fetch_rss_items
from app.modules.transcription import transcribe
from app.modules.summarization import summarize_transcript, translate_title_to_chinese
from app.modules.content import select_top
from app.modules.subscribers import list_active
from app.modules.distribution import distribute
from app.repositories.content import insert_content, exists_by_url
from app.repositories.send_log import record_send
from app.utils.newsletter_template import build_newsletter_html


async def run_weekly_newsletter():
    """Execute weekly newsletter generation pipeline"""
    logger.info("weekly_pipeline_starting")

    async with AsyncSessionLocal() as db:
        try:
            # 1. Load sources
            sources = await list_sources(db)
            logger.info("sources_loaded", count=len(sources))

            # 2. Collect content
            collected = []
            for source in sources:
                if not source.get("active", True):
                    logger.info("source_skipped_inactive", source_name=source.get("name"))
                    continue

                logger.info("processing_source", source_name=source.get("name"), source_url=source["url"])

                items = await fetch_rss_items(
                    source["url"],
                    source.get("max_items_per_run", 5)
                )

                logger.info("rss_items_fetched", source_name=source.get("name"), item_count=len(items))

                for idx, item in enumerate(items, 1):
                    logger.info("processing_item", item_num=idx, title=item.get("title", "")[:100], url=item["url"])

                    # Deduplication check
                    if not settings.force_recent and await exists_by_url(db, item["url"]):
                        logger.info("content_skipped_duplicate", url=item["url"])
                        continue

                    # Transcription
                    logger.info("transcription_starting", url=item["url"])
                    transcript_result = await transcribe(item["url"])
                    logger.info("transcription_result", url=item["url"], has_text=bool(transcript_result.get("text")), success=transcript_result.get("success"))

                    text = transcript_result.get("text") or item.get("snippet", "")
                    logger.info("text_after_fallback", url=item["url"], text_length=len(text), text_preview=text[:200] if text else "")

                    if not text:
                        logger.warning("content_skipped_no_text", url=item["url"], item_title=item.get("title"))
                        continue

                    # Summarization
                    logger.info("summarization_starting", url=item["url"], text_length=len(text))
                    try:
                        summary_result = await summarize_transcript(text)
                        logger.info("summarization_result", url=item["url"], has_summary=bool(summary_result.get("summary")), quality_score=summary_result.get("qualityScore", 0))
                    except Exception as e:
                        logger.error("summarization_failed", url=item["url"], error=str(e), exc_info=True)
                        continue

                    # Title translation
                    logger.info("title_translation_starting", original_title=item["title"])
                    try:
                        zh_title = await translate_title_to_chinese(item["title"])
                        logger.info("title_translation_result", original=item["title"], translated=zh_title)
                    except Exception as e:
                        logger.error("title_translation_failed", original_title=item["title"], error=str(e), exc_info=True)
                        zh_title = item["title"]

                    # Build content object
                    content = {
                        "source_id": source.get("id"),
                        "title": zh_title,
                        "original_url": item["url"],
                        "transcript": text[:15000],
                        "summary": summary_result.get("summary", ""),
                        "key_points": summary_result.get("keyPoints", []),
                        "quality_score": summary_result.get("qualityScore", 0),
                        "status": "approved"
                    }

                    collected.append(content)
                    logger.info("content_added_to_collection", url=item["url"], quality_score=content["quality_score"])

                    # Insert into database
                    if source.get("id"):
                        try:
                            await insert_content(db, content)
                            logger.info("content_inserted_to_db", url=item["url"])
                        except Exception as e:
                            logger.error("content_insert_failed", url=item["url"], error=str(e), exc_info=True)

            logger.info("content_collected", total=len(collected))

            # 3. Select top content
            top_contents = select_top(collected, 10)
            logger.info("content_selected", selected=len(top_contents))

            if not top_contents:
                logger.warning("no_content_to_send")
                return

            # 4. Distribute
            subscribers = await list_active(db)
            if not subscribers:
                logger.warning("no_active_subscribers")
                return

            for sub in subscribers:
                prefs = sub.get("preferences", {})
                max_items = prefs.get("maxItemsPerNewsletter", 10)
                min_score = prefs.get("minQualityScore", 0.0)
                chosen = select_top(top_contents, limit=max_items, min_score=min_score)
                html = build_newsletter_html(chosen)

                result = await distribute(
                    {"title": "每周Newsletter", "html": html},
                    {"channel": sub["channelType"], "address": sub["identifier"]}
                )

                await record_send(db, sub["id"], sub["channelType"], result["ok"], result.get("error"))

                if result["ok"]:
                    logger.info("sent", subscriber=sub["identifier"], channel=sub["channelType"])
                else:
                    logger.error("send_failed", subscriber=sub["identifier"], error=result.get("error"))

            logger.info("weekly_pipeline_done")

        except Exception as e:
            logger.error("weekly_pipeline_failed", error=str(e), exc_info=True)
            raise


def setup_scheduler():
    """Configure APScheduler for weekly newsletter"""
    scheduler = AsyncIOScheduler()

    # Add weekly newsletter job
    trigger = CronTrigger.from_crontab(settings.weekly_cron)
    scheduler.add_job(
        run_weekly_newsletter,
        trigger,
        id="weekly_newsletter",
        name="Weekly Newsletter Generation"
    )

    logger.info("scheduler_configured", cron=settings.weekly_cron)
    return scheduler
