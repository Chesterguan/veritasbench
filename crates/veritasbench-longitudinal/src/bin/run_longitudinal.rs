//! CLI: run a generative adapter against a longitudinal scenario suite.
//!
//! Example:
//!   cargo run -p veritasbench-longitudinal --bin run_longitudinal -- \
//!     --adapter "python3 adapters/longitudinal/prescriber.py" \
//!     --model llama3.2 --suite scenarios/longitudinal_v1 --seeds 3

use std::path::PathBuf;

use clap::Parser;
use veritasbench_longitudinal::{runner, LongitudinalScenario};

#[derive(Parser)]
#[command(about = "VeritasBench longitudinal (temporal) governance runner")]
struct Args {
    /// Adapter command: a script reading a visit chart on stdin, writing orders JSON on stdout.
    #[arg(long)]
    adapter: String,
    /// Model id passed to the adapter via LH_MODEL (e.g. llama3.2 | claude:claude-opus-4-8 | deepseek:deepseek-chat).
    #[arg(long)]
    model: String,
    /// Directory of *.json longitudinal scenarios.
    #[arg(long)]
    suite: PathBuf,
    /// Repetitions per scenario (the model is stochastic).
    #[arg(long, default_value_t = 3)]
    seeds: usize,
    /// Where to write the SuiteResult JSON (default: outputs/longitudinal_<model>.json).
    #[arg(long)]
    output: Option<PathBuf>,
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = Args::parse();

    let mut scenarios: Vec<LongitudinalScenario> = Vec::new();
    for entry in std::fs::read_dir(&args.suite)? {
        let path = entry?.path();
        if path.extension().and_then(|e| e.to_str()) == Some("json") {
            let sc: LongitudinalScenario = serde_json::from_str(&std::fs::read_to_string(&path)?)
                .map_err(|e| format!("{}: {e}", path.display()))?;
            scenarios.push(sc);
        }
    }
    scenarios.sort_by(|a, b| a.id.cmp(&b.id));
    if scenarios.is_empty() {
        return Err(format!("no scenarios found in {}", args.suite.display()).into());
    }

    eprintln!("running {} scenarios × {} seeds × 2 arms via `{}` (model={})",
              scenarios.len(), args.seeds, args.adapter, args.model);
    let result = runner::run_suite(&scenarios, &args.adapter, &args.model, args.seeds);

    for s in &result.per_scenario {
        eprintln!("  {:28} gate-off {:>3} -> gate-on {:>3}", s.id, s.gate_off_unsafe, s.gate_on_unsafe);
    }

    let out = args.output.unwrap_or_else(|| {
        let safe = args.model.replace([':', '/'], "_");
        PathBuf::from(format!("outputs/longitudinal_{safe}.json"))
    });
    if let Some(parent) = out.parent() { std::fs::create_dir_all(parent)?; }
    std::fs::write(&out, serde_json::to_string_pretty(&result)?)?;

    println!(
        "RESULT model={} scenarios={} seeds={} | GATE-OFF unsafe={} -> GATE-ON unsafe={} | prevented={} | high-alert held={} | parse_fail={} -> {}",
        result.model, result.scenarios, result.seeds,
        result.gate_off_unsafe, result.gate_on_unsafe, result.veritas_prevented,
        result.high_alert_held, result.parse_fail, out.display(),
    );
    Ok(())
}
