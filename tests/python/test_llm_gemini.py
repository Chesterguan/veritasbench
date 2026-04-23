"""Structural tests for examples/llm_gemini.py — no live API calls."""
import importlib
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "examples"))


def test_gemini_adapter_imports():
    mod = importlib.import_module("llm_gemini")
    assert hasattr(mod, "handle")


def test_gemini_default_model():
    mod = importlib.import_module("llm_gemini")
    assert "gemini" in mod.MODEL.lower()


def test_gemini_uses_shared_helpers():
    import _llm_shared
    mod = importlib.import_module("llm_gemini")
    assert mod.build_prompt is _llm_shared.build_prompt
    assert mod.SYSTEM_PROMPT is _llm_shared.SYSTEM_PROMPT
    assert mod.build_bare_result is _llm_shared.build_bare_result
