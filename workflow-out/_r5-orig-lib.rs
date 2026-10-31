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
//!
//! W1-B1: the platform-mechanism probes are mounted at `probe/` (S1 timer
//! semantics, S2 oracle certification round; fields below prefixed `probe_`
//! plus the `cert_probe` oracle topic). See probe/mod.rs and
//! workflow-out/w1b1-*.md for the experiment record. Escrow surface
//! untouched.
//!
//! W1-B2: S3 LLM wiring + S4 RPC alignment landed (plan/evidence:
//! workflow-out/w1b2-*.md). (a) `assess_brief` — instance-side assessment
//! with the real lyquid-llm backend (mode contract R1#4: empty api_key OR
//! base_url => HeuristicModel replay; else LyquidLlmModel), report cached in
//! instance `assessment_cache` keyed by the brief summary and returned as the
//! JSON string over the export=eth face (R2#1 wire shape, single
//! serialization point in assessor::report_json). (b) export=eth attribute
//! additions ONLY (method list / ACCESS_MATRIX / bodies untouched), precedent
//! = the W1-A five methods: submit_deliverable, complete, claim_timeout,
//! cancel, committee_config, evidence_entries_json, balance_of, due_deals —
//! the keeper/demo write path (w1b2-s4-rpc.md §B-④h proved un-exported
//! methods are `FuncNotFound` over the ETH API).
//!
//! R2（路线①）：open_dispute / apply_committee_verdict 亦 eth 导出，对抗流
//! 上链跑真 devnet。open_dispute 参数 (String,String) 本就 ABI 兼容；
//! apply_committee_verdict 的 wire 参数扁平化为 (string,uint8,string[])，体内
//! 重建 wire 结构体——结构体参数无 EthAbiType，而裸 u8（ethabi.rs:258-280，
//! 活体先例 create_deal 的 est_confidence）与 Vec<String>（ethabi.rs:395，
//! 活体先例 committee_config）均有。诚实边界：扁平 wire 仍无签名，demo 占位
//! 性质未变，真实 oracle 认证 TODO(W4)（committee.rs:12-18）。方案见
//! workflow-out/plan.md §4。单一签名例外（登记偏离）：
//! `balance_of` returns wire `U128` — bare `u128` has no EthAbiType in
//! v0.8.1 (ethabi.rs:218-281); same edge-conversion pattern as the
//! faucet/create_deal amount params (R1#1).
//!
//! R3（路线②，E2 四节点委员会演示）：顶层壳模块 `committee_certified`（oracle
//! 主题 `cert_verdict`）把 W1-B1 的 cert_probe 探针正主化为演示级生产接线——
//! 认证回调 `committee_verdict_certified` 把 `ctx.cert.signers`（平台证书里的
//! 真实节点签名集）映射为 NodeID 显示串，以 `CommitteeCertWire` 形态进入与本
//! 文件 `apply_committee_verdict` **完全相同**的校验/裁决/写回/结算链（共享
//! 单点 helper `apply_cert_and_payout`）——路线①② 共享 core::apply_verdict
//! 单点，信任模型唯一。待裁 deal 由 network 域 `e2_armed_deal` 经共识状态传给
//! 全体节点的 `propose`（init 仍只携带 price-feed 已证的 avg_num/target 二字段）。
//! 该模块是 **cert 门控的资金路径**（helper → apply_payout → credit 真实结算），
//! 不是 probe 类 SPIKE 例外；其 7 方法门禁台账见 `committee_certified.rs`
//! 模块头 E2 门禁表。方案：workflow-out/plan.md §3。

