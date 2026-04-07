# Admin Trigger Newsletter — Design Spec

**Date:** 2026-04-07
**Status:** Approved

## Overview

Add a "Trigger Newsletter" page to the sqladmin admin UI (`/admin/trigger`) that lets an authenticated admin manually fire the weekly newsletter pipeline without leaving the browser. The trigger is async (fire-and-forget). A process-local `asyncio.Lock` prevents double-click duplicates from `/admin/trigger` only — overlap with the cron scheduler or the Basic-Auth `/trigger` endpoint is out of scope and not prevented by this feature.

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
  1. Reads `lock = self._admin_ref.app.state.trigger_lock` (an `asyncio.Lock`). If not present, logs a warning, sets `session["flash"] = "Trigger unavailable."`, and redirects 303.
  2. Tries a **non-blocking acquire**: `acquired = lock.acquire_nowait()` (or `not lock.locked()` then `lock._value` check — use `asyncio.Lock` internals carefully; preferred: attempt `loop.call_soon(lock.acquire)` or use a simple boolean flag). **Correct pattern**: call `acquired = not lock.locked()` is still racy. The safe approach is to use a separate `asyncio.Event` or a plain `bool` flag stored on `app.state` (`trigger_running: bool`), set it atomically in a single-threaded async context before `create_task`. Since the event loop is single-threaded, reading and setting `app.state.trigger_running` in the same coroutine before yielding is race-free.
  3. If `trigger_running` is `True`: sets `session["flash"] = "Already running — please wait."` and redirects 303.
  4. If `False`: sets `app.state.trigger_running = True`, creates the background task, sets `session["flash"] = "Newsletter generation started."`, and redirects 303.

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

The `except` block ensures unobserved-task exceptions are logged (not silently dropped), and `finally` always clears the flag.

In `lifespan`, initialise: `app.state.trigger_running = False`.

### Template: `app/admin/templates/sqladmin/trigger.html`

- Extends `sqladmin/layout.html`
- Override the **`content`** block (not `body`) — sqladmin page content belongs in `{% block content %}`.
- Override the **`content_header`** block for the page title.
- Body of `content` block contains:
  - Flash message banner (shown if `flash` is set).
  - `<form method="POST">` with a "Run Newsletter Now" submit button.
  - Small note: "This will send to all active subscribers immediately."

### Changes to `app/main.py`

1. `Admin(app, engine, ..., templates_dir="app/admin/templates")` — sqladmin's Jinja2 loader is rooted here; the template is found at `sqladmin/trigger.html` relative to this root.
2. In `lifespan`, after scheduler setup: `app.state.trigger_running = False`.
3. `admin.add_view(TriggerAdmin)` alongside existing views.
4. Import `TriggerAdmin` from `app.admin.views.trigger`.

### Auth

`sqladmin`'s `authentication_backend` wraps all `@expose` routes with `login_required`. No additional auth code needed. Unauthenticated requests are redirected to `/admin/login`.

### Route

`/admin/trigger`. Does not collide with the existing top-level `POST /trigger` Basic-Auth endpoint.

### Single-process assumption

`trigger_running` is a Python object on `app.state` — it is process-local. With multiple uvicorn workers or replicas the flag would not be shared. This app currently runs as a single worker (`uvicorn app.main:app`) so this is acceptable.

## Error Handling

- Unobserved task exceptions: caught by `except Exception` in `_run_and_clear`, logged via structlog, flag cleared in `finally`.
- Missing `trigger_running` on `app.state` (startup failure): POST logs a warning and returns an error flash rather than crashing.
- `run_weekly_newsletter()` existing error handling (top-level `try/except` + re-raise) is preserved; `_run_and_clear`'s `except` catches the re-raised exception.

## Testing

Three tests in `tests/test_trigger_admin.py`:

- `test_trigger_page_requires_login` — unauthenticated GET `/admin/trigger` returns 302 to `/admin/login`. Uses `TestClient` with no session cookie.
- `test_trigger_post_fires_task` — authenticated POST (mock session with `token=authenticated`). Mocks `run_weekly_newsletter`. Asserts 303 redirect, `trigger_running` set to `True` before task completes, flash message in session.
- `test_trigger_post_already_running` — authenticated POST while `app.state.trigger_running = True`. Asserts 303 redirect, flash = `"Already running — please wait."`, no second task created.

Admin login state in tests is established by pre-seeding the session cookie (same pattern as `test_trigger_auth.py`: patch `app.main.settings`).

## Files Changed

| File | Change |
|------|--------|
| `app/admin/views/trigger.py` | Create |
| `app/admin/templates/sqladmin/trigger.html` | Create |
| `app/admin/views/__init__.py` | Export `TriggerAdmin` |
| `app/main.py` | Add `templates_dir`, `trigger_running`, `add_view(TriggerAdmin)` |
| `tests/test_trigger_admin.py` | Create |
