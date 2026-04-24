# Security & Robustness Review — 2026-04-24

> Status: Captured 2026-04-24 by code-reviewer agent. 3-round fix-review-test loop completed same day.
> **Outcome: 19 of 23 findings fixed with tests; 4 explicitly deferred.** 111 Rust + 48 Python tests green after fixes.
> Scope: Rust runner + Python adapters + orchestration scripts. Honest-framing + reproducibility integrity included.
> Known issue already tracked separately: `runner-incremental-persistence.md` (final-write data loss).

## Fix status (2026-04-24, post review-loop)

| # | Finding | Status | Fix location |
|---|---|---|---|
| 1 | Unbounded adapter stdout read | **Fixed** | `adapter.rs` — `read_capped` caps pipes at 8 MB, drains remainder |
| 2 | stdin-write outside timeout | **Fixed** | `adapter.rs` — unified `tokio::join!` under one outer `timeout` |
| 3 | Full `os.environ` to adapter subprocess | **Fixed** | `run_model.py` — `_build_scoped_env` + `SYSTEM_ENV_ALLOWLIST` |
| 4 | `normalize_decision` silent coerce to `allow` | **Fixed** | `_llm_shared.py` — raises `InvalidDecisionError`; all 4 adapters updated |
| 5 | Adapter stdout/stderr verbatim in errors | **Fixed** | `adapter.rs` — `sanitize_for_error` truncates + scrubs Bearer/sk-* tokens |
| 6 | p95/p99 off-by-one | **Fixed** | `main.rs` — new `percentile()` nearest-rank impl |
| 7 | providers.yaml SSRF via base_url | **Fixed** | `run_model.py` + `llm_openai_compat.py` — `_validate_base_url` |
| 8 | `filter_map(e.ok())` drops scenarios silently | **Fixed** | `suite.rs` — propagates iteration errors |
| 9 | `--suite` path traversal | **Fixed** | `main.rs` — `is_safe_suite_name` guard |
| 10 | Retries on fatal errors | **Fixed** | `error.rs` — `AdapterFatal` variant; `adapter.rs` — `classify_stderr` |
| 11 | UTF-8 byte-indexing in `capitalize_first` | **Fixed** | `markdown.rs` — char-based impl |
| 12 | `unwrap_or_default` on difficulty | **Fixed** | `aggregate.rs` — exhaustive `match` helper `difficulty_str` |
| 13 | `expect("serialize schema")` | **Fixed** | `main.rs` — explicit `match` with exit |
| 14 | No scenario file size cap | **Fixed** | `suite.rs` — 16 MB cap, `VBError::ScenarioTooLarge` |
| 15 | `exit(1)` on any error_count | **Fixed** | `main.rs` — `exit(2)` for partial success, `exit(1)` for write failure |
| 16 | llm_openai_compat.py no scheme check | **Fixed** | module-load `_validate_base_url` |
| 17 | Classify too-aggressive on bare tokens (iter-2) | **Fixed** | tightened FATAL_MARKERS to SDK exception classes + explicit HTTP phrases |
| 18 | `redact_after_marker` only first occurrence (iter-2) | **Fixed** | `redact_all_after_marker` loops |
| 19 | Bare `sk-*` tokens not scrubbed (iter-2) | **Fixed** | `redact_bare_key_tokens` (UTF-8 safe, word-boundary, min 20-char body) |
| 20 | `VBError::Report` abused for oversize scenario (iter-2) | **Fixed** | new `VBError::ScenarioTooLarge` variant |
| 21 | `_build_scoped_env` raw KeyError (iter-2) | **Fixed** | explicit `ValueError` with clear message |
| 22 | `outputs/` world-readable | **Deferred** — Windows/Unix perm model differs; add README note |
| 23 | Hardcoded `python3` | **Deferred** — design choice, document `VERITASBENCH_PYTHON` for future |
| 24 | Cargo MSRV not declared | **Deferred** — needs actual testing to confirm minimum Rust version |
| 25 | `safety.rs` PHI extraction via `split_whitespace` | **Deferred** — benchmark-only; explicitly out-of-scope |
| 26 | `VERITASBENCH_ADAPTER_PATH` validation | **Accepted risk** — user-controlled env, `examples/` checked first |

## Verification

After each fix round, the full test suite was run:
- Iteration 1 → 107 Rust + 45 Python tests (green)
- Iteration 2 → 111 Rust + 48 Python tests (green)
- Iteration 3 → verified by second independent code-review pass; **"None actionable"**.

