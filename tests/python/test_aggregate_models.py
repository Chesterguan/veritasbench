"""Tests for scripts/aggregate_models.py"""
import csv
import pathlib
import subprocess
import sys


SCRIPT = pathlib.Path(__file__).resolve().parents[2] / "scripts" / "aggregate_models.py"
FIXTURES = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "fake_outputs"


def test_aggregator_produces_csv(tmp_path):
    out = tmp_path / "combined.csv"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--input-dir", str(FIXTURES), "--csv", str(out)],
        capture_output=True,
        timeout=10,
    )
    assert proc.returncode == 0, proc.stderr.decode()
    assert out.exists()
    with open(out) as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 2
    shorts = {r["short_name"] for r in rows}
    assert shorts == {"fake_a", "fake_b"}


def test_csv_has_percentage_columns(tmp_path):
    out = tmp_path / "combined.csv"
    subprocess.run(
        [sys.executable, str(SCRIPT), "--input-dir", str(FIXTURES), "--csv", str(out)],
        capture_output=True, timeout=10, check=True,
    )
    with open(out) as f:
        rows = list(csv.DictReader(f))
    a = next(r for r in rows if r["short_name"] == "fake_a")
    assert a["policy_compliance_pct"] == "81.7"  # 470/575*100
    assert a["safety_pct"] == "73.8"             # 240/325*100
    assert a["traceability_pct"] == "0.0"
    assert a["controllability_pct"] == "0.0"


def test_aggregator_produces_markdown_table(tmp_path):
    out = tmp_path / "table.md"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--input-dir", str(FIXTURES), "--markdown", str(out)],
        capture_output=True,
        timeout=10,
    )
    assert proc.returncode == 0, proc.stderr.decode()
    text = out.read_text()
    assert "| Model" in text
    assert "fake_a" in text
    assert "fake_b" in text
    assert "%" in text


def test_markdown_includes_dangerous_failures_and_latency(tmp_path):
    out = tmp_path / "table.md"
    subprocess.run(
        [sys.executable, str(SCRIPT), "--input-dir", str(FIXTURES), "--markdown", str(out)],
        capture_output=True, timeout=10, check=True,
    )
    text = out.read_text()
    assert "25" in text and "18" in text   # dangerous_failures counts
    assert "1100" in text and "1300" in text   # latency p50


def test_empty_input_dir_exits_nonzero(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--input-dir", str(empty)],
        capture_output=True,
        timeout=10,
    )
    assert proc.returncode != 0
    assert b"no outputs" in proc.stderr.lower() or b"not found" in proc.stderr.lower()


def test_real_output_readable():
    """Smoke test against the real outputs/llm_gpt_4o_mini directory."""
    real = pathlib.Path(__file__).resolve().parents[2] / "outputs"
    if not (real / "llm_gpt_4o_mini" / "report.json").exists():
        import pytest
        pytest.skip("no real gpt_4o_mini output to read")
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--input-dir", str(real)],
        capture_output=True,
        timeout=10,
    )
    assert proc.returncode == 0, proc.stderr.decode()
    assert b"gpt_4o_mini" in proc.stdout
