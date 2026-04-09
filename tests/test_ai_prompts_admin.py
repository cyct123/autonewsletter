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
    response = client.post(
        "/admin/ai-prompts",
        data={"field": "summarize", "action": "save", "instructions": "test"}
    )
    assert "/admin/login" in str(response.url)


def test_ai_prompts_get_shows_defaults():
    mock_config = _make_mock_config()
    mock_cm, mock_get_config = _mock_db_context(mock_config)

    with patch("app.admin.views.ai_prompts.AsyncSessionLocal", return_value=mock_cm), \
         patch("app.admin.views.ai_prompts.get_system_config", mock_get_config), \
         patch("app.admin.auth.settings") as mock_settings:
        client = TestClient(app, raise_server_exceptions=False)
        _login(client, mock_settings)
        response = client.get("/admin/ai-prompts")

    assert response.status_code == 200
    assert "Using app default" in response.text
    assert "用中文输出" in response.text
    assert "将以下标题精准翻译为中文标题" in response.text


def test_ai_prompts_get_shows_custom():
    mock_config = _make_mock_config(
        summarize_prompt="custom summarize",
        translate_prompt="custom translate"
    )
    mock_cm, mock_get_config = _mock_db_context(mock_config)

    with patch("app.admin.views.ai_prompts.AsyncSessionLocal", return_value=mock_cm), \
         patch("app.admin.views.ai_prompts.get_system_config", mock_get_config), \
         patch("app.admin.auth.settings") as mock_settings:
        client = TestClient(app, raise_server_exceptions=False)
        _login(client, mock_settings)
        response = client.get("/admin/ai-prompts")

    assert response.status_code == 200
    assert "Custom override" in response.text
    assert "custom summarize" in response.text
    assert "custom translate" in response.text


def test_ai_prompts_post_save_summarize():
    mock_config = _make_mock_config()
    mock_cm, mock_get_config = _mock_db_context(mock_config)

    with patch("app.admin.views.ai_prompts.AsyncSessionLocal", return_value=mock_cm), \
         patch("app.admin.views.ai_prompts.get_system_config", mock_get_config), \
         patch("app.admin.auth.settings") as mock_settings:
        client = TestClient(app, raise_server_exceptions=False)
        _login(client, mock_settings)
        response = client.post(
            "/admin/ai-prompts",
            data={"field": "summarize", "action": "save", "instructions": "new instructions"},
            follow_redirects=False
        )

    assert response.status_code == 303
    assert mock_config.summarize_prompt == "new instructions"
    mock_cm.__aenter__.return_value.commit.assert_called_once()


def test_ai_prompts_post_save_translate():
    mock_config = _make_mock_config()
    mock_cm, mock_get_config = _mock_db_context(mock_config)

    with patch("app.admin.views.ai_prompts.AsyncSessionLocal", return_value=mock_cm), \
         patch("app.admin.views.ai_prompts.get_system_config", mock_get_config), \
         patch("app.admin.auth.settings") as mock_settings:
        client = TestClient(app, raise_server_exceptions=False)
        _login(client, mock_settings)
        response = client.post(
            "/admin/ai-prompts",
            data={"field": "translate", "action": "save", "instructions": "new translate"},
            follow_redirects=False
        )

    assert response.status_code == 303
    assert mock_config.translate_prompt == "new translate"


def test_ai_prompts_post_reset_summarize():
    mock_config = _make_mock_config(summarize_prompt="old custom")
    mock_cm, mock_get_config = _mock_db_context(mock_config)

    with patch("app.admin.views.ai_prompts.AsyncSessionLocal", return_value=mock_cm), \
         patch("app.admin.views.ai_prompts.get_system_config", mock_get_config), \
         patch("app.admin.auth.settings") as mock_settings:
        client = TestClient(app, raise_server_exceptions=False)
        _login(client, mock_settings)
        response = client.post(
            "/admin/ai-prompts",
            data={"field": "summarize", "action": "reset"},
            follow_redirects=False
        )

    assert response.status_code == 303
    assert mock_config.summarize_prompt is None


