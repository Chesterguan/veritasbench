#!/usr/bin/env python3
"""
aggregate_axis_b.py — collate the Axis B matrix runs into a single grid.

Reads outputs/axisB_<wrapper>_<llm>/report.json plus the existing 2026-04-24
bare baselines from outputs/llm_*/report.json. Emits two views:

  1. Long table: one row per (llm, wrapper) combo
  2. Grid: rows = LLMs, columns = wrappers, cells = headline metrics

Usage:
    python3 scripts/aggregate_axis_b.py [--input-dir outputs] [--markdown out.md]
"""
import argparse
import json
import sys
from pathlib import Path

# Mapping: short LLM key → (display name, bare-baseline output dir)
LLMS = [
    ("gpt4omini", "GPT-4o-mini", "llm_gpt_4o_mini"),
    ("claude46", "Claude Sonnet 4.6", "llm_claude_sonnet_46"),
    ("glm46", "GLM-4.6", "llm_glm_46"),
]

# Mapping: wrapper key → (display name, output-dir prefix)
WRAPPERS = [
    ("bare", "Bare LLM", None),  # uses LLMS baseline dir
    ("topic_rails", "+ NeMo Guardrails", "axisB_topic_rails"),
    ("content_filter", "+ OpenAI Guardrails", "axisB_content_filter"),
    ("hitl_prompt", "+ LangGraph HITL", "axisB_hitl_prompt"),
]


def pct(d):
    if not d or not d.get("possible"):
        return None
    return 100.0 * d["earned"] / d["possible"]


def df_str(r):
    d = r.get("dangerous_failures")
    if isinstance(d, dict):
        n, t = d["count"], d["total"]
        return f"{n}/{t} ({100*n/t:.1f}%)"
    return "n/a"


def load_report(path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def build_row(report, llm_name, wrapper_name):
    if report is None:
        return {
            "llm": llm_name, "wrapper": wrapper_name, "n": None,
            "policy": None, "safety": None, "trace": None, "ctrl": None,
            "df": "missing",
        }
    return {
        "llm": llm_name,
        "wrapper": wrapper_name,
        "n": len(report.get("per_scenario", [])),
        "policy": pct(report.get("policy_compliance")),
        "safety": pct(report.get("safety")),
        "trace": pct(report.get("traceability")),
        "ctrl": pct(report.get("controllability")),
        "df": df_str(report),
    }


def fmt_pct(v):
    return f"{v:.1f}%" if v is not None else "—"


def render_long_table(rows):
    out = ["## Axis B — long table\n"]
    out.append("| LLM | Wrapper | n | Policy | Safety | Trace | Ctrl | Dangerous |")
    out.append("|---|---|---:|---:|---:|---:|---:|---:|")
    for r in rows:
        n = str(r["n"]) if r["n"] else "—"
        out.append(
            f"| {r['llm']} | {r['wrapper']} | {n} | "
            f"{fmt_pct(r['policy'])} | {fmt_pct(r['safety'])} | "
            f"{fmt_pct(r['trace'])} | {fmt_pct(r['ctrl'])} | {r['df']} |"
        )
    return "\n".join(out)


def render_grid(rows, metric_key, metric_label):
    out = [f"## Axis B grid — {metric_label}\n"]
    header = "| LLM \\ Wrapper |" + "".join(f" {w[1]} |" for w in WRAPPERS)
    sep = "|---|" + "---:|" * len(WRAPPERS)
    out.append(header)
    out.append(sep)
    by_llm = {}
    for r in rows:
        by_llm.setdefault(r["llm"], {})[r["wrapper"]] = r
    for _, llm_disp, _ in LLMS:
        cells = []
        for _, wrap_disp, _ in WRAPPERS:
            r = by_llm.get(llm_disp, {}).get(wrap_disp)
            if r is None:
                cells.append("—")
            elif metric_key == "df":
                cells.append(r["df"])
            else:
                cells.append(fmt_pct(r.get(metric_key)))
        out.append(f"| {llm_disp} | " + " | ".join(cells) + " |")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", default="outputs", type=Path)
    ap.add_argument("--markdown", type=Path, default=None,
                    help="Write markdown output to this path (else stdout)")
    args = ap.parse_args()

    rows = []
    for llm_key, llm_name, bare_dir in LLMS:
        for wrap_key, wrap_name, wrap_prefix in WRAPPERS:
            if wrap_prefix is None:
                report_path = args.input_dir / bare_dir / "report.json"
            else:
                report_path = args.input_dir / f"{wrap_prefix}_{llm_key}" / "report.json"
            rows.append(build_row(load_report(report_path), llm_name, wrap_name))

    sections = [
        render_long_table(rows),
        "",
        render_grid(rows, "policy", "Policy Compliance"),
        "",
        render_grid(rows, "safety", "Safety"),
        "",
        render_grid(rows, "trace", "Traceability"),
        "",
        render_grid(rows, "ctrl", "Controllability"),
        "",
        render_grid(rows, "df", "Dangerous Failures"),
    ]
    output = "\n".join(sections) + "\n"

    if args.markdown:
        args.markdown.write_text(output)
        print(f"Wrote {args.markdown}", file=sys.stderr)
    else:
        sys.stdout.write(output)


if __name__ == "__main__":
    main()
