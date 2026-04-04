use std::path::Path;

use veritasbench_core::score::BenchmarkReport;

fn pct(earned: u32, possible: u32) -> u32 {
    if possible == 0 { 0 } else { (earned as f64 / possible as f64 * 100.0).round() as u32 }
}

pub fn generate_markdown(report: &BenchmarkReport) -> String {
    let pol = &report.policy_compliance;
    let saf = &report.safety;
    let tra = &report.traceability;
    let con = &report.controllability;

    let pol_pct = (pol.percentage() * 100.0).round() as u32;
    let saf_pct = (saf.percentage() * 100.0).round() as u32;
    let tra_pct = (tra.percentage() * 100.0).round() as u32;
    let con_pct = (con.percentage() * 100.0).round() as u32;

    // Per-tier policy compliance breakdown
    let tier_section = {
        let mut tiers: std::collections::BTreeMap<String, (u32, u32)> = std::collections::BTreeMap::new();
        for s in &report.per_scenario {
            if let (Some(pol_score), Some(diff)) = (s.policy_compliance, s.difficulty.as_ref()) {
                let entry = tiers.entry(diff.clone()).or_insert((0, 0));
                entry.0 += pol_score;
                entry.1 += 1;
            }
        }
        if tiers.is_empty() {
            String::new()
        } else {
            let mut lines = vec![
                "\n## Policy Compliance by Difficulty\n".to_string(),
                "| Difficulty | Earned | Possible | % |".to_string(),
                "|---|---|---|---|".to_string(),
            ];
            for (tier, (earned, possible)) in &tiers {
                lines.push(format!(
                    "| {} | {} | {} | {}% |",
                    tier.chars().next().map(|c| c.to_uppercase().to_string()).unwrap_or_default()
                        + &tier[1..],
                    earned, possible, pct(*earned, *possible)
                ));
            }
            lines.push(String::new());
            lines.join("\n")
        }
    };

    // Per-scenario-type breakdown (all 4 dimensions)
    let type_section = {
        // Map type prefix -> (pol_earned, pol_possible, saf_earned, saf_possible, tra_earned, tra_possible, con_earned, con_possible)
        let mut types: std::collections::BTreeMap<String, [u32; 8]> = std::collections::BTreeMap::new();
        let type_names: std::collections::HashMap<&str, &str> = [
            ("UA", "Unauthorized Access"), ("MA", "Missing Approval"),
            ("MJ", "Missing Justification"), ("PL", "PHI Leakage"),
            ("US", "Unsafe Action Sequence"), ("EO", "Emergency Override"),
            ("CM", "Consent Management"), ("CA", "Conflicting Authority"),
            ("II", "Incomplete Information"), ("SI", "System-Initiated"),
            ("AG", "Accountability Gap"),
        ].iter().cloned().collect();

        for s in &report.per_scenario {
            let prefix = s.scenario_id.split('-').next().unwrap_or("??");
            let name = type_names.get(prefix).unwrap_or(&prefix).to_string();
            let entry = types.entry(name).or_insert([0; 8]);
            if let Some(v) = s.policy_compliance { entry[0] += v; entry[1] += 1; }
            if let Some(v) = s.safety { entry[2] += v; entry[3] += 1; }
            if let Some(v) = s.traceability { entry[4] += v; entry[5] += 3; }
            if let Some(v) = s.controllability { entry[6] += v; entry[7] += 2; }
        }

        if types.is_empty() {
            String::new()
        } else {
            let mut lines = vec![
                "\n## Scores by Scenario Type\n".to_string(),
                "| Type | Policy | Safety | Traceability | Controllability |".to_string(),
                "|---|---|---|---|---|".to_string(),
            ];
            for (name, d) in &types {
                let pol_s = if d[1] > 0 { format!("{}%", pct(d[0], d[1])) } else { "-".into() };
                let saf_s = if d[3] > 0 { format!("{}%", pct(d[2], d[3])) } else { "-".into() };
                let tra_s = if d[5] > 0 { format!("{}%", pct(d[4], d[5])) } else { "-".into() };
                let con_s = if d[7] > 0 { format!("{}%", pct(d[6], d[7])) } else { "-".into() };
                lines.push(format!("| {} | {} | {} | {} | {} |", name, pol_s, saf_s, tra_s, con_s));
            }
            lines.push(String::new());
            lines.join("\n")
        }
    };

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
        **Dangerous Failures:** {df_count}/{df_total} (adapter allowed when governance required deny/block)\n\
        {tier_section}\
        {type_section}",
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
        tier_section = tier_section,
        type_section = type_section,
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
                difficulty: None,
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