pub mod types;
pub mod core;
pub mod committee;
pub mod assessor;
pub mod timeout;
pub mod probe;
pub mod committee_certified;

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
    // W1-B2：键型由 DealId 改为 brief 摘要串——「先评估后建 deal」时序下
    // deal 尚不存在，键 = buyer|seller|terms|scope 摘要（assess_brief 写入）。
    // 只动 instance 域，types.rs 冻结不触。
    instance assessment_cache: HashMap<String, AssessmentReport> = new_hashmap();
    instance watcher_last_slot: u64 = 0;

    // probe state (W1-B1) — 主 escrow 字段零改动。R1 已证子模块不能自带
    // state!（ldk syntax.rs:105-167 展开为调用点 `pub mod __lyquid`，而方法
    // 宏硬编码 `crate::__lyquid` 上下文；cargo check 实录
    // workflow-out/_w1b1-r1-submodule-state-check.txt），故探针字段并入本块。
    // S1 instance 域（节点本地观测）
    instance probe_fires: u64 = 0;
    instance probe_registered_at_ms: u64 = 0;
    instance probe_last_fire_at_ms: u64 = 0;
    instance probe_arm_delay_ms: u64 = 0;
    // S1 network 域（共识观测面 = exactly-once 判定域）
    network probe_net_fires: u64 = 0;
    network probe_net_last_fire_ms: u64 = 0;
    // S2 域：oracle 委员会探针 + 认证回合记录（price-feed:167 声明形态）
    network oracle cert_probe;
    network probe_rounds: u64 = 0;
    network probe_last_signers_raw: Vec<u64> = Vec::new();
    network probe_last_signers_nodes: Vec<String> = Vec::new();
    instance probe_propose_count: u64 = 0;

    // R3（路线② E2）域：认证裁决 oracle 主题——先例 = 上面的 `cert_probe`
    // （price-feed:167 声明形态；probe/mod.rs:13-16 已证子模块不能自带 state!，
    // 故新主题字段并入本块）。probe 的 cert_probe 保留不动，作为机制对照面。
    network oracle cert_verdict;
    // R3 arming：待裁 deal 的共识选择（network 域 = 共识持久、全节点可见；
    // 仲裁 R2#1-a）。init 只携带 price-feed 已证的 `avg_num`/`target` 二字段
    // （风险 R2），待裁对象改由本字段经共识状态传给全体节点的 propose；
    // 未 arm 时为空串，propose fail-closed。
    network e2_armed_deal: String = String::new();
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
// R3 指向：committee_certified 的 certified 回调面不入本矩阵（cert 即认证，
// origin=ZERO 过不了地址门）；其门禁台账见 committee_certified.rs 模块头 E2 表。
// ---------------------------------------------------------------------------

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Access { Buyer, Seller, BuyerOrSeller, Broker, Committee, Anyone }

/// Broker identity for devnet runs. W1-A: pinned by the T4.5 self-signed
/// notarize probe (D4b) — the string below returned status=1 (Ok(seq)) on
/// `notarize("probe-deal-d4b", <this string>, ...)`; per the from==caller
/// check (enforced before any state write) that means it equals
/// `ctx.caller.to_string()` exactly, EIP-55 checksummed hex. Evidence: tx
/// 0xf962ef3bb9ff4fc16a2830fd6e46c816e1963ae2522a0c2ab3759aa8f466c9af
/// (workflow-out/w1a-call-poc.txt). TODO(W2): real deployer identity via
/// the real deployment flow.
const BROKER: &str = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266";

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
    ("apply_committee_verdict", Access::Committee),  // caller 须为委员会成员且 signers 包含 caller；R2 起扁平 eth wire（verdict_code+signers），仍无签名、真实 oracle 认证 TODO(W4)（committee.rs:12-18 生产路径）（仲裁#1）
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
// 调用通道注记（T4.5 实测，D8b 备选落地）：shaker serve 的虚拟主机 HTTP 面
// 仅服务 `export = http` 的 instance 方法（对 native 面全部 Not found，探针
// 存档 workflow-out/w1a-call-poc.txt）——而本 crate 方法清单冻结、不得新增
// http 包装方法。故 Funded 路径 + 探针五方法（faucet/create_deal/fund/
// notarize/deal_info）按 D8b 备选加 `export = eth`，经容器内 cast 以 ETH ABI
// 调用；属性面变化而已，方法清单/矩阵零增删。其余方法维持 native 形态。
// W1-B2 属性面增补（D3）：正常流/keeper 所需的 network 方法补 `export = eth`
//（submit_deliverable/complete/claim_timeout/cancel/committee_config/
// evidence_entries_json/balance_of/due_deals），先例 = W1-A 五方法；仅属性行
// + 行内注释，方法清单/ACCESS_MATRIX/函数体零改动。
// open_dispute / apply_committee_verdict —— 对抗流组件，W1-B2 曾刻意不 eth 化
//（R2#2 注记 / R3 结构体参数无 EthAbiType）；R2 路线①解除：两者均 eth 导出，
// apply_committee_verdict 的 wire 参数扁平化为 (uint8,string[])（plan.md §4）。
// R3（路线②）通道分工（committee_certified.rs）：e2_configure 的 bytes32[] wire
// 面不在 rpc.py 编码器支持集（string/uint*/bool/string[]）——**走 cast send 通道**
//（docker_exec_cast，S2 probe_configure 同形先例），_ABI 无此行、编码器零扩展
//（终裁冻结条款 1）；e2_arm / e2_net_config 走 NodeClient eth 收发（export = eth，
// 返回面 string 已支持）；e2_run_verdict_round 走 **cast call**（S2 §3/§4 实证：
// cast send 对内部异步提交类方法 status 1 但内层静默丢失）。
// 借用纪律（S5 实证，D3-2）：每个方法开头单点 reborrow
// `let state = &mut *ctx.network;`（只读 getter 用 `&*`），体内一律
// `state.<field>`；不逐处 `ctx.network.` 前缀——多字段并存时逐处前缀触发
// E0502（同时可变+不可变借用），单点 reborrow 后字段级分离借用编译通过。
// 标量字段统一 `*` 解引用（宏生成字段为 `&'static mut T` 句柄，
// erc20 `*state.total_supply` 同款）。

