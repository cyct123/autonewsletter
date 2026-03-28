# tests/test_admin_auth.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.admin.auth import AdminAuth

pytestmark = pytest.mark.asyncio


async def test_authenticate_returns_true_when_token_set():
    auth = AdminAuth(secret_key="test")
    request = MagicMock()
    request.session = {"token": "authenticated"}
    assert await auth.authenticate(request) is True


async def test_authenticate_returns_false_when_no_token():
    auth = AdminAuth(secret_key="test")
    request = MagicMock()
    request.session = {}
    assert await auth.authenticate(request) is False


async def test_login_succeeds_with_correct_credentials():
    auth = AdminAuth(secret_key="test")
    request = AsyncMock()
    request.session = {}
    form_data = {"username": "admin", "password": "secret"}
    request.form = AsyncMock(return_value=form_data)

    with patch("app.admin.auth.settings") as mock_settings:
        mock_settings.admin_user = "admin"
        mock_settings.admin_pass = "secret"
        result = await auth.login(request)

    assert result is True
    assert request.session["token"] == "authenticated"


async def test_login_fails_with_wrong_password():
    auth = AdminAuth(secret_key="test")
    request = AsyncMock()
    request.session = {}
    form_data = {"username": "admin", "password": "wrong"}
    request.form = AsyncMock(return_value=form_data)

    with patch("app.admin.auth.settings") as mock_settings:
        mock_settings.admin_user = "admin"
        mock_settings.admin_pass = "secret"
        result = await auth.login(request)

    assert result is False
    assert "token" not in request.session


async def test_logout_clears_session():
    auth = AdminAuth(secret_key="test")
    request = MagicMock()
    request.session = {"token": "authenticated"}
    await auth.logout(request)
    assert request.session == {}
