"""
openai_guardrails_simulated.py — OpenAI Agents SDK with Guardrails adapter.

Models OpenAI's guardrails: input/output content filtering and tracing, but no
policy engine and no execution control. Content safety is a strength; policy
compliance and human-in-the-loop are not supported.

Results are deterministic via scenario ID hash.
"""
import hashlib
import json
import re
import sys
from datetime import datetime, timezone


def deterministic_chance(scenario_id: str, threshold: float) -> bool:
    """Returns True with probability `threshold` based on scenario ID hash."""
    h = int(hashlib.sha256(scenario_id.encode()).hexdigest()[:8], 16)
    return (h % 100) < (threshold * 100)


_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_DOB_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
# OpenAI guardrails catch SSN and DOB but miss contextual names
_NAME_RE = re.compile(r"\b[A-Z][a-z]+ [A-Z][a-z]+\b")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _partial_redact(text: str) -> str:
    """Redact SSNs and DOBs; names are NOT redacted (guardrail limitation)."""
    text = _SSN_RE.sub("[SSN REDACTED]", text)
    text = _DOB_RE.sub("[DOB REDACTED]", text)
    # Names intentionally NOT redacted — OpenAI guardrails miss contextual names
    return text


def _trace_entry(action: str) -> dict:
    """
    Produces a limited trace entry as OpenAI's tracing would emit.
    Fields: timestamp and action only. No reason, no resource.
    """
    return {
        "timestamp": _now(),
        "actor": None,
        "action": action,
        "resource": None,   # traces don't capture resource-level detail
        "decision": None,
        "reason": None,     # traces don't capture internal reasoning
    }


# Per-scenario-type deny probabilities
_DENY_PROBABILITY = {
    # Guardrail catches some role violations via prompt analysis
    "unauthorized_access": 0.70,
    # No approval mechanism — always allows
    "missing_approval": 0.00,
    # Inconsistent — guardrail fires on some but not all justification gaps
    "missing_justification": 0.50,
    # PHI filter handles this — handled separately below
    "phi_leakage": 1.00,
    # Good at drug interaction detection via prompt
    "unsafe_action_sequence": 0.80,
}


def handle(scenario: dict) -> dict:
    scenario_id = scenario.get("id", "")
    stype = scenario.get("scenario_type", "")
    action = scenario.get("action") or {}
    verb = action.get("verb", "unknown")
    target = action.get("target_resource", "unknown")

    audit_entries = []

    if stype == "phi_leakage":
        content = scenario.get("input_content") or ""
        has_ssn = bool(_SSN_RE.search(content))
        has_dob = bool(_DOB_RE.search(content))
        has_phi = has_ssn or has_dob

        if has_phi:
            decision = "deny"
            output_content = _partial_redact(content)
        else:
            # Guardrail missed it (e.g. name-only PHI)
            decision = "allow"
            output_content = content

        audit_entries.append(_trace_entry(f"{verb} {target}"))
        return {
            "decision": decision,
            "audit_entries": audit_entries,
            "execution_halted": False,
            "human_notified": False,
            "output_content": output_content,
        }

    if stype == "missing_approval":
        # No approval concept — always allows, no trace for this
        return {
            "decision": "allow",
            "audit_entries": [],
            "execution_halted": False,
            "human_notified": False,
            "output_content": scenario.get("input_content"),
        }

    # All other scenario types: probabilistic decision
    deny_prob = _DENY_PROBABILITY.get(stype, 0.50)
    if deterministic_chance(scenario_id, deny_prob):
        decision = "deny"
    else:
        decision = "allow"

    # Guardrail produces ONE limited trace entry
    audit_entries.append(_trace_entry(f"{verb} {target}"))

    return {
        "decision": decision,
        # Single entry; reason and resource fields are null (trace limitation)
        "audit_entries": audit_entries,
        # Guardrails reject but never pause execution
        "execution_halted": False,
        # No human-in-the-loop mechanism
        "human_notified": False,
        "output_content": None if decision == "deny" else scenario.get("input_content"),
    }


if __name__ == "__main__":
    scenario = json.loads(sys.stdin.read())
    print(json.dumps(handle(scenario)))
