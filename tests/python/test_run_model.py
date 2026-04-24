"""Tests for scripts/run_model.py — argument parsing and env-var resolution."""
import os
import pathlib
import subprocess
import sys


SCRIPT = pathlib.Path(__file__).resolve().parents[2] / "scripts" / "run_model.py"


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
