import pytest
import requests

from tools.deepseek_client import DeepSeekClient, DeepseekError


class FakeResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self.payload = payload or {}
        self.closed = False

    def json(self):
        return self.payload

    def close(self):
        self.closed = True


def test_missing_key_is_explicit_and_never_calls_network(monkeypatch):
    client = DeepSeekClient("")
    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: pytest.fail("network called"))

    assert client.available is False
    with pytest.raises(DeepseekError, match="not configured"):
        client.chat([{"role": "user", "content": "hello"}])


def test_retry_backoff_timeout_and_token_budget_are_bounded(monkeypatch):
    responses = [
        FakeResponse(503),
        FakeResponse(200, {"choices": [{"message": {"content": "safe answer"}}]}),
    ]
    calls = []
    sleeps = []

    def fake_post(*args, **kwargs):
        calls.append(kwargs)
        return responses.pop(0)

    monkeypatch.setattr(requests, "post", fake_post)
    monkeypatch.setattr("tools.deepseek_client.time.sleep", sleeps.append)
    client = DeepSeekClient(
        "secret",
        timeout=3,
        max_retries=1,
        backoff=0.1,
        max_tokens=256,
    )

    assert client.chat([{"role": "user", "content": "hello"}]) == "safe answer"
    assert len(calls) == 2
    assert calls[0]["timeout"] == 3
    assert calls[0]["json"]["max_tokens"] == 256
    assert sleeps == [0.1]


def test_provider_errors_are_sanitized_after_bounded_retries(monkeypatch):
    attempts = []

    def unavailable(*_args, **_kwargs):
        attempts.append(1)
        raise requests.ConnectionError("private upstream details")

    monkeypatch.setattr(requests, "post", unavailable)
    monkeypatch.setattr("tools.deepseek_client.time.sleep", lambda _delay: None)
    client = DeepSeekClient("secret", max_retries=2)

    with pytest.raises(DeepseekError, match="bounded retries") as raised:
        client.chat([{"role": "user", "content": "hello"}])

    assert len(attempts) == 3
    assert "private upstream details" not in str(raised.value)
