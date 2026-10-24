//! TrustBridge Lyquid — committee-attested fulfillment trust layer.
//!
//! Layering contract (see PLAN §3.1):
//!   types/core = pure domain logic, plain `cargo test`.
//!   this file  = thin platform wrappers: caller guards + ledger effects,
//!                mirroring the verified `erc20` example's `state!`/method style.
//!
//! S5 (W1-A) landed: the inline `SPIKE(W1)` items in this file are verified
//! against ldk v0.7.3 and rewritten as conclusions below (each cites the
//! platform source it was checked against). The remaining W1 items live in
//! W1-B (S1 timer semantics, S2 oracle, S3 lyquid-llm, S4 RPC packaging) —
//! see timeout.rs / assessor.rs / committee.rs for the still-open markers.
//!
//! Two seams own the platform-side structure (stage-two W2 work, now landed):
//!   error bridging    -> "Platform error bridge" block below;
//!   caller permission -> "Caller-permission matrix" block below.

pub mod types;
pub mod core;
pub mod committee;
pub mod assessor;
pub mod timeout;

use types::*;
use lyquid::prelude::*;

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
// Platform error bridge — the single seam for every failure that crosses
// into the platform result type. The W1 swap points are exactly two
// functions + one alias below; nothing else in this file may construct
// a LyquidError directly.
// ---------------------------------------------------------------------------

/// Platform result type. S5-verified (was SPIKE(W1)): ldk v0.7.3 already
/// exports the same name and shape (`pub type LyquidResult<T> =
/// Result<T, LyquidError>`, ldk lyquid/src/lib.rs:199), so the local alias
/// retired into a plain re-export — if the name ever drifts, only this
/// line changes.
pub use lyquid::LyquidResult;

fn lyquid_error(msg: &str) -> lyquid::LyquidError {
    // S5-verified (was SPIKE(W1)): the v0.7.3 error enum has no `msg`
    // constructor; the guest-runtime string variant is
    // `LyquidError::LyquidRuntime(String)` (ldk lyquid/src/lib.rs:172-189),
    // same form the erc20 example uses (erc20 src/lib.rs:31).
    LyquidError::LyquidRuntime(msg.to_string())
}

/// core::TransitionError -> platform error. Exhaustive match: one arm per
/// variant, so a NEW core variant (e.g. stage-one's InvalidFeeBps,
/// core.rs:26) is a compile error here instead of a silent format drift.
///
/// Why `map_err(bridge_core_err)` and not `impl From`: both the error trait
/// and `LyquidError` are foreign to this crate, so the orphan rules forbid a
/// blanket `From` impl — an explicit bridge call at each of the eight core
/// call sites is the only legal shape for "converge in one place".
fn bridge_core_err(e: core::TransitionError) -> lyquid::LyquidError {
    let msg = match e {
        core::TransitionError::WrongState { is, expected } => {
            format!("wrong state: got {is:?}, expected one of {expected:?}")
        }
        core::TransitionError::Terminal => "deal is terminal".to_string(),
        core::TransitionError::NotFundedYet => "deal is not funded yet".to_string(),
        core::TransitionError::DeadlineNotReached { now, deadline } => {
            format!("timeout not reached yet: now={now}, deadline={deadline}")
        }
        core::TransitionError::DeadlinePassed { now, deadline } => {
            format!("deadline passed: now={now}, deadline={deadline}")
        }
        core::TransitionError::MissingDeliverable => "deliverable digest missing".to_string(),
        core::TransitionError::MissingCert => {
            "committee certificate missing or evidence mismatch".to_string()
        }
        core::TransitionError::InsufficientCommittee { signers, required } => {
            format!("insufficient committee signers: got {signers}, need {required}")
        }
        core::TransitionError::NonMemberSigner(s) => format!("non-member signer: {s}"),
        core::TransitionError::InvalidSignerSet => {
            "invalid signer set (duplicate signers)".to_string()
        }
        core::TransitionError::InvalidFeeBps { got, max } => {
            format!("fee_bps out of range: got {got}, max {max}")
        }
    };
    lyquid_error(&msg)
}

