# tests/test_trigger_auth.py
import pytest
import base64
from unittest.mock import patch, AsyncMock


def make_auth_header(user, password):
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def test_trigger_requires_auth():
    with patch("app.main.settings") as mock_settings:
        mock_settings.admin_user = "admin"
        mock_settings.admin_pass = "secret"
        mock_settings.admin_session_secret = "test"
        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post("/trigger")
        assert response.status_code == 401


def test_trigger_accepts_correct_credentials():
    with patch("app.main.settings") as mock_settings, \
         patch("app.main.run_weekly_newsletter", new_callable=AsyncMock) as mock_run:
        mock_settings.admin_user = "admin"
        mock_settings.admin_pass = "secret"
        mock_settings.admin_session_secret = "test"
        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post("/trigger", headers=make_auth_header("admin", "secret"))
        assert response.status_code == 200
        mock_run.assert_called_once()


def test_health_no_auth_required():
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/health")
    assert response.status_code == 200
