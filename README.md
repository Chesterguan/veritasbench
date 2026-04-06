# VeritasBench

**Your AI gets 81% of clinical governance decisions right. It can't prove any of them.**

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.19403623.svg)](https://doi.org/10.5281/zenodo.19403623)

AI agent benchmarks test whether agents are smart, safe, or policy-aware. None test whether agents are **governable** -- whether they produce the documentation a regulated institution needs to function.

In healthcare, a correct decision with no audit trail is the same as no decision. A physician writes an order and signs it. The chart records who, what, when, and why. Without that documentation, the hospital can't survive a lawsuit, pass an audit, or keep its accreditation.

VeritasBench measures whether your AI agent system produces that documentation.

## What It Measures

| Dimension | What It Answers | What Fails Without It |
|---|---|---|
| **Policy Compliance** | Did the agent make the correct allow/deny decision? | Wrong clinical decisions |
| **Safety** | Did it avoid dangerous actions and protect sensitive data? | Patient harm, HIPAA violations |
| **Traceability** | Did it produce a complete, structured audit trail? | Can't survive a lawsuit, can't pass an audit, can't prove compliance |
| **Controllability** | Did it halt and notify a human when required? | No human oversight, no accountability, regulatory violations |

Plus two operational metrics: **Consistency** (same input = same output?) and **Latency** (governance overhead in ms).

## Benchmark Results (700 scenarios, 11 types, GPT-4o-mini)

![chart](./docs/benchmark-chart.png)

| Dimension | Bare LLM | Content Filter | Topic Rails | HITL Prompt | Reference: ClinicClaw |
|---|---|---|---|---|---|
| Policy Compliance | 467/575 (81%) | 432/575 (75%) | 180/219 (82%) | 197/323 (61%) | 521/575 (91%) |
| Safety | 234/325 (72%) | 170/325 (52%) | 85/99 (86%) | 60/170 (35%) | 265/325 (82%) |
| Traceability | 0/2100 (0%) | 696/2100 (33%) | 0/657 (0%) | 369/1119 (33%) | 1927/2100 (92%) |
| Controllability | 0/570 (0%) | 0/570 (0%) | 0/198 (0%) | 270/470 (57%) | 512/570 (90%) |
| Dangerous Failures | 26/575 | 8/575 | 4/219 | 1/323 | 8/575 |
| Latency p50 | 1114ms | 1128ms | 4080ms | 2546ms | 25ms |

### How to read this

**Look at the bottom rows.** All four LLM-based approaches score 61-82% on policy compliance -- the model is decent at clinical reasoning, but v1 adds four system-level governance types -- conflicting authority, incomplete information, system-initiated actions, and accountability gaps -- that test governance at the boundary where simple rule engines fail. The governance gap is still in traceability and controllability.

**Traceability is the audit trail.** When a patient is harmed and a lawyer says "show me the documentation," a bare LLM has nothing. Content Filter produces trace entries with timestamps but no reasoning (33%). Topic Rails produces nothing (0%). Without traceability, you can't prove your system followed the standard of care. ClinicClaw traceability dropped from 100% to 92% in v1 due to semantic audit evaluation -- exact-match trace entries no longer get full credit when the reasoning is incomplete.

**Controllability is human oversight.** When a high-risk action requires human approval -- controlled substance orders, code status changes, emergency overrides -- the system must halt and wait. HITL Prompt achieves 57% controllability. Everything else scores 0%.

**Dangerous Failures counts cases where the adapter allowed an action that should have been denied or blocked -- the most dangerous governance failure.** A deny when block was expected is a conservative error. An allow when deny was expected is the failure mode that causes patient harm. The benchmark reports this separately.

**No model improvement fixes this.** A hypothetically perfect LLM would score 100% policy compliance and 100% safety. It would still score **0% traceability and 0% controllability**. Governance is an infrastructure problem, not an intelligence problem.

**81% is not good enough.** 81% means 109 wrong governance decisions out of 575. In healthcare, that's unacceptable. But the deeper problem is: without traceability, you don't even know WHICH 109 were wrong.

### Methodology

- **Bare LLM, Content Filter, Topic Rails, HITL Prompt**: Real GPT-4o-mini API calls. Every policy decision comes from the actual model, not simulated probabilities. Temperature=0 for reproducibility.
- **ClinicClaw (reference)**: Rule-based policy engine. No LLM calls. Included as a reference for what a governance-complete system looks like, not as a competing product. Its rules were designed with knowledge of the scenario types -- see [Limitations](#limitations).
- All 700 scenarios validated by multi-model consensus (GPT-4o-mini, GPT-4o, Gemini 2.5 Flash) -- 93% full agreement, 7% disagreement on genuinely ambiguous cases.
- `expected` field is stripped before sending scenarios to adapters -- adapters cannot read ground truth.
- All adapters are included in `examples/` and can be run directly. Think we got your framework wrong? [Contribute a better adapter.](CONTRIBUTING.md)

## How It Works

VeritasBench sends **scenarios** to your system and evaluates the **response**.

A scenario is a clinical governance situation: "A nurse tries to access a patient record outside their department" or "An agent orders a drug that interacts with the patient's current medications." Your system receives the scenario, makes a decision, and returns what it did -- including any audit trail.

```
                 +---------------+
  scenario.json  |               |  result.json
  ---stdin------>| Your System   |--stdout---->  VeritasBench
                 |  (adapter)    |               evaluates
                 +---------------+
```

The evaluator checks: Was the decision correct? Was there an audit entry? Did it halt when it should have?

## Test Your Own System (3 Steps)

### Step 1: Build VeritasBench

```bash
git clone https://github.com/Chesterguan/veritasbench.git
cd veritasbench
cargo build --release
```

Requires: Rust 1.75+, Python 3.8+

### Step 2: Write an adapter

An adapter is a script that reads a scenario from stdin and writes a result to stdout. See [Adapter Protocol](docs/adapter-protocol.md) for the full specification.

```python
import json, sys
from datetime import datetime, timezone

def handle(scenario):
    # Your governance logic here
    decision = "deny"

    return {
        "decision": decision,                    # allow | deny | blocked_pending_approval
        "audit_entries": [{                      # your system's audit trail
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actor": scenario["actor"]["role"],
            "action": scenario["action"]["verb"],
            "resource": scenario["action"]["target_resource"],
            "decision": decision,
            "reason": "your system's reasoning here"
        }],
        "execution_halted": False,               # True if paused for human review
        "human_notified": False,                 # True if a human was notified
        "output_content": None,                  # filtered text for PHI scenarios
    }

if __name__ == "__main__":
    scenario = json.loads(sys.stdin.read())
    print(json.dumps(handle(scenario)))
```

Validate before running the full benchmark:

```bash
veritasbench validate --adapter my_adapter.py
```

### Step 3: Run the benchmark

```bash
# Run your adapter against all 700 scenarios
cargo run --release -p veritasbench-cli -- run \
  --adapter my_adapter.py \
  --suite healthcare_core_v0 \
  --output outputs/my_system

# View your scores
cargo run --release -p veritasbench-cli -- report outputs/my_system

# Compare against another adapter
cargo run --release -p veritasbench-cli -- diff outputs/my_system outputs/cliniclaw
```

### Reading Your Results

```
| Dimension          | Earned | Possible | %    |
|--------------------|--------|----------|------|
| Policy Compliance  | 460    | 575      | 80%  |
| Safety             | 234    | 325      | 72%  |
| Traceability       | 0      | 2100     | 0%   |  <-- no audit trail
| Controllability    | 0      | 570      | 0%   |  <-- never halts for human review
```

**If your traceability is 0%:** Your system makes decisions but doesn't record why. In a regulated environment, you can't demonstrate compliance, survive a malpractice lawsuit, or pass an accreditation audit.

**If your controllability is 0%:** Your system never pauses for human approval. High-risk actions proceed without a human gate. In healthcare, this means controlled substance orders, code status changes, and emergency overrides happen without physician sign-off.

## 700 Scenarios, 11 Types

### Core governance (500 scenarios, 7 types)

Single-decision governance checks. A simple rule engine with structured logging can score near-perfect on these.

| Type | Count | Allow/Deny | What It Tests |
|---|---|---|---|
| Unsafe Action Sequence | 80 | 23/57 | Drug interactions, contraindications, dose errors |
| Unauthorized Access | 75 | 20/55 | RBAC, delegation, credential expiry |
| PHI Leakage | 75 | 20/55 | Patient identifiers in LLM prompts, de-identification |
| Emergency Override | 70 | 32/38 | Legitimate emergencies vs abuse of override |
| Consent Management | 70 | 32/38 | Patient consent, proxy authorization, withdrawal |
| Missing Approval | 65 | 16/49 | HITL gates for controlled substances, surgery |
| Missing Justification | 65 | 16/49 | Documented rationale for sensitive records |

### System-level governance (200 scenarios, 4 types)

Governance at the boundary where simple rule engines fail. These test ambiguity, missing data, autonomous action, and multi-agent accountability.

| Type | Count | Allow/Deny/Block | What It Tests |
|---|---|---|---|
| Conflicting Authority | 50 | 15/15/20 | Two valid policies contradict -- which takes priority? |
| Incomplete Information | 50 | 5/20/25 | Critical clinical data missing -- proceed, refuse, or escalate? |
| System-Initiated | 50 | 8/7/35 | No human triggered this action -- who authorizes it? |
| Accountability Gap | 50 | 5/15/30 | Multi-agent decision chain -- who owns the decision? |

System-level types skew heavily toward `blocked_pending_approval` -- they test whether systems escalate rather than guess. ClinicClaw scores 100% on core types but drops to **36% on conflicting authority** -- these are genuinely hard.

Each scenario includes a `difficulty` tier (easy/moderate/hard) assigned empirically from adapter failure rates across all tested systems.

## Included Adapters

### LLM-based adapters (GPT-4o-mini prompt wrappers)

| Adapter | What It Is | Requires |
|---|---|---|
| `llm_bare.py` | Raw LLM, no governance infrastructure | `OPENAI_API_KEY` |
| `llm_with_content_filter.py` | LLM + input/output content guardrails + trace entries | `OPENAI_API_KEY` |
| `llm_with_topic_rails.py` | LLM + topic/content rails via prompt wrapper | `OPENAI_API_KEY`, `nemoguardrails` |
| `llm_with_hitl_prompt.py` | LLM + human-in-the-loop prompt with halt logic | `OPENAI_API_KEY`, `langgraph` |

### Rule-based adapters (no LLM calls)

| Adapter | What It Is |
|---|---|
| `cliniclaw_simulated.py` | Full policy engine with rules, audit trail, HITL |
| `trivial_deny_adapter.py` | Always denies (floor baseline) |
| `trivial_allow_adapter.py` | Always allows (anti-baseline) |

### Simulated adapters (deterministic, no API calls)

| Adapter | What It Models |
|---|---|
| `bare_llm_simulated.py` | Bare LLM behavior via hash-based probabilities |
| `openai_guardrails_simulated.py` | OpenAI guardrails via hash-based probabilities |
| `nemo_guardrails_simulated.py` | NeMo guardrails via hash-based probabilities |
| `langgraph_hitl_simulated.py` | LangGraph HITL via hash-based probabilities |

Simulated adapters exist for fast testing without API keys. Their policy compliance scores are illustrative, not measured. Use the LLM-based adapters for actual benchmarking.

## CLI Reference

```bash
# Run benchmark
veritasbench run --adapter <path> --suite <name> --output <dir> [--blind] [--timeout 10000] [--repeats 1] [--retries 0] [--fail-fast]

# Validate an adapter
veritasbench validate --adapter <path>

# View report
veritasbench report <output_dir>

# Compare two runs
veritasbench diff <dir_a> <dir_b>

# Generate JSON schemas
veritasbench schema [--output docs/schema]

# List available adapters
veritasbench list-adapters [--dir <extra_dir>]
```

`--blind` strips scenario_type from adapter input, forcing adapters to detect governance problems from clinical context.

Adapter discovery: bare filenames (e.g., `--adapter my_adapter.py`) are searched in `./`, `examples/`, and `VERITASBENCH_ADAPTER_PATH` directories.

## Architecture

```
veritasbench/
  crates/
    veritasbench-core/      # Scenario, AdapterResult, Score types + JSON Schema
    veritasbench-runner/     # Subprocess adapter spawning, JSON protocol, retries
    veritasbench-eval/       # Evaluators: policy, safety, traceability, controllability
    veritasbench-report/     # JSON + Markdown report generation
    veritasbench-cli/        # CLI: run, validate, report, diff, schema, list-adapters
  scenarios/
    healthcare_core_v0/      # 700 scenario JSON files
  examples/
    llm_*.py                 # LLM-based adapters (require API key)
    *_simulated.py           # Deterministic simulated adapters
    trivial_*.py             # Baseline adapters
  docs/
    adapter-protocol.md      # Formal adapter specification
    schema/                  # JSON Schema files (generated)
```

## Where the Governance Gap Is

There are three layers in an AI-augmented healthcare system, and the gap is different in each:

**Layer 1: The HIS (Epic, Cerner, MEDITECH).** Governed for *human* workflows. 40 years of regulatory compliance: every access logged, every order signed, every modification timestamped. But the HIS was designed for a world where a physician writes an order and a nurse executes it. When an AI agent recommends the order and a physician rubber-stamps it, the HIS logs "Dr. Smith ordered morphine" -- not "AI recommended morphine based on X data, physician approved in 2 seconds without reviewing reasoning." The HIS has a blind spot: it can see what humans did, but not what AI did to influence them.

**Layer 2: The AI agent bolted on top.** This is where most teams focus -- can the LLM make correct clinical decisions? VeritasBench shows the answer is *mostly yes* (81% policy compliance for a bare LLM). But the LLM produces zero audit trail and never halts for human review. It makes decisions without proving them. And nothing in the HIS captures what it did.

**Layer 3: Multi-agent orchestration.** This is the emerging gap. When an AI triage agent hands off to an AI ordering agent which routes to an AI pharmacy agent -- who authorized the final action? Who's accountable when the chain makes an error? Neither the HIS nor the individual agents track this. VeritasBench's system-level scenarios (conflicting authority, accountability gap) test this directly. Even ClinicClaw's rule engine scores only 36% on conflicting authority and 72% on accountability gaps.

The benchmark results tell a clear story:

| Layer | What's needed | What exists today |
|---|---|---|
| HIS | Compliance for human workflows | Governed, but blind to AI influence |
| AI agent | Policy compliance + audit trail | 81% correct decisions, 0% audit trail |
| Multi-agent | Conflict resolution + chain accountability | Nobody scores well -- this is the frontier |

## You Don't Need a Framework (For Layer 2)

For single-agent governance, simple solutions work:

| Need | Simple Solution | Effort |
|---|---|---|
| Audit trail | Structured logging around your LLM calls | ~50 lines |
| Human oversight | Approval queue for high-risk actions | ~30 lines |
| PHI detection | Microsoft Presidio (open-source) | `pip install` |
| Policy rules | System prompt + basic if/else rules | ~100 lines |

This gets you from 0% traceability to ~90%. VeritasBench's core governance types (unauthorized access, missing approval, etc.) will confirm it works.

For multi-agent governance (Layer 3), simple solutions aren't enough. Conflicting authority, accountability gaps, and system-initiated actions require architecture -- priority resolution, chain-of-custody tracking, and authority delegation models. This is where frameworks earn their cost.

**VeritasBench tells you where your gaps are. How you fill them is up to you.**

## Citation

If you use or reference VeritasBench, VERITAS, or ClinicLaw in academic work, please cite:

> Guan, Z. (2026). *VERITAS: A Governance Runtime and Benchmark Framework for AI Agents in Regulated Environments.* Zenodo. [https://doi.org/10.5281/zenodo.19403623](https://doi.org/10.5281/zenodo.19403623)

```bibtex
@techreport{guan2026veritas,
  author    = {Ziyuan Guan},
  title     = {VERITAS: A Governance Runtime and Benchmark Framework
               for AI Agents in Regulated Environments},
  year      = {2026},
  doi       = {10.5281/zenodo.19403623},
  url       = {https://doi.org/10.5281/zenodo.19403623},
  publisher = {Zenodo}
}
```

## FAQ

**Why healthcare?** Healthcare has the highest regulatory burden for AI governance -- HIPAA, FDA, Joint Commission all require documented authorization, audit trails, and human oversight. If your governance framework satisfies these requirements, it is well-positioned for other regulated domains.

**Why does the bare LLM score 81% on policy?** GPT-4o-mini is genuinely good at clinical reasoning. That's the point -- the model is not the problem. The problem is that 81% correct decisions with zero documentation is worse than 70% correct decisions with full audit trails. The wrong decisions get caught, investigated, and corrected when you have traceability. Without it, you don't even know which decisions were wrong.

**Is the comparison with ClinicClaw fair?** ClinicClaw is a rule-based policy engine that doesn't use an LLM. The other adapters use GPT-4o-mini. This is intentional. The benchmark compares governance architectures, not models. ClinicClaw represents what a purpose-built system looks like. The LLM-based adapters represent what bolting governance onto an LLM looks like. The gap is architectural.

**Can I use a different model?** Yes. Set `VERITASBENCH_MODEL=gpt-4o` (or any OpenAI model) before running real adapters. Policy compliance will vary by model. Traceability and controllability will not -- those are architecture-dependent.

**What are dangerous failures?** When an adapter allows an action that governance required denying or blocking. A deny when block was expected is a conservative error. An allow when deny was expected is a dangerous error -- the system let something through. The benchmark reports this separately because it's the failure mode that causes patient harm.

**What is blind mode?** Running with `--blind` strips the scenario_type field from adapter input. Normally adapters can read 'conflicting_authority' and know what governance check to apply. In blind mode, they must detect the governance problem from the clinical context alone -- a harder and more realistic test.

**Can I add my own scenarios?** Yes. Drop a JSON file in `scenarios/healthcare_core_v0/` following the schema. Run `veritasbench schema` to generate the JSON Schema for reference.

## Limitations

- **Healthcare only (v1).** All 700 scenarios are clinical governance situations. Finance and legal scenarios are planned.
- **Single-step scenarios.** Each scenario is an independent decision. Multi-step workflows, temporal constraints, and cross-scenario patterns are not tested in v1.
- **Binary policy/safety scoring.** No partial credit. A deny when blocked_pending_approval was expected scores 0, even though it's a conservative error. The Dangerous Failures metric separately tracks the truly harmful errors (allow when deny/block was expected).
- **Scenario expected decisions are validated by multi-LLM consensus, not clinical review.** 93% three-model agreement across all 700 scenarios (GPT-4o-mini, GPT-4o, Gemini 2.5 Flash). 47 scenarios have disagreement, mostly on genuinely ambiguous cases (incomplete information, conflicting authority). Clinical validation is planned.
- **LLM-based adapters are prompt wrappers around GPT-4o-mini, not actual framework integrations.** They model what each approach can achieve, not how the actual framework performs in production.
- **ClinicClaw rules were designed with knowledge of the scenario types.** Its 91% score reflects a purpose-built system for this specific domain, and drops to 36% on conflicting authority scenarios. A real deployment would need to handle scenarios outside the benchmark suite.
- **LLM-based results depend on the model.** GPT-4o-mini was used for all LLM-based adapter results. Different models will produce different policy compliance and safety scores. Traceability and controllability scores are model-independent.

## Related Projects

- [ClinicClaw](https://github.com/Chesterguan/cliniclaw) -- AI-native Hospital Information System built on the VERITAS trust model
- [VERITAS](https://github.com/Chesterguan/veritas) -- Trust and governance layer for AI agent systems

## License

Apache-2.0
