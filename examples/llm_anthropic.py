"""
llm_anthropic.py — Native Anthropic SDK adapter.

Benchmarks Claude Sonnet 4.6 (or any Anthropic model) with prompt
caching enabled on the system prompt. Use this instead of routing
Claude through OpenRouter if you want the ~90% input-token savings
that prompt caching provides over repeated scenario runs.

Reads from environment:
    ANTHROPIC_API_KEY   — Anthropic API key
    VERITASBENCH_MODEL  — model ID (default: claude-sonnet-4-6)

Requires: `pip install anthropic`
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from anthropic import Anthropic  # noqa: E402

from _llm_shared import SYSTEM_PROMPT, build_bare_result, build_prompt, normalize_decision  # noqa: E402

MODEL = os.environ.get("VERITASBENCH_MODEL", "claude-sonnet-4-6")

_client = None
_DECISION_JSON_RE = re.compile(r'\{[^{}]*"decision"[^{}]*\}', re.DOTALL)


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic()
    return _client


def handle(scenario: dict) -> dict:
    response = _get_client().messages.create(
        model=MODEL,
        max_tokens=256,
        temperature=0,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {
                "role": "user",
                "content": build_prompt(scenario)
                + '\n\nRespond with ONLY a JSON object like {"decision": "deny"}.',
            },
        ],
    )
    # Anthropic returns a list of content blocks; extract the first text block.
    text = ""
    for block in response.content:
        if getattr(block, "type", None) == "text":
            text = block.text
            break

    parsed = {}
    match = _DECISION_JSON_RE.search(text)
    if match:
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            parsed = {}

    # normalize_decision raises InvalidDecisionError on unknown/missing decisions;
    # we let it propagate so the scenario counts as failed rather than silently
    # scored as 'allow' (see examples/_llm_shared.py).
    decision = normalize_decision(parsed.get("decision") if parsed else None)
    return build_bare_result(decision, scenario)


if __name__ == "__main__":
    scenario = json.loads(sys.stdin.read())
    print(json.dumps(handle(scenario)))