/// Devnet-only faucet so the demo can mint internal-ledger tokens.
/// TODO(W2): gate behind a DEMO flag; listed in the report's trust-assumption
/// table as a demo-only trust hole.
#[method::network(export = eth)]
pub fn faucet(ctx: &mut _, to: AgentId, amount: U128) -> LyquidResult<()> {
    // T4.5 通道形态（登记 implementation.md）：export = eth 要求参数实现
    // EthAbiType，v0.7.3 无 u128 裸型（仅 U64/U128/U256 alloy 包装，ethabi.rs:218-281）
    // ——故 wire 面收 U128（ABI uint128），边界 to::<u128>() 转回领域域，
    // 数值语义不变（native/call! 面不变，W1-B RPC 对齐以此为准）。
    let amount: u128 = amount.to::<u128>();
    let state = &mut *ctx.network;
    credit(state, &to, amount);
    log!(faucet, &format!("faucet:{}:+{}", to, amount));
    Ok(())
}

/// Broker creates a deal from an accepted assessment (see assessor.rs for the
/// instance->network two-step). The timeout must be estimate-derived.
#[method::network(export = eth)]
pub fn create_deal(
    ctx: &mut _,
    buyer: AgentId,
    seller: AgentId,
    amount: U128,
    fee_bps: u16,
    terms_digest: Digest,
    acceptance_digest: Digest,
    est_duration_ms: u64,
    est_confidence: u8,
) -> LyquidResult<DealId> {
    let state = &mut *ctx.network;
    require(Access::Broker, &ctx.caller, state, None)?;
    // T4.5 通道形态：同 faucet —— wire 面收 U128，边界转回 u128 领域域。
    let amount: u128 = amount.to::<u128>();
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
#[method::network(export = eth)]
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
    // T4.5 通道注记：本 devnet 构建的 eth_call 读路径对非-bartender lyquid
    // 一律 "Invalid contract address"（节点侧限制，对照实测：同 selector 对
    // bartender 可路由；登记 implementation.md，S4/W1-B 对齐范围）。
    // deal_info 因此不可达，转由 fund 的 Ok 路径经控制台输出与 deal_info
    // 完全相同的 DealView JSON（字面 "state":"Funded" 证据）——console
    // 输出非共识状态，语义零影响。
    {
        let deal = state.deals.get(&deal_id).ok_or_else(|| lyquid_error("no such deal"))?;
        let view = serde_json::to_string(&DealView::from(deal)).map_err(|e| lyquid_error(&format!("json serialize: {e}")))?;
        lyquid::println!("fund:deal_view: {}", view);
    }
    Ok(())
}

/// Append-only communication notarization. Anyone may submit; entries are
/// sequenced per deal. This is the fulfillment evidence the committee rules on.
/// 裁决时的证书根由本日志条目折叠派生（core::evidence_root，经 apply_committee_verdict 单点读取）。
#[method::network(export = eth)]
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

#[method::network(export = eth)] // W1-B2 属性面增补（D3），先例 W1-A 五方法
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
#[method::network(export = eth)] // W1-B2 属性面增补（D3），先例 W1-A 五方法
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
#[method::network(export = eth)] // W1-B2 属性面增补（D3）：keeper.py 写通道
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
#[method::network(export = eth)] // W1-B2 属性面增补（D3），先例 W1-A 五方法
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

