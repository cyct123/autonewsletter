# AI Prompt Editor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `/admin/ai-prompts` page that lets authenticated admins edit and reset the summarization and translation instruction blocks used by the AI pipeline, stored in the existing `SystemConfig` DB row.

**Architecture:** Extract hardcoded AI prompt strings from `app/services/ai.py` into a new `app/services/ai_prompts.py` module that owns defaults and prompt-building functions. Add two nullable `Text` columns to `SystemConfig`. Wire a new `AIPromptsAdmin(BaseView)` sqladmin page (two independent forms, one per instruction block) that reads/writes those columns via `AsyncSessionLocal`.

**Tech Stack:** SQLAlchemy `Text` column, Alembic migration, sqladmin `BaseView`/`@expose`, Starlette session flash, Jinja2 template, `AsyncSessionLocal`, pytest + `unittest.mock`.

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `app/services/ai_prompts.py` | **Create** | Defaults, `SUMMARIZE_FIXED_SUFFIX`, `build_summarize_prompt`, `build_translate_prompt` |
| `app/models/system_config.py` | **Modify** | Add `summarize_prompt` and `translate_prompt` nullable Text columns |
| `alembic/versions/<hash>_add_ai_prompt_columns.py` | **Create** | Migration that adds the two columns |
| `app/services/ai.py` | **Modify** | Replace hardcoded prompts with calls to builders; add `using_custom_prompt` log field |
| `app/admin/views/ai_prompts.py` | **Create** | `AIPromptsAdmin(BaseView)` — GET/POST handler |
| `app/admin/templates/sqladmin/ai_prompts.html` | **Create** | Jinja2 template — two sections, badges, textareas, fixed-suffix previews |
| `app/admin/views/__init__.py` | **Modify** | Export `AIPromptsAdmin` |
| `app/main.py` | **Modify** | Import and `admin.add_view(AIPromptsAdmin)` |
| `tests/test_ai_prompts_builders.py` | **Create** | Pure unit tests for `ai_prompts.py` builders (no DB, no HTTP) |
| `tests/test_ai_prompts_admin.py` | **Create** | HTTP-level view tests using `TestClient` with mocked auth and DB |

---

## Task 1: Create `app/services/ai_prompts.py` with builder tests

**Files:**
- Create: `app/services/ai_prompts.py`
- Create: `tests/test_ai_prompts_builders.py`

- [ ] **Step 1.1: Write the failing builder tests**

Create `tests/test_ai_prompts_builders.py`:

```python
# tests/test_ai_prompts_builders.py
from app.services.ai_prompts import (
    DEFAULT_SUMMARIZE_INSTRUCTIONS,
    DEFAULT_TRANSLATE_INSTRUCTIONS,
    SUMMARIZE_FIXED_SUFFIX,
    build_summarize_prompt,
    build_translate_prompt,
)


def test_build_summarize_prompt_default():
    prompt = build_summarize_prompt(None, "some article text")
    assert DEFAULT_SUMMARIZE_INSTRUCTIONS in prompt
    assert SUMMARIZE_FIXED_SUFFIX in prompt
    assert "some article text" in prompt
    assert "你是中文资讯编辑" in prompt


def test_build_summarize_prompt_custom():
    prompt = build_summarize_prompt("custom instructions", "some article text")
    assert "custom instructions" in prompt
    assert DEFAULT_SUMMARIZE_INSTRUCTIONS not in prompt
    assert SUMMARIZE_FIXED_SUFFIX in prompt
    assert "some article text" in prompt


def test_build_summarize_prompt_truncates_text():
    long_text = "x" * 7000
    prompt = build_summarize_prompt(None, long_text)
    # text is truncated to 6000 chars before appending
    assert "x" * 6000 in prompt
    assert "x" * 6001 not in prompt


def test_build_translate_prompt_default():
    prompt = build_translate_prompt(None, "My Article Title")
    assert DEFAULT_TRANSLATE_INSTRUCTIONS in prompt
    assert "My Article Title" in prompt
    assert "标题:" in prompt


def test_build_translate_prompt_custom():
    prompt = build_translate_prompt("自定义翻译指令", "My Article Title")
    assert "自定义翻译指令" in prompt
    assert DEFAULT_TRANSLATE_INSTRUCTIONS not in prompt
    assert "My Article Title" in prompt


def test_build_translate_prompt_truncates_title():
    long_title = "T" * 300
    prompt = build_translate_prompt(None, long_title)
    assert "T" * 200 in prompt
    assert "T" * 201 not in prompt
```

