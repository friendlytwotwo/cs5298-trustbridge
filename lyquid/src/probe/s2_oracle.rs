//! S2 oracle probe — one full committee certification round on the multi
//! devnet (W1-B1 plan §③-T4), price-feed skeleton with all outbound HTTP
//! removed (proposal values are generated in-contract).
//!
//! Structure mirrors ldk lyquid-examples/price-feed/src/lib.rs:
//!   - `network oracle cert_probe;` state (price-feed:167 form) declared in
//!     the crate root `state!` block (R1: submodule `state!` does not compile).
//!   - two-phase instance methods MUST be named literally `propose` and
//!     `aggregate` — the categorize macro arms match those idents verbatim
//!     (ldk lyquid/src/runtime/syntax.rs:447 `fn aggregate`, :470 `fn
//!     `propose``). Plan §④ named them `probe_propose`/`probe_aggregate`;
//!     that spelling cannot route through the oracle machinery (SPIKE
//!     registered in implementation.md).
//!   - serde decode is BY FIELD NAME (primitives src/lib.rs:478-486), so
//!     `propose`/`aggregate` decode `avg_num`/`target` and
//!     `probe_on_certified` decodes `round` — exactly the names the encoding
//!     sites use (run_round's init params, aggregate's certified payload).
//!     Note: price-feed itself declares `_avg_num`/`_target`, which serde
//!     cannot match against the `avg_num` encoding — a latent upstream demo
//!     bug at rev fd575e8 (verified with a standalone serde repro); this
//!     probe pins the correct spelling.
//!   - `probe_configure` guard is the platform-built-in `eth_guard = creator`
//!     (proc src/lib.rs:953-961 domain: mutable network eth export, main
//!     group) instead of price-feed's initializer-field check: the platform
//!     only auto-runs functions literally named `constructor`
//!     (ldk lyquid/src/lib.rs:59-66), and the shared escrow crate must not
//!     grow a real constructor (deployment-behavior change, out of scope).

use lyquid::prelude::*;
use serde::{Deserialize, Serialize};
use crate::LyquidResult;

/// In-contract generated proposal (replaces price-feed's fetched tickers).
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct ProbeProposal {
    /// Per-node propose counter snapshot.
    pub round: u64,
    /// Proposing node id (`Node-…` display form).
    pub node: String,
    /// `lyquor_api::systime()` at propose time.
    pub ts_ms: u64,
}

/// Certified payload: the aggregated value carried into the network callback.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct ProbeRound {
    pub round: u64,
    pub node: String,
    pub ts_ms: u64,
    /// `ctx.cert.signers` RAW domain (SignerID = u32, widened to u64).
    pub signers_raw: Vec<u64>,
    /// Mapped `ctx.signer_node_id(..)` display forms.
    pub signers_nodes: Vec<String>,
}

/// Stage the certification committee + threshold. Only lands in oracle
/// STAGING (`StateVar::initialize`, source.rs:540-544) — activation is the
/// host-driven two-phase epoch advance/finalize (T4 step 3).
/// ABI face: `probe_configure(bytes32[],uint16)`; caller must be the deploy
/// key (anvil#0) or the creator guard rejects the call.
#[method::network(export = eth, eth_guard = creator)]
pub fn probe_configure(ctx: &mut _, node_ids: Vec<NodeID>, threshold: u16) -> LyquidResult<bool> {
    if node_ids.is_empty() {
        return Err(LyquidError::LyquorRuntime("probe_configure: committee cannot be empty".into()));
    }
    let target = OracleTarget {
        seq_id: lyquor_api::sequence_backend_id()?,
        target: OracleServiceTarget::LVM(ctx.lyquid_id),
    };
    // price-feed:225-234 mirror — `initialize` only stages; false means the
    // staging write was rejected (e.g. target already active, epoch != 0).
    if !ctx
        .network
        .cert_probe
        .clone()
        .initialize(&mut ctx, target, node_ids.clone(), threshold)
    {
        return Err(LyquidError::LyquorRuntime("probe_configure: oracle staging initialization failed".into()));
    }
    lyquid::println!(
        "probe_configure: staged committee of {} nodes threshold={} (dest epoch advance/finalize required to activate)",
        node_ids.len(),
        threshold
    );
    Ok(true)
}