// W1-B2 注记（R2#2）历史记录：open_dispute 曾刻意不 eth 化（对抗流留在 sim）。
// R2 路线①解除：本方法 eth 导出；参数 (DealId, Digest) = (string,string) 全 ABI
// 兼容，_ABI 行 W1-B2 已冻结（rpc.py `open_dispute(string,string)`）。
#[method::network(export = eth)]
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
///
/// R2 route ① wire shape: `(deal_id, verdict_code: u8, signers: Vec<AgentId>)`
/// = `(string,uint8,string[])`. Struct params have no EthAbiType, but bare
/// `u8` does (ethabi.rs:258-280; live precedent = create_deal's
/// `est_confidence`) and so does `Vec<AgentId>` (ethabi.rs:395; live
/// precedent = committee_config). The wire struct is rebuilt in-body from the
/// flat params, so the validation / verdict / write-back chain below is
/// byte-for-byte unchanged (committee.rs untouched).
/// Honest boundary: the flat wire still carries NO signature — the demo
/// placeholder stands; real authentication is the R3 route ② oracle certified
/// call (`committee_certified::committee_verdict_certified`, same helper).
///
/// R3 行为保持重构（仲裁 R1#3 / 风险 R7）：构建 wire 结构体之后的
/// **证书校验/裁决/写回/结算链整体搬入共享 helper `apply_cert_and_payout`**
/// （路线② 认证回调用同一个 helper）。本函数保留 wire 形态、Committee 地址门
/// 与 caller∈signers 检查——路线①语义零变化（G2 sim 零回退 + G3 对抗流复跑）。
#[method::network(export = eth)]
pub fn apply_committee_verdict(ctx: &mut _, deal_id: DealId, verdict_code: u8, signers: Vec<AgentId>) -> LyquidResult<()> {
    // R2 路线①：扁平 wire 参数 → wire 结构体（结构体与 into_domain 保留，
    // committee 域/壳零改动）。
    let cert = committee::CommitteeCertWire { verdict_code, signers };
    let state = &mut *ctx.network;
    // 仲裁#1：caller 须为委员会成员（require 的 Committee 臂，同一
    // committee_members 状态）且亲自签署本证书；wire 无签名为 demo 占位——
    // 真实提交者认证走 oracle certified call（R3 路线② 已落地：认证回调
    // committee_verdict_certified 复用同一 helper，签名集来自平台证书
    // ctx.cert.signers，经 cert 门做实质成员校验）。
    let caller = require(Access::Committee, &ctx.caller, state, None)?;
    if !cert.signers.iter().any(|s| *s == caller) {
        return Err(lyquid_error("caller must be among the certificate signers"));
    }
    // R3 行为保持：其后的校验/裁决/写回/结算链逐字搬入 helper（单点）。
    apply_cert_and_payout(state, deal_id, cert)
}

// --- committee config (demo: broker-managed; trust assumption documented) ---
// W1-B2（D3）：参数面 Vec<AgentId> 的 EthAbiType 有实现（impl<T: EthAbiType>
// EthAbiType for Vec<T>，ethabi.rs:395 实读），故可加 export=eth；demo 正常/
// 超时流不前置委员会配置（R2#2）——R2 起对抗流实调本方法（node 模式每次运行
// 前置 committee_config，地址制委员名单）。

#[method::network(export = eth)] // W1-B2 属性面增补（D3）：Vec 参数 ABI 兼容（R3）
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

#[method::network(export = eth)]
pub fn deal_info(ctx: &_, deal_id: DealId) -> LyquidResult<String> {
    let state = &*ctx.network;
    let deal = state.deals.get(&deal_id).ok_or_else(|| lyquid_error("no such deal"))?;
    // Consensus replay must not panic: serialization errors become platform
    // errors instead of an unwrap.
    let json = serde_json::to_string(&DealView::from(deal)).map_err(|e| lyquid_error(&format!("json serialize: {e}")))?;
    // T4.5 通道注记（登记 implementation.md）：本 devnet 构建（node main-latest
    // 0.8.x）的 eth_call 读路径对 lyquid 合约一律回 "Invalid contract
    // address"（节点侧问题，属 S4/W1-B RPC 对齐范围）；导出 getter 亦不可作
    // 交易发送（staticcall-only 路由，revert）。deal_info 的输出改经控制台
    // 单点导出（lyquid::println!，erc20 transfer 同款），shaker console 可取
    // ——控制台输出非共识状态，语义零影响。
    lyquid::println!("deal_info: {}", json);
    Ok(json)
}

