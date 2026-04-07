# app/admin/views/trigger.py
import asyncio
import structlog
from sqladmin import BaseView, expose
from starlette.responses import RedirectResponse
from app.jobs.weekly_newsletter import run_weekly_newsletter

logger = structlog.get_logger()


async def _run_and_clear(fn, app_state):
    """Run fn() and always reset trigger_running, even on failure."""
    try:
        await fn()
    except Exception:
        logger.error("trigger_task_failed", exc_info=True)
    finally:
        app_state.trigger_running = False


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
                # Note: trigger_running is process-local; multi-worker deployments do
                # not share this flag across workers (acceptable for admin convenience).
                outer_app.state.trigger_task = asyncio.create_task(
                    _run_and_clear(run_weekly_newsletter, outer_app.state)
                )
                request.session["flash"] = "Newsletter generation started."

            return RedirectResponse(
                url=request.url_for("admin:trigger_page"),
                status_code=303,
            )

        # GET
        flash = request.session.pop("flash", None)
        return await self.templates.TemplateResponse(
            request,
            "sqladmin/trigger.html",
            {"flash": flash},
        )
