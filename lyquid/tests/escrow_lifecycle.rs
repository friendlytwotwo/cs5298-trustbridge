//! End-to-end lifecycle over the pure core, with a mirror of lib.rs's
//! `apply_payout` ledger effects, asserting balance conservation across the
//! whole book (not just per payout).
//!
//! The same scenario will run against the deployed Lyquid in W2 via
//! scripts/demo.py --node; this file is the always-available fallback (B1).

use std::collections::HashMap;
use trustbridge::core::{self, CompleteAuth};
use trustbridge::types::*;

#[test]
fn normal_flow_book_is_conservation_closed() {
    let mut book: HashMap<String, u128> = HashMap::new();
    let mut d = deal(1_000, 200);

    // faucet + fund
    *book.entry(d.buyer.clone()).or_insert(0) += 10_000;
    core::fund(&mut d, 10).unwrap();
    *book.get_mut(&d.buyer).unwrap() -= d.amount; // escrow debit

    // evidence + deliverable
    core::submit_deliverable(&mut d, "deliv".into(), 20).unwrap();

    // settle with buyer consent, mirroring apply_payout
    let p = core::complete(&mut d, 30, &CompleteAuth::BuyerConsent, None).unwrap();
    *book.entry(d.seller.clone()).or_insert(0) += p.to_seller;
    *book.entry(d.broker.clone()).or_insert(0) += p.fee_to_broker;

    assert_eq!(d.state, DealState::Settled);
    assert_eq!(p.refund_to_buyer, 0);
    // money in the book minus the un-escrowed remainder == minted amount
    let total: u128 = book.values().sum();
    assert_eq!(total + d.amount - d.amount, 10_000);
    assert_eq!(book["bob"], 980);
    assert_eq!(book["broker"], 20);
    assert_eq!(book["alice"], 9_000);
}

#[test]
fn timeout_flow_refunds_buyer_completely() {
    let mut book: HashMap<String, u128> = HashMap::new();
    let mut d = deal(1_000, 200);
    *book.entry(d.buyer.clone()).or_insert(0) += 1_000;
    core::fund(&mut d, 10).unwrap();
    *book.get_mut(&d.buyer).unwrap() -= 1_000;

    // seller never delivers; watcher fires after the deadline
    let p = core::claim_timeout(&mut d, 50).unwrap();
    *book.get_mut(&d.buyer).unwrap() += p.refund_to_buyer;

    assert_eq!(d.state, DealState::Refunded);
    assert_eq!(book["alice"], 1_000); // made whole
    assert_eq!(book.values().sum::<u128>() - 1_000, 0); // nothing leaked to others
}

#[test]
fn adversarial_forged_evidence_ends_in_refund_plus_flag() {
    let mut book: HashMap<String, u128> = HashMap::new();
    let mut d = deal(1_000, 200);
    *book.entry(d.buyer.clone()).or_insert(0) += 1_000;
    core::fund(&mut d, 10).unwrap();
    *book.get_mut(&d.buyer).unwrap() -= 1_000;

    // seller forges a deliverable in time, buyer disputes
    core::submit_deliverable(&mut d, "forged".into(), 45).unwrap();
    core::open_dispute(&mut d, "does-not-match-terms".into()).unwrap();

    let members = vec!["n1".to_string(), "n2".to_string(), "n3".to_string(), "n4".to_string()];
    let cert = CommitteeCert {
        verdict: Verdict::Malicious,
        signers: vec!["n1".into(), "n2".into(), "n3".into()],
        evidence_root: core::evidence_root(&d),
    };
    let mut log = MisconductLog::new();
    let p = core::apply_verdict(&mut d, cert, &members, 3, &mut log).unwrap();
    *book.get_mut(&d.buyer).unwrap() += p.refund_to_buyer;

    assert_eq!(d.state, DealState::Refunded);
    assert_eq!(book["alice"], 1_000);
    assert_eq!(log.get("bob"), Some(&1)); // reputation hook fired
}

