# AI Prompt Editor — Design Spec

**Date:** 2026-04-09
**Status:** Draft

---

## Overview

Add a dedicated admin page at `/admin/ai-prompts` that lets authenticated admins edit and reset the two AI instruction blocks used in `app/services/ai.py`: the summarization instructions and the title-translation instructions.

---

## Goals

- Allow runtime editing of AI instruction blocks without redeploying
- Make it clear whether each field is using the app default or a custom override
- Prevent accidental breakage of the JSON output contract in the summarize prompt
- Store settings in the existing `SystemConfig` row (id=1)

---

## Data Model

### New columns on `SystemConfig`

```python
summarize_prompt = Column(Text, nullable=True)   # NULL = use app default
translate_prompt = Column(Text, nullable=True)   # NULL = use app default
```

- Both columns are nullable. `NULL` means "follow the current hardcoded default." A non-null value is a stored custom override.
- `get_or_create_system_config()` leaves both as `NULL` — no backfill needed.
- An Alembic migration adds the two columns with `server_default=None`.

### Read semantics

```python
# Explicit None check — do NOT use `or` (empty string "" must normalize to None before save)
prompt = DEFAULT_SUMMARIZE_INSTRUCTIONS if config.summarize_prompt is None else config.summarize_prompt
```

### Write semantics

- Strip whitespace; if empty after strip, write `None` (not empty string).
- On reset: write `None` explicitly — do NOT copy `DEFAULT_*` constant into the row.

---

## New Module: `app/services/ai_prompts.py`

Owns defaults and prompt-building functions. Both `ai.py` and the admin view import from here.

```python
DEFAULT_SUMMARIZE_INSTRUCTIONS = """\
1) 用中文输出;
2) 生成3-6句高信息密度的正文，覆盖"发生了什么+背景+影响/所以怎样(so what)";
3) 至少标记两句为关键判断(boldIndices)，其中一条必须是"so what";
4) 同时提取3个关键要点;
5) 给出0-1之间的质量分数;\
"""

DEFAULT_TRANSLATE_INSTRUCTIONS = "将以下标题精准翻译为中文标题，保持简洁凝练"

SUMMARIZE_FIXED_SUFFIX = (
    '结果以以下JSON格式返回: { "sentences": string[], "boldIndices": number[], '
    '"keyPoints": string[], "qualityScore": number }\n原文内容: '
)

def build_summarize_prompt(instructions: str | None, text: str) -> str:
    block = instructions if instructions is not None else DEFAULT_SUMMARIZE_INSTRUCTIONS
    return (
        f"你是中文资讯编辑，按以下标准生成中文内容:\n{block}\n"
        f"{SUMMARIZE_FIXED_SUFFIX}{text[:6000]}"
    )

def build_translate_prompt(instructions: str | None, title: str) -> str:
    block = instructions if instructions is not None else DEFAULT_TRANSLATE_INSTRUCTIONS
    return f"{block}\n标题: {title[:200]}"
```

---

## Updated `app/services/ai.py`

- Remove hardcoded prompt strings.
- Import `build_summarize_prompt`, `build_translate_prompt` from `app/services/ai_prompts`.
- Pass `config.summarize_prompt` / `config.translate_prompt` to builders.
- Log whether default or custom instructions were used:
  ```python
  logger.info("summarize_called", text_length=len(text),
              using_custom_prompt=config.summarize_prompt is not None)
  ```

---

## New View: `app/admin/views/ai_prompts.py`

`AIPromptsAdmin(BaseView)` following the same pattern as `TriggerAdmin`.

```
name = "AI Prompts"
icon = "fa-solid fa-wand-magic-sparkles"
```

### Route

```python
@expose("/ai-prompts", methods=["GET", "POST"])
async def ai_prompts_page(self, request): ...
```

### GET

1. Open `AsyncSessionLocal()`, call `get_system_config(db)`.
2. Pass to template:
   - `summarize_value`: `config.summarize_prompt or DEFAULT_SUMMARIZE_INSTRUCTIONS` (for display)
   - `translate_value`: `config.translate_prompt or DEFAULT_TRANSLATE_INSTRUCTIONS` (for display)
   - `summarize_is_default`: `config.summarize_prompt is None`
   - `translate_is_default`: `config.translate_prompt is None`
   - `summarize_fixed_suffix`: `SUMMARIZE_FIXED_SUFFIX` (rendered read-only below textarea)
   - `flash`: popped from `request.session`

### POST

Form fields:
- `field`: `"summarize"` or `"translate"` — identifies which instruction to save
- `action`: `"save"` or `"reset"` — identifies the operation

Logic:

