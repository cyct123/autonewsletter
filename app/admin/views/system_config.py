# app/admin/views/system_config.py
import structlog
from sqladmin import ModelView
from apscheduler.triggers.cron import CronTrigger
from app.models.system_config import SystemConfig

logger = structlog.get_logger()


class SystemConfigAdmin(ModelView, model=SystemConfig):
    name = "System Config"
    name_plural = "System Config"
    icon = "fa-solid fa-gear"

    column_list = [
        SystemConfig.weekly_cron,
        SystemConfig.ai_model,
        SystemConfig.default_max_items_per_run,
        SystemConfig.force_recent,
    ]

    # Single-row config — no creation or deletion
    can_create = False
    can_edit = True
    can_delete = False
    can_view_details = True

    async def on_model_change(self, data, model, is_created, request):
        """Validate fields before saving. Raises ValueError on invalid input."""
        try:
            CronTrigger.from_crontab(data["weekly_cron"])
        except Exception:
            raise ValueError("weekly_cron: cron expression is invalid")
        if data.get("ai_model") not in ("deepseek", "openai"):
            raise ValueError("ai_model: must be 'deepseek' or 'openai'")

    async def after_model_change(self, data, model, is_created, request):
        """Hot-reload the APScheduler job after weekly_cron is saved."""
        # sqladmin mounts self.admin (inner Starlette app) at /admin, so request.app
        # is the inner app. Access the outer FastAPI app via _admin_ref.app.
        outer_app = getattr(self.__class__, "_admin_ref", None)
        outer_app = outer_app.app if outer_app is not None else request.app
        scheduler = getattr(outer_app.state, "scheduler", None)
        if scheduler is None:
            logger.warning("scheduler_not_found",
                           reason="app.state.scheduler not set, skipping hot-reload")
            return
        new_cron = data["weekly_cron"]
        try:
            from zoneinfo import ZoneInfo
            trigger = CronTrigger.from_crontab(new_cron, timezone=ZoneInfo("Asia/Shanghai"))
            scheduler.reschedule_job("weekly_newsletter", trigger=trigger)
            logger.info("scheduler_reloaded", weekly_cron=new_cron)
        except Exception as e:
            logger.error("scheduler_reload_failed", error=str(e))
