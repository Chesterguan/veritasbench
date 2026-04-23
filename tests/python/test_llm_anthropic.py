"""Structural tests for examples/llm_anthropic.py — no live API calls."""
import importlib
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "examples"))


def test_anthropic_adapter_imports():
    mod = importlib.import_module("llm_anthropic")
    assert hasattr(mod, "handle")
    assert hasattr(mod, "SYSTEM_PROMPT")


def test_anthropic_default_model():
    mod = importlib.import_module("llm_anthropic")
    assert "claude" in mod.MODEL.lower()


def test_anthropic_uses_shared_helpers():
    import _llm_shared
    mod = importlib.import_module("llm_anthropic")
    assert mod.build_prompt is _llm_shared.build_prompt
    assert mod.SYSTEM_PROMPT is _llm_shared.SYSTEM_PROMPT
    assert mod.build_bare_result is _llm_shared.build_bare_result
