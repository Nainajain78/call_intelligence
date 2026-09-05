"""
Shared LLM client. Wired to Groq (OpenAI-compatible API, free tier, fast
open-weight models). Reads GROQ_API_KEY from the environment.

Only this file knows which provider is in use -- every other module just
calls call_llm() / call_llm_json().
"""
from __future__ import annotations
import json
import os
import re
import time
from typing import Any

from groq import Groq
from groq import APIStatusError

MODEL = os.environ.get("CALL_INTEL_MODEL", "openai/gpt-oss-120b")

_client = None

RETRYABLE_STATUS_CODES = {429, 500, 502, 503}
MAX_RETRIES = 5
BASE_DELAY_SECONDS = 3


def _get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Run: $env:GROQ_API_KEY=\"your-key-here\""
            )
        _client = Groq(api_key=api_key)
    return _client


def _chat_with_retry(**kwargs):
    client = _get_client()
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return client.chat.completions.create(**kwargs)
        except APIStatusError as e:
            status_code = getattr(e, "status_code", None)
            last_error = e
            if status_code in RETRYABLE_STATUS_CODES and attempt < MAX_RETRIES:
                delay = BASE_DELAY_SECONDS * (2 ** (attempt - 1))
                print(f"  [retry] {status_code} from Groq, attempt {attempt}/{MAX_RETRIES}, "
                      f"waiting {delay}s...")
                time.sleep(delay)
                continue
            raise
    raise last_error


def call_llm(system: str, user: str, max_tokens: int = 2000, temperature: float = 0.0) -> str:
    response = _chat_with_retry(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return response.choices[0].message.content or ""


def call_llm_json(system: str, user: str, max_tokens: int = 2000) -> Any:
    response = _chat_with_retry(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        max_tokens=max_tokens,
        temperature=0.0,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content or ""
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"Model did not return valid JSON.\nRaw output:\n{raw}") from e
