# Runner — Incremental Persistence (NDJSON Append Log)

> Status: Captured 2026-04-24 after the DeepSeek-R1 run lost 324 scored scenarios to a mid-run EPERM.
> Severity: data-integrity bug for any long-running benchmark. Not a security issue.
> Scope: v1.3. ~50 lines of Rust.

## What happened (2026-04-24)

The DeepSeek-R1 run scored 324 scenarios successfully over ~80 minutes, then the runner hit `[Errno 1] Operation not permitted` on the adapter file mid-run (likely macOS TCC revocation on the external `/Volumes/extraSupply` APFS volume). 326 subsequent scenarios all errored on the same path.

At end of run, `write_json_report` also hit EPERM when serializing `report.json`. Because the runner accumulates **all** per-scenario results in memory and only persists them as part of that single final write, **every one of the 324 successfully-scored scenarios was discarded** along with the failed ones. No `outputs/llm_deepseek_r1/` directory was ever created.

## Root cause (in code)

`crates/veritasbench-cli/src/main.rs:250-273`:

```rust
// all_scores is a Vec<ScenarioScore> built during the 700-scenario loop
let report = BenchmarkReport { ..., per_scenario: all_scores };
let json_path = output_dir.join("report.json");
if let Err(e) = write_json_report(&report, &json_path) {
    eprintln!("error: failed to write JSON report: {e}");
    std::process::exit(1);
}
```

One write, at the end, all-or-nothing. No checkpointing, no append log, no fsync.

This is safe when:
- Runs finish in 10-30 min (non-reasoning models), and
- The output path is on local disk where TCC / removable-volume TCC can't rescind permission mid-write.

Neither assumption holds for reasoning models on external APFS volumes.

## Proposed fix

### 1. NDJSON append log per scenario (primary)

Open `<output_dir>/scenarios.ndjson` in append mode before the scoring loop starts. After each scenario scores, write one JSON line and (optionally) fsync:

```rust
use std::io::Write;
let mut log = std::fs::OpenOptions::new()
    .create(true).append(true)
    .open(output_dir.join("scenarios.ndjson"))?;

for scenario in scenarios {
    let result = run_and_score(scenario, ...).await?;
    all_scores.push(result.clone());
    writeln!(log, "{}", serde_json::to_string(&result)?)?;
    log.flush()?; // optional fsync on strict durability setups
}
```

Append-only writes survive mid-run crashes: all completed lines are already on disk before the next scenario starts. An NDJSON stream is trivially parseable (`jq -s .` or line-by-line).

### 2. Raw adapter output per scenario (secondary, for dangerous_failures recovery)

The R1 log preserved `policy=0/1 safety=0/1 trace=N/3 ctrl=0/1` for each scored scenario but **not the raw decision** (`"allow"` / `"deny"` / `"blocked_pending_approval"`). That gap is what made the 324 scenarios unrecoverable for `dangerous_failures` even from the stdout log — `policy=0` doesn't tell you which direction the model went wrong.

Include `adapter_raw_output` in the NDJSON record. Or, if size is a concern, include just the parsed `decision` field.

### 3. `veritasbench recover <output_dir>` subcommand

New subcommand reads `scenarios.ndjson` and rebuilds `report.json` + `report.md` offline. Turns the final report write from a hard failure point into a derivable artifact. Sketch:

```rust
let scores: Vec<ScenarioScore> = BufReader::new(File::open(log_path)?)
    .lines()
    .filter_map(|l| l.ok())
    .filter_map(|l| serde_json::from_str(&l).ok())
    .collect();
// ... aggregate same way the live runner does, then write report.json
```

This also covers the case where the user kills a run midway (Ctrl-C after 400 scenarios) — partial reports become trivial to generate.

### 4. Write `report.json` atomically (nice-to-have)

Current `write_json_report` in `crates/veritasbench-report/src/json.rs:17` is a plain `std::fs::write`. If that call is interrupted (signal, EPERM, power loss), the file can be partially written and corrupt. Standard pattern:

```rust
// write to report.json.tmp, fsync, rename over report.json
let tmp = path.with_extension("json.tmp");
std::fs::write(&tmp, &json)?;
File::open(&tmp)?.sync_all()?;
std::fs::rename(tmp, path)?;
```

## Scope

- ~20 lines for (1), ~10 for (2), ~20 for (3), ~5 for (4). Total under 100.
- No new dependencies. `serde_json` and `std::io::Write` are already in use.
- Add a regression test: kill the runner after 50 scenarios via signal, then run `recover` and assert report matches a reference.

## Not in scope

- Streaming aggregation (keeping running means/variances per-scenario to avoid the final `Vec` materialization). Memory is not the bottleneck here — durability is.
- Distributed / sharded runs. Local-disk NDJSON is enough.

## Acceptance criteria

- After a mid-run SIGINT at scenario 400, `ls <output_dir>` shows `scenarios.ndjson` with exactly 400 lines.
- `veritasbench recover <output_dir>` produces a `report.json` whose scores match the first-400-scenarios subset of a clean full run.
- No change in behavior for completed runs (the final `report.json` is still produced the same way).