// ---------------------------------------------------------------------------
// Caller-permission matrix — the single seam for every "who may call this".
// The table is the audit surface (one row per network fn); `require` is the
// only enforcement point. W1 landed the real caller identity in
// `caller_agent` alone and every guard is live without further edits.
// ---------------------------------------------------------------------------

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Access { Buyer, Seller, BuyerOrSeller, Broker, Committee, Anyone }

/// Broker identity for devnet runs. W1-A placeholder: backfilled with the
/// deployer/caller address string confirmed by the T4.5 self-signed
/// notarize probe (D4b of workflow-out/plan.md). TODO(W2): real deployer
/// identity via the real deployment flow.
const BROKER: &str = "TBD-CALLER-ADDR";

/// The matrix — one row per network fn. Data, so the audit is one glance.
/// Reviewer: diff this against core's guard docs.
pub const ACCESS_MATRIX: &[(&str, Access)] = &[
    ("faucet",                Access::Anyone),  // devnet demo; TODO(W2) DEMO flag（既有注释保留）
    ("create_deal",           Access::Broker),
    ("fund",                  Access::Buyer),
    ("notarize",              Access::Anyone),  // append-only 公证；from 强制等于 caller（自署名），防伪造 acceptance 条目（仲裁#3）
    ("submit_deliverable",    Access::Seller),
    ("complete",              Access::Buyer),
    ("claim_timeout",         Access::Anyone),  // permissionless by design（timeout.rs 模式）
    ("cancel",                Access::Buyer),
    ("open_dispute",          Access::BuyerOrSeller), // core.rs:180 "Any party"
    ("apply_committee_verdict", Access::Committee),  // caller 须为委员会成员且 cert.signers 包含 caller；wire 无签名为 demo 占位，真实 oracle 认证 TODO(W4)（committee.rs:12-18 生产路径）（仲裁#1）
    ("committee_config",      Access::Broker),   // demo: broker-managed（既有 TODO(W2) 注释保留）
    ("deal_info | evidence_entries_json | balance_of | due_deals", Access::Anyone), // 只读 getter
];

/// Single enforcement point. FAIL-CLOSED 设计不变：caller 身份来自
/// `ctx.caller: Address`（S5 实证，见 caller_agent），字符串化后进入本
/// 函数；矩阵与判定结构零改动。
fn require(access: Access, caller: &Address, state: &__lyquid::NetworkState, deal: Option<&Deal>) -> LyquidResult<AgentId> {
    // &Address 与 AgentId/String 不能直接比较：先统一到 AgentId 域，
    // 此后所有比较（含 BROKER 常量、committee_members 键）都在 AgentId 上做。
    let caller: AgentId = caller.to_string();
    let ok = match access {
        Access::Anyone => true,
        Access::Buyer => deal.map(|d| d.buyer == caller).unwrap_or(false),
        Access::Seller => deal.map(|d| d.seller == caller).unwrap_or(false),
        Access::BuyerOrSeller => deal.map(|d| d.buyer == caller || d.seller == caller).unwrap_or(false),
        Access::Broker => caller == BROKER,
        // 仲裁#1：委员会门禁，复用 committee_config 写入的 committee_members
        // network 状态（与 apply_committee_verdict 的证书校验同源）；未配置
        // 即空集 -> 拒绝（fail-closed）。
        Access::Committee => state.committee_members.get(&caller).copied().unwrap_or(false),
    };
    if ok { Ok(caller) } else { Err(lyquid_error("caller not permitted for this action")) }
}

// ---------------------------------------------------------------------------
// Network functions (deterministic, replayed by all nodes)
// ---------------------------------------------------------------------------
// 借用纪律（S5 实证，D3-2）：每个方法开头单点 reborrow
// `let state = &mut *ctx.network;`（只读 getter 用 `&*`），体内一律
// `state.<field>`；不逐处 `ctx.network.` 前缀——多字段并存时逐处前缀触发
// E0502（同时可变+不可变借用），单点 reborrow 后字段级分离借用编译通过。
// 标量字段统一 `*` 解引用（宏生成字段为 `&'static mut T` 句柄，
// erc20 `*state.total_supply` 同款）。

