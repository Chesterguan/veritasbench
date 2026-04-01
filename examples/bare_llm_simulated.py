"""
bare_llm_simulated.py — No governance baseline adapter.

Models a raw LLM with zero governance infrastructure. The LLM is "smart" —
it often gives the right clinical answer — but has no policy engine, no audit
trail, and no execution control. Results are deterministic via scenario ID hash.
"""
import hashlib
import json
import sys


def deterministic_chance(scenario_id: str, threshold: float) -> bool:
    """Returns True with probability `threshold` based on scenario ID hash."""
    h = int(hashlib.sha256(scenario_id.encode()).hexdigest()[:8], 16)
    return (h % 100) < (threshold * 100)


# Per-scenario-type behavior probabilities for "deny" decision.
# The LLM makes a best-guess; no policy engine enforces anything.
_DENY_PROBABILITY = {
    # LLM sometimes reasons correctly about role violations
    "unauthorized_access": 0.60,
    # LLM never blocks on missing approval — no approval mechanism exists
    "missing_approval": 0.00,
    # LLM is inconsistent about justification requirements
    "missing_justification": 0.50,
    # LLM passes PHI through unchanged — no PHI filter
    "phi_leakage": 0.00,
    # LLM knows drug interactions well but isn't infallible
    "unsafe_action_sequence": 0.70,
    # LLM sometimes reasons correctly about emergencies but is inconsistent
    "emergency_override": 0.50,
    # LLM occasionally catches consent violations but has no consent model
    "consent_management": 0.55,
}


def handle(scenario: dict) -> dict:
    scenario_id = scenario.get("id", "")
    stype = scenario.get("scenario_type", "")

    deny_prob = _DENY_PROBABILITY.get(stype, 0.50)

    if stype == "missing_approval":
        # No approval mechanism — always allows regardless of hash
        decision = "allow"
    elif deterministic_chance(scenario_id, deny_prob):
        decision = "deny"
    else:
        decision = "allow"

    # PHI leakage: output passes through unchanged — no filter
    output_content = None
    if stype == "phi_leakage":
        output_content = scenario.get("input_content")

    return {
        "decision": decision,
        # No audit infrastructure — audit trail is always empty
        "audit_entries": [],
        # No execution control — never halted
        "execution_halted": False,
        # No human-in-the-loop mechanism
        "human_notified": False,
        "output_content": output_content,
    }


if __name__ == "__main__":
    scenario = json.loads(sys.stdin.read())
    print(json.dumps(handle(scenario)))
