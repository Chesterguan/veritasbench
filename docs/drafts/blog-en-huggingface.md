# We Tested 10 Frontier LLMs on Clinical Governance. They All Failed the Same Test.

> Companion blog post for VeritasBench v1.2. Target: HuggingFace Blog / Medium / personal Substack.
> Words: ~1700. Placeholders: `{{GEMINI_ROW}}`, `{{DEEPSEEK_R1_ROW}}` to be filled after runs complete.
> Chart placeholder: `![chart](./benchmark-chart-models.png)` — generated from outputs/combined_results.csv after all runs.

---

## TL;DR

We ran 10 frontier LLMs — Claude Sonnet 4.6, GPT-4o-mini, Gemini 2.5 Pro, DeepSeek-V3.2, DeepSeek-R1, Qwen3-Max, GLM-4.6, Kimi K2, Hunyuan A13B, and MedGemma 4B — against a 700-scenario clinical governance benchmark. The models spanned four research labs, two geographies, two reasoning modes, and one medical specialization.

**Policy compliance varied from 70% to 87%. Traceability was 0% across every single model. Controllability was 0% across every single model.**

The governance gap does not close with scale, does not close with reasoning, does not close with medical fine-tuning. It is architectural. The benchmark proves this by testing the same pattern (bare LLM, JSON output) across model families that collectively represent ~$10B in model R&D.

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

## The 10 models we tested

Every model was invoked via the same bare-LLM pattern: the scenario JSON is sent, the model is asked to respond with `{"decision": "allow" | "deny" | "blocked_pending_approval"}`, and its output is parsed. No governance infrastructure is added — just the LLM, a system prompt, and temperature 0.

| Category | Models |
|---|---|
| **Western general (frontier)** | Claude Sonnet 4.6, GPT-4o-mini, Gemini 2.5 Pro |
| **Chinese general (frontier)** | DeepSeek-V3.2, Qwen3-Max, GLM-4.6, Kimi K2, Hunyuan A13B |
| **Chinese general (reasoning)** | DeepSeek-R1 |
| **Western medical (specialized)** | MedGemma 4B (Google, Gemma 2 base) |

Notable design choices:
- **Routing**: frontier Chinese and Western models through OpenRouter (a single aggregator). Gemini via the native Google GenAI SDK (for context caching and comparability). MedGemma via local Ollama (Q4_K_M quantization).
- **Prompt**: identical across all models. Asks only for a decision (no audit entries, no halt signals). This is the naive deployment pattern — most production LLM integrations use something like this before adding governance wrappers.
- **Temperature**: 0 (reproducibility).
- **Retries**: 2 at runner level, plus per-adapter 429 exponential backoff.

## The results

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
| {{DEEPSEEK_R1_ROW}}
```

```
### Western — medical-specialized

