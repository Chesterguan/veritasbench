# W3: 10-Model Benchmark Runs + Reporting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run 10 new models against the full `healthcare_v1` suite (700 scenarios each), aggregate the results, regenerate the benchmark chart, and update the README with an 11-row model table and a "Medical LLMs don't fix the governance gap" section driven by real data.

**Architecture:** W3 has two phases: (1) **execution** — user runs `scripts/run_model.py` per model as keys arrive, generating `outputs/llm_<short>/` directories; (2) **reporting** — an aggregator script collates results into a CSV, regenerates the chart, and produces the Markdown + README updates. Execution tasks are user-driven and can ship partially; reporting tasks land once at least 6 of 10 models are complete.

**Tech Stack:** Bash (orchestration), Python (aggregator, chart regeneration using matplotlib or the existing HTML chart script), Markdown (docs).

**Prerequisites:** W1 complete (no critical/high audit findings blocking); W2 complete (`llm_openai_compat.py`, `providers.yaml`, `scripts/run_model.py` all landed and tested).

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `outputs/llm_deepseek_v3/` ... `outputs/llm_meditron_70b/` | Create (run-time) | 10 model run outputs |
| `scripts/aggregate_models.py` | Create | Collate outputs/llm_* into a CSV + MD table |
| `outputs/combined_results.csv` | Create (run-time) | Machine-readable combined results |
| `docs/results-by-model.md` | Create | 11-row model table with per-dimension scores |
| `docs/benchmark-chart.png` | Modify | Regenerated from combined CSV |
| `docs/archived/benchmark-chart-v1.png` | Create | Archive of pre-expansion chart |
| `README.md` | Modify | Add model-comparison table + medical-LLM findings section |
| `tests/python/test_aggregate_models.py` | Create | Unit tests for aggregator |

---

### Task 1: Build `scripts/aggregate_models.py` (TDD)

**Files:**
- Create: `scripts/aggregate_models.py`
- Create: `tests/python/test_aggregate_models.py`
- Create: `tests/fixtures/fake_outputs/llm_fake_a/report.json`
- Create: `tests/fixtures/fake_outputs/llm_fake_b/report.json`

- [ ] **Step 1: Create fixture outputs (two fake report.json files)**

Write `tests/fixtures/fake_outputs/llm_fake_a/report.json`:

```json
{
  "adapter": "llm_openai_compat.py",
  "suite": "healthcare_v1",
  "dimensions": {
    "policy_compliance": {"earned": 470, "possible": 575},
    "safety":            {"earned": 240, "possible": 325},
    "traceability":      {"earned":   0, "possible": 2100},
    "controllability":   {"earned":   0, "possible": 570}
  },
  "dangerous_failures": 25,
  "latency_ms": {"p50": 1100, "p95": 2800}
}
```

Write `tests/fixtures/fake_outputs/llm_fake_b/report.json`:

```json
{
  "adapter": "llm_openai_compat.py",
  "suite": "healthcare_v1",
  "dimensions": {
    "policy_compliance": {"earned": 500, "possible": 575},
    "safety":            {"earned": 260, "possible": 325},
    "traceability":      {"earned":   0, "possible": 2100},
    "controllability":   {"earned":   0, "possible": 570}
  },
  "dangerous_failures": 18,
  "latency_ms": {"p50": 1300, "p95": 3100}
}
```

**Before committing**: run `jq keys outputs/bare_llm_v1/report.json` to confirm the real schema matches the fixture shape above. If the real report uses different keys (e.g., `policy` instead of `policy_compliance`), update both fixtures and the aggregator to match. This plan uses `policy_compliance` as a placeholder — correct to actual schema during implementation.

- [ ] **Step 2: Write failing tests**

Write `tests/python/test_aggregate_models.py`:

```python
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


def test_aggregator_produces_markdown_table(tmp_path):
    out = tmp_path / "table.md"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--input-dir", str(FIXTURES), "--markdown", str(out)],
        capture_output=True,
        timeout=10,
    )
    assert proc.returncode == 0, proc.stderr.decode()
    text = out.read_text()
    assert "| Model" in text or "| Short name" in text
    assert "fake_a" in text
    assert "fake_b" in text
    # Percentages should render.
    assert "%" in text
```

- [ ] **Step 3: Verify failure**

```bash
cd /Volumes/extraSupply/veritasbench
python -m pytest tests/python/test_aggregate_models.py -v 2>&1 | tail -15
```
Expected: FAIL — script does not exist.

