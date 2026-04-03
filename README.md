# VeritasBench

**Your AI gets 88% of clinical governance decisions right. It can't prove any of them.**

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

## Benchmark Results (500 scenarios, GPT-4o-mini)

![chart](./docs/benchmark-chart.png)

| Dimension | ClinicClaw | Bare LLM | OpenAI Guardrails | NeMo Guardrails | LangGraph HITL |
|---|---|---|---|---|---|
| Policy Compliance | 417/425 (**98%**) | 373/425 (88%) | 368/425 (87%) | 365/425 (86%) | 292/424 (69%) |
| Safety | 217/225 (**96%**) | 175/225 (78%) | 129/225 (57%) | 135/225 (60%) | 108/225 (48%) |
| Traceability | 1500/1500 (**100%**) | 0/1500 (0%) | 500/1500 (33%) | 0/1500 (0%) | 499/1497 (33%) |
| Controllability | 270/270 (**100%**) | 0/270 (0%) | 0/270 (0%) | 0/270 (0%) | 270/270 (**100%**) |
| Latency p50 | **25ms** | 1157ms | 1122ms | 3889ms | 2458ms |

### How to read this

**Policy compliance is a distraction.** All LLM-based approaches score 86-88% -- the model is already decent at clinical reasoning. Adding guardrails doesn't improve it. The governance gap is in the bottom two rows.

**Traceability is the audit trail.** When a patient is harmed and a lawyer says "show me the documentation," a bare LLM has nothing. OpenAI Guardrails produces trace entries with timestamps but no reasoning (33%). NeMo produces nothing (0%). Only a purpose-built governance system produces complete, structured audit records.

**Controllability is human oversight.** When a high-risk action requires human approval -- controlled substance orders, code status changes, emergency overrides -- the system must halt and wait. LangGraph's interrupt nodes do this (100%). Everything else proceeds without asking (0%).

**No model improvement fixes this.** A hypothetically perfect LLM would score 100% policy compliance and 100% safety. It would still score **0% traceability and 0% controllability**. Governance is an infrastructure problem, not an intelligence problem.

### Methodology

- **Bare LLM, OpenAI Guardrails, NeMo Guardrails, LangGraph HITL**: Real GPT-4o-mini API calls. Every policy decision comes from the actual model, not simulated probabilities. Temperature=0 for reproducibility.
- **ClinicClaw**: Rule-based policy engine. No LLM calls. Its decisions come from hardcoded clinical rules, not a model. This is intentional -- it represents what a purpose-built governance system looks like.
- All adapters are included in `examples/` and can be run directly.

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
# Run your adapter against all 500 scenarios
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
| Policy Compliance  | 340    | 425      | 80%  |
| Safety             | 180    | 225      | 80%  |
| Traceability       | 0      | 1500     | 0%   |  <-- no audit trail
| Controllability    | 0      | 270      | 0%   |  <-- never halts for human review
```

**If your traceability is 0%:** Your system makes decisions but doesn't record why. In a regulated environment, you can't demonstrate compliance, survive a malpractice lawsuit, or pass an accreditation audit.

**If your controllability is 0%:** Your system never pauses for human approval. High-risk actions proceed without a human gate. In healthcare, this means controlled substance orders, code status changes, and emergency overrides happen without physician sign-off.

## 500 Scenarios, 7 Types

| Type | Count | Allow/Deny | What It Tests |
|---|---|---|---|
| Unsafe Action Sequence | 80 | 23/57 | Drug interactions, contraindications, dose errors, safe combinations |
| Unauthorized Access | 75 | 20/55 | RBAC, delegation, credential expiry, consent withdrawal, legitimate access |
| PHI Leakage | 75 | 20/55 | Patient identifiers sent to LLM, de-identified prompts, re-identification risk |
| Emergency Override | 70 | 32/38 | Legitimate clinical emergencies vs abuse of override mechanisms |
| Consent Management | 70 | 32/38 | Patient consent grants, proxy authorization, consent withdrawal, HIPAA |
| Missing Approval | 65 | 16/49 | Human-in-the-loop gates for controlled substances, surgery, code status |
| Missing Justification | 65 | 16/49 | Documented rationale for VIP records, psych notes, substance abuse records |

Each type includes both ALLOW and DENY scenarios (~32% allow overall).

## Included Adapters

### Real adapters (GPT-4o-mini API calls)

| Adapter | What It Is | Requires |
|---|---|---|
| `real_bare_llm.py` | Raw LLM, no governance infrastructure | `OPENAI_API_KEY` |
| `real_openai_guardrails.py` | LLM + input/output content guardrails + trace entries | `OPENAI_API_KEY` |
| `real_nemo_guardrails.py` | LLM + NeMo Guardrails content/topic rails | `OPENAI_API_KEY`, `nemoguardrails` |
| `real_langgraph_hitl.py` | LLM + LangGraph state graph with interrupt nodes | `OPENAI_API_KEY`, `langgraph` |

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

Simulated adapters exist for fast testing without API keys. Their policy compliance scores are illustrative, not measured. Use the real adapters for actual benchmarking.

## CLI Reference

```bash
# Run benchmark
veritasbench run --adapter <path> --suite <name> --output <dir> [--timeout 10000] [--repeats 1] [--retries 0] [--fail-fast]

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
    healthcare_core_v0/      # 500 scenario JSON files
  examples/
    real_*.py                # Real LLM-based adapters (require API key)
    *_simulated.py           # Deterministic simulated adapters
    trivial_*.py             # Baseline adapters
  docs/
    adapter-protocol.md      # Formal adapter specification
    schema/                  # JSON Schema files (generated)
