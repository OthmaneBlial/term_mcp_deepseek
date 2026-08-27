import pytest

from term_mcp_deepseek.app import create_app
from term_mcp_deepseek.config import Settings


def test_http_config_fails_closed_without_token(tmp_path):
    settings = Settings(workspace_root=str(tmp_path), auth_token="")

    assert "AUTH_TOKEN" in settings.validate_for_http()[0]
    with pytest.raises(ValueError, match="AUTH_TOKEN"):
        create_app(settings=settings)


def test_wildcard_origin_is_rejected(tmp_path):
    settings = Settings(
        workspace_root=str(tmp_path),
        auth_token="a" * 32,
        allowed_origins=("*",),
    )

    assert any("wildcard" in error for error in settings.validate_for_http())
