//! Domain types for TrustBridge.
//!
//! Deliberately free of Lyquid/platform imports so the whole domain layer
//! (`types` + `core`) unit-tests with plain `cargo test` and survives SDK churn.

use std::collections::HashMap;

/// Agent identifier. In the demo this is a stable string (e.g. "agent-alice");
/// in the interop story it maps to an ERC-8004 agent id.
pub type AgentId = String;
/// Deal identifier (agent-supplied uuid-ish string).
pub type DealId = String;
/// Lowercase hex sha256 digest of a canonicalized message payload.
/// Digest format aligns with the x402 Foundation "delivery-receipt attestation"
/// proposal (#2833): sha256 fingerprints of the exact request/response payloads.
pub type Digest = String;

/// Demo parameter: slot length of the devnet consensus. SPIKE(W1): read the
/// real value from the node config and replace this constant.
pub const SLOT_MS: u64 = 400;

/// Safety factor applied to the LLM's p90 duration estimate when converting to
/// an on-chain timeout. 2x keeps refunds conservative (buyer-favoring slack).
pub const TIMEOUT_SAFETY_FACTOR: u64 = 2;

/// Deal lifecycle. Terminal states are `Settled` and `Refunded`; nothing may
/// transition out of a terminal state (enforced in `core`).
///
/// Design note (from the architecture-review PDF's model-checking lesson):
/// automatic timeout refunds are only legal from `Funded` — i.e. before ANY
/// deliverable evidence exists. Once evidence is submitted, money can only move
/// via buyer consent (`complete`) or a committee verdict. This kills the whole
/// "cancel vs late-evidence" race class (1,017/10,080 violating orderings there).
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum DealState {
    /// Created by the broker with terms + LLM-derived timeout; not yet funded.
    Qualified,
    /// Buyer escrowed `amount`; the timeout clock starts at `funded_slot`.
    Funded,
    /// Seller submitted a deliverable digest; awaiting completion or verdict.
    Submitted,
    /// A party opened a dispute; funds frozen until committee verdict.
    Disputed,
    /// Terminal: paid out (seller proceeds + broker fee).
    Settled,
    /// Terminal: buyer refunded in full (timeout / cancel / verdict).
    Refunded,
}

impl DealState {
    pub fn is_terminal(&self) -> bool {
        matches!(self, DealState::Settled | DealState::Refunded)
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Verdict {
    /// Evidence satisfies the acceptance criteria -> pay the seller.
    Fulfilled,
    /// Deliverable does not satisfy criteria -> refund the buyer.
    NotFulfilled,
    /// Fabricated / manipulated evidence -> refund buyer + record misconduct.
    Malicious,
}

/// Committee verdict certificate. Demo trust model: signers must be members of
/// the on-chain committee set and |signers| >= threshold. Production path is the
/// oracle certified-call flow (`propose_and_certify`, `ctx.cert.signers`) — see
/// `committee.rs`.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CommitteeCert {
    pub verdict: Verdict,
    /// Distinct committee member ids that signed this verdict.
    pub signers: Vec<AgentId>,
    /// Merkle/root digest over the evidence entries the verdict was based on.
    pub evidence_root: Digest,
}

/// One notarized message in a deal's communication trace. Append-only,
/// sequence-enforced; `payload_digest` is computed client-side (agents hash
/// canonical JSON) so the chain only stores and orders digests.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct EvidenceEntry {
    pub seq: u64,
    pub from: AgentId,
    pub to: AgentId,
    pub payload_digest: Digest,
    pub slot: u64,
}

#[derive(Clone, Debug)]
pub struct Deal {
    pub id: DealId,
    pub buyer: AgentId,
    pub seller: AgentId,
    pub broker: AgentId,
    /// Escrowed amount in internal ledger units (demo token, 18-dec-ish).
    pub amount: u128,
    /// Broker fee in basis points, charged only on successful settlement.
    pub fee_bps: u16,
    /// sha256 of the agreed license terms document (scope, media, territory).
    pub terms_digest: Digest,
    /// sha256 of the acceptance criteria the committee verifies against.
    pub acceptance_digest: Digest,
    /// LLM p90 estimate (ms) for the whole fulfillment, from `assessor`.
    pub est_duration_ms: u64,
    pub est_confidence: u8,
    /// On-chain timeout, in slots, counted from `funded_slot`.
    pub timeout_slots: u64,
    pub created_slot: u64,
    pub funded_slot: Option<u64>,
    pub state: DealState,
    pub deliverable_digest: Option<Digest>,
    pub committee_cert: Option<CommitteeCert>,
    pub dispute_reason: Option<Digest>,
}

impl Deal {
    /// Absolute deadline in slots. `None` until funded (clock starts at funding).
    pub fn deadline_slot(&self) -> Option<u64> {
        self.funded_slot.map(|f| f + self.timeout_slots)
    }

    /// Fee split charged on settlement. Conservation invariant checked in tests.
    pub fn split(&self) -> (u128, u128) {
        let fee = self.amount * self.fee_bps as u128 / 10_000;
        (self.amount - fee, fee) // (to_seller, fee_to_broker)
    }
}

/// Output of any money-moving transition. `total()` must equal `deal.amount`.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Payout {
    pub to_seller: u128,
    pub fee_to_broker: u128,
    pub refund_to_buyer: u128,
    pub slash_to_treasury: u128,
}

impl Payout {
    pub fn full_refund(amount: u128) -> Self {
        Payout { to_seller: 0, fee_to_broker: 0, refund_to_buyer: amount, slash_to_treasury: 0 }
    }
    pub fn settle(amount: u128, fee_bps: u16) -> Self {
        let fee = amount * fee_bps as u128 / 10_000;
        Payout {
            to_seller: amount - fee,
            fee_to_broker: fee,
            refund_to_buyer: 0,
            slash_to_treasury: 0,
        }
    }
    pub fn total(&self) -> u128 {
        self.to_seller + self.fee_to_broker + self.refund_to_buyer + self.slash_to_treasury
    }
}

/// Per-agent reputation hook (misconduct counter). Feeds the report's
/// "trust assumptions" section; intentionally minimal for the demo.
pub type MisconductLog = HashMap<AgentId, u32>;

/// LLM assessment report produced by the instance-side assessor. Only its
/// digest is promoted to network state (two-step pattern: instance computes,
/// network call commits).
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct AssessmentReport {
    pub qualification_score: u8, // 0-100, buyer qualification
    pub risks: Vec<String>,
    pub est_duration_ms: u64, // p90 estimate
    pub est_confidence: u8,   // 0-100
}

/// Convert an assessment into on-chain timeout slots.
pub fn timeout_slots_from_estimate(est_ms: u64) -> u64 {
    (est_ms.saturating_mul(TIMEOUT_SAFETY_FACTOR)) / SLOT_MS
}
