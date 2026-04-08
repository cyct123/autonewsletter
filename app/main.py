# app/main.py
import base64
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from sqladmin import Admin
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import Response

from app.config import settings
from app.database import engine, AsyncSessionLocal
from app.jobs.weekly_newsletter import setup_scheduler, run_weekly_newsletter
from app.modules.sources import init_sources_from_env
from app.repositories.system_config import get_or_create_system_config
from app.utils.logger import logger

from app.admin.auth import AdminAuth
from app.admin.views.source import SourceAdmin
from app.admin.views.subscriber import SubscriberAdmin
from app.admin.views.content import ContentAdmin
from app.admin.views.send_log import SendLogAdmin
from app.admin.views.system_config import SystemConfigAdmin
from app.admin.views.trigger import TriggerAdmin


class TriggerAuthMiddleware(BaseHTTPMiddleware):
    """HTTP Basic Auth protection for POST /trigger only."""

    async def dispatch(self, request, call_next):
        if request.url.path == "/trigger" and request.method == "POST":
            auth = request.headers.get("Authorization", "")
            if not auth.startswith("Basic "):
                return Response(
                    "Unauthorized", status_code=401,
                    headers={"WWW-Authenticate": "Basic"},
                )
            try:
                decoded = base64.b64decode(auth[6:]).decode()
                username, password = decoded.split(":", 1)
            except Exception:
                return Response(
                    "Unauthorized", status_code=401,
                    headers={"WWW-Authenticate": "Basic"},
                )
            if username != settings.admin_user or password != settings.admin_pass:
                return Response(
                    "Unauthorized", status_code=401,
                    headers={"WWW-Authenticate": "Basic"},
                )
        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    logger.info("autonewsletter_starting")

    async with AsyncSessionLocal() as db:
        try:
            await init_sources_from_env(db)
        except Exception:
            logger.warning("init_sources_failed")
        config = await get_or_create_system_config(db)

    scheduler = setup_scheduler(weekly_cron=config.weekly_cron)
    app.state.scheduler = scheduler
    app.state.trigger_running = False
    app.state.last_run_at = None
    app.state.last_run_error = None
    scheduler.start()

    if settings.immediate_run:
        logger.info("immediate_run_triggered")
        await run_weekly_newsletter()

    logger.info("scheduler_ready")

    yield

    scheduler.shutdown()
    logger.info("scheduler_stopped")


app = FastAPI(
    title="AutoNewsletter",
    description="Automated newsletter system with RSS, AI summarization, and multi-channel distribution",
    version="2.0.0",
    lifespan=lifespan,
)

# Middleware registration order matters in Starlette (last added = first executed at runtime)
# SessionMiddleware added first → executes second (provides session for AdminAuth)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.admin_session_secret or "changeme-set-ADMIN_SESSION_SECRET",
)
# TriggerAuthMiddleware added second → executes first (gates /trigger before session runs)
app.add_middleware(TriggerAuthMiddleware)

# Admin — constructed here in main.py to avoid circular import
authentication_backend = AdminAuth(
    secret_key=settings.admin_session_secret or "changeme-set-ADMIN_SESSION_SECRET"
)
admin = Admin(app, engine, authentication_backend=authentication_backend,
              templates_dir=str(Path(__file__).resolve().parent / "admin" / "templates"))
admin.add_view(SourceAdmin)
admin.add_view(SubscriberAdmin)
admin.add_view(ContentAdmin)
admin.add_view(SendLogAdmin)
admin.add_view(SystemConfigAdmin)
admin.add_view(TriggerAdmin)


@app.get("/health")
async def health_check():
    """Health check endpoint — no auth required"""
    return {"status": "ok", "service": "autonewsletter"}


@app.post("/trigger")
async def trigger_newsletter():
    """Manually trigger newsletter generation — requires Basic Auth"""
    logger.info("manual_trigger_requested")
    await run_weekly_newsletter()
    return {"status": "triggered", "message": "Newsletter generation started"}


@app.get("/")
async def root():
    return {
        "service": "AutoNewsletter",
        "version": "2.0.0",
        "endpoints": {
            "health": "/health",
            "trigger": "/trigger (POST, requires Basic Auth)",
            "admin": "/admin",
        },
    }
