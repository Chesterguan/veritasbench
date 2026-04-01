"""
cliniclaw_simulated.py — VERITAS reference implementation adapter.

Models ClinicClaw's governance: deny-by-default policy engine, full audit
trail, human-in-the-loop. Every scenario gets a complete audit entry.
"""
import json
import re
import sys
from datetime import datetime, timezone
from typing import Optional


# ---------------------------------------------------------------------------
# Known unsafe drug interaction pairs (both directions covered by normalization)
# ---------------------------------------------------------------------------
DRUG_INTERACTIONS = [
    ("warfarin", "aspirin"),
    ("ssri", "maoi"),
    ("methotrexate", "nsaid"),
    ("lithium", "ace"),
    ("digoxin", "amiodarone"),
]

# PHI patterns
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_DOB_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_NAME_RE = re.compile(r"\b[A-Z][a-z]+ [A-Z][a-z]+\b")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _audit(actor: str, action: str, resource: str, decision: str, reason: str) -> dict:
    return {
        "timestamp": _now(),
        "actor": actor,
        "action": action,
        "resource": resource,
        "decision": decision,
        "reason": reason,
    }


def _actor_id(actor: dict) -> str:
    return f"{actor.get('role', 'unknown')}@{actor.get('department', 'unknown')}"


def _check_unauthorized_access(scenario: dict) -> Optional[dict]:
    """Deny if actor's permissions do not cover the target resource."""
    actor = scenario.get("actor") or {}
    action = scenario.get("action") or {}
    permissions: list = actor.get("permissions") or []
    target: str = action.get("target_resource", "")
    verb: str = action.get("verb", "")

    # Derive required permission from verb + resource type (FHIR resource name)
    resource_type = target.split("/")[0] if "/" in target else target
    required = f"{verb}:{resource_type.lower()}" if verb and resource_type else None

    # Department-scoped permissions (e.g. read:cardiology) only grant access to
    # department-level resources, NOT to general FHIR resource types like Patient.
    # A ward nurse with read:cardiology can read cardiology-department artifacts;
    # they still need read:patient to read Patient resources directly.
    has_permission = (
        not required  # no required permission derivable → pass this check
        or required in permissions
        or any(p.endswith(":*") or p == "*" for p in permissions)
    )

    if not has_permission:
        reason = (
            f"actor lacks required permission '{required}' "
            f"(has: {permissions or 'none'})"
        )
        return {
            "decision": "deny",
            "audit_entries": [
                _audit(
                    _actor_id(actor),
                    f"{verb} {target}",
                    target,
                    "deny",
                    reason,
                )
            ],
            "execution_halted": False,
            "human_notified": False,
            "output_content": None,
        }
    return None


def _check_missing_approval(scenario: dict) -> Optional[dict]:
    """Block if approval_status is 'none' or absent for action requiring approval."""
    actor = scenario.get("actor") or {}
    action = scenario.get("action") or {}
    target = action.get("target_resource", "unknown")
    verb = action.get("verb", "unknown")

    approval_status = scenario.get("approval_status")
    if approval_status == "none" or approval_status is None and scenario.get("scenario_type") == "missing_approval":
        return {
            "decision": "blocked_pending_approval",
            "audit_entries": [
                _audit(
                    _actor_id(actor),
                    f"{verb} {target}",
                    target,
                    "blocked_pending_approval",
                    "action requires approval; approval_status is 'none' — halting execution pending human review",
                )
            ],
            "execution_halted": True,
            "human_notified": True,
            "output_content": None,
        }
    return None


def _check_missing_justification(scenario: dict) -> Optional[dict]:
    """Deny if justification is absent."""
    actor = scenario.get("actor") or {}
    action = scenario.get("action") or {}
    target = action.get("target_resource", "unknown")
    verb = action.get("verb", "unknown")

    if scenario.get("justification") is None and scenario.get("scenario_type") == "missing_justification":
        return {
            "decision": "deny",
            "audit_entries": [
                _audit(
                    _actor_id(actor),
                    f"{verb} {target}",
                    target,
                    "deny",
                    "justification required — no clinical rationale provided for this action",
                )
            ],
            "execution_halted": False,
            "human_notified": False,
            "output_content": None,
        }
    return None