| Model                | Policy          | Safety          | Traceability | Controllability | Dangerous  | p50      |
|----------------------|-----------------|-----------------|--------------|-----------------|------------|----------|
| MedGemma 4B (Google) | 400/575 (69.6%) | 221/325 (68.0%) | 0/2100 (0%)  | 0/570 (0%)      | 135/575    | 2136 ms  |
```

(Full reproducible numbers at [outputs/combined_results.csv](https://github.com/Chesterguan/veritasbench/blob/main/outputs/combined_results.csv).)

## What the data says

### 1. Chinese frontier matches Western frontier — on capability

GLM-4.6 tops policy compliance at 86.9%, edging Claude Sonnet 4.6's 85.7%. Qwen3-Max ties Claude on safety (80.3% vs 79.7%) and actually beats it on Dangerous Failures (15 vs 14 — statistical noise, but not a gap).

This is the first broad apples-to-apples comparison I've seen where the lab of origin (Beijing/Shanghai vs San Francisco/Mountain View) stops being a signal once you get above the frontier. DeepSeek-V3.2 and Qwen3-Max are effectively peers of GPT-4o-mini and Claude Sonnet 4.6 on this benchmark.

### 2. Capability varies. Governance doesn't.

Plot Policy Compliance against Traceability:

```
Policy %   Traceability %
87         0
86         0
83         0
83         0
81         0
79         0
70         0
70         0
```

The Y axis is flat. Moving from a 13B Chinese generalist (Hunyuan A13B, 70%) to a frontier Chinese reasoner (DeepSeek-R1) or a frontier Western model (Claude Sonnet 4.6, 86%) gains you 16 percentage points on decision quality. **It gains you zero percentage points on traceability.**

That is the architectural claim. The models are not the bottleneck. The pipeline is.

### 3. Medical specialization ≠ better governance

MedGemma 4B — Google's medical-fine-tuned Gemma 2 — scores 69.6% Policy, below every non-medical model tested. A 4B-parameter medical model cannot compensate for scale: Claude Sonnet 4.6 (general) beats it by 16 percentage points on clinical decisions.

This cuts against a common prior that "medical-specialized models will be better at medical tasks." For clinical governance reasoning (which is as much about regulatory text as it is about medicine), general frontier models with strong reasoning appear to dominate.

And MedGemma, like every other model, scored 0% on traceability. Medical fine-tuning doesn't install governance infrastructure either.

### 4. Dangerous failure rate correlates with model capability

"Dangerous Failures" — cases where the model allowed an action that should have been denied or blocked — tracks capability closely:

- Claude Sonnet 4.6: 14 / 575 (2.4%)
- Qwen3-Max: 15 / 575 (2.6%)
- GLM-4.6: 23 / 571 (4.0%)
- GPT-4o-mini: 26 / 575 (4.5%)
- DeepSeek-V3.2: 29 / 575 (5.0%)
- Kimi K2: 25 / 572 (4.4%)
- MedGemma 4B: 135 / 575 (23.5%)
- Hunyuan A13B: 154 / 575 (26.8%)

The top-quartile frontier models make ~3% dangerous errors. The mid-tier models make ~5%. Specialist-but-small models make ~25%. Scale and general capability matter a lot for safety.

**But even Claude Sonnet 4.6's 14 dangerous failures are still 14 dangerous failures.** "Mostly safe" is not a legal category.

## Capable ≠ Accountable

The core finding doesn't need hedging. Across 10 models:

- **Policy compliance ranges from 70% to 87%** — a 17 percentage-point band that rewards larger, stronger, better-trained models.
- **Traceability is 0% on all 10** — a zero-point band that no amount of scale, reasoning, or specialization closes.
- **Controllability is 0% on all 10** — same.

If your organization's governance strategy is *"pick a better LLM"*, this benchmark suggests that strategy will not close the gap. The gap is not in decision quality. It is in the pipeline's ability to *record* decisions and *halt* for human review — both of which are architectural features a bare LLM pipeline cannot produce regardless of how smart the LLM is.

The v1 published results (comparing governance *patterns* rather than models) show the same point from the other side: adding a content-filter wrapper takes traceability from 0% to 33%; a rule-based engine like ClinicClaw takes it to 92%. Infrastructure is what moves these numbers.

## Caveats (must read before citing)

- **Prompt is minimal by design.** The prompt asks only for a decision, not audit entries or halt signals. This is the naive deployment pattern — most production LLM integrations look like this before adding governance wrappers. A critic can correctly note that a different prompt asking for audit entries might score non-zero on traceability. The architectural claim still holds: bare deployment pipelines don't have a place to *enforce* those outputs, and v1's governance-pattern comparison shows that adding the infrastructure (not changing the prompt) is what moves the number.

- **Skipped scenarios.** Kimi K2 (3 policy / 2 safety skipped) and GLM-4.6 (4 / 3 skipped) had early infrastructure errors that exhausted the runner's 2 retries. Their percentages are on the evaluated denominators (572 / 571). Worst-case impact: ±0.5 pp.

- **Local model is quantized.** MedGemma 4B was run via Ollama at the default Q4_K_M quantization. Full-precision MedGemma 4B may score 2–5 pp higher. We mention this because it affects the "medical models underperform" story: part of the gap might be quantization, though the 16 pp gap against Claude is too large for quantization alone to explain.

- **Sibling grading.** Ground-truth `expected` decisions are the multi-model consensus of GPT-4o-mini + GPT-4o + Gemini 2.5 Flash. Since GPT-4o-mini and Gemini 2.5 Pro are benchmarked, their scores may carry a 2–5 pp systematic advantage. Independent clinical-expert audit is listed as future work.

- **OpenRouter routing.** Models routed through OpenRouter (DeepSeek-V3.2/R1, Qwen3-Max, GLM-4.6, Kimi K2, Claude Sonnet 4.6) may have been served by different underlying providers with different quantizations. Latency is not directly comparable across routes; scores should be.

- **Model version drift.** All runs are timestamped 2026-04-24. Slugs like `anthropic/claude-sonnet-4.6` may silently update.

See [docs/future-work/benchmark-realism-improvements.md](https://github.com/Chesterguan/veritasbench/blob/main/docs/future-work/benchmark-realism-improvements.md) for the plan to close these caveats in v1.3.

## Try it

```bash
git clone https://github.com/Chesterguan/veritasbench
cd veritasbench
cargo build --release

cp .env.example .env
# edit .env, add keys
# minimum: OPENROUTER_API_KEY (covers 7 models) + OPENAI_API_KEY (for baseline)

python scripts/run_model.py gpt-4o-mini                   # reproduce the baseline
python scripts/run_model.py deepseek-v3                   # try a Chinese frontier
python scripts/run_model.py deepseek-r1 --timeout 60000   # reasoning model
python scripts/aggregate_models.py --input-dir outputs --markdown docs/my-results.md
```

Bring your own adapter to test a governance *pattern* instead of a model — see [docs/adapter-protocol.md](https://github.com/Chesterguan/veritasbench/blob/main/docs/adapter-protocol.md).

## What's next

v1.3 will address the caveats above (prompt variant asking for audit entries, provider-pinning, quantization metadata, clinician audit of a 100-scenario subset). If you work in a regulated industry and would fund a medical-LLM access grant (Meditron3-70B, HuatuoGPT-o1-72B, Med42-70B via Together.ai or HF Inference Endpoints), please reach out.

If your governance architecture claims to solve the Traceability/Controllability gap, I want to benchmark you. Open an issue with your adapter.

---

**Repo**: [github.com/Chesterguan/veritasbench](https://github.com/Chesterguan/veritasbench)
**Author**: Ziyuan Guan ([@chesterguan](https://github.com/Chesterguan))
**License**: Apache-2.0 (both code and scenarios)
**DOI**: [10.5281/zenodo.19403623](https://doi.org/10.5281/zenodo.19403623)
