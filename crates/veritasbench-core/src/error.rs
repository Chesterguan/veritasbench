use thiserror::Error;

#[derive(Debug, Error)]
pub enum VBError {
    #[error("scenario parse error: {0}")]
    ScenarioParse(#[from] serde_json::Error),
    /// Transient adapter error (network blip, 5xx, etc.) — retried by the runner.
    #[error("adapter error: {0}")]
    Adapter(String),
    /// Non-retryable adapter error (auth, config, schema, missing model) — not retried.
    #[error("adapter fatal error (not retried): {0}")]
    AdapterFatal(String),
    #[error("adapter timeout after {0}ms")]
    AdapterTimeout(u64),
    #[error("suite not found: {0}")]
    SuiteNotFound(String),
    #[error("scenario file too large: {path} is {size} bytes (max {max})")]
    ScenarioTooLarge { path: String, size: u64, max: u64 },
    #[error("io error: {0}")]
    Io(#[from] std::io::Error),
    #[error("report error: {0}")]
    Report(String),
}

impl VBError {
    /// Whether the runner should retry this error. Only transient `Adapter` errors retry;
    /// timeouts, fatal adapter errors, and programmer/IO errors do not.
    pub fn is_retryable(&self) -> bool {
        matches!(self, VBError::Adapter(_))
    }
}
