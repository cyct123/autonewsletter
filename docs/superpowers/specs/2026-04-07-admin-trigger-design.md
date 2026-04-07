# Admin Trigger Newsletter — Design Spec

**Date:** 2026-04-07
**Status:** Approved

## Overview

Add a "Trigger Newsletter" page to the sqladmin admin UI (`/admin/trigger`) that lets an authenticated admin manually fire the weekly newsletter pipeline without leaving the browser. The trigger is async (fire-and-forget). A process-local boolean flag prevents double-click duplicates from `/admin/trigger` within the same process. Overlap with the cron scheduler or the Basic-Auth `/trigger` endpoint is out of scope and not prevented by this feature.

## Architecture

### New file: `app/admin/views/trigger.py`

```python
class TriggerAdmin(BaseView):
    name = "Trigger Newsletter"
    icon = "fa-solid fa-paper-plane"

    @expose("/trigger", methods=["GET", "POST"])
    async def trigger_page(self, request): ...
```

Route behaviour:

- **GET**: Renders `sqladmin/trigger.html`. Pops `session["flash"]` and passes it as `flash` to the template context (shown once, cleared on read).
- **POST**:
  1. Reads `outer_app = self._admin_ref.app` (same pattern as `system_config.py`).
  2. Checks `outer_app.state.trigger_running`. If `True`: sets `session["flash"] = "Already running — please wait."` and redirects 303.
  3. If `False`: sets `outer_app.state.trigger_running = True`, creates the background task via `asyncio.create_task(_run_and_clear(run_weekly_newsletter, outer_app.state))`, sets `session["flash"] = "Newsletter generation started."`, and redirects 303.
  4. If `trigger_running` is not present on `app.state` (startup failure), logs a warning and redirects 303 with `session["flash"] = "Trigger unavailable — check logs."`.

Because the asyncio event loop is single-threaded, reading and writing `app.state.trigger_running` in the same coroutine before any `await` is race-free.

Background task wrapper:

```python
async def _run_and_clear(fn, app_state):
    try:
        await fn()
    except Exception:
        logger.error("trigger_task_failed", exc_info=True)
    finally:
        app_state.trigger_running = False
```

The `except` block ensures unobserved-task exceptions are logged rather than silently dropped; `finally` always resets the flag.

### Template: `app/admin/templates/sqladmin/trigger.html`

- Extends `sqladmin/layout.html`
- Override `{% block content_header %}` for the page title ("Trigger Newsletter").
- Override `{% block content %}` (not `body`) for page body:
  - Flash message banner (shown if `flash` is set).
  - `<form method="POST">` with a "Run Newsletter Now" submit button.
  - Small note: "This will send to all active subscribers immediately."

### Changes to `app/main.py`

1. `Admin(app, engine, ..., templates_dir="app/admin/templates")` — sqladmin's Jinja2 loader roots here; the template is found at `sqladmin/trigger.html` relative to this root, falling back to sqladmin's packaged templates for everything else.
2. In `lifespan`, after scheduler setup: `app.state.trigger_running = False`.
3. `admin.add_view(TriggerAdmin)` alongside existing views.
4. Import `TriggerAdmin` from `app.admin.views.trigger`.

### Auth

`sqladmin`'s `authentication_backend` wraps all `@expose` routes with `login_required`. Unauthenticated requests are redirected to `/admin/login`. No additional auth code needed.

### Route

`/admin/trigger`. Does not collide with the existing top-level `POST /trigger` Basic-Auth endpoint.

### Single-process assumption

`trigger_running` is a Python object on `app.state` — it is process-local. The Docker deployment (`docker-compose`) runs a single uvicorn worker and is the primary deployment target, so this is acceptable. The non-Docker production command in `start.sh` uses `--workers 4`; with multiple workers the flag is not shared and the guard does not prevent cross-worker duplicates. That limitation is acceptable for an admin convenience feature.

## Error Handling

- Unobserved task exceptions: caught by `except Exception` in `_run_and_clear`, logged via structlog, flag reset in `finally`.
- Missing `trigger_running` on `app.state` (startup failure): POST logs a warning and redirects with an error flash rather than crashing.
- `run_weekly_newsletter()`'s existing top-level `try/except` + re-raise is preserved; `_run_and_clear`'s `except` catches the re-raised exception at the task boundary.

## Testing

Three tests in `tests/test_trigger_admin.py`:

- `test_trigger_page_requires_login` — unauthenticated GET `/admin/trigger` follows the redirect and asserts the final URL contains `/admin/login`. Uses `TestClient(app, raise_server_exceptions=False)`.
- `test_trigger_post_fires_task` — logs in via POST `/admin/login` (with `admin_pass` patched) to obtain a real signed session cookie, then POST `/admin/trigger`. Mocks `run_weekly_newsletter`. Asserts 303 redirect and `session["flash"] = "Newsletter generation started."`.
- `test_trigger_post_already_running` — same login flow, sets `app.state.trigger_running = True` before POSTing. Asserts 303 redirect and `session["flash"] = "Already running — please wait."`.

## Files Changed

| File | Change |
|------|--------|
| `app/admin/views/trigger.py` | Create |
| `app/admin/templates/sqladmin/trigger.html` | Create |
| `app/admin/views/__init__.py` | Export `TriggerAdmin` |
| `app/main.py` | Add `templates_dir`, `trigger_running`, `add_view(TriggerAdmin)` |
| `tests/test_trigger_admin.py` | Create |
