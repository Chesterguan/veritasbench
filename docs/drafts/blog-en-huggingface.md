# We Tested 10 LLMs and 5 Wrappers on Clinical Governance. Architecture *Enforces*, Prompts *Request*, Bare Pipes Don't Record.

> Companion blog post for VeritasBench v1.3. Target: HuggingFace Blog / Medium / personal Substack.
> Words: ~2400. Charts: `![models](./benchmark-chart-models.png)`, `![wrappers](./benchmark-chart-wrappers.png)`, `![trace-ladder](./benchmark-chart-trace-ladder.png)` — generated from `outputs/combined_results.csv`, `outputs/wrapper_comparison.csv`, and `scripts/aggregate_axis_b.py` output.

---

## TL;DR

We ran a 700-scenario clinical governance benchmark across three layers of inquiry.

**Axis A — vary the LLM, keep the wrapper.** 10 frontier LLMs, identical bare-LLM prompt (Claude Sonnet 4.6, GPT-4o-mini, Gemini 2.5 Pro, DeepSeek-V3.2, Qwen3-Max, GLM-4.6, Kimi K2, Hunyuan A13B, MedGemma 4B, **DeepSeek-R1 reasoning**). Policy compliance ranged **69.6% → 86.9%**. **Traceability = 0.0% on all 10. Controllability = 0.0% on all 10.** Reasoning mode does not change this — bare DeepSeek-R1 is 0%/0% just like every other bare LLM.

**Axis B — pick the winner, vary the wrapper.** Three LLM tiers (Claude Sonnet 4.6, GPT-4o-mini, DeepSeek-R1) under four governance patterns each (bare, NeMo Guardrails, OpenAI Guardrails, LangGraph HITL). Same 700 scenarios. Traceability moved **0% → 33.1%** *identically across all three LLMs*. Controllability moved **0% → 47.4%** *identically across all three LLMs*.

**Axis C — refine the architectural claim.** Two follow-ups that sharpen the v1.2 finding:
- A full-audit wrapper variant (populates actor/resource/decision/reason fields, not just timestamp+action) lifts Trace to **100%** on every LLM tested. The 33.1% in Axis B was a *structural floor* of the v1.2 wrappers' skeletal audit-entry template — not the trace-ceiling for governance wrappers.
- A bare LLM with an *audit-asking prompt* (no wrapper, just ask for `audit_entries` alongside `decision`) scores **87.8% Trace** on GPT-4o-mini. Asking unlocks most of the rubric. The architectural difference is not "wrappers enable, bare cannot" — it is **"wrappers enforce, prompts request, bare with default prompt records nothing."**

The architectural claim survives but gets sharper. **Models choose your decision quality. Wrappers enforce your audit/halt invariants. Default-prompt bare pipes record nothing — that is a deployment choice, not a capability limit.**

Below: the data, the methodology, the caveats, and the ask.

---

## What the benchmark measures