- [ ] **Step 1.2: Run tests to verify they fail**

```bash
docker exec -w /app autonewsletter-app python -m pytest tests/test_ai_prompts_builders.py -v
```

Expected: `ModuleNotFoundError` or `ImportError` — `app/services/ai_prompts.py` does not exist yet.

- [ ] **Step 1.3: Create `app/services/ai_prompts.py`**

```python
# app/services/ai_prompts.py

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
    """Build the full summarization prompt.

    The instruction block is user-configurable (stored in SystemConfig.summarize_prompt).
    The preamble and JSON schema contract are always fixed — editing them would break
    JSON parsing in ai.py.
    """
    block = instructions if instructions is not None else DEFAULT_SUMMARIZE_INSTRUCTIONS
    return (
        f"你是中文资讯编辑，按以下标准生成中文内容:\n{block}\n"
        f"{SUMMARIZE_FIXED_SUFFIX}{text[:6000]}"
    )


def build_translate_prompt(instructions: str | None, title: str) -> str:
    """Build the full title translation prompt.

    The instruction text is user-configurable. The title is always appended by code.
    """
    block = instructions if instructions is not None else DEFAULT_TRANSLATE_INSTRUCTIONS
    return f"{block}\n标题: {title[:200]}"
```

- [ ] **Step 1.4: Copy file to container and run tests**

```bash
docker cp app/services/ai_prompts.py autonewsletter-app:/app/app/services/ai_prompts.py
docker cp tests/test_ai_prompts_builders.py autonewsletter-app:/app/tests/test_ai_prompts_builders.py
docker exec -w /app autonewsletter-app python -m pytest tests/test_ai_prompts_builders.py -v
```

Expected: 6 tests PASS.

- [ ] **Step 1.5: Commit**

```bash
git add app/services/ai_prompts.py tests/test_ai_prompts_builders.py
git commit -m "feat(ai): add ai_prompts module with build functions and defaults"
```

---

## Task 2: Add columns to `SystemConfig` and generate migration

**Files:**
- Modify: `app/models/system_config.py`
- Create: `alembic/versions/<hash>_add_ai_prompt_columns.py` (via autogenerate)

- [ ] **Step 2.1: Add columns to the model**

Edit `app/models/system_config.py`. The full file after edit:

```python
# app/models/system_config.py
from sqlalchemy import Column, Integer, String, Boolean, Text
from app.database import Base


class SystemConfig(Base):
    __tablename__ = "system_config"

    id = Column(Integer, primary_key=True, default=1)
    weekly_cron = Column(String, nullable=False, default="0 9 * * 3")
    ai_model = Column(String, nullable=False, default="deepseek")
    default_max_items_per_run = Column(Integer, nullable=False, default=5)
    force_recent = Column(Boolean, nullable=False, default=False)
    summarize_prompt = Column(Text, nullable=True)   # NULL = use app default
    translate_prompt = Column(Text, nullable=True)   # NULL = use app default
```

- [ ] **Step 2.2: Generate the Alembic migration**

```bash
docker cp app/models/system_config.py autonewsletter-app:/app/app/models/system_config.py
docker exec -w /app autonewsletter-app alembic revision --autogenerate -m "add_ai_prompt_columns"
```

Expected output: `Generating /app/alembic/versions/<hash>_add_ai_prompt_columns.py ... done`

- [ ] **Step 2.3: Copy the generated migration out of the container**

```bash
# Find the new migration file
docker exec autonewsletter-app ls alembic/versions/
# Copy it out (replace <hash> with the actual hash shown above)
docker cp autonewsletter-app:/app/alembic/versions/<hash>_add_ai_prompt_columns.py alembic/versions/
```

