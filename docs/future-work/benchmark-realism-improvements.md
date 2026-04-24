# Benchmark Realism Improvements — Follow-up Plan

> Status: Captured 2026-04-24 during the 11-model run. Not blocking v1.x.
> Motivation: honest-framing review raised several ways the benchmark
> could better reflect real-world LLM governance, rather than testing
> a specific prompt + ground-truth pipeline.

## Issues identified

### 1. Prompt limits the "governance ceiling"

The shared prompt in `examples/_llm_shared.py` asks for a decision only:

> `Respond with ONLY a JSON object: {"decision": "allow" | "deny" | "blocked_pending_approval"}`

This makes `audit_entries=[]` trivially true. The 0% Traceability score is
therefore **partly a statement about the prompt**, not a hard LLM limitation.

**The architectural claim still holds** — bare deployment pipelines don't have
a place to record audit entries even if the LLM could produce them. But
critics will note the ceiling is prompt-dependent.

#### Proposed fix

Add a second adapter path `llm_openai_compat_with_audit.py` that explicitly
asks the model to emit a full audit entry (`actor`, `action`, `resource`,
`reason`) alongside the decision. Compare:
- **Bare**: current result — 0% traceability (measures deployment pattern)
- **Asked**: asked-for-audit result — measures LLM capability to format audit

Two columns in the final table, same suite. This lets readers see both
"what a bare pipe produces" and "what the LLM can produce when asked".

### 2. Ground truth is LLM-judged

`scripts/llm_judge_validate.py` uses GPT-4o-mini + GPT-4o + Gemini 2.5 Flash
consensus to compute `expected.decision`. Since GPT-4o-mini and Gemini 2.5 Pro
are tested, there is a ~2-5 pp systematic advantage for models in the judge
pool.

#### Proposed fix

Sample audit of 100 scenarios by a licensed clinician (MD/PharmD). Compare
clinician decision with LLM-judge consensus. If they agree on >90%, keep
the LLM judges. If <90%, migrate ground truth to clinician labels, at least
for the audited subset.

Long-term: move ground truth outside the model population entirely
(clinician panel, Joint Commission case library, published medical malpractice
reviews).

### 3. OpenRouter routing is unobserved

Results for models routed through OpenRouter may have been served by different
backends (Alibaba direct vs Novita vs Fireworks, each with different
quantization/serving stacks). We don't record which backend handled each
scenario.

#### Proposed fix

In `examples/llm_openai_compat.py`, capture the `provider_name` header from
OpenRouter responses and pass it through in a new `meta.provider` field of
the AdapterResult. Runner persists this in `per_scenario[].meta`. Final
report includes a histogram of which providers served a given model.

Also: accept an optional `provider_pin` yaml field per provider in
`providers.yaml` that sets OpenRouter's `provider: { order: [...] }`
parameter to force a single backend.

### 4. Local model quantization not recorded

Runs of MedGemma 4B, Meditron 7B, Meditron3-8B used Ollama defaults
(Q4_K_M). The `report.json` does not encode this. Scores for these
models should not be directly compared to full-precision API runs
without a caveat.

#### Proposed fix

In `examples/llm_openai_compat.py`, optionally query the Ollama
`/api/show` endpoint on startup to capture the quantization level
(`parameter_size`, `quantization_level`) and include it in result
metadata. Final report notes quantization next to each local-model row.

### 5. Model version drift not pinned

Slugs like `anthropic/claude-sonnet-4.6` may update silently when the
provider releases a revision. Our reports capture only the timestamp.

#### Proposed fix

Capture the returned `model` field from each response (many providers
return a more specific build ID than what was requested, e.g.
`claude-sonnet-4-6-20260401`). Store in `per_scenario[].meta.model_version`.
Include a histogram in the final report showing which specific model
versions served a run.

### 6. Blind mode is off by default

`--blind` strips `scenario_type` from the input so adapters can't cheat
by matching on type. Our 11-model run did not use `--blind`.

#### Proposed fix

Run a second pass of the top 4 models under `--blind` and report the
delta. If the delta is small (e.g. <2 pp), publish both numbers and note
that scenario-type hints don't dominate. If the delta is large, that's
itself an interesting finding — scenario-type names are leaking signal
to models trained on medical data.

### 7. "Bare LLM" is one deployment pattern among many

v1 already has 5 governance patterns (bare, content filter, topic rails,
HITL prompt, ClinicClaw rule engine). Our new model-comparison table is
"bare LLM, vary the model." Equally interesting: "fix a strong model
(Claude Sonnet 4.6), vary the governance pattern." Would show that
infrastructure matters more than model choice, on the same model.

#### Proposed fix

Run Claude Sonnet 4.6 through all 4 v1 governance patterns (not just
bare), to produce a "pattern × model" matrix. Demonstrates that the
90%+ traceability under ClinicClaw is from architecture, not from
ClinicClaw being a better "reasoner" — because the underlying LLM is
the same strong model across all patterns.

## When to do this

Not before v1.2 ships (the 11-model blog post / LinkedIn / README update).
Ship the current results first, honestly disclose the caveats in Limitations,
then iterate on these improvements for v1.3.

## Priority order

If we could do only one of the above, **#3 (provider logging) and #4
(quantization capture)** are the cheapest and most honest — they just
add metadata, no new runs needed. #1 (audit-asked prompt) is the most
paper-impactful. #2 (clinician audit) is the biggest effort and the
biggest credibility gain.

## Success criterion

The benchmark is "more realistic" when an external reader cannot attack
it with a one-line criticism. Today's v1 has three such criticisms:
1. "You didn't ask for audit entries" → fix with #1
2. "Your judge is one of the models" → fix with #2
3. "You don't know which quantization ran" → fix with #3 and #4

Close all three and the benchmark becomes difficult to dismiss.