def test_ai_prompts_post_reset_translate():
    mock_config = _make_mock_config(translate_prompt="old custom")
    mock_cm, mock_get_config = _mock_db_context(mock_config)

    with patch("app.admin.views.ai_prompts.AsyncSessionLocal", return_value=mock_cm), \
         patch("app.admin.views.ai_prompts.get_system_config", mock_get_config), \
         patch("app.admin.auth.settings") as mock_settings:
        client = TestClient(app, raise_server_exceptions=False)
        _login(client, mock_settings)
        response = client.post(
            "/admin/ai-prompts",
            data={"field": "translate", "action": "reset"},
            follow_redirects=False
        )

    assert response.status_code == 303
    assert mock_config.translate_prompt is None


def test_ai_prompts_post_empty_string_becomes_none():
    mock_config = _make_mock_config()
    mock_cm, mock_get_config = _mock_db_context(mock_config)

    with patch("app.admin.views.ai_prompts.AsyncSessionLocal", return_value=mock_cm), \
         patch("app.admin.views.ai_prompts.get_system_config", mock_get_config), \
         patch("app.admin.auth.settings") as mock_settings:
        client = TestClient(app, raise_server_exceptions=False)
        _login(client, mock_settings)
        response = client.post(
            "/admin/ai-prompts",
            data={"field": "summarize", "action": "save", "instructions": "   "},
            follow_redirects=False
        )

    assert response.status_code == 303
    assert mock_config.summarize_prompt is None


def test_ai_prompts_post_invalid_field():
    mock_config = _make_mock_config()
    mock_cm, mock_get_config = _mock_db_context(mock_config)

    with patch("app.admin.views.ai_prompts.AsyncSessionLocal", return_value=mock_cm), \
         patch("app.admin.views.ai_prompts.get_system_config", mock_get_config), \
         patch("app.admin.auth.settings") as mock_settings:
        client = TestClient(app, raise_server_exceptions=False)
        _login(client, mock_settings)
        response = client.post(
            "/admin/ai-prompts",
            data={"field": "invalid", "action": "save", "instructions": "test"},
            follow_redirects=False
        )

    assert response.status_code == 303
    mock_cm.__aenter__.return_value.commit.assert_not_called()


def test_ai_prompts_post_invalid_action():
    mock_config = _make_mock_config()
    mock_cm, mock_get_config = _mock_db_context(mock_config)

    with patch("app.admin.views.ai_prompts.AsyncSessionLocal", return_value=mock_cm), \
         patch("app.admin.views.ai_prompts.get_system_config", mock_get_config), \
         patch("app.admin.auth.settings") as mock_settings:
        client = TestClient(app, raise_server_exceptions=False)
        _login(client, mock_settings)
        response = client.post(
            "/admin/ai-prompts",
            data={"field": "summarize", "action": "delete", "instructions": "test"},
            follow_redirects=False
        )

    assert response.status_code == 303
    mock_cm.__aenter__.return_value.commit.assert_not_called()


def test_ai_prompts_post_too_long_summarize():
    mock_config = _make_mock_config()
    mock_cm, mock_get_config = _mock_db_context(mock_config)

    with patch("app.admin.views.ai_prompts.AsyncSessionLocal", return_value=mock_cm), \
         patch("app.admin.views.ai_prompts.get_system_config", mock_get_config), \
         patch("app.admin.auth.settings") as mock_settings:
        client = TestClient(app, raise_server_exceptions=False)
        _login(client, mock_settings)
        response = client.post(
            "/admin/ai-prompts",
            data={"field": "summarize", "action": "save", "instructions": "x" * 4001},
            follow_redirects=False
        )

    assert response.status_code == 303
    mock_cm.__aenter__.return_value.rollback.assert_called_once()


def test_ai_prompts_post_too_long_translate():
    mock_config = _make_mock_config()
    mock_cm, mock_get_config = _mock_db_context(mock_config)

    with patch("app.admin.views.ai_prompts.AsyncSessionLocal", return_value=mock_cm), \
         patch("app.admin.views.ai_prompts.get_system_config", mock_get_config), \
         patch("app.admin.auth.settings") as mock_settings:
        client = TestClient(app, raise_server_exceptions=False)
        _login(client, mock_settings)
        response = client.post(
            "/admin/ai-prompts",
            data={"field": "translate", "action": "save", "instructions": "T" * 501},
            follow_redirects=False
        )

    assert response.status_code == 303
    mock_cm.__aenter__.return_value.rollback.assert_called_once()
