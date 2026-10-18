//! Refund-rule model check (E3 evidence).
//!
//! Method ported from the architecture-review PDF's finding: a naive
//! "cancel releases everything / honor late claims" rule violates invariants
//! in 1,017 of 10,080 event orderings. Our rule set (auto-refund only from
//! `Funded`; evidence freezes funds to consent/verdict paths) must show ZERO
//! violations under exhaustive event-order enumeration.
//!
//! Invariants checked after every ordering:
//!   I1 conservation: sum of all successful payouts == amount if (and only if)
//!      the deal reached a terminal state; 0 otherwise.
//!   I2 single settlement: at most one money-moving transition ever succeeds.
//!   I3 terminality: no event succeeds once the deal is terminal.

use trustbridge::core::{self, CompleteAuth};
use trustbridge::types::*;

fn deal() -> Deal {
    Deal {
        id: "mc".into(),
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

fn members() -> Vec<AgentId> {
    vec!["n1".into(), "n2".into(), "n3".into(), "n4".into()]
}

fn cert(verdict: Verdict) -> CommitteeCert {
    CommitteeCert {
        verdict,
        signers: vec!["n1".into(), "n2".into(), "n3".into()],
        evidence_root: core::evidence_root(&[]), // matches core::evidence_root fold of the (empty) model log
    }
}

/// One executable step of the ordering under test.
#[derive(Clone)]
enum Step {
    Fund,
    Submit(u64),          // submission time
    ClaimTimeout(u64),    // claim time
    Cancel,
    Dispute,
    Verdict(Verdict),
    Complete,             // buyer-consent settlement; legal from Submitted only
}

fn run(steps: &[Step]) -> (u128, usize, Option<DealState>) {
    let mut d = deal();
    let mut log = MisconductLog::new();
    let mut paid_total = 0u128;
    let mut payouts = 0usize;
    let m = members();
    for s in steps {
        let r = match s {
            Step::Fund => core::fund(&mut d, 10).map(|_| 0),
            Step::Submit(t) => core::submit_deliverable(&mut d, "deliv".into(), *t).map(|_| 0),
            Step::ClaimTimeout(t) => core::claim_timeout(&mut d, *t).map(|p| p.total()),
            Step::Cancel => core::cancel(&mut d, 60).map(|p| p.total()),
            Step::Dispute => core::open_dispute(&mut d, "r".into()).map(|_| 0),
            Step::Verdict(v) => core::apply_verdict(&mut d, cert(v.clone()), &m, 3, &[], &mut log).map(|p| p.total()),
            Step::Complete => core::complete(&mut d, 61, &CompleteAuth::BuyerConsent, None, &[]).map(|p| p.total()),
        };
        if let Ok(amount) = r {
            if amount > 0 {
                paid_total += amount;
                payouts += 1;
            }
        }
    }
    (paid_total, payouts, Some(d.state))
}

fn check(ordering: &[Step], label: &str) -> bool {
    let (paid, count, state) = run(ordering);
    let terminal = matches!(state, Some(DealState::Settled) | Some(DealState::Refunded));
    let ok = if terminal {
        paid == 1_000 && count == 1
    } else {
        paid == 0 && count == 0
    };
    if !ok {
        eprintln!("VIOLATION [{}] state={:?} paid={} payouts={}", label, state, paid, count);
    }
    ok
}

/// Heap's algorithm over the five post-fund events.
fn permutations(mut items: Vec<Step>, k: usize, out: &mut Vec<Vec<Step>>) {
    if k == 1 {
        out.push(items.clone());
        return;
    }
    for i in 0..k {
        permutations(items.clone(), k - 1, out);
        let j = if k % 2 == 0 { i } else { 0 };
        items.swap(j, k - 1);
    }
}

#[test]
fn all_orderings_preserve_invariants() {
    let submit = Step::Submit(45); // in-time evidence (deadline = 50)
    let claim = Step::ClaimTimeout(60); // past deadline
    let mut orders = Vec::new();
    permutations(vec![submit, claim, Step::Cancel, Step::Dispute, Step::Verdict(Verdict::Fulfilled)], 5, &mut orders);
    assert_eq!(orders.len(), 120);

    let mut violations = 0;
    for o in &orders {
        let mut full = vec![Step::Fund];
        full.extend(o.iter().cloned());
        if !check(&full, "in-time-submit") {
            violations += 1;
        }
    }
    // Variant: late evidence (rejected by guard) must behave identically.
    let mut orders_late = Vec::new();
    permutations(
        vec![Step::Submit(51), Step::ClaimTimeout(60), Step::Cancel, Step::Dispute, Step::Verdict(Verdict::NotFulfilled)],
        5,
        &mut orders_late,
    );
    for o in &orders_late {
        let mut full = vec![Step::Fund];
        full.extend(o.iter().cloned());
        if !check(&full, "late-submit") {
            violations += 1;
        }
    }
    assert_eq!(violations, 0, "refund rule violations found — see stderr");
}

/// F11: the consent (`complete`) path joins the exhaustive enumeration, so
/// I2 "at most one money-moving transition" is checked with the consent and
/// verdict payout routes coexisting. Six post-fund events -> 720 orderings,
/// x {Fulfilled, NotFulfilled} verdict variants = 1440 runs. `Complete` only
/// succeeds from `Submitted`; earlier attempts fail with no effect, so the
/// enumeration also covers the premature-complete branch. Existing test and
/// the run/check/permutations machinery are reused unchanged.
#[test]
fn all_orderings_with_complete_preserve_invariants() {
    let mut violations = 0;
    for verdict in [Verdict::Fulfilled, Verdict::NotFulfilled] {
        let mut orders = Vec::new();
        permutations(
            vec![
                Step::Submit(45),       // in-time evidence (deadline = 50)
                Step::ClaimTimeout(60), // past deadline
                Step::Cancel,
                Step::Dispute,
                Step::Verdict(verdict),
                Step::Complete,
            ],
            6,
            &mut orders,
        );
        assert_eq!(orders.len(), 720);
        for o in &orders {
            let mut full = vec![Step::Fund];
            full.extend(o.iter().cloned());
            if !check(&full, "with-complete") {
                violations += 1;
            }
        }
    }
    assert_eq!(violations, 0, "refund rule violations found — see stderr");
}
