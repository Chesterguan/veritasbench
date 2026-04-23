# Chinese & Medical LLM Benchmark Expansion — Design Spec

> Date: 2026-04-23
> Status: Draft (awaiting user review)
> Scope: Scoring audit + multi-provider adapter infrastructure + 10-model benchmark runs

## 1. Overview

VeritasBench v1 ships with a single tested model family (OpenAI GPT-4o-mini) across four governance adapters. Gemini appears in the ground-truth validation pipeline (`scripts/llm_judge_validate.py`) but is never benchmarked as a tested model. This spec expands the benchmark matrix to 10 new models spanning Chinese/Western geography and generalist/medical specialization, while auditing the scoring code for math or semantic gaps and eliminating an adapter-protocol friction point that blocks non-OpenAI providers.

### Goals

1. **Audit the scoring code** for math correctness, dimension applicability, semantic traceability enforcement, blind-mode soundness, and consistency between published README numbers and raw outputs.
2. **Collapse per-provider adapter explosion** into one generic OpenAI-compatible adapter plus two optional native-SDK adapters, so any of 10+ providers can be benchmarked by changing three env vars rather than writing new adapter code.
3. **Produce a 10-model results table** with both Chinese and Western, both generalist and medical-specialized, testing the core thesis: *governance is an architecture problem, not a model problem.*

### Non-goals

- No scenario-set expansion (no finance, legal, multi-step, or temporal scenarios).
- No new scoring dimensions.
- No changes to the `expected` ground-truth labels.
- No re-run of published v1 GPT-4o-mini results — new models append to the results table; existing results remain authoritative.
- No LLM-as-judge for the new runs — trust the existing multi-model consensus `expected` labels.
- No modification to governance-pattern adapters (`llm_with_content_filter.py`, `llm_with_topic_rails.py`, `llm_with_hitl_prompt.py`) — they test patterns, not models, and their OpenAI coupling preserves reproducibility of published v1.

## 2. Workstream 1: Scoring Audit

### 2.1 Scope

Read everything in:

- `crates/veritasbench-eval/src/{policy,safety,traceability,controllability,consistency,aggregate,lib}.rs`
- `crates/veritasbench-core/src/score.rs`
- `crates/veritasbench-core/src/scenario.rs` (for `--blind` field handling)
- `crates/veritasbench-report/src/{json,markdown,lib}.rs`
- `crates/veritasbench-runner/src/adapter.rs` (for scenario-stripping behavior)

### 2.2 Audit checks

1. **Math correctness** — formulas in each scorer; aggregate weights and denominators; handling of zero/NaN; rounding-vs-truncation when computing percentages.
2. **Dimension applicability** — each scenario type awards the right dimensions. Existing `aggregate::tests::test_*_dimensions` unit tests suggest per-type logic; audit every type×dimension pair against the prose in `README.md` §"System-level governance" and `docs/adapter-protocol.md` §Scoring.
3. **Semantic traceability** — README claims the 3rd traceability point requires "meaningful reason referencing scenario context." Identify whether this is enforced by keyword match, length heuristic, LLM judge, or something else. Report the mechanism and its failure modes.
4. **Accountability-gap chain length math** — README says traceability requires "audit entries proportional to unattributed steps in the decision chain." Verify this matches `test_chain_enough_entries_scores_3` and `test_chain_too_few_entries_scores_0` behavior.
5. **Blind mode** — `--blind` strips `scenario_type`. Verify:
   - Is it stripped at the scenario-load layer or at the adapter-pipe layer?
   - Are nested fields that reveal type (e.g. `prior_state.conflicting_policies`, `prior_state.system_trigger`, `prior_state.decision_chain`) also stripped, or does blind mode leak type via structural signals?
   - Is `expected` stripped in both blind and non-blind modes?
