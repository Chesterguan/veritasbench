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


def test_normalize_decision_invalid_defaults_to_allow():
    assert shared.normalize_decision("approved") == "allow"
    assert shared.normalize_decision("") == "allow"
    assert shared.normalize_decision(None) == "allow"


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
