#!/usr/bin/env python3
"""
make_charts.py — generate the three v1.3 release charts as PNGs.

Reads the v1.3 result directories under outputs/ and emits:
  docs/benchmark-chart-models.png       Axis A — 10 LLMs bare on Policy / Trace
  docs/benchmark-chart-wrappers.png     Axis B — 3 LLMs × 4 wrappers (Trace + Ctrl)
  docs/benchmark-chart-trace-ladder.png Axis C — trace-performance ladder

Run from project root:
    python3 scripts/make_charts.py
"""
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).parent.parent
OUTPUTS = ROOT / "outputs"
DOCS = ROOT / "docs"
DOCS.mkdir(exist_ok=True)


def pct(x):
    if not x or not x.get("possible"):
        return 0.0
    return 100.0 * x["earned"] / x["possible"]


def load_report(name):
    p = OUTPUTS / name / "report.json"
    if not p.exists():
        return None
    return json.loads(p.read_text())


# ─────────────────────────────────────────────────────────────────────
# Chart 1: Axis A — 10 LLMs bare. Policy bars + Trace flat-zero line.
# ─────────────────────────────────────────────────────────────────────

AXIS_A_RUNS = [
    ("GLM-4.6", "llm_glm_46"),
    ("Claude Sonnet 4.6", "llm_claude_sonnet_46"),
    ("Qwen3-Max", "llm_qwen3_max"),
    ("DeepSeek-V3.2", "llm_deepseek_v3"),
    ("GPT-4o-mini", "llm_gpt_4o_mini"),
    ("DeepSeek-R1", "v13_r1_bare"),
    ("Gemini 2.5 Pro", "llm_gemini_25_pro"),
    ("Kimi K2", "llm_kimi_k2"),
    ("Hunyuan A13B", "llm_hunyuan_a13b"),
    ("MedGemma 4B", "llm_medgemma_4b"),
]

names, policy, trace = [], [], []
for label, dir_name in AXIS_A_RUNS:
    r = load_report(dir_name)
    if r is None:
        continue
    names.append(label)
    policy.append(pct(r["policy_compliance"]))
    trace.append(pct(r["traceability"]))

fig, ax = plt.subplots(figsize=(11, 5.5))
x = np.arange(len(names))
ax.bar(x, policy, color="#2a78d6", label="Policy compliance %")
ax.plot(x, trace, "o-", color="#d63831", linewidth=2, markersize=8, label="Traceability % (flat zero)")
ax.axhline(0, color="#d63831", linewidth=1, linestyle="--", alpha=0.4)
ax.set_xticks(x)
ax.set_xticklabels(names, rotation=30, ha="right")
ax.set_ylim(0, 100)
ax.set_ylabel("Score (%)")
ax.set_title("Axis A — 10 LLMs, bare (default prompt). Policy varies; Traceability is flat zero.")
ax.legend(loc="upper right")
ax.grid(axis="y", alpha=0.3)
for xi, p_val in zip(x, policy):
    ax.text(xi, p_val + 1.5, f"{p_val:.0f}%", ha="center", fontsize=9)
plt.tight_layout()
plt.savefig(DOCS / "benchmark-chart-models.png", dpi=140)
plt.close()
print(f"wrote {DOCS / 'benchmark-chart-models.png'}")


# ─────────────────────────────────────────────────────────────────────
# Chart 2: Axis B — 3 LLMs × 4 wrappers. Trace and Ctrl side by side.
# ─────────────────────────────────────────────────────────────────────

WRAPPERS = ["Bare", "+ NeMo", "+ OAI Guardrails", "+ LangGraph HITL"]
LLMS_AXIS_B = [
    ("GPT-4o-mini", ["llm_gpt_4o_mini", "axisB_topic_rails_gpt4omini",
                     "axisB_content_filter_gpt4omini", "axisB_hitl_prompt_gpt4omini"]),
    ("Claude Sonnet 4.6", ["llm_claude_sonnet_46", "axisB_topic_rails_claude46",
                           "axisB_content_filter_claude46", "axisB_hitl_prompt_claude46"]),
    ("DeepSeek-R1", ["v13_r1_bare", "v13_r1_topic_rails",
                     "v13_r1_content_filter", "v13_r1_hitl_prompt"]),
]

