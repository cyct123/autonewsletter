# tests/test_trigger_admin.py
import asyncio
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from app.main import app


def test_trigger_page_requires_login():
    client = TestClient(app, raise_server_exceptions=False, follow_redirects=True)
    response = client.get("/admin/trigger")
    assert "/admin/login" in str(response.url)


def test_trigger_post_fires_task():
    with patch("app.admin.auth.settings") as mock_settings, \
         patch("app.admin.views.trigger.run_weekly_newsletter", new_callable=AsyncMock) as mock_run, \
         patch("app.admin.views.trigger.asyncio.create_task") as mock_create_task:
        mock_settings.admin_user = "admin"
        mock_settings.admin_pass = "testpass"
        scheduled = []

        def capture_task(coro):
            scheduled.append(coro)
            return object()

        mock_create_task.side_effect = capture_task
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
        assert len(scheduled) == 1
        asyncio.run(scheduled.pop())
        mock_run.assert_called_once()
        assert app.state.trigger_running is False


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
