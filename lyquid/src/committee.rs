//! Committee endorsement: threshold verification + oracle/UPC wiring notes.
//!
//! Two paths, one trust model:
//!
//! 1. DEMO PATH (implemented): members run an instance-side check of the deal's
//!    evidence log against the acceptance criteria, then their verdicts are
//!    aggregated into a `CommitteeCert` (signer set >= threshold) and applied
//!    via the network fn `apply_committee_verdict`, which re-validates against
//!    the on-chain committee config. `validate_cert` (core) is the single
//!    source of truth for the guard.
//!
//! 2. PRODUCTION PATH (W4/W5, E2 demo): the same endorsement rides the
//!    platform's oracle certified-call flow — `network oracle ...;`,
//!    `propose_and_certify`, `set_threshold`, `ctx.cert.signers` — exactly the
//!    machinery the official `price-feed` example exercises on a 4-node
//!    localnet (4 reporters, committee median, certification threshold).
//!    TODO(W4): port that skeleton here; keep `validate_cert` as the fallback
//!    guard so the trust story degrades gracefully, not silently.
//!
//! Honesty guardrails for the report (E3 trust-assumption table):
//! - Threshold agreement is not semantic truth: k-of-n signatures attest that
//!   k members *ran the check*, not that the check's conclusion is correct.
//! - Committee collusion is an explicit assumption (bounded by member
//!   selection + misconduct log, not eliminated).

use crate::types::*;

/// Wire format for a verdict submitted to `apply_committee_verdict`.
/// `signers` are committee member ids; `verdict` is 0=Fulfilled,1=NotFulfilled,2=Malicious.
pub struct CommitteeCertWire {
    pub verdict_code: u8,
    pub signers: Vec<AgentId>,
}

impl CommitteeCertWire {
    pub fn into_domain(self, _entries: &[EvidenceEntry]) -> CommitteeCert {
        let verdict = match self.verdict_code {
            0 => Verdict::Fulfilled,
            1 => Verdict::NotFulfilled,
            _ => Verdict::Malicious,
        };
        CommitteeCert {
            verdict,
            signers: self.signers,
            // SPIKE(W1)/TODO(W3): root over the ordered evidence log; must match
            // what the committee members actually inspected.
            evidence_root: String::new(),
        }
    }
}

/// Instance-side member check: does the evidence log satisfy the acceptance
/// criteria? Pure digest-shape checks here; the LLM-assisted semantic check
/// lives in assessor.rs (keep model inference OUT of consensus path).
///
/// 归属可信性（仲裁#3 联动）：`notarize` 的 from==caller 自署名强制在 lib.rs
/// 执行（`require`/`caller_agent` 体系），本函数的 `e.from == deal.seller`
/// 判定因此是可信的真归属，伪造 acceptance 条目无法通过共识入口。
pub fn check_evidence_shape(entries: &[EvidenceEntry], deal: &Deal) -> bool {
    // Minimum admissible trace: an offer/acceptance pair and a deliverable
    // digest matching what was submitted on-chain.
    let has_acceptance = entries.iter().any(|e| e.from == deal.seller && e.to == deal.buyer);
    match &deal.deliverable_digest {
        Some(d) => has_acceptance && entries.iter().any(|e| &e.payload_digest == d),
        None => false,
    }
}

/// Demo storage shim for the committee member set; replaced by network state /
/// oracle config once SPIKE(W1) settles Vec-in-network-state syntax.
pub fn set_members(_members: Vec<AgentId>) {
    // TODO(W2): write through to the `committee_members` network field.
}

pub fn members() -> Vec<AgentId> {
    // TODO(W2): read from network state; placeholder = 4-node localnet ids.
    //
    // 接线说明（阶段二）：network 状态（lib.rs `committee_members`，由
    // `committee_config` 写入）是校验权威源；本 shim 仅服务 instance 侧
    // 占位，lib.rs 的 `apply_committee_verdict` 已改读 network 状态，
    // 不再调用它。
    vec!["node-1".into(), "node-2".into(), "node-3".into(), "node-4".into()]
}
