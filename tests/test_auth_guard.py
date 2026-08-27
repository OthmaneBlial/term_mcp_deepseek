import pytest

from tools.auth import BearerTokenAuth, JWTAuth


def test_jwt_round_trip():
    auth = JWTAuth("test-secret-that-is-at-least-32-bytes")
    token = auth.create("developer", ttl_seconds=60)

    claims = auth.verify(token)

    assert claims["sub"] == "developer"
    assert claims["iss"] == "term-mcp"


def test_bearer_auth_uses_constant_shape_and_rejects_wrong_scheme():
    token = "local-token-that-is-longer-than-thirty-two-characters"
    auth = BearerTokenAuth(token)

    assert auth.verify_header(f"Bearer {token}") is True
    assert auth.verify_header(f"Basic {token}") is False
    assert auth.verify_header("Bearer wrong") is False


def test_short_bearer_token_is_rejected():
    with pytest.raises(ValueError, match="32"):
        BearerTokenAuth("too-short")
