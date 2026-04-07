# Admin Trigger Newsletter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `/admin/trigger` page to the sqladmin admin UI with a "Run Newsletter Now" button that fires `run_weekly_newsletter()` asynchronously and shows a flash confirmation.

**Architecture:** A new `TriggerAdmin(BaseView)` in `app/admin/views/trigger.py` handles GET (render page + flash) and POST (set `app.state.trigger_running`, fire background task). A Jinja2 template at `app/admin/templates/sqladmin/trigger.html` renders inside sqladmin's layout. `app/main.py` is updated with `templates_dir`, the `trigger_running` flag in lifespan, and view registration.

**Tech Stack:** sqladmin 0.23.0 `BaseView`/`@expose`, FastAPI `app.state`, `asyncio.create_task`, Starlette `TestClient`, pytest

**Prerequisite:** This plan was validated against sqladmin 0.23.0 (`BaseView` route-name registration behaviour). `requirements.txt` currently has `sqladmin>=0.16.0`. Before starting, confirm the installed version: `docker exec autonewsletter-app python -c "import importlib.metadata; print(importlib.metadata.version('sqladmin'))"` — must print `0.23.x`. If a different version is installed, pin `sqladmin==0.23.0` in `requirements.txt` and rebuild first.

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `app/admin/views/trigger.py` | Create | `TriggerAdmin` view — GET render, POST fire/guard |
| `app/admin/templates/sqladmin/trigger.html` | Create | Page HTML inheriting sqladmin layout |
| `app/admin/views/__init__.py` | Modify | Export `TriggerAdmin` |
| `app/main.py` | Modify | Add `templates_dir`, `trigger_running`, `add_view(TriggerAdmin)` |
| `tests/test_trigger_admin.py` | Create | Three tests: unauth redirect, success flash, already-running flash |

---

### Task 1: Write failing tests

**Files:**
- Create: `tests/test_trigger_admin.py`

- [ ] **Step 1.1: Create the test file**

```python
# tests/test_trigger_admin.py
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from app.main import app


def _login(client: TestClient) -> None:
    """POST to /admin/login with default test credentials. Client stores the session cookie."""
    with patch("app.admin.auth.settings") as mock_settings:
        mock_settings.admin_user = "admin"
        mock_settings.admin_pass = "testpass"
        client.post(
            "/admin/login",
            data={"username": "admin", "password": "testpass"},
            follow_redirects=False,
        )


def test_trigger_page_requires_login():
    client = TestClient(app, raise_server_exceptions=False, follow_redirects=True)
    response = client.get("/admin/trigger")
    assert "/admin/login" in str(response.url)


def test_trigger_post_fires_task():
    with patch("app.admin.auth.settings") as mock_settings, \
         patch("app.admin.views.trigger.run_weekly_newsletter", new_callable=AsyncMock):
        mock_settings.admin_user = "admin"
        mock_settings.admin_pass = "testpass"
        client = TestClient(app, raise_server_exceptions=False)
        # Login to get session cookie
        client.post(
            "/admin/login",
            data={"username": "admin", "password": "testpass"},
            follow_redirects=False,
        )
        # Set flag manually (lifespan doesn't run in TestClient without context manager)
        app.state.trigger_running = False
        # POST trigger
        response = client.post("/admin/trigger", follow_redirects=True)
        assert response.status_code == 200
        assert "Newsletter generation started." in response.text


def test_trigger_post_already_running():
    with patch("app.admin.auth.settings") as mock_settings:
        mock_settings.admin_user = "admin"
        mock_settings.admin_pass = "testpass"
        client = TestClient(app, raise_server_exceptions=False)
        client.post(
            "/admin/login",
            data={"username": "admin", "password": "testpass"},
            follow_redirects=False,
        )
        app.state.trigger_running = True
        response = client.post("/admin/trigger", follow_redirects=True)
        assert response.status_code == 200
        assert "Already running" in response.text
        # Cleanup
        app.state.trigger_running = False
```

- [ ] **Step 1.2: Copy to container and run — verify all 3 tests fail**

```bash
docker exec autonewsletter-app mkdir -p /app/tests
docker cp tests/test_trigger_admin.py autonewsletter-app:/app/tests/test_trigger_admin.py
docker exec -w /app autonewsletter-app python -m pytest tests/test_trigger_admin.py -v
```

Expected: 3 failures. Errors like `404` for `/admin/trigger` or import errors.

---

### Task 2: Implement view, template, and wire main.py

**Files:**
- Create: `app/admin/views/trigger.py`
- Create: `app/admin/templates/sqladmin/trigger.html`
- Modify: `app/admin/views/__init__.py`
- Modify: `app/main.py`

- [ ] **Step 2.1: Create `app/admin/views/trigger.py`**

```python
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
                asyncio.create_task(
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
```

- [ ] **Step 2.2: Create the template directory and file**

```bash
mkdir -p app/admin/templates/sqladmin
```

Create `app/admin/templates/sqladmin/trigger.html`:

