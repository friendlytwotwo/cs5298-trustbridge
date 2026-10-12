//! TrustBridge Lyquid — committee-attested fulfillment trust layer.
//!
//! Layering contract (see PLAN §3.1):
//!   types/core = pure domain logic, plain `cargo test`.
//!   this file  = thin platform wrappers: caller guards + ledger effects,
//!                mirroring the verified `erc20` example's `state!`/method style.
//!
//! Every `SPIKE(W1)` comment marks an API assumption that week-1 must verify
//! against ldk v0.7.3 (see README "W1 spike checklist").

pub mod types;
pub mod core;
pub mod committee;
pub mod assessor;
pub mod timeout;

use types::*;

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
// Mirrors the verified erc20 example: `network` = consensus-sequenced global
// (escrow ledger, evidence log, committee config); `instance` = node-local
// best-effort (LLM caches, watcher bookkeeping). HashMaps go through the
// deterministic alias (`new_hashmap()`), never bare std::HashMap iteration.

state! {
    // --- consensus (network) state ---
    network deals: HashMap<DealId, Deal> = new_hashmap();
    network balances: HashMap<AgentId, u128> = new_hashmap();
    network evidence_log: HashMap<DealId, Vec<EvidenceEntry>> = new_hashmap();
    network committee_members: HashMap<AgentId, bool> = new_hashmap();
    network committee_threshold: u32 = 3;
    network misconduct: HashMap<AgentId, u32> = new_hashmap();
    network deal_counter: u64 = 0;

    // --- node-local (instance) state ---
    instance assessment_cache: HashMap<DealId, AssessmentReport> = new_hashmap();
    instance watcher_last_slot: u64 = 0;
}

// ---------------------------------------------------------------------------
// Network functions (deterministic, replayed by all nodes)
// ---------------------------------------------------------------------------

/// Devnet-only faucet so the demo can mint internal-ledger tokens.
/// TODO(W2): gate behind a DEMO flag; listed in the report's trust-assumption
/// table as a demo-only trust hole.
#[method::network]
pub fn faucet(ctx: Context, to: AgentId, amount: u128) -> LyquidResult<()> {
    let _ = ctx;
    credit(&to, amount);
    log!("faucet:{}:+{}", to, amount);
    Ok(())
}

/// Broker creates a deal from an accepted assessment (see assessor.rs for the
/// instance->network two-step). The timeout must be estimate-derived.
#[method::network]
pub fn create_deal(
    ctx: Context,
    buyer: AgentId,
    seller: AgentId,
    amount: u128,
    fee_bps: u16,
    terms_digest: Digest,
    acceptance_digest: Digest,
    est_duration_ms: u64,
    est_confidence: u8,
) -> LyquidResult<DealId> {
    let _ = ctx;
    // SPIKE(W1): caller-identity accessor (er-20 example uses `eth_guard =
    // creator` on exported fns); enforce broker-only creation once known.
    deal_counter += 1;
    let id = format!("deal-{}", deal_counter);
    let timeout_slots = timeout_slots_from_estimate(est_duration_ms).max(1);
    let deal = core::create(Deal {
        id: id.clone(),
        buyer,
        seller,
        broker: "agent-broker".to_string(), // TODO(W2): real caller id
        amount,
        fee_bps,
        terms_digest,
        acceptance_digest,
        est_duration_ms,
        est_confidence,
        timeout_slots,
        created_slot: current_slot(),
        funded_slot: None,
        state: DealState::Qualified,
        deliverable_digest: None,
        committee_cert: None,
        dispute_reason: None,
    })?;
    deals.insert(id.clone(), deal);
    Ok(id)
}

/// Buyer escrows the full amount (internal ledger debit + state transition).
#[method::network]
pub fn fund(ctx: Context, deal_id: DealId) -> LyquidResult<()> {
    let buyer = caller_agent(&ctx)?;
    let now = current_slot();
    let deal = deals.get_mut(&deal_id).ok_or_else(|| lyquid_error("no such deal"))?;
    if deal.buyer != buyer {
        return Err(lyquid_error("only the buyer may fund"));
    }
    let amount = deal.amount;
    core::fund(deal, now)?;
    debit(&buyer, amount)?;
    log!("fund:{}:by:{}", deal_id, buyer);
    Ok(())
}