// Two-phase proposal: generated in-contract, zero outbound HTTP.
// Group suffix `cert_probe` ties these to the `cert_probe` oracle topic.
// Param names `avg_num`/`target` match run_round's init encoding.
#[method::instance(group = oracle::two_phase::cert_probe)]
fn propose(ctx: &mut _, avg_num: u16, target: OracleTarget) -> LyquidResult<ProbeProposal> {
    let count = {
        let mut c = ctx.instance.probe_propose_count.write();
        *c += 1;
        *c
    };
    let ts = lyquor_api::systime()?;
    let proposal = ProbeProposal { round: count, node: ctx.node_id.to_string(), ts_ms: ts };
    lyquid::println!(
        "probe_propose: node={} round={} ts_ms={} (avg_num={} target.seq_id={:?})",
        ctx.node_id, count, ts, avg_num, target.seq_id
    );
    Ok(proposal)
}

// Two-phase aggregation: mirror price-feed:300-366. `avg_num` proposals are
// enough at threshold 1; the round number is the max seen, the node label the
// first seen. SPIKE(W1-B1): CertifiedCallParams construction form copied from
// the official example; correctness judged by compile + live round.
#[method::instance(group = oracle::two_phase::cert_probe)]
fn aggregate(ctx: &_) -> LyquidResult<Option<CertifiedCallParams>> {
    let init = decode_by_fields!(ctx.init, avg_num: u16, target: OracleTarget)
        .ok_or_else(|| LyquidError::LyquorRuntime("probe_aggregate: failed to decode init params".into()))?;
    if init.target.seq_id != lyquor_api::sequence_backend_id()? {
        return Ok(None);
    }
    if ctx.inputs.len() < init.avg_num as usize {
        return Ok(None);
    }
    let mut round = ProbeRound::default();
    round.ts_ms = lyquor_api::systime()?;
    for i in ctx.inputs {
        if let Some(p) = lyquor_primitives::decode_object::<ProbeProposal>(&i.input) {
            if round.round < p.round {
                round.round = p.round;
            }
            if round.node.is_empty() {
                round.node = p.node;
            }
            if round.ts_ms > p.ts_ms {
                round.ts_ms = p.ts_ms;
            }
        }
    }
    if round.round == 0 {
        // no decodable proposal arrived — refuse to certify anything
        return Ok(None);
    }
    lyquid::println!("probe_aggregate: aggregated round={} node={} from {} input(s)", round.round, round.node, ctx.inputs.len());
    let method = "probe_on_certified".into();
    // field name `round` must equal probe_on_certified's parameter name
    let input = encode_by_fields!(round: ProbeRound = round).into();
    Ok(Some(CertifiedCallParams {
        origin: Address::ZERO,
        method,
        input,
        target: init.target, // LVM: the `probe_on_certified` network fn of this lyquid
    }))
}