/// Devnet-only faucet so the demo can mint internal-ledger tokens.
/// TODO(W2): gate behind a DEMO flag; listed in the report's trust-assumption
/// table as a demo-only trust hole.
#[method::network]
pub fn faucet(ctx: &mut _, to: AgentId, amount: u128) -> LyquidResult<()> {
    let state = &mut *ctx.network;
    credit(state, &to, amount);
    log!(faucet, &format!("faucet:{}:+{}", to, amount));
    Ok(())
}

/// Broker creates a deal from an accepted assessment (see assessor.rs for the
/// instance->network two-step). The timeout must be estimate-derived.
#[method::network]
pub fn create_deal(
    ctx: &mut _,
    buyer: AgentId,
    seller: AgentId,
    amount: u128,
    fee_bps: u16,
    terms_digest: Digest,
    acceptance_digest: Digest,
    est_duration_ms: u64,
    est_confidence: u8,
) -> LyquidResult<DealId> {
    let state = &mut *ctx.network;
    require(Access::Broker, &ctx.caller, state, None)?;
    // Broker-only creation enforced above (ACCESS_MATRIX Broker row).
    // S5-verified（was SPIKE(W1)）: caller accessor is `ctx.caller: Address`
    // （erc20 src/lib.rs:161 + CallContext 定义）；BROKER 地址经 T4.5 探针
    // 回填（D4b），守卫即活化。
    // Platform-side input validation (stage-two W2 work, core.rs:46-48):
    // degenerate inputs are rejected here, ONCE, before any state moves.
    // fee_bps is deliberately NOT re-checked: the >10_000 cap belongs to
    // core::create (core.rs:54) and reaches us bridged as InvalidFeeBps —
    // a second platform-side copy would only drift.
    if amount == 0 { return Err(lyquid_error("amount must be > 0")); }
    if buyer.is_empty() || seller.is_empty() { return Err(lyquid_error("buyer/seller must be non-empty")); }
    if buyer == seller { return Err(lyquid_error("buyer and seller must differ")); }
    if est_confidence > 100 { return Err(lyquid_error("est_confidence must be 0-100")); }
    if terms_digest.is_empty() || acceptance_digest.is_empty() {
        return Err(lyquid_error("terms/acceptance digest must be non-empty"));
    }
    // est_duration_ms == 0 stays allowed: timeout_slots is already clamped
    // to >= 1 by `.max(1)` below.
    *state.deal_counter += 1;
    let id = format!("deal-{}", *state.deal_counter);
    let timeout_slots = timeout_slots_from_estimate(est_duration_ms).max(1);
    let deal = core::create(Deal {
        id: id.clone(),
        buyer,
        seller,
        broker: BROKER.to_string(), // TODO(W2): real deployer identity
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
    }).map_err(bridge_core_err)?;
    state.deals.insert(id.clone(), deal);
    Ok(id)
}

/// Buyer escrows the full amount (internal ledger debit + state transition).
#[method::network]
pub fn fund(ctx: &mut _, deal_id: DealId) -> LyquidResult<()> {
    let state = &mut *ctx.network;
    let buyer = {
        let deal = state.deals.get(&deal_id).ok_or_else(|| lyquid_error("no such deal"))?;
        require(Access::Buyer, &ctx.caller, state, Some(deal))?
    };
    let now = current_slot();
    let amount = {
        let deal = state.deals.get_mut(&deal_id).ok_or_else(|| lyquid_error("no such deal"))?;
        // 与 debit 同源预检：先拒绝余额不足，再转状态。core::fund 只改状态，
        // debit 才动账；预检通过后同一次调用内 debit 必然成功（确定性执行）。
        // S5-verified（was SPIKE(W1)）: network-method Err 的原子回滚语义
        // 不再被依赖——预检使两种平台语义下设计均正确；fund 的 devnet
        // 成功输出（workflow-out/w1a-funded-evidence.txt）是行为证据。
        let bal = state.balances.get(&buyer).copied().unwrap_or(0);
        if bal < deal.amount {
            return Err(lyquid_error("insufficient balance"));
        }
        core::fund(deal, now).map_err(bridge_core_err)?;
        deal.amount
    };
    debit(state, &buyer, amount)?;
    log!(fund, &format!("fund:{}:by:{}", deal_id, buyer));
    Ok(())
}

