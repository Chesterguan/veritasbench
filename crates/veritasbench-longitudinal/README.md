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

## What the first runs found (ClinicClaw, the originating system)

Judged by this oracle across model tiers: a clean capability staircase on *textbook*
hazards (small-local 24% → frontier 0%), but on these *hard* cases **even the frontier
model cracks** and the gradient breaks — the external high-alert gate catches the
governance-relevant subset (e.g. a frontier model continuing warfarin through a rising
INR), while non-high-alert clinical contraindications land in both arms (necessary, not
sufficient — you need a clinical layer too).

## Status & integrity

Early but working end-to-end. The contribution is the **discipline**, not any number:
pre-registered design, oracle hidden from the model, harm defined by external cited
authorities, errors not aimed at the gate, full distribution reported (incl. where the
gate fails and a clean control to catch over-flagging). A result that violates these is a
demo, not evidence.
