//! Timeout execution: "off-chain trigger; on-chain guard".
//!
//! Verified risk (feasibility report R1): multi-node timer semantics for
//! `TriggerMode::Once(ms)` are undocumented (who fires, restart dedup, latency).
//! Therefore the PRIMARY design never depends on trigger correctness:
//!
//!   watcher (any node, instance fn) scans deals -> submits `claim_timeout`
//!   -> network guard re-derives eligibility from consensus state and time.
//!
//! Duplicate/late/racing watcher submissions are harmless: the guard is
//! idempotent (Funded-only, terminal-safe). The native `trigger!` /
//! `TriggerMode::Once` registration below is an OPTIMIZATION to be enabled
//! after SPIKE(W1-1) proves its semantics on the 4-node devnet with
//! kill/restart tests.
//!
//! Watcher sources, in preference order:
//!   1. instance trigger on this node (if spike OK),
//!   2. an agent-side keeper loop (scripts/keeper.py) hammering the HTTP API,
//!   3. any third party — the claim is permissionless by design.

use crate::types::DealId;

/// Instance watcher body: fetch due deals via the network getter and submit
/// claims for each. Ledger effects are zero when the guard rejects — safe to
/// re-run, safe to run on every node.
// TODO(W2): wire to the real instance-call + cross-call surface:
//   let due = call!(self, due_deals(now))?;
//   for id in due { call!(self, claim_timeout(id))?; }
pub fn watcher_step(current_slot: u64) -> Vec<DealId> {
    // Placeholder: real body calls the `due_deals` network fn then submits.
    // Pure scan logic itself is already tested in core::due_for_timeout.
    let _ = current_slot;
    Vec::new()
}

/// Spike #1 registration sketch (enable only after W1 verification):
///
///   // in an instance init or start method:
///   trigger!(
///       "trustbridge-watcher",
///       "watcher_step",
///       vec![],
///       TriggerMode::Recurrent(5_000) // every 5s
///   )?;
///
/// SPIKE(W1-1) acceptance: on the 4-node devnet, with a deal past deadline,
/// (a) exactly one refund lands (guard dedups), (b) killing/restarting nodes
/// never double-refunds, (c) firing latency < 2x the trigger period.
pub const SPIKE_1_TRIGGER_REGISTRATION: &str = "see doc comment above";