New tests added specifically for fixes:
- Rust: `percentile` (5 cases), `is_safe_suite_name` (9 cases), `sanitize_for_error` + `scrub_*` (5 cases including UTF-8), `classify_stderr` fatal/transient (2 multi-assertion), `capitalize_first` UTF-8, adapter fatal-not-retried, adapter parse-is-fatal, adapter large-stdout-no-oom.
- Python: `_validate_base_url` (5 cases incl. IMDS/file/https/loopback), `_build_scoped_env` scoping (2 cases incl. foreign-key drop), `normalize_decision` strict/case/empty/None (5 cases), adapter-level SSRF rejections (3 cases).

---

## Original findings (pre-fix snapshot, kept for history)

## Critical (exploitable or data-loss)

- **`crates/veritasbench-runner/src/adapter.rs:96` — adapter stdout consumed unbounded into memory.** `child.wait_with_output()` buffers the entire stdout pipe before return. A runaway or hostile adapter can OOM the runner (700 scenarios × many MB). Add max-bytes cap or streaming read with limit.

- **`crates/veritasbench-runner/src/adapter.rs:69–76` — stdin-write race on timeout.** `stdin.write_all(...).await` runs before the timeout wrapper on `wait_with_output`. If the adapter never reads stdin (crash, full pipe buffer), `write_all` blocks forever. Wrap stdin-write + wait in a single `tokio::time::timeout`.

- **`scripts/run_model.py:68` + line 63 — every adapter subprocess inherits full `os.environ`.** Third-party adapters silently receive ALL provider keys (OPENROUTER, ANTHROPIC, GEMINI, SILICONFLOW, OPENAI) instead of only the one they need. Scope env to the single key per provider.

## High (likely to bite real users)

- **`crates/veritasbench-runner/src/adapter.rs:98` — adapter stdout verbatim in error message.** Partial API responses, OAuth error bodies, provider debug logs get copied into `VBError::Adapter(...)` and written to console + `outputs/_run_*.log`. Truncate or scrub.

- **`crates/veritasbench-runner/src/adapter.rs:88–93` — adapter stderr surfaced verbatim on non-zero exit.** Same leakage channel. Python SDK tracebacks can include request args. Truncate or scrub bearer-token patterns.

- **`examples/_llm_shared.py:75` — `normalize_decision` silently coerces unknown/None to `"allow"`.** Worst possible default for a safety benchmark. `"DENY"`/`"block"`/`"{}"` all become `allow`, distorting `dangerous_failures` and policy scores. Fail closed (`deny` or error). **This is an integrity-of-published-results issue.**

- **`crates/veritasbench-cli/src/main.rs:245–246` — latency percentile index arithmetic wrong.** `(len as f64 * 0.95) as usize` should be `(len - 1) * 95 / 100`. Off-by-one; p99 for small N collapses to last element. Minor for N=700, distorts smaller runs.

- **`scripts/run_model.py:42` + `scripts/aggregate_models.py:48` — `yaml.safe_load(providers.yaml)` with no URL validation.** A malicious PR changing base_url to `http://169.254.169.254/latest/meta-data/` (cloud metadata) or internal addresses causes SSRF + key leak. Allowlist scheme: `https://` + `http://localhost` only. `VERITASBENCH_ADAPTER_PATH` env (main.rs:477) has the same issue.

- **`crates/veritasbench-runner/src/suite.rs:14–23` — `filter_map(|e| e.ok())` silently drops unreadable scenarios.** 700-file suite silently becomes 699; scored against 700-possible; nobody notices. Propagate or warn.

- **`crates/veritasbench-cli/src/main.rs:140` — `PathBuf::from("scenarios").join(&suite_name)` allows path traversal** via `--suite ../../../etc`. User-vs-self, but contributor manifests pointing absolute/relative outside repo silently work on one machine and not another. Validate path stays under `scenarios/`.

- **`crates/veritasbench-runner/src/adapter.rs:149` — retries on ALL errors, including auth/schema/model-not-found.** 3× the money for scenarios that will never succeed. Classify: retry 5xx/network, don't retry 4xx/parse.

- **`examples/llm_openai_compat.py:108` — worst-case 429 backoff × Rust retries.** Individual 60 s cap × 5 retries × 3 Rust attempts ≈ 3 min per scenario before the Rust timeout short-circuits. Verify stdin-write timeout (above) doesn't stall earlier.

## Medium (defensive improvements)

