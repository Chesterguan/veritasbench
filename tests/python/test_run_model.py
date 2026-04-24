"""Tests for scripts/run_model.py — argument parsing and env-var resolution."""
import importlib.util
import os
import pathlib
import subprocess
import sys


REPO = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "run_model.py"


def _load_run_model_module():
    """Import scripts/run_model.py as a module so we can test helpers directly."""
    spec = importlib.util.spec_from_file_location("run_model", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run_dry(args, env=None):
    e = os.environ.copy()
    if env is not None:
        # Completely replace (caller provides full env).
        e = env
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args, "--dry-run"],
        capture_output=True,
        env=e,
        timeout=10,
    )


def test_unknown_short_name_exits_nonzero():
    proc = _run_dry(["does-not-exist"])
    assert proc.returncode != 0
    stderr = proc.stderr.decode().lower()
    assert "unknown" in stderr or "not found" in stderr


def test_missing_key_env_exits_nonzero():
    # gpt-4o-mini requires OPENAI_API_KEY.
    env = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}
    # Also strip PATH-independent stuff that could carry leaked keys.
    env.setdefault("PATH", os.environ.get("PATH", ""))
    proc = _run_dry(["gpt-4o-mini"], env=env)
    assert proc.returncode != 0
    assert b"OPENAI_API_KEY" in proc.stderr


def test_dry_run_prints_cargo_command():
    env = os.environ.copy()
    env["OPENAI_API_KEY"] = "sk-test"
    proc = _run_dry(["gpt-4o-mini"], env=env)
    assert proc.returncode == 0, proc.stderr.decode()
    out = proc.stdout.decode()
    assert "cargo run" in out
    assert "llm_openai_compat.py" in out
    assert "healthcare_v1" in out
    assert "--retries" in out and "2" in out
    assert "--timeout" in out and "30000" in out


def test_dry_run_default_output_path():
    env = os.environ.copy()
    env["OPENAI_API_KEY"] = "sk-test"
    proc = _run_dry(["gpt-4o-mini"], env=env)
    out = proc.stdout.decode()
    assert "outputs/llm_gpt_4o_mini" in out


def test_dry_run_respects_timeout_override():
    env = os.environ.copy()
    env["OPENROUTER_API_KEY"] = "sk-or-test"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "deepseek-r1", "--timeout", "60000", "--dry-run"],
        capture_output=True,
        env=env,
        timeout=10,
    )
    assert proc.returncode == 0, proc.stderr.decode()
    assert "60000" in proc.stdout.decode()


# ── URL validation (SSRF guard) ──────────────────────────────────────────

def test_validate_base_url_accepts_https():
    mod = _load_run_model_module()
    mod._validate_base_url("https://api.openai.com/v1", "gpt-4o-mini")
    mod._validate_base_url("https://openrouter.ai/api/v1", "deepseek-v3")


def test_validate_base_url_accepts_localhost_http():
    mod = _load_run_model_module()
    mod._validate_base_url("http://localhost:11434/v1", "medgemma-4b")
    mod._validate_base_url("http://127.0.0.1:8000/v1", "custom-local")


def test_validate_base_url_rejects_plain_http():
    mod = _load_run_model_module()
    import pytest
    with pytest.raises(ValueError, match="scheme"):
        mod._validate_base_url("http://evil.example.com/v1", "x")


def test_validate_base_url_rejects_cloud_metadata():
    mod = _load_run_model_module()
    import pytest
    # IMDS IP is the classic SSRF exfiltration target.
    with pytest.raises(ValueError, match="metadata"):
        mod._validate_base_url("http://169.254.169.254/latest/meta-data/", "x")
    # Even dressed up as https, we still refuse it.
    with pytest.raises(ValueError, match="metadata"):
        mod._validate_base_url("https://metadata.google.internal/", "x")


def test_validate_base_url_rejects_file_scheme():
    mod = _load_run_model_module()
    import pytest
    with pytest.raises(ValueError):
        mod._validate_base_url("file:///etc/passwd", "x")


# ── Env scoping (no cross-provider key leakage) ─────────────────────────

def test_build_scoped_env_drops_foreign_keys():
    mod = _load_run_model_module()
    cfg = {
        "adapter": "llm_openai_compat.py",
        "env": {"OPENAI_BASE_URL": "https://openrouter.ai/api/v1", "VERITASBENCH_MODEL": "x"},
        "key_env": "OPENROUTER_API_KEY",
    }
    # Seed os.environ with a bunch of keys.
    os.environ["OPENROUTER_API_KEY"] = "or-key"
    os.environ["ANTHROPIC_API_KEY"] = "anthropic-key"
    os.environ["GEMINI_API_KEY"] = "gemini-key"
    os.environ["SILICONFLOW_API_KEY"] = "sf-key"
    try:
        scoped = mod._build_scoped_env(cfg, "deepseek-v3")
    finally:
        for k in ("ANTHROPIC_API_KEY", "GEMINI_API_KEY", "SILICONFLOW_API_KEY"):
            os.environ.pop(k, None)

    # Only OPENROUTER_API_KEY (and its OPENAI_API_KEY alias for openai-compat) is present.
    assert scoped.get("OPENROUTER_API_KEY") == "or-key"
    assert scoped.get("OPENAI_API_KEY") == "or-key"
    assert "ANTHROPIC_API_KEY" not in scoped, "foreign key leaked into subprocess env"
    assert "GEMINI_API_KEY" not in scoped, "foreign key leaked into subprocess env"
    assert "SILICONFLOW_API_KEY" not in scoped, "foreign key leaked into subprocess env"


def test_build_scoped_env_preserves_system_essentials():
    mod = _load_run_model_module()
    cfg = {
        "adapter": "llm_gemini.py",
        "env": {"VERITASBENCH_MODEL": "gemini-2.5-pro"},
        "key_env": "GEMINI_API_KEY",
    }
    os.environ["GEMINI_API_KEY"] = "g-key"
    os.environ["RANDOM_UNRELATED_SECRET"] = "leak-me-not"
    try:
        scoped = mod._build_scoped_env(cfg, "gemini-25-pro")
    finally:
        os.environ.pop("RANDOM_UNRELATED_SECRET", None)

    # Essentials still there.
    assert "PATH" in scoped
    # Unrelated env vars are dropped.
    assert "RANDOM_UNRELATED_SECRET" not in scoped
    # Gemini adapter doesn't need OPENAI_API_KEY aliasing.
    assert scoped.get("GEMINI_API_KEY") == "g-key"
    assert "OPENAI_API_KEY" not in scoped or scoped.get("OPENAI_API_KEY") == os.environ.get("OPENAI_API_KEY", "")
