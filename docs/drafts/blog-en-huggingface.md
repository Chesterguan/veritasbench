# We Tested 9 LLMs and 4 Governance Wrappers on Clinical Decisions. Only One Axis Moves Traceability.

> Companion blog post for VeritasBench v1.2. Target: HuggingFace Blog / Medium / personal Substack.
> Words: ~2000. Charts: `![models](./benchmark-chart-models.png)` and `![wrappers](./benchmark-chart-wrappers.png)` — generated from `outputs/combined_results.csv` and `outputs/wrapper_comparison.csv`.

---

## TL;DR

We ran a 700-scenario clinical governance benchmark along two independent axes.

**Axis A — vary the LLM, keep the wrapper.** 9 frontier LLMs, identical bare-LLM prompt (Claude Sonnet 4.6, GPT-4o-mini, Gemini 2.5 Pro, DeepSeek-V3.2, Qwen3-Max, GLM-4.6, Kimi K2, Hunyuan A13B, MedGemma 4B). Policy compliance ranged **69.6% → 86.9%**. **Traceability = 0.0% on all 9. Controllability = 0.0% on all 9.**

**Axis B — pick the winner, vary the wrapper.** Two LLM tiers (Claude Sonnet 4.6 — Axis A's #2 model; GPT-4o-mini — #5) under four governance patterns each (bare, NeMo Guardrails, OpenAI Guardrails, LangGraph HITL). Same 700 scenarios. Traceability moved **0% → 33.1%** identically on both LLMs. Controllability moved **0% → 47.4%** identically on both LLMs. (GLM-4.6, Axis A's Policy leader, was attempted but its NeMo wrapper combo paced at ~8 hours per run — the actual Policy winner has no wrapper data yet, deferred to v1.3.)

The two axes together are the architectural claim, now provable instead of assertable: **swapping models cannot close the governance gap. Swapping the pipeline can — and the same wrapper produces the same Trace/Ctrl gain regardless of which LLM is underneath.** The model is not the bottleneck. The pipeline is.

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