6. **README-number cross-check** — re-derive the 81%, 72%, 0%, 0% (bare LLM) and 91%, 82%, 92%, 90% (ClinicClaw) numbers from `outputs/bare_llm_v1/` and `outputs/cliniclaw_v1/` JSON. Report any discrepancy.
7. **Dangerous-failure counts** — the "allow when deny/block was expected" counts must match the prose definition. Check `crates/veritasbench-eval/` for where this is computed.
8. **Latency accounting** — confirm p50 latency is per-scenario end-to-end (spawn → exit), not just the adapter's LLM call. This matters for the aggregator-overhead note in W3.

### 2.3 Deliverable

`docs/audits/2026-04-23-scoring-audit.md` — findings in a table with columns: `severity` (critical/high/medium/low), `file:line`, `description`, `proposed fix`, `fix effort`. Critical/high issues become blocking PRs before W3 runs start; medium/low become follow-up issues.

### 2.4 Exit criteria

- Audit document committed.
- Every critical/high finding has a merged fix.
- `cargo test` still passes after fixes.
- If README numbers changed due to fixes, re-run the two existing adapters (`bare_llm_v1`, `cliniclaw_v1`) and update the numbers.

## 3. Workstream 2: Adapter Infrastructure

### 3.1 Design principle

A VeritasBench adapter is a subprocess that reads a scenario from stdin and writes an `AdapterResult` to stdout. The benchmark doesn't care what's inside — it only cares about the I/O contract. So "supporting 10 providers" should not mean "10 adapter files." It should mean **one adapter that reads provider config from env vars, plus native-SDK adapters only where they unlock provider-specific wins** (Anthropic prompt caching, Google context caching).

### 3.2 New files

**`examples/llm_openai_compat.py`** — generic OpenAI-compatible adapter.

- Reads env vars: `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `VERITASBENCH_MODEL`.
- Shares prompt-building logic with `llm_bare.py` (extracted to `examples/_llm_shared.py`).
- Handles `response_format={"type":"json_object"}` fallback: some providers (notably DeepSeek-R1 in reasoning mode, some Chinese providers) don't support it. On receiving a 400 mentioning `response_format`, retry without the flag and regex-parse a JSON object out of the response text. Log the fallback to stderr.
- Handles reasoning-model response shape: some providers emit `<think>...</think>` or a separate reasoning field. Strip/skip reasoning, extract the final answer JSON.
- Normalizes `decision` to one of the three valid values; defaults to `"allow"` on parse failure (same as existing `llm_bare.py`).
- Bare-LLM output shape: empty `audit_entries`, `execution_halted=False`, `human_notified=False` — matches `llm_bare.py` exactly, because we're testing the model, not a governance pattern.

**`examples/llm_anthropic.py`** — native Anthropic SDK adapter.

- Reads env vars: `ANTHROPIC_API_KEY`, `VERITASBENCH_MODEL` (default `claude-sonnet-4-6`).
- Uses `anthropic.Anthropic().messages.create()` with prompt caching on the system prompt.
- Same I/O shape as `llm_openai_compat.py`.
- Optional: if the user routes Claude through OpenRouter, they use `llm_openai_compat.py` instead. This file exists for direct Anthropic API users who want prompt caching.

**`examples/llm_gemini.py`** — native Google `google-genai` SDK adapter.

- Reads env vars: `GEMINI_API_KEY`, `VERITASBENCH_MODEL` (default `gemini-2.5-pro`).
- Uses context caching.
- Same I/O shape.
- Optional; OpenRouter path also works.

### 3.3 Refactored files

**`examples/_llm_shared.py`** — new shared module.

- `build_prompt(scenario: dict) -> str` — the existing prompt-building logic from `llm_bare.py`, extracted verbatim.
- `normalize_decision(raw: str) -> str` — canonicalize to `allow` | `deny` | `blocked_pending_approval`.
- `build_bare_result(decision: str, scenario: dict) -> dict` — the "bare LLM" output shape (empty audit, no halt, no human notify, `output_content` mirrored for allow).

**`examples/llm_bare.py`** — refactored to import from `_llm_shared.py`. Semantic behavior unchanged. Existing `outputs/bare_llm_v1/` run remains reproducible because the effective logic is identical.

### 3.4 New support files

**`examples/providers.yaml`** — short-name → provider config table. Documentation + source of truth for `scripts/run_model.py`. Example rows:

```yaml
gpt-4o-mini:
  adapter: llm_openai_compat.py
  env:
    OPENAI_BASE_URL: https://api.openai.com/v1
    VERITASBENCH_MODEL: gpt-4o-mini
  key_env: OPENAI_API_KEY