/// Append-only communication notarization. Anyone may submit; entries are
/// sequenced per deal. This is the fulfillment evidence the committee rules on.
/// 裁决时的证书根由本日志条目折叠派生（core::evidence_root，经 apply_committee_verdict 单点读取）。
#[method::network]
pub fn notarize(ctx: &mut _, deal_id: DealId, from: AgentId, to: AgentId, payload_digest: Digest) -> LyquidResult<u64> {
    // 自署名强制（仲裁#3）：任何人可提交，但条目的 from 必须等于提交者本人
    // ——`check_evidence_shape` 的 `e.from == deal.seller`（committee.rs:58）
    // 因此成为可信的真归属，伪造 acceptance 条目被挡在共识入口。不收窄为
    // BuyerOrSeller：demo 流中 broker 本身就是合法作者（demo.py:57/58/69 的
    // from 分别为 ALICE/BROKER/BOB，broker.py:46/53 以 broker 为 from）。
    // `from` 参数保留：wire 形态与 rpc.py:49 兼容；弃参改造属阶段四评估。
    let state = &mut *ctx.network;
    let caller = caller_agent(&ctx.caller)?;
    if from != caller {
        return Err(lyquid_error("notarize is self-signed only: `from` must equal the caller"));
    }
    // TODO(W4): require the payload_digest to carry an x402-#2833-style
    // request/response binding so receipts stay format-compatible.
    let entries = state.evidence_log.entry(deal_id.clone()).or_default();
    let seq = entries.len() as u64;
    entries.push(EvidenceEntry { seq, from, to, payload_digest, slot: current_slot() });
    Ok(seq)
}

#[method::network]
pub fn submit_deliverable(ctx: &mut _, deal_id: DealId, deliverable_digest: Digest) -> LyquidResult<()> {
    let state = &mut *ctx.network;
    {
        let deal = state.deals.get(&deal_id).ok_or_else(|| lyquid_error("no such deal"))?;
        require(Access::Seller, &ctx.caller, state, Some(deal))?;
    }
    let now = current_slot();
    let deal = state.deals.get_mut(&deal_id).ok_or_else(|| lyquid_error("no such deal"))?;
    core::submit_deliverable(deal, deliverable_digest, now).map_err(bridge_core_err)?;
    Ok(())
}

/// Buyer-consented settlement of a submitted deal.
#[method::network]
pub fn complete(ctx: &mut _, deal_id: DealId) -> LyquidResult<()> {
    let state = &mut *ctx.network;
    {
        let deal = state.deals.get(&deal_id).ok_or_else(|| lyquid_error("no such deal"))?;
        require(Access::Buyer, &ctx.caller, state, Some(deal))?;
    }
    let now = current_slot();
    let (payout, buyer, seller, broker, escrowed) = {
        let deal = state.deals.get_mut(&deal_id).ok_or_else(|| lyquid_error("no such deal"))?;
        let p = core::complete(deal, now, &core::CompleteAuth::BuyerConsent, None,
            // BuyerConsent 分支不读证据日志（core::complete 签名统一穿参）。
            &[]).map_err(bridge_core_err)?;
        (p, deal.buyer.clone(), deal.seller.clone(), deal.broker.clone(), deal.amount)
    };
    apply_payout(state, &payout, &buyer, &seller, &broker, escrowed)?;
    Ok(())
}

/// Permissionless timeout claim — the on-chain guard half of the
/// "off-chain trigger; on-chain guard" pattern (watcher: timeout.rs).
#[method::network]
pub fn claim_timeout(ctx: &mut _, deal_id: DealId) -> LyquidResult<bool> {
    let state = &mut *ctx.network;
    let now = current_slot();
    let (payout, buyer, seller, broker, escrowed) = {
        let deal = state.deals.get_mut(&deal_id).ok_or_else(|| lyquid_error("no such deal"))?;
        let p = core::claim_timeout(deal, now).map_err(bridge_core_err)?; // guard re-derives eligibility
        (p, deal.buyer.clone(), deal.seller.clone(), deal.broker.clone(), deal.amount)
    };
    apply_payout(state, &payout, &buyer, &seller, &broker, escrowed)?;
    Ok(true)
}

