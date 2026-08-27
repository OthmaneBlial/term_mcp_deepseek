from __future__ import annotations

import pytest

from term_mcp_deepseek.app import create_app
from term_mcp_deepseek.config import Settings

TEST_TOKEN = "test-token-that-is-longer-than-thirty-two-characters"


@pytest.fixture
def app(tmp_path):
    settings = Settings(
        workspace_root=str(tmp_path),
        secret_key="test-secret",
        jwt_secret="test-jwt-secret",
        auth_token=TEST_TOKEN,
        allowed_origins=("http://localhost:8000",),
    )
    application = create_app(settings=settings, overrides={"TESTING": True})
    yield application
    application.close_term_mcp()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_headers():
    return {"Authorization": f"Bearer {TEST_TOKEN}"}