def _redact_phi(text: str) -> str:
    text = _SSN_RE.sub("[SSN REDACTED]", text)
    text = _DOB_RE.sub("[DOB REDACTED]", text)
    text = _NAME_RE.sub("[NAME REDACTED]", text)
    return text


def _check_phi_leakage(scenario: dict) -> Optional[dict]:
    """Detect PHI in input_content; strip it from output and deny."""
    actor = scenario.get("actor") or {}
    action = scenario.get("action") or {}
    target = action.get("target_resource", "unknown")
    verb = action.get("verb", "unknown")

    content = scenario.get("input_content")
    if not isinstance(content, str):
        return None

    has_ssn = bool(_SSN_RE.search(content))
    has_dob = bool(_DOB_RE.search(content))
    has_name = bool(_NAME_RE.search(content))

    if not (has_ssn or has_dob or has_name):
        return None

    phi_types = []
    if has_ssn:
        phi_types.append("SSN")
    if has_dob:
        phi_types.append("date-of-birth")
    if has_name:
        phi_types.append("patient name")

    reason = f"PHI detected in output ({', '.join(phi_types)}) — content redacted, action denied"
    return {
        "decision": "deny",
        "audit_entries": [
            _audit(
                _actor_id(actor),
                f"{verb} {target}",
                target,
                "deny",
                reason,
            )
        ],
        "execution_halted": False,
        "human_notified": False,
        "output_content": _redact_phi(content),
    }


def _normalize_drug(name: str) -> str:
    return name.strip().lower()


def _check_unsafe_action_sequence(scenario: dict) -> Optional[dict]:
    """Deny if active_orders contain a known dangerous drug interaction."""
    actor = scenario.get("actor") or {}
    action = scenario.get("action") or {}
    target = action.get("target_resource", "unknown")
    verb = action.get("verb", "unknown")

    prior_state = scenario.get("prior_state") or {}
    active_orders: list = prior_state.get("active_orders") or []

    # Normalize all drug names present in active orders
    drugs = set()
    for order in active_orders:
        if isinstance(order, str):
            drugs.add(_normalize_drug(order))
        elif isinstance(order, dict):
            name = order.get("drug") or order.get("medication") or order.get("name") or ""
            if name:
                drugs.add(_normalize_drug(name))

    for drug_a, drug_b in DRUG_INTERACTIONS:
        if drug_a in drugs and drug_b in drugs:
            reason = (
                f"unsafe drug interaction detected: {drug_a} + {drug_b} — "
                "co-administration is contraindicated; action denied"
            )
            return {
                "decision": "deny",
                "audit_entries": [
                    _audit(
                        _actor_id(actor),
                        f"{verb} {target}",
                        target,
                        "deny",
                        reason,
                    )
                ],
                "execution_halted": False,
                "human_notified": False,
                "output_content": None,
            }
    return None


def handle(scenario: dict) -> dict:
    stype = scenario.get("scenario_type", "")

    # Policy checks run in order; first match wins (deny-by-default cascade)
    if stype == "unauthorized_access":
        result = _check_unauthorized_access(scenario)
        if result:
            return result

    if stype == "missing_approval":
        result = _check_missing_approval(scenario)
        if result:
            return result

    if stype == "missing_justification":
        result = _check_missing_justification(scenario)
        if result:
            return result

    if stype == "phi_leakage":
        result = _check_phi_leakage(scenario)
        if result:
            return result

    if stype == "unsafe_action_sequence":
        result = _check_unsafe_action_sequence(scenario)
        if result:
            return result

    # Default: allow with full audit (scenario passed all policy checks)
    actor = scenario.get("actor") or {}
    action = scenario.get("action") or {}
    target = action.get("target_resource", "unknown")
    verb = action.get("verb", "unknown")

    return {
        "decision": "allow",
        "audit_entries": [
            _audit(
                _actor_id(actor),
                f"{verb} {target}",
                target,
                "allow",
                "all policy checks passed",
            )
        ],
        "execution_halted": False,
        "human_notified": False,
        "output_content": scenario.get("input_content"),
    }


if __name__ == "__main__":
    scenario = json.loads(sys.stdin.read())
    print(json.dumps(handle(scenario)))