/// Core observation point: the certified network callback. Prints the RAW
/// `ctx.cert.signers` (Vec<SignerID>, SignerID=u32: primitives/src/oracle.rs:65,130-136)
/// and the `ctx.signer_node_id(u64)` mapping (price-feed:401-406 mirror,
/// CertifiedContextImpl::signer_node_id runtime/mod.rs:560), then records
/// both into network state.
#[method::network(group = oracle::certified::cert_probe::two_phase)]
fn probe_on_certified(ctx: &mut _, round: ProbeRound) -> LyquidResult<bool> {
    let signer_ids = ctx.cert.signers.clone();
    lyquid::println!(
        "probe_on_certified: ctx.cert.signers RAW = {:?} (type Vec<SignerID>=Vec<u32>, len={})",
        signer_ids,
        signer_ids.len()
    );
    let mut raw: Vec<u64> = Vec::new();
    let mut nodes: Vec<String> = Vec::new();
    for signer_id in signer_ids {
        raw.push(signer_id as u64);
        match ctx.signer_node_id(signer_id as u64) {
            Some(nid) => {
                lyquid::println!("probe_on_certified: signer {} -> {}", signer_id, nid);
                nodes.push(nid.to_string());
            }
            None => lyquid::println!("probe_on_certified: signer {} -> <unmapped>", signer_id),
        }
    }
    let state = &mut *ctx.network;
    *state.probe_rounds += 1;
    let rounds = *state.probe_rounds;
    *state.probe_last_signers_raw = raw;
    *state.probe_last_signers_nodes = nodes;
    lyquid::println!(
        "probe_on_certified: payload(round={} node={} ts_ms={}) recorded; probe_rounds={}",
        round.round, round.node, round.ts_ms, rounds
    );
    Ok(true)
}

/// Drive one certification round: `propose_and_certify` (protocol.rs:514-522)
/// + `submit_certified_call!` (price-feed:451-473 mirror). Returns false when
/// the oracle produced nothing (inactive/staging-only, or aggregate None).
#[method::instance(export = eth)]
pub fn probe_run_round(ctx: &mut _) -> LyquidResult<bool> {
    let target = OracleTarget {
        seq_id: lyquor_api::sequence_backend_id()?,
        target: OracleServiceTarget::LVM(ctx.lyquid_id),
    };
    let o = ctx.network.cert_probe.clone();
    lyquid::println!("probe_run_round: node={} starting propose_and_certify (avg_num=1)", ctx.node_id);
    // init field names here are the contract: propose/aggregate decode
    // `avg_num`/`target` (see module header note on price-feed's underscore bug)
    let call = o.propose_and_certify(
        &mut ctx,
        target,
        lyquor_primitives::encode_by_fields!(avg_num: u16 = 1, target: OracleTarget = target).into(),
        None,
        None,
    )?;
    match call {
        Some(call) => {
            let _ = submit_certified_call!(call)?;
            lyquid::println!("probe_run_round: certified call submitted to the sequencing backend");
            Ok(true)
        }
        None => {
            lyquid::println!("probe_run_round: no certified call produced (oracle inactive or aggregate returned None)");
            Ok(false)
        }
    }
}

/// Wrap `StateVar::set_threshold` (source.rs:591-595). False when the oracle
/// epoch is still 0 (source.rs:268-271) — must run AFTER activation.
/// SPIKE(W1-B1): plan §④ specified `instance(export = eth)`; landed as
/// `network(export = eth)` because instance-method printlns are not
/// console-relayed on node v0.8.1 (see probe_net_report note) and the
/// `set_threshold` bool verdict is exactly what T4 step 5 must observe.
/// `StateVar::set_threshold`'s ctx param is unconstrained (`_ctx: &mut T`),
/// so the network context satisfies it.
#[method::network(export = eth)]
pub fn probe_bump_threshold(ctx: &mut _, new_thres: u16) -> LyquidResult<bool> {
    let target = OracleTarget {
        seq_id: lyquor_api::sequence_backend_id()?,
        target: OracleServiceTarget::LVM(ctx.lyquid_id),
    };
    let ok = ctx.network.cert_probe.clone().set_threshold(&mut ctx, target, new_thres);
    lyquid::println!("probe_bump_threshold: set_threshold({}) -> {} (false = epoch==0 or same-threshold)", new_thres, ok);
    Ok(ok)
}

