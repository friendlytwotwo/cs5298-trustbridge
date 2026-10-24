//! S1 timer probe — `TriggerMode::Once(ms)` semantics on the multi-node
//! devnet (W1-B1 plan §③-T3).
//!
//! Dual observation domains, deliberately separated:
//!   - instance domain (`probe_fires`, per-node, non-consensus): what THIS
//!     node's timer did locally. Node-local, resets on redeploy/restart.
//!   - network domain (`probe_net_fires`, consensus): exactly-once judging
//!     domain. `probe_on_timer` reaches it only through `call!` ->
//!     `probe_mark_fire` (the timeout.rs A-grade cross-call form), so every
//!     accepted fire is sequenced and replayed by all nodes.
//!
//! Experiment protocol (per round): `probe_reset_net` (cast send) -> read
//! baseline via `probe_get_report` -> `probe_arm(5000)` on each node under
//! test -> poll `probe_get_report` -> delta judgement
//! `(probe_net_fires - baseline) == number of successful arms`.
//!
//! Call channel facts (W1-A, implementation.md §④): probe methods callable
//! from outside are non-view `export = eth` (cast send; `()` and bool
//! returns both fine), observation goes through `lyquid::println!` +
//! `shaker console`; `eth_call` reads are broken for non-bartender lyquids
//! on this devnet build, so nothing here relies on reads.

use lyquid::prelude::*;
use crate::LyquidResult;

/// Arm a one-shot timer on THIS node's instance: resets the instance
/// counters, remembers registration wall-clock, and registers
/// `TriggerMode::Once(delay_ms)`. Non-view (cast send channel).
#[method::instance(export = eth)]
pub fn probe_arm(ctx: &mut _, delay_ms: u64) -> LyquidResult<()> {
    *ctx.instance.probe_fires.write() = 0;
    let now = lyquor_api::systime()?;
    *ctx.instance.probe_registered_at_ms.write() = now;
    *ctx.instance.probe_last_fire_at_ms.write() = 0;
    *ctx.instance.probe_arm_delay_ms.write() = delay_ms;
    // SPIKE(W1-B1): trigger target is the default-group instance method
    // `probe_on_timer`; the `= now` expr freezes the registration-time value
    // into the trigger input (encode_by_fields semantics, primitives
    // src/lib.rs:461-475). `TriggerMode::Once(0)` = "immediate" per
    // primitives/src/lib.rs:159-168.
    trigger!(probe_on_timer(fired_at_ms: u64 = now), TriggerMode::Once(delay_ms));
    lyquid::println!("probe_arm: node={} delay_ms={} registered_at_ms={}", ctx.node_id, delay_ms, now);
    Ok(())
}

/// Control group for experiment (c): periodic firing via `Recurrent`.
/// Arms without resetting the instance counters so successive periods are
/// observable as increments.
#[method::instance(export = eth)]
pub fn probe_arm_recurrent(ctx: &mut _, interval_ms: u64) -> LyquidResult<()> {
    let now = lyquor_api::systime()?;
    *ctx.instance.probe_registered_at_ms.write() = now;
    *ctx.instance.probe_arm_delay_ms.write() = interval_ms;
    trigger!(probe_on_timer(fired_at_ms: u64 = now), TriggerMode::Recurrent(interval_ms));
    lyquid::println!("probe_arm_recurrent: node={} interval_ms={} registered_at_ms={}", ctx.node_id, interval_ms, now);
    Ok(())
}

/// Trigger target. Instance-local bookkeeping first, then the consensus
/// observation via the A-grade cross-call (timeout.rs:52-59 form). The
/// `fired_at_ms` param matches the trigger input encoding exactly (decode is
/// by serde field name, primitives/src/lib.rs:478-486).
#[method::instance]
fn probe_on_timer(ctx: &mut _, fired_at_ms: u64) -> LyquidResult<()> {
    let n = {
        let mut fires = ctx.instance.probe_fires.write();
        *fires += 1;
        *fires
    };
    let now = lyquor_api::systime()?;
    *ctx.instance.probe_last_fire_at_ms.write() = now;
    lyquid::println!("probe FIRE #{} node={} at_ms={} (trigger payload fired_at_ms={})", n, ctx.node_id, now, fired_at_ms);
    let self_id = ctx.lyquid_id;
    call!((self_id).probe_mark_fire(fired_at_ms: u64 = now) -> (ok: LyquidResult<bool>)).ok?;
    Ok(())
}