/// Append-only communication notarization. Anyone may submit; entries are
/// sequenced per deal. This is the fulfillment evidence the committee rules on.
#[method::network]
pub fn notarize(ctx: Context, deal_id: DealId, from: AgentId, to: AgentId, payload_digest: Digest) -> LyquidResult<u64> {
    let _ = ctx;
    // TODO(W4): require the payload_digest to carry an x402-#2833-style
    // request/response binding so receipts stay format-compatible.
    let entries = evidence_log.entry(deal_id.clone()).or_default();
    let seq = entries.len() as u64;
    entries.push(EvidenceEntry { seq, from, to, payload_digest, slot: current_slot() });
    Ok(seq)
}

#[method::network]
pub fn submit_deliverable(ctx: Context, deal_id: DealId, deliverable_digest: Digest) -> LyquidResult<()> {
    let seller = caller_agent(&ctx)?;
    let now = current_slot();
    let deal = deals.get_mut(&deal_id).ok_or_else(|| lyquid_error("no such deal"))?;
    if deal.seller != seller {
        return Err(lyquid_error("only the seller may submit"));
    }
    core::submit_deliverable(deal, deliverable_digest, now)?;
    Ok(())
}

/// Buyer-consented settlement of a submitted deal.
#[method::network]
pub fn complete(ctx: Context, deal_id: DealId) -> LyquidResult<()> {
    let buyer = caller_agent(&ctx)?;
    let now = current_slot();
    let (payout, buyer, seller, broker) = {
        let deal = deals.get_mut(&deal_id).ok_or_else(|| lyquid_error("no such deal"))?;
        if deal.buyer != buyer {
            return Err(lyquid_error("only the buyer may consent"));
        }
        let p = core::complete(deal, now, &core::CompleteAuth::BuyerConsent, None)?;
        (p, deal.buyer.clone(), deal.seller.clone(), deal.broker.clone())
    };
    apply_payout(&payout, &buyer, &seller, &broker)?;
    Ok(())
}

/// Permissionless timeout claim — the on-chain guard half of the
/// "off-chain trigger; on-chain guard" pattern (watcher: timeout.rs).
#[method::network]
pub fn claim_timeout(ctx: Context, deal_id: DealId) -> LyquidResult<bool> {
    let _ = ctx;
    let now = current_slot();
    let (payout, buyer, seller, broker) = {
        let deal = deals.get_mut(&deal_id).ok_or_else(|| lyquid_error("no such deal"))?;
        let p = core::claim_timeout(deal, now)?; // guard re-derives eligibility
        (p, deal.buyer.clone(), deal.seller.clone(), deal.broker.clone())
    };
    apply_payout(&payout, &buyer, &seller, &broker)?;
    Ok(true)
}

/// Buyer cancels a deal that has no submitted evidence yet.
#[method::network]
pub fn cancel(ctx: Context, deal_id: DealId) -> LyquidResult<()> {
    let buyer = caller_agent(&ctx)?;
    let (payout, buyer, seller, broker) = {
        let deal = deals.get_mut(&deal_id).ok_or_else(|| lyquid_error("no such deal"))?;
        if deal.buyer != buyer {
            return Err(lyquid_error("only the buyer may cancel"));
        }
        let p = core::cancel(deal, current_slot())?;
        (p, deal.buyer.clone(), deal.seller.clone(), deal.broker.clone())
    };
    apply_payout(&payout, &buyer, &seller, &broker)?;
    Ok(())
}

#[method::network]
pub fn open_dispute(ctx: Context, deal_id: DealId, reason_digest: Digest) -> LyquidResult<()> {
    let _ = ctx;
    let deal = deals.get_mut(&deal_id).ok_or_else(|| lyquid_error("no such deal"))?;
    core::open_dispute(deal, reason_digest)?;
    Ok(())
}

/// Apply a committee verdict. The certificate is re-validated against the
/// on-chain committee config; `Malicious` bumps the misconduct log.
/// Production path: verdict arrives via oracle certified call — see committee.rs.
#[method::network]
pub fn apply_committee_verdict(ctx: Context, deal_id: DealId, cert: committee::CommitteeCertWire) -> LyquidResult<()> {
    let _ = ctx;
    let members: Vec<AgentId> = committee::members();
    let threshold = committee_threshold as usize;
    let cert = cert.into_domain();

    let (payout, buyer, seller, broker) = {
        let deal = deals.get_mut(&deal_id).ok_or_else(|| lyquid_error("no such deal"))?;
        let p = core::apply_verdict(deal, cert, &members, threshold, &mut misconduct)?;
        (p, deal.buyer.clone(), deal.seller.clone(), deal.broker.clone())
    };
    apply_payout(&payout, &buyer, &seller, &broker)?;
    Ok(())
}

