from __future__ import annotations

import json
from typing import TypeVar

from openai import OpenAI
from pydantic import BaseModel, ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

from ..settings import settings

T = TypeVar("T", bound=BaseModel)


def _client() -> OpenAI | None:
    if not settings.openai_api_key:
        return None
    kwargs = {"api_key": settings.openai_api_key}
    if settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url
    return OpenAI(**kwargs)


def _extract_json(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        s = s.strip("`")
    # best-effort: locate first { ... } block
    start = s.find("{")
    end = s.rfind("}")
    if start >= 0 and end > start:
        return s[start : end + 1]
    return s


@retry(wait=wait_exponential_jitter(initial=0.5, max=4.0), stop=stop_after_attempt(3))
def chat_json(model: str, *, system: str, user: str, out_model: type[T]) -> T:
    client = _client()
    if client is None:
        raise RuntimeError("LLM disabled (OPENAI_API_KEY not set)")

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.1,
    )
    content = resp.choices[0].message.content or ""
    raw = _extract_json(content)
    try:
        data = json.loads(raw)
        return out_model.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as e:
        # force retry by raising
        raise RuntimeError(f"Invalid JSON/schema: {e}. Raw: {content[:4000]}") from e

