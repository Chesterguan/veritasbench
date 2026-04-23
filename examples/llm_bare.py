"""
llm_bare.py — Bare LLM with zero governance.

Sends each scenario to GPT-4o-mini and asks it to make a governance decision.
No guardrails, no audit trail, no human-in-the-loop. The LLM decides based
purely on its training and the scenario description.

This is the floor: what happens when you give an LLM clinical governance
decisions with no governance infrastructure.

Requires: OPENAI_API_KEY environment variable, `pip install openai`
"""
import json
import os
import sys

# Ensure examples/ is on sys.path so `_llm_shared` resolves when invoked
# from any working directory.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from openai import OpenAI  # noqa: E402

from _llm_shared import SYSTEM_PROMPT, build_bare_result, build_prompt, normalize_decision  # noqa: E402

MODEL = os.environ.get("VERITASBENCH_MODEL", "gpt-4o-mini")

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI()
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