#[test]
fn committee_fulfill_flow_book_conservation() {
    // Committee-routed settlement (F12 blind spot: the three flows above only
    // exercised BuyerConsent / timeout / verdict). Ledger effects mirror
    // lib.rs apply_payout exactly.
    let mut book: HashMap<String, u128> = HashMap::new();
    let mut d = deal(1_000, 200);

    // faucet + fund
    *book.entry(d.buyer.clone()).or_insert(0) += 10_000;
    core::fund(&mut d, 10).unwrap();
    *book.get_mut(&d.buyer).unwrap() -= d.amount; // escrow debit

    // seller delivers in time; a committee cert (not the buyer) settles it
    core::submit_deliverable(&mut d, "deliv".into(), 20).unwrap();
    let members = vec!["n1".to_string(), "n2".to_string(), "n3".to_string(), "n4".to_string()];
    let cert = CommitteeCert {
        verdict: Verdict::Fulfilled,
        signers: vec!["n1".into(), "n2".into(), "n3".into()],
        evidence_root: core::evidence_root(&d),
    };
    let p = core::complete(&mut d, 30, &CompleteAuth::Committee(cert), Some((&members, 3))).unwrap();
    *book.entry(d.seller.clone()).or_insert(0) += p.to_seller;
    *book.entry(d.broker.clone()).or_insert(0) += p.fee_to_broker;

    assert_eq!(d.state, DealState::Settled);
    assert!(d.committee_cert.is_some());
    assert_eq!(p.refund_to_buyer, 0);
    assert_eq!(book["bob"], 980);
    assert_eq!(book["broker"], 20);
    assert_eq!(book["alice"], 9_000);
    assert_eq!(book.values().sum::<u128>(), 10_000); // whole book == faucet
}

#[test]
fn committee_refund_flow_book_conservation() {
    // Committee-routed refund through `complete`; doubles as the end-to-end
    // F1 proof: a NotFulfilled verdict must land the deal in Refunded (the
    // old code mislabelled it Settled), with the buyer made whole.
    let mut book: HashMap<String, u128> = HashMap::new();
    let mut d = deal(1_000, 200);

    // faucet + fund
    *book.entry(d.buyer.clone()).or_insert(0) += 1_000;
    core::fund(&mut d, 10).unwrap();
    *book.get_mut(&d.buyer).unwrap() -= 1_000;

    // seller delivers; the committee rules the deliverable NotFulfilled
    core::submit_deliverable(&mut d, "weak".into(), 20).unwrap();
    let members = vec!["n1".to_string(), "n2".to_string(), "n3".to_string(), "n4".to_string()];
    let cert = CommitteeCert {
        verdict: Verdict::NotFulfilled,
        signers: vec!["n1".into(), "n2".into(), "n3".into()],
        evidence_root: core::evidence_root(&d),
    };
    let p = core::complete(&mut d, 30, &CompleteAuth::Committee(cert), Some((&members, 3))).unwrap();
    *book.get_mut(&d.buyer).unwrap() += p.refund_to_buyer;

    assert_eq!(p, Payout::full_refund(1_000));
    assert_eq!(d.state, DealState::Refunded);
    assert!(d.committee_cert.is_some());
    assert_eq!(book["alice"], 1_000); // made whole
    assert_eq!(book.values().sum::<u128>() - 1_000, 0); // nothing leaked to others
}

fn deal(amount: u128, fee_bps: u16) -> Deal {
    Deal {
        id: "d".into(),
        buyer: "alice".into(),
        seller: "bob".into(),
        broker: "broker".into(),
        amount,
        fee_bps,
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

// W2 TODO: same scenario against the deployed Lyquid. Sketch (enable after
// SPIKE(W1) settles macro/signature drift):
//
//   #[lyquid_test::test]
//   fn devnet_normal_flow() {
//       // faucet -> create_deal -> fund -> notarize xN -> submit_deliverable
//       // -> complete; assert deal_info state transitions and balances.
//   }
