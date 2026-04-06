use std::path::Path;

use veritasbench_core::score::BenchmarkReport;

pub fn generate_json(report: &BenchmarkReport) -> Result<String, serde_json::Error> {
    serde_json::to_string_pretty(report)
}

pub fn write_json_report(
    report: &BenchmarkReport,
    path: &Path,
) -> Result<(), Box<dyn std::error::Error>> {
    let json = generate_json(report)?;
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)?;
    }
    std::fs::write(path, json)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use veritasbench_core::score::{
        BenchmarkReport, ConsistencyResult, DangerousFailureStats, DimensionScore, LatencyStats,
        ScenarioScore,
    };

    fn sample_report() -> BenchmarkReport {
        BenchmarkReport {
            suite: "healthcare_v1".into(),
            adapter: "trivial_deny".into(),
            timestamp: "2026-03-30T00:00:00Z".into(),
            policy_compliance: DimensionScore { earned: 1, possible: 1 },
            safety: DimensionScore { earned: 0, possible: 0 },
            traceability: DimensionScore { earned: 3, possible: 3 },
            controllability: DimensionScore { earned: 0, possible: 0 },
            consistency: ConsistencyResult { identical: 1, total: 1 },
            latency: LatencyStats { p50_ms: 50, p95_ms: 80, p99_ms: 100 },
            dangerous_failures: DangerousFailureStats { count: 0, total: 0 },
            per_scenario: vec![ScenarioScore {
                scenario_id: "UA-001".into(),
                policy_compliance: Some(1),
                safety: None,
                traceability: Some(3),
                controllability: None,
                latency_ms: 50,
                dangerous_failure: None,
                difficulty: None,
            }],
        }
    }

    #[test]
    fn test_generate_json_roundtrip() {
        let report = sample_report();
        let json = generate_json(&report).expect("serialize should succeed");
        let parsed: BenchmarkReport =
            serde_json::from_str(&json).expect("deserialize should succeed");

        assert_eq!(parsed.suite, report.suite);
        assert_eq!(parsed.adapter, report.adapter);
        assert_eq!(parsed.policy_compliance.earned, 1);
        assert_eq!(parsed.traceability.possible, 3);
        assert_eq!(parsed.per_scenario.len(), 1);
        assert_eq!(parsed.per_scenario[0].scenario_id, "UA-001");
    }

    #[test]
    fn test_write_json_report_to_temp_file() {
        let report = sample_report();
        let dir = std::env::temp_dir().join("veritasbench_report_test");
        let path = dir.join("report.json");

        write_json_report(&report, &path).expect("write should succeed");

        let content = std::fs::read_to_string(&path).expect("file should exist");
        let parsed: BenchmarkReport =
            serde_json::from_str(&content).expect("file content should be valid JSON");

        assert_eq!(parsed.suite, "healthcare_v1");
        assert_eq!(parsed.latency.p50_ms, 50);

        // Clean up
        let _ = std::fs::remove_file(&path);
        let _ = std::fs::remove_dir(&dir);
    }
}
