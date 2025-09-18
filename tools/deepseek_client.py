# -*- coding: utf-8 -*-
import os, json, requests
from typing import Iterable, Optional

DEEPSEEK_BASE = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_KEY  = os.getenv("DEEPSEEK_API_KEY")  # set in .env, DO NOT hardcode

class DeepseekError(RuntimeError): ...

def _headers():
    if not DEEPSEEK_KEY:
        raise DeepseekError("missing DEEPSEEK_API_KEY")
    return {
        "Authorization": f"Bearer {DEEPSEEK_KEY}",
        "Content-Type": "application/json",
    }

def chat(messages, model="deepseek-chat", temperature=0.7, timeout=30) -> str:
    """
    Non-streaming chat completion. Raises DeepseekError on 4xx/5xx.
    """
    url = f"{DEEPSEEK_BASE.rstrip('/')}/v1/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "stream": False
    }
    r = requests.post(url, headers=_headers(), json=payload, timeout=timeout)
    if r.status_code == 401:
        raise DeepseekError("401 unauthorized: invalid/expired key, wrong project, or unpaid account")
    if r.status_code == 404:
        raise DeepseekError("404 endpoint/model: check base URL and model name")
    if r.status_code == 429:
        raise DeepseekError("429 rate limit or insufficient credits")
    if r.status_code >= 400:
        raise DeepseekError(f"{r.status_code} {r.text}")
    data = r.json()
    try:
        return data["choices"][0]["message"]["content"]
    except Exception:
        raise DeepseekError(f"unexpected response: {json.dumps(data)[:500]}")

def stream(messages, model="deepseek-chat", temperature=0.7, timeout=30) -> Iterable[str]:
    """
    Streaming chat completion. Yields text deltas.
    """
    url = f"{DEEPSEEK_BASE.rstrip('/')}/v1/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "stream": True
    }
    with requests.post(url, headers=_headers(), json=payload, timeout=timeout, stream=True) as r:
        if r.status_code == 401:
            raise DeepseekError("401 unauthorized")
        if r.status_code >= 400:
            raise DeepseekError(f"{r.status_code} {r.text}")
        for line in r.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue
            chunk = line[5:].strip()
            if chunk == "[DONE]":
                break
            try:
                obj = json.loads(chunk)
                yield obj["choices"][0]["delta"].get("content", "")
            except Exception:
                # ignore malformed keepalives
                continue