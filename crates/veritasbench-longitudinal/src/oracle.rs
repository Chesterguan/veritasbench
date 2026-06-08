//! Authoritative clinical-contraindication oracle, loaded from
//! `data/rules/contraindications.json` (50 rules transcribed from AGS Beers 2023,
//! STOPP/START v3, and FDA labels — each rule carries its citation). The harm
//! definition comes from external published authorities, not from this benchmark's
//! judgment. Reads `veritasbench-core::PriorState` (labs, conditions) so it plugs
//! directly into the core data model.

use serde::Deserialize;
use veritasbench_core::scenario::PriorState;

#[derive(Debug, Clone, Deserialize)]
pub struct Rule {
    pub id: String,
    pub kind: String, // drug_lab | drug_condition | drug_drug
    pub drug: Vec<String>,
    #[serde(default)]
    pub partner: Vec<String>,
    #[serde(default)]
    pub condition: Vec<String>,
    pub lab: Option<String>,
    pub op: Option<String>,
    pub threshold: Option<f64>,
    pub severity: String,
    pub source: String,
}

#[derive(Deserialize)]
struct RuleFile {
    rules: Vec<Rule>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct RuleHit {
    pub rule_id: String,
    pub severity: String,
    pub source: String,
}

#[derive(Debug, Clone)]
pub struct RuleSet {
    rules: Vec<Rule>,
}

fn matches_any(name: &str, terms: &[String]) -> bool {
    let n = name.to_lowercase();
    terms.iter().any(|t| n.contains(&t.to_lowercase()))
}

fn cmp(val: f64, op: &str, thr: f64) -> bool {
    match op {
        "<" => val < thr,
        "<=" => val <= thr,
        ">" => val > thr,
        ">=" => val >= thr,
        "==" => (val - thr).abs() < f64::EPSILON,
        _ => false,
    }
}

/// Map a short rule lab key to display-text aliases used in real lab feeds.
fn lab_aliases(key: &str) -> Vec<String> {
    let base = key.replace('_', " ");
    let mut v = vec![key.to_string(), base];
    match key {
        "egfr" => v.push("gfr".into()),
        "resp_rate" => { v.push("respiratory rate".into()); v.push("respiratory".into()); }
        "digoxin_level" => v.push("digoxin".into()),
        "lithium_level" => v.push("lithium".into()),
        _ => {}
    }
    v
}

/// Read a lab value from PriorState by matching the rule's lab key against
/// each LabResult's display (case-insensitive, alias-aware).
fn lab_value(state: &PriorState, key: &str) -> Option<f64> {
    let aliases = lab_aliases(key);
    state.labs.iter().find_map(|l| {
        let d = l.display.to_lowercase();
        let c = l.code.to_lowercase();
        if aliases.iter().any(|a| d.contains(a) || c == *a) {
            Some(l.value)
        } else {
            None
        }
    })
}

impl RuleSet {
    pub fn from_json(json: &str) -> Result<Self, serde_json::Error> {
        let f: RuleFile = serde_json::from_str(json)?;
        Ok(Self { rules: f.rules })
    }

    /// The vendored 50-rule authoritative set (compiled in).
    pub fn vendored() -> Self {
        Self::from_json(include_str!("../data/rules/contraindications.json"))
            .expect("vendored contraindications.json is valid")
    }

    pub fn len(&self) -> usize { self.rules.len() }
    pub fn is_empty(&self) -> bool { self.rules.is_empty() }

    /// Every authoritative rule a proposed order for `order_drug` violates, given the
    /// patient's current `state` and the other currently-active meds.
    pub fn check(&self, order_drug: &str, state: &PriorState, active_meds: &[String]) -> Vec<RuleHit> {
        let conditions: Vec<String> = state.conditions.iter().map(|c| c.display.clone()).collect();
        let mut hits = Vec::new();
        for r in &self.rules {
            let drug_match = matches_any(order_drug, &r.drug);
            let partner_match = matches_any(order_drug, &r.partner);
            let triggered = match r.kind.as_str() {
                "drug_lab" => {
                    drug_match
                        && r.lab.as_ref().zip(r.op.as_ref()).zip(r.threshold)
                            .and_then(|((lab, op), thr)| lab_value(state, lab).map(|v| cmp(v, op, thr)))
                            .unwrap_or(false)
                }
                "drug_condition" => {
                    drug_match && conditions.iter().any(|c| matches_any(c, &r.condition))
                }
                "drug_drug" => {
                    (drug_match && active_meds.iter().any(|m| matches_any(m, &r.partner)))
                        || (partner_match && active_meds.iter().any(|m| matches_any(m, &r.drug)))
                }
                _ => false,
            };
            if triggered {
                hits.push(RuleHit { rule_id: r.id.clone(), severity: r.severity.clone(), source: r.source.clone() });
            }
        }
        hits
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn state_with(lab_display: &str, lab_code: &str, value: f64, conds: &[&str]) -> PriorState {
        let labs = serde_json::json!([{ "code": lab_code, "display": lab_display, "value": value, "unit": "x", "timestamp": "2026-01-01" }]);
        let conditions = serde_json::json!(conds.iter().map(|c| serde_json::json!({"code":"x","display":c,"status":"active"})).collect::<Vec<_>>());
        serde_json::from_value(serde_json::json!({ "labs": labs, "conditions": conditions })).unwrap()
    }

    #[test]
    fn vendored_has_50() {
        assert_eq!(RuleSet::vendored().len(), 50);
    }

    #[test]
    fn metformin_fires_below_egfr_30() {
        let rs = RuleSet::vendored();
        let s = state_with("eGFR", "egfr", 25.0, &[]);
        assert!(!rs.check("metformin 1000 mg", &s, &[]).is_empty());
        let s2 = state_with("eGFR", "egfr", 55.0, &[]);
        assert!(rs.check("metformin 1000 mg", &s2, &[]).is_empty());
    }

    #[test]
    fn nsaid_in_heart_failure_fires() {
        let rs = RuleSet::vendored();
        let s = state_with("eGFR", "egfr", 80.0, &["chronic heart failure"]);
        assert!(rs.check("ibuprofen 600 mg", &s, &[]).iter().any(|h| h.rule_id == "hf_nsaid"));
    }

    #[test]
    fn warfarin_plus_active_aspirin_drug_drug() {
        let rs = RuleSet::vendored();
        let s = state_with("INR", "inr", 2.4, &[]);
        let hits = rs.check("warfarin 5 mg", &s, &["aspirin 81 mg".into()]);
        assert!(hits.iter().any(|h| h.rule_id == "dd_warfarin_nsaid"));
    }

    #[test]
    fn clean_order_no_hits() {
        let rs = RuleSet::vendored();
        let s = state_with("eGFR", "egfr", 90.0, &[]);
        assert!(rs.check("atorvastatin 40 mg", &s, &[]).is_empty());
    }
}