deepseek-v3:
  adapter: llm_openai_compat.py
  env:
    OPENAI_BASE_URL: https://openrouter.ai/api/v1
    VERITASBENCH_MODEL: deepseek/deepseek-chat-v3.2
  key_env: OPENROUTER_API_KEY

huatuogpt-o1:
  adapter: llm_openai_compat.py
  env:
    OPENAI_BASE_URL: https://api.siliconflow.cn/v1
    VERITASBENCH_MODEL: FreedomIntelligence/HuatuoGPT-o1-72B
  key_env: SILICONFLOW_API_KEY

baichuan-m2:
  adapter: llm_openai_compat.py
  env:
    OPENAI_BASE_URL: https://api.baichuan-ai.com/v1
    VERITASBENCH_MODEL: Baichuan-M2
  key_env: BAICHUAN_API_KEY

claude-sonnet-46:
  adapter: llm_openai_compat.py  # or llm_anthropic.py for direct
  env:
    OPENAI_BASE_URL: https://openrouter.ai/api/v1
    VERITASBENCH_MODEL: anthropic/claude-sonnet-4.6
  key_env: OPENROUTER_API_KEY
```

Full 11-row table (existing GPT-4o-mini + 10 new) in §4.2.

**`scripts/run_model.py`** — thin driver.

```
python scripts/run_model.py <short-name> [--suite healthcare_v1] [--output outputs/<short-name>] [--retries 2] [--timeout 30000]
```

Behavior:
1. Load `examples/providers.yaml`; error if short-name is missing.
2. Verify the key env var is set; error with a clear message if missing.
3. Set `OPENAI_API_KEY` to the value of the key_env var (so the adapter reads it uniformly).
4. Set all other env vars from the `env` block.
5. Default `--output` to `outputs/llm_<short_name>/`.
6. Invoke `cargo run --release -p veritasbench-cli -- run --adapter <adapter> --suite <suite> --output <output> --retries 2 --timeout 30000`.
7. Propagate exit code.

### 3.5 Tests

- **Unit tests**: mock HTTP server (Python `http.server` or `pytest-httpserver`) returning a canonical OAI-compat chat completion. Assert `llm_openai_compat.py` produces a valid `AdapterResult`, handles 400-on-response_format fallback, handles reasoning-model shapes.
- **Integration test**: add to `tests/integration.rs` — spawn `llm_openai_compat.py` with a fake `OPENAI_BASE_URL` pointing at a Rust-side mock server, verify the full pipeline parses the result.
- Existing integration tests remain green (no regressions in `bare_llm_simulated`, `cliniclaw_simulated`, etc.).

### 3.6 Explicitly out of scope

- No changes to `llm_with_content_filter.py`, `llm_with_topic_rails.py`, `llm_with_hitl_prompt.py`. These test governance *patterns* on top of a fixed OpenAI base, and their published v1 numbers must remain reproducible.
- No streaming, no async batching, no in-adapter retries (runner-level `--retries` is sufficient).
- No adapter-auto-discovery of provider (don't try to detect "this is a Chinese model" from the base URL).
- No per-model prompt tuning — every model sees the same prompt. The benchmark compares governance-architecture performance holding the prompt constant.

### 3.7 Exit criteria

- `examples/llm_openai_compat.py`, `examples/llm_anthropic.py`, `examples/llm_gemini.py`, `examples/_llm_shared.py`, `examples/providers.yaml`, `scripts/run_model.py` committed.
- `veritasbench validate --adapter llm_openai_compat.py` passes with `OPENAI_BASE_URL=https://api.openai.com/v1 OPENAI_API_KEY=<key> VERITASBENCH_MODEL=gpt-4o-mini`.
- New unit + integration tests pass.
- Existing 84 Rust tests + simulated-adapter integration tests remain green.
- `llm_bare.py` refactor preserves byte-identical output on a 10-scenario smoke test against the v1 suite.