Verify the migration contains:

```python
op.add_column('system_config', sa.Column('summarize_prompt', sa.Text(), nullable=True))
op.add_column('system_config', sa.Column('translate_prompt', sa.Text(), nullable=True))
```

- [ ] **Step 2.4: Apply the migration**

```bash
docker exec -w /app autonewsletter-app alembic upgrade head
```

Expected: `Running upgrade 7c819eed91ce -> <hash>, add_ai_prompt_columns`

- [ ] **Step 2.5: Verify columns exist**

```bash
docker exec autonewsletter-db psql -U autonews -d autonews -c "\d system_config"
```

Expected: `summarize_prompt` and `translate_prompt` columns with type `text`, nullable.

- [ ] **Step 2.6: Run full test suite to confirm nothing broke**

```bash
docker exec -w /app autonewsletter-app python -m pytest tests/ -q
```

Expected: all existing tests PASS (new columns are nullable, no existing logic broken).

- [ ] **Step 2.7: Commit**

```bash
git add app/models/system_config.py alembic/versions/<hash>_add_ai_prompt_columns.py
git commit -m "feat(db): add summarize_prompt and translate_prompt columns to SystemConfig"
```

---

## Task 3: Update `app/services/ai.py` to use builders

**Files:**
- Modify: `app/services/ai.py`

- [ ] **Step 3.1: Update `ai.py`**

Replace the hardcoded `prompt = """...""" + text[:6000]` block and translate prompt string. The full updated file:

```python
# app/services/ai.py
import json
from sqlalchemy.ext.asyncio import AsyncSession
from openai import AsyncOpenAI
from app.config import settings
from app.repositories.system_config import get_system_config
from app.services.ai_prompts import build_summarize_prompt, build_translate_prompt
from app.utils.logger import logger


async def summarize(text: str, db: AsyncSession) -> dict:
    """Generate Chinese summary with key points and quality score"""
    config = await get_system_config(db)

    if config.ai_model == "openai" and settings.openai_api_key:
        api_key = settings.openai_api_key
        base_url = None
        model = "gpt-4o-mini"
    elif settings.deepseek_api_key:
        if config.ai_model == "openai":
            logger.warning("ai_model_fallback", configured="openai", reason="OPENAI_API_KEY not set, using DeepSeek")
        api_key = settings.deepseek_api_key
        base_url = "https://api.deepseek.com"
        model = "deepseek-chat"
    else:
        logger.warning("no_api_key_configured", message="Neither DEEPSEEK_API_KEY nor OPENAI_API_KEY is set")
        return {
            "summary": text[:300],
            "sentences": [],
            "boldIndices": [],
            "keyPoints": [],
            "qualityScore": 0,
        }

    logger.info("summarize_called", text_length=len(text),
                using_custom_prompt=config.summarize_prompt is not None)
    client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    prompt = build_summarize_prompt(config.summarize_prompt, text)

    logger.info("ai_request_starting", model=model, prompt_length=len(prompt))

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )

        output = response.choices[0].message.content
        logger.info("ai_response_received", model=model, output_length=len(output), output_preview=output[:200])

        parsed = json.loads(output)
        result = {
            "summary": "".join(parsed.get("sentences", [])),
            "sentences": parsed.get("sentences", []),
            "boldIndices": parsed.get("boldIndices", []),
            "keyPoints": parsed.get("keyPoints", []),
            "qualityScore": float(parsed.get("qualityScore", 0))
        }
        logger.info("ai_summarization_success", model=model, quality_score=result["qualityScore"], key_points_count=len(result["keyPoints"]))
        return result
    except json.JSONDecodeError as e:
        logger.error("ai_json_parse_failed", error=str(e), output=output[:500] if 'output' in locals() else "N/A")
        return {
            "summary": text[:300],
            "sentences": [],
            "boldIndices": [],
            "keyPoints": [],
            "qualityScore": 0.5
        }
    except Exception as e:
        logger.error("ai_summarization_failed", error=str(e), error_type=type(e).__name__, exc_info=True)
        return {
            "summary": text[:300],
            "sentences": [],
            "boldIndices": [],
            "keyPoints": [],
            "qualityScore": 0.5
        }


async def translate_title(title: str, db: AsyncSession) -> str:
    """Translate English title to Chinese"""
    ascii_count = sum(1 for c in title if ord(c) < 128)
    ascii_ratio = ascii_count / max(len(title), 1)

    logger.info("translate_title_called", title=title[:100], ascii_ratio=ascii_ratio)

    if ascii_ratio < 0.6:
        logger.info("translation_skipped", reason="already_chinese", ascii_ratio=ascii_ratio)
        return title

    config = await get_system_config(db)

    if config.ai_model == "openai" and settings.openai_api_key:
        api_key = settings.openai_api_key
        base_url = None
        model = "gpt-4o-mini"
    elif settings.deepseek_api_key:
        if config.ai_model == "openai":
            logger.warning("ai_model_fallback", configured="openai", reason="OPENAI_API_KEY not set, using DeepSeek")
        api_key = settings.deepseek_api_key
        base_url = "https://api.deepseek.com"
        model = "deepseek-chat"
    else:
        logger.warning("translation_skipped_no_api_key")
        return title

    client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    prompt = build_translate_prompt(config.translate_prompt, title)

    try:
        logger.info("translation_request_starting", model=model,
                    using_custom_prompt=config.translate_prompt is not None)
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )

        translated = response.choices[0].message.content.strip()
        logger.info("translation_success", original=title, translated=translated)
        return translated or title
    except Exception as e:
        logger.error("title_translation_failed", error=str(e), error_type=type(e).__name__, exc_info=True)
        return title
```

