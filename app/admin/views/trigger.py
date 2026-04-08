# app/admin/views/trigger.py
import asyncio
import datetime
import structlog
from sqladmin import BaseView, expose
from starlette.responses import RedirectResponse
from app.jobs.weekly_newsletter import run_weekly_newsletter

logger = structlog.get_logger()


async def _run_and_clear(fn, app_state):
    """Run fn() and always reset trigger_running, even on failure."""
    error_msg = None
    try:
        await fn()
    except asyncio.CancelledError:
        logger.warning("trigger_task_cancelled")
        raise
    except Exception as e:
        logger.error("trigger_task_failed", exc_info=True)
        error_msg = str(e)
    finally:
        app_state.trigger_running = False
        app_state.trigger_task = None
        app_state.last_run_at = datetime.datetime.now(datetime.timezone.utc)
        app_state.last_run_error = error_msg


class TriggerAdmin(BaseView):
    name = "Trigger Newsletter"
    icon = "fa-solid fa-paper-plane"

    @expose("/trigger", methods=["GET", "POST"])
    async def trigger_page(self, request):
        if request.method == "POST":
            outer_app = self.__class__._admin_ref.app
            trigger_running = getattr(outer_app.state, "trigger_running", None)

            if trigger_running is None:
                logger.warning("trigger_running_not_set")
                request.session["flash"] = "Trigger unavailable — check logs."
                return RedirectResponse(
                    url=request.url_for("admin:trigger_page"),
                    status_code=303,
                )

            if trigger_running:
                request.session["flash"] = "Already running — please wait."
            else:
                outer_app.state.trigger_running = True
                # Store task reference on app.state to prevent GC before completion.
                # trigger_running is process-local and only prevents duplicate
                # /admin/trigger clicks within this worker process.
                outer_app.state.trigger_task = asyncio.create_task(
                    _run_and_clear(run_weekly_newsletter, outer_app.state)
                )
                request.session["flash"] = "Newsletter generation started."

            return RedirectResponse(
                url=request.url_for("admin:trigger_page"),
                status_code=303,
            )

        # GET
        outer_app = self.__class__._admin_ref.app
        flash = request.session.pop("flash", None)
        trigger_running = getattr(outer_app.state, "trigger_running", False)
        last_run_at = getattr(outer_app.state, "last_run_at", None)
        last_run_error = getattr(outer_app.state, "last_run_error", None)
        return await self.templates.TemplateResponse(
            request,
            "sqladmin/trigger.html",
            {
                "flash": flash,
                "trigger_running": trigger_running,
                "last_run_at": last_run_at,
                "last_run_error": last_run_error,
            },
        )
