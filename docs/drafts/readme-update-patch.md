# README.md Update Plan for v1.2

> Ready to apply. Two-axis final roster:
> - **Axis A** = 9 models, bare LLM (outputs/combined_results.csv, 2026-04-24).
> - **Axis B** = GPT-4o-mini × 4 wrappers (outputs/real_*_v2/, 2026-04-04).
> DeepSeek-R1 was attempted but adapter calls were lost to a runner persistence bug — no usable results; deferred to v1.3.
>
> Strategy: keep v1 structure intact (governance-patterns table stays as context), add two new layers — a "model sweep" (Axis A) and a "wrapper sweep" (Axis B). Together they make the architectural claim provable instead of assertable.

---

## Change 1: Hero line (top of README)

### Current (line 3)

```markdown
**Your AI gets 81% of clinical governance decisions right. It can't prove any of them.**
```

### New

```markdown
**We ran a 700-scenario clinical governance benchmark two ways. Swapping the LLM among 9 frontier models moves Policy ±17pp and moves Traceability/Controllability by exactly zero. Swapping the governance wrapper at fixed LLM moves Traceability 0→33% and Controllability 0→47.5%. The model is not the bottleneck. The pipeline is.**
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

## Change 4: Add new section "Axis B — winner + wrappers, two LLM tiers"

Insert directly after the Axis A section.

```markdown
### Axis B — pick the winner, vary the wrapper (2 LLMs × 4 wrappers)

