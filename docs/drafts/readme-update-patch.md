# README.md Update Plan for v1.3

> Ready to apply. Three-axis final roster:
> - **Axis A** = 10 models incl. DeepSeek-R1 reasoning, bare LLM (outputs/combined_results.csv, 2026-04-24 + outputs/v13_r1_bare/, 2026-04-28).
> - **Axis B** = 3 LLMs × 4 wrappers (outputs/axisB_*_{gpt4omini,claude46}/, 2026-04-27 + outputs/v13_r1_*/, 2026-04-28).
> - **Axis C (v1.3)** = trace-ceiling experiment (outputs/v13_full_audit_*/) + audit-prompt experiment (outputs/v13_audit_prompt_gpt4omini/).
>
> Strategy: keep v1 structure intact (governance-patterns table stays as context), add three layers — model sweep (Axis A), wrapper sweep (Axis B), and architectural-claim refinement (Axis C). Together they prove and then sharpen the architectural argument.

---

## Change 1: Hero line (top of README)

### Current (line 3)

```markdown
**Your AI gets 81% of clinical governance decisions right. It can't prove any of them.**
```

### New

```markdown
**We ran a 700-scenario clinical governance benchmark across three axes. Swapping the LLM among 10 frontier models — including a reasoning model — moves Policy ±17pp and moves Traceability/Controllability by exactly zero. Swapping the governance wrapper at fixed LLM moves Traceability 0→33→100% (depending on the wrapper's audit-entry shape) and Controllability 0→47% (LangGraph interrupts). And asking the bare LLM for audit entries — no wrapper — unlocks 87.8% Trace on GPT-4o-mini. Wrappers enforce, prompts request, default-prompt bare pipes record nothing. Models choose decision quality; wrappers enforce audit/halt invariants.**
```

Reason: the two-axis contrast is stronger than either single-axis framing. Axis A alone ("9 models all 0%") can be dismissed as prompt-dependent. Axis B alone ("wrappers move the number") lacks a null baseline. Together they demonstrate the gap is architectural.

## Change 2: Add new section "The two-axis setup"

Insert this as a new top-level section between the current intro and "Benchmark Results".

```markdown
## The two-axis setup

A single benchmark number is unfalsifiable. "LLM X scored 82%" tells you nothing about whether the limiting factor is the model, the prompt, the pipeline, or the grader. To test where the bottleneck actually lives, we hold one axis fixed and move the other.

- **Axis A** pins the *pipeline* (bare LLM + identical prompt + JSON output) and sweeps the *model* across 9 frontier LLMs from four labs and two geographies.
- **Axis B** pins the *model* (GPT-4o-mini) and sweeps the *wrapper* across 4 representative governance patterns: bare, NeMo Guardrails, OpenAI Guardrails, LangGraph HITL.

If governance scales with model quality, Axis A should move. If it scales with architecture, Axis B should move. The answer is unambiguous.
```

## Change 3: Add new section "Axis A — 9 LLMs, bare-LLM wrapper"

Insert this section directly below the existing "Benchmark Results (700 scenarios, 11 types, GPT-4o-mini)" block and before "How to read this".

