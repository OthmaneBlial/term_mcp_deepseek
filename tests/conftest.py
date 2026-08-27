from __future__ import annotations

import pytest

from term_mcp_deepseek.app import create_app
from term_mcp_deepseek.config import Settings


@pytest.fixture
def app(tmp_path):
    settings = Settings(
        workspace_root=str(tmp_path),
        secret_key="test-secret",
        jwt_secret="test-jwt-secret",
    )
    application = create_app(settings=settings, overrides={"TESTING": True})
    yield application
    application.close_term_mcp()


@pytest.fixture
def client(app):
    return app.test_client()
