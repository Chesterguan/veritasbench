use serde::{Deserialize, Serialize};

use crate::scenario::Decision;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AdapterResult {
    pub decision: Decision,
    pub audit_entries: Vec<AuditEntry>,
    pub execution_halted: bool,
    pub human_notified: bool,
    pub output_content: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuditEntry {
    pub timestamp: Option<String>,
    pub actor: Option<String>,
    pub action: Option<String>,
    pub resource: Option<String>,
    pub decision: Option<String>,
    pub reason: Option<String>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_deny_with_audit() {
        let json = r#"{
            "decision": "deny",
            "audit_entries": [{
                "timestamp": "2026-03-30T00:00:00Z",
                "actor": "nurse/42",
                "action": "write",
                "resource": "MedicationRequest/99",
                "decision": "deny",
                "reason": "unauthorized role"
            }],
            "execution_halted": true,
            "human_notified": true,
            "output_content": null
        }"#;
        let r: AdapterResult = serde_json::from_str(json).unwrap();
        assert_eq!(r.decision, Decision::Deny);
        assert!(r.execution_halted);
        assert!(r.human_notified);
        assert_eq!(r.audit_entries.len(), 1);
        assert_eq!(r.audit_entries[0].reason.as_deref(), Some("unauthorized role"));
    }

    #[test]
    fn test_minimal_allow() {
        let json = r#"{
            "decision": "allow",
            "audit_entries": [],
            "execution_halted": false,
            "human_notified": false,
            "output_content": null
        }"#;
        let r: AdapterResult = serde_json::from_str(json).unwrap();
        assert_eq!(r.decision, Decision::Allow);
        assert!(!r.execution_halted);
        assert!(r.audit_entries.is_empty());
    }

    #[test]
    fn test_blocked_pending_approval() {
        let json = r#"{
            "decision": "blocked_pending_approval",
            "audit_entries": [{
                "timestamp": null,
                "actor": "physician/7",
                "action": "dispense",
                "resource": "MedicationRequest/5",
                "decision": "blocked_pending_approval",
                "reason": "requires attending sign-off"
            }],
            "execution_halted": true,
            "human_notified": true,
            "output_content": "Awaiting approval from attending physician"
        }"#;
        let r: AdapterResult = serde_json::from_str(json).unwrap();
        assert_eq!(r.decision, Decision::BlockedPendingApproval);
        assert!(r.execution_halted);
        assert!(r.human_notified);
        assert_eq!(r.output_content.as_deref(), Some("Awaiting approval from attending physician"));
        assert!(r.audit_entries[0].timestamp.is_none());
    }

    #[test]
    fn test_roundtrip() {
        let r = AdapterResult {
            decision: Decision::Deny,
            audit_entries: vec![AuditEntry {
                timestamp: Some("2026-03-30T00:00:00Z".into()),
                actor: Some("system".into()),
                action: Some("validate".into()),
                resource: Some("Encounter/1".into()),
                decision: Some("deny".into()),
                reason: Some("policy violation".into()),
            }],
            execution_halted: true,
            human_notified: false,
            output_content: None,
        };
        let json = serde_json::to_string(&r).unwrap();
        let r2: AdapterResult = serde_json::from_str(&json).unwrap();
        assert_eq!(r2.decision, Decision::Deny);
        assert_eq!(r2.audit_entries[0].reason.as_deref(), Some("policy violation"));
    }
}
