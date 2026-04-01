use std::path::Path;

#[tokio::test]
async fn test_full_pipeline_trivial_deny() {
    // CARGO_MANIFEST_DIR is tests/; scenarios and examples are at workspace root
    let manifest = Path::new(env!("CARGO_MANIFEST_DIR"));
    let workspace_root = manifest.parent().expect("workspace root");

    let suite_path = workspace_root.join("scenarios/healthcare_core_v0");
    let adapter_path = workspace_root.join("examples/trivial_deny_adapter.py");

    // Load scenarios
    let scenarios = veritasbench_runner::suite::load_suite(&suite_path).unwrap();
    assert_eq!(scenarios.len(), 100);

    // Run each scenario
    let mut scores = Vec::new();
    for scenario in &scenarios {
        let run_result = veritasbench_runner::adapter::run_adapter(&adapter_path, scenario, 30_000)
            .await
            .unwrap();
        let score = veritasbench_eval::aggregate::evaluate_scenario(scenario, &run_result.result, run_result.latency_ms);
        scores.push(score);
    }

    // Aggregate
    let (policy, safety, trace, control) = veritasbench_eval::aggregate::aggregate_scores(&scores);

    // Trivial deny should get high policy compliance (deny is correct for most scenarios)
    assert!(policy.possible > 0);
    assert!(policy.earned > 0);
    // All scenarios require audit, and trivial deny provides full audit
    assert!(trace.possible > 0);
    assert!(trace.earned > 0);

    // Generate report
    let report = veritasbench_core::score::BenchmarkReport {
        suite: "healthcare_core_v0".to_string(),
        adapter: "trivial_deny_adapter.py".to_string(),
        timestamp: "2026-04-01T00:00:00Z".to_string(),
        policy_compliance: policy,
        safety,
        traceability: trace,
        controllability: control,
        consistency: veritasbench_core::score::ConsistencyResult { identical: 0, total: 0 },
        latency: veritasbench_core::score::LatencyStats { p50_ms: 0, p95_ms: 0, p99_ms: 0 },
        per_scenario: scores,
    };

    let json = veritasbench_report::json::generate_json(&report).unwrap();
    assert!(json.contains("healthcare_core_v0"));

    let md = veritasbench_report::markdown::generate_markdown(&report);
    assert!(md.contains("Policy Compliance"));
    assert!(md.contains("Traceability"));
}
