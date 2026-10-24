//! Timeout execution: "off-chain trigger; on-chain guard".
//!
//! W1-B1 S1 verdict (was SPIKE(W1-1), resolved 2026-10-24; evidence:
//! workflow-out/w1b1-s1-timer.md): native `TriggerMode::Once`/`Recurrent`
//! instance triggers registered fine (arm txs status=1, no node-side errors)
//! but NEVER fired on the 4-node multi devnet (v0.8.1) — exactly-once delta
//! was 0-of-2 arms (experiment a), no restart replay (b), no firing at any
//! of {2000,5000,10000} ms nor under Recurrent(2000) with 12 forced blocks
//! (c). Therefore native triggers are NOT usable on this environment and
//! the PRIMARY design below is the only path (its on-chain guard was the
//! safety net all along — no code change needed):
//!
//!   watcher (any node, instance fn) scans deals -> submits `claim_timeout`
//!   -> network guard re-derives eligibility from consensus state and time.
//!
//! Duplicate/late/racing watcher submissions are harmless: the guard is
//! idempotent (Funded-only, terminal-safe). The watcher's first source is an
//! agent-side keeper loop (scripts/keeper.py, W1-B2) hammering the ETH API;
//! any third party also works — the claim is permissionless by design.

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
// conclusions inline below. The last open item (W1-1 trigger registration)
// was settled by W1-B1 S1: native triggers never fire on the multi v0.8.1
// devnet (workflow-out/w1b1-s1-timer.md §4), so this watcher is driven by a
// keeper loop, not by a native trigger.
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

/// SPIKE(W1-1) — RESOLVED by W1-B1 S1 (2026-10-24, workflow-out/w1b1-s1-timer.md).
/// Three-column record, per the SPIKE discipline (user ruling 3, W1-A):
///   假设: `TriggerMode::Once(ms)` on the 4-node devnet fires exactly once
///         per arm, survives node kill/restart without double-firing, with
///         firing latency < 2x the period (the acceptance below).
///   验证: probe Lyquid `Lyquid-zz2jue…` on multi v0.8.1 (w1b1-s1-timer.md):
///         (a) 2 arms (node1+node2, status=1) -> network delta 0;
///         (b) node services killed/restarted (anvil kept) -> 0->0, chain
///             continuous (block 42->46), no replay;
///         (c) delays {2000,5000,10000} + Recurrent(2000) with 12 forced
///             blocks over 60s -> zero fires in every group.
///   结论: native instance triggers DO NOT FIRE on this environment —
///         unusable; keeper mode (this watcher + permissionless
///         `claim_timeout`) is the shipped path. Registration sketch kept
///         below for the record and for a future node version that fixes
///         trigger scheduling (retest before enabling).
///
///   // in an instance init or start method:
///   //   trigger!("trustbridge-watcher", "watcher_step", vec![], TriggerMode::Recurrent(5_000))?;
pub const SPIKE_1_TRIGGER_REGISTRATION: &str = "resolved unusable 2026-10-24: see doc comment above";