## 4. Workstream 3: 10-Model Benchmark Runs

### 4.1 Sequencing

User-executed as API keys arrive. No strict order required; each model is independent. Recommended run order (cheap-to-expensive, to catch infra bugs early):

1. DeepSeek-V3.2 (cheapest, well-documented)
2. Qwen3-Max
3. GLM-4.6
4. Kimi K2
5. DeepSeek-R1 (reasoning — tests the reasoning-model response-shape handling)
6. Gemini 2.5 Pro
7. Claude Sonnet 4.6
8. Baichuan-M2 (direct key, medical)
9. HuatuoGPT-o1-72B (SiliconFlow, medical)
10. Meditron-70B (Together.ai or OpenRouter, medical)

### 4.2 Model × provider matrix

| # | Short name | Model | Category | Adapter | Provider | key_env |
|---|---|---|---|---|---|---|
| 0 | `gpt-4o-mini` | GPT-4o-mini | Western general (existing baseline) | `llm_openai_compat.py` | OpenAI | `OPENAI_API_KEY` |
| 1 | `deepseek-v3` | DeepSeek-V3.2 | Chinese general | `llm_openai_compat.py` | OpenRouter | `OPENROUTER_API_KEY` |
| 2 | `deepseek-r1` | DeepSeek-R1 | Chinese reasoning | `llm_openai_compat.py` | OpenRouter | `OPENROUTER_API_KEY` |
| 3 | `qwen3-max` | Qwen3-Max | Chinese general | `llm_openai_compat.py` | OpenRouter | `OPENROUTER_API_KEY` |
| 4 | `glm-46` | GLM-4.6 | Chinese general | `llm_openai_compat.py` | OpenRouter | `OPENROUTER_API_KEY` |
| 5 | `kimi-k2` | Kimi K2 | Chinese general | `llm_openai_compat.py` | OpenRouter | `OPENROUTER_API_KEY` |
| 6 | `claude-sonnet-46` | Claude Sonnet 4.6 | Western general | `llm_openai_compat.py` | OpenRouter | `OPENROUTER_API_KEY` |
| 7 | `gemini-25-pro` | Gemini 2.5 Pro | Western general | `llm_openai_compat.py` | OpenRouter | `OPENROUTER_API_KEY` |
| 8 | `baichuan-m2` | Baichuan-M2 | Chinese medical | `llm_openai_compat.py` | Baichuan Open Platform | `BAICHUAN_API_KEY` |
| 9 | `huatuogpt-o1` | HuatuoGPT-o1-72B | Chinese medical | `llm_openai_compat.py` | SiliconFlow | `SILICONFLOW_API_KEY` |
| 10 | `meditron-70b` | Meditron-70B | Western medical | `llm_openai_compat.py` | OpenRouter or Together.ai | `OPENROUTER_API_KEY` |

Minimum keys needed: **3** — OpenRouter, SiliconFlow, Baichuan. OpenAI key stays as-is for the baseline.

### 4.3 Output layout

```
outputs/
  bare_llm_v1/             (existing — preserved, do not overwrite)
  cliniclaw_v1/            (existing — preserved)
  llm_deepseek_v3/
  llm_deepseek_r1/
  llm_qwen3_max/
  llm_glm_46/
  llm_kimi_k2/
  llm_claude_sonnet_46/
  llm_gemini_25_pro/
  llm_baichuan_m2/
  llm_huatuogpt_o1/
  llm_meditron_70b/
```

Each directory contains the standard VeritasBench output: per-scenario JSONs, `report.json`, `report.md`.

### 4.4 Reporting deliverables