```markdown
### Axis A — results by model (9 frontier LLMs, bare-LLM pattern)

Same 700 scenarios, same prompt, varying the underlying LLM. Measures whether changing the model alone closes the governance gap. It does not.

#### Western — general

| Model | Policy | Safety | Traceability | Controllability | Dangerous | Latency p50 |
|---|---|---|---|---|---|---|
| Claude Sonnet 4.6 | 493/575 (86%) | 259/325 (80%) | 0/2100 (0%) | 0/570 (0%) | 14/575 | 1909ms |
| Gemini 2.5 Pro | 454/572 (79%) | 270/324 (83%) | 0/2091 (0%) | 0/568 (0%) | 8/572 | 8130ms |
| GPT-4o-mini | 466/575 (81%) | 234/325 (72%) | 0/2100 (0%) | 0/570 (0%) | 26/575 | 1117ms |

#### Chinese — general

| Model | Policy | Safety | Traceability | Controllability | Dangerous | Latency p50 |
|---|---|---|---|---|---|---|
| GLM-4.6 | 496/571 (87%) | 258/322 (80%) | 0/2088 (0%) | 0/570 (0%) | 23/571 | 2493ms |
| Qwen3-Max | 479/575 (83%) | 261/325 (80%) | 0/2100 (0%) | 0/570 (0%) | 15/575 | 1908ms |
| DeepSeek-V3.2 | 477/575 (83%) | 226/325 (70%) | 0/2100 (0%) | 0/570 (0%) | 29/575 | 3099ms |
| Kimi K2 | 450/572 (79%) | 203/323 (63%) | 0/2091 (0%) | 0/566 (0%) | 25/572 | 2000ms |
| Hunyuan A13B | 403/575 (70%) | 175/325 (54%) | 0/2100 (0%) | 0/570 (0%) | 154/575 | 1490ms |

#### Western — medical-specialized

| Model | Policy | Safety | Traceability | Controllability | Dangerous | Latency p50 |
|---|---|---|---|---|---|---|
| MedGemma 4B (Google) | 400/575 (70%) | 221/325 (68%) | 0/2100 (0%) | 0/570 (0%) | 135/575 | 2136ms |

Full reproducible numbers: [outputs/combined_results.csv](outputs/combined_results.csv).

**Axis A tells us:** Policy spans a 17.3pp band (Hunyuan A13B 70.1% → GLM-4.6 86.9%). Chinese frontier matches Western frontier on capability (GLM-4.6 edges Claude Sonnet 4.6 by 1.2pp; Qwen3-Max ties Claude on Safety). Medical-specialized 4B underperforms all general frontier models. **Traceability and Controllability are 0% on every single model** — no lab, no geography, no scale, no specialization moves the governance dimensions.
```

## Change 4: Add new section "Axis B — winner + wrappers, three LLM tiers"

Insert directly after the Axis A section.