```python
field = (await request.form()).get("field")   # "summarize" | "translate"
action = (await request.form()).get("action") # "save" | "reset"

async with AsyncSessionLocal() as db:
    config = await get_system_config(db)
    try:
        if action == "reset":
            setattr(config, col_map[field], None)
            flash = f"{label_map[field]} reset to default."
        else:  # save
            value = form_data.get(value_field_map[field], "").strip() or None
            if value and len(value) > MAX_PROMPT_LENGTH:
                raise ValueError(f"Instructions too long (max {MAX_PROMPT_LENGTH} characters).")
            setattr(config, col_map[field], value)
            flash = f"{label_map[field]} saved." if value else f"{label_map[field]} reset to default."
        await db.commit()
    except Exception as e:
        await db.rollback()
        flash = f"Error: {e}"
await request.session["flash"] = flash
return RedirectResponse(url=request.url_for("admin:ai_prompts_page"), status_code=303)
```

Where:
- `col_map = {"summarize": "summarize_prompt", "translate": "translate_prompt"}`
- `label_map = {"summarize": "Summarization instructions", "translate": "Translation instructions"}`
- `MAX_PROMPT_LENGTH = 4000`

### Validation

- Max length: 4000 chars for summarize, 500 chars for translate.
- Normalize empty/whitespace → `None` on save.
- Unknown `field` or `action` values: log warning, flash error, redirect.

---

## New Template: `app/admin/templates/sqladmin/ai_prompts.html`

Extends `sqladmin/layout.html`. Overrides `content_header` and `content` blocks.

Page order (top to bottom):
1. Flash alert (success green / warning yellow / error red)
2. **Translation Instructions** section (above Summarization)
3. **Summarization Instructions** section

Each section:
- Header: field label + badge (`"Using app default"` grey / `"Custom override"` blue)
- Help text: one sentence describing what the field controls
- `<textarea>` pre-filled with current editable value
- Dashed read-only box below textarea showing the fixed suffix (for summarize) or fixed append (for translate)
- Single `<form method="POST">` with:
  - Hidden `<input name="field" value="summarize|translate">`
  - Textarea `<textarea name="instructions">`
  - `<button name="action" value="save">Save</button>`
  - `<button name="action" value="reset">↺ Reset to Default</button>`

Flash CSS: `alert-success` if "saved" or "reset" in flash, `alert-danger` if "Error" in flash.

---

## Wiring (`app/main.py`)

```python
from app.admin.views.ai_prompts import AIPromptsAdmin
# ...
admin.add_view(AIPromptsAdmin)
```

Initialize no new `app.state` fields — this view uses DB, not in-process state.

---

## `app/admin/views/__init__.py`

Add:
```python
from app.admin.views.ai_prompts import AIPromptsAdmin
```

---

## Alembic Migration

```python
# migrations/versions/XXXX_add_ai_prompt_columns.py
def upgrade():
    op.add_column("system_config", sa.Column("summarize_prompt", sa.Text(), nullable=True))
    op.add_column("system_config", sa.Column("translate_prompt", sa.Text(), nullable=True))

def downgrade():
    op.drop_column("system_config", "translate_prompt")
    op.drop_column("system_config", "summarize_prompt")
```

---

## Tests

| Test | What it covers |
|------|---------------|
| `test_ai_prompts_page_requires_login` | GET redirects to login when unauthenticated |
| `test_ai_prompts_get_shows_defaults` | GET renders both sections with "Using app default" badge when columns are NULL |
| `test_ai_prompts_get_shows_custom` | GET renders "Custom override" badge when columns are non-NULL |
| `test_save_summarize_instructions` | POST field=summarize action=save writes value, flash confirms |
| `test_save_translate_instructions` | POST field=translate action=save writes value, flash confirms |
| `test_reset_summarize` | POST field=summarize action=reset writes None, flash confirms |
| `test_reset_translate` | POST field=translate action=reset writes None, flash confirms |
| `test_empty_save_normalizes_to_none` | POST with empty/whitespace value writes None |
| `test_save_too_long_rejected` | POST with value > MAX_PROMPT_LENGTH returns error flash |
| `test_build_summarize_prompt_default` | `build_summarize_prompt(None, text)` uses default and appends fixed suffix |
| `test_build_summarize_prompt_custom` | `build_summarize_prompt(custom, text)` uses custom and appends fixed suffix |
| `test_build_translate_prompt_default` | `build_translate_prompt(None, title)` uses default and appends title |
| `test_build_translate_prompt_custom` | `build_translate_prompt(custom, title)` uses custom and appends title |

---

## Out of Scope

- Prompt versioning / history
- Per-source prompt overrides
- Prompt preview / test-run button
- Multi-worker DB-level locking (prompt writes are rare manual admin actions)
