//! Timeout execution: "off-chain trigger; on-chain guard".
//!
//! Verified risk (feasibility report R1): multi-node timer semantics for
//! `TriggerMode::Once(ms)` are undocumented (who fires, restart dedup, latency).
//! Therefore the PRIMARY design never depends on trigger correctness:
//!
//!   watcher (any node, instance fn) scans deals -> submits `claim_timeout`
//!   -> network guard re-derives eligibility from consensus state and time.
//!
//! Duplicate/late/racing watcher submissions are harmless: the guard is
//! idempotent (Funded-only, terminal-safe). The native `trigger!` /
//! `TriggerMode::Once` registration below is an OPTIMIZATION to be enabled
//! after SPIKE(W1-1) proves its semantics on the 4-node devnet with
//! kill/restart tests.
//!
//! Watcher sources, in preference order:
//!   1. instance trigger on this node (if spike OK),
//!   2. an agent-side keeper loop (scripts/keeper.py) hammering the HTTP API,
//!   3. any third party — the claim is permissionless by design.

use lyquid::prelude::*;
use crate::types::DealId;
use crate::LyquidResult;

/// Instance watcher body: fetch due deals via the network getter and submit
/// claims for each. Ledger effects are zero when the guard rejects — safe to
/// re-run, safe to run on every node.
// W2 wire note: the old two-line sketch (`call!(self, due_deals(now))` +
// per-id `claim_timeout`) is now LANDED as this body; the remaining inline
// SPIKE(W1) items (instance attribute/Context shape, consensus-time wiring
// inside an instance fn, the `call!` cross-call form) were all S5-verified —
// conclusions inline below. What remains is exactly the W1-1 trigger
// registration marked further down (doc comment above + SPIKE_1 const).
// 接线说明（阶段二）：`current_slot` 取自 lib.rs 的同名单点函数
// （本段已升 pub(crate)），不得另开时间源（G5 时间单点收敛；
// `due_deals(now)` 仅 advisory）。
// S5-verified（was SPIKE(W1)）：`#[method::instance]` + `ctx: &mut _` 即
// template 同款形态（lyquid-template/src/lib.rs:48），编译通过为证。
#[method::instance]
pub fn watcher_step(ctx: &mut _) -> LyquidResult<Vec<DealId>> {
    // G5 时间单点：now 只取自 lib.rs 的 current_slot 单点（本段升为
    // pub(crate)，纯可见性变化）；旧签名的 current_slot 入参移除——
    // 调用方不再能注入伪造时钟。S5-verified（was SPIKE(W1)）：instance fn
    // 内取共识时间 = 复用 crate::current_slot 单点（内部
    // lyquor_api::chain_pos()，无 ctx 依赖），无需 ctx 派生。
    let now = crate::current_slot();
    // S5-verified（was SPIKE(W1)）：call! 跨调用 = basicswap 命名参数 +
    // 返回解包形态（basicswap/src/lib.rs:31），同 crate 自调用以
    // ctx.lyquid_id 为目标（CallContext/InstanceContext 字段）。A 档落地。
    // due_deals 为 advisory getter，动钱守卫在 claim_timeout 内部重新推导。
    let self_id = ctx.lyquid_id;
    let due: Vec<DealId> =
        call!((self_id).due_deals(now: u64 = now) -> (due: LyquidResult<Vec<DealId>>)).due?;
    let mut claimed = Vec::new();
    for id in due {
        // S5-verified（was SPIKE(W1)）：guard 幂等（Funded-only,
        // terminal-safe），重复/迟到提交无害；单笔失败整轮中断（`?`，与
        // 原草图一致）；幂等语义由 core 测试既钉（阶段一）。
        let _ = call!((self_id).claim_timeout(deal_id: DealId = id.clone()) -> (ok: LyquidResult<bool>)).ok?;
        claimed.push(id);
    }
    Ok(claimed)
}

/// Spike #1 registration sketch (enable only after W1 verification):
///
///   // in an instance init or start method:
///   trigger!(
///       "trustbridge-watcher",
///       "watcher_step",
///       vec![],
///       TriggerMode::Recurrent(5_000) // every 5s
///   )?;
///
/// SPIKE(W1-1) acceptance: on the 4-node devnet, with a deal past deadline,
/// (a) exactly one refund lands (guard dedups), (b) killing/restarting nodes
/// never double-refunds, (c) firing latency < 2x the trigger period.
pub const SPIKE_1_TRIGGER_REGISTRATION: &str = "see doc comment above";
