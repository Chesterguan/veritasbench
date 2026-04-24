#!/usr/bin/env python3
"""
aggregate_models.py — collate outputs/llm_* into a combined CSV + Markdown table.

Usage:
    python scripts/aggregate_models.py --input-dir outputs --csv outputs/combined_results.csv
    python scripts/aggregate_models.py --input-dir outputs --markdown docs/results-by-model.md
    python scripts/aggregate_models.py --input-dir outputs               # prints CSV to stdout

Reads every outputs/llm_<short>/report.json, emits one row per model with
raw earned/possible counts and pre-computed percentages on each of the four
governance dimensions, plus dangerous-failure count and latency p50.
"""
import argparse
import csv
import json
import pathlib
import sys


DIMENSIONS = ["policy_compliance", "safety", "traceability", "controllability"]


def _pct(earned: int, possible: int) -> float:
    if possible == 0:
        return 0.0
    return round(100.0 * earned / possible, 1)


def _load_reports(input_dir: pathlib.Path) -> list[dict]:
    rows = []
    for d in sorted(input_dir.iterdir()):
        if not d.is_dir() or not d.name.startswith("llm_"):
            continue
        report = d / "report.json"
        if not report.exists():
            continue
        data = json.loads(report.read_text())
        row = {"short_name": d.name[len("llm_"):]}
        for k in DIMENSIONS:
            dim = data.get(k, {}) or {}
            earned = int(dim.get("earned", 0))
            possible = int(dim.get("possible", 0))
            row[f"{k}_earned"] = earned
            row[f"{k}_possible"] = possible
            row[f"{k}_pct"] = _pct(earned, possible)
        df = data.get("dangerous_failures", {}) or {}
        row["dangerous_failures_count"] = int(df.get("count", 0) if isinstance(df, dict) else df)
        row["dangerous_failures_total"] = int(df.get("total", 0) if isinstance(df, dict) else 0)
        lat = data.get("latency", {}) or {}
        row["latency_p50_ms"] = int(lat.get("p50_ms", 0))
        row["latency_p95_ms"] = int(lat.get("p95_ms", 0))
        row["adapter"] = data.get("adapter", "")
        row["suite"] = data.get("suite", "")
        rows.append(row)
    return rows


def _write_csv(rows: list[dict], path: pathlib.Path) -> None:
    if not rows:
        path.write_text("short_name\n")
        return
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _write_markdown(rows: list[dict], path: pathlib.Path) -> None:
    lines = [
        "| Model | Policy | Safety | Traceability | Controllability | Dangerous Failures | Latency p50 |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['short_name']} "
            f"| {r['policy_compliance_earned']}/{r['policy_compliance_possible']} ({r['policy_compliance_pct']}%) "
            f"| {r['safety_earned']}/{r['safety_possible']} ({r['safety_pct']}%) "
            f"| {r['traceability_earned']}/{r['traceability_possible']} ({r['traceability_pct']}%) "
            f"| {r['controllability_earned']}/{r['controllability_possible']} ({r['controllability_pct']}%) "
            f"| {r['dangerous_failures_count']}/{r['dangerous_failures_total']} "
            f"| {r['latency_p50_ms']}ms |"
        )
    path.write_text("\n".join(lines) + "\n")


def _write_csv_to_stdout(rows: list[dict]) -> None:
    if not rows:
        return
    writer = csv.DictWriter(sys.stdout, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--csv", default=None)
    parser.add_argument("--markdown", default=None)
    args = parser.parse_args()

    input_dir = pathlib.Path(args.input_dir)
    if not input_dir.is_dir():
        print(f"aggregate: input dir does not exist: {input_dir}", file=sys.stderr)
        return 1

    rows = _load_reports(input_dir)
    if not rows:
        print(f"aggregate: no outputs/llm_*/report.json found in {input_dir}", file=sys.stderr)
        return 1

    if args.csv:
        _write_csv(rows, pathlib.Path(args.csv))
    if args.markdown:
        _write_markdown(rows, pathlib.Path(args.markdown))
    if not args.csv and not args.markdown:
        _write_csv_to_stdout(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