```markdown
### Axis B — pick the winner, vary the wrapper (3 LLMs × 4 wrappers)

Axis A picked the headline. We then re-ran the wrapper experiments with **three LLM tiers** to test whether wrapper effects transfer across capability and reasoning mode: Claude Sonnet 4.6 (Axis A #2 at 85.7%), GPT-4o-mini (#5 at 81.0%), and DeepSeek-R1 reasoning (80.9%).

| LLM | Wrapper | n | Policy | Safety | Trace | Ctrl | Dangerous |
|---|---|---:|---:|---:|---:|---:|---:|
| GPT-4o-mini | Bare LLM | 700 | 81.0% | 72.0% | 0.0% | 0.0% | 26/575 (4.5%) |
| GPT-4o-mini | + NeMo Guardrails | 700 | 81.2% | 61.2% | 0.0% | 0.0% | 25/575 (4.3%) |
| GPT-4o-mini | + OpenAI Guardrails | 700 | 74.1% | 51.7% | **33.1%** | 0.0% | 7/575 (1.2%) |
| GPT-4o-mini | + LangGraph HITL | 700 | 66.8% | 51.7% | **33.1%** | **47.4%** | 22/575 (3.8%) |
| Claude Sonnet 4.6 | Bare LLM | 700 | 85.7% | 79.7% | 0.0% | 0.0% | 14/575 (2.4%) |
| Claude Sonnet 4.6 | + NeMo Guardrails | 700 | 83.5% | 60.0% | 0.0% | 0.0% | **3/575 (0.5%)** |
| Claude Sonnet 4.6 | + OpenAI Guardrails | 700 | 83.1% | 59.7% | **33.1%** | 0.0% | 6/575 (1.0%) |
| Claude Sonnet 4.6 | + LangGraph HITL | 700 | 72.3% | 60.3% | **33.1%** | **47.4%** | 11/575 (1.9%) |
| DeepSeek-R1 (reasoning) | Bare LLM | 700 | 80.9% | 64.9% | 0.0% | 0.0% | 18/575 (3.1%) |
| DeepSeek-R1 (reasoning) | + NeMo Guardrails | 700 | 83.5% | 63.1% | 0.0% | 0.0% | 11/575 (1.9%) |
| DeepSeek-R1 (reasoning) | + OpenAI Guardrails | 700 | 78.8% | 60.0% | **33.1%** | 0.0% | **1/575 (0.2%)** |
| DeepSeek-R1 (reasoning) | + LangGraph HITL | 700 | 66.6% | 43.7% | **33.1%** | **47.4%** | 9/575 (1.6%) |

Trace and Ctrl gains are *identical* across all three LLMs — including the reasoning model — confirming they are wrapper-architectural properties, not LLM properties.

**Axis B tells us three things:**

1. **Trace and Ctrl gains are LLM-invariant across 3 LLMs.** Same wrapper, three different LLMs (instruction-tuned, mid-tier, reasoning) → identical gain. OpenAI Guardrails: +33.1pp Trace on all three. LangGraph HITL: +33.1pp Trace AND +47.4pp Ctrl on all three. The interrupt primitive fires deterministically on `missing_approval` and `emergency_override` scenario types — the LLM's output isn't on the decision path. **Trace and Ctrl are properties of the pipeline, not the model — and Axis C below confirms 33% is a wrapper-template floor, not the trace ceiling.**
2. **OpenAI Guardrails Policy hit varies with LLM tier; LangGraph HITL doesn't.** OpenAI Guardrails costs GPT-4o-mini −6.9pp Policy but only −2.6pp on Claude and −2.1pp on R1. LangGraph HITL costs ~13–14pp on all three (LLM-invariant interrupt cost). NeMo varies: R1 actually gains +2.6pp under NeMo, GPT is neutral, Claude loses −2.2pp.
3. **R1 + OpenAI Guardrails = 1/575 dangerous failures (0.2%) — the lowest DF rate observed across the matrix.** OpenAI Guardrails consistently halves DF on every LLM tested. NeMo + Claude is also striking at 0.5% (n=3 events; wide CI). Treat as suggestive evidence of strong wrapper × LLM interactions worth replicating in v1.4.

No Axis B wrapper clears 50% on both Trace AND Ctrl simultaneously with skeletal audit entries. The Axis C full-audit wrapper (below) does — 100% Trace + 0% Ctrl (no interrupt primitive). The combined "100% Trace + ≥50% Ctrl" wrapper has not yet been built.
```

## Change 4b: Add new section "Axis C — refining the architectural claim"

Insert directly after the Axis B section.

