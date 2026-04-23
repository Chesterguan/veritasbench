"""
llm_gemini.py — Native Google GenAI SDK adapter.

Benchmarks Gemini 2.5 Pro (or any Gemini model). Uses the `google-genai`
SDK for direct access (not the legacy ai-platform Vertex SDK).

Reads from environment:
    GEMINI_API_KEY     — Google AI Studio API key
    VERITASBENCH_MODEL — model ID (default: gemini-2.5-pro)

Requires: `pip install google-genai`
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from google import genai  # noqa: E402
from google.genai import types  # noqa: E402

from _llm_shared import SYSTEM_PROMPT, build_bare_result, build_prompt, normalize_decision  # noqa: E402

MODEL = os.environ.get("VERITASBENCH_MODEL", "gemini-2.5-pro")

_client = None
_DECISION_JSON_RE = re.compile(r'\{[^{}]*"decision"[^{}]*\}', re.DOTALL)


def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    return _client


def handle(scenario: dict) -> dict:
    response = _get_client().models.generate_content(
        model=MODEL,
        contents=build_prompt(scenario)
        + '\n\nRespond with ONLY a JSON object like {"decision": "deny"}.',
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0,
            response_mime_type="application/json",
        ),
    )
    text = response.text or ""
    parsed = {}
    match = _DECISION_JSON_RE.search(text)
    if match:
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            parsed = {}
    decision = normalize_decision(parsed.get("decision", "allow") if parsed else "allow")
    return build_bare_result(decision, scenario)


if __name__ == "__main__":
    scenario = json.loads(sys.stdin.read())
    print(json.dumps(handle(scenario)))