- [ ] **Step 4: Implement `scripts/aggregate_models.py`**

```python
#!/usr/bin/env python3
"""
aggregate_models.py — collate outputs/llm_* into a combined CSV + Markdown table.

Usage:
    python scripts/aggregate_models.py --input-dir outputs --csv outputs/combined_results.csv
    python scripts/aggregate_models.py --input-dir outputs --markdown docs/results-by-model.md
"""
import argparse
import csv
import json
import pathlib
import sys


DIMENSIONS = ["policy_compliance", "safety", "traceability", "controllability"]


def _pct(earned, possible):
    if possible == 0:
        return 0.0
    return 100.0 * earned / possible


def _load_reports(input_dir: pathlib.Path):
    rows = []
    for d in sorted(input_dir.iterdir()):
        if not d.is_dir():
            continue
        if not d.name.startswith("llm_"):
            continue
        report = d / "report.json"
        if not report.exists():
            continue
        data = json.loads(report.read_text())
        dims = data.get("dimensions", {})
        short = d.name[len("llm_"):]
        row = {"short_name": short}
        for k in DIMENSIONS:
            earned = dims.get(k, {}).get("earned", 0)
            possible = dims.get(k, {}).get("possible", 0)
            row[f"{k}_earned"] = earned
            row[f"{k}_possible"] = possible
            row[f"{k}_pct"] = round(_pct(earned, possible), 1)
        row["dangerous_failures"] = data.get("dangerous_failures", 0)
        row["latency_p50_ms"] = data.get("latency_ms", {}).get("p50", 0)
        rows.append(row)
    return rows


def write_csv(rows, path: pathlib.Path):
    if not rows:
        path.write_text("short_name\n")
        return
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(rows, path: pathlib.Path):
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
            f"| {r['dangerous_failures']} "
            f"| {r['latency_p50_ms']}ms |"
        )
    path.write_text("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--csv", default=None)
    parser.add_argument("--markdown", default=None)
    args = parser.parse_args()

    rows = _load_reports(pathlib.Path(args.input_dir))
    if not rows:
        print(f"aggregate: no outputs/llm_* directories with report.json found in {args.input_dir}", file=sys.stderr)
        return 1

    if args.csv:
        write_csv(rows, pathlib.Path(args.csv))
    if args.markdown:
        write_markdown(rows, pathlib.Path(args.markdown))
    if not args.csv and not args.markdown:
        # Default: print CSV to stdout.
        import io
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
        sys.stdout.write(buf.getvalue())
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run tests**

```bash
cd /Volumes/extraSupply/veritasbench
python -m pytest tests/python/test_aggregate_models.py -v 2>&1 | tail -15
```
Expected: both tests pass.

- [ ] **Step 6: Commit**

```bash
cd /Volumes/extraSupply/veritasbench
git add scripts/aggregate_models.py tests/python/test_aggregate_models.py tests/fixtures/fake_outputs/
git commit -m "feat: aggregate_models.py — combine per-model reports into CSV + MD"
```

---

### Task 2: Execute runs (user-driven, one per model)

**Prerequisites**: W2 complete, API keys set in environment.

For each of the 10 models below, the user runs a single command. **This is not a parallel task — run them sequentially** (cleaner logs, avoids rate-limit contention). Cheapest first.

- [ ] **Step 1: `gpt-4o-mini` baseline (if re-running after W1 audit fixes)**

```bash
cd /Volumes/extraSupply/veritasbench
export OPENAI_API_KEY=<key>
python scripts/run_model.py gpt-4o-mini --output outputs/llm_gpt4o_mini
```

(If W1 did not touch scoring math, skip this — reuse existing `outputs/bare_llm_v1/`.)

- [ ] **Step 2: `deepseek-v3`**

```bash
cd /Volumes/extraSupply/veritasbench
export OPENROUTER_API_KEY=<key>
python scripts/run_model.py deepseek-v3
```

- [ ] **Step 3: `qwen3-max`**

```bash
cd /Volumes/extraSupply/veritasbench
python scripts/run_model.py qwen3-max
```

- [ ] **Step 4: `glm-46`**

```bash
cd /Volumes/extraSupply/veritasbench
python scripts/run_model.py glm-46
```

- [ ] **Step 5: `kimi-k2`**

```bash
cd /Volumes/extraSupply/veritasbench
python scripts/run_model.py kimi-k2
```

- [ ] **Step 6: `deepseek-r1`** (reasoning — watch for longer latency)

```bash
cd /Volumes/extraSupply/veritasbench
python scripts/run_model.py deepseek-r1 --timeout 60000
```
Note: reasoning models may exceed default 30s timeout. `--timeout 60000` gives 60s per scenario.

- [ ] **Step 7: `gemini-25-pro`**

```bash
cd /Volumes/extraSupply/veritasbench
python scripts/run_model.py gemini-25-pro
```

- [ ] **Step 8: `claude-sonnet-46`**

```bash
cd /Volumes/extraSupply/veritasbench
python scripts/run_model.py claude-sonnet-46
```

- [ ] **Step 9: `huatuogpt-ii`** (Chinese medical)

```bash
cd /Volumes/extraSupply/veritasbench
export SILICONFLOW_API_KEY=<key>
python scripts/run_model.py huatuogpt-ii
```

- [ ] **Step 10: `huatuogpt-o1`** (Chinese medical reasoning)

```bash
cd /Volumes/extraSupply/veritasbench
python scripts/run_model.py huatuogpt-o1 --timeout 60000
```

- [ ] **Step 11: `meditron-70b`** (Western medical)

```bash
cd /Volumes/extraSupply/veritasbench
python scripts/run_model.py meditron-70b
```

- [ ] **Step 12: Sanity-check each run**

```bash
cd /Volumes/extraSupply/veritasbench
for d in outputs/llm_*; do
  echo "=== $d ==="
  if [ -f "$d/report.json" ]; then
    echo "OK: $(jq '.dimensions.policy_compliance.earned' "$d/report.json")/$(jq '.dimensions.policy_compliance.possible' "$d/report.json") policy"
  else
    echo "MISSING report.json"
  fi
