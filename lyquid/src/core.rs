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
///
/// Conservation invariant, stated precisely: summed over a deal's whole life,
/// total payouts are **at most** the escrowed amount, and any single payout
/// satisfies `p.total() == deal.amount` **iff** the deal ever reached
/// `Funded` — money can only leave escrow that was actually posted. Hence a
/// cancel from `Qualified` (nothing escrowed yet) returns the all-zero
/// payout; paying `full_refund` there would mint tokens. This mirrors the
/// FakeNode reference implementation (`agents/common/rpc.py`, `cancel`:
/// credits the buyer only `if d.state == "Funded"`). The state still moves to
/// `Refunded` so an unfunded deal can be aborted, and the platform caller is
/// unchanged: `apply_payout` is a no-op on a zero payout. `now` is kept only
/// for API symmetry with the other transitions (a Qualified deal has no
/// deadline, so time plays no role here).
pub fn cancel(deal: &mut Deal, now: u64) -> Result<Payout, TransitionError> {
    require_states(deal, &[DealState::Qualified, DealState::Funded], &["Qualified", "Funded"])?;
    let payout = if deal.funded_slot.is_some() {
        Payout::full_refund(deal.amount) // escrow was posted: refund it in full
    } else {
        Payout { to_seller: 0, fee_to_broker: 0, refund_to_buyer: 0, slash_to_treasury: 0 }
    };
    let _ = now; // API symmetry only; see doc above
    deal.state = DealState::Refunded;
    Ok(payout)
}

/// Seller submits the deliverable digest. Legal until the deadline. NOTE:
/// after this point automatic refund is impossible by construction — money
/// moves only via `complete` or a committee verdict.
///
/// Boundary semantics (intentional, pinned by
/// `deadline_boundary_double_closed_and_race_resolved` and mirrored by the
/// FakeNode, `agents/common/rpc.py`: `slot <= dl` here, `slot >= dl` in
/// `claim_timeout`): submission is legal iff `now <= deadline` and the
/// timeout claim iff `now >= deadline`, so at `now == deadline` BOTH are
/// legal — the boundary is double-closed by design. This is race-safe: the
/// two transitions start from the same state (`Funded`) but are mutually
/// exclusive once one lands, so for two same-slot transactions either
/// ordering resolves without a double payout — submit first: the deal is
/// `Submitted`, the claim gets `WrongState`; claim first: the deal is
/// terminal (`Refunded`), the submit gets `Terminal`. Terminal closure plus
/// state disjointness means no double-payout ordering exists (the model
/// check in `tests/modelcheck_refund.rs` enumerates these orderings).
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
///
/// The terminal state mirrors the outcome (F1 fix; same mapping as
/// `apply_verdict` and as the FakeNode mirror, `agents/common/rpc.py`
/// `complete`/`apply_committee_verdict`): paying the seller settles
/// (`Settled`), refunding the buyer refunds (`Refunded`). The old code marked
/// every `complete` as `Settled`, mislabelling a Committee NotFulfilled/
/// Malicious refund as a settlement.
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
    deal.state = match auth {
        CompleteAuth::BuyerConsent => DealState::Settled,
        CompleteAuth::Committee(cert) => match cert.verdict {
            Verdict::Fulfilled => DealState::Settled,
            Verdict::NotFulfilled | Verdict::Malicious => DealState::Refunded,
        },
    };
    Ok(payout)
}

/// Permissionless timeout refund ("off-chain trigger; on-chain guard": a
/// watcher submits, this guard re-derives everything from consensus state).
/// Only from `Funded` — see the state-machine doc on the race-class kill.
///
/// Boundary semantics: legal iff `now >= deadline` — the double-closed twin
/// of `submit_deliverable`'s `now <= deadline` (at `now == deadline` both are
/// legal on purpose); see the race-safety argument there.
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
    // F4 fix: map the terminal state from the verdict itself, like `complete`
    // does. The old `to_seller > 0` heuristic mislabelled a Fulfilled verdict
    // under `fee_bps == 10_000` (to_seller == 0, legal!) as `Refunded`.
    deal.state = match cert.verdict {
        Verdict::Fulfilled => DealState::Settled,
        Verdict::NotFulfilled | Verdict::Malicious => DealState::Refunded,
    };
    Ok(payout)
}

