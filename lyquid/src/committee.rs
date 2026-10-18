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
use crate::core;

/// Wire format for a verdict submitted to `apply_committee_verdict`.
/// `signers` are committee member ids; `verdict` is 0=Fulfilled,1=NotFulfilled,2=Malicious.
pub struct CommitteeCertWire {
    pub verdict_code: u8,
    pub signers: Vec<AgentId>,
}

impl CommitteeCertWire {
    pub fn into_domain(self, entries: &[EvidenceEntry]) -> CommitteeCert {
        let verdict = match self.verdict_code {
            0 => Verdict::Fulfilled,
            1 => Verdict::NotFulfilled,
            _ => Verdict::Malicious,
        };
        CommitteeCert {
            verdict,
            signers: self.signers,
            // SPIKE(W1): 委员会成员实际检视的证据集假定与 network evidence_log 完全一致；root 折叠唯一定义在 core::evidence_root（读-算-校同源，阶段3b 契约替换）。
            evidence_root: core::evidence_root(entries),
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

#[cfg(test)]
mod tests {
    use super::*;

    /// Minimal well-formed Deal for shape tests. Pure types, no platform dep.
    fn shape_deal(deliverable: Option<Digest>) -> Deal {
        Deal {
            id: "deal-1".into(),
            buyer: "buyer".into(),
            seller: "seller".into(),
            broker: "broker".into(),
            amount: 1_000,
            fee_bps: 100,
            terms_digest: "terms".into(),
            acceptance_digest: "acceptance".into(),
            est_duration_ms: 60_000,
            est_confidence: 40,
            timeout_slots: 300,
            created_slot: 0,
            funded_slot: Some(1),
            state: DealState::Submitted,
            deliverable_digest: deliverable,
            committee_cert: None,
            dispute_reason: None,
        }
    }

    fn entry(seq: u64, from: &str, to: &str, payload: &str) -> EvidenceEntry {
        EvidenceEntry {
            seq,
            from: from.into(),
            to: to.into(),
            payload_digest: payload.into(),
            slot: seq,
        }
    }

    #[test]
    fn shape_accepts_acceptance_pair_plus_deliverable() {
        // 卖家→买家条目 + 条目 payload == 已提交 deliverable_digest -> true。
        let deal = shape_deal(Some("digest-1".into()));
        let entries = vec![
            entry(0, "buyer", "seller", "offer"),
            entry(1, "seller", "buyer", "digest-1"),
        ];
        assert!(check_evidence_shape(&entries, &deal));
    }

    #[test]
    fn shape_rejects_when_no_deliverable_submitted() {
        // deal.deliverable_digest == None -> None 臂直接 false
        //（committee.rs 的 `None => false`，即使证据链本身成形）。
        let deal = shape_deal(None);
        let entries = vec![entry(0, "seller", "buyer", "digest-1")];
        assert!(!check_evidence_shape(&entries, &deal));
    }

    #[test]
    fn shape_rejects_when_no_seller_to_buyer_entry() {
        // 缺卖家→买家方向的条目（只有买家→卖家）-> has_acceptance 为 false。
        let deal = shape_deal(Some("digest-1".into()));
        let entries = vec![
            entry(0, "buyer", "seller", "digest-1"), // 方向反了
            entry(1, "buyer", "seller", "other"),
        ];
        assert!(!check_evidence_shape(&entries, &deal));
    }

    #[test]
    fn into_domain_root_matches_core_fold() {
        // G15: 路径统一钉死（阶段3b D4）——committee 侧证书根必须恒等于
        // core::evidence_root 同输入的输出（唯一定义点，committee 不带副本），
        // 且顺序敏感性与 core 侧一致地传播。
        let wire = || CommitteeCertWire {
            verdict_code: 0, // Fulfilled；本测试只关心 evidence_root
            signers: vec!["n1".into(), "n2".into(), "n3".into()],
        };
        let e1 = entry(1, "alice", "bob", "deadbeef");
        let e2 = entry(2, "bob", "alice", "cafebabe");

        let empty: Vec<EvidenceEntry> = Vec::new();
        assert_eq!(wire().into_domain(&empty).evidence_root, core::evidence_root(&empty));
        let one = vec![e1.clone()];
        assert_eq!(wire().into_domain(&one).evidence_root, core::evidence_root(&one));
        let two = vec![e1.clone(), e2.clone()];
        assert_eq!(wire().into_domain(&two).evidence_root, core::evidence_root(&two));
        // 顺序敏感性传播：置换切片后 committee 侧根同样相异。
        let perm = vec![e2.clone(), e1.clone()];
        assert_ne!(
            wire().into_domain(&perm).evidence_root,
            core::evidence_root(&[e1, e2])
        );
    }
}
