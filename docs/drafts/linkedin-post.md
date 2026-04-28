# LinkedIn Post Drafts

Three variants — pick one or remix. Numbers reflect the **two-axis v1.2 snapshot**:
- Axis A (2026-04-24): 9 LLMs × 700 scenarios × bare LLM.
- Axis B (2026-04-27): 2 LLM tiers (Claude Sonnet 4.6, GPT-4o-mini) × 700 scenarios × 4 governance wrappers (bare, NeMo Guardrails, OpenAI Guardrails, LangGraph HITL).

---

## Version A — Two-axis hook (recommended)

We ran a 700-scenario clinical governance benchmark along two independent axes.

**Axis A — vary the LLM, keep the wrapper.** 9 frontier models (Claude Sonnet 4.6, GPT-4o-mini, Gemini 2.5 Pro, DeepSeek-V3.2, Qwen3-Max, GLM-4.6, Kimi K2, Hunyuan A13B, MedGemma 4B), identical bare-LLM prompt.
— Policy compliance: 69.6% → 86.9%
— Traceability: **0% on every single model**
— Controllability: **0% on every single model**

**Axis B — pick a winner, vary the wrapper.** Two LLM tiers (Claude Sonnet 4.6, GPT-4o-mini) under bare + NeMo Guardrails + OpenAI Guardrails + LangGraph HITL. Same 700 scenarios. (GLM-4.6, the actual Axis A Policy leader, has no wrapper data yet — its NeMo combo paced too slow for v1.2; coming in v1.3.)
— Traceability: 0% → **33.1%** (identical gain on BOTH LLMs)
— Controllability: 0% → **47.4%** (identical gain on BOTH LLMs)

Swapping the LLM among 9 frontier models moves Policy ±17pp and moves Trace/Ctrl by exactly zero. Swapping the wrapper at fixed LLM moves Trace 0 → 33pp and Ctrl 0 → 47pp — and the same wrapper produces identical Trace/Ctrl gains on Claude Sonnet 4.6 and GPT-4o-mini. The architectural lever is wrapper-side, not model-side.

**The model is not the bottleneck. The pipeline is.**

In a regulated industry, a correct decision without documentation is equivalent to no decision. "Our model is smarter" is not a defense when a lawyer asks for the chart. Model quality → decision quality. Pipeline design → audit and halt primitives. They're different knobs.

VeritasBench (open source, Apache-2.0): github.com/Chesterguan/veritasbench

#AIGovernance #HealthcareAI #LLM #ClinicalAI

---

## Version B — Single-number hook

A 17 percentage-point gap on decision quality.
A 47.5 percentage-point gap on controllability.
Two different axes. Two different knobs.

We tested 9 frontier LLMs at the bare-LLM pattern — Claude Sonnet 4.6, GPT-4o-mini, Gemini 2.5 Pro, DeepSeek-V3.2, Qwen3-Max, GLM-4.6, Kimi K2, Hunyuan A13B, MedGemma 4B. Policy compliance varied 70% → 87%. Traceability and controllability were 0% on every single one.

Then we pinned GPT-4o-mini and swapped the governance wrapper. NeMo Guardrails, OpenAI Guardrails, LangGraph HITL. Policy moved ±14pp. **Controllability moved 0% → 47.5%** — the LangGraph `interrupt` primitive genuinely halts execution for human review, a property no amount of model capability can produce.

Swapping the LLM didn't move the governance dimensions. Swapping the wrapper did.

If your AI governance strategy is "pick a better LLM," this benchmark says it won't close the gap. Architecture is the lever. Model quality is a different lever.

VeritasBench: github.com/Chesterguan/veritasbench

#AIGovernance #HealthcareCompliance #LLM

---

## Version C — Contrast hook

Claude Sonnet 4.6 made 14 dangerous clinical errors out of 575.
Hunyuan A13B made 154 — 11× more.

Both produced identical audit trails: none.

Then we wrapped GPT-4o-mini in LangGraph's Human-in-the-Loop pattern — a middling model with an interrupt primitive. It halted for human review on 47.5% of the scenarios where it should.

When a patient is harmed, the lawyer doesn't care which model you used. They care whether you can produce the record. And whether you halted in time.

Across 9 models on the bare-LLM pattern: Policy 70–87%, Trace 0%, Ctrl 0%. Across 4 governance wrappers on the same LLM: Trace 0–33%, Ctrl 0–47.5%.

Governance is architecture, not model quality.

github.com/Chesterguan/veritasbench

---

## Hashtag strategy

For reach:
`#AIGovernance #HealthcareAI #LLM #ClinicalAI #HealthcareCompliance`

For technical audience:
`#LLMBenchmarks #AIBenchmarks #MedicalAI #AIResearch`

For Chinese audience (if cross-posting 简体):
`#AI治理 #医疗AI #大模型 #合规`

## Posting tips

- LinkedIn rewards POSTING TIME CONSISTENCY. If you normally post 9am PT, stick to that.
- First comment should link to blog post (keeps LinkedIn algorithm happy vs external link in main post)
- Tag nobody who didn't consent. Don't @ Anthropic, OpenAI, NVIDIA, etc.
- Engage in the comments for the first 2 hours after posting — LinkedIn boosts posts with early engagement.
- If hitting 1000+ impressions, post a "thanks for reading, here's the blog" follow-up 24h later.

## What to update before posting

Replace `github.com/Chesterguan/veritasbench` with the actual HuggingFace blog URL once published (or keep both).

Version A is the full two-axis pitch — best for a technical LinkedIn audience.
Version B emphasizes the single provocative comparison (17pp vs 47.5pp) — best for a mixed audience that needs one number to remember.
Version C is the ethical-stakes angle — best for healthcare-compliance and regulated-industry readers.

Do not claim "10 models" — DeepSeek-R1 was attempted and the data was lost to a runner persistence bug. It's deferred to v1.3. If asked, the honest answer is: "9 produced comparable results, 8 others didn't for documented reasons — see the blog."