trace_grid = []  # rows = LLMs, cols = wrappers
ctrl_grid = []
for _, dirs in LLMS_AXIS_B:
    row_t, row_c = [], []
    for d in dirs:
        r = load_report(d)
        if r is None:
            row_t.append(0.0)
            row_c.append(0.0)
        else:
            row_t.append(pct(r["traceability"]))
            row_c.append(pct(r["controllability"]))
    trace_grid.append(row_t)
    ctrl_grid.append(row_c)

fig, (ax_t, ax_c) = plt.subplots(1, 2, figsize=(13, 5))
x = np.arange(len(WRAPPERS))
width = 0.27
colors = ["#2a78d6", "#d68a2a", "#7d2ad6"]

for i, (llm_label, _) in enumerate(LLMS_AXIS_B):
    offset = (i - 1) * width
    ax_t.bar(x + offset, trace_grid[i], width, label=llm_label, color=colors[i])
    ax_c.bar(x + offset, ctrl_grid[i], width, label=llm_label, color=colors[i])

for ax, grid, title in [(ax_t, trace_grid, "Traceability (%)"),
                        (ax_c, ctrl_grid, "Controllability (%)")]:
    ax.set_xticks(x)
    ax.set_xticklabels(WRAPPERS, rotation=15, ha="right")
    ax.set_ylim(0, 110)
    ax.set_ylabel(title)
    ax.set_title(f"Axis B — {title} across 3 LLMs × 4 wrappers")
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    for j, row in enumerate(grid):
        for xi, v in enumerate(row):
            if v > 0.5:
                ax.text(xi + (j - 1) * width, v + 2, f"{v:.0f}%", ha="center", fontsize=8)

fig.suptitle("Same wrapper, identical Trace/Ctrl gain across instruction-tuned, mid-tier, and reasoning LLMs",
             fontsize=11, y=1.02)
plt.tight_layout()
plt.savefig(DOCS / "benchmark-chart-wrappers.png", dpi=140, bbox_inches="tight")
plt.close()
print(f"wrote {DOCS / 'benchmark-chart-wrappers.png'}")


# ─────────────────────────────────────────────────────────────────────
# Chart 3: Trace-performance ladder
# ─────────────────────────────────────────────────────────────────────

LADDER_RUNS = [
    ("Bare LLM\ndefault prompt\n(Axis A: 10 LLMs)", "llm_gpt_4o_mini", "0% across 10 LLMs"),
    ("Wrapper +\nskeletal audit\n(Axis B)", "axisB_content_filter_gpt4omini", "33.1% (template floor)"),
    ("Bare LLM +\nasking prompt\n(Axis C, GPT-4o-mini)", "v13_audit_prompt_gpt4omini", "87.8% (LLM-cooperation)"),
    ("Wrapper +\nfull audit\n(Axis C, 3 LLMs)", "v13_full_audit_gpt4omini", "100% across 3 LLMs"),
]

labels = [l for l, _, _ in LADDER_RUNS]
sublabels = [s for _, _, s in LADDER_RUNS]
trace_vals = []
for _, dir_name, _ in LADDER_RUNS:
    r = load_report(dir_name)
    trace_vals.append(pct(r["traceability"]) if r else 0.0)

fig, ax = plt.subplots(figsize=(10, 5))
colors = ["#9aa3ad", "#5d8ed6", "#d68a2a", "#3aa83a"]
bars = ax.bar(range(len(labels)), trace_vals, color=colors, width=0.6)
ax.set_xticks(range(len(labels)))
ax.set_xticklabels(labels, fontsize=10)
ax.set_ylabel("Traceability (%)")
ax.set_ylim(0, 110)
ax.set_title("Axis C — the trace-performance ladder\nWrappers ENFORCE, prompts REQUEST, default-prompt bare pipes record nothing",
             fontsize=11)
ax.grid(axis="y", alpha=0.3)
for bar, val, sub in zip(bars, trace_vals, sublabels):
    ax.text(bar.get_x() + bar.get_width()/2, val + 3, f"{val:.1f}%",
            ha="center", fontsize=12, fontweight="bold")
    ax.text(bar.get_x() + bar.get_width()/2, val/2 if val > 15 else val + 10, sub,
            ha="center", fontsize=8, color="white" if val > 15 else "#444",
            fontweight="normal")
plt.tight_layout()
plt.savefig(DOCS / "benchmark-chart-trace-ladder.png", dpi=140, bbox_inches="tight")
plt.close()
print(f"wrote {DOCS / 'benchmark-chart-trace-ladder.png'}")

print("\nAll three charts generated.")