#[method::network(export = eth)] // W1-B2 属性面增补（D3），先例 W1-A 五方法
pub fn evidence_entries_json(ctx: &_, deal_id: DealId) -> LyquidResult<String> {
    let state = &*ctx.network;
    Ok(serde_json::to_string(&state.evidence_log.get(&deal_id).cloned().unwrap_or_default())
        .map_err(|e| lyquid_error(&format!("json serialize: {e}")))?)
}

/// W1-B2（R1#1 明文豁免，唯一一处签名微调）：返回面 `u128` -> `U128`——裸
/// u128 无 EthAbiType（ethabi.rs:218-281，仅 U8..U64 + U64/U128/U256 包装），
/// 先例 = faucet/create_deal 的 amount 边界转换（本文件上方同款注释）。
/// rpc.py 按 uint128 解码，keeper/demo 断言口径不变。
#[method::network(export = eth)] // W1-B2 属性面增补（D3）+ 返回面 U128（R1#1）
pub fn balance_of(ctx: &_, agent: AgentId) -> LyquidResult<U128> {
    let state = &*ctx.network;
    Ok(U128::from(state.balances.get(&agent).copied().unwrap_or(0)))
}

/// Advisory-only listing of deals past their timeout at the CALLER-supplied
/// `now`. The parameter cannot move funds: the only guard on money movement
/// is `claim_timeout`, which re-derives time via `current_slot` — a forged
/// `now` at most perturbs this informational list. Signature kept identical
/// to the FakeNode mirror (rpc.py `due_deals(now)`); stage-four alignment.
#[method::network(export = eth)] // W1-B2 属性面增补（D3）：keeper 读通道；Vec 返回 ABI 兼容（R3）
pub fn due_deals(ctx: &_, now: u64) -> LyquidResult<Vec<DealId>> {
    let state = &*ctx.network;
    Ok(core::due_for_timeout(state.deals.iter(), now))
}

// ---------------------------------------------------------------------------
// Instance functions (node-local; LLM egress lives ONLY here)
// ---------------------------------------------------------------------------

