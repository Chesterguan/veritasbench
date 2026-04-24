# Medical-Specialized LLM Testing — Follow-up Plan

> Status: Blocked on hosting access. See "Access problem" below.
> Created: 2026-04-24
> Related: `docs/superpowers/specs/2026-04-23-chinese-medical-llm-benchmark-design.md`

## Why this is a separate follow-up

The 2026-04-23 benchmark spec included 3 medical-specialized models: HuatuoGPT-II-34B, HuatuoGPT-o1-72B, and Meditron-70B. During execution on 2026-04-24 we discovered that **none of these models are accessible through any public OpenAI-compatible inference API** that the user has access to. The main benchmark run proceeded with 9 general-purpose models instead.

This document tracks what we learned about medical-LLM accessibility so the next attempt doesn't repeat the dead-end investigation.

## Access problem

Checked against the user's available keys (OpenRouter, SiliconFlow, Novita, HuggingFace) on 2026-04-24:

| Platform | Endpoint | Medical models available? |
|---|---|---|
| OpenRouter | `router.openrouter.ai/v1` | **None.** HuatuoGPT/Meditron/Med42/OpenBioLLM/BioMistral — none routed. |
| SiliconFlow (international) | `api.siliconflow.com/v1` | **None.** 71 hosted models; all general-purpose. |
| Novita AI | `api.novita.ai/v3/openai` | **None.** General models only. |
| HuggingFace Inference Providers | `router.huggingface.co/v1` | **None.** 121 provider-routed models; 0 medical. |
| HuggingFace Serverless Inference | `api-inference.huggingface.co/models/<id>` | **Deprecated** (HTTP 404 on POST for OpenMeditron/PULSE/etc). |

## Candidate models (when access becomes available)

All three are open-weight and available for download on HuggingFace — the access problem is inference hosting, not the weights themselves.

### Tier A: Direct successors to originals in the spec

| Model | HF ID | Size | Notes |
|---|---|---|---|
| Meditron3-70B | `OpenMeditron/Meditron3-70B` | 70B | 2026-updated successor to EPFL Meditron |
| Meditron3-8B | `OpenMeditron/Meditron3-8B` | 8B | Smaller variant, faster to serve |

### Tier B: Chinese medical

| Model | HF ID | Size | Notes |
|---|---|---|---|
| HuatuoGPT-II-34B | `FreedomIntelligence/HuatuoGPT-II-34B` | 34B | Chinese medical generalist |
| HuatuoGPT-o1-72B | `FreedomIntelligence/HuatuoGPT-o1-72B` | 72B | Medical + reasoning |
| PULSE-7bv5 | `OpenMEDLab/PULSE-7bv5` | 7B | Shanghai AI Lab Chinese medical |
| PULSE-20bv5 | `OpenMEDLab/PULSE-20bv5` | 20B | Larger PULSE variant |

### Tier C: Western medical alternatives

| Model | HF ID | Notes |
|---|---|---|
| Med42-70B | `m42-health/Llama3-Med42-70B` | Better-cited than Meditron on some tasks |
| OpenBioLLM-70B | `aaditya/Llama3-OpenBioLLM-70B` | Saama Tech |
| BioMistral-7B | `BioMistral/BioMistral-7B` | Smaller, Mistral-based |

## Paths to unblock

Roughly in order of effort:

### 1. Together.ai (~30 min setup, $5-15 per model run)

Together.ai hosts Meditron-70B and some other medical models. User would need to:
1. Sign up at https://api.together.xyz/
2. Get API key (starts with `tkn_...`)
3. Add to `.env`: `TOGETHER_API_KEY=...`
4. Update `examples/providers.yaml` to point `meditron-70b` at Together.ai

Already scaffolded — see the commented-out Together.ai config in `providers.yaml` under `meditron-70b`.

### 2. HuggingFace Inference Endpoints — dedicated deployment (~$0.70–$3/hour)

Each medical model is deployed as a dedicated endpoint on HF's infrastructure.
- Deploy via https://ui.endpoints.huggingface.co/ for the specific HF model ID
- Use a GPU instance sized to the model (70B needs ~2×A100 or L40S)
- Endpoint gets a unique URL; set `OPENAI_BASE_URL=<endpoint-url>/v1` in `providers.yaml`
- Tear down when done to stop billing

Cost estimate for 3 medical models × 700 scenarios:
- ~1 hour per model at ~$1.50/hour average → ~$5 total
- Plus idle time while deploying/downloading weights → budget $15 total

### 3. Local vLLM (no per-query cost, requires GPU)

If the user has access to an 80 GB A100/H100, run vLLM locally:
```bash
vllm serve OpenMeditron/Meditron3-70B --port 8000
```
Then in `providers.yaml`:
```yaml
meditron-70b:
  adapter: llm_openai_compat.py
  env:
    OPENAI_BASE_URL: http://localhost:8000/v1
    VERITASBENCH_MODEL: OpenMeditron/Meditron3-70B
  key_env: OPENAI_API_KEY  # any non-empty value — local vLLM ignores auth
```

vLLM exposes an OpenAI-compatible endpoint — the existing `llm_openai_compat.py` adapter works unchanged.

Plausible for a grad-student-with-lab-GPU setup; infeasible on the user's MacBook.

## When to do this

Not blocking the main benchmark run. Do this as a second pass when:

1. User has Together.ai / HF Inference Endpoint / GPU access **AND**
2. The main 9-model benchmark has shipped + been reviewed **AND**
3. The core thesis ("governance is architecture, not model quality") has already been demonstrated in the main results.

## Deliverables (when unblocked)

- 3-5 medical-model runs in `outputs/llm_<model>/`
- Medical-vs-general comparison table appended to `docs/results-by-model.md`
- Short README section contrasting medical-specialized Policy/Safety with generalist frontier LLMs — expected finding: medical models don't close the Traceability/Controllability gap (it's architectural) and may not even close the Policy/Safety gap (frontier generalists are strong enough).
