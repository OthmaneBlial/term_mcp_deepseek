"""Small DeepSeek client with bounded errors and no global secret state."""

from __future__ import annotations

import json
import time
from collections.abc import Iterable
from typing import Any

import requests


class DeepseekError(RuntimeError):
    pass


class DeepSeekClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-chat",
        timeout: float = 20,
        max_retries: int = 2,
        backoff: float = 0.25,
        max_tokens: int = 1024,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff = backoff
        self.max_tokens = max_tokens

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
    ) -> str:
        headers = self._headers()
        response = None
        for attempt in range(self.max_retries + 1):
            try:
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": self.max_tokens,
                        "stream": False,
                    },
                    timeout=self.timeout,
                )
            except requests.RequestException as error:
                if attempt >= self.max_retries:
                    raise DeepseekError("DeepSeek is unavailable after bounded retries") from error
                time.sleep(self.backoff * (2**attempt))
                continue
            if response.status_code != 429 and response.status_code < 500:
                break
            if attempt >= self.max_retries:
                break
            response.close()
            time.sleep(self.backoff * (2**attempt))
        if response is None:
            raise DeepseekError("DeepSeek is unavailable")
        self._raise_for_status(response)
        try:
            data = response.json()
        except requests.JSONDecodeError as error:
            raise DeepseekError("DeepSeek returned invalid JSON") from error
        try:
            return str(data["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as error:
            raise DeepseekError("DeepSeek returned an unexpected response shape") from error

    def stream(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
    ) -> Iterable[str]:
        with requests.post(
            f"{self.base_url}/chat/completions",
            headers=self._headers(),
            json={
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": self.max_tokens,
                "stream": True,
            },
            timeout=self.timeout,
            stream=True,
        ) as response:
            self._raise_for_status(response)
            for line in response.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data:"):
                    continue
                chunk = line[5:].strip()
                if chunk == "[DONE]":
                    break
                try:
                    payload: dict[str, Any] = json.loads(chunk)
                    content = payload["choices"][0]["delta"].get("content", "")
                except (json.JSONDecodeError, KeyError, IndexError, TypeError):
                    continue
                if content:
                    yield str(content)

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise DeepseekError("DEEPSEEK_API_KEY is not configured")
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _raise_for_status(response: requests.Response) -> None:
        messages = {
            401: "DeepSeek rejected the API key",
            404: "DeepSeek endpoint or model was not found",
            429: "DeepSeek rate limit or credit limit reached",
        }
        if response.status_code in messages:
            raise DeepseekError(messages[response.status_code])
        if response.status_code >= 400:
            raise DeepseekError(f"DeepSeek request failed with HTTP {response.status_code}")


def chat(
    messages,
    model: str = "deepseek-chat",
    temperature: float = 0.2,
    timeout: float = 30,
) -> str:
    """Compatibility helper; new code should instantiate DeepSeekClient."""
    import os

    return DeepSeekClient(
        api_key=os.getenv("DEEPSEEK_API_KEY", ""),
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        model=model,
        timeout=timeout,
    ).chat(messages, temperature)


__all__ = ["DeepSeekClient", "DeepseekError", "chat"]
