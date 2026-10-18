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

use crate::types::DealId;
use crate::LyquidResult;

/// Instance watcher body: fetch due deals via the network getter and submit
/// claims for each. Ledger effects are zero when the guard rejects — safe to
/// re-run, safe to run on every node.
// W2 wire note: the old two-line sketch (`call!(self, due_deals(now))` +
// per-id `claim_timeout`) is now LANDED as this body; what remains is exactly
// the SPIKE(W1) items marked inline below (instance attribute/Context shape,
// consensus-time wiring inside an instance fn, the `call!` cross-call form).
// 接线说明（阶段二）：`current_slot` 取自 lib.rs 的同名单点函数
// （本段已升 pub(crate)），不得另开时间源（G5 时间单点收敛；
// `due_deals(now)` 仅 advisory）。
// SPIKE(W1): `#[method::instance]` 属性与 `Context` 类型为 erc20 example 面
// （lib.rs 网络侧同款写法）；按该面书写，W1 落地时只换接线不改结构。
#[method::instance]
pub fn watcher_step(ctx: Context) -> LyquidResult<Vec<DealId>> {
    let _ = ctx;
    // G5 时间单点：now 只取自 lib.rs 的 current_slot 单点（本段升为
    // pub(crate)，纯可见性变化）；旧签名的 current_slot 入参移除——
    // 调用方不再能注入伪造时钟。SPIKE(W1): instance fn 内取共识时间的
    // 真实接线（ctx 派生 or crate helper）。
    let now = crate::current_slot();
    // SPIKE(W1): call! 跨函数调用形态；due_deals 为 advisory getter，动钱
    // 守卫在 claim_timeout 内部重新推导（lib.rs:306-316）。
    let due: Vec<DealId> = call!(ctx, due_deals(now))?;
    let mut claimed = Vec::new();
    for id in due {
        // SPIKE(W1): guard 幂等（Funded-only, terminal-safe），重复/迟到
        // 提交无害；单笔失败整轮中断（`?`，与原草图一致）。
        let _ = call!(ctx, claim_timeout(id.clone()))?;
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
