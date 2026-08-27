from tools.auth import JWTAuth


def test_jwt_round_trip():
    auth = JWTAuth("test-secret-that-is-at-least-32-bytes")
    token = auth.create("developer", ttl_seconds=60)

    claims = auth.verify(token)

    assert claims["sub"] == "developer"
    assert claims["iss"] == "term-mcp"
