//! VeritasBench — Longitudinal (temporal) governance suite.
//!
//! VeritasBench-core evaluates a *single* governance decision on a static scenario
//! (allow/deny/audit/halt). This crate adds the **temporal axis** that core's
//! `prior_state` / `UnsafeActionSequence` only gestured at: a real generative model
//! reconciles a patient's medications over a **sequence of visits** whose clinical
//! state evolves, its own orders persist into the next visit, and an **authoritative
//! clinical oracle** (Beers 2023 / STOPP-START v3 / FDA, cited per rule) judges whether
//! an unsafe order reaches the patient. Two arms (governed / ungoverned) quantify what
//! an external high-alert gate prevents.
//!
//! It reuses `veritasbench-core` clinical types (`PriorState`, `LabResult`, `Condition`)
//! as the per-visit state, so it sits under the same benchmark umbrella rather than
//! duplicating the data model.

pub mod oracle;
pub mod runner;

use serde::{Deserialize, Serialize};
use veritasbench_core::scenario::{Difficulty, PriorState};

/// `PriorState` has no upstream `Default`; build an empty one for serde defaults.
pub(crate) fn empty_prior_state() -> PriorState {
    serde_json::from_str("{}").expect("empty prior_state is valid")
}

/// A patient seen over a sequence of visits — the temporal scenario unit.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LongitudinalScenario {
    pub id: String,
    #[serde(default = "default_version")]
    pub version: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub difficulty: Option<Difficulty>,
    pub patient: PatientHeader,
    /// Medications the patient arrives on (the starting list).
    pub baseline_meds: Vec<String>,
    /// One entry per visit; labs/conditions evolve across the sequence.
    pub visits: Vec<Visit>,
}

fn default_version() -> String {
    "0.1.0".into()
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PatientHeader {
    pub age: u32,
    pub sex: String,
    #[serde(default)]
    pub baseline_conditions: Vec<String>,
}

/// One visit: the clinical state the model sees, reusing core's `PriorState`
/// (labs, conditions, allergies, patient context, active orders).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Visit {
    #[serde(default = "empty_prior_state")]
    pub state: PriorState,
}

/// Per-arm outcome for one model run over a suite.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SuiteResult {
    pub model: String,
    pub seeds: usize,
    pub scenarios: usize,
    /// Unsafe orders that reached the patient — ungoverned arm.
    pub gate_off_unsafe: usize,
    /// Unsafe orders that reached the patient — governed (high-alert gate) arm.
    pub gate_on_unsafe: usize,
    pub veritas_prevented: usize,
    pub high_alert_held: usize,
    pub parse_fail: usize,
    pub per_scenario: Vec<ScenarioOutcome>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScenarioOutcome {
    pub id: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub difficulty: Option<Difficulty>,
    pub gate_off_unsafe: usize,
    pub gate_on_unsafe: usize,
}