- [ ] **Step 3.2: Copy and run full test suite**

```bash
docker cp app/services/ai.py autonewsletter-app:/app/app/services/ai.py
docker exec -w /app autonewsletter-app python -m pytest tests/ -q
```

Expected: all tests PASS (including 6 builder tests from Task 1).

- [ ] **Step 3.3: Commit**

```bash
git add app/services/ai.py
git commit -m "refactor(ai): use build_summarize_prompt and build_translate_prompt from ai_prompts"
```

---

## Task 4: View, template, wiring, and view tests

**Files:**
- Create: `app/admin/views/ai_prompts.py`
- Create: `app/admin/templates/sqladmin/ai_prompts.html`
- Modify: `app/admin/views/__init__.py`
- Modify: `app/main.py`
- Create: `tests/test_ai_prompts_admin.py`

- [ ] **Step 4.1: Write the failing view tests**

Create `tests/test_ai_prompts_admin.py`:

```python
# tests/test_ai_prompts_admin.py
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from app.main import app


def _make_mock_config(summarize_prompt=None, translate_prompt=None):
    """Return a mock SystemConfig row."""
    cfg = MagicMock()
    cfg.summarize_prompt = summarize_prompt
    cfg.translate_prompt = translate_prompt
    return cfg


def _mock_db_context(mock_config):
    """Return patched AsyncSessionLocal and get_system_config for use in `with patch(...)` blocks."""
    mock_session = AsyncMock()
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    return mock_cm, AsyncMock(return_value=mock_config)


def _login(client, mock_settings):
    mock_settings.admin_user = "admin"
    mock_settings.admin_pass = "testpass"
    client.post("/admin/login", data={"username": "admin", "password": "testpass"},
                follow_redirects=False)


def test_ai_prompts_page_requires_login():
    client = TestClient(app, raise_server_exceptions=False, follow_redirects=True)
    response = client.get("/admin/ai-prompts")
    assert "/admin/login" in str(response.url)


def test_ai_prompts_post_requires_login():
    client = TestClient(app, raise_server_exceptions=False, follow_redirects=True)
    response = client.post("/admin/ai-prompts",
                           data={"field": "summarize", "action": "save", "instructions": "x"})
    assert "/admin/login" in str(response.url)


def test_ai_prompts_get_shows_defaults():
    mock_config = _make_mock_config(summarize_prompt=None, translate_prompt=None)
    mock_cm, mock_get = _mock_db_context(mock_config)
    with patch("app.admin.auth.settings") as mock_settings, \
         patch("app.admin.views.ai_prompts.AsyncSessionLocal", return_value=mock_cm), \
         patch("app.admin.views.ai_prompts.get_system_config", mock_get):
        client = TestClient(app, raise_server_exceptions=False)
        _login(client, mock_settings)
        response = client.get("/admin/ai-prompts")
    assert response.status_code == 200
    assert "Using app default" in response.text


def test_ai_prompts_get_shows_custom():
    mock_config = _make_mock_config(summarize_prompt="my custom instructions",
                                    translate_prompt="my custom translation")
    mock_cm, mock_get = _mock_db_context(mock_config)
    with patch("app.admin.auth.settings") as mock_settings, \
         patch("app.admin.views.ai_prompts.AsyncSessionLocal", return_value=mock_cm), \
         patch("app.admin.views.ai_prompts.get_system_config", mock_get):
        client = TestClient(app, raise_server_exceptions=False)
        _login(client, mock_settings)
        response = client.get("/admin/ai-prompts")
    assert response.status_code == 200
    assert "Custom override" in response.text
    assert "my custom instructions" in response.text


def test_save_summarize_instructions():
    mock_config = _make_mock_config()
    mock_cm, mock_get = _mock_db_context(mock_config)
    with patch("app.admin.auth.settings") as mock_settings, \
         patch("app.admin.views.ai_prompts.AsyncSessionLocal", return_value=mock_cm), \
         patch("app.admin.views.ai_prompts.get_system_config", mock_get):
        client = TestClient(app, raise_server_exceptions=False)
        _login(client, mock_settings)
        response = client.post("/admin/ai-prompts",
                               data={"field": "summarize", "action": "save",
                                     "instructions": "new instructions"},
                               follow_redirects=True)
    assert response.status_code == 200
    assert "Summarization instructions saved." in response.text
    assert mock_config.summarize_prompt == "new instructions"


def test_save_translate_instructions():
    mock_config = _make_mock_config()
    mock_cm, mock_get = _mock_db_context(mock_config)
    with patch("app.admin.auth.settings") as mock_settings, \
         patch("app.admin.views.ai_prompts.AsyncSessionLocal", return_value=mock_cm), \
         patch("app.admin.views.ai_prompts.get_system_config", mock_get):
        client = TestClient(app, raise_server_exceptions=False)
        _login(client, mock_settings)
        response = client.post("/admin/ai-prompts",
                               data={"field": "translate", "action": "save",
                                     "instructions": "新翻译指令"},
                               follow_redirects=True)
    assert response.status_code == 200
    assert "Translation instructions saved." in response.text
    assert mock_config.translate_prompt == "新翻译指令"


def test_reset_summarize():
    mock_config = _make_mock_config(summarize_prompt="old custom")
    mock_cm, mock_get = _mock_db_context(mock_config)
    with patch("app.admin.auth.settings") as mock_settings, \
         patch("app.admin.views.ai_prompts.AsyncSessionLocal", return_value=mock_cm), \
         patch("app.admin.views.ai_prompts.get_system_config", mock_get):
        client = TestClient(app, raise_server_exceptions=False)
        _login(client, mock_settings)
        response = client.post("/admin/ai-prompts",
                               data={"field": "summarize", "action": "reset"},
                               follow_redirects=True)
    assert response.status_code == 200
    assert "reset to default" in response.text
    assert mock_config.summarize_prompt is None


def test_reset_translate():
    mock_config = _make_mock_config(translate_prompt="old custom")
    mock_cm, mock_get = _mock_db_context(mock_config)
    with patch("app.admin.auth.settings") as mock_settings, \
         patch("app.admin.views.ai_prompts.AsyncSessionLocal", return_value=mock_cm), \
         patch("app.admin.views.ai_prompts.get_system_config", mock_get):
        client = TestClient(app, raise_server_exceptions=False)
        _login(client, mock_settings)
        response = client.post("/admin/ai-prompts",
                               data={"field": "translate", "action": "reset"},
                               follow_redirects=True)
    assert response.status_code == 200
    assert "reset to default" in response.text
    assert mock_config.translate_prompt is None


def test_empty_save_normalizes_to_none():
    mock_config = _make_mock_config(summarize_prompt="old value")
    mock_cm, mock_get = _mock_db_context(mock_config)
    with patch("app.admin.auth.settings") as mock_settings, \
         patch("app.admin.views.ai_prompts.AsyncSessionLocal", return_value=mock_cm), \
         patch("app.admin.views.ai_prompts.get_system_config", mock_get):
        client = TestClient(app, raise_server_exceptions=False)
        _login(client, mock_settings)
        client.post("/admin/ai-prompts",
                    data={"field": "summarize", "action": "save", "instructions": "   "},
                    follow_redirects=True)
    assert mock_config.summarize_prompt is None


def test_save_too_long_rejected():
    mock_config = _make_mock_config()
    mock_cm, mock_get = _mock_db_context(mock_config)
    with patch("app.admin.auth.settings") as mock_settings, \
         patch("app.admin.views.ai_prompts.AsyncSessionLocal", return_value=mock_cm), \
         patch("app.admin.views.ai_prompts.get_system_config", mock_get):
        client = TestClient(app, raise_server_exceptions=False)
        _login(client, mock_settings)
        response = client.post("/admin/ai-prompts",
                               data={"field": "summarize", "action": "save",
                                     "instructions": "x" * 4001},
                               follow_redirects=True)
    assert response.status_code == 200
    assert "Error" in response.text


def test_unknown_field_rejected():
    mock_config = _make_mock_config()
    mock_cm, mock_get = _mock_db_context(mock_config)
    with patch("app.admin.auth.settings") as mock_settings, \
         patch("app.admin.views.ai_prompts.AsyncSessionLocal", return_value=mock_cm), \
         patch("app.admin.views.ai_prompts.get_system_config", mock_get):
        client = TestClient(app, raise_server_exceptions=False)
        _login(client, mock_settings)
        response = client.post("/admin/ai-prompts",
                               data={"field": "badfield", "action": "save",
                                     "instructions": "x"},
                               follow_redirects=False)
    # Should 303 to the GET without touching DB
    assert response.status_code == 303


def test_unknown_action_rejected():
    mock_config = _make_mock_config()
    mock_cm, mock_get = _mock_db_context(mock_config)
    with patch("app.admin.auth.settings") as mock_settings, \
         patch("app.admin.views.ai_prompts.AsyncSessionLocal", return_value=mock_cm), \
         patch("app.admin.views.ai_prompts.get_system_config", mock_get):
        client = TestClient(app, raise_server_exceptions=False)
        _login(client, mock_settings)
        response = client.post("/admin/ai-prompts",
                               data={"field": "summarize", "action": "badaction",
                                     "instructions": "x"},
                               follow_redirects=False)
    # Should 303 to the GET without touching DB
    assert response.status_code == 303
```

