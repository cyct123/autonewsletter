# app/admin/views/ai_prompts.py
from sqladmin import BaseView, expose
from starlette.responses import RedirectResponse
from app.database import AsyncSessionLocal
from app.repositories.system_config import get_system_config
from app.services.ai_prompts import (
    DEFAULT_SUMMARIZE_INSTRUCTIONS,
    DEFAULT_TRANSLATE_INSTRUCTIONS,
    SUMMARIZE_FIXED_SUFFIX,
)
from app.utils.logger import logger

_COL_MAP = {"summarize": "summarize_prompt", "translate": "translate_prompt"}
_LABEL_MAP = {"summarize": "Summarization instructions", "translate": "Translation instructions"}
_MAX_PROMPT_LENGTHS = {"summarize": 4000, "translate": 500}
_TRANSLATE_FIXED_APPEND = "标题: [title text]"


class AIPromptsAdmin(BaseView):
    name = "AI Prompts"
    icon = "fa-solid fa-wand-magic-sparkles"

    @expose("/ai-prompts", methods=["GET", "POST"])
    async def ai_prompts_page(self, request):
        if request.method == "POST":
            form_data = await request.form()
            field = form_data.get("field")
            action = form_data.get("action")

            # Validate before touching DB
            if field not in _COL_MAP or action not in ("save", "reset"):
                logger.warning("ai_prompts_invalid_post", field=field, action=action)
                request.session["flash"] = "Error: invalid request."
                return RedirectResponse(
                    url=request.url_for("admin:ai_prompts_page"), status_code=303
                )

            flash = ""
            async with AsyncSessionLocal() as db:
                config = await get_system_config(db)
                try:
                    if action == "reset":
                        setattr(config, _COL_MAP[field], None)
                        flash = f"{_LABEL_MAP[field]} reset to default."
                    else:  # save
                        value = (form_data.get("instructions") or "").strip() or None
                        max_len = _MAX_PROMPT_LENGTHS[field]
                        if value and len(value) > max_len:
                            raise ValueError(
                                f"Instructions too long (max {max_len} characters)."
                            )
                        setattr(config, _COL_MAP[field], value)
                        flash = (
                            f"{_LABEL_MAP[field]} saved."
                            if value
                            else f"{_LABEL_MAP[field]} reset to default."
                        )
                    await db.commit()
                except Exception as e:
                    await db.rollback()
                    logger.exception("ai_prompts_save_error", field=field, action=action)
                    flash = f"Error: {e}"

            request.session["flash"] = flash
            return RedirectResponse(
                url=request.url_for("admin:ai_prompts_page"), status_code=303
            )

        # GET
        flash = request.session.pop("flash", None)
        async with AsyncSessionLocal() as db:
            config = await get_system_config(db)

        summarize_is_default = config.summarize_prompt is None
        translate_is_default = config.translate_prompt is None
        return await self.templates.TemplateResponse(
            request,
            "sqladmin/ai_prompts.html",
            {
                "flash": flash,
                "summarize_value": (
                    DEFAULT_SUMMARIZE_INSTRUCTIONS
                    if summarize_is_default
                    else config.summarize_prompt
                ),
                "translate_value": (
                    DEFAULT_TRANSLATE_INSTRUCTIONS
                    if translate_is_default
                    else config.translate_prompt
                ),
                "summarize_is_default": summarize_is_default,
                "translate_is_default": translate_is_default,
                "summarize_fixed_suffix": SUMMARIZE_FIXED_SUFFIX,
                "translate_fixed_append": _TRANSLATE_FIXED_APPEND,
            },
        )