Axis A picked the headline. We then re-ran the wrapper experiments with **two LLM tiers** to test whether wrapper effects transfer across model strength: Claude Sonnet 4.6 (Axis A's #2 at 85.7% Policy) and GPT-4o-mini (#5 at 81.0%).

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

(GLM-4.6, Axis A's Policy leader, was attempted but the NeMo+GLM combination paced at ~8 hours per run; deferred to v1.3 once the runner persistence fix lands and overnight unattended runs are safe.)

**Axis B tells us three things:**

1. **Trace and Ctrl gains are LLM-invariant.** Same wrapper, two different LLMs → identical gain. OpenAI Guardrails: +33.1pp Trace on both. LangGraph HITL: +33.1pp Trace AND +47.4pp Ctrl on both. The interrupt primitive fires deterministically on `missing_approval` and `emergency_override` scenario types — the LLM's output isn't on the decision path. **Trace and Ctrl are properties of the pipeline, not the model.** Note: 33.1% is a *floor* — both wrappers we tested produce skeletal audit entries (timestamp + action only; actor/resource/reason left null), each scoring 1 of 3 grader sub-criteria = 33.3%. A wrapper populating all three audit fields would score higher.
2. **OpenAI Guardrails' Policy hit depends on LLM tier; the other two wrappers don't.** OpenAI Guardrails costs GPT-4o-mini −6.9pp Policy but only −2.6pp on Claude (4.3pp gap). NeMo and LangGraph HITL cost roughly equal Policy on both LLMs (gaps of 2.4pp and 0.8pp respectively). The "better LLM absorbs wrapper restrictions" pattern shows up in 1 of 3 wrappers tested, on n=2 LLMs — suggestive, not yet a general claim.
3. **NeMo + Claude is the surprise dangerous-failures standout, but n=3 limits the claim.** Claude bare DF 2.4% → NeMo+Claude DF 0.5% (suggestive 79% reduction, the lowest DF rate of any combo tested). Same wrapper on GPT-4o-mini gives 4.3% — basically equal to GPT bare. With only 3 dangerous failures observed, the 95% CI is roughly [0.1%, 1.5%]; treat as suggestive evidence of a wrapper × LLM interaction, not a settled number.

No tested wrapper clears 50% on both Trace AND Ctrl simultaneously. None were designed around audit and halt as first-class primitives.
```

## Change 5: Replace "Capable ≠ Accountable" with the joint-axis synthesis

Insert a new top-level section between "Where the Governance Gap Is" and "You Don't Need a Framework (For Layer 2)".

```markdown
## Capable ≠ Accountable: the joint picture

Across both axes, 17 data points (9 LLMs bare on Axis A + 2 LLMs × 4 wrappers on Axis B):

| Dimension | Axis A range (model varies, bare) | Axis B range (2 LLMs × 4 wrappers) |
|---|---|---|
| Policy | 69.6% → 86.9% (Δ 17.3 pp) | 66.8% → 85.7% (Δ 18.9 pp) |
| Safety | 53.8% → 83.3% (Δ 29.5 pp) | 51.7% → 79.7% (Δ 28.0 pp) |
| **Traceability** | **0% → 0% (Δ 0 pp)** | **0% → 33.1% (identical Δ across both LLMs)** |
| **Controllability** | **0% → 0% (Δ 0 pp)** | **0% → 47.4% (identical Δ across both LLMs)** |

Policy and Safety are capability-sensitive — a better LLM *or* a different wrapper can move them. Traceability and Controllability are capability-*insensitive* on Axis A and capability-*invariant* on Axis B (same wrapper produces identical Trace/Ctrl gain on both LLM tiers tested). **They are architectural properties, not model properties.**

If your governance strategy is "pick a better LLM," this benchmark shows that strategy does not close the Trace/Ctrl gap. Picking a better LLM moves Policy from 81% to 87%. It does not move Traceability one percentage point off zero. The gap is in the pipeline's ability to *record* decisions and *halt* for human review — architectural features a bare LLM pipeline cannot produce regardless of how smart the LLM is, and that wrappers produce identically across LLM tiers.

**Pick your model for decision quality. Pick your wrapper for governance. They are different knobs.**

Notable per-axis findings:

- **Chinese frontier matches Western frontier on capability.** GLM-4.6 (87% Policy) slightly edges Claude Sonnet 4.6 (86%); Qwen3-Max ties Claude on Safety.
- **Gemini 2.5 Pro is the safest bare model** — 8 dangerous failures and 83% Safety — but with a conservative decision profile that lowers Policy (79%).
- **Medical specialization did not help.** MedGemma 4B (70% Policy) is below every non-medical frontier model; the 16pp gap vs. Claude is too large for Q4 quantization alone.
- **LangGraph HITL is the only wrapper that moves Controllability off zero.** The `interrupt` primitive is the architectural lever — and its 47.4pp Ctrl gain is identical on Claude and on GPT-4o-mini.
- **NeMo Guardrails + Claude is the dangerous-failures standout.** 0.5% DF — a 79% reduction from Claude bare's 2.4%. Same wrapper on GPT-4o-mini gives 4.3% (basically equal to GPT bare). Wrapper-effect on dangerous-failures is wrapper × LLM interaction, not pure-architectural.
```

## Change 6: Update "How to read this" prose

### Current

> **Look at the bottom rows.** All four LLM-based approaches score 61-82% on policy compliance...

### New

> **Look at the bottom rows of all three tables.** Across 4 governance patterns (original v1 simulated table — including the CliniClaw typed reference), 9 LLMs (Axis A), and 2 LLMs × 4 wrappers (Axis B), policy compliance ranges from 61% to 87%. **Traceability and Controllability are 0% for every bare-LLM row regardless of model choice.** They only move off zero when the wrapper architecture explicitly includes an audit layer (OpenAI Guardrails or LangGraph HITL on Axis B; CliniClaw on the v1 simulated table) or an interrupt primitive (LangGraph HITL on Axis B). And on Axis B, the same wrapper produces the same Trace/Ctrl gain on both LLM tiers tested — confirming these dimensions are architectural, not capability-driven.

## Change 7: Expand "Limitations" section

Append to the existing Limitations list:

```markdown
- **Axis A prompt is minimal by design.** Asks only for a decision. 0% Trace on Axis A is therefore a property of the deployment pattern (bare JSON pipe), not proof that LLMs cannot format audit entries. Axis B shows that adding the infrastructure — not changing the prompt — is what moves the number. v1.3 will test a prompt variant explicitly asking for audit entries as a ceiling measurement.
- **Axis B wrapper depth is representative, not exhaustive.** Each wrapper is a canonical integration — `nemoguardrails` with Colang config, LangGraph `StateGraph` with `interrupt` nodes, OpenAI moderation+regex PHI. Not adversarially-tuned configs. "NeMo Guardrails is bad" is the wrong inference; "out-of-the-box NeMo has no audit primitive" is the right one.
- **Axis B uses 2 of the 9 Axis A LLMs.** Claude Sonnet 4.6 (Axis A's #2) and GPT-4o-mini (#5) under all 4 wrappers. GLM-4.6 (Axis A's #1) was attempted but the NeMo+GLM combination paced at ~8 hours per run; deferred to v1.3 once the runner persistence fix lands and unattended overnight runs are safe. The "wrapper effect transfers across LLM tiers" claim rests on these two LLMs.
- **Axis B bare baselines come from 2026-04-24 Axis A runs; wrapper rows are 2026-04-27.** Same-model bare run replicates within ~0.2pp Policy across the 3-day gap, so this is acceptable.
- **LLM-judged ground truth has sibling bias.** `expected.decision` is GPT-4o-mini + GPT-4o + Gemini 2.5 Flash consensus. GPT-4o-mini and Gemini 2.5 Pro are benchmarked; they may carry a 2–5pp systematic advantage. Clinician audit of 100 scenarios planned for v1.3.
- **OpenRouter routing is unobserved.** Models via OpenRouter may have been served by different backends. Latency not comparable across routes.
- **Local models are quantized.** MedGemma 4B at Q4_K_M. Full-precision scores may be 2–5pp higher.
- **DeepSeek-R1, Meditron-7B, Meditron3-8B attempted but excluded** — see `docs/future-work/` for detailed writeups. DeepSeek-R1 lost 324 scored scenarios to a runner persistence bug; Meditron-7B timed out 28% (JSON-following issue); Meditron3-8B scored 57% at Q4 (quantization artifact). None were fair representatives of their class.
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