1. **`scripts/aggregate_models.py`** — reads all `outputs/llm_*/` dirs, emits `outputs/combined_results.csv` and a Markdown table grouped by (Geography × General/Medical).
2. **Updated `docs/benchmark-chart.png`** — regenerated from the expanded CSV using the same chart-generation logic. Old chart archived at `docs/archived/benchmark-chart-v1.png`.
3. **New `docs/results-by-model.md`** — 11-row table with columns: Model, Category, Policy %, Safety %, Traceability %, Controllability %, Dangerous Failures, Latency p50 (ms), Aggregator (if any).
4. **README update** — replace the current 4-adapter results table with an "adapters" table (governance patterns) and a "models" table (same governance pattern, different LLM backing it). The existing 4 adapter rows stay in the adapters table; the 10 new models plus the GPT-4o-mini baseline form the models table.
5. **New README section: "Medical LLMs don't fix the governance gap"** — short writeup driven by actual data. Expected finding: medical-specialized models may improve Policy/Safety modestly but score ~0 on Traceability/Controllability, reinforcing the architectural thesis. Report the honest result even if it surprises us.

### 4.5 Methodology notes (to add to README / methodology section)

- **Aggregator overhead**: results routed through OpenRouter or SiliconFlow have ~100–300ms additional p50 latency vs direct-provider runs. Latency is reported but not directly comparable across aggregator/direct lines. See the per-row "Aggregator" column.
- **Reasoning models**: DeepSeek-R1 and HuatuoGPT-o1 emit chain-of-thought tokens. These inflate latency and output-token costs but are stripped before JSON parsing.
- **Rate limits**: `--retries 2 --timeout 30000` is the standard invocation. Skipped scenarios (rare, non-retriable timeouts) are excluded from scoring denominators, matching existing v1 methodology.
- **Model versions pinned**: every model ID in `providers.yaml` is pinned to a specific version string so runs are reproducible. Provider-side silent updates to a floating alias would invalidate reproducibility.

### 4.6 Exit criteria

- All 10 new runs complete (can ship partial if some providers are unreachable — note which).
- `docs/results-by-model.md` committed with the new table.
- README updated.
- Chart regenerated.
- `outputs/combined_results.csv` committed so downstream researchers can reproduce the tables.

## 5. Open questions — answered

| Question | Decision |
|---|---|
| Aggregator-vs-direct latency methodology | (a) Note overhead in methodology; accept the noise. Add an "Aggregator" column to the results table. |
| Failure policy for mid-run API errors | `--retries 2 --timeout 30000` baked into `scripts/run_model.py` default. |
| Failed-adapter reconstruction from collaborator's instructions | Skip. The generic OAI-compat design addresses the root cause (hardcoded `OpenAI()` client). Revisit if the new infra doesn't unblock the collaborator. |

## 6. Success criteria (overall)

1. Scoring audit produces a written document; all critical/high findings are fixed.
2. Three env vars (`OPENAI_API_KEY`, `OPENAI_BASE_URL`, `VERITASBENCH_MODEL`) are sufficient to benchmark any OpenAI-compatible model — no new adapter code required.
3. At least 6 of the 10 new models have full runs against the v1 suite (soft target; partial shipment acceptable if some providers are unreachable from the user's network).
4. The expanded results table supports or refutes "medical LLMs don't close the governance gap" on real data, not speculation.
5. Published v1 GPT-4o-mini numbers remain unchanged (or are updated alongside an explicit audit-fix explanation if any scoring bugs were found).

## 7. Sequencing summary

```
W1 (audit)  ──────────►  W1 fixes  ──────►
                                            │
                                            ▼
W2 (adapter infra — can start in parallel) ─┤
                                            ▼
                                        User runs W3 as keys arrive
                                            │
                                            ▼
                                        W3 reporting (chart + tables + README)
```

W1 and W2 can be prepared in parallel because they touch disjoint codebases (Rust eval vs Python adapters). W3 waits on both: scoring bugs would contaminate new numbers, and adapter infra is a prerequisite to running the new models.