```

## The Governance Gap Is in the AI Layer

Your HIS is already governed. Epic, Cerner, MEDITECH -- 40 years of regulatory compliance baked in. Every access logged, every order signed, every modification timestamped. People sue hospitals constantly, and hospitals survive because the audit trail is already there.

The governance gap isn't in the HIS. It's in the AI agent bolted on top of it. The HIS records that an order was placed. It doesn't record what the AI recommended, what data it accessed, whether a human reviewed its recommendation, or whether its reasoning was clinically sound.

VeritasBench measures that gap. It doesn't prescribe how to fill it.

## You Don't Need a Framework

For many use cases, simple solutions are enough:

| Need | Simple Solution | Effort |
|---|---|---|
| Audit trail | Structured logging around your LLM calls | ~50 lines |
| Human oversight | Approval queue for high-risk actions | ~30 lines |
| PHI detection | Microsoft Presidio (open-source) | `pip install` |
| Policy rules | System prompt + basic if/else rules | ~100 lines |

A full governance framework (VERITAS, custom, or otherwise) earns its cost when you need integration between these pieces, completeness guarantees, tamper-proofing, and regulatory certification. For internal tools, research, or non-clinical agents, start simple.

**VeritasBench tells you where your gaps are. How you fill them is up to you.**

## FAQ

**Why healthcare?** Healthcare has the highest regulatory burden for AI governance -- HIPAA, FDA, Joint Commission all require documented authorization, audit trails, and human oversight. If your governance framework satisfies these requirements, it is well-positioned for other regulated domains.

**Why does the bare LLM score 88% on policy?** GPT-4o-mini is genuinely good at clinical reasoning. That's the point -- the model is not the problem. The problem is that 88% correct decisions with zero documentation is worse than 80% correct decisions with full audit trails. The wrong decisions get caught, investigated, and corrected when you have traceability. Without it, you don't even know which decisions were wrong.

**Is the comparison with ClinicClaw fair?** ClinicClaw is a rule-based policy engine that doesn't use an LLM. The other adapters use GPT-4o-mini. This is intentional. The benchmark compares governance architectures, not models. ClinicClaw represents what a purpose-built system looks like. The LLM-based adapters represent what bolting governance onto an LLM looks like. The gap is architectural.

**Can I use a different model?** Yes. Set `VERITASBENCH_MODEL=gpt-4o` (or any OpenAI model) before running real adapters. Policy compliance will vary by model. Traceability and controllability will not -- those are architecture-dependent.

**Can I add my own scenarios?** Yes. Drop a JSON file in `scenarios/healthcare_core_v0/` following the schema. Run `veritasbench schema` to generate the JSON Schema for reference.

## Limitations

- **Healthcare only (v0).** All 500 scenarios are clinical governance situations. Finance and legal scenarios are planned.
- **Single-step scenarios.** Each scenario is an independent decision. Multi-step workflows, temporal constraints, and cross-scenario patterns are not tested in v0.
- **Binary policy/safety scoring.** No partial credit for close decisions.
- **ClinicClaw rules were designed with knowledge of the scenario types.** Its 98% score reflects a purpose-built system for this specific domain. A real deployment would need to handle scenarios outside the benchmark suite.
- **LLM-based results depend on the model.** GPT-4o-mini was used for all real adapter results. Different models will produce different policy compliance and safety scores. Traceability and controllability scores are model-independent.

## Related Projects

- [ClinicClaw](https://github.com/Chesterguan/cliniclaw) -- AI-native Hospital Information System built on the VERITAS trust model
- [VERITAS](https://github.com/Chesterguan/veritas) -- Trust and governance layer for AI agent systems

## License

Apache-2.0
