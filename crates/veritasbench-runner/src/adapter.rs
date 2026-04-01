use std::path::Path;
use std::time::Instant;

use tokio::io::AsyncWriteExt;
use tokio::process::Command;
use veritasbench_core::error::VBError;
use veritasbench_core::result::AdapterResult;
use veritasbench_core::scenario::Scenario;

/// Output from a single adapter invocation.
pub struct RunResult {
    pub result: AdapterResult,
    /// Wall-clock time from spawn to stdout parse, in milliseconds.
    pub latency_ms: u64,
}

/// Spawn `python3 adapter_path`, pipe the serialized `scenario` to stdin,
/// collect stdout, and parse it as an `AdapterResult`.
///
/// Returns `VBError::AdapterTimeout` if the process does not finish within
/// `timeout_ms` milliseconds.  Returns `VBError::Adapter` if the process
/// exits non-zero or if stdout cannot be parsed.
pub async fn run_adapter(
    adapter_path: &Path,
    scenario: &Scenario,
    timeout_ms: u64,
) -> Result<RunResult, VBError> {
    let scenario_json = serde_json::to_string(scenario)?;

    let mut child = Command::new("python3")
        .arg(adapter_path)
        .stdin(std::process::Stdio::piped())
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::piped())
        .spawn()
        .map_err(|e| VBError::Adapter(format!("failed to spawn adapter: {e}")))?;

    // Write scenario JSON to stdin, then close it so the adapter sees EOF
    if let Some(mut stdin) = child.stdin.take() {
        stdin
            .write_all(scenario_json.as_bytes())
            .await
            .map_err(|e| VBError::Adapter(format!("failed to write stdin: {e}")))?;
        // Drop flushes and closes the pipe
    }

    let start = Instant::now();
    let timeout = std::time::Duration::from_millis(timeout_ms);

    let output = tokio::time::timeout(timeout, child.wait_with_output())
        .await
        .map_err(|_| VBError::AdapterTimeout(timeout_ms))?
        .map_err(|e| VBError::Adapter(format!("process wait failed: {e}")))?;

    let latency_ms = start.elapsed().as_millis() as u64;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr).to_string();
        return Err(VBError::Adapter(format!(
            "adapter exited with status {}: {stderr}",
            output.status
        )));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let result: AdapterResult = serde_json::from_str(stdout.trim())
        .map_err(|e| VBError::Adapter(format!("failed to parse adapter output: {e}\nstdout: {stdout}")))?;

    Ok(RunResult { result, latency_ms })
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;
    use veritasbench_core::scenario::{Action, Actor, Decision, Expected, ScenarioType};

    fn workspace_root() -> PathBuf {
        let manifest = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        manifest
            .parent()
            .expect("crates dir")
            .parent()
            .expect("workspace root")
            .to_path_buf()
    }

    fn sample_scenario() -> Scenario {
        Scenario {
            id: "UA-001".into(),
            version: "0.1.0".into(),
            scenario_type: ScenarioType::UnauthorizedAccess,
            actor: Actor {
                role: "ward_nurse".into(),
                department: "cardiology".into(),
                permissions: vec!["read:cardiology".into()],
            },
            action: Action {
                verb: "read".into(),
                target_resource: "Patient/P-892".into(),
            },
            prior_state: None,
            input_content: None,
            approval_status: None,
            justification: None,
            expected: Expected {
                decision: Decision::Deny,
                audit_required: true,
                content_clean: None,
            },
        }
    }

    #[tokio::test]
    async fn test_trivial_deny_adapter() {
        let adapter = workspace_root().join("examples/trivial_deny_adapter.py");
        let scenario = sample_scenario();

        let run = run_adapter(&adapter, &scenario, 5_000)
            .await
            .expect("adapter should succeed");

        assert_eq!(run.result.decision, Decision::Deny);
        assert_eq!(run.result.audit_entries.len(), 1);
        let entry = &run.result.audit_entries[0];
        assert_eq!(entry.actor.as_deref(), Some("ward_nurse"));
        assert_eq!(entry.action.as_deref(), Some("read"));
        assert_eq!(entry.resource.as_deref(), Some("Patient/P-892"));
        assert_eq!(entry.reason.as_deref(), Some("baseline: deny all"));
        assert!(!run.result.execution_halted);
        assert!(!run.result.human_notified);
        assert!(run.latency_ms < 5_000);
    }

    #[tokio::test]
    async fn test_trivial_allow_adapter() {
        let adapter = workspace_root().join("examples/trivial_allow_adapter.py");
        let scenario = sample_scenario();

        let run = run_adapter(&adapter, &scenario, 5_000)
            .await
            .expect("adapter should succeed");

        assert_eq!(run.result.decision, Decision::Allow);
        assert!(run.result.audit_entries.is_empty());
        assert!(!run.result.execution_halted);
    }

    #[tokio::test]
    async fn test_adapter_timeout() {
        // Use a script that sleeps longer than the timeout
        // We can simulate by passing a non-existent adapter with 1ms timeout
        // But a cleaner approach: write a temp script that sleeps
        use std::io::Write;
        let dir = std::env::temp_dir();
        let script = dir.join("sleep_adapter.py");
        let mut f = std::fs::File::create(&script).unwrap();
        writeln!(f, "import time, json, sys").unwrap();
        writeln!(f, "time.sleep(10)").unwrap();
        writeln!(f, "print(json.dumps({{\"decision\":\"deny\",\"audit_entries\":[],\"execution_halted\":False,\"human_notified\":False,\"output_content\":None}}))").unwrap();
        drop(f);

        let scenario = sample_scenario();
        let result = run_adapter(&script, &scenario, 200).await;
        assert!(matches!(result, Err(VBError::AdapterTimeout(200))));
    }
}