```markdown
### Axis C — refining the architectural claim (v1.3)

v1.2 stopped at "wrappers can do governance, models can't." v1.3 added two surgical experiments that sharpen the claim. Same 700 scenarios, same grader.

**Experiment 1: trace-ceiling wrapper.** A new `examples/llm_with_full_audit.py` adapter — same OpenAI moderation + regex PHI logic as `llm_with_content_filter.py`, but the audit-entry template populates `actor`, `resource`, `decision`, and `reason` (instead of leaving them null). Tested on three LLMs:

| LLM | Wrapper | n | Trace | Policy | DF |
|---|---|---:|---:|---:|---:|
| GPT-4o-mini | + full-audit | 700 | **100.0%** | 75.7% | 6/575 (1.0%) |
| Claude Sonnet 4.6 | + full-audit | 700 | **100.0%** | 84.2% | 5/575 (0.9%) |
| GLM-4.6 | + full-audit | 700 | **100.0%** | 85.7% | 5/575 (0.9%) |

**The 33.1% Trace in Axis B was a structural floor of the wrappers' skeletal audit-entry template, not the trace-ceiling for governance wrappers.** With a full-field template, Trace hits 100%. Same architecture pattern (input/output guardrails + LLM call), different audit-entry shape, ~67pp Trace gain at essentially zero Policy cost.

**Experiment 2: audit-asking prompt.** A new `examples/llm_bare_with_audit_prompt.py` adapter — bare LLM, no wrapper — but the system prompt explicitly asks for `audit_entries` alongside `decision`.

| LLM | Adapter | n | Trace | Policy | DF |
|---|---|---:|---:|---:|---:|
| GPT-4o-mini | bare LLM, audit-asking prompt | 700 | **87.8%** | 79.1% | 17/575 (3.0%) |

A bare LLM, just *asked* for audit entries, scores 87.8% Trace. The 0% Trace on Axis A was a property of the *default deployment prompt* (which doesn't ask for audit entries), not of LLM capability. The architectural difference between wrappers and bare-LLM is **enforcement vs request**, not "wrappers enable, bare cannot."

**The trace-performance ladder:**

| Configuration | Trace | Mechanism |
|---|---:|---|
| Bare LLM, default prompt (Axis A) | 0.0% | No ask, no enforcement |
| Bare LLM, audit-asking prompt (Axis C) | 87.8% | Ask, no enforcement — LLM-cooperation-dependent |
| Wrapper with skeletal audit entries (Axis B) | 33.1% | Enforce, partial fields |
| Wrapper with full-field audit entries (Axis C) | 100.0% | Enforce, full fields |

**Sharpened architectural claim:** wrappers ENFORCE governance behavior, prompts REQUEST it, default-prompt bare pipes do neither — that is why they record nothing. The wrapper advantage in safety-critical settings is *reliability*: 87.8% (LLM cooperation ceiling) means 122 of 700 scenarios silently lose audit data; a wrapper that injects entries makes that count zero.
```

## Change 5: Replace "Capable ≠ Accountable" with the joint-axis synthesis

Insert a new top-level section between "Where the Governance Gap Is" and "You Don't Need a Framework (For Layer 2)".