- [ ] **Step 4.2: Copy test file to container and run to confirm failure**

```bash
docker cp tests/test_ai_prompts_admin.py autonewsletter-app:/app/tests/test_ai_prompts_admin.py
docker exec -w /app autonewsletter-app python -m pytest tests/test_ai_prompts_admin.py -v
```

Expected: all 12 tests FAIL with errors about missing view/route.

- [ ] **Step 4.3: Create `app/admin/views/ai_prompts.py`**

```python
# app/admin/views/ai_prompts.py
import structlog
from sqladmin import BaseView, expose
from starlette.responses import RedirectResponse
from app.database import AsyncSessionLocal
from app.repositories.system_config import get_system_config
from app.services.ai_prompts import (
    DEFAULT_SUMMARIZE_INSTRUCTIONS,
    DEFAULT_TRANSLATE_INSTRUCTIONS,
    SUMMARIZE_FIXED_SUFFIX,
)

logger = structlog.get_logger()

_COL_MAP = {"summarize": "summarize_prompt", "translate": "translate_prompt"}
_LABEL_MAP = {
    "summarize": "Summarization instructions",
    "translate": "Translation instructions",
}
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
```

- [ ] **Step 4.4: Create `app/admin/templates/sqladmin/ai_prompts.html`**

```html
{% extends "sqladmin/layout.html" %}

{% block content_header %}
<div class="container-xl">
  <div class="page-header">
    <div class="row align-items-center">
      <div class="col-auto">
        <h2 class="page-title">AI Prompts</h2>
      </div>
    </div>
  </div>
</div>
{% endblock %}

{% block content %}
<div class="container-xl">
  <div class="row row-cards">
    <div class="col-12 col-md-8">

      {% if flash %}
      <div class="alert {% if 'Error' in flash %}alert-danger{% else %}alert-success{% endif %} mb-3" role="alert">
        {{ flash }}
      </div>
      {% endif %}

      {# Translation Instructions — appears above Summarization #}
      <div class="card mb-4">
        <div class="card-body">
          <div class="d-flex align-items-center gap-2 mb-2">
            <h3 class="card-title mb-0">Translation Instructions</h3>
            {% if translate_is_default %}
            <span class="badge bg-secondary">Using app default</span>
            {% else %}
            <span class="badge bg-primary">Custom override</span>
            {% endif %}
          </div>
          <p class="text-muted mb-3">Controls how English titles are translated to Chinese.</p>
          <form method="POST">
            <input type="hidden" name="field" value="translate">
            <div class="mb-2">
              <textarea class="form-control font-monospace" name="instructions" rows="3"
                        style="resize: vertical;">{{ translate_value }}</textarea>
            </div>
            <div class="border border-dashed rounded-bottom p-2 mb-3 small text-muted font-monospace"
                 style="background:#f8f9fa;border-top:none!important">
              <span class="text-secondary">[ always appended → ]</span> {{ translate_fixed_append }}
            </div>
            <div class="d-flex gap-2">
              <button type="submit" name="action" value="save" class="btn btn-primary btn-sm">Save</button>
              <button type="submit" name="action" value="reset" class="btn btn-secondary btn-sm">↺ Reset to Default</button>
            </div>
          </form>
        </div>
      </div>

      {# Summarization Instructions #}
      <div class="card">
        <div class="card-body">
          <div class="d-flex align-items-center gap-2 mb-2">
            <h3 class="card-title mb-0">Summarization Instructions</h3>
            {% if summarize_is_default %}
            <span class="badge bg-secondary">Using app default</span>
            {% else %}
            <span class="badge bg-primary">Custom override</span>
            {% endif %}
          </div>
          <p class="text-muted mb-3">Controls the numbered rules sent to the AI for generating Chinese summaries. The JSON output schema is always appended automatically.</p>
          <form method="POST">
            <input type="hidden" name="field" value="summarize">
            <div class="mb-2">
              <textarea class="form-control font-monospace" name="instructions" rows="8"
                        style="resize: vertical;">{{ summarize_value }}</textarea>
            </div>
            <div class="border border-dashed rounded-bottom p-2 mb-3 small text-muted font-monospace"
                 style="background:#f8f9fa;border-top:none!important">
              <span class="text-secondary">[ always appended → ]</span> {{ summarize_fixed_suffix }}
            </div>
            <div class="d-flex gap-2">
              <button type="submit" name="action" value="save" class="btn btn-primary btn-sm">Save</button>
              <button type="submit" name="action" value="reset" class="btn btn-secondary btn-sm">↺ Reset to Default</button>
            </div>
          </form>
        </div>
      </div>

    </div>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 4.5: Update `app/admin/views/__init__.py`**

```python
from app.admin.views.trigger import TriggerAdmin
from app.admin.views.ai_prompts import AIPromptsAdmin
```

- [ ] **Step 4.6: Update `app/main.py`**

Add import after the existing `TriggerAdmin` import:

```python
from app.admin.views.ai_prompts import AIPromptsAdmin
```

Add `add_view` call after the existing `admin.add_view(TriggerAdmin)` line:

```python
admin.add_view(AIPromptsAdmin)
```

- [ ] **Step 4.7: Copy all files to container and run view tests**

```bash
docker cp app/admin/views/ai_prompts.py autonewsletter-app:/app/app/admin/views/ai_prompts.py
docker exec autonewsletter-app mkdir -p /app/app/admin/templates/sqladmin
docker cp app/admin/templates/sqladmin/ai_prompts.html autonewsletter-app:/app/app/admin/templates/sqladmin/ai_prompts.html
docker cp app/admin/views/__init__.py autonewsletter-app:/app/app/admin/views/__init__.py
docker cp app/main.py autonewsletter-app:/app/app/main.py
docker exec -w /app autonewsletter-app python -m pytest tests/test_ai_prompts_admin.py -v
```

Expected: 12 tests PASS.

- [ ] **Step 4.8: Run the full test suite**

```bash
docker exec -w /app autonewsletter-app python -m pytest tests/ -q
```

Expected: all tests PASS (20 existing + 6 builder + 12 view = 38 total).

- [ ] **Step 4.9: Commit**

```bash
git add app/admin/views/ai_prompts.py \
        app/admin/templates/sqladmin/ai_prompts.html \
        app/admin/views/__init__.py \
        app/main.py \
        tests/test_ai_prompts_admin.py
