"""
llm_openai_compat.py — Generic OpenAI-compatible adapter.

Benchmarks any provider that exposes an OpenAI-compatible
/v1/chat/completions endpoint. No governance — bare LLM output shape,
matching llm_bare.py.

Reads from environment:
    OPENAI_API_KEY   — provider's API key
    OPENAI_BASE_URL  — provider's base URL (e.g. https://openrouter.ai/api/v1)
    VERITASBENCH_MODEL — provider's model ID string

Usage (via scripts/run_model.py or directly):
    OPENAI_BASE_URL=https://openrouter.ai/api/v1 \
    OPENAI_API_KEY=sk-or-... \
    VERITASBENCH_MODEL=deepseek/deepseek-chat-v3.2 \
    python examples/llm_openai_compat.py < scenario.json
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from openai import OpenAI  # noqa: E402

from _llm_shared import SYSTEM_PROMPT, build_bare_result, build_prompt, normalize_decision  # noqa: E402

BASE_URL = os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1"
MODEL = os.environ.get("VERITASBENCH_MODEL", "gpt-4o-mini")

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(base_url=BASE_URL)
    return _client


def handle(scenario: dict) -> dict:
    response = _get_client().chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_prompt(scenario)},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    parsed = json.loads(response.choices[0].message.content)
    decision = normalize_decision(parsed.get("decision", "allow"))
    return build_bare_result(decision, scenario)


if __name__ == "__main__":
    scenario = json.loads(sys.stdin.read())
    print(json.dumps(handle(scenario)))
