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
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from openai import APIStatusError, OpenAI  # noqa: E402

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
    try:
        msg = str(exc).lower()
    except Exception:
        msg = ""
    return exc.status_code == 400 and "response_format" in msg


def handle(scenario: dict) -> dict:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_prompt(scenario)},
    ]
    kwargs = dict(model=MODEL, messages=messages, temperature=0)

    try:
        response = _get_client().chat.completions.create(
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
            response = _get_client().chat.completions.create(**kwargs)
            content = response.choices[0].message.content or ""
            parsed = _extract_decision_json(content)
        else:
            raise

    decision = normalize_decision(parsed.get("decision", "allow") if parsed else "allow")
    return build_bare_result(decision, scenario)


if __name__ == "__main__":
    scenario = json.loads(sys.stdin.read())
    print(json.dumps(handle(scenario)))
