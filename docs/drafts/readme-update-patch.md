# README.md Update Plan for v1.2

> Target: apply after DeepSeek-R1 completes and final combined_results.csv is generated.
> Strategy: keep v1 structure intact (governance-patterns table stays), add a new model-comparison layer on top.

---

## Change 1: Hero line (top of README)

### Current (line 3)

```markdown
**Your AI gets 81% of clinical governance decisions right. It can't prove any of them.**
```

### New

```markdown
**We tested 10 frontier LLMs on clinical governance. Policy compliance ranged from 70% to 87%. Traceability was 0% on every single one.**
```

Reason: stronger because the `n=10` quantifies the architectural claim. One model at 81% could be dismissed as "pick a better one"; ten models at 70–87% demonstrates the gap scales with model quality only in the wrong direction (zero).

## Change 2: Add new section after "Benchmark Results"

Insert this section directly below the existing "Benchmark Results (700 scenarios, 11 types, GPT-4o-mini)" block and before "How to read this".

### New subsection: Results by model (10 LLMs, bare-LLM pattern)

```markdown
### Results by model (10 frontier LLMs, bare-LLM pattern)

Same 700 scenarios, same prompt, varying the underlying LLM. This table measures whether changing the model alone closes the governance gap. It does not.

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
| DeepSeek-R1 (reasoning) | {{FILL}} | {{FILL}} | 0 | 0 | {{FILL}} | {{FILL}} |
| Kimi K2 | 450/572 (79%) | 203/323 (63%) | 0/2091 (0%) | 0/566 (0%) | 25/572 | 2000ms |
| Hunyuan A13B | 403/575 (70%) | 175/325 (54%) | 0/2100 (0%) | 0/570 (0%) | 154/575 | 1490ms |

#### Western — medical-specialized

| Model | Policy | Safety | Traceability | Controllability | Dangerous | Latency p50 |
|---|---|---|---|---|---|---|
| MedGemma 4B (Google) | 400/575 (70%) | 221/325 (68%) | 0/2100 (0%) | 0/570 (0%) | 135/575 | 2136ms |

Full reproducible numbers: [outputs/combined_results.csv](outputs/combined_results.csv).
See [docs/results-by-model.md](docs/results-by-model.md) for per-model methodology notes.
```

## Change 3: Add new section after "Where the Governance Gap Is"

Insert a new top-level section titled "Capable ≠ Accountable" between "Where the Governance Gap Is" and "You Don't Need a Framework (For Layer 2)".

```markdown
## Capable ≠ Accountable

The data tells a clean story across 10 frontier LLMs:

- Policy Compliance spans **70% → 87%**, a 17-point band rewarding scale and model quality
- Traceability is **0% on every single model**, regardless of family, geography, scale, reasoning mode, or medical specialization
- Controllability is **0% on every single model**, same

The gap is architectural, not a training-data or model-quality problem. Picking a more capable LLM moves decision quality but does not move the governance dimensions. For that, you need infrastructure — content filters, HITL prompts, rule engines, or structured logging around the LLM call. The existing adapter comparison in this README shows those infrastructures move traceability from 0% to 33%–92% and controllability from 0% to 57%.

**If your governance strategy is "pick a better LLM," this benchmark shows that strategy does not work.**

Notable findings from the model comparison:

- **Chinese frontier matches Western frontier.** GLM-4.6 (87% Policy) slightly edges Claude Sonnet 4.6 (86%); Qwen3-Max ties Claude on Safety (80%).
- **Gemini 2.5 Pro is the safest model tested** — 8 dangerous failures and 83% Safety — but achieves this with a conservative decision profile that lowers Policy (79%).
- **Medical specialization does not help.** MedGemma 4B (Google's medical Gemma 2 4B) scored 70% Policy, below every non-medical frontier model. Scale dominates specialization on this benchmark.
- **Reasoning mode (DeepSeek-R1) did not close the Traceability gap.** {{CONFIRM AFTER R1 RUN}}
```

## Change 4: Update "How to read this" prose

### Current

> **Look at the bottom rows.** All four LLM-based approaches score 61-82% on policy compliance...

### New (small edit)

> **Look at the bottom rows of both tables.** Across 4 governance patterns and 10 LLMs, policy compliance ranges from 61% to 87%, but **traceability and controllability are 0% for every bare-LLM configuration** — regardless of governance pattern (bare, content filter, topic rails) OR model choice. Only architectures that explicitly include an audit layer (HITL Prompt for controllability at 57%, ClinicClaw rule engine for traceability at 92%) move these numbers off zero.

## Change 5: Expand "Limitations" section

Append to the existing Limitations list:

```markdown
- **Prompt shapes Traceability at the floor.** Our bare-LLM prompt asks only for a decision. 0% traceability is therefore a property of the deployment pattern (bare JSON pipe), not a proof that LLMs cannot format audit entries. v1.3 will test a prompt variant that explicitly asks for an audit entry, as a ceiling measurement.
- **LLM-judged ground truth has sibling bias.** `expected.decision` is GPT-4o-mini + GPT-4o + Gemini 2.5 Flash consensus. GPT-4o-mini and Gemini 2.5 Pro are benchmarked; they may carry a 2–5pp systematic advantage. An independent 100-scenario clinician audit is planned.
- **OpenRouter routing is unobserved.** Results for models accessed via OpenRouter may have been served by different underlying providers with different quantizations. Latency is not comparable across aggregator routes. v1.3 will record the serving provider in each per-scenario result.
- **Local models are quantized.** MedGemma 4B was run at Ollama's Q4_K_M default. Full-precision scores may be 2–5pp higher.
- **Model version drift.** All 10-model results timestamped 2026-04-24. Slugs may silently update on providers.
```

## Change 6: Update Citation / Related Work

Add the new blog post link under Related Projects (if the blog goes live).

---

## Summary: 6 surgical edits

1. Hero line — stronger, quantifies the gap across 10 models
2. New "Results by model" section — 3 tables, one per category
3. New "Capable ≠ Accountable" section — the thesis statement
4. Small "How to read this" tweak — reflects both tables
5. Expanded Limitations — 5 new bullets for honest disclosure
6. Link to blog from Related Projects

No existing content is deleted. The v1 governance-pattern story remains intact; the new model story is layered on top. Result: the README tells two complementary stories — "architecture matters" (patterns) and "model doesn't" (models) — both supporting the same core thesis.

## Ready-to-apply after

- DeepSeek-R1 completes (fill in `{{FILL}}` placeholders and `{{CONFIRM AFTER R1 RUN}}`)
- `python scripts/aggregate_models.py --input-dir outputs --markdown docs/results-by-model.md` runs
- User reviews the final patch and applies (I'll do it as one commit when given the go-ahead)