(Full reproducible numbers at [outputs/combined_results.csv](https://github.com/Chesterguan/veritasbench/blob/main/outputs/combined_results.csv).)

### What Axis A tells us

**Policy compliance spans a 17.3 pp band.** GLM-4.6 leads (86.9%) by a hair over Claude Sonnet 4.6 (85.7%). The bottom is held by small or quantized models: Hunyuan A13B at 70.1%, MedGemma 4B at 69.6%. Scale and general capability matter a lot for decision quality.

**Chinese frontier matches Western frontier.** GLM-4.6, Qwen3-Max, and DeepSeek-V3.2 are all within 4 pp of Claude Sonnet 4.6 on policy, and Qwen3-Max ties Claude on safety (80.3% vs 79.7%) with fewer dangerous failures (15 vs 14 — noise). Lab of origin stopped being a capability signal once you're above the frontier.

**Dangerous failures cluster into three tiers.** Frontier (<30): Claude 14, Qwen 15, GLM 23, Kimi 25, GPT 26, DeepSeek 29. Gemini is an outlier with only 8. Failing tier: Hunyuan 154, MedGemma 135 — both 20%+ dangerous-failure rates.

**Medical specialization didn't help.** MedGemma 4B — Google's medical-fine-tuned Gemma 2 — scored below every non-medical model tested. Part of this is quantization (Q4_K_M Ollama), but the 16 pp gap against Claude is too large to explain with quantization alone. Domain fine-tuning at 4B can't compensate for scale on clinical governance reasoning.

**Traceability and Controllability are 0% on every single model.** Not one model — not Claude Sonnet, not Gemini, not GLM, not the dedicated medical one — produced a single audit entry or a single halt-for-approval signal. The Y axis of the "capability vs. governance" plot is flat:

```
Policy %   Traceability %
87         0
86         0
83         0
83         0
81         0
79         0
79         0
70         0
70         0
```

Axis A is the null result. **Swapping the LLM moves Policy by ±17pp and moves Trace/Ctrl by exactly zero.**

---

## Axis B: pick the winner, vary the wrapper

Axis A picked the headline. GLM-4.6 leads Policy at 86.9%, Claude Sonnet 4.6 at 85.7% (+4.7pp over GPT-4o-mini's 81.0%). But all three — and the other six — score 0% on Traceability and Controllability. So the next question: pick a winner, add a governance wrapper, see what moves.

We re-ran the wrapper experiments fresh on 2026-04-27, with **two LLM tiers** to test whether the wrapper effect transfers across model strength:

- **Claude Sonnet 4.6** — Axis A's #2 model on Policy (Axis A: 85.7%), strongest fully-reproducible LLM available
- **GPT-4o-mini** — Axis A's #5 model (81.0%), included as a controlled cross-tier comparison

Each LLM ran the same 700 scenarios under each of four pipelines:

- **Bare LLM** — no wrapper, direct API call
- **NeMo Guardrails** — NVIDIA's [`nemoguardrails`](https://github.com/NVIDIA/NeMo-Guardrails) library with Colang topic/content rails (no audit primitive, no halt primitive)
- **OpenAI Guardrails** — moderation API + regex PHI scrubbing as input/output guardrails (audit entries from guardrail evaluations, no halt primitive)
- **LangGraph HITL** — LangGraph `StateGraph` with real `interrupt` nodes that halt execution on `missing_approval` and `emergency_override` scenario types

(GLM-4.6, the Axis A Policy leader, was attempted but the NeMo+GLM combo paced at ~8 hours per run — combined per-call NeMo init overhead × GLM's higher inference latency. Deferred to v1.3 once the runner persistence fix lands and we can run unattended overnight.)

### Results — full 2 × 4 matrix

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

Bare baselines come from the 2026-04-24 Axis A runs (n=700 each, full schema with `dangerous_failures`). The 8 wrapper rows are fresh full runs on 2026-04-27, identical 700 scenarios, single-source per row — no cross-run blending.

### What the matrix tells us

**1. Traceability and Controllability are LLM-invariant.** Same wrapper, two different LLMs → identical gains:

| | Trace gain | Ctrl gain |
|---|---|---|
| + NeMo Guardrails | 0pp / 0pp | 0pp / 0pp |
| + OpenAI Guardrails | **+33.1pp / +33.1pp** | 0pp / 0pp |
| + LangGraph HITL | **+33.1pp / +33.1pp** | **+47.4pp / +47.4pp** |

The LangGraph `interrupt` primitive fires deterministically on `missing_approval` and `emergency_override` scenarios — the LLM's output isn't on that decision path. Same logic for guardrail-derived audit entries: they come from the wrapper's evaluation events, not from the LLM's response content. **Trace and Ctrl are properties of the pipeline, not of the model.** No LLM produces them without a wrapper; any LLM produces them with one.

**What 33.1% Trace actually means.** This is a *floor*, not a ceiling. The grader scores Traceability out of 3 sub-criteria per scenario (entry exists + required fields populated + semantic reason). Both wrappers we tested use the same skeletal `_trace_entry` template — `{timestamp, action}` filled, `{actor, resource, reason}` left null — so each scenario with any entry earns 1 of 3 = 33.3%. The fact that two different wrappers land on identical Trace scores is mostly because they share the same minimal-audit-entry shape, not because 33% is the natural ceiling for governance wrappers. A wrapper that populated `actor` and `reason` would score higher. The headline finding ("wrappers move Trace off zero on both LLMs") survives, but the *level* (33.1%) is structural.

**2. OpenAI Guardrails is the only wrapper whose Policy hit depends on LLM tier.** Comparing ΔPolicy:

| Wrapper | GPT-4o-mini ΔPolicy | Claude ΔPolicy | Difference |
|---|---:|---:|---:|
| + NeMo Guardrails | +0.2pp | −2.2pp | 2.4pp |
| + LangGraph HITL | −14.2pp | −13.4pp | 0.8pp |
| + **OpenAI Guardrails** | **−6.9pp** | **−2.6pp** | **4.3pp** |

LangGraph's interrupt fires on the same scenario types regardless of LLM, costing ~13–14pp Policy on both — that gap is structural, LLM-invariant. NeMo's content rails cost roughly equally on both. Only OpenAI Guardrails shows a clear LLM-tier dependence: its moderation+regex pipeline asks the LLM to be more conservative, and Claude is calibrated enough to remain mostly correct under that prompting (−2.6pp), while GPT-4o-mini over-corrects to defensive denies (−6.9pp). Whether this pattern generalizes to other wrappers and other LLMs is a v1.3 question — n=2 LLMs and n=1 demonstrating wrapper isn't enough to claim "Policy degradation always depends on LLM tier."

**3. NeMo Guardrails + Claude is the surprise dangerous-failures standout — though n=3 limits how hard we can push the claim.** The DF column reveals a non-obvious finding: **3/575 (0.5%)** — the lowest DF rate of any combination tested, suggestive of a 79% reduction from Claude bare's 2.4%. The same wrapper on GPT-4o-mini gives 4.3% — basically equal to GPT bare. NeMo's content-safety rails appear to make Claude markedly conservative on dangerous actions; GPT-4o-mini doesn't respond the same way to the same prompt prefix. **The wrapper-effect on Dangerous-failures looks like a wrapper × LLM interaction**, not a pure-architectural property. Caveat: with only 3 dangerous failures observed, the 95% confidence interval on this rate is roughly [0.1%, 1.5%]; a single different scenario flipping would shift the headline noticeably. Treat the 0.5% as suggestive evidence of a striking interaction worth replicating, not as a settled number.

OpenAI Guardrails consistently lowers DF on both LLMs (4.5%→1.2% GPT-4o-mini, 2.4%→1.0% Claude — both ~75% reduction). LangGraph HITL has mixed DF effects: interrupts catch some dangerous decisions in the routed types, but the LangGraph `decide` node handling non-HITL types doesn't apply extra conservatism.

**4. No wrapper clears 50% on both Trace AND Ctrl simultaneously.** Each one moves only a subset of dimensions:
- NeMo Guardrails: helps Dangerous (only on calibrated LLMs), no Trace, no Ctrl
- OpenAI Guardrails: adds Trace, halves DF, no Ctrl, costs Safety
- LangGraph HITL: adds Trace AND Ctrl, halves DF, costs Policy and Safety

None of the three was designed around audit and halt as first-class primitives.

---

## The joint picture: capable ≠ accountable

Across both axes, **17 data points** (9 LLMs × bare on Axis A; 2 LLMs × 4 wrappers on Axis B):

| Dimension | Axis A range (model varies, bare) | Axis B range (2 LLMs × 4 wrappers) |
|---|---|---|
| Policy | 69.6% → 86.9% (Δ 17.3 pp) | 66.8% → 85.7% (Δ 18.9 pp) |
| Safety | 53.8% → 83.3% (Δ 29.5 pp) | 51.7% → 79.7% (Δ 28.0 pp) |
| **Traceability** | **0% → 0%** (Δ 0 pp) | **0% → 33.1%** (identical Δ across both LLMs) |
| **Controllability** | **0% → 0%** (Δ 0 pp) | **0% → 47.4%** (identical Δ across both LLMs) |
| Dangerous (best/worst) | 8/572 (1.4%) → 154/575 (26.8%) | 3/575 (0.5%) → 26/575 (4.5%) |

Policy and Safety are capability-sensitive — a better LLM *or* a different wrapper moves them. Traceability and Controllability are capability-insensitive on Axis A and capability-*invariant* on Axis B (same wrapper → same gain on both LLM tiers we tested). **They are architectural properties, not model properties.**

If your governance strategy is *"pick a better LLM"*, this benchmark shows that strategy does not close the Trace/Ctrl gap. Picking a better LLM moves Policy from 81% to 87%. It does not move Traceability one percentage point off zero. The gap is not in decision quality. It is in the pipeline's ability to *record* decisions and *halt* for human review — architectural features that a bare LLM pipeline cannot produce regardless of how smart the LLM is, and that wrappers produce even on a mid-tier LLM.

**Pick your model for decision quality. Pick your wrapper for governance. They are different knobs.**

---

## Models attempted but not in the headline comparison

| Model | Outcome | Reason not reported |
|---|---|---|
| DeepSeek-R1 (reasoning, OpenRouter) | 324/700 scenarios scored, data lost | Runner hit `[Errno 1] Operation not permitted` on the output volume mid-run; all scored scenarios were in a single at-end write and were discarded with the failures. Persistence fix planned for v1.3, then re-run. |
| Meditron-7B (Ollama, Llama 2 base) | 28% of scenarios timed out | Model is trained on clinical QA text and doesn't reliably emit JSON-only responses — adapter-layer instruction-following issue, not a capability signal. |
| Meditron3-8B (Ollama, Q4_K_M GGUF) | 700/700 completed | 57% Policy / 191 dangerous failures, dominated by 4-bit quantization loss rather than medical-specialization signal. Publishing would mislead readers into "medical-specialized = weak" when the story is "Q4 quant is lossy." |
| HuatuoGPT-II-34B, HuatuoGPT-o1-72B, Meditron3-70B, Med42-70B, OpenBioLLM-70B, PULSE-7b/20b | Never ran | None available on OpenRouter / SiliconFlow / Novita / HuggingFace Inference Providers as of 2026-04-24. All are open-weight on HuggingFace — the access problem is hosting, not licensing. |

This list is load-bearing. DeepSeek-R1 and the medical-specialized models were the exact datapoints needed to test whether reasoning-mode or domain specialization might close the Traceability/Controllability gap. We haven't ruled that out — but nothing in the 9 models we could benchmark, or the 4 wrappers we ran, suggests it will.

## Caveats (must read before citing)

- **Axis A prompt is minimal by design.** Asks only for a decision, not audit entries or halt signals. This is the naive deployment pattern. A critic can correctly note that a different prompt asking for audit entries might score non-zero on traceability. The architectural claim still holds: bare deployment pipelines don't have a place to *enforce* those outputs, and Axis B shows that adding the infrastructure (not changing the prompt) is what moves the number.

- **Axis B wrapper depth is representative, not exhaustive.** Each framework is a canonical integration — `nemoguardrails` with Colang config, LangGraph `StateGraph` with `interrupt` nodes, OpenAI moderation+regex PHI as guardrails. These are not adversarially-tuned configs designed to maximize scores. Readers should not infer "NeMo Guardrails is bad" from one config — they should infer "the out-of-the-box NeMo pattern has no audit primitive." Both are true.

- **Axis B uses 2 of the 9 Axis A LLMs.** We tested Claude Sonnet 4.6 (Axis A's #2) and GPT-4o-mini (#5) under all 4 wrappers. GLM-4.6 (Axis A's #1) was attempted but the NeMo+GLM combination paced at ~8 hours per run due to combined per-call init overhead and GLM's higher latency; deferred to v1.3 once the runner persistence fix lands and overnight runs are safe. The "wrapper effect transfers across LLM tiers" claim rests on these two LLMs; transfer to GLM-4.6 and other Axis A models is plausible (Trace and Ctrl gains are deterministic by wrapper architecture) but not yet measured.

- **Axis B bare baselines come from 2026-04-24 Axis A runs.** Wrapper runs are 2026-04-27. The same-model bare run replicates within ~0.2pp Policy across dates, so this is acceptable, but careful comparisons across the two dates carry a small slug-drift risk.

- **Skipped scenarios on Axis A.** Kimi K2 (n=697) and GLM-4.6 (n=696) had early infrastructure errors that exhausted the runner's 2 retries. Percentages on those rows are evaluated denominators; worst-case ±0.5 pp impact on those models' headline numbers.

- **MedGemma 4B is Q4-quantized.** Full-precision MedGemma 4B may score 2–5 pp higher. We flag this because it affects the medical-specialization story; the 16 pp gap against Claude is too large for quantization alone, but part of the delta could be Q4.

- **Sibling grading.** Ground-truth `expected` decisions are the multi-model consensus of GPT-4o-mini + GPT-4o + Gemini 2.5 Flash. Since GPT-4o-mini and Gemini 2.5 Pro are benchmarked, their scores may carry a 2–5 pp systematic advantage. Independent clinical-expert audit is listed as future work.

- **OpenRouter routing is unobserved.** Models routed through OpenRouter may have been served by different underlying providers with different quantizations. Latency is not comparable across routes; scores should be.

- **Model version drift.** Axis A runs are timestamped 2026-04-24. Axis B wrapper runs are 2026-04-27. Slugs like `anthropic/claude-sonnet-4.6` or `openai/gpt-4o-mini` may silently update.

See [docs/future-work/benchmark-realism-improvements.md](https://github.com/Chesterguan/veritasbench/blob/main/docs/future-work/benchmark-realism-improvements.md) for the plan to close these caveats in v1.3.

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

python scripts/aggregate_axis_b.py --markdown docs/my-axis-b.md
```

Bring your own adapter to test a governance *pattern* — see [docs/adapter-protocol.md](https://github.com/Chesterguan/veritasbench/blob/main/docs/adapter-protocol.md).

## What's next

v1.3 will address the caveats above: prompt variant that asks for audit entries, provider-pinning, quantization metadata, DeepSeek-R1 reasoning datapoint, clinician audit of a 100-scenario subset, and an Axis A × Axis B sweep (every wrapper × every model = 9×4 grid) to test whether wrapper gains transfer across LLMs.

If you work in a regulated industry and would fund a medical-LLM access grant (Meditron3-70B, HuatuoGPT-o1-72B, Med42-70B via Together.ai or HF Inference Endpoints), please reach out.

If your governance architecture claims to solve the Traceability/Controllability gap, I want to benchmark you. Open an issue with your adapter.

---

**Repo**: [github.com/Chesterguan/veritasbench](https://github.com/Chesterguan/veritasbench)
**Author**: Ziyuan Guan ([@chesterguan](https://github.com/Chesterguan))
**License**: Apache-2.0 (both code and scenarios)
**DOI**: [10.5281/zenodo.19403623](https://doi.org/10.5281/zenodo.19403623)