/// Consensus-side fire record — the exactly-once judging domain.
/// Sequenced on the shared anvil backend; replayed identically by all nodes.
#[method::network(export = eth)]
pub fn probe_mark_fire(ctx: &mut _, fired_at_ms: u64) -> LyquidResult<bool> {
    let state = &mut *ctx.network;
    *state.probe_net_fires += 1;
    let n = *state.probe_net_fires;
    *state.probe_net_last_fire_ms = fired_at_ms;
    lyquid::println!("probe NET FIRE #{} fired_at_ms={}", n, fired_at_ms);
    Ok(true)
}

/// Baseline step for every experiment round: zero the consensus counters
/// (cast send reachable). Kept as its own network method instead of folding
/// into `probe_arm` so the reset is itself a consensus fact one can point at
/// in the archived transcript.
#[method::network(export = eth)]
pub fn probe_reset_net(ctx: &mut _) -> LyquidResult<()> {
    let state = &mut *ctx.network;
    let old = *state.probe_net_fires;
    *state.probe_net_fires = 0;
    *state.probe_net_last_fire_ms = 0;
    lyquid::println!("probe_reset_net: cleared (old net_fires={})", old);
    Ok(())
}

/// Network-domain report — the pollable observation primitive for the a/b/c
/// rounds. SPIKE(W1-B1): instance-method printlns are NOT relayed by the
/// v0.8.1 node console (probe_arm/probe_get_report stay silent while network
/// printlns flow; live-tested, archived in w1b1-s1-timer.md) — so every
/// console observation MUST ride a network method. This one prints the
/// consensus counters (the judging domain) as one JSON line.
#[method::network(export = eth)]
pub fn probe_net_report(ctx: &mut _) -> LyquidResult<()> {
    let state = &mut *ctx.network;
    let net_fires = *state.probe_net_fires;
    let net_last_fire_ms = *state.probe_net_last_fire_ms;
    lyquid::println!(
        "probe_net_report: {{\"probe_net_fires\":{},\"net_last_fire_ms\":{}}}",
        net_fires, net_last_fire_ms
    );
    Ok(())
}

/// Full report in one println (instance + network domains) — single console
/// fetch per poll. `LyquidResult<()>` return: cast send carries it fine
/// (W1-A fund precedent); observation is via console, not return value.
/// Note (SPIKE above): only the network half of this line is console-visible
/// on node v0.8.1; kept for parity with the plan and future node fixes.
#[method::instance(export = eth)]
pub fn probe_get_report(ctx: &mut _) -> LyquidResult<()> {
    let fires = *ctx.instance.probe_fires.read();
    let registered_at = *ctx.instance.probe_registered_at_ms.read();
    let last_fire_at = *ctx.instance.probe_last_fire_at_ms.read();
    let arm_delay = *ctx.instance.probe_arm_delay_ms.read();
    let net_fires = *ctx.network.probe_net_fires;
    let net_last_fire_ms = *ctx.network.probe_net_last_fire_ms;
    lyquid::println!(
        "probe_report: {{\"node\":\"{}\",\"instance\":{{\"probe_fires\":{},\"registered_at_ms\":{},\"last_fire_at_ms\":{},\"arm_delay_ms\":{}}},\"network\":{{\"probe_net_fires\":{},\"net_last_fire_ms\":{}}}}}",
        ctx.node_id, fires, registered_at, last_fire_at, arm_delay, net_fires, net_last_fire_ms
    );
    Ok(())
}
