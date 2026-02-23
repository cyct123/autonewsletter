from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.config import settings
from app.jobs.weekly_newsletter import setup_scheduler, run_weekly_newsletter
from app.utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    logger.info("autonewsletter_starting")

    # Start scheduler
    scheduler = setup_scheduler()
    scheduler.start()

    # Run immediately if configured
    if settings.immediate_run:
        logger.info("immediate_run_triggered")
        await run_weekly_newsletter()

    logger.info("scheduler_ready")

    yield

    # Shutdown scheduler
    scheduler.shutdown()
    logger.info("scheduler_stopped")


app = FastAPI(
    title="AutoNewsletter",
    description="Automated newsletter system with RSS, AI summarization, and multi-channel distribution",
    version="2.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "service": "autonewsletter"}


@app.post("/trigger")
async def trigger_newsletter():
    """Manually trigger newsletter generation"""
    logger.info("manual_trigger_requested")
    await run_weekly_newsletter()
    return {"status": "triggered", "message": "Newsletter generation started"}


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "AutoNewsletter",
        "version": "2.0.0",
        "endpoints": {
            "health": "/health",
            "trigger": "/trigger (POST)"
        }
    }