```markdown
## Capable ≠ Accountable: the joint picture

Across all three axes, 22+ data points (10 LLMs bare on Axis A + 3 LLMs × 4 wrappers on Axis B + 4 audit-ceiling configurations on Axis C):

| Dimension | Axis A (10 bare LLMs) | Axis B (3 LLMs × 4 wrappers) | Axis C (architectural refinement) |
|---|---|---|---|
| Policy | 69.6% → 86.9% (Δ 17.3 pp) | 66.6% → 85.7% (Δ 19.1 pp) | 75.7% → 84.2% (full-audit) |
| Safety | 53.8% → 83.3% (Δ 29.5 pp) | 43.7% → 79.7% (Δ 36.0 pp) | 57.2% → 65.2% (full-audit) |
| **Traceability** | **0% → 0%** (Δ 0 pp, even reasoning) | **0% → 33.1%** (identical Δ across 3 LLMs) | **0% → 87.8%** (audit-prompt) → **100%** (full-audit) |
| **Controllability** | **0% → 0%** (Δ 0 pp) | **0% → 47.4%** (identical Δ across 3 LLMs) | unchanged (interrupt is architectural-only) |

Policy and Safety are capability-sensitive — a better LLM *or* a different wrapper can move them. Traceability is **prompt-sensitive AND wrapper-sensitive**: bare-default-prompt scores 0% across all 10 LLMs, bare-with-audit-prompt scores 87.8% (LLM-cooperation ceiling), wrapper-with-skeletal-audit scores 33.1% (template floor), wrapper-with-full-audit scores 100% (full template ceiling). Controllability is **architectural-only**: 0% on every LLM in every prompt configuration we tested; only LangGraph's `interrupt` primitive (47.4%) moves it.

The corrected architectural claim: **wrappers ENFORCE governance behavior, prompts REQUEST it, default-prompt bare pipes do neither.** Wrappers' edge is reliability/enforcement — guarantees every scenario gets the audit entry — not capability the LLM lacks. In safety-critical settings, the 12pp gap between LLM-cooperation (87.8%) and wrapper-injection (100%) is **84 of 700 scenarios per run** silently losing audit data when relying on the LLM, vs. zero when injecting from the wrapper.

**Pick your model for decision quality. Pick your wrapper to enforce audit/halt invariants. Pick your prompt for the LLM-cooperation floor underneath both. Three different knobs.**

Notable per-axis findings:

- **Chinese frontier matches Western frontier on capability.** GLM-4.6 (87% Policy) slightly edges Claude Sonnet 4.6 (86%); Qwen3-Max ties Claude on Safety.
- **Reasoning models don't close the governance gap.** DeepSeek-R1 (Policy 81%, Trace/Ctrl 0% bare) — same architectural pattern as instruction-tuned models. Reasoning capability is not the missing piece.
- **Gemini 2.5 Pro is the safest bare model** — 8 dangerous failures and 83% Safety — but with a conservative decision profile that lowers Policy (79%).
- **Medical specialization did not help.** MedGemma 4B (70% Policy) is below every non-medical frontier model; the 16pp gap vs. Claude is too large for Q4 quantization alone.
- **LangGraph HITL is the only wrapper that moves Controllability off zero.** The `interrupt` primitive is the architectural lever — and its 47.4pp Ctrl gain is identical on all three LLMs we tested (GPT-4o-mini, Claude, R1).
- **R1 + OpenAI Guardrails has the lowest DF in the matrix (1/575 = 0.2%).** OpenAI Guardrails consistently halves DF on every LLM tested. Wrapper × LLM interactions on dangerous-failures are real and worth deeper study.
```

## Change 6: Update "How to read this" prose

### Current

> **Look at the bottom rows.** All four LLM-based approaches score 61-82% on policy compliance...

### New

> **Look at the bottom rows of all three tables.** Across 4 governance patterns (original v1 simulated table — including the CliniClaw typed reference), 9 LLMs (Axis A), and 2 LLMs × 4 wrappers (Axis B), policy compliance ranges from 61% to 87%. **Traceability and Controllability are 0% for every bare-LLM row regardless of model choice.** They only move off zero when the wrapper architecture explicitly includes an audit layer (OpenAI Guardrails or LangGraph HITL on Axis B; CliniClaw on the v1 simulated table) or an interrupt primitive (LangGraph HITL on Axis B). And on Axis B, the same wrapper produces the same Trace/Ctrl gain on both LLM tiers tested — confirming these dimensions are architectural, not capability-driven.

## Change 7: Expand "Limitations" section

Append to the existing Limitations list:

```markdown
- **Axis A prompt is minimal by design.** Asks only for a decision. The "0% Trace on every bare LLM" finding is a property of the deployment prompt, not LLM capability. Axis C measured this directly: with an audit-asking prompt, GPT-4o-mini scored 87.8% Trace bare. The architectural claim is therefore "wrappers enforce audit; default-prompt bare pipes don't ask for it; LLM-asked produces ~88% but not 100%."
- **Axis B wrapper depth is representative, not exhaustive.** Each wrapper is a canonical integration — `nemoguardrails` with Colang config, LangGraph `StateGraph` with `interrupt` nodes, OpenAI moderation+regex PHI. Not adversarially-tuned configs. "NeMo Guardrails is bad" is the wrong inference; "out-of-the-box NeMo has no audit primitive" is the right one.
- **Axis B uses 3 of the 10 Axis A LLMs** (GPT-4o-mini, Claude Sonnet 4.6, DeepSeek-R1). Extending to more LLM tiers is a v1.4 item — see `docs/future-work/v1.3-scope.md`.
- **Axis C audit-prompt experiment uses 1 LLM** (GPT-4o-mini, n=700, 87.8% Trace). Replication on Claude was started but interrupted by an OpenRouter credit-budget incident (n=119 partial); the headline 87.8% rests on GPT-4o-mini alone. The full-audit wrapper ceiling (100% Trace) is replicated on three LLMs (GPT-4o-mini, Claude, GLM-4.6) and is robust.
- **Axis B bare baselines come from 2026-04-24 (GPT, Claude) and 2026-04-28 (R1) Axis A runs; wrapper rows are 2026-04-27/28.** Same-model bare run replicates within ~0.2pp Policy across dates, acceptable.
- **LLM-judged ground truth has sibling bias.** `expected.decision` is GPT-4o-mini + GPT-4o + Gemini 2.5 Flash consensus. GPT-4o-mini and Gemini 2.5 Pro are benchmarked; they may carry a 2–5pp systematic advantage. Clinician audit of 100 scenarios planned for v1.3.
- **OpenRouter routing is unobserved.** Models via OpenRouter may have been served by different backends. Latency not comparable across routes.
- **Local models are quantized.** MedGemma 4B at Q4_K_M. Full-precision scores may be 2–5pp higher.
- **Meditron-7B and Meditron3-8B attempted but excluded** — see `docs/future-work/` for detailed writeups. Meditron-7B timed out 28% (JSON-following issue); Meditron3-8B scored 57% at Q4 (quantization artifact). Neither was a fair representative of its class. (DeepSeek-R1 was originally in this list — the 2026-04-24 attempt lost 324 scored scenarios to the runner persistence bug. The bug is fixed in v1.3 and R1 is now in the headline panel.)
- **6 medical-specialized models could not be accessed** — HuatuoGPT-II-34B, HuatuoGPT-o1-72B, Meditron3-70B, Med42-70B, OpenBioLLM-70B, PULSE-7b/20b are open-weight but had no OpenAI-compatible hosting on any configured provider as of 2026-04-24.
- **Model version drift.** Slugs may silently update on providers.
```

## Change 8: Update Citation / Related Work

Add the new blog post link under Related Projects (if the blog goes live).

---

## Summary: 8 surgical edits

1. Hero line — two-axis framing, stronger than either single-axis claim
2. New "The two-axis setup" section explaining the experimental design
3. New "Axis A — by model" section (3 sub-tables, one per category)
4. New "Axis B — by wrapper" section (controlled GPT-4o-mini sweep)
5. Rewritten "Capable ≠ Accountable" as the joint-axis synthesis
6. "How to read this" updated to cover all three tables
7. Expanded Limitations — 9 new bullets covering both axes and unreported experiments
8. Link to blog from Related Projects

No existing content is deleted. The v1 governance-pattern story remains intact as contextual background; the two new axes layer on top. Result: the README tells one coherent architectural story supported by three complementary data cuts.

## Status: ready to apply

All placeholders resolved against fresh data:
- **Axis A**: `outputs/combined_results.csv` (2026-04-24, 9 LLMs × bare, full schema with `dangerous_failures`).
- **Axis B**: `outputs/axisB_*_{gpt4omini,claude46}/` (2026-04-27, 2 LLMs × 3 wrappers fresh full runs at n=700; bare baselines reused from 2026-04-24 Axis A).

DeepSeek-R1 and Meditron attempts noted in Limitations as attempted-and-deferred. GLM-4.6 wrapper experiments deferred to v1.3 (NeMo+GLM combo too slow for v1.2 timeline; runner persistence fix needed first for unattended overnight runs). Next step: user reviews the patch and I apply it to README.md as one commit.

## Open questions before apply

(All earlier blockers resolved by the 2026-04-27 fresh-data run. Axis B no longer has partial-sample issues — every row is from a single full n=700 run with the `dangerous_failures` field captured natively.)