/// Buyer cancels a deal that has no submitted evidence yet.
#[method::network]
pub fn cancel(ctx: &mut _, deal_id: DealId) -> LyquidResult<()> {
    let state = &mut *ctx.network;
    {
        let deal = state.deals.get(&deal_id).ok_or_else(|| lyquid_error("no such deal"))?;
        require(Access::Buyer, &ctx.caller, state, Some(deal))?;
    }
    let (payout, buyer, seller, broker, escrowed) = {
        let deal = state.deals.get_mut(&deal_id).ok_or_else(|| lyquid_error("no such deal"))?;
        let p = core::cancel(deal, current_slot()).map_err(bridge_core_err)?;
        (p, deal.buyer.clone(), deal.seller.clone(), deal.broker.clone(), deal.amount)
    };
    apply_payout(state, &payout, &buyer, &seller, &broker, escrowed)?;
    Ok(())
}

#[method::network]
pub fn open_dispute(ctx: &mut _, deal_id: DealId, reason_digest: Digest) -> LyquidResult<()> {
    let state = &mut *ctx.network;
    // core.rs:180: "Any party" = the deal's parties (BuyerOrSeller); before
    // this guard existed the fn was callable by anyone at all.
    {
        let deal = state.deals.get(&deal_id).ok_or_else(|| lyquid_error("no such deal"))?;
        require(Access::BuyerOrSeller, &ctx.caller, state, Some(deal))?;
    }
    let deal = state.deals.get_mut(&deal_id).ok_or_else(|| lyquid_error("no such deal"))?;
    core::open_dispute(deal, reason_digest).map_err(bridge_core_err)?;
    Ok(())
}

/// Apply a committee verdict. The certificate is re-validated against the
/// on-chain committee config; `Malicious` bumps the misconduct log.
/// Production path: verdict arrives via oracle certified call — see committee.rs.
#[method::network]
pub fn apply_committee_verdict(ctx: &mut _, deal_id: DealId, cert: committee::CommitteeCertWire) -> LyquidResult<()> {
    // 权威源是 committee_config 写入的 network 状态；committee::members() 只是
    // instance 侧占位 shim（本函数不再调用它）。S5-verified（was
    // SPIKE(W1)）: `state.committee_members.iter()` 的语法即平台 HashMap
    // 句柄的常规迭代，编译通过即证据。
    // 顺序无关性：`members.contains(s)` 与阈值比较均与迭代顺序无关
    // （ahash 确定性种子下 HashMap 迭代本身也确定，见 prelude::new_hashmap）。
    let state = &mut *ctx.network;
    let members: Vec<AgentId> = state.committee_members.iter().map(|(m, _)| m.clone()).collect();
    let threshold = *state.committee_threshold as usize;
    // 仲裁#1：caller 须为委员会成员（require 的 Committee 臂，同一
    // committee_members 状态）且亲自签署本证书；wire 无签名为 demo 占位——
    // 真实提交者认证走 oracle certified call，TODO(W4)
    // （committee.rs:12-18 生产路径）。
    let caller = require(Access::Committee, &ctx.caller, state, None)?;
    if !cert.signers.iter().any(|s| *s == caller) {
        return Err(lyquid_error("caller must be among the certificate signers"));
    }
    // 读-算-校同源（阶段3b）：同一条目切片先喂 into_domain 折叠出证书根，再传 core::apply_verdict 由 validate_cert 重算比对——cert.evidence_root 与裁决校验不可能指向不同数据。
    let entries: Vec<EvidenceEntry> = state.evidence_log.get(&deal_id).cloned().unwrap_or_default();
    let cert = cert.into_domain(&entries);

    // misconduct 计数单点在 core::apply_verdict（经 &mut misconduct 完成），
    // 平台层不得重复累加；终态同样由 core 从裁决映射，平台层不推断。
    // S5 新形态差异（登记 implementation.md）：v0.7.3 network state 的
    // HashMap 是 hashbrown+ahash（prelude::HashMap，确定性种子），而领域
    // 类型 MisconductLog = std::collections::HashMap（types.rs:181，零平台
    // 依赖冻结）——二者类型不同，core 的 &mut MisconductLog 形参无法直接
    // 接收 network 状态句柄。桥接（lib.rs 平台层；types/core 零改动）：
    // std 镜像传入、Ok 后写回——计数单点仍只在 core，平台层不推断。
    let mut misconduct_domain: std::collections::HashMap<AgentId, u32> =
        state.misconduct.iter().map(|(k, v)| (k.clone(), *v)).collect();
    let (payout, buyer, seller, broker, escrowed) = {
        let deal = state.deals.get_mut(&deal_id).ok_or_else(|| lyquid_error("no such deal"))?;
        let p = core::apply_verdict(deal, cert, &members, threshold, &entries, &mut misconduct_domain).map_err(bridge_core_err)?;
        (p, deal.buyer.clone(), deal.seller.clone(), deal.broker.clone(), deal.amount)
    };
    // 仅 Ok 路径写回：Err 时 `?` 早退、镜像丢弃，与 deal 不变的语义一致。
    state.misconduct.clear();
    for (k, v) in misconduct_domain {
        state.misconduct.insert(k, v);
    }
    apply_payout(state, &payout, &buyer, &seller, &broker, escrowed)?;
    Ok(())
}

