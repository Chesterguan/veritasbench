use veritasbench_core::scenario::Decision;
use veritasbench_core::score::ConsistencyResult;

/// Given decisions from multiple runs (runs[run_index][scenario_index]),
/// count scenarios with identical decisions across all runs.
pub fn eval_consistency(runs: &[Vec<Decision>]) -> ConsistencyResult {
    if runs.is_empty() {
        return ConsistencyResult { identical: 0, total: 0 };
    }

    let scenario_count = runs[0].len();
    if scenario_count == 0 {
        return ConsistencyResult { identical: 0, total: 0 };
    }

    // Single run — all scenarios are trivially consistent
    if runs.len() == 1 {
        return ConsistencyResult {
            identical: scenario_count as u32,
            total: scenario_count as u32,
        };
    }

    let mut identical = 0u32;
    for i in 0..scenario_count {
        let first = &runs[0][i];
        let all_same = runs[1..].iter().all(|run| run.get(i) == Some(first));
        if all_same {
            identical += 1;
        }
    }

    ConsistencyResult { identical, total: scenario_count as u32 }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_all_consistent() {
        let runs = vec![
            vec![Decision::Deny, Decision::Allow, Decision::BlockedPendingApproval],
            vec![Decision::Deny, Decision::Allow, Decision::BlockedPendingApproval],
            vec![Decision::Deny, Decision::Allow, Decision::BlockedPendingApproval],
        ];
        let result = eval_consistency(&runs);
        assert_eq!(result.identical, 3);
        assert_eq!(result.total, 3);
    }

    #[test]
    fn test_one_inconsistent() {
        let runs = vec![
            vec![Decision::Deny, Decision::Allow, Decision::Deny],
            vec![Decision::Deny, Decision::Deny, Decision::Deny],
        ];
        let result = eval_consistency(&runs);
        assert_eq!(result.identical, 2); // index 0 and 2 are consistent
        assert_eq!(result.total, 3);
    }

    #[test]
    fn test_single_run() {
        let runs = vec![vec![Decision::Deny, Decision::Allow]];
        let result = eval_consistency(&runs);
        assert_eq!(result.identical, 2);
        assert_eq!(result.total, 2);
    }

    #[test]
    fn test_empty_runs() {
        let result = eval_consistency(&[]);
        assert_eq!(result.identical, 0);
        assert_eq!(result.total, 0);
    }

    #[test]
    fn test_all_inconsistent() {
        let runs = vec![
            vec![Decision::Deny, Decision::Allow],
            vec![Decision::Allow, Decision::Deny],
        ];
        let result = eval_consistency(&runs);
        assert_eq!(result.identical, 0);
        assert_eq!(result.total, 2);
    }
}