/// Certificate validation shared by `complete` and `apply_verdict`.
/// Demo trust model: distinct known members, |signers| >= threshold.
/// Production: replace with oracle certified-call verification
/// (`ctx.cert.signers`, `propose_and_certify`) — see committee.rs.
///
/// Placeholder contract (stage-three tripwire): `evidence_root(deal)` is
/// currently the empty string, so a certificate passes the evidence check
/// **only** when it carries `evidence_root == ""`. When W3 replaces the
/// placeholder with the real fold, update the pinned tests in the same
/// change: `missing_cert_paths_pinned` here and the `String::new()` in
/// `tests/modelcheck_refund.rs`. The evidence-mismatch path below reuses
/// `MissingCert` (same variant as "complete with Committee auth but no
/// committee supplied") on purpose; splitting a dedicated `EvidenceMismatch`
/// out is TODO(W3) — do not "fix" one path without the other.
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
///
/// Placeholder contract: this ALWAYS returns the empty string until W3.
/// `validate_cert` requires a certificate's `evidence_root` to equal it, so
/// empty-string roots are the only valid ones today (pinned by
/// `missing_cert_paths_pinned` and by the `String::new()` in
/// `tests/modelcheck_refund.rs`). Replacing this with the real fold
/// (TODO(W3)) must update those pinned tests in the same change.
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

    // -- F2: cancelling an unfunded deal must not mint a refund -------------

    #[test]
    fn cancel_from_qualified_pays_nothing() {
        // Before the fix, cancelling from Qualified returned
        // Payout::full_refund(amount) even though the buyer never escrowed
        // anything — the platform layer would have credited tokens out of
        // thin air (lib.rs cancel -> apply_payout).
        let mut d = deal();
        let p = cancel(&mut d, 5).unwrap();
        assert_eq!(
            p,
            Payout { to_seller: 0, fee_to_broker: 0, refund_to_buyer: 0, slash_to_treasury: 0 }
        );
        assert_eq!(p.refund_to_buyer, 0);
        assert_eq!(p.total(), 0);
        assert_eq!(d.state, DealState::Refunded); // the abort path still closes the deal
        // Funded cancel keeps its original behaviour: full refund (pinned).
        let mut funded = deal();
        fund(&mut funded, 10).unwrap();
        let p2 = cancel(&mut funded, 11).unwrap();
        assert_eq!(p2, Payout::full_refund(1_000));
        assert_eq!(funded.state, DealState::Refunded);
    }

    // -- F1/F4: the terminal state mirrors the verdict -----------------------

    #[test]
    fn complete_committee_fulfilled_settles() {
        // Long-uncovered blind spot: the Committee branch of `complete`.
        let mut d = deal();
        fund(&mut d, 10).unwrap();
        submit_deliverable(&mut d, "deliv".into(), 20).unwrap();
        let members = vec!["n1".to_string(), "n2".to_string(), "n3".to_string(), "n4".to_string()];
        let cert = CommitteeCert {
            verdict: Verdict::Fulfilled,
            signers: vec!["n1".into(), "n2".into(), "n3".into()],
            evidence_root: evidence_root(&d),
        };
        let p = complete(&mut d, 30, &CompleteAuth::Committee(cert), Some((&members, 3))).unwrap();
        assert_eq!(d.state, DealState::Settled);
        assert_eq!((p.to_seller, p.fee_to_broker), (980, 20));
        assert_eq!(p.total(), d.amount);
        assert!(d.committee_cert.is_some()); // the ruling cert is stored
    }

    #[test]
    fn complete_committee_notfulfilled_refunds_state_refunded() {
        // F1 fix proof (fails on the old code, which set Settled
        // unconditionally): a refunding Committee verdict through `complete`
        // must land the deal in Refunded, not Settled.
        let mut d = deal();
        fund(&mut d, 10).unwrap();
        submit_deliverable(&mut d, "deliv".into(), 20).unwrap();
        let members = vec!["n1".to_string(), "n2".to_string(), "n3".to_string(), "n4".to_string()];
        let cert = CommitteeCert {
            verdict: Verdict::NotFulfilled,
            signers: vec!["n1".into(), "n2".into(), "n3".into()],
            evidence_root: evidence_root(&d),
        };
        let p = complete(&mut d, 30, &CompleteAuth::Committee(cert), Some((&members, 3))).unwrap();
        assert_eq!(p, Payout::full_refund(1_000));
        assert_eq!(d.state, DealState::Refunded);
        assert_eq!(p.total(), d.amount); // conservation
        assert!(d.committee_cert.is_some());
    }

    #[test]
    fn verdict_fulfilled_full_fee_still_settled() {
        // F4 fix proof (fails on the old `to_seller > 0` heuristic):
        // fee_bps == 10_000 is legal (create accepts <= 10_000), so a
        // Fulfilled verdict pays to_seller == 0 — and must still settle.
        let mut d = deal_with(1_000, 10_000);
        fund(&mut d, 10).unwrap();
        submit_deliverable(&mut d, "deliv".into(), 20).unwrap();
        open_dispute(&mut d, "r".into()).unwrap();
        let members = vec!["n1".to_string(), "n2".to_string(), "n3".to_string(), "n4".to_string()];
        let cert = CommitteeCert {
            verdict: Verdict::Fulfilled,
            signers: vec!["n1".into(), "n2".into(), "n3".into()],
            evidence_root: evidence_root(&d),
        };
        let mut log = MisconductLog::new();
        let p = apply_verdict(&mut d, cert, &members, 3, &mut log).unwrap();
        assert_eq!(d.state, DealState::Settled);
        assert_eq!(p.to_seller, 0);
        assert_eq!(p.fee_to_broker, 1_000);
        assert_eq!(p.total(), d.amount); // conservation
    }

    // -- F5: the deadline boundary is double-closed by design, and any same-
    //    slot race between submit and claim resolves without double payout --

    #[test]
    fn deadline_boundary_double_closed_and_race_resolved() {
        // deadline = funded(10) + timeout(40) = 50.
        // (1) submit AT the boundary succeeds — never covered before.
        let mut submitted = deal();
        fund(&mut submitted, 10).unwrap();
        submit_deliverable(&mut submitted, "deliv".into(), 50).unwrap();
        assert_eq!(submitted.state, DealState::Submitted);
        // (3) ordering A resolves safely: submit first -> the claim bounces.
        assert!(matches!(
            claim_timeout(&mut submitted, 50),
            Err(TransitionError::WrongState { .. })
        ));

        // (2) claim AT the boundary succeeds (echoes the existing
        // timeout_refunds_only_after_deadline_and_only_from_funded).
        let mut claimed = deal();
        fund(&mut claimed, 10).unwrap();
        let p = claim_timeout(&mut claimed, 50).unwrap();
        assert_eq!(p, Payout::full_refund(1_000));
        assert_eq!(claimed.state, DealState::Refunded);
        // (4) ordering B resolves safely: claim first -> the submit bounces.
        assert!(matches!(
            submit_deliverable(&mut claimed, "late".into(), 50),
            Err(TransitionError::Terminal)
        ));
    }

    // -- F6: both MissingCert paths are pinned (placeholder era; W3 splits
    //    the evidence-mismatch variant out — see validate_cert docs) --------

    #[test]
    fn missing_cert_paths_pinned() {
        // Path (a): Committee auth but no committee supplied to `complete`.
        let mut d = deal();
        fund(&mut d, 10).unwrap();
        submit_deliverable(&mut d, "deliv".into(), 20).unwrap();
        let cert = CommitteeCert {
            verdict: Verdict::Fulfilled,
            signers: vec!["n1".into(), "n2".into(), "n3".into()],
            evidence_root: String::new(), // placeholder contract: must be ""
        };
        assert!(matches!(
            complete(&mut d, 30, &CompleteAuth::Committee(cert.clone()), None),
            Err(TransitionError::MissingCert)
        ));
        // The failed call must not have touched the deal; it is still
        // Submitted and ready for the next attempt below.
        assert_eq!(d.state, DealState::Submitted);
        assert!(d.committee_cert.is_none());

        // Path (b): evidence-root mismatch reuses MissingCert until W3
        // introduces EvidenceMismatch. The placeholder contract pins
        // evidence_root(deal) == "", so a non-empty root must fail.
        let members = vec!["n1".to_string(), "n2".to_string(), "n3".to_string(), "n4".to_string()];
        let mismatch = CommitteeCert { evidence_root: "nonempty".into(), ..cert };
        assert!(matches!(
            complete(&mut d, 30, &CompleteAuth::Committee(mismatch), Some((&members, 3))),
            Err(TransitionError::MissingCert)
        ));
        assert_eq!(d.state, DealState::Submitted);
        assert!(d.committee_cert.is_none());
    }
}
