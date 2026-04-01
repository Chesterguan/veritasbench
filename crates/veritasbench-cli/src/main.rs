use std::path::PathBuf;

use clap::{Parser, Subcommand};
use veritasbench_core::score::{BenchmarkReport, LatencyStats};
use veritasbench_eval::aggregate::{aggregate_scores, evaluate_scenario};
use veritasbench_eval::consistency::eval_consistency;
use veritasbench_report::json::write_json_report;
use veritasbench_report::markdown::{generate_markdown, write_markdown_report};
use veritasbench_runner::adapter::run_adapter;
use veritasbench_runner::suite::load_suite;

#[derive(Parser)]
#[command(name = "veritasbench", about = "Benchmark AI agent governance properties")]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Run a benchmark suite against an adapter
    Run {
        /// Path to the adapter script
        #[arg(long)]
        adapter: PathBuf,

        /// Suite name (resolved as scenarios/{suite})
        #[arg(long)]
        suite: String,

        /// Output directory for report files
        #[arg(long)]
        output: PathBuf,

        /// Number of repeat runs (for consistency scoring)
        #[arg(long, default_value_t = 1)]
        repeats: u32,

        /// Adapter timeout in milliseconds
        #[arg(long, default_value_t = 10_000)]
        timeout: u64,
    },

    /// Print a markdown report from a saved output directory
    Report {
        /// Path to the output directory containing report.json
        path: PathBuf,
    },

    /// Compare two report directories side by side
    Diff {
        /// First report directory
        a: PathBuf,
        /// Second report directory
        b: PathBuf,
    },
}

#[tokio::main]
async fn main() {
    let cli = Cli::parse();

    match cli.command {
        Commands::Run { adapter, suite, output, repeats, timeout } => {
            run_command(adapter, suite, output, repeats, timeout).await;
        }
        Commands::Report { path } => {
            report_command(path);
        }
        Commands::Diff { a, b } => {
            diff_command(a, b);
        }
    }
}

async fn run_command(
    adapter_path: PathBuf,
    suite_name: String,
    output_dir: PathBuf,
    repeats: u32,
    timeout_ms: u64,
) {
    // Resolve suite directory relative to cwd
    let suite_dir = PathBuf::from("scenarios").join(&suite_name);

    let scenarios = match load_suite(&suite_dir) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("error: failed to load suite '{}': {}", suite_name, e);
            std::process::exit(1);
        }
    };

    if scenarios.is_empty() {
        eprintln!("error: suite '{}' contains no scenarios", suite_name);
        std::process::exit(1);
    }

    println!("Running {} scenarios x {} repeats", scenarios.len(), repeats);

    // runs[repeat_index] = vec of decisions per scenario (for consistency)
    let mut all_runs: Vec<Vec<veritasbench_core::scenario::Decision>> = Vec::new();
    let mut all_scores = Vec::new();
    let mut all_latencies: Vec<u64> = Vec::new();

    for repeat in 0..repeats {
        if repeats > 1 {
            println!("--- Repeat {} ---", repeat + 1);
        }

        let mut run_decisions = Vec::new();

        for scenario in &scenarios {
            let run_result = match run_adapter(&adapter_path, scenario, timeout_ms).await {
                Ok(r) => r,
                Err(e) => {
                    eprintln!("  {} ... ERROR: {}", scenario.id, e);
                    std::process::exit(1);
                }
            };

            let score =
                evaluate_scenario(scenario, &run_result.result, run_result.latency_ms);

            // Format per-scenario output line
            let pol = score.policy_compliance.map(|v| v.to_string()).unwrap_or_else(|| "-".into());
            let saf = score.safety.map(|v| v.to_string()).unwrap_or_else(|| "-".into());
            let tra = score
                .traceability
                .map(|v| format!("{}/3", v))
                .unwrap_or_else(|| "-".into());
            let ctrl =
                score.controllability.map(|v| v.to_string()).unwrap_or_else(|| "-".into());

            println!(
                "  {} ... policy={} safety={} trace={} ctrl={} {}ms",
                scenario.id, pol, saf, tra, ctrl, run_result.latency_ms
            );

            run_decisions.push(run_result.result.decision.clone());
            all_latencies.push(run_result.latency_ms);
            all_scores.push(score);
        }

        all_runs.push(run_decisions);
    }

    // Aggregate scores
    let (pol, saf, tra, con) = aggregate_scores(&all_scores);

    // Consistency across runs — transpose: runs[scenario][repeat]
    let consistency = if repeats > 1 {
        eval_consistency(&all_runs)
    } else {
        veritasbench_core::score::ConsistencyResult {
            identical: scenarios.len() as u32,
            total: scenarios.len() as u32,
        }
    };

    // Latency stats
    all_latencies.sort_unstable();
    let len = all_latencies.len();
    let latency = LatencyStats {
        p50_ms: all_latencies[len / 2],
        p95_ms: all_latencies[(len as f64 * 0.95) as usize],
        p99_ms: all_latencies[(len as f64 * 0.99) as usize],
    };

    let report = BenchmarkReport {
        suite: suite_name,
        adapter: adapter_path.display().to_string(),
        timestamp: chrono::Utc::now().to_rfc3339(),
        policy_compliance: pol,
        safety: saf,
        traceability: tra,
        controllability: con,
        consistency,
        latency,
        per_scenario: all_scores,
    };

    // Write outputs
    let json_path = output_dir.join("report.json");
    let md_path = output_dir.join("report.md");

    if let Err(e) = write_json_report(&report, &json_path) {
        eprintln!("error: failed to write JSON report: {}", e);
        std::process::exit(1);
    }
    if let Err(e) = write_markdown_report(&report, &md_path) {
        eprintln!("error: failed to write markdown report: {}", e);
        std::process::exit(1);
    }

    println!("\nReports written to {}", output_dir.display());
    println!();
    print!("{}", generate_markdown(&report));
}

