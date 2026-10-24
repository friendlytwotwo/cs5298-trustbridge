//! W1-B1 platform mechanism probes.
//!
//! Purpose: exercise two undocumented platform behaviors on the 4-node multi
//! devnet, with every conclusion archived under `workflow-out/w1b1-*.md`:
//!   - `s1_timer`  — `TriggerMode::Once(ms)` semantics (fires-once? restart
//!     dedup? latency?) — verdict feeds the S1 conclusion table and the
//!     `timeout.rs` SPIKE_1 markers (native trigger vs keeper mode).
//!   - `s2_oracle` — a full committee certification round (`propose_and_certify`
//!     + `set_threshold`), pinned on the real shape of `ctx.cert.signers`.
//!
//! Discipline (W1 SPIKE rule, user ruling 3 in W1-A): each assumption is
//! either verified and rewritten as a conclusion with its evidence, or left
//! marked. Probe code is additive-only: it shares the crate's `state!` block
//! (fields prefixed `probe_`; R1-verified — a submodule `state!` does NOT
//! compile, see `workflow-out/_w1b1-r1-submodule-state-check.txt`) but never
//! touches the escrow methods, the access matrix, or `types.rs`/`core.rs`.
//! Probes are demo-tier scaffolding: they carry no escrow funds logic and are
//! expected to be removed or explicitly retired at W2.

pub mod s1_timer;
pub mod s2_oracle;
