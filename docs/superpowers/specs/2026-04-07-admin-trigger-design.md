# Admin Trigger Newsletter — Design Spec

**Date:** 2026-04-07
**Status:** Approved

## Overview

Add a "Trigger Newsletter" page to the sqladmin admin UI (`/admin/trigger`) that lets an authenticated admin manually fire the weekly newsletter pipeline without leaving the browser. The trigger is async (fire-and-forget) with a concurrency lock to prevent duplicate runs.

## Architecture

### New file: `app/admin/views/trigger.py`

A `TriggerAdmin(BaseView)` with a single `@expose("/trigger", methods=["GET", "POST"])` route:

- **GET**: Renders `trigger.html`. Pops any `"flash"` key from the session and passes it to the template (shown once after a POST).
- **POST**:
  - Reads `self._admin_ref.app.state.trigger_lock` (an `asyncio.Lock`).
  - If the lock is already held: sets `session["flash"] = "Already running."` and redirects 303.
  - If the lock is free: wraps `run_weekly_newsletter()` in a helper that acquires the lock, creates the task with `asyncio.create_task()`, sets `session["flash"] = "Newsletter generation started."`, and redirects 303.

Lock acquire/release pattern (inside the coroutine passed to `create_task`):

```python
async def _run_locked(lock, fn):
    async with lock:
        await fn()
```

This ensures the lock is released even if `run_weekly_newsletter()` raises.

### Template: `app/admin/templates/sqladmin/trigger.html`

Extends `sqladmin/layout.html`. Body contains:
- A flash message banner (shown if `flash` is set).
- A single `<form method="POST">` with a "Run Newsletter Now" submit button.
- A note: "This will send to all active subscribers immediately."

### Changes to `app/main.py`

1. `Admin(app, engine, ..., templates_dir="app/admin/templates")` — enables custom templates.
2. In `lifespan`, after creating the scheduler: `app.state.trigger_lock = asyncio.Lock()`.
3. `admin.add_view(TriggerAdmin)` alongside the existing views.

### Auth

`sqladmin`'s `authentication_backend` wraps all `@expose` routes with `login_required`. No additional auth code needed.

### Route

The exposed route lands at `/admin/trigger` (sqladmin prepends `/admin` to BaseView routes). This does not collide with the existing top-level `POST /trigger` endpoint.

## Error Handling

- If `run_weekly_newsletter()` raises, the exception is caught inside the job and logged (existing behaviour in `weekly_newsletter.py`). The unobserved-task-exception problem is mitigated by the existing `try/except` at the top of the pipeline.
- If `trigger_lock` is not found on `app.state` (e.g. startup failed), the POST falls through to a logged warning and redirects with an error flash.

## Testing

One integration test in `tests/test_trigger_admin.py`:

- `test_trigger_page_requires_login` — unauthenticated GET `/admin/trigger` returns 302 to `/admin/login`.
- `test_trigger_post_fires_task` — authenticated POST mocks `asyncio.create_task` and `run_weekly_newsletter`, asserts 303 redirect and flash in session.
- `test_trigger_post_locked` — authenticated POST while lock is held returns 303 with "Already running." flash.

## Files Changed

| File | Change |
|------|--------|
| `app/admin/views/trigger.py` | Create |
| `app/admin/templates/sqladmin/trigger.html` | Create |
| `app/admin/views/__init__.py` | Export `TriggerAdmin` |
| `app/main.py` | Add `templates_dir`, `trigger_lock`, `add_view(TriggerAdmin)` |
| `tests/test_trigger_admin.py` | Create |
