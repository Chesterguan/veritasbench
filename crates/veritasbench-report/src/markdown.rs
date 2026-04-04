use std::path::Path;

use veritasbench_core::score::BenchmarkReport;

pub fn generate_markdown(report: &BenchmarkReport) -> String {
    let pol = &report.policy_compliance;
    let saf = &report.safety;
    let tra = &report.traceability;
    let con = &report.controllability;

    let pol_pct = (pol.percentage() * 100.0).round() as u32;
    let saf_pct = (saf.percentage() * 100.0).round() as u32;
    let tra_pct = (tra.percentage() * 100.0).round() as u32;
    let con_pct = (con.percentage() * 100.0).round() as u32;

    let consistency_pct = if report.consistency.total == 0 {
        0
    } else {
        (report.consistency.identical as f64 / report.consistency.total as f64 * 100.0).round()
            as u32
    };

    format!(
        "# VeritasBench Report — {suite}\n\
        \n\
        **Adapter:** `{adapter}`\n\
        **Timestamp:** {timestamp}\n\
        \n\
        ## Scores\n\
        \n\
        | Dimension | Earned | Possible | % |\n\
        |---|---|---|---|\n\
        | Policy Compliance | {pol_e} | {pol_p} | {pol_pct}% |\n\
        | Safety | {saf_e} | {saf_p} | {saf_pct}% |\n\
        | Traceability | {tra_e} | {tra_p} | {tra_pct}% |\n\
        | Controllability | {con_e} | {con_p} | {con_pct}% |\n\
        \n\
        ## Metrics\n\
        \n\
        **Consistency:** {consistency_pct}% ({con_id}/{con_tot} identical across runs)\n\
        \n\
        **Latency:** p50={p50}ms  p95={p95}ms  p99={p99}ms\n\
        \n\
        **Dangerous Failures:** {df_count}/{df_total} (adapter allowed when governance required deny/block)\n",
        suite = report.suite,
        adapter = report.adapter,
        timestamp = report.timestamp,
        pol_e = pol.earned,
        pol_p = pol.possible,
        pol_pct = pol_pct,
        saf_e = saf.earned,
        saf_p = saf.possible,
        saf_pct = saf_pct,
        tra_e = tra.earned,
        tra_p = tra.possible,
        tra_pct = tra_pct,
        con_e = con.earned,
        con_p = con.possible,
        con_pct = con_pct,
        consistency_pct = consistency_pct,
        con_id = report.consistency.identical,
        con_tot = report.consistency.total,
        p50 = report.latency.p50_ms,
        p95 = report.latency.p95_ms,
        p99 = report.latency.p99_ms,
        df_count = report.dangerous_failures.count,
        df_total = report.dangerous_failures.total,
    )
}

pub fn write_markdown_report(
    report: &BenchmarkReport,
    path: &Path,
) -> Result<(), Box<dyn std::error::Error>> {
    let md = generate_markdown(report);
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)?;
    }
    std::fs::write(path, md)?;
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
            suite: "healthcare_core_v0".into(),
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
            }],
        }
    }

    #[test]
    fn test_markdown_contains_dimension_names() {
        let md = generate_markdown(&sample_report());
        assert!(md.contains("Policy Compliance"), "missing Policy Compliance");
        assert!(md.contains("Safety"), "missing Safety");
        assert!(md.contains("Traceability"), "missing Traceability");
        assert!(md.contains("Controllability"), "missing Controllability");
    }

    #[test]
    fn test_markdown_contains_percentages() {
        let md = generate_markdown(&sample_report());
        // Policy: 1/1 = 100%
        assert!(md.contains("100%"), "missing 100% for policy");
    }

    #[test]
    fn test_markdown_contains_latency_stats() {
        let md = generate_markdown(&sample_report());
        assert!(md.contains("p50=50ms"), "missing p50");
        assert!(md.contains("p95=80ms"), "missing p95");
        assert!(md.contains("p99=100ms"), "missing p99");
    }

    #[test]
    fn test_markdown_contains_suite_and_adapter() {
        let md = generate_markdown(&sample_report());
        assert!(md.contains("healthcare_core_v0"), "missing suite name");
        assert!(md.contains("trivial_deny"), "missing adapter name");
        assert!(md.contains("2026-03-30T00:00:00Z"), "missing timestamp");
    }

    #[test]
    fn test_write_markdown_report_to_temp_file() {
        let report = sample_report();
        let dir = std::env::temp_dir().join("veritasbench_md_test");
        let path = dir.join("report.md");

        write_markdown_report(&report, &path).expect("write should succeed");

        let content = std::fs::read_to_string(&path).expect("file should exist");
        assert!(content.contains("VeritasBench Report"), "missing header");
        assert!(content.contains("Latency"), "missing latency section");

        // Clean up
        let _ = std::fs::remove_file(&path);
        let _ = std::fs::remove_dir(&dir);
    }
}