/// Instance-side assessment (R1: export = eth restored in the 4×string wire
/// shape): assess a buyer brief with the LLM and return the report JSON STRING.
/// The caller (broker) then submits `create_deal` with the returned estimate
/// values — the documented two-step commit; nothing here touches consensus
/// state (instance `assessment_cache` only).
///
/// Wire shape (R1): `brief_json` is the DealBrief four-field JSON
/// (`{"buyer_profile_digest","seller_profile_digest","terms_digest",
/// "license_scope"}`; assessor.rs `#[derive(Deserialize)]` is the parse
/// contract). The former 7-param form (four brief strings + three backend
/// params) tripped solc "Stack too deep" on the generated instance stub in
/// SequenceBackend.sol — the 6×string variant compiled, so 4 parameters are
/// the safe margin. The 7-param record stays as the platform-limit archive:
/// workflow-out/w1b2-claim-probe-evidence.txt §2 and w1b2-r1-s3-assess.md §4.
///
/// Mode contract (R1#4): `api_key` OR `base_url` empty => HeuristicModel
/// (TB_LLM replay, offline-deterministic); both non-empty => LyquidLlmModel
/// (custom endpoint via chat_completions+bearer_auth, R1#4; empty base_url
/// with a key would mean stock OpenAI). The println line tags the mode so
/// console output doubles as mode evidence.
///
/// Backend params travel as METHOD PARAMETERS by design (devnet semantics):
/// the eth wire call includes them in calldata, so the "key" is visible to
/// whoever can read the chain anyway — a documented demo trust hole, to be
/// moved behind instance config in W2'. Do NOT log the key.
#[method::instance(export = eth)] // R1 恢复导出：7→4 string（solc 6-string 实测边界，D3）
pub fn assess_brief(
    ctx: &mut _,
    brief_json: String,   // DealBrief 四字段的 JSON 串（R1 wire 形态）
    base_url: String,
    api_key: String,
    model: String,
) -> LyquidResult<String> {
    let brief: assessor::DealBrief = serde_json::from_str(&brief_json)
        .map_err(|e| lyquid_error(&format!("brief parse: {e}")))?;
    // 模式契约（R1#4）：api_key/base_url 任一为空 => HeuristicModel（TB_LLM
    // 回放，离线确定）；双非空 => LyquidLlmModel（R1#4 后端构造）。
    let (mode, report) = if api_key.is_empty() || base_url.is_empty() {
        let r = assessor::assess(&assessor::HeuristicModel, &brief)
            .map_err(|e| lyquid_error(&format!("assess(replay): {e}")))?;
        ("heuristic", r)
    } else {
        let lm = assessor::LyquidLlmModel::new(&base_url, &api_key, &model)
            .map_err(|e| lyquid_error(&e))?;
        let r = assessor::assess(&lm, &brief)
            .map_err(|e| lyquid_error(&format!("assess(llm): {e}")))?;
        ("llm", r)
    };
    // R2#1 序列化单点：返回面 = assessor::report_json 产出的报告 JSON 串。
    // W1-B2 编译修复（与本轮探针无关，登记 implementation.md）：report_json 的
    // Err 类型是 String，而 lyquid_error 收 &str——原直接 map_err(lyquid_error)
    // 在 wasm 目标下 E0631，改为闭包转接（语义零变化）。
    let json = assessor::report_json(&report).map_err(|e| lyquid_error(&e))?;
    // instance 缓存按 brief 摘要串键（「先评估后建 deal」时序下 deal 尚不
    // 存在，DealId 键不可用；本方法唯一 instance 写点）。
    let key = format!(
        "{}|{}|{}|{}",
        brief.buyer_profile_digest, brief.seller_profile_digest, brief.terms_digest, brief.license_scope
    );
    ctx.instance.assessment_cache.write().insert(key, report);
    lyquid::println!("assess_brief: mode={mode} report={json}");
    Ok(json)
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

/// R3（路线②）：裁决链单点 —— **证书校验、裁决映射、misconduct 镜像、状态写回
/// 与资金结算只有这一份实现**。两个调用方：
///   - 路线① `apply_committee_verdict`（扁平 eth wire + Committee 地址门 +
///     caller∈signers 的 demo 占位认证）；
///   - 路线② `committee_certified::committee_verdict_certified`（certified
///     回调，签名集来自平台证书 `ctx.cert.signers`，映射为 NodeID 显示串）。
/// 两条路线的信任差异只在「谁认证了 signer 集」；此后的语义完全共享
/// （core::apply_verdict 单点，committee.rs 零改动）。
///
/// **这是资金路径**：末尾 apply_payout → credit 真实结算（plan §3.2-E/H）。
/// evidence_root 由本函数从**当前全量证据日志**折叠（into_domain 单点，
/// core.rs:225-231 读-算-校同源契约），调用方不得自带根。
///
/// `pub(crate)`：仅 crate 内可见（跨模块调用需要；对外方法面不变）。
pub(crate) fn apply_cert_and_payout(state: &mut __lyquid::NetworkState, deal_id: DealId, cert: committee::CommitteeCertWire) -> LyquidResult<()> {
    let verdict_code = cert.verdict_code;
    // 权威源是 committee_config 写入的 network 状态；committee::members() 只是
    // instance 侧占位 shim（本函数不调用它）。S5-verified（was
    // SPIKE(W1)）: `state.committee_members.iter()` 的语法即平台 HashMap
    // 句柄的常规迭代，编译通过即证据。
    // 顺序无关性：`members.contains(s)` 与阈值比较均与迭代顺序无关
    // （ahash 确定性种子下 HashMap 迭代本身也确定，见 prelude::new_hashmap）。
    let members: Vec<AgentId> = state.committee_members.iter().map(|(m, _)| m.clone()).collect();
    let threshold = *state.committee_threshold as usize;
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
    // R2 取证缝：misconduct 无 getter 且方法清单冻结（不得新增方法），故走既有
    // println 观测缝（先例 fund 的 deal_view、deal_info）。打印**累计**计数视图
    // （每个 Ok 裁决都打，NotFulfilled 场景的对照点是计数不增而非无行）；
    // println 非共识状态，语义零影响，计数单点仍在 core。R3：路线② 回调经同一
    // helper 同样打本行（console 取证=node1），两路线计数视图可直接对照。
    {
        let mut counts: Vec<(AgentId, u32)> =
            state.misconduct.iter().map(|(k, v)| (k.clone(), *v)).collect();
        counts.sort();
        let view = counts.iter().map(|(k, v)| format!("{k}={v}")).collect::<Vec<_>>().join(",");
        lyquid::println!("apply_verdict: deal={} verdict={} misconduct=[{}]", deal_id, verdict_code, view);
    }
    Ok(())
}

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
