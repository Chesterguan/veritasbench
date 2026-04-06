#!/usr/bin/env python3
"""
Assign difficulty tiers to all scenarios based on governance complexity.

Rules:
- easy: Clear-cut decisions. Single policy applies, no ambiguity.
  * UA with no permissions → deny (obvious)
  * PL with SSN/DOB in content → deny (pattern match)
  * MA with approval_status=none → blocked (mechanical check)
  * MJ with justification=null → deny (mechanical check)
  * SI with human_pre_authorization present → allow (lookup)
  * AG with no attribution_gap → allow (chain is clean)
  * II with emergency_treatment permission → allow (override rule)

- moderate: Requires reasoning about context. Multiple factors to weigh.
  * US with drug interaction (requires clinical knowledge)
  * EO legitimate emergency (requires context evaluation)
  * CM with active consent (requires consent model)
  * CA with priority_rule present (must resolve conflict)
  * II with absence_type=pending/system_unavailable (judgment call)
  * SI with protocol-based trigger (standing order evaluation)
  * AG with partial attribution (some steps attributed, some not)

- hard: Genuinely ambiguous. Reasonable systems could disagree.
  * CA with priority_rule=null (true ambiguity)
  * II with never_recorded + clinical significance judgment
  * EO abuse of override (looks like emergency but isn't)
  * AG with all-AI chain (full accountability gap)
  * Role-based ambiguity scenarios (equal authority conflicts)
"""
import json
import os
import sys

SCENARIO_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "scenarios", "healthcare_v1"
)


def classify_difficulty(scenario: dict) -> str:
    stype = scenario.get("scenario_type", "")
    expected = scenario.get("expected", {}).get("decision", "")
    prior = scenario.get("prior_state") or {}
    actor = scenario.get("actor") or {}
    permissions = actor.get("permissions", [])

    # --- Unauthorized Access ---
    if stype == "unauthorized_access":
        if not permissions:
            return "easy"  # No permissions = obvious deny
        # Cross-department, terminated employee, credential issues
        if prior.get("employment_status") == "terminated":
            return "moderate"
        if prior.get("cross_state_practice_authorized") is False:
            return "moderate"
        if expected == "allow":
            return "moderate"  # Allow cases require more reasoning
        return "easy"

    # --- Missing Approval ---
    if stype == "missing_approval":
        approval = scenario.get("approval_status")
        if approval in (None, "none"):
            return "easy"  # No approval = mechanical block
        if approval in ("emergency_override", "emergency_standing_order"):
            return "moderate"  # Emergency context
        return "moderate"

    # --- Missing Justification ---
    if stype == "missing_justification":
        justification = scenario.get("justification")
        if justification is None:
            return "easy"  # No justification = mechanical deny
        return "moderate"

    # --- PHI Leakage ---
    if stype == "phi_leakage":
        content = scenario.get("input_content", "") or ""
        # SSN or DOB patterns are easy to detect
        import re
        if re.search(r"\d{3}-\d{2}-\d{4}", content) or re.search(r"\d{4}-\d{2}-\d{2}", content):
            return "easy"
        # Names-only PHI is harder
        return "moderate"

    # --- Unsafe Action Sequence ---
    if stype == "unsafe_action_sequence":
        orders = prior.get("active_orders", [])
        if len(orders) == 1:
            return "moderate"  # Single interaction to detect
        if len(orders) > 1:
            return "hard"  # Multiple interactions to reason about
        return "moderate"

    # --- Emergency Override ---
    if stype == "emergency_override":
        if expected == "allow":
            return "moderate"  # Legitimate emergency
        return "hard"  # Abuse of override — hard to distinguish

    # --- Consent Management ---
    if stype == "consent_management":
        consent = prior.get("consent_status") or prior.get("consent_record", {}).get("status")
        if consent in ("withdrawn", "revoked"):
            return "easy"  # Clear deny
        if consent in ("active", "granted"):
            return "easy"  # Clear allow
        return "moderate"  # Proxy consent, partial consent, etc.

    # --- Conflicting Authority ---
    if stype == "conflicting_authority":
        priority = prior.get("priority_rule")
        if priority is not None:
            return "moderate"  # Has a resolution rule, but must apply it
        return "hard"  # Genuine ambiguity, must escalate

    # --- Incomplete Information ---
    if stype == "incomplete_information":
        missing = prior.get("missing_data", {})
        absence = missing.get("absence_type", "")
        if "emergency_treatment" in permissions:
            return "moderate"  # Emergency override is a known pattern
        if absence == "expired" and expected == "allow":
            return "easy"  # Data existed, minor staleness
        if absence == "never_recorded":
            significance = missing.get("clinical_significance", "")
            if "teratogenic" in significance or "narrow_therapeutic" in significance or "thrombolytic" in significance:
                return "hard"  # High-stakes missing data
            return "moderate"
        return "moderate"

    # --- System-Initiated ---
    if stype == "system_initiated":
        trigger = prior.get("system_trigger", {})
        pre_auth = trigger.get("human_pre_authorization")
        if pre_auth is not None:
            return "easy"  # Pre-authorized = allow
        trigger_type = trigger.get("type", "")
        if trigger_type == "predictive_model":
            return "hard"  # AI prediction-driven action, hardest to govern
        return "moderate"

    # --- Accountability Gap ---
    if stype == "accountability_gap":
        chain = prior.get("decision_chain", [])
        gap = prior.get("attribution_gap")
        if gap is None:
            return "easy"  # No gap = clean chain
        unattributed = sum(1 for s in chain if not s.get("attributed", True))
        if unattributed == len(chain):
            return "hard"  # Fully AI-driven chain
        if unattributed >= 2:
            return "hard"  # Multiple gaps
        return "moderate"

    return "moderate"  # Default


def main():
    counts = {"easy": 0, "moderate": 0, "hard": 0}
    type_counts = {}

    files = sorted(f for f in os.listdir(SCENARIO_DIR) if f.endswith(".json"))
    for fname in files:
        path = os.path.join(SCENARIO_DIR, fname)
        with open(path) as f:
            scenario = json.load(f)

        difficulty = classify_difficulty(scenario)
        scenario["difficulty"] = difficulty

        with open(path, "w") as f:
            json.dump(scenario, f, indent=4)
            f.write("\n")

        counts[difficulty] += 1
        stype = scenario.get("scenario_type", "unknown")
        if stype not in type_counts:
            type_counts[stype] = {"easy": 0, "moderate": 0, "hard": 0}
        type_counts[stype][difficulty] += 1

    print(f"Total: {sum(counts.values())} scenarios")
    print(f"  Easy:     {counts['easy']}")
    print(f"  Moderate: {counts['moderate']}")
    print(f"  Hard:     {counts['hard']}")
    print()
    for stype in sorted(type_counts):
        tc = type_counts[stype]
        print(f"  {stype}: easy={tc['easy']} moderate={tc['moderate']} hard={tc['hard']}")


if __name__ == "__main__":
    main()
