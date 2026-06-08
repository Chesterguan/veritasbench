# veritasbench-longitudinal — the temporal axis

VeritasBench-core scores a **single** governance decision on a static scenario
(allow / deny / audit / halt). This crate adds the dimension core's `prior_state` and
`UnsafeActionSequence` only gestured at: a **real generative model**, over a **sequence
of visits** with **persistent, evolving clinical state**, where the model's own orders
carry into the next visit — and an **authoritative clinical oracle** judges whether an
unsafe order actually **reaches the patient over time**. Two arms (governed / ungoverned)
quantify what an external high-alert gate prevents.

It answers a question single-shot scenarios structurally cannot: **does the agent drift
into harm over a long horizon, and does external governance contain it?**

## Why it's a companion, not a duplicate

| | VeritasBench-core | veritasbench-longitudinal |
|---|---|---|
| Subject under test | the **governance layer's decision** (an adapter that decides) | the **model's generative behaviour** + the gate |
| Shape | single-shot, static scenario | persistent, multi-visit, real LLM in the loop |
| Measures | decision correctness + traceability + controllability | **unsafe orders reaching the patient over time** |
| Difficulty | per-scenario tag | a **capability × difficulty** surface |

It **reuses** `veritasbench-core` clinical types — each visit's state is a core
`PriorState` (labs, conditions, allergies, patient context). So it sits under the same
benchmark umbrella and citation, sharing the data model rather than forking it.

## The hidden oracle (the answer key)

Harm is defined by `data/rules/contraindications.json` — **50 rules transcribed from
published authorities** (AGS Beers 2023, STOPP/START v3, FDA labels, KDIGO), **each rule
carrying its citation**. The harm definition is external and authoritative, not the
benchmark author's judgment, and the model **never sees the rules** — it is only asked to
"reconcile." Drop in a fuller rule set (e.g. a downloaded DDInter / RxRisk export) to
expand coverage.

## Adapter protocol (generative)

A longitudinal adapter is a script that reads a **visit chart** on stdin and writes
**medication orders** on stdout — the VeritasBench adapter pattern, generalized from
"decide" to "prescribe":

```
stdin  {"age":74,"sex":"male","conditions":[...],"labs":[{"name":"eGFR","value":25,"unit":"mL/min"}],"current_medications":[...]}
stdout {"orders":[{"drug":"metformin","dose_mg":1000,"frequency":"BID","action":"continue|adjust|hold|start"}]}
```

The reference adapter `adapters/longitudinal/prescriber.py` drives a local Ollama model or
a frontier API (Claude / DeepSeek) chosen by the `LH_MODEL` env var.

## Run it

```bash
cargo build --release -p veritasbench-longitudinal

# local model
cargo run -p veritasbench-longitudinal --bin run_longitudinal -- \
  --adapter "python3 adapters/longitudinal/prescriber.py" \
  --model llama3.2 --suite scenarios/longitudinal_v1 --seeds 3

# frontier ceiling (keys via env)
export ANTHROPIC_API_KEY=...   DEEPSEEK_API_KEY=...
cargo run -p veritasbench-longitudinal --bin run_longitudinal -- \
  --adapter "python3 adapters/longitudinal/prescriber.py" \
  --model claude:claude-opus-4-8 --suite scenarios/longitudinal_v1 --seeds 3
```

Writes `outputs/longitudinal_<model>.json` and prints the gate-off vs gate-on summary.

## Scenarios

`scenarios/longitudinal_v1/` — 10 hard cases (multi-hazard, borderline thresholds,
gate-blind non-high-alert hazards, drug-drug, plus a clean control), each a 12-visit
trajectory whose labs/conditions evolve. **Constructed** (Synthea-style) for now; the
intended upgrade is **real longitudinal trajectories** from the MIMIC-IV→OMOP test bed,
so the cases are real-patient-derived rather than authored.

## First results (`longitudinal_v1`, 10 scenarios × 3 seeds)

Unsafe orders reaching the patient, ungoverned vs governed (high-alert gate):

| Model | Tier | ungoverned | governed | prevented | high-alert held |
|---|---|---:|---:|---:|---:|
| llama3.2 | small local | 264 | 176 | 88 | 6 |
| medgemma:4b | small medical | 75 | 83 | 0 | 2 |
| deepseek-chat | frontier | 48 | 50 | 0 | 14 |
| claude-opus-4-8 | frontier | 66 | 30 | 36 | 6 |

**Reading it honestly:**

- **The capability gradient breaks on hard cases.** Ungoverned counts do *not* rank by
  model strength — claude (66) > deepseek (48), medgemma (75) ≈ claude. The strongest
  model is not the safest here; failures cluster by *case type*, not model rank.
- **The gate's clean value is the high-alert class it governs.** claude's errors
  concentrate in H03 (continuing warfarin through a rising INR — a high-alert drug), so
  the gate holds them and prevents 36. deepseek held 14 high-alert orders (H03+H04) but
  its *other* errors fall on gate-blind hazards (spironolactone, glyburide, diltiazem)
  that land in both arms.
- **For models whose errors are mostly non-high-alert, the net gap is noise.** Because the
  two arms are independent stochastic runs, governed can even exceed ungoverned (medgemma
  83>75, deepseek 50>48). The robust signals are the **held count** and the **per-scenario
  high-alert catches**, not the net — a measurement property of intervening on an LLM whose
  trajectory diverges once you gate it.
- **Clean control (H10) = 0 across all four tiers** — the oracle does not over-flag.

**Cross-validates the originating ClinicClaw engine** (a separate Rust-native implementation):
claude **66→30** here vs **62→24** there, with identical failure structure. Two independent
code paths, same result.

**Bottom line:** the governance gate is *necessary, not sufficient* — it contains the
high-alert class it governs (verifiable, model-independent), while clinical
contraindications on ordinary drugs need a second clinical layer.

## Status & integrity

Early but working end-to-end. The contribution is the **discipline**, not any number:
pre-registered design, oracle hidden from the model, harm defined by external cited
authorities, errors not aimed at the gate, full distribution reported (incl. where the
gate fails and a clean control to catch over-flagging). A result that violates these is a
demo, not evidence.