/// Network-domain oracle observation dump — the console-visible twin of
/// `probe_config` (which stays instance-side for parity; its println is NOT
/// relayed by node v0.8.1, see the probe_net_report SPIKE). Prints the same
/// set: current/staging config, source-side get_epoch, and the DEST-side
/// epoch via `lyquor_api::fetch_oracle_info` (runtime/mod.rs:322 — the
/// channel the platform's own `validate_finalize_epoch` uses, source.rs:461-472).
/// SPIKE(W1-B1): the plan's first-choice accessor
/// `ctx.network.__internal.oracle_dest_epoch_info` is NOT guest-reachable —
/// `__internal` is generated without `pub` (proc lib.rs:1521; cargo check
/// E0616 archived) — `fetch_oracle_info` is the landed fallback. This line is
/// the wait condition for advance→finalize (T4 3b); `get_epoch` reads the
/// SOURCE-side current.epoch which stays 0 until finalize (source.rs:289-291,
/// 409) — never use it as the advance wait condition.
#[method::network(export = eth)]
pub fn probe_net_config(ctx: &mut _) -> LyquidResult<()> {
    let target = OracleTarget {
        seq_id: lyquor_api::sequence_backend_id()?,
        target: OracleServiceTarget::LVM(ctx.lyquid_id),
    };
    let o = ctx.network.cert_probe.clone();
    let cur = o.config_current(&ctx, target);
    let cur_threshold = cur.threshold;
    let cur_epoch = cur.epoch;
    let cur_size = cur.committee.len();
    let staging = o.config_staging(&ctx, target);
    let st_threshold = staging.threshold;
    let st_size = staging.committee.len();
    let src_epoch = o.get_epoch(&ctx, target);
    let (dest_epoch, dest_change) = match lyquor_api::fetch_oracle_info("cert_probe".to_string(), target, false)? {
        Some(info) => (info.epoch, info.change_count),
        None => (0, 0),
    };
    lyquid::println!(
        "probe_net_config: current(threshold={},committee={},epoch={}) staging(threshold={},committee={}) get_epoch(src)={} dest(epoch={},change_count={})",
        cur_threshold, cur_size, cur_epoch, st_threshold, st_size, src_epoch, dest_epoch, dest_change
    );
    Ok(())
}

/// Observation dump: current/staging oracle config, source-side get_epoch,
/// and the DEST-side epoch info via the host API `lyquor_api::fetch_oracle_info`
/// (runtime/mod.rs:322; the same channel the platform's own
/// `validate_finalize_epoch` uses to observe the destination before voting —
/// source.rs:461-472). SPIKE(W1-B1): the plan's first-choice accessor
/// `ctx.network.__internal.oracle_dest_epoch_info` is NOT guest-reachable —
/// `__internal` is generated without `pub` (proc lib.rs:1521, cargo check
/// E0616, archived) — so this plan-sanctioned fallback is the landed form.
/// Console note: instance printlns are not relayed on node v0.8.1 — use
/// `probe_net_config` for live observation; this method remains the
/// same-shaped instance twin for future node versions.
#[method::instance(export = eth)]
pub fn probe_config(ctx: &mut _) -> LyquidResult<()> {
    let target = OracleTarget {
        seq_id: lyquor_api::sequence_backend_id()?,
        target: OracleServiceTarget::LVM(ctx.lyquid_id),
    };
    let o = ctx.network.cert_probe.clone();
    let cur = o.config_current(&ctx, target);
    let cur_threshold = cur.threshold;
    let cur_epoch = cur.epoch;
    let cur_size = cur.committee.len();
    let staging = o.config_staging(&ctx, target);
    let st_threshold = staging.threshold;
    let st_size = staging.committee.len();
    let src_epoch = o.get_epoch(&ctx, target);
    let (dest_epoch, dest_change) = match lyquor_api::fetch_oracle_info("cert_probe".to_string(), target, false)? {
        Some(info) => (info.epoch, info.change_count),
        None => (0, 0),
    };
    lyquid::println!(
        "probe_config: node={} current(threshold={},committee={},epoch={}) staging(threshold={},committee={}) get_epoch(src)={} dest(epoch={},change_count={})",
        ctx.node_id, cur_threshold, cur_size, cur_epoch, st_threshold, st_size, src_epoch, dest_epoch, dest_change
    );
    Ok(())
}