// --- committee config (demo: broker-managed; trust assumption documented) ---

#[method::network]
pub fn committee_config(ctx: &mut _, members: Vec<AgentId>, threshold: u32) -> LyquidResult<()> {
    let state = &mut *ctx.network;
    require(Access::Broker, &ctx.caller, state, None)?;
    // TODO(W2): caller guard (broker/deployer only) — enforced above via
    // require(Access::Broker) until the real deployer identity exists.
    state.committee_members.clear();
    for m in members {
        state.committee_members.insert(m, true);
    }
    *state.committee_threshold = threshold;
    Ok(())
}

// --- getters used by agents and the watcher ---

#[method::network]
pub fn deal_info(ctx: &_, deal_id: DealId) -> LyquidResult<String> {
    let state = &*ctx.network;
    let deal = state.deals.get(&deal_id).ok_or_else(|| lyquid_error("no such deal"))?;
    // Consensus replay must not panic: serialization errors become platform
    // errors instead of an unwrap.
    Ok(serde_json::to_string(&DealView::from(deal)).map_err(|e| lyquid_error(&format!("json serialize: {e}")))?)
}

#[method::network]
pub fn evidence_entries_json(ctx: &_, deal_id: DealId) -> LyquidResult<String> {
    let state = &*ctx.network;
    Ok(serde_json::to_string(&state.evidence_log.get(&deal_id).cloned().unwrap_or_default())
        .map_err(|e| lyquid_error(&format!("json serialize: {e}")))?)
}

#[method::network]
pub fn balance_of(ctx: &_, agent: AgentId) -> LyquidResult<u128> {
    let state = &*ctx.network;
    Ok(state.balances.get(&agent).copied().unwrap_or(0))
}

/// Advisory-only listing of deals past their timeout at the CALLER-supplied
/// `now`. The parameter cannot move funds: the only guard on money movement
/// is `claim_timeout`, which re-derives time via `current_slot` — a forged
/// `now` at most perturbs this informational list. Signature kept identical
/// to the FakeNode mirror (rpc.py `due_deals(now)`); stage-four alignment.
#[method::network]
pub fn due_deals(ctx: &_, now: u64) -> LyquidResult<Vec<DealId>> {
    let state = &*ctx.network;
    Ok(core::due_for_timeout(state.deals.iter(), now))
}

// ---------------------------------------------------------------------------
// Shared helpers (ledger effects)
// ---------------------------------------------------------------------------
// S5 形态（erc20 同款）：自由 helper 以 `state: &mut __lyquid::NetworkState`
// 穿参，方法内调用点传 reborrow 后的 state。

fn debit(state: &mut __lyquid::NetworkState, agent: &AgentId, amount: u128) -> LyquidResult<()> {
    let bal = state.balances.get(agent).copied().unwrap_or(0);
    if bal < amount {
        return Err(lyquid_error("insufficient balance"));
    }
    state.balances.insert(agent.clone(), bal - amount);
    Ok(())
}

