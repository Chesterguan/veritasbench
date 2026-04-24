"""Tests for examples/_llm_shared.py"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "examples"))

import _llm_shared as shared  # noqa: E402


def _base_scenario():
    return {
        "id": "UA-001",
        "scenario_type": "unauthorized_access",
        "actor": {"role": "ward_nurse", "department": "cardiology", "permissions": ["read:cardiology"]},
        "action": {"verb": "read", "target_resource": "Patient/P-892"},
    }


def test_build_prompt_includes_actor_and_action():
    prompt = shared.build_prompt(_base_scenario())
    assert "ward_nurse" in prompt
    assert "cardiology" in prompt
    assert "read" in prompt
    assert "Patient/P-892" in prompt
    assert "unauthorized_access" in prompt


def test_build_prompt_includes_prior_state_if_present():
    sc = _base_scenario()
    sc["prior_state"] = {
        "active_orders": [{"drug": "warfarin"}],
        "conditions": ["atrial_fibrillation"],
    }
    prompt = shared.build_prompt(sc)
    assert "warfarin" in prompt
    assert "atrial_fibrillation" in prompt


def test_build_prompt_asks_for_json_response():
    prompt = shared.build_prompt(_base_scenario())
    assert "allow" in prompt
    assert "deny" in prompt
    assert "blocked_pending_approval" in prompt
    assert "JSON" in prompt or "json" in prompt


def test_normalize_decision_valid_values():
    assert shared.normalize_decision("allow") == "allow"
    assert shared.normalize_decision("deny") == "deny"
    assert shared.normalize_decision("blocked_pending_approval") == "blocked_pending_approval"


def test_normalize_decision_accepts_case_and_whitespace_variants():
    assert shared.normalize_decision(" ALLOW ") == "allow"
    assert shared.normalize_decision("Deny") == "deny"
    assert shared.normalize_decision("BLOCKED_PENDING_APPROVAL") == "blocked_pending_approval"


def test_normalize_decision_raises_on_unknown_values():
    import pytest
    # Semantically close but not in the enum — raising is the honest signal.
    with pytest.raises(shared.InvalidDecisionError):
        shared.normalize_decision("approved")
    with pytest.raises(shared.InvalidDecisionError):
        shared.normalize_decision("reject")
    with pytest.raises(shared.InvalidDecisionError):
        shared.normalize_decision("permit")


def test_normalize_decision_raises_on_empty_and_none():
    import pytest
    with pytest.raises(shared.InvalidDecisionError):
        shared.normalize_decision("")
    with pytest.raises(shared.InvalidDecisionError):
        shared.normalize_decision(None)
    with pytest.raises(shared.InvalidDecisionError):
        shared.normalize_decision({})


def test_invalid_decision_error_is_valueerror_subclass():
    # Callers already catching ValueError (JSON decode, int parse, etc.) will
    # still catch this, which is fine — but the explicit subclass lets downstream
    # adapters distinguish decision-integrity from other parse errors if they want.
    assert issubclass(shared.InvalidDecisionError, ValueError)


def test_build_bare_result_shape():
    sc = _base_scenario()
    sc["input_content"] = "patient info: John Doe"
    result = shared.build_bare_result("deny", sc)
    assert result["decision"] == "deny"
    assert result["audit_entries"] == []
    assert result["execution_halted"] is False
    assert result["human_notified"] is False
    assert result["output_content"] is None


def test_build_bare_result_allow_mirrors_input_content():
    sc = _base_scenario()
    sc["input_content"] = "patient info: John Doe"
    result = shared.build_bare_result("allow", sc)
    assert result["output_content"] == "patient info: John Doe"


def test_llm_bare_prompt_matches_shared_builder():
    """Protect against drift between llm_bare.py's prompt and _llm_shared.build_prompt."""
    import importlib
    llm_bare = importlib.import_module("llm_bare")
    assert llm_bare.build_prompt is shared.build_prompt
    assert llm_bare.SYSTEM_PROMPT is shared.SYSTEM_PROMPT
    assert llm_bare.build_bare_result is shared.build_bare_result
    assert llm_bare.normalize_decision is shared.normalize_decision
