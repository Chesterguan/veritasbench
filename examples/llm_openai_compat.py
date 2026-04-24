"""
llm_openai_compat.py — Generic OpenAI-compatible adapter.

Benchmarks any provider that exposes an OpenAI-compatible
/v1/chat/completions endpoint. No governance — bare LLM output shape,
matching llm_bare.py.

Reads from environment:
    OPENAI_API_KEY   — provider's API key
    OPENAI_BASE_URL  — provider's base URL (e.g. https://openrouter.ai/api/v1)
    VERITASBENCH_MODEL — provider's model ID string

Handles two realities of non-OpenAI providers:
  1. Some reject `response_format={"type":"json_object"}` — fall back
     to unconstrained generation and regex-extract a decision object.
  2. Reasoning models (DeepSeek-R1, HuatuoGPT-o1) may emit <think>...
     </think> blocks inline. Because the regex fallback only looks for
     {"decision": "..."}, reasoning prose in the rest of the response
     is harmless — see tests/python/test_llm_openai_compat.py.

Usage (via scripts/run_model.py or directly):
    OPENAI_BASE_URL=https://openrouter.ai/api/v1 \
    OPENAI_API_KEY=sk-or-... \
    VERITASBENCH_MODEL=deepseek/deepseek-chat-v3.2 \
    python examples/llm_openai_compat.py < scenario.json
"""
import json
import os
import random
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from openai import APIStatusError, OpenAI, RateLimitError  # noqa: E402

from _llm_shared import SYSTEM_PROMPT, build_bare_result, build_prompt, normalize_decision  # noqa: E402

BASE_URL = os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1"
MODEL = os.environ.get("VERITASBENCH_MODEL", "gpt-4o-mini")

_client = None

_DECISION_JSON_RE = re.compile(r'\{[^{}]*"decision"[^{}]*\}', re.DOTALL)


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(base_url=BASE_URL)
    return _client


def _extract_decision_json(text: str) -> dict:
    """Pull a {"decision": "..."} object out of free-form LLM text."""
    match = _DECISION_JSON_RE.search(text)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}


def _is_response_format_error(exc: APIStatusError) -> bool:
    """Detect providers that reject response_format={"type":"json_object"}.

    Different providers surface this failure differently:
      - OpenAI / most: error message mentions "response_format"
      - OpenRouter+Novita: "model does not support feature: structured-outputs"
      - Some: "json_object" or "structured outputs" (with space)
    """
    try:
        msg = str(exc).lower()
    except Exception:
        msg = ""
    if exc.status_code != 400:
        return False
    return any(tok in msg for tok in ("response_format", "structured-outputs", "structured outputs", "json_object", "json schema"))


_MAX_429_RETRIES = 5


def _create_with_backoff(**kwargs):
    """Call chat.completions.create, retrying on 429 with exponential backoff.

    Many providers (OpenRouter, DashScope, SiliconFlow) enforce per-model RPM
    limits. When we run several models concurrently against the same gateway,
    the LLM adapter needs to wait out 429s rather than let the runner mark
    the whole scenario failed.
    """
    attempt = 0
    while True:
        try:
            return _get_client().chat.completions.create(**kwargs)
        except RateLimitError as exc:
            attempt += 1
            if attempt > _MAX_429_RETRIES:
                raise
            # Honor Retry-After if the provider sent one; otherwise exponential + jitter.
            retry_after = None
            try:
                retry_after = float(exc.response.headers.get("Retry-After", "") or "")
            except (AttributeError, ValueError, TypeError):
                retry_after = None
            delay = retry_after if retry_after and retry_after > 0 else (2 ** attempt) + random.uniform(0, 1)
            delay = min(delay, 60.0)
            print(
                f"llm_openai_compat: 429 rate-limit, sleeping {delay:.1f}s (attempt {attempt}/{_MAX_429_RETRIES})",
                file=sys.stderr,
            )
            time.sleep(delay)


def handle(scenario: dict) -> dict:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_prompt(scenario)},
    ]
    kwargs = dict(model=MODEL, messages=messages, temperature=0)

    try:
        response = _create_with_backoff(
            **kwargs, response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content or ""
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            parsed = _extract_decision_json(content)
    except APIStatusError as exc:
        if _is_response_format_error(exc):
            print(
                "llm_openai_compat: provider rejected response_format, retrying without it",
                file=sys.stderr,
            )
            response = _create_with_backoff(**kwargs)
            content = response.choices[0].message.content or ""
            parsed = _extract_decision_json(content)
        else:
            raise

    decision = normalize_decision(parsed.get("decision", "allow") if parsed else "allow")
    return build_bare_result(decision, scenario)


if __name__ == "__main__":
    scenario = json.loads(sys.stdin.read())
    print(json.dumps(handle(scenario)))
