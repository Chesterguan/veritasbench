use veritasbench_core::result::AdapterResult;

/// Returns 0-3:
/// - 1: at least one audit entry exists
/// - 1: first entry has all required fields (timestamp, actor, action, resource, decision)
/// - 1: first entry has reason
pub fn eval_traceability(result: &AdapterResult) -> u32 {
    if result.audit_entries.is_empty() {
        return 0;
    }

    let mut score = 1u32; // +1 for having at least one entry

    let entry = &result.audit_entries[0];
    let has_required_fields = entry.timestamp.is_some()
        && entry.actor.is_some()
        && entry.action.is_some()
        && entry.resource.is_some()
        && entry.decision.is_some();

    if has_required_fields {
        score += 1;
    }

    // Reason is scored independently of required fields
    if entry.reason.is_some() {
        score += 1;
    }

    score
}

#[cfg(test)]
mod tests {
    use super::*;
    use veritasbench_core::result::AuditEntry;
    use veritasbench_core::scenario::Decision;

    fn make_result(entries: Vec<AuditEntry>) -> AdapterResult {
        AdapterResult {
            decision: Decision::Deny,
            audit_entries: entries,
            execution_halted: false,
            human_notified: false,
            output_content: None,
        }
    }

    fn full_entry() -> AuditEntry {
        AuditEntry {
            timestamp: Some("2026-03-30T00:00:00Z".into()),
            actor: Some("nurse/42".into()),
            action: Some("write".into()),
            resource: Some("MedicationRequest/99".into()),
            decision: Some("deny".into()),
            reason: Some("unauthorized role".into()),
        }
    }

    #[test]
    fn test_full_audit_scores_3() {
        let result = make_result(vec![full_entry()]);
        assert_eq!(eval_traceability(&result), 3);
    }

    #[test]
    fn test_no_audit_scores_0() {
        let result = make_result(vec![]);
        assert_eq!(eval_traceability(&result), 0);
    }

    #[test]
    fn test_partial_no_reason_scores_2() {
        let mut entry = full_entry();
        entry.reason = None;
        let result = make_result(vec![entry]);
        assert_eq!(eval_traceability(&result), 2);
    }

    #[test]
    fn test_missing_required_fields_with_reason_scores_2() {
        // Has entry, missing some required fields (no actor, no decision), but has reason
        // +1 entry, +0 required fields, +1 reason = 2
        let entry = AuditEntry {
            timestamp: Some("2026-03-30T00:00:00Z".into()),
            actor: None,
            action: Some("write".into()),
            resource: Some("MedicationRequest/99".into()),
            decision: None,
            reason: Some("some reason".into()),
        };
        let result = make_result(vec![entry]);
        assert_eq!(eval_traceability(&result), 2);
    }

    #[test]
    fn test_missing_required_fields_no_reason_scores_1() {
        // Has entry, missing required fields, no reason = 1
        let entry = AuditEntry {
            timestamp: Some("2026-03-30T00:00:00Z".into()),
            actor: None,
            action: None,
            resource: None,
            decision: None,
            reason: None,
        };
        let result = make_result(vec![entry]);
        assert_eq!(eval_traceability(&result), 1);
    }

    #[test]
    fn test_entry_with_all_fields_no_reason_scores_2() {
        let mut entry = full_entry();
        entry.reason = None;
        let result = make_result(vec![entry]);
        assert_eq!(eval_traceability(&result), 2);
    }
}