VeritasBench ([github.com/Chesterguan/veritasbench](https://github.com/Chesterguan/veritasbench)) sends 700 clinical governance scenarios to an adapter and evaluates what comes back on four dimensions:

| Dimension | What it asks | How it's scored |
|---|---|---|
| **Policy Compliance** | Did the agent make the correct allow/deny/block decision? | 0 or 1 per scenario — binary |
| **Safety** | Did it avoid dangerous actions and protect sensitive data? | Includes PHI leakage check |
| **Traceability** | Did it produce a complete, meaningful audit trail? | 3 points: entry + fields + semantic reason |
| **Controllability** | Did it halt and notify a human when required? | 2 points: halted + notified |

Plus a Dangerous Failures counter: cases where the adapter allowed an action that governance required denying or blocking — the failure mode that causes patient harm.

The 700 scenarios cover 11 governance types including unauthorized access, missing approval, PHI leakage, unsafe drug interactions, and four system-level types (conflicting authority, incomplete information, system-initiated actions, accountability gaps) that break naive rule engines.

## The two-axis setup

A single benchmark number is unfalsifiable. "LLM X scored 82%" tells you nothing about whether the limiting factor is the model, the prompt, the pipeline, or the grader. To test where the bottleneck actually lives, we held one axis fixed and moved the other.

- **Axis A** pins the *pipeline* (bare LLM + identical prompt + JSON output) and sweeps the *model* across 9 frontier LLMs from four labs and two geographies.
- **Axis B** pins the *model* (GPT-4o-mini) and sweeps the *wrapper* across 4 representative governance patterns: bare, NeMo Guardrails, OpenAI Guardrails, LangGraph HITL.

If governance scales with model quality, Axis A should move. If it scales with architecture, Axis B should move. The answer is unambiguous.

---

## Axis A: model varies, wrapper fixed (bare LLM)

Every model is invoked with the same prompt: scenario JSON in, `{"decision": "allow" | "deny" | "blocked_pending_approval"}` out. No governance infrastructure — just the LLM, a system prompt, and temperature 0. This is the naive deployment pattern most production LLM integrations look like before adding a wrapper.

| Category | Models |
|---|---|
| **Western general (frontier)** | Claude Sonnet 4.6, GPT-4o-mini, Gemini 2.5 Pro |
| **Chinese general (frontier)** | DeepSeek-V3.2, Qwen3-Max, GLM-4.6, Kimi K2, Hunyuan A13B |
| **Reasoning** | DeepSeek-R1 (DeepSeek-R1-0528 via OpenRouter) |
| **Western medical (specialized)** | MedGemma 4B (Google, Gemma 2 base) |

Design choices:
- **Routing**: frontier Chinese and Western models via OpenRouter (one aggregator). Gemini via the native Google GenAI SDK. Claude Sonnet 4.6 runs on the native Anthropic SDK with prompt caching. MedGemma via local Ollama (Q4_K_M quantization).
- **Prompt**: identical across all models. Asks only for a decision, not audit entries or halt signals.
- **Temperature**: 0. **Retries**: 2 at runner level, plus per-adapter 429 exponential backoff.

### Results

```
### Western — general

| Model              | Policy          | Safety          | Traceability | Controllability | Dangerous  | p50      |
|--------------------|-----------------|-----------------|--------------|-----------------|------------|----------|
| Claude Sonnet 4.6  | 493/575 (85.7%) | 259/325 (79.7%) | 0/2100 (0%)  | 0/570 (0%)      | 14/575     | 1909 ms  |
| Gemini 2.5 Pro     | 454/572 (79.4%) | 270/324 (83.3%) | 0/2091 (0%)  | 0/568 (0%)      |  8/572     | 8130 ms  |
| GPT-4o-mini        | 466/575 (81.0%) | 234/325 (72.0%) | 0/2100 (0%)  | 0/570 (0%)      | 26/575     | 1117 ms  |
```

```
### Chinese — general

| Model              | Policy          | Safety          | Traceability | Controllability | Dangerous  | p50      |
|--------------------|-----------------|-----------------|--------------|-----------------|------------|----------|
| GLM-4.6            | 496/571 (86.9%) | 258/322 (80.1%) | 0/2088 (0%)  | 0/570 (0%)      | 23/571     | 2493 ms  |
| Qwen3-Max          | 479/575 (83.3%) | 261/325 (80.3%) | 0/2100 (0%)  | 0/570 (0%)      | 15/575     | 1908 ms  |
| DeepSeek-V3.2      | 477/575 (83.0%) | 226/325 (69.5%) | 0/2100 (0%)  | 0/570 (0%)      | 29/575     | 3099 ms  |
| Kimi K2            | 450/572 (78.7%) | 203/323 (62.8%) | 0/2091 (0%)  | 0/566 (0%)      | 25/572     | 2000 ms  |
| Hunyuan A13B       | 403/575 (70.1%) | 175/325 (53.8%) | 0/2100 (0%)  | 0/570 (0%)      | 154/575    | 1490 ms  |
```

```
### Western — medical-specialized

| Model                | Policy          | Safety          | Traceability | Controllability | Dangerous  | p50      |
|----------------------|-----------------|-----------------|--------------|-----------------|------------|----------|
| MedGemma 4B (Google) | 400/575 (69.6%) | 221/325 (68.0%) | 0/2100 (0%)  | 0/570 (0%)      | 135/575    | 2136 ms  |
```

```
### Reasoning

| Model              | Policy          | Safety          | Traceability | Controllability | Dangerous  |
|--------------------|-----------------|-----------------|--------------|-----------------|------------|
| DeepSeek-R1-0528   | 465/575 (80.9%) | 211/325 (64.9%) | 0/2100 (0%)  | 0/570 (0%)      | 18/575     |
```

(Full reproducible numbers at [outputs/combined_results.csv](https://github.com/Chesterguan/veritasbench/blob/main/outputs/combined_results.csv).)

### What Axis A tells us

**Policy compliance spans a 17.3 pp band.** GLM-4.6 leads (86.9%) by a hair over Claude Sonnet 4.6 (85.7%). The bottom is held by small or quantized models: Hunyuan A13B at 70.1%, MedGemma 4B at 69.6%. Scale and general capability matter a lot for decision quality.

**Chinese frontier matches Western frontier.** GLM-4.6, Qwen3-Max, and DeepSeek-V3.2 are all within 4 pp of Claude Sonnet 4.6 on policy, and Qwen3-Max ties Claude on safety (80.3% vs 79.7%) with fewer dangerous failures (15 vs 14 — noise). Lab of origin stopped being a capability signal once you're above the frontier.

**Dangerous failures cluster into three tiers.** Frontier (<30): Claude 14, Qwen 15, GLM 23, Kimi 25, GPT 26, DeepSeek 29. Gemini is an outlier with only 8. Failing tier: Hunyuan 154, MedGemma 135 — both 20%+ dangerous-failure rates.

**Medical specialization didn't help.** MedGemma 4B — Google's medical-fine-tuned Gemma 2 — scored below every non-medical model tested. Part of this is quantization (Q4_K_M Ollama), but the 16 pp gap against Claude is too large to explain with quantization alone. Domain fine-tuning at 4B can't compensate for scale on clinical governance reasoning.

**Reasoning mode does not close the gap.** DeepSeek-R1-0528 — the only explicit chain-of-thought reasoning model in the panel — scores 80.9% Policy (mid-tier) with **0% Trace and 0% Ctrl** like every other bare LLM. Reasoning capacity does not manifest as audit-trail or halt-for-review behavior. This was a load-bearing question from v1.2 ("does reasoning fix governance?") and the answer is unambiguous: no.

**Traceability and Controllability are 0% on every single model.** Not one model — not Claude Sonnet, not Gemini, not GLM, not the reasoning model, not the dedicated medical one — produced a single audit entry or a single halt-for-approval signal. The Y axis of the "capability vs. governance" plot is flat:

```
Policy %   Traceability %
87         0
86         0
83         0
83         0
81         0  ← DeepSeek-R1 reasoning sits here
81         0
79         0
79         0
70         0
70         0
```

Axis A is the null result. **Swapping the LLM moves Policy by ±17pp and moves Trace/Ctrl by exactly zero.** Adding reasoning mode to the panel didn't change the Y-axis story.

---

## Axis B: pick the winner, vary the wrapper

Axis A picked the headline. Top-3 by Policy are GLM-4.6 (86.9%), Claude Sonnet 4.6 (85.7%), and Qwen3-Max (83.3%); the reasoning model DeepSeek-R1 sits mid-tier at 80.9% Policy. But all 10 score 0% on Traceability and Controllability. So the next question: pick representative LLMs from across the capability spectrum, add a governance wrapper, see what moves.

We re-ran the wrapper experiments with **three LLM tiers** to test whether the wrapper effect transfers across model strength and reasoning capability:

- **Claude Sonnet 4.6** — Axis A's #2 (Policy 85.7%), strong frontier instruction-tuned
- **GPT-4o-mini** — Axis A's #5 (Policy 81.0%), mid-tier controlled comparison
- **DeepSeek-R1** — Axis A's reasoning entry (Policy 80.9%), tests whether chain-of-thought changes wrapper-effect

Each LLM ran the same 700 scenarios under each of four pipelines:

- **Bare LLM** — no wrapper, direct API call
- **NeMo Guardrails** — NVIDIA's [`nemoguardrails`](https://github.com/NVIDIA/NeMo-Guardrails) library with Colang topic/content rails (no audit primitive, no halt primitive)
- **OpenAI Guardrails** — moderation API + regex PHI scrubbing as input/output guardrails (audit entries from guardrail evaluations, no halt primitive)
- **LangGraph HITL** — LangGraph `StateGraph` with real `interrupt` nodes that halt execution on `missing_approval` and `emergency_override` scenario types

### Results — full 3 × 4 matrix

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

Bare baselines come from the 2026-04-24 (GPT, Claude) and 2026-04-28 (R1) Axis A runs, n=700 each, full schema with `dangerous_failures`. The 12 wrapper rows are fresh full runs on 2026-04-27 / 2026-04-28, identical 700 scenarios, single-source per row — no cross-run blending.

### What the matrix tells us

**1. Traceability and Controllability are LLM-invariant across all 3 LLMs tested.** Same wrapper, three different LLMs (instruction-tuned frontier, mid-tier, reasoning) → identical gains:

| | Trace gain (GPT / Claude / R1) | Ctrl gain (GPT / Claude / R1) |
|---|---|---|
| + NeMo Guardrails | 0pp / 0pp / 0pp | 0pp / 0pp / 0pp |
| + OpenAI Guardrails | **+33.1pp / +33.1pp / +33.1pp** | 0pp / 0pp / 0pp |
| + LangGraph HITL | **+33.1pp / +33.1pp / +33.1pp** | **+47.4pp / +47.4pp / +47.4pp** |

Adding a reasoning model (DeepSeek-R1) didn't shift the pattern. The LangGraph `interrupt` primitive fires deterministically on `missing_approval` and `emergency_override` scenarios — the LLM's output isn't on that decision path. Same logic for guardrail-derived audit entries: they come from the wrapper's evaluation events, not from the LLM's response content. **Trace and Ctrl are properties of the pipeline, not of the model.** No LLM produces them without a wrapper; any LLM produces them with one — and the *level* of the gain is wrapper-determined, not model-determined.

**What 33.1% Trace actually means.** This is a *floor*, not a ceiling. The grader scores Traceability out of 3 sub-criteria per scenario (entry exists + required fields populated + semantic reason). Both wrappers we tested in this matrix use the same skeletal `_trace_entry` template — `{timestamp, action}` filled, `{actor, resource, reason}` left null — so each scenario with any entry earns 1 of 3 = 33.3%. The fact that two different wrappers land on identical Trace scores is mostly because they share the same minimal-audit-entry shape, not because 33% is the natural ceiling for governance wrappers. (We tested this directly in the Axis C follow-up — see below — where a wrapper populating all three audit fields scores 100%.)

**2. OpenAI Guardrails Policy hit varies with LLM tier; the other wrappers don't.** Comparing ΔPolicy across all 3 LLMs:

| Wrapper | GPT-4o-mini Δ | Claude Δ | DeepSeek-R1 Δ | Range |
|---|---:|---:|---:|---:|
| + NeMo Guardrails | +0.2pp | −2.2pp | +2.6pp | 4.8pp |
| + LangGraph HITL | −14.2pp | −13.4pp | −14.3pp | 0.9pp |
| + **OpenAI Guardrails** | **−6.9pp** | **−2.6pp** | **−2.1pp** | **4.8pp** |

LangGraph's interrupt fires on the same scenario types regardless of LLM, costing ~13–14pp Policy on all three — that gap is structural, LLM-invariant. OpenAI Guardrails' moderation+regex pipeline asks the LLM to be more conservative; Claude and R1 are calibrated enough to remain mostly correct (−2.6pp, −2.1pp) while GPT-4o-mini over-corrects to defensive denies (−6.9pp). NeMo also varies (R1 actually gains +2.6pp Policy under NeMo, GPT is neutral, Claude loses −2.2pp), suggesting NeMo's topic rails interact with each model's response style differently.

**3. R1 + OpenAI Guardrails is the lowest-DF combination observed.** The DF column reveals a striking interaction:

- **DeepSeek-R1 + OpenAI Guardrails: 1/575 (0.2%)** — the lowest DF rate of any (LLM, wrapper) combination tested
- **NeMo Guardrails + Claude Sonnet 4.6: 3/575 (0.5%)** — second-lowest, suggestive 79% reduction from Claude bare
- **OpenAI Guardrails on every LLM tested**: 4.5%→1.2% (GPT), 2.4%→1.0% (Claude), 3.1%→0.2% (R1) — all 70-95% DF reductions

The wrapper-effect on Dangerous-failures **looks like a wrapper × LLM interaction**, not a pure-architectural property. The R1 + OpenAI Guardrails 0.2% headline is one observed dangerous failure out of 575 — n=1 events — so the confidence interval is wide [<0.1%, ~1.0%]. Treat as suggestive evidence of a strong interaction worth replicating in v1.4.

LangGraph HITL has mixed DF effects across LLMs: interrupts catch some dangerous decisions in the routed scenario types (`missing_approval`, `emergency_override`), but the LangGraph `decide` node handling non-HITL types doesn't apply extra conservatism — so DF on the non-interrupt scenarios stays close to bare. A per-governance-type breakdown using `scripts/breakdown_by_type.py` shows dangerous failures actually concentrate on **different** scenario types per LLM (Claude on Missing Justification, GPT-4o-mini on System-Initiated, R1 on a similar but not identical pattern), which suggests the LangGraph `HITL_TYPES` set should be tuned per LLM or replaced with a data-driven approach in v1.4.

**4. No wrapper clears 50% on both Trace AND Ctrl simultaneously.** Each one moves only a subset of dimensions:
- NeMo Guardrails: helps Dangerous (only on calibrated LLMs), no Trace, no Ctrl
- OpenAI Guardrails: adds Trace, halves DF, no Ctrl, costs Safety
- LangGraph HITL: adds Trace AND Ctrl, halves DF, costs Policy and Safety

None of the three was designed around audit and halt as first-class primitives.

---

## The joint picture: capable ≠ accountable

Across the first two axes, **22 data points** (10 LLMs × bare on Axis A; 3 LLMs × 4 wrappers on Axis B):

| Dimension | Axis A range (model varies, bare) | Axis B range (3 LLMs × 4 wrappers) |
|---|---|---|
| Policy | 69.6% → 86.9% (Δ 17.3 pp) | 66.6% → 85.7% (Δ 19.1 pp) |
| Safety | 53.8% → 83.3% (Δ 29.5 pp) | 43.7% → 79.7% (Δ 36.0 pp) |
| **Traceability** | **0% → 0%** (Δ 0 pp) | **0% → 33.1%** (identical Δ across all 3 LLMs) |
| **Controllability** | **0% → 0%** (Δ 0 pp) | **0% → 47.4%** (identical Δ across all 3 LLMs) |
| Dangerous (best/worst) | 8/572 (1.4%) → 154/575 (26.8%) | 1/575 (0.2%) → 26/575 (4.5%) |

Policy and Safety are capability-sensitive — a better LLM *or* a different wrapper moves them. Traceability and Controllability are capability-insensitive on Axis A and capability-*invariant* on Axis B (same wrapper → same gain on all three LLM tiers we tested, including the reasoning model). **They are architectural properties, not model properties.**

If your governance strategy is *"pick a better LLM"*, this benchmark shows that strategy does not close the Trace/Ctrl gap. Picking a better LLM moves Policy from 81% to 87%. It does not move Traceability one percentage point off zero — even with a reasoning model. The gap is not in decision quality. It is in the pipeline's ability to *record* decisions and *halt* for human review — architectural features that a bare LLM pipeline (with the typical "just give me the decision" prompt) cannot produce regardless of how smart the LLM is, and that wrappers produce even on a mid-tier LLM.

But — and this is where v1.3 sharpens the v1.2 claim — the architectural difference isn't *capability*. The next axis below shows that bare LLMs *can* produce audit entries when asked. The difference is **enforcement**: wrappers guarantee the entries get recorded; prompts depend on LLM cooperation; default-prompt bare pipes record nothing simply because nothing in the pipeline ever requested or required it.

---

## Axis C: refining the architectural claim — enforcement vs request

v1.2 stopped at Axis B and said "wrappers move Trace 0→33%, models can't." That's the assertion the v1.3 follow-up tightened with two surgical experiments — one a new wrapper variant, one a new prompt variant — that disambiguate *what specifically* about wrappers makes them work.

### The trace-performance ladder

Same 700 scenarios. Same grading rubric. Four configurations probing the architecture-vs-prompt axis:

| # | Configuration | Trace | What it measures |
|---|---|---:|---|
| 1 | Bare LLM, default prompt (Axis A) | **0.0%** | Naive deployment — no ask, no enforcement |
| 2 | Bare LLM, audit-asking prompt (P2.5) | **87.8%** (GPT-4o-mini, n=700) | The LLM-cooperation ceiling — ask, no enforcement |
| 3 | Wrapper with skeletal audit entries (Axis B) | **33.1%** | Enforce, partial fields (1 of 3 grader sub-criteria) |
| 4 | Wrapper with full-field audit entries (P2.4) | **100.0%** (GPT-4o-mini, Claude, GLM) | Enforce, full fields (3 of 3) |

(For #4, the full-audit wrapper was tested on three LLMs — GPT-4o-mini, Claude Sonnet 4.6, and GLM-4.6 — and hit 100% Trace on all three, confirming the trace ceiling is wrapper-architectural, not LLM-dependent.)

### What the ladder says

**Row 2 is the surprising one.** A bare LLM, no wrapper, no governance infrastructure — but with a system prompt that explicitly asks for `audit_entries` alongside `decision` — scores **87.8% Trace**. GPT-4o-mini, when asked nicely, produces audit entries that satisfy nearly all of the grader's rubric. Asking unlocks most of the trace gap.

This is a meaningful refinement of the v1.2 claim. The v1.2 reading "0% Trace = LLMs can't do audit" overstated what the data showed. The truer reading is: "0% Trace on Axis A = the default deployment prompt does not ask for audit entries, and bare LLMs only output what they are asked for." That is a *prompt-engineering* finding, not an LLM-capability finding.

**Row 4 vs row 3 is the architectural finding.** Two wrappers around the same LLM, identical OpenAI moderation + regex PHI logic, identical scenario coverage. The only difference: one wrapper's audit-entry template fills `actor`, `resource`, `decision`, and `reason`; the other leaves them null. **The structural difference between 33% and 100% is the audit-entry shape the wrapper enforces, not anything about the LLM.** The 33.1% in v1.2 was a wrapper template choice that happens to satisfy 1 of 3 grader sub-criteria. Pick a richer template and you hit 100%. The trace ceiling for governance wrappers is 100%, not 33%.

### The corrected architectural claim

The v1.2 architectural claim was *"wrappers can do governance, models can't."* The v1.3 architectural claim is sharper:

> **Wrappers ENFORCE governance behavior. Prompts REQUEST it. Default-prompt bare pipes do neither, which is why they record nothing.**

Three deployment patterns on Trace:
- **Bare LLM, default prompt**: 0% Trace — the LLM doesn't volunteer what isn't asked for. No audit primitive in the pipeline at all.
- **Bare LLM, audit-asking prompt**: 87.8% Trace — the LLM cooperates on ~88% of cases. The remaining 12% are scenarios where the LLM produces malformed entries, omits fields, or fails the keyword-relevance check on the reason. The LLM is **capable** but not **reliable**.
- **Wrapper that injects full audit entries**: 100% Trace — the wrapper guarantees every scenario has a complete audit entry, regardless of what the LLM does. The LLM cooperation is **bypassed** for the audit dimension; the wrapper takes over.

The architectural advantage of wrappers, then, is not "they enable governance behavior LLMs can't do" — it's "they enforce governance behavior every time, instead of relying on the LLM to do it consistently." That is a much stronger property in safety-critical settings, where 87.8% (the LLM-cooperation ceiling) means **122 of 700 scenarios silently lose audit data** versus 0 with a wrapper that injects entries.

For Controllability the picture is cleaner — `interrupt`-style halts cannot be requested from the LLM; the pipeline either has a halt primitive or it doesn't. LangGraph's interrupt is the only such primitive in our matrix, and it produces the only non-zero Ctrl scores. There is no audit-prompt-style equivalent for Ctrl.

**Pick your model for decision quality. Pick your wrapper to enforce audit and halt. Pick your prompt for the LLM-cooperation floor underneath both.** They are three different knobs.

---

## Models attempted but not in the headline comparison

| Model | Outcome | Reason not reported |
|---|---|---|
| ~~DeepSeek-R1~~ | **Now in the headline panel.** | The original 2026-04-24 run was lost to a mid-run EPERM (the runner did one big report write at end). v1.3 landed an NDJSON append-log persistence fix; the re-run completed cleanly on 2026-04-28 with 700 scenarios scored × 4 wrappers. |
| Meditron-7B (Ollama, Llama 2 base) | 28% of scenarios timed out | Model is trained on clinical QA text and doesn't reliably emit JSON-only responses — adapter-layer instruction-following issue, not a capability signal. |
| Meditron3-8B (Ollama, Q4_K_M GGUF) | 700/700 completed | 57% Policy / 191 dangerous failures, dominated by 4-bit quantization loss rather than medical-specialization signal. Publishing would mislead readers into "medical-specialized = weak" when the story is "Q4 quant is lossy." |
| HuatuoGPT-II-34B, HuatuoGPT-o1-72B, Meditron3-70B, Med42-70B, OpenBioLLM-70B, PULSE-7b/20b | Never ran | None available on OpenRouter / SiliconFlow / Novita / HuggingFace Inference Providers as of 2026-04-24. All are open-weight on HuggingFace — the access problem is hosting, not licensing. |

This list is load-bearing. DeepSeek-R1 and the medical-specialized models were the exact datapoints needed to test whether reasoning-mode or domain specialization might close the Traceability/Controllability gap. We haven't ruled that out — but nothing in the 9 models we could benchmark, or the 4 wrappers we ran, suggests it will.

## Caveats (must read before citing)

- **Axis A prompt is minimal by design.** Asks only for a decision, not audit entries or halt signals. The "0% Trace on every bare LLM" finding is a property of *the deployment prompt* (which doesn't ask for audit entries), not of LLM capability. Axis C (above) measured this directly: with an audit-asking prompt, GPT-4o-mini scored 87.8% Trace bare. The architectural claim is therefore "wrappers enforce audit; default-prompt bare pipes don't ask for it; LLM-asked produces ~88% but not 100%."

- **Axis B wrapper depth is representative, not exhaustive.** Each framework is a canonical integration — `nemoguardrails` with Colang config, LangGraph `StateGraph` with `interrupt` nodes, OpenAI moderation+regex PHI as guardrails. These are not adversarially-tuned configs designed to maximize scores. Readers should not infer "NeMo Guardrails is bad" from one config — they should infer "the out-of-the-box NeMo pattern has no audit primitive." Both are true.

- **Axis B uses 3 of the 10 Axis A LLMs** (GPT-4o-mini, Claude Sonnet 4.6, DeepSeek-R1) under all 4 wrappers. Adding more LLM tiers is straightforward now that the persistence fix lands — see `docs/future-work/v1.3-scope.md` for the v1.4 plan to extend to 6+ LLMs and complete a full 10×4 grid.

- **Axis C uses 1 LLM for the audit-asking prompt experiment** (GPT-4o-mini, n=700, 87.8% Trace). Replication on Claude was started but interrupted by an OpenRouter credit-budget incident and is partial (n=119); the headline 87.8% rests on GPT-4o-mini alone. The full-audit wrapper ceiling (100% Trace) is replicated on three LLMs (GPT-4o-mini, Claude, GLM-4.6) and is robust.

- **Axis B bare baselines come from 2026-04-24 (GPT, Claude) and 2026-04-28 (R1) Axis A runs.** Wrapper runs are 2026-04-27 / 2026-04-28. The same-model bare run replicates within ~0.2pp Policy across dates, so this is acceptable, but careful comparisons across the two dates carry a small slug-drift risk.

- **Skipped scenarios on Axis A.** Kimi K2 (n=697) and GLM-4.6 (n=696) had early infrastructure errors that exhausted the runner's 2 retries. Percentages on those rows are evaluated denominators; worst-case ±0.5 pp impact on those models' headline numbers.

- **MedGemma 4B is Q4-quantized.** Full-precision MedGemma 4B may score 2–5 pp higher. We flag this because it affects the medical-specialization story; the 16 pp gap against Claude is too large for quantization alone, but part of the delta could be Q4.

- **Sibling grading.** Ground-truth `expected` decisions are the multi-model consensus of GPT-4o-mini + GPT-4o + Gemini 2.5 Flash. Since GPT-4o-mini and Gemini 2.5 Pro are benchmarked, their scores may carry a 2–5 pp systematic advantage. Independent clinical-expert audit is listed as future work.

- **OpenRouter routing is unobserved.** Models routed through OpenRouter may have been served by different underlying providers with different quantizations. Latency is not comparable across routes; scores should be.

- **Wrapper × LLM dangerous-failure interactions are observed at small n.** The R1 + OpenAI Guardrails 0.2% (n=1 dangerous failure) and NeMo + Claude 0.5% (n=3) headline numbers have wide confidence intervals. Treat as suggestive of real interactions worth replicating; do not over-anchor on the exact percentages.

- **Model version drift.** Axis A runs are timestamped 2026-04-24 (GPT, Claude, others) / 2026-04-28 (R1). Axis B and C wrapper runs are 2026-04-27 to 2026-04-28. Slugs like `anthropic/claude-sonnet-4.6` or `openai/gpt-4o-mini` may silently update on providers.

See [docs/future-work/v1.3-scope.md](https://github.com/Chesterguan/veritasbench/blob/main/docs/future-work/v1.3-scope.md) and [`benchmark-realism-improvements.md`](https://github.com/Chesterguan/veritasbench/blob/main/docs/future-work/benchmark-realism-improvements.md) for the plan to close these caveats in v1.4.

## Try it

```bash
git clone https://github.com/Chesterguan/veritasbench
cd veritasbench
cargo build --release

cp .env.example .env
# add OPENROUTER_API_KEY (7 models) + OPENAI_API_KEY + ANTHROPIC_API_KEY + GEMINI_API_KEY

# Axis A — model sweep
python scripts/run_model.py gpt-4o-mini                   # reproduce the baseline
python scripts/run_model.py glm-46                        # top scorer in this run
python scripts/aggregate_models.py --input-dir outputs --markdown docs/my-results.md

# Axis B — wrapper sweep (adapters in examples/, route via env vars)
# Pin GPT-4o-mini under all three wrappers:
export OPENAI_BASE_URL=https://api.openai.com/v1 OPENAI_API_KEY=$OPENAI_API_KEY VERITASBENCH_MODEL=gpt-4o-mini
cargo run --release -- run --adapter examples/llm_with_topic_rails.py     --suite healthcare_v1 --output outputs/axisB_topic_rails_gpt4omini --timeout 120000 --retries 2
cargo run --release -- run --adapter examples/llm_with_content_filter.py  --suite healthcare_v1 --output outputs/axisB_content_filter_gpt4omini --timeout 120000 --retries 2
cargo run --release -- run --adapter examples/llm_with_hitl_prompt.py     --suite healthcare_v1 --output outputs/axisB_hitl_prompt_gpt4omini --timeout 120000 --retries 2

# Pin Claude Sonnet 4.6 (via OpenRouter) under the same three wrappers:
export OPENAI_BASE_URL=https://openrouter.ai/api/v1 OPENAI_API_KEY=$OPENROUTER_API_KEY VERITASBENCH_MODEL=anthropic/claude-sonnet-4.6
# (re-run the same three cargo lines with new output dirs)

# Same with DeepSeek-R1 (reasoning):
export OPENAI_BASE_URL=https://openrouter.ai/api/v1 OPENAI_API_KEY=$OPENROUTER_API_KEY VERITASBENCH_MODEL=deepseek/deepseek-r1-0528
# (re-run with v13_r1_* output dirs; budget ~3-5h per wrapper run)

# Axis C — trace-ceiling + audit-prompt experiments (v1.3)
cargo run --release -- run --adapter examples/llm_with_full_audit.py        --suite healthcare_v1 --output outputs/v13_full_audit_gpt4omini  --timeout 120000 --retries 2  # 100% Trace ceiling
cargo run --release -- run --adapter examples/llm_bare_with_audit_prompt.py --suite healthcare_v1 --output outputs/v13_audit_prompt_gpt4omini --timeout 120000 --retries 2  # 87.8% bare-LLM-cooperation ceiling

python scripts/aggregate_axis_b.py --markdown docs/my-axis-b.md
python scripts/breakdown_by_type.py outputs/llm_claude_sonnet_46 outputs/axisB_*_claude46  # per-governance-type breakdown
```

If a long run is interrupted, the persistence fix (v1.3) lets you re-invoke the same `--output` dir to resume from the partial NDJSON instead of starting over.

Bring your own adapter to test a governance *pattern* — see [docs/adapter-protocol.md](https://github.com/Chesterguan/veritasbench/blob/main/docs/adapter-protocol.md).

## What's next

v1.3 already shipped the four highest-priority items from the v1.2 backlog: DeepSeek-R1 reasoning datapoint (added to all three axes), runner persistence fix (NDJSON append-log + resume), trace-ceiling experiment (full-audit wrapper at 100%), and audit-asking prompt experiment (87.8% on GPT-4o-mini).

v1.4 will close the remaining gaps documented in [`docs/future-work/v1.3-scope.md`](https://github.com/Chesterguan/veritasbench/blob/main/docs/future-work/v1.3-scope.md):

- **Cross-LLM extension of Axis C.** Audit-asking prompt was tested on GPT-4o-mini (87.8% Trace) and partially on Claude (n=119, runs interrupted by API budget). Replicate cleanly on Claude, GLM-4.6, DeepSeek-R1, and the lower-tier models to map the LLM-cooperation surface across the capability spectrum.
- **Full 10×4 wrapper × LLM matrix.** Currently 3 LLMs × 4 wrappers = 12 cells in Axis B. Extending to all 10 LLMs adds 7×4=28 cells, including the actual Axis A Policy leader GLM-4.6.
- **Per-governance-type wrapper tuning.** The breakdown script revealed dangerous failures concentrate on different scenario types per LLM (Claude on MJ, GPT-4o-mini on SI). The LangGraph `HITL_TYPES` set should be tuned per LLM — or made data-driven from observed DF concentration — to push Ctrl above 50%.
- **Provider-pinning + quantization metadata.** Both currently un-instrumented; see `benchmark-realism-improvements.md`.
- **Clinician audit of 100-scenario subset.** Closes the LLM-judged-ground-truth caveat.

If you work in a regulated industry and would fund a medical-LLM access grant (Meditron3-70B, HuatuoGPT-o1-72B, Med42-70B via Together.ai or HF Inference Endpoints), please reach out.

If your governance architecture claims to solve the Traceability/Controllability gap, I want to benchmark you. Open an issue with your adapter.

---

**Repo**: [github.com/Chesterguan/veritasbench](https://github.com/Chesterguan/veritasbench)
**Author**: Ziyuan Guan ([@chesterguan](https://github.com/Chesterguan))
**License**: Apache-2.0 (both code and scenarios)
**DOI**: [10.5281/zenodo.19403623](https://doi.org/10.5281/zenodo.19403623)
