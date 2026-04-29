#!/usr/bin/env python3
"""
breakdown_by_type.py — per-scenario-type aggregation across runs.

Slices each report's `per_scenario` array by scenario-ID prefix (the
governance type — AG, CA, CM, EO, II, MA, MJ, PL, SI, UA, US) and reports
Policy / Safety / Traceability / Controllability / Dangerous-failure
averages per type.

Useful for answering:
  - Which 2-3 scenario types are 100% of dangerous failures concentrated in?
  - Which types does each wrapper actually halt on? (Validates LangGraph
    HITL_TYPES set.)
  - Are model-tier Policy gains uniform across types or concentrated on
    specific governance types?

Usage:
    python3 scripts/breakdown_by_type.py outputs/llm_claude_sonnet_46
    python3 scripts/breakdown_by_type.py outputs/axisB_hitl_prompt_claude46
    python3 scripts/breakdown_by_type.py outputs/llm_gpt_4o_mini outputs/axisB_*_gpt4omini  # multi
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

TYPE_NAMES = {
    "AG": "Accountability Gap",
    "CA": "Conflicting Authority",
    "CM": "Consent Management",
    "EO": "Emergency Override",
    "II": "Incomplete Information",
    "MA": "Missing Approval",
    "MJ": "Missing Justification",
    "PL": "PHI Leakage",
    "SI": "System-Initiated",
    "UA": "Unauthorized Access",
    "US": "Unsafe Action Sequence",
}

TYPE_ORDER = ["AG", "CA", "CM", "EO", "II", "MA", "MJ", "PL", "SI", "UA", "US"]


def aggregate_one_dir(report_path: Path):
    """Return dict[type_prefix] = aggregated metrics."""
    if not report_path.exists():
        return None
    data = json.loads(report_path.read_text())
    per_scenario = data.get("per_scenario") or []
    if not per_scenario:
        return None

    by_type = defaultdict(lambda: {
        "n": 0,
        "policy_earned": 0, "policy_possible": 0,
        "safety_earned": 0, "safety_possible": 0,
        "trace_earned": 0, "trace_possible": 0,
        "ctrl_earned": 0, "ctrl_possible": 0,
        "dangerous": 0, "dangerous_eligible": 0,
        "latencies": [],
    })

    for s in per_scenario:
        sid = s.get("scenario_id", "")
        prefix = sid.split("-", 1)[0] if "-" in sid else "?"
        b = by_type[prefix]
        b["n"] += 1
        # Policy: 0/1 binary
        pol = s.get("policy_compliance")
        if pol is not None:
            b["policy_earned"] += pol
            b["policy_possible"] += 1
        # Safety: 0/1 binary, may be null when not applicable
        saf = s.get("safety")
        if saf is not None:
            b["safety_earned"] += saf
            b["safety_possible"] += 1
        # Traceability: 0..3 out of 3
        tra = s.get("traceability")
        if tra is not None:
            b["trace_earned"] += tra
            b["trace_possible"] += 3
        # Controllability: 0..2 out of 2 (or 0/1?), may be null
        ctrl = s.get("controllability")
        if ctrl is not None:
            b["ctrl_earned"] += ctrl
            # Look up max from a sample to infer denominator; default to 2
            b["ctrl_possible"] += 2
        # Dangerous failure: only counted on scenarios where it's defined
        dang = s.get("dangerous_failure")
        if dang is not None:
            b["dangerous_eligible"] += 1
            if dang:
                b["dangerous"] += 1
        # Latency
        lat = s.get("latency_ms")
        if lat is not None:
            b["latencies"].append(lat)

    return dict(by_type)


def fmt_pct(earned, possible):
    if possible == 0:
        return "—"
    return f"{100.0*earned/possible:.1f}%"


def fmt_df(count, eligible):
    if eligible == 0:
        return "—"
    return f"{count}/{eligible} ({100.0*count/eligible:.1f}%)"


def render_table(label: str, by_type: dict):
    print(f"\n## {label}\n")
    print("| Type | Name | n | Policy | Safety | Trace | Ctrl | Dangerous |")
    print("|---|---|---:|---:|---:|---:|---:|---:|")
    for t in TYPE_ORDER:
        if t not in by_type:
            continue
        b = by_type[t]
        name = TYPE_NAMES.get(t, "?")
        print(f"| {t} | {name} | {b['n']} | "
              f"{fmt_pct(b['policy_earned'], b['policy_possible'])} | "
              f"{fmt_pct(b['safety_earned'], b['safety_possible'])} | "
              f"{fmt_pct(b['trace_earned'], b['trace_possible'])} | "
              f"{fmt_pct(b['ctrl_earned'], b['ctrl_possible'])} | "
              f"{fmt_df(b['dangerous'], b['dangerous_eligible'])} |")


def render_dangerous_concentration(by_type_per_run: list[tuple[str, dict]]):
    """Show which types account for which fraction of total dangerous failures
    across all runs combined."""
    total_by_type = defaultdict(lambda: {"dangerous": 0, "eligible": 0})
    for _, by_type in by_type_per_run:
        for t, b in by_type.items():
            total_by_type[t]["dangerous"] += b["dangerous"]
            total_by_type[t]["eligible"] += b["dangerous_eligible"]
    grand_total = sum(t["dangerous"] for t in total_by_type.values())
    if grand_total == 0:
        return
    print("\n## Dangerous-failure concentration across all runs\n")
    print(f"Total dangerous failures observed across the runs reported above: **{grand_total}**.\n")
    print("| Type | Name | Dangerous | % of all DF | Per-row rate |")
    print("|---|---|---:|---:|---:|")
    for t in TYPE_ORDER:
        if t not in total_by_type:
            continue
        d = total_by_type[t]
        if d["eligible"] == 0:
            continue
        pct_of_total = 100.0 * d["dangerous"] / grand_total
        per_row_rate = 100.0 * d["dangerous"] / d["eligible"]
        print(f"| {t} | {TYPE_NAMES.get(t, '?')} | {d['dangerous']} | "
              f"{pct_of_total:.1f}% | {per_row_rate:.1f}% |")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+", type=Path,
                    help="Output directories (each containing report.json)")
    args = ap.parse_args()

    by_type_per_run = []
    for d in args.dirs:
        report_path = d / "report.json"
        by_type = aggregate_one_dir(report_path)
        if by_type is None:
            print(f"# {d.name}: no report.json or empty per_scenario", file=sys.stderr)
            continue
        label = d.name
        render_table(label, by_type)
        by_type_per_run.append((label, by_type))

    if len(by_type_per_run) > 1:
        render_dangerous_concentration(by_type_per_run)


if __name__ == "__main__":
    main()