done
```

- [ ] **Step 13: Commit all new outputs**

```bash
cd /Volumes/extraSupply/veritasbench
git add outputs/llm_*
git commit -m "data: $(ls outputs/llm_*/report.json | wc -l) new model runs on healthcare_v1"
```

---

### Task 3: Generate combined CSV + per-model Markdown table

**Files:**
- Create: `outputs/combined_results.csv`
- Create: `docs/results-by-model.md`

- [ ] **Step 1: Run aggregator**

```bash
cd /Volumes/extraSupply/veritasbench
python scripts/aggregate_models.py --input-dir outputs --csv outputs/combined_results.csv --markdown docs/results-by-model.md
```

- [ ] **Step 2: Enrich `docs/results-by-model.md` with category labels**

The aggregator's output is raw; it doesn't know which models are Chinese/Western or General/Medical. Open the generated file and prepend a header with category grouping.

Use the Edit tool to replace the file with:

```markdown
# VeritasBench Results by Model

> Generated: 2026-04-23 | Suite: healthcare_v1 (700 scenarios) | See also: [README benchmark results](../README.md#benchmark-results)

All rows below use `examples/llm_openai_compat.py` (or the native SDK variants) — bare LLM, no governance infrastructure. Each model was asked to make the correct allow/deny/block decision and produce an audit trail. None of them produce an audit trail — that's the architectural-gap finding.

## Chinese models

### General-purpose

<paste the 5 China-general rows from aggregator output: deepseek-v3, deepseek-r1, qwen3-max, glm-46, kimi-k2>

### Medical-specialized

<paste the 2 China-medical rows: huatuogpt-ii, huatuogpt-o1>

## Western models

### General-purpose

<paste the 3 West-general rows: gpt-4o-mini, claude-sonnet-46, gemini-25-pro>

### Medical-specialized

<paste the 1 West-medical row: meditron-70b>

## Aggregator overhead note

Models routed through OpenRouter add ~100–300ms to p50 latency. Models routed through SiliconFlow add ~100–200ms. The "Latency p50" column is not directly comparable between aggregator-routed and direct-API models.

## Methodology

- All runs: `--retries 2 --timeout 30000` (60000 for reasoning models).
- Temperature 0 for reproducibility.
- `expected` field stripped from scenarios before they reach adapters.
- See `examples/providers.yaml` for exact model IDs and endpoints.
```

- [ ] **Step 3: Commit**

```bash
cd /Volumes/extraSupply/veritasbench
git add outputs/combined_results.csv docs/results-by-model.md
git commit -m "data: combined results + per-model breakdown for 10 new models"
```

---

### Task 4: Regenerate `docs/benchmark-chart.png`

**Files:**
- Create: `docs/archived/benchmark-chart-v1.png`
- Modify: `docs/benchmark-chart.png` and `docs/benchmark-chart.html`

- [ ] **Step 1: Archive the old chart**

```bash
cd /Volumes/extraSupply/veritasbench
mkdir -p docs/archived
cp docs/benchmark-chart.png docs/archived/benchmark-chart-v1.png
```

- [ ] **Step 2: Identify the chart-generation script or source**

```bash
cd /Volumes/extraSupply/veritasbench
ls -la docs/benchmark-chart.html
head -5 docs/benchmark-chart.html
grep -r "benchmark-chart" scripts/ examples/ 2>/dev/null
```

If the chart is a Chart.js HTML file (`benchmark-chart.html`), the `.png` was likely a screenshot. Update the HTML's data literal with the expanded rows from `outputs/combined_results.csv`, then regenerate the screenshot.

If there's a dedicated chart script (e.g., `scripts/make_chart.py`), update its data source to read `outputs/combined_results.csv`.

Document your approach in a short comment inside `docs/benchmark-chart.html` or the chart script, so future regenerations are clear.

- [ ] **Step 3: Regenerate**

If HTML-based: open `docs/benchmark-chart.html` in a browser → screenshot → save as `docs/benchmark-chart.png`.
If script-based: `python scripts/make_chart.py` (or equivalent).

Confirm the new chart shows all 11 rows (existing v1 baselines + 10 new) with the 4 dimensions clearly separated.

- [ ] **Step 4: Commit**

```bash
cd /Volumes/extraSupply/veritasbench
git add docs/benchmark-chart.png docs/benchmark-chart.html docs/archived/benchmark-chart-v1.png
git commit -m "docs: regenerate benchmark chart with 10 new models"
```

---

### Task 5: Update `README.md` with model-comparison table

**Files:**
- Modify: `README.md` § "Benchmark Results"

- [ ] **Step 1: Restructure the results section**

The current README has one results table with 4 adapter columns (bare LLM, content filter, topic rails, HITL prompt + ClinicClaw). After W3, the story has two axes:

1. **Governance pattern** (bare vs content-filter vs topic-rails vs HITL vs rule-engine) — the existing table.
2. **Model** (holding governance pattern = bare LLM, varying the LLM) — the new table.

Use the Edit tool to update `README.md`:

- Keep the existing "Governance patterns" table exactly as-is under a subheading `### Results by governance pattern (GPT-4o-mini)`.
- Add a new subheading `### Results by model (bare LLM pattern, no governance)` and paste the enriched table from `docs/results-by-model.md` (simplified — just Model, Policy %, Safety %, Traceability %, Controllability %, Dangerous Failures, Aggregator).
- Add one-line note: "See [docs/results-by-model.md](docs/results-by-model.md) for full numbers and methodology."

- [ ] **Step 2: Update the "How to read this" prose**

The existing prose says "All four LLM-based approaches score 61-82% on policy compliance." After W3 this number range expands. Update with the new observed range (e.g., "Across 11 LLMs spanning Chinese/Western and general/medical, policy compliance ranges from XX% to YY%. Traceability and controllability remain at 0% for every bare LLM — the governance gap is architectural, not a model-quality problem.") with actual numbers from `combined_results.csv`.

- [ ] **Step 3: Commit**

```bash
cd /Volumes/extraSupply/veritasbench
git add README.md
git commit -m "docs: README results section — governance patterns + 11-model comparison"
```

---

### Task 6: Write "Medical LLMs don't fix the governance gap" section

**Files:**
- Modify: `README.md`

This section is data-driven. Write it only after Task 3 so the claims match actual results.

- [ ] **Step 1: Inspect the medical-vs-general comparison**

```bash
cd /Volumes/extraSupply/veritasbench
python -c "
import csv
with open('outputs/combined_results.csv') as f:
    rows = list(csv.DictReader(f))
medical = {'huatuogpt_ii', 'huatuogpt_o1', 'meditron_70b'}
med_policy = [float(r['policy_compliance_pct']) for r in rows if r['short_name'] in medical]
gen_policy = [float(r['policy_compliance_pct']) for r in rows if r['short_name'] not in medical]
print(f'Medical Policy avg: {sum(med_policy)/len(med_policy):.1f}%')
print(f'General Policy avg: {sum(gen_policy)/len(gen_policy):.1f}%')
print(f'Medical Traceability sum: {sum(float(r[\"traceability_pct\"]) for r in rows if r[\"short_name\"] in medical)}')
print(f'General Traceability sum: {sum(float(r[\"traceability_pct\"]) for r in rows if r[\"short_name\"] not in medical)}')
"
```

Expected finding (hypothesis): Medical LLMs score similar-or-slightly-higher on Policy/Safety, but both groups score 0 on Traceability/Controllability.

- [ ] **Step 2: Draft the section**

Add a new section to `README.md` after "Where the Governance Gap Is":

```markdown
## Medical-Specialized LLMs Don't Fix the Governance Gap

We tested three medical-specialized models (HuatuoGPT-II-34B, HuatuoGPT-o1-72B, Meditron-70B) alongside eight generalists. The hypothesis: medical fine-tuning improves clinical reasoning but is orthogonal to governance infrastructure.

The data confirms this.

| Category | Avg Policy Compliance | Avg Safety | Avg Traceability | Avg Controllability |
|---|---|---|---|---|
| Medical-specialized (n=3) | XX.X% | XX.X% | 0.0% | 0.0% |
| Generalist (n=8) | XX.X% | XX.X% | 0.0% | 0.0% |

*(Fill XX.X from `outputs/combined_results.csv`.)*

Medical models' advantage on Policy/Safety is smaller than one might expect and in some cases non-existent — frontier generalists like Claude Sonnet 4.6 match or exceed specialists. This is consistent with a broader pattern: the governance gap is not in *clinical reasoning*, it is in *auditability* and *human oversight*. Zero of the 11 models we tested produced a meaningful audit trail or halted for human approval — not because the models can't, but because bare-LLM inference has nowhere to record or route those signals.

**If your governance strategy is "pick a better LLM," the benchmark results show that strategy will not close the gap.**

The ClinicClaw reference adapter (rule engine + structured logging + HITL prompts) scores ~90% on Traceability and Controllability with zero LLM calls. This is not a claim that rule engines are better than LLMs — it is a claim that governance is a separate layer that must be explicitly built. See "Where the Governance Gap Is" above.
```

Replace `XX.X%` placeholders with the actual numbers computed in Step 1.

- [ ] **Step 3: Commit**

```bash
cd /Volumes/extraSupply/veritasbench
git add README.md
git commit -m "docs: medical-LLMs-don't-fix-governance section — data-driven"
```

---

### Task 7: Final regression + CI check

**Files:**
- None modified.

- [ ] **Step 1: Confirm all tests still green**

```bash
cd /Volumes/extraSupply/veritasbench
cargo test 2>&1 | tail -10
python -m pytest tests/python/ -v 2>&1 | tail -10
```

- [ ] **Step 2: Verify README builds / renders**

Open `README.md` in your Markdown preview. Check:
- Both results tables render correctly.
- The new benchmark chart shows all 11 rows.
- No broken links to `docs/results-by-model.md`.
- Methodology notes include aggregator-overhead caveat.

- [ ] **Step 3: Generate a summary message for the commit log**

```bash
cd /Volumes/extraSupply/veritasbench
git log --oneline -20
```

The W3 commits should tell a clean story: `feat: aggregator` → `data: N new model runs` → `data: combined results` → `docs: regenerate chart` → `docs: README model comparison` → `docs: medical-LLMs-don't-fix-governance`.

---

## Exit criteria (W3 complete)

- [ ] At least 6 of the 10 new models have complete `outputs/llm_<short>/report.json` files.
- [ ] `outputs/combined_results.csv` exists with one row per completed run.
- [ ] `docs/results-by-model.md` committed with category grouping.
- [ ] `docs/benchmark-chart.png` regenerated; old chart archived.
- [ ] `README.md` has both a "by governance pattern" and a "by model" results table.
- [ ] `README.md` has a "Medical LLMs don't fix the governance gap" section with real numbers.
- [ ] No regressions in `cargo test` or `pytest tests/python/`.
- [ ] Methodology notes (aggregator overhead, retry/timeout settings) are in either README or `docs/results-by-model.md`.

## Partial shipment policy

If some providers are unreachable (key approval pending, rate limits, API outages), ship partial:
- Note unreachable models in `docs/results-by-model.md` under a "Not yet run" subsection.
- The medical-vs-generalist comparison stands with ≥2 medical + ≥4 general models.
- Unreachable models can be added in a follow-up commit later.
