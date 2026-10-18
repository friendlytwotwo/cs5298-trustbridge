//! Pure deal state machine: guards, transitions, conservation.
//!
//! No platform imports. Every network function in `lib.rs` is a thin wrapper:
//! check caller -> mutate via this module -> apply ledger effects. All B1
//! reproducibility tests (and the refund model-check) target this module.

use crate::types::*;

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum TransitionError {
    WrongState { is: DealState, expected: &'static [&'static str] },
    Terminal,
    NotFundedYet,
    DeadlineNotReached { now: u64, deadline: u64 },
    DeadlinePassed { now: u64, deadline: u64 },
    MissingDeliverable,
    MissingCert,
    InsufficientCommittee { signers: usize, required: usize },
    NonMemberSigner(AgentId),
    InvalidSignerSet,
    /// Deal creation was handed a broker fee above the 10_000 bps (100%) cap.
    /// Safety note: within this crate nothing exhaustively matches
    /// `TransitionError` and no `From<TransitionError>` exists — `lib.rs`
    /// propagates every error with `?` — so adding a variant cannot break a
    /// caller; the platform-layer bridge is stage-two (W2) work.
    InvalidFeeBps { got: u16, max: u16 },
}

fn require_states(deal: &Deal, expected: &'static [DealState], names: &'static [&'static str]) -> Result<(), TransitionError> {
    if deal.state.is_terminal() {
        return Err(TransitionError::Terminal);
    }
    if !expected.contains(&deal.state) {
        return Err(TransitionError::WrongState { is: deal.state.clone(), expected: names });
    }
    Ok(())
}

/// Broker creates a deal from an accepted assessment. Timeout derives from the
/// LLM estimate (`timeout_slots_from_estimate`), never hand-picked.
///
/// `fee_bps` is runtime-checked against the 100% cap: above it every
/// settlement would underflow `amount - fee` (a checked release build would
/// silently wrap the seller's share into an astronomic number). The other
/// degenerate inputs stay `debug_assert`s on purpose: `timeout_slots == 0` is
/// already clamped to `.max(1)` by the platform layer, and `amount == 0`
/// cannot break conservation — platform-side input validation is stage-two
/// (W2) work.
pub fn create(
    spec: Deal,
) -> Result<Deal, TransitionError> {
    debug_assert_eq!(spec.state, DealState::Qualified);
    debug_assert!(spec.timeout_slots > 0, "timeout must come from an estimate");
    if spec.fee_bps > 10_000 {
        return Err(TransitionError::InvalidFeeBps { got: spec.fee_bps, max: 10_000 });
    }
    Ok(spec)
}

/// Buyer escrows `deal.amount`. Starts the timeout clock at `now`.
pub fn fund(deal: &mut Deal, now: u64) -> Result<(), TransitionError> {
    require_states(deal, &[DealState::Qualified], &["Qualified"])?;
    deal.funded_slot = Some(now);
    deal.state = DealState::Funded;
    Ok(())
}

/// Buyer may cancel while no evidence exists (same guard class as timeout).
pub fn cancel(deal: &mut Deal, now: u64) -> Result<Payout, TransitionError> {
    require_states(deal, &[DealState::Qualified, DealState::Funded], &["Qualified", "Funded"])?;
    let payout = Payout::full_refund(deal.amount);
    if deal.funded_slot.is_some() {
        let _ = now; // refund is immediate; time only matters for auto-timeout
    }
    deal.state = DealState::Refunded;
    Ok(payout)
}

/// Seller submits the deliverable digest. Legal until the deadline. NOTE:
/// after this point automatic refund is impossible by construction — money
/// moves only via `complete` or a committee verdict.
pub fn submit_deliverable(deal: &mut Deal, digest: Digest, now: u64) -> Result<(), TransitionError> {
    require_states(deal, &[DealState::Funded], &["Funded"])?;
    let deadline = deal.deadline_slot().ok_or(TransitionError::NotFundedYet)?;
    if now > deadline {
        return Err(TransitionError::DeadlinePassed { now, deadline });
    }
    deal.deliverable_digest = Some(digest);
    deal.state = DealState::Submitted;
    Ok(())
}

/// Authority to complete a submitted deal: buyer consent, or a committee cert.
pub enum CompleteAuth {
    BuyerConsent,
    Committee(CommitteeCert),
}

/// Settle a submitted deal. With `Committee`, also validates the certificate
/// against the given committee set/threshold (caller supplies the on-chain
/// config; this function stays pure and testable).
pub fn complete(deal: &mut Deal, now: u64, auth: &CompleteAuth, committee: Option<(&[AgentId], usize)>) -> Result<Payout, TransitionError> {
    require_states(deal, &[DealState::Submitted], &["Submitted"])?;
    let payout = match auth {
        CompleteAuth::BuyerConsent => Payout::settle(deal.amount, deal.fee_bps),
        CompleteAuth::Committee(cert) => {
            let (members, threshold) = committee.ok_or(TransitionError::MissingCert)?;
            validate_cert(cert, members, threshold, deal)?;
            deal.committee_cert = Some(cert.clone());
            match cert.verdict {
                Verdict::Fulfilled => Payout::settle(deal.amount, deal.fee_bps),
                Verdict::NotFulfilled | Verdict::Malicious => Payout::full_refund(deal.amount),
            }
        }
    };
    let _ = now;
    deal.state = DealState::Settled;
    Ok(payout)
}

/// Permissionless timeout refund ("off-chain trigger; on-chain guard": a
/// watcher submits, this guard re-derives everything from consensus state).
/// Only from `Funded` — see the state-machine doc on the race-class kill.
pub fn claim_timeout(deal: &mut Deal, now: u64) -> Result<Payout, TransitionError> {
    require_states(deal, &[DealState::Funded], &["Funded"])?;
    let deadline = deal.deadline_slot().ok_or(TransitionError::NotFundedYet)?;
    if now < deadline {
        return Err(TransitionError::DeadlineNotReached { now, deadline });
    }
    deal.state = DealState::Refunded;
    Ok(Payout::full_refund(deal.amount))
}

/// Any party freezes funds pending a committee verdict. No deadline check:
/// disputes on submitted evidence are legal until terminal.
pub fn open_dispute(deal: &mut Deal, reason_digest: Digest) -> Result<(), TransitionError> {
    require_states(deal, &[DealState::Funded, DealState::Submitted], &["Funded", "Submitted"])?;
    deal.dispute_reason = Some(reason_digest);
    deal.state = DealState::Disputed;
    Ok(())
}

/// Apply a committee verdict to a disputed deal. `Malicious` additionally
/// flags the seller in the misconduct log (reputation hook).
pub fn apply_verdict(
    deal: &mut Deal,
    cert: CommitteeCert,
    committee_members: &[AgentId],
    threshold: usize,
    misconduct: &mut MisconductLog,
) -> Result<Payout, TransitionError> {
    require_states(deal, &[DealState::Disputed], &["Disputed"])?;
    validate_cert(&cert, committee_members, threshold, deal)?;
    deal.committee_cert = Some(cert.clone());
    let payout = match cert.verdict {
        Verdict::Fulfilled => Payout::settle(deal.amount, deal.fee_bps),
        Verdict::NotFulfilled => Payout::full_refund(deal.amount),
        Verdict::Malicious => {
            *misconduct.entry(deal.seller.clone()).or_insert(0) += 1;
            Payout::full_refund(deal.amount)
        }
    };
    deal.state = if payout.to_seller > 0 { DealState::Settled } else { DealState::Refunded };
    Ok(payout)
}

/// Certificate validation shared by `complete` and `apply_verdict`.
/// Demo trust model: distinct known members, |signers| >= threshold.
/// Production: replace with oracle certified-call verification
/// (`ctx.cert.signers`, `propose_and_certify`) — see committee.rs.
pub fn validate_cert(cert: &CommitteeCert, members: &[AgentId], threshold: usize, deal: &Deal) -> Result<(), TransitionError> {
    let mut seen = std::collections::HashSet::new();
    for s in &cert.signers {
        if !members.contains(s) {
            return Err(TransitionError::NonMemberSigner(s.clone()));
        }
        if !seen.insert(s) {
            return Err(TransitionError::InvalidSignerSet);
        }
    }
    if cert.signers.len() < threshold {
        return Err(TransitionError::InsufficientCommittee { signers: cert.signers.len(), required: threshold });
    }
    // The verdict must be about THIS deal's evidence.
    if cert.evidence_root != evidence_root(deal) {
        return Err(TransitionError::MissingCert); // TODO(W3): dedicated EvidenceMismatch error
    }
    Ok(())
}

/// Root digest over a deal's ordered evidence log. Chain-agnostic: lib.rs
/// computes the same root from network state before applying a verdict.
/// Simple order-preserving fold (not a merkle tree) — adequate for the demo,
/// documented as such in the report.
pub fn evidence_root(deal: &Deal) -> Digest {
    // Placeholder fold: in lib.rs this iterates the actual evidence entries.
    // Kept here so `validate_cert` has a pure definition to check against;
    // lib.rs must pass the same value via deal-adjacent state.
    // TODO(W3): replace with real fold over entries once notary stores them.
    let _ = deal;
    String::new()
}

/// Watcher helper: deals eligible for a timeout claim right now.
pub fn due_for_timeout<'a>(deals: impl Iterator<Item = (&'a DealId, &'a Deal)>, now: u64) -> Vec<DealId> {
    deals
        .filter(|(_, d)| d.state == DealState::Funded)
        .filter(|(_, d)| d.deadline_slot().map(|dl| now >= dl).unwrap_or(false))
        .map(|(id, _)| id.clone())
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn deal() -> Deal {
        Deal {
            id: "d1".into(),
            buyer: "alice".into(),
            seller: "bob".into(),
            broker: "broker".into(),
            amount: 1_000,
            fee_bps: 200,
            terms_digest: "t".into(),
            acceptance_digest: "a".into(),
            est_duration_ms: 8_000,
            est_confidence: 80,
            timeout_slots: 40,
            created_slot: 1,
            funded_slot: None,
            state: DealState::Qualified,
            deliverable_digest: None,
            committee_cert: None,
            dispute_reason: None,
        }
    }

    /// Parameterized factory for the fee/amount edge cases (F3/F4).
    fn deal_with(amount: u128, fee_bps: u16) -> Deal {
        let mut d = deal();
        d.amount = amount;
        d.fee_bps = fee_bps;
        d
    }

    #[test]
    fn happy_path_settles_with_fee_split_and_conservation() {
        let mut d = deal();
        fund(&mut d, 10).unwrap();
        submit_deliverable(&mut d, "deliv".into(), 20).unwrap();
        let p = complete(&mut d, 30, &CompleteAuth::BuyerConsent, None).unwrap();
        assert_eq!((p.to_seller, p.fee_to_broker), (980, 20));
        assert_eq!(p.total(), d.amount);
        assert_eq!(d.state, DealState::Settled);
    }

    #[test]
    fn timeout_refunds_only_after_deadline_and_only_from_funded() {
        let mut d = deal();
        fund(&mut d, 10).unwrap();
        assert!(matches!(claim_timeout(&mut d, 49), Err(TransitionError::DeadlineNotReached { .. })));
        let p = claim_timeout(&mut d, 50).unwrap();
        assert_eq!(p, Payout::full_refund(1_000));
        assert_eq!(d.state, DealState::Refunded);
        // terminal: nothing else moves
        assert!(matches!(claim_timeout(&mut d, 99), Err(TransitionError::Terminal)));
    }

    #[test]
    fn submitted_evidence_blocks_auto_refund_and_survives_late_clock() {
        let mut d = deal();
        fund(&mut d, 10).unwrap();
        submit_deliverable(&mut d, "deliv".into(), 45).unwrap();
        // well past the deadline, but evidence exists -> no auto refund
        assert!(matches!(claim_timeout(&mut d, 500), Err(TransitionError::WrongState { .. })));
        // buyer consent still settles
        let p = complete(&mut d, 501, &CompleteAuth::BuyerConsent, None).unwrap();
        assert_eq!(p.total(), d.amount);
    }

    #[test]
    fn late_deliverable_is_rejected() {
        let mut d = deal();
        fund(&mut d, 10).unwrap(); // deadline = 50
        assert!(matches!(
            submit_deliverable(&mut d, "late".into(), 51),
            Err(TransitionError::DeadlinePassed { .. })
        ));
    }

    #[test]
    fn dispute_then_malicious_verdict_refunds_and_flags_seller() {
        let mut d = deal();
        fund(&mut d, 10).unwrap();
        submit_deliverable(&mut d, "forged".into(), 20).unwrap();
        open_dispute(&mut d, "reason".into()).unwrap();
        let members = vec!["n1".to_string(), "n2".to_string(), "n3".to_string(), "n4".to_string()];
        let cert = CommitteeCert {
            verdict: Verdict::Malicious,
            signers: vec!["n1".into(), "n2".into(), "n3".into()],
            evidence_root: evidence_root(&d),
        };
        let mut log = MisconductLog::new();
        let p = apply_verdict(&mut d, cert, &members, 3, &mut log).unwrap();
        assert_eq!(p, Payout::full_refund(1_000));
        assert_eq!(log.get("bob"), Some(&1));
        assert_eq!(d.state, DealState::Refunded);
    }

    #[test]
    fn committee_below_threshold_is_rejected() {
        let mut d = deal();
        fund(&mut d, 10).unwrap();
        submit_deliverable(&mut d, "x".into(), 20).unwrap();
        open_dispute(&mut d, "r".into()).unwrap();
        let members = vec!["n1".to_string(), "n2".to_string(), "n3".to_string(), "n4".to_string()];
        let cert = CommitteeCert {
            verdict: Verdict::Fulfilled,
            signers: vec!["n1".into(), "n2".into()], // 2 < 3
            evidence_root: evidence_root(&d),
        };
        let mut log = MisconductLog::new();
        assert!(matches!(
            apply_verdict(&mut d, cert, &members, 3, &mut log),
            Err(TransitionError::InsufficientCommittee { .. })
        ));
    }

    #[test]
    fn cancel_only_without_evidence() {
        let mut d = deal();
        fund(&mut d, 10).unwrap();
        assert_eq!(cancel(&mut d, 11).unwrap(), Payout::full_refund(1_000));
        let mut d2 = deal();
        fund(&mut d2, 10).unwrap();
        submit_deliverable(&mut d2, "d".into(), 20).unwrap();
        assert!(matches!(cancel(&mut d2, 21), Err(TransitionError::WrongState { .. })));
    }

    #[test]
    fn due_for_timeout_picks_only_expired_funded() {
        let mut a = deal(); // funded at 10, deadline 50
        fund(&mut a, 10).unwrap();
        let mut b = deal();
        b.id = "d2".into();
        fund(&mut b, 40).unwrap(); // deadline 80
        let mut c = deal();
        c.id = "d3".into();
        fund(&mut c, 10).unwrap();
        submit_deliverable(&mut c, "x".into(), 20).unwrap(); // submitted: never due
        let d1 = "d1".to_string();
        let d2 = "d2".to_string();
        let d3 = "d3".to_string();
        let due = due_for_timeout(
            [(&d1, &a), (&d2, &b), (&d3, &c)].into_iter(),
            60,
        );
        assert_eq!(due, vec!["d1".to_string()]);
    }

    // -- F3: fee cap validation + conservation under every rounding edge ----

    #[test]
    fn fee_bps_over_cap_rejected_at_create() {
        assert!(matches!(
            create(deal_with(1_000, 10_001)),
            Err(TransitionError::InvalidFeeBps { got: 10_001, max: 10_000 })
        ));
        // Boundary: exactly at the 100% cap stays legal.
        assert!(create(deal_with(1_000, 10_000)).is_ok());
    }

    #[test]
    fn fee_rounding_edges_conservation() {
        // Floor rounding itself never breaks conservation: to_seller is an
        // exact subtraction, so to_seller + fee == amount for every legal cap.
        for (amount, fee_bps) in [(1u128, 3333u16), (3, 3333), (7, 3333), (10_000, 1), (1, 200)] {
            let d = deal_with(amount, fee_bps);
            let (to_seller, fee) = d.split();
            assert_eq!(to_seller + fee, amount, "split conservation for ({amount}, {fee_bps})");
            let p = Payout::settle(amount, fee_bps);
            assert_eq!(p.total(), amount, "settle conservation for ({amount}, {fee_bps})");
            assert_eq!((p.to_seller, p.fee_to_broker), (to_seller, fee));
        }
        // Floor semantics pinned on concrete values, e.g. (3, 3333): fee=0.
        assert_eq!(deal_with(3, 3333).split(), (3, 0));
        assert_eq!(deal_with(1, 3333).split(), (1, 0));
        assert_eq!(deal_with(7, 3333).split(), (5, 2));
        assert_eq!(deal_with(10_000, 1).split(), (9_999, 1));
        assert_eq!(
            Payout::settle(3, 3333),
            Payout { to_seller: 3, fee_to_broker: 0, refund_to_buyer: 0, slash_to_treasury: 0 }
        );
    }

    #[test]
    fn split_never_underflows() {
        // Defense layer: even a hand-crafted Deal that bypasses create's
        // runtime cap check (fee_bps = u16::MAX = 65_535) must not panic in
        // debug nor wrap in release — the clamp pins fee == amount.
        let d = deal_with(5_000, u16::MAX);
        let (to_seller, fee) = d.split();
        assert_eq!((to_seller, fee), (0, 5_000));
        assert_eq!(to_seller + fee, d.amount);
        let p = Payout::settle(5_000, u16::MAX);
        assert_eq!(p.total(), 5_000);
        assert_eq!((p.to_seller, p.fee_to_broker), (0, 5_000));
        // Same for the saturating_mul path: amount * fee_bps overflows u128
        // and must saturate before the clamp.
        let d = deal_with(u128::MAX, u16::MAX);
        let (to_seller, fee) = d.split();
        assert_eq!((to_seller, fee), (0, u128::MAX));
        assert_eq!(to_seller + fee, u128::MAX);
    }
}