// --- committee config (demo: broker-managed; trust assumption documented) ---

#[method::network]
pub fn committee_config(ctx: Context, members: Vec<AgentId>, threshold: u32) -> LyquidResult<()> {
    let _ = ctx;
    // TODO(W2): caller guard (broker/deployer only).
    committee_members.clear();
    for m in members {
        committee_members.insert(m, true);
    }
    committee_threshold = threshold;
    Ok(())
}

// --- getters used by agents and the watcher ---

#[method::network]
pub fn deal_info(ctx: Context, deal_id: DealId) -> LyquidResult<String> {
    let _ = ctx;
    let deal = deals.get(&deal_id).ok_or_else(|| lyquid_error("no such deal"))?;
    Ok(serde_json::to_string(&DealView::from(deal)).unwrap())
}

#[method::network]
pub fn evidence_entries_json(ctx: Context, deal_id: DealId) -> LyquidResult<String> {
    let _ = ctx;
    Ok(serde_json::to_string(&evidence_log.get(&deal_id).cloned().unwrap_or_default()).unwrap())
}

#[method::network]
pub fn balance_of(ctx: Context, agent: AgentId) -> LyquidResult<u128> {
    let _ = ctx;
    Ok(balances.get(&agent).copied().unwrap_or(0))
}

#[method::network]
pub fn due_deals(ctx: Context, now: u64) -> LyquidResult<Vec<DealId>> {
    let _ = ctx;
    Ok(core::due_for_timeout(deals.iter(), now))
}

// ---------------------------------------------------------------------------
// Shared helpers (ledger effects)
// ---------------------------------------------------------------------------

fn debit(agent: &AgentId, amount: u128) -> Result<(), lyquid::LyquidError> {
    let bal = balances.get(agent).copied().unwrap_or(0);
    if bal < amount {
        return Err(lyquid_error("insufficient balance"));
    }
    balances.insert(agent.clone(), bal - amount);
    Ok(())
}

fn credit(agent: &AgentId, amount: u128) {
    let bal = balances.get(agent).copied().unwrap_or(0);
    balances.insert(agent.clone(), bal + amount);
}

/// Apply a core Payout. Escrow was debited at `fund`; this moves funds out.
/// Conservation (sum == deal.amount) is asserted by core tests.
fn apply_payout(p: &Payout, buyer: &AgentId, seller: &AgentId, broker: &AgentId) -> Result<(), lyquid::LyquidError> {
    if p.to_seller > 0 {
        credit(seller, p.to_seller);
    }
    if p.fee_to_broker > 0 {
        credit(broker, p.fee_to_broker);
    }
    if p.refund_to_buyer > 0 {
        credit(buyer, p.refund_to_buyer);
    }
    // Demo has no seller stake, so slash_to_treasury is always 0 today;
    // the stake+slash extension is the documented W4 stretch (report E3).
    Ok(())
}

/// Consensus time source. SPIKE(W1): find the real slot/height accessor on
/// network ctx; until then this is the platform seam all guards route through.
fn current_slot() -> u64 {
    // SPIKE(W1): replace with ctx-derived slot.
    0
}

/// Caller identity extraction. SPIKE(W1): confirm accessor (`ctx.from`,
/// `ctx.signer`, or eth address via `eth_guard = creator`).
fn caller_agent(_ctx: &Context) -> Result<AgentId, lyquid::LyquidError> {
    // SPIKE(W1)
    Ok("unknown".to_string())
}

fn lyquid_error(msg: &str) -> lyquid::LyquidError {
    // SPIKE(W1): confirm the error constructor; the template likely ships one.
    lyquid::LyquidError::msg(msg)
}

/// Serializable view returned to agents.
#[derive(serde::Serialize)]
struct DealView {
    id: String,
    buyer: String,
    seller: String,
    amount: u128,
    state: String,
    timeout_slots: u64,
    deadline_slot: Option<u64>,
}

impl From<&Deal> for DealView {
    fn from(d: &Deal) -> Self {
        DealView {
            id: d.id.clone(),
            buyer: d.buyer.clone(),
            seller: d.seller.clone(),
            amount: d.amount,
            state: format!("{:?}", d.state),
            timeout_slots: d.timeout_slots,
            deadline_slot: d.deadline_slot(),
        }
    }
}