- **`crates/veritasbench-report/src/markdown.rs:43` — byte-indexing UTF-8 string** with `&tier[1..]`. Panics if difficulty contains multi-byte prefix char (not today).
- **`crates/veritasbench-eval/src/aggregate.rs:115–120` — `unwrap_or_default()` on difficulty→string** silently gives `""` on serialize failure. Unreachable today, but non-obvious.
- **`crates/veritasbench-cli/src/main.rs:366–367` — `.expect("serialize schema")`** violates the "no unwrap in production" rule. Replace with typed error.
- **`crates/veritasbench-runner/src/suite.rs:30` — `std::fs::read_to_string` has no size cap.** 2 GB scenario JSON OOMs the runner. Metadata check before read.
- **`outputs/` files are world-readable (0644)** — scenarios may contain synthetic PHI (or real, if user-authored). Consider 0600 on Unix; add README note.
- **`examples/llm_openai_compat.py:51` — `OpenAI(base_url=BASE_URL)` no scheme check.** `file:///etc/passwd` passed to httpx could yield confusing errors. Enforce `https://` or localhost.
- **`crates/veritasbench-cli/src/main.rs:282` — `exit(1)` on any error_count** even when report was written. Calling scripts treat as total failure. Use distinct code (2) for partial success.
- **`crates/veritasbench-runner/src/adapter.rs:61` — hardcoded `"python3"`.** Fails on Windows; picks Py2 on some macOS configs. Respect `VERITASBENCH_PYTHON` env.
- **`examples/llm_bare.py:47` — `json.loads(...)` no try/except.** Empty content crashes adapter. Intentional (non-zero exit → Rust counts as failure), but document the pattern vs. the silent-coerce pattern in `_llm_shared.py`.

## Low / nitpick

- **`crates/veritasbench-cli/src/main.rs:463`** uses `is_none_or` (Rust 1.82+). No MSRV declared in `Cargo.toml`.
- **`Cargo.toml`** — missing `rust-version` field.
- **`scripts/run_model.py:89`** — subprocess return code propagated but compile errors aren't distinguished from runtime errors.
- **`crates/veritasbench-eval/src/safety.rs:43`** — PHI extraction via `split_whitespace()` misses `"Mr.Doe"` / Unicode spaces. Low risk (benchmark, not runtime filter).

## Out of scope / false alarms checked

- **Shell injection** — no `shell=True`, no string-interpolated commands. `subprocess.call(list, ...)` and Rust `Command::new().arg()` are all safe. Clean.
- **Path traversal via scenario `id` → filename** — only `report.json`/`report.md` written today. When v1.3 incremental persistence lands, sanitize `id` (current `^[A-Z]{2}-\d{3}$` regex already holds).
- **Concurrency** — runner iterates scenarios serially inside async; no shared mutable state across tasks. Clean.
- **`unwrap`/`expect` audit (non-test paths)** — only 4 hits, 3 acceptable (compile-time schemas, structurally unreachable), 1 flagged above (schema_command).
- **Supply chain** — Cargo.lock has 82 standard crates; no unusual deps. Python side pulls only first-party SDKs.
- **Key leakage in existing `outputs/_run_*.log`** — grep for `sk-`, `sk_or`, `Bearer` clean.

## Top 3 to fix before v1.3 ships

1. **Scope per-provider env vars** (`run_model.py`) — adapter-ecosystem safety.
2. **Fix `normalize_decision` + adapter-stdout-on-error leak** — honesty of published numbers + user key safety.
3. **Wrap stdin-write+wait in one timeout, cap adapter stdout size** — one bad provider currently can stall or OOM the whole run.

## Files reviewed

- `crates/veritasbench-runner/src/{adapter,suite}.rs`
- `crates/veritasbench-cli/src/main.rs`
- `crates/veritasbench-core/src/{scenario,result,score,error}.rs`
- `crates/veritasbench-eval/src/{aggregate,policy,safety,traceability,controllability,consistency}.rs`
- `crates/veritasbench-report/src/{json,markdown}.rs`
- `scripts/{run_model,aggregate_models,llm_judge_validate,recalculate_difficulty,generate_system_scenarios,assign_difficulty}.py`
- `examples/{_llm_shared,llm_openai_compat,llm_bare,llm_anthropic,llm_gemini,llm_with_hitl_prompt,llm_with_topic_rails,llm_with_content_filter,_test_adapters}.py`
- `examples/providers.yaml`
- `{.env.example,.gitignore,Cargo.toml,Cargo.lock}`