```html
{% extends "sqladmin/layout.html" %}

{% block content_header %}
<div class="container-xl">
  <div class="page-header">
    <div class="row align-items-center">
      <div class="col-auto">
        <h2 class="page-title">
          Trigger Newsletter
        </h2>
      </div>
    </div>
  </div>
</div>
{% endblock %}

{% block content %}
<div class="container-xl">
  <div class="row row-cards">
    <div class="col-12 col-md-6">
      <div class="card">
        <div class="card-body">
          {% if flash %}
          <div class="alert {% if 'started' in flash %}alert-success{% else %}alert-warning{% endif %} mb-3" role="alert">
            {{ flash }}
          </div>
          {% endif %}
          <p class="text-muted mb-4">This will send the newsletter to all active subscribers immediately.</p>
          <form method="POST">
            <button type="submit" class="btn btn-primary">
              <i class="fa-solid fa-paper-plane me-2"></i>Run Newsletter Now
            </button>
          </form>
        </div>
      </div>
    </div>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 2.3: Update `app/admin/views/__init__.py`**

```python
from app.admin.views.trigger import TriggerAdmin
```

- [ ] **Step 2.4: Update `app/main.py`**

Replace the `Admin(...)` line (currently line 100):

```python
admin = Admin(app, engine, authentication_backend=authentication_backend,
              templates_dir="app/admin/templates")
```

Add `TriggerAdmin` import alongside the other view imports:

```python
from app.admin.views.trigger import TriggerAdmin
```

Add `trigger_running` initialisation in `lifespan`, after the scheduler lines (after `logger.info("scheduler_ready")`... actually place it right after `app.state.scheduler = scheduler`):

```python
    app.state.scheduler = scheduler
    app.state.trigger_running = False
    scheduler.start()
```

Add `admin.add_view(TriggerAdmin)` after the existing `add_view` calls (line 105):

```python
admin.add_view(TriggerAdmin)
```

- [ ] **Step 2.5: Copy all new/modified files to container**

```bash
docker cp app/admin/views/trigger.py autonewsletter-app:/app/app/admin/views/trigger.py
docker cp app/admin/views/__init__.py autonewsletter-app:/app/app/admin/views/__init__.py
docker exec autonewsletter-app mkdir -p /app/app/admin/templates/sqladmin
docker cp app/admin/templates/sqladmin/trigger.html autonewsletter-app:/app/app/admin/templates/sqladmin/trigger.html
docker cp app/main.py autonewsletter-app:/app/app/main.py
```

- [ ] **Step 2.6: Run all tests — verify all 3 pass**

```bash
docker exec -w /app autonewsletter-app python -m pytest tests/test_trigger_admin.py -v
```

Expected:
```
tests/test_trigger_admin.py::test_trigger_page_requires_login PASSED
tests/test_trigger_admin.py::test_trigger_post_fires_task PASSED
tests/test_trigger_admin.py::test_trigger_post_already_running PASSED
3 passed
```

- [ ] **Step 2.7: Run full test suite — verify no regressions**

First ensure all test files and pytest.ini are present in the container (they may already be there from prior sessions — run anyway to be safe):

```bash
docker exec autonewsletter-app mkdir -p /app/tests
docker cp pytest.ini autonewsletter-app:/app/pytest.ini
docker cp tests/conftest.py autonewsletter-app:/app/tests/conftest.py
docker cp tests/test_admin_auth.py autonewsletter-app:/app/tests/test_admin_auth.py
docker cp tests/test_sources_module.py autonewsletter-app:/app/tests/test_sources_module.py
docker cp tests/test_system_config_repo.py autonewsletter-app:/app/tests/test_system_config_repo.py
docker cp tests/test_trigger_auth.py autonewsletter-app:/app/tests/test_trigger_auth.py
docker cp tests/test_trigger_admin.py autonewsletter-app:/app/tests/test_trigger_admin.py
```

Then run:

```bash
docker exec -w /app autonewsletter-app python -m pytest tests/ -v
```

Expected: all 20 tests pass (17 existing + 3 new).

- [ ] **Step 2.8: Commit**

```bash
git add app/admin/views/trigger.py \
        app/admin/views/__init__.py \
        app/admin/templates/sqladmin/trigger.html \
        app/main.py \
        tests/test_trigger_admin.py
git commit -m "feat(admin): add trigger newsletter page with async fire-and-forget"
```

---

### Task 3: End-to-end smoke test

- [ ] **Step 3.1: Restart container with latest code**

```bash
docker-compose up --build --no-deps -d app
```

Wait for `scheduler_ready` in logs:

```bash
sleep 5 && docker logs autonewsletter-app --tail 5
```

- [ ] **Step 3.2: Verify `/admin/trigger` appears in nav**

```bash
curl -s -c /tmp/smoke_cookies.txt -b /tmp/smoke_cookies.txt \
  -X POST http://localhost:8000/admin/login \
  -d "username=admin&password=<YOUR_ADMIN_PASS>" \
  -o /dev/null -w "%{http_code}\n"
# Expected: 302

curl -s -c /tmp/smoke_cookies.txt -b /tmp/smoke_cookies.txt \
  http://localhost:8000/admin/trigger \
  -o /tmp/trigger_page.html -w "%{http_code}\n"
# Expected: 200

grep -o "Run Newsletter Now\|Trigger Newsletter" /tmp/trigger_page.html
# Expected: both strings present
```

- [ ] **Step 3.3: POST trigger and verify flash**

```bash
curl -s -c /tmp/smoke_cookies.txt -b /tmp/smoke_cookies.txt \
  -X POST http://localhost:8000/admin/trigger \
  -o /dev/null -w "%{http_code} %{redirect_url}\n"
# Expected: 303 http://localhost:8000/admin/trigger

curl -s -c /tmp/smoke_cookies.txt -b /tmp/smoke_cookies.txt \
  http://localhost:8000/admin/trigger \
  -o /tmp/trigger_after.html -w "%{http_code}\n"

grep "Newsletter generation started\|Already running" /tmp/trigger_after.html
# Expected: one of those strings
```

- [ ] **Step 3.4: Check logs for pipeline activity**

```bash
docker logs autonewsletter-app --tail 20
# Expected: manual_trigger_requested or weekly_pipeline_starting event
```