fn credit(state: &mut __lyquid::NetworkState, agent: &AgentId, amount: u128) {
    let bal = state.balances.get(agent).copied().unwrap_or(0);
    state.balances.insert(agent.clone(), bal + amount);
}

/// Apply a core Payout. Escrow was debited at `fund`; this moves funds out.
/// Conservation (sum == deal.amount) is asserted by core tests.
///
/// Alignment contract with the stage-one core semantics (F1/F2/F4):
/// - All-zero Payout (Qualified-cancel, core.rs:87) falls through the three
///   `> 0` gates and is a no-op — nothing is minted out of thin air. The
///   platform-side half of the F2 argument lives right here, pinned.
/// - slash_to_treasury: the demo has no seller stake (`fund` debits only the
///   buyer's escrow), so core produces 0 today. The credit branch is still
///   written, paying a TREASURY demo account, so the W4 stake+slash
///   extension lands at a single point; until then it is explicit dead
///   code. TODO(W4) (this is not an ldk-API-assumption item).
/// - Conservation defense: `debug_assert!(p.total() <= escrowed)` catches
///   minting-class bugs during testing.
/// - `escrowed == deal.amount` premise (R#2): fund returning Ok implies the
///   escrow debit succeeded — the balance precheck makes `debit` succeed
///   within the same deterministic call; the order stays precheck ->
///   core::fund (sets Funded) -> debit and must NOT be reordered (debit
///   succeeding while core::fund fails would strand debited funds).
fn apply_payout(state: &mut __lyquid::NetworkState, p: &Payout, buyer: &AgentId, seller: &AgentId, broker: &AgentId, escrowed: u128) -> LyquidResult<()> {
    debug_assert!(p.total() <= escrowed, "payout exceeds escrow");
    if p.to_seller > 0 {
        credit(state, seller, p.to_seller);
    }
    if p.fee_to_broker > 0 {
        credit(state, broker, p.fee_to_broker);
    }
    if p.refund_to_buyer > 0 {
        credit(state, buyer, p.refund_to_buyer);
    }
    if p.slash_to_treasury > 0 {
        credit(state, &TREASURY.to_string(), p.slash_to_treasury);
    }
    Ok(())
}

/// Demo treasury account for slash proceeds (see apply_payout doc).
const TREASURY: &str = "treasury";

/// Consensus time source. S5-verified (was SPIKE(W1)): the host API
/// `lyquor_api::chain_pos()` returns the `ChainPos` (block/idx packed u128),
/// and `.block()` is the u64 block height — same single point the platform's
/// own bartender uses (ldk bartender/src/lib.rs:90-96). No ctx parameter is
/// needed, so the single-point function shape (G5) survives untouched.
///
/// Single-point audit (stage-two): every consumer of consensus time in this
/// file routes through this function — `create_deal` (created_slot), `fund`
/// (timeout clock start), `notarize` (entry.slot), `submit_deliverable`,
/// `complete`, `claim_timeout`, `cancel`. Any NEW use of time must go
/// through here; `due_deals(now)` is advisory-only (see its doc), and the
/// future watcher must call this same single point (timeout.rs).
pub(crate) fn current_slot() -> u64 {
    // S5-verified（was SPIKE(W1): replace with ctx-derived slot）: no ctx
    // needed — the host API is context-free, single-point shape kept.
    lyquor_api::chain_pos().map(|p| p.block()).unwrap_or(0)
}

/// Caller identity extraction. S5-verified (was SPIKE(W1)): the context
/// field is `ctx.caller: Address` (CallContext, ldk lyquid/src/lib.rs:162);
/// the AgentId domain is the address's string form — the exact spelling
/// (checksum case) is pinned by the T4.5 self-signed notarize probe and
/// recorded in workflow-out/implementation.md.
/// `require()` is this function's only role-check consumer — every
/// permission in the matrix is live through it.
fn caller_agent(caller: &Address) -> LyquidResult<AgentId> {
    // S5-verified（was SPIKE(W1)）: string form pinned by the T4.5 probe.
    Ok(caller.to_string())
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