fn report_command(dir: PathBuf) {
    let json_path = dir.join("report.json");
    let content = match std::fs::read_to_string(&json_path) {
        Ok(c) => c,
        Err(e) => {
            eprintln!("error: failed to read {}: {}", json_path.display(), e);
            std::process::exit(1);
        }
    };
    let report: BenchmarkReport = match serde_json::from_str(&content) {
        Ok(r) => r,
        Err(e) => {
            eprintln!("error: failed to parse report.json: {}", e);
            std::process::exit(1);
        }
    };
    print!("{}", generate_markdown(&report));
}

fn diff_command(a_dir: PathBuf, b_dir: PathBuf) {
    let report_a = load_report_from_dir(&a_dir);
    let report_b = load_report_from_dir(&b_dir);

    println!("# VeritasBench Diff\n");
    println!("| Dimension | A earned/possible | B earned/possible | Delta |");
    println!("|---|---|---|---|");

    let dims = [
        ("Policy Compliance", &report_a.policy_compliance, &report_b.policy_compliance),
        ("Safety", &report_a.safety, &report_b.safety),
        ("Traceability", &report_a.traceability, &report_b.traceability),
        ("Controllability", &report_a.controllability, &report_b.controllability),
    ];

    for (name, da, db) in &dims {
        let pct_a = da.percentage() * 100.0;
        let pct_b = db.percentage() * 100.0;
        let delta = pct_b - pct_a;
        let delta_str = if delta > 0.0 {
            format!("+{:.0}%", delta)
        } else if delta < 0.0 {
            format!("{:.0}%", delta)
        } else {
            "0%".to_string()
        };
        println!(
            "| {} | {}/{} ({:.0}%) | {}/{} ({:.0}%) | {} |",
            name,
            da.earned,
            da.possible,
            pct_a,
            db.earned,
            db.possible,
            pct_b,
            delta_str
        );
    }

    println!();
    println!(
        "**A:** {} @ {}", report_a.adapter, report_a.timestamp
    );
    println!(
        "**B:** {} @ {}", report_b.adapter, report_b.timestamp
    );
}

fn load_report_from_dir(dir: &PathBuf) -> BenchmarkReport {
    let json_path = dir.join("report.json");
    let content = match std::fs::read_to_string(&json_path) {
        Ok(c) => c,
        Err(e) => {
            eprintln!("error: failed to read {}: {}", json_path.display(), e);
            std::process::exit(1);
        }
    };
    match serde_json::from_str(&content) {
        Ok(r) => r,
        Err(e) => {
            eprintln!("error: failed to parse {}: {}", json_path.display(), e);
            std::process::exit(1);
        }
    }
}
