use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScenarioScore {
    pub scenario_id: String,
    pub policy_compliance: Option<u32>,
    pub safety: Option<u32>,
    pub traceability: Option<u32>,
    pub controllability: Option<u32>,
    pub latency_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DimensionScore {
    pub earned: u32,
    pub possible: u32,
}

impl DimensionScore {
    pub fn percentage(&self) -> f64 {
        if self.possible == 0 {
            return 0.0;
        }
        self.earned as f64 / self.possible as f64
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConsistencyResult {
    pub identical: u32,
    pub total: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LatencyStats {
    pub p50_ms: u64,
    pub p95_ms: u64,
    pub p99_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BenchmarkReport {
    pub suite: String,
    pub adapter: String,
    pub timestamp: String,
    pub policy_compliance: DimensionScore,
    pub safety: DimensionScore,
    pub traceability: DimensionScore,
    pub controllability: DimensionScore,
    pub consistency: ConsistencyResult,
    pub latency: LatencyStats,
    pub per_scenario: Vec<ScenarioScore>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_dimension_score_percentage_normal() {
        let d = DimensionScore { earned: 3, possible: 4 };
        assert!((d.percentage() - 0.75).abs() < f64::EPSILON);
    }

    #[test]
    fn test_dimension_score_percentage_zero_possible() {
        let d = DimensionScore { earned: 0, possible: 0 };
        assert_eq!(d.percentage(), 0.0);
    }

    #[test]
    fn test_dimension_score_percentage_full() {
        let d = DimensionScore { earned: 10, possible: 10 };
        assert!((d.percentage() - 1.0).abs() < f64::EPSILON);
    }

    #[test]
    fn test_scenario_score_creation() {
        let s = ScenarioScore {
            scenario_id: "ua-001".into(),
            policy_compliance: Some(10),
            safety: Some(8),
            traceability: Some(5),
            controllability: None,
            latency_ms: 312,
        };
        assert_eq!(s.scenario_id, "ua-001");
        assert_eq!(s.policy_compliance, Some(10));
        assert!(s.controllability.is_none());
        assert_eq!(s.latency_ms, 312);
    }

    #[test]
    fn test_benchmark_report_roundtrip() {
        let report = BenchmarkReport {
            suite: "core-safety-v1".into(),
            adapter: "cliniclaw-mock".into(),
            timestamp: "2026-03-30T00:00:00Z".into(),
            policy_compliance: DimensionScore { earned: 40, possible: 50 },
            safety: DimensionScore { earned: 35, possible: 40 },
            traceability: DimensionScore { earned: 20, possible: 25 },
            controllability: DimensionScore { earned: 18, possible: 20 },
            consistency: ConsistencyResult { identical: 9, total: 10 },
            latency: LatencyStats { p50_ms: 120, p95_ms: 450, p99_ms: 900 },
            per_scenario: vec![
                ScenarioScore {
                    scenario_id: "ua-001".into(),
                    policy_compliance: Some(10),
                    safety: Some(8),
                    traceability: Some(5),
                    controllability: Some(4),
                    latency_ms: 200,
                },
            ],
        };

        let json = serde_json::to_string(&report).unwrap();
        let r2: BenchmarkReport = serde_json::from_str(&json).unwrap();

        assert_eq!(r2.suite, "core-safety-v1");
        assert_eq!(r2.adapter, "cliniclaw-mock");
        assert_eq!(r2.policy_compliance.earned, 40);
        assert_eq!(r2.consistency.identical, 9);
        assert_eq!(r2.latency.p95_ms, 450);
        assert_eq!(r2.per_scenario.len(), 1);
        assert_eq!(r2.per_scenario[0].scenario_id, "ua-001");
    }
}
