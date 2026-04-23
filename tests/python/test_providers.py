"""Tests for examples/providers.yaml — structural and content assertions."""
import pathlib
import yaml


PROVIDERS = pathlib.Path(__file__).resolve().parents[2] / "examples" / "providers.yaml"


def _load():
    with open(PROVIDERS) as f:
        return yaml.safe_load(f)


def test_providers_file_exists():
    assert PROVIDERS.exists()


def test_all_entries_have_required_fields():
    data = _load()
    for short_name, cfg in data.items():
        assert "adapter" in cfg, short_name
        assert "env" in cfg, short_name
        assert "key_env" in cfg, short_name
        assert "VERITASBENCH_MODEL" in cfg["env"], short_name
        assert "OPENAI_BASE_URL" in cfg["env"] or cfg["adapter"] != "llm_openai_compat.py", short_name


def test_expected_short_names_present():
    data = _load()
    expected = {
        "gpt-4o-mini",
        "deepseek-v3",
        "deepseek-r1",
        "qwen3-max",
        "glm-46",
        "kimi-k2",
        "claude-sonnet-46",
        "gemini-25-pro",
        "huatuogpt-ii",
        "huatuogpt-o1",
        "meditron-70b",
    }
    missing = expected - set(data.keys())
    assert not missing, f"missing providers: {missing}"


def test_key_env_vars_are_reasonable():
    data = _load()
    allowed_key_envs = {
        "OPENAI_API_KEY",
        "OPENROUTER_API_KEY",
        "SILICONFLOW_API_KEY",
        "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY",
        "TOGETHER_API_KEY",
    }
    for short, cfg in data.items():
        assert cfg["key_env"] in allowed_key_envs, f"{short}: unusual key_env {cfg['key_env']}"