git commit -m "feat(admin): add AI Prompts page to edit summarization and translation instructions"
```

---

## Task 5: Smoke test in running container

- [ ] **Step 5.1: Restart container to load new code**

```bash
docker restart autonewsletter-app
sleep 5
docker logs autonewsletter-app --tail 5
```

Expected: `Application startup complete.`

- [ ] **Step 5.2: Login and verify page loads**

```bash
curl -s -c /tmp/ai_smoke.txt -b /tmp/ai_smoke.txt \
  -X POST http://localhost:8000/admin/login \
  -d "username=admin&password=<your ADMIN_PASS from .env>" \
  -o /dev/null -w "%{http_code}\n"
# Expected: 302

curl -s -c /tmp/ai_smoke.txt -b /tmp/ai_smoke.txt \
  http://localhost:8000/admin/ai-prompts \
  -o /tmp/ai_page.html -w "%{http_code}\n"
# Expected: 200

grep -o "AI Prompts\|Using app default\|Translation Instructions" /tmp/ai_page.html
# Expected: all three strings present
```

- [ ] **Step 5.3: POST a save and verify flash**

```bash
curl -s -c /tmp/ai_smoke.txt -b /tmp/ai_smoke.txt \
  -X POST http://localhost:8000/admin/ai-prompts \
  -d "field=translate&action=save&instructions=测试翻译指令" \
  -o /dev/null -w "%{http_code} %{redirect_url}\n"
# Expected: 303

curl -s -c /tmp/ai_smoke.txt -b /tmp/ai_smoke.txt \
  http://localhost:8000/admin/ai-prompts \
  -o /tmp/ai_after.html -w "%{http_code}\n"
grep -o "Translation instructions saved\|Custom override" /tmp/ai_after.html
# Expected: both present
```

- [ ] **Step 5.4: POST reset and verify badge reverts**

```bash
curl -s -c /tmp/ai_smoke.txt -b /tmp/ai_smoke.txt \
  -X POST http://localhost:8000/admin/ai-prompts \
  -d "field=translate&action=reset" \
  -o /dev/null -w "%{http_code}\n"
# Expected: 303

curl -s -c /tmp/ai_smoke.txt -b /tmp/ai_smoke.txt \
  http://localhost:8000/admin/ai-prompts \
  -o /tmp/ai_reset.html -w "%{http_code}\n"
grep -o "reset to default\|Using app default" /tmp/ai_reset.html
# Expected: both present
```

- [ ] **Step 5.5: Rebuild Docker image**

```bash
docker-compose up --build --no-deps -d app
sleep 5
docker logs autonewsletter-app --tail 5
```

Expected: `Application startup complete.`
