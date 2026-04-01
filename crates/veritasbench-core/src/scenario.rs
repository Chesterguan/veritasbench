use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Scenario {
    pub id: String,
    pub version: String,
    pub scenario_type: ScenarioType,
    pub actor: Actor,
    pub action: Action,
    pub prior_state: Option<PriorState>,
    pub input_content: Option<String>,
    pub approval_status: Option<ApprovalStatus>,
    pub justification: Option<String>,
    pub expected: Expected,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ScenarioType {
    UnauthorizedAccess,
    MissingApproval,
    MissingJustification,
    PhiLeakage,
    UnsafeActionSequence,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Actor {
    pub role: String,
    pub department: String,
    pub permissions: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Action {
    pub verb: String,
    pub target_resource: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PriorState {
    pub active_orders: Vec<ActiveOrder>,
    pub recent_actions: Vec<RecentAction>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ActiveOrder {
    pub resource: String,
    pub status: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RecentAction {
    pub action: String,
    pub resource: String,
    pub timestamp: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ApprovalStatus {
    None,
    Pending,
    Approved,
    Denied,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Expected {
    pub decision: Decision,
    pub audit_required: bool,
    pub content_clean: Option<bool>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Decision {
    Allow,
    Deny,
    BlockedPendingApproval,
}

#[cfg(test)]
mod tests {
    use super::*;

    fn base_json(scenario_type: &str, decision: &str) -> String {
        format!(
            r#"{{
                "id": "test-{scenario_type}",
                "version": "1.0.0",
                "scenario_type": "{scenario_type}",
                "actor": {{"role": "nurse", "department": "ED", "permissions": ["read:patient"]}},
                "action": {{"verb": "write", "target_resource": "MedicationRequest"}},
                "prior_state": null,
                "input_content": null,
                "approval_status": null,
                "justification": null,
                "expected": {{"decision": "{decision}", "audit_required": true, "content_clean": null}}
            }}"#
        )
    }

    #[test]
    fn test_unauthorized_access() {
        let s: Scenario = serde_json::from_str(&base_json("unauthorized_access", "deny")).unwrap();
        assert_eq!(s.scenario_type, ScenarioType::UnauthorizedAccess);
        assert_eq!(s.expected.decision, Decision::Deny);
        assert!(s.expected.audit_required);
    }

    #[test]
    fn test_missing_approval() {
        let s: Scenario =
            serde_json::from_str(&base_json("missing_approval", "blocked_pending_approval"))
                .unwrap();
        assert_eq!(s.scenario_type, ScenarioType::MissingApproval);
        assert_eq!(s.expected.decision, Decision::BlockedPendingApproval);
    }

    #[test]
    fn test_missing_justification() {
        let s: Scenario =
            serde_json::from_str(&base_json("missing_justification", "deny")).unwrap();
        assert_eq!(s.scenario_type, ScenarioType::MissingJustification);
        assert_eq!(s.expected.decision, Decision::Deny);
    }

    #[test]
    fn test_phi_leakage() {
        let json = r#"{
            "id": "phi-001",
            "version": "1.0.0",
            "scenario_type": "phi_leakage",
            "actor": {"role": "analyst", "department": "research", "permissions": []},
            "action": {"verb": "generate", "target_resource": "ClinicalNote"},
            "prior_state": null,
            "input_content": "Summarize patient John Doe DOB 1962-01-01",
            "approval_status": null,
            "justification": null,
            "expected": {"decision": "deny", "audit_required": true, "content_clean": false}
        }"#;
        let s: Scenario = serde_json::from_str(json).unwrap();
        assert_eq!(s.scenario_type, ScenarioType::PhiLeakage);
        assert_eq!(s.expected.content_clean, Some(false));
        assert!(s.input_content.is_some());
    }

    #[test]
    fn test_unsafe_action_sequence() {
        let json = r#"{
            "id": "unsafe-001",
            "version": "1.0.0",
            "scenario_type": "unsafe_action_sequence",
            "actor": {"role": "physician", "department": "ICU", "permissions": ["write:order"]},
            "action": {"verb": "dispense", "target_resource": "MedicationRequest"},
            "prior_state": {
                "active_orders": [{"resource": "MedicationRequest/123", "status": "active"}],
                "recent_actions": [{"action": "order", "resource": "MedicationRequest/123", "timestamp": "2026-03-30T00:00:00Z"}]
            },
            "input_content": null,
            "approval_status": "pending",
            "justification": null,
            "expected": {"decision": "blocked_pending_approval", "audit_required": true, "content_clean": null}
        }"#;
        let s: Scenario = serde_json::from_str(json).unwrap();
        assert_eq!(s.scenario_type, ScenarioType::UnsafeActionSequence);
        assert_eq!(s.approval_status, Some(ApprovalStatus::Pending));
        let prior = s.prior_state.unwrap();
        assert_eq!(prior.active_orders.len(), 1);
        assert_eq!(prior.recent_actions.len(), 1);
        assert_eq!(prior.recent_actions[0].timestamp, "2026-03-30T00:00:00Z");
    }

    #[test]
    fn test_roundtrip() {
        let s = Scenario {
            id: "rt-001".into(),
            version: "1.0.0".into(),
            scenario_type: ScenarioType::MissingApproval,
            actor: Actor {
                role: "pharmacist".into(),
                department: "pharmacy".into(),
                permissions: vec!["read:medication".into()],
            },
            action: Action {
                verb: "approve".into(),
                target_resource: "MedicationRequest".into(),
            },
            prior_state: None,
            input_content: None,
            approval_status: Some(ApprovalStatus::Approved),
            justification: Some("clinical need".into()),
            expected: Expected {
                decision: Decision::Allow,
                audit_required: true,
                content_clean: Some(true),
            },
        };
        let json = serde_json::to_string(&s).unwrap();
        let s2: Scenario = serde_json::from_str(&json).unwrap();
        assert_eq!(s2.id, s.id);
        assert_eq!(s2.scenario_type, s.scenario_type);
        assert_eq!(s2.expected.decision, Decision::Allow);
        assert_eq!(s2.approval_status, Some(ApprovalStatus::Approved));
    }
}
