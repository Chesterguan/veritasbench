use thiserror::Error;

#[derive(Debug, Error)]
pub enum VBError {
    #[error("scenario parse error: {0}")]
    ScenarioParse(#[from] serde_json::Error),
    #[error("adapter error: {0}")]
    Adapter(String),
    #[error("adapter timeout after {0}ms")]
    AdapterTimeout(u64),
    #[error("suite not found: {0}")]
    SuiteNotFound(String),
    #[error("io error: {0}")]
    Io(#[from] std::io::Error),
    #[error("report error: {0}")]
    Report(String),
}
