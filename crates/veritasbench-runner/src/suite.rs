use std::path::Path;

use veritasbench_core::{error::VBError, scenario::Scenario};

/// Load all `.json` scenario files from `path`, sorted by filename.
///
/// Returns `VBError::SuiteNotFound` if the directory does not exist.
/// Returns `VBError::Io` or `VBError::ScenarioParse` on read/parse failure.
pub fn load_suite(path: &Path) -> Result<Vec<Scenario>, VBError> {
    if !path.exists() {
        return Err(VBError::SuiteNotFound(path.display().to_string()));
    }

    let mut entries: Vec<_> = std::fs::read_dir(path)?
        .filter_map(|e| e.ok())
        .filter(|e| {
            e.path()
                .extension()
                .and_then(|ext| ext.to_str())
                .map(|ext| ext == "json")
                .unwrap_or(false)
        })
        .collect();

    // Sort by filename for deterministic ordering
    entries.sort_by_key(|e| e.file_name());

    let mut scenarios = Vec::with_capacity(entries.len());
    for entry in entries {
        let content = std::fs::read_to_string(entry.path())?;
        let scenario: Scenario = serde_json::from_str(&content)?;
        scenarios.push(scenario);
    }

    Ok(scenarios)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    fn workspace_root() -> PathBuf {
        // CARGO_MANIFEST_DIR is crates/veritasbench-runner; go up two levels
        let manifest = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        manifest
            .parent()
            .expect("crates dir")
            .parent()
            .expect("workspace root")
            .to_path_buf()
    }

    #[test]
    fn test_load_real_suite() {
        let suite_dir = workspace_root().join("scenarios/healthcare_v1");
        let scenarios = load_suite(&suite_dir).expect("should load suite");
        assert!(!scenarios.is_empty(), "expected at least one scenario");

        // Verify UA-001 is present and correct
        let ua001 = scenarios.iter().find(|s| s.id == "UA-001").expect("UA-001 should be present");
        assert_eq!(ua001.actor.role, "ward_nurse");
        assert_eq!(ua001.action.verb, "read");
        assert_eq!(ua001.action.target_resource, "Patient/P-892");
        assert!(ua001.expected.audit_required);
    }

    #[test]
    fn test_sorted_order() {
        let suite_dir = workspace_root().join("scenarios/healthcare_v1");
        let scenarios = load_suite(&suite_dir).expect("should load suite");
        let ids: Vec<&str> = scenarios.iter().map(|s| s.id.as_str()).collect();
        let mut sorted = ids.clone();
        sorted.sort();
        assert_eq!(ids, sorted, "scenarios should be sorted by filename");
    }

    #[test]
    fn test_nonexistent_directory() {
        let bad_path = PathBuf::from("/tmp/veritasbench_nonexistent_suite_xyz");
        let result = load_suite(&bad_path);
        assert!(result.is_err());
        match result.unwrap_err() {
            VBError::SuiteNotFound(p) => assert!(p.contains("nonexistent_suite_xyz")),
            other => panic!("expected SuiteNotFound, got {other}"),
        }
    }
}
