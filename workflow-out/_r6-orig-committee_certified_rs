//! R3（路线②）E2 四节点委员会演示：生产化的 oracle 认证接线。
//!
//! 把 W1-B1 的 `probe/s2_oracle.rs` 探针正主化为演示级接线——**多节点认证
//! 替换路线①的「broker 单点签署 + 占位串成员」**（implementation.md §6-#9 的
//! 两个占位性质）。与 probe 的关系：probe 保持不动作为机制对照面；本模块是
//! 演示级准生产接线（顶层壳模块，不入 probe/ ——该目录注记明言 W1-B1 SPIKE、
//! W2 移除，`probe/mod.rs:17-18`）。
//!
//! ## 机制（plan §3.1–§3.3）
//!
//! ```text
//! e2_configure(bytes32[] NodeID, th)   → oracle 主题 cert_verdict 的 staging
//! advance/finalize（cast call 平台内置）→ 委员会激活（dest epoch 是等待条件）
//! e2_arm(deal_id)                      → network 域 e2_armed_deal（单发全节点生效）
//! e2_run_verdict_round()（node1 单次）  → propose_and_certify
//!   propose   ← 每节点独立读 armed deal + network 证据日志，verdict 由链上证据派生
//!   aggregate ← 提案一致才出证（不一致 = 拒证 None）
//! committee_verdict_certified          ← 平台 certified call 送达（origin=ZERO）
//!   ctx.cert.signers → signer_node_id → NodeID 串 → CommitteeCertWire
//!   → crate::apply_cert_and_payout（= 路线① 同一 helper）
//!   → core::apply_verdict → apply_payout（真实结算）
//! ```
//!
//! 路线①② 共享 core::apply_verdict 单点，信任模型唯一；差异只在「谁认证了
//! signer 集」：路线① = Committee 地址门 + caller∈signers（demo 占位），
//! 路线② = 平台证书自身（签名集逐节点映射后由 `core::validate_cert` 四查）。
//!
//! ## E2 门禁台账（7 方法 × 面 × 实际门 × 是否触资金；仲裁 R1#3）
//!
//! | 方法 | 面 | 实际门 | 触资金 |
//! |---|---|---|---|
//! | `e2_configure` | network-eth | `eth_guard = creator`（部署钥 anvil#0，fail-closed） | 否（仅 oracle staging） |
//! | `e2_arm` | network-eth | `eth_guard = creator`（演示编排面，与 e2_configure 同口径；写共识状态） | 否 |
//! | `propose` | instance-two_phase | armed 检查 + deal 存在 + Disputed 检查（全 fail-closed）；只读 network 状态 | 否 |
//! | `aggregate` | instance-two_phase | 一致性拒证（deal/verdict 不一致 → None）；只组装 certified call | 否 |
//! | `committee_verdict_certified` | network-certified | **cert 门 = core::validate_cert**（全员 ∈ committee_members + 去重 + ≥threshold + evidence_root 匹配）；直调 fail-closed | **是**（共享 helper → apply_payout → credit 真实结算） |
//! | `e2_run_verdict_round` | instance-eth | 无门（仅发起认证回合；安全域 = oracle 委员会本身） | 否 |
//! | `e2_net_config` | network-eth | 无门（只读观测 dump） | 否 |
//!
//! **为何不入 ACCESS_MATRIX（lib.rs 矩阵审计面注记指向本表）**：
//! 矩阵的设计语义是「每行一个 network fn 的 require 地址门、require 是唯一
//! 执行点」；certified call 的 origin = ZERO（s2_oracle.rs:148 实证
//! `CertifiedCallParams { origin: Address::ZERO, .. }`），地址门必然 fail-closed。
//! 入矩阵须写「此行不经 require」的特例，破坏「一瞥即得的审计面」——故矩阵
//! 本体零增删，改由本表承担审计面。**probe 先例不可类推**：probe 网络方法
//! 不入矩阵属 SPIKE 例外（`probe/mod.rs:17-18` 明言 W2 移除/退役）**且零资金**；
//! 本模块的 `committee_verdict_certified` 触资金（§3.5 主场景即全额退款），
//! 必须自带台账。
//!
//! ## 通道纪律（plan §3.6）
//! - `e2_configure`：**cast send**（rpc.py `docker_exec_cast`；`bytes32[]` 不在
//!   NodeClient 编码器支持集，编码器零扩展 = 终裁冻结条款 1；S2 probe_configure
//!   同形实证 `w1b1-s2-oracle.md` §2）。
//! - `e2_arm` / `e2_net_config`：NodeClient eth 收发（export = eth；返回面
//!   string 已支持，先例 deal_info）。
//! - `e2_run_verdict_round`：**cast call**（S2 §3/§4 实证：cast send 对内部异步
//!   提交类方法 status 1 但内层静默丢失）。仅 node1 单次触发——propose 经 UPC
//!   广播自带全节点提案（protocol.rs:312/:316）；**禁多次触发**：首回合裁决已把
//!   deal 推离 Disputed，core.rs:199 的 Disputed 门必败。
//!
//! ## 只读边界
//! 本模块**只读** escrow 状态（deals / evidence_log），唯一的 escrow 写路径是
//! 认证回调经共享 helper 的裁决结算；不新开任何 escrow 方法、不触 ACCESS_MATRIX、
//! 不改 types/core/committee（冻结面）。

use lyquid::prelude::*;
use serde::{Deserialize, Serialize};

use crate::committee;
use crate::types::*;
use crate::LyquidResult;

/// 单提案 wire：serde 按**字段名**解码（P6；probe `ProbeProposal` 同款——
/// price-feed 的 `_avg_num`/`_target` 是上游潜在 bug，本模块钉正确拼写）。
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct VerdictProposal {
    /// 被检视的 deal（来源 = network 域 armed deal）。
    pub deal_id: String,
    /// 0=Fulfilled / 1=NotFulfilled（本模块只由证据形状派生这两个值）。
    pub verdict_code: u8,
    /// 提案节点（`Node-…` 显示形）。
    pub node: String,
    /// `lyquor_api::systime()` 提案时刻（wall clock 域，对照用）。
    pub ts_ms: u64,
}

/// 认证回合的 `avg_num`（**编码期常量**）：首跑 = 4（L2 编排：arm 一次 +
/// node1 单次触发 → 4 提案 → 4 签）。fallback 改 1（L1 口径：1 提案 + 4 签）
/// 须**重新 cp/deploy**（编码期常量改值需重部署）——预登记见 plan §3.4 与
/// implementation.md 偏离表（仲裁 R2#2）。
const E2_AVG_NUM: u16 = 4;

/// 认证主题（oracle 主题名 = certified 回调宏的 `$first` = dest cert 校验的
/// topic 字符串；state! 里对应 `network oracle cert_verdict;`）。
const E2_TOPIC: &str = "cert_verdict";

/// 认证回调方法名（aggregate 送出的 `CertifiedCallParams.method`；必须与回调
/// 函数名逐字一致，否则平台按方法名寻址失败）。
const E2_CERTIFIED_METHOD: &str = "committee_verdict_certified";

// ---------------------------------------------------------------------------
// 配置与编排面（network）
// ---------------------------------------------------------------------------

/// 配置认证委员会 + 阈值（镜像 probe_configure，落 `cert_verdict` 主题）。
/// 仅入 oracle **staging**（`StateVar::initialize`，source.rs:540-544）——
/// 激活 = 平台内置 advance/finalize 两阶段（dest_epoch 是等待条件，P5）。
///
/// ABI 面 `e2_configure(bytes32[],uint16)`（`Vec<NodeID>` = bytes32[]，S2 实证）；
/// **调用通道 = cast send**（见模块头通道纪律）。守卫 `eth_guard = creator`：
/// creator = 部署钥 anvil#0（P4；S2 §2 同款先例）。
#[method::network(export = eth, eth_guard = creator)]
pub fn e2_configure(ctx: &mut _, node_ids: Vec<NodeID>, threshold: u16) -> LyquidResult<bool> {
    if node_ids.is_empty() {
        return Err(LyquidError::LyquorRuntime(
            "e2_configure: committee cannot be empty".into(),
        ));
    }
    if threshold == 0 {
        return Err(LyquidError::LyquorRuntime(
            "e2_configure: threshold must be > 0".into(),
        ));
    }
    let target = OracleTarget {
        seq_id: lyquor_api::sequence_backend_id()?,
        target: OracleServiceTarget::LVM(ctx.lyquid_id),
    };
    // price-feed:225-234 mirror — `initialize` only stages; false means the
    // staging write was rejected (e.g. target already active, epoch != 0).
    if !ctx
        .network
        .cert_verdict
        .clone()
        .initialize(&mut ctx, target, node_ids.clone(), threshold)
    {
        return Err(LyquidError::LyquorRuntime(
            "e2_configure: oracle staging initialization failed".into(),
        ));
    }
    lyquid::println!(
        "e2_configure: staged committee of {} nodes threshold={} (dest epoch advance/finalize required to activate)",
        node_ids.len(),
        threshold
    );
    Ok(true)
}

/// arm：选择「委员会下一轮裁哪一单」。
///
/// 写 **network 域** `e2_armed_deal`（共识持久、全节点可见）——经 NodeClient
/// `_send`（eth_sendTransaction）**单次发送即全体节点生效**，无需每节点 arm
/// （仲裁 R2#1-a）。**门 = creator**（演示编排面，与 e2_configure 同口径
/// fail-closed）：无门会让任意 caller 改写 armed deal 干扰演示；终局安全仍由
/// 回调的 cert 门兜底（纵深防御）。
///
/// 为何需要 arming：init 只携带 price-feed 已证的 `avg_num`/`target` 二字段
/// （P6；第三字段未经平台实证，不冒险，风险 R2）——待裁对象经共识状态传给
/// 全体节点的 propose。读回断言口径：`e2_net_config()` 的 `armed_deal`
/// （console 回显行仅作 transcript 佐证，不作断言载体）。
#[method::network(export = eth, eth_guard = creator)]
pub fn e2_arm(ctx: &mut _, deal_id: DealId) -> LyquidResult<bool> {
    if deal_id.is_empty() {
        return Err(LyquidError::LyquorRuntime(
            "e2_arm: deal_id cannot be empty".into(),
        ));
    }
    let state = &mut *ctx.network;
    *state.e2_armed_deal = deal_id.clone();
    lyquid::println!(
        "e2_arm: armed_deal={} (network domain; single send visible to all nodes)",
        deal_id
    );
    Ok(true)
}

/// 观测 dump：**arm 读回的唯一断言载体** + oracle 配置面（advance/finalize 的
/// 等待条件面）。返回 JSON 串（`_ABI` 返回面冻结为 string，终裁条款 2；先例
/// deal_info 的 JSON getter）。字段至少含 `armed_deal`（未 arm = 空串）
/// 与 current/staging 的 threshold/committee/epoch、源侧 get_epoch、dest
/// epoch/change_count（`fetch_oracle_info("cert_verdict", …)` 口径，镜像
/// probe_net_config s2_oracle.rs:257-281）。
///
/// 注：`dest.epoch` 才是 advance→finalize 的等待条件；`get_epoch` 读源侧
/// current.epoch，finalize 前恒 0（P5，勿用）。println 保留但仅作 console
/// 佐证——断言走 NodeClient 对返回串的 JSON 解码。
///
/// ctx 用**只读形**（`&_` → ImmutableNetworkContext）：本方法是纯观测 dump，
/// 且 eth_call 读通道只路由只读方法（R2 实测 §5-4：`fund` 等可变 network 方法
/// 在 eth_call 上恒 FuncNotFound，`deal_info` 等 `&_` getter 正常路由）。arm
/// 读回断言走 NodeClient `call("e2_net_config()")`，故必须落在可路由面。
#[method::network(export = eth)]
pub fn e2_net_config(ctx: &_) -> LyquidResult<String> {
    let target = OracleTarget {
        seq_id: lyquor_api::sequence_backend_id()?,
        target: OracleServiceTarget::LVM(ctx.lyquid_id),
    };
    let o = ctx.network.cert_verdict.clone();
    let cur = o.config_current(&ctx, target);
    let cur_threshold = cur.threshold;
    let cur_epoch = cur.epoch;
    let cur_size = cur.committee.len();
    let staging = o.config_staging(&ctx, target);
    let st_threshold = staging.threshold;
    let st_size = staging.committee.len();
    let src_epoch = o.get_epoch(&ctx, target);
    let (dest_epoch, dest_change) = match lyquor_api::fetch_oracle_info(E2_TOPIC.to_string(), target, false)? {
        Some(info) => (info.epoch, info.change_count),
        None => (0, 0),
    };
    let armed: String = (*ctx.network.e2_armed_deal).clone();
    let json = serde_json::json!({
        "armed_deal": armed,
        "current": { "threshold": cur_threshold, "committee": cur_size, "epoch": cur_epoch },
        "staging": { "threshold": st_threshold, "committee": st_size },
        "get_epoch": src_epoch,
        "dest": { "epoch": dest_epoch, "change_count": dest_change },
    })
    .to_string();
    lyquid::println!("e2_net_config: {}", json);
    Ok(json)
}

// ---------------------------------------------------------------------------
// 两阶段（instance）：每节点独立检视 + 聚合出证
// ---------------------------------------------------------------------------

/// 每节点独立检视（两阶段 propose，**字面名** = 平台宏契约，ldk
/// syntax.rs:470；改名即无法路由 oracle 机制）。
///
/// 读 armed deal + network `evidence_log[deal_id]` + `deals[deal_id]`
/// （instance 只读 network 先例 = probe_config s2_oracle.rs:294-317），跑
/// `committee::check_evidence_shape`（committee.rs:66-74，只读调用，零改动）
/// → **verdict 由链上证据派生**：shape 成立 → Fulfilled(0)，不成立 →
/// NotFulfilled(1)。不是脚本喂值——这是「真实 4 节点检视」的最诚实形态。
///
/// fail-closed：未 arm / deal 不存在 / 非 Disputed → Err（该节点不出提案）。
/// Malicious 不由形状派生，路线① 保留其入口（两条路线互补）。
#[method::instance(group = oracle::two_phase::cert_verdict)]
fn propose(ctx: &mut _, avg_num: u16, target: OracleTarget) -> LyquidResult<VerdictProposal> {
    let deal_id: String = (*ctx.network.e2_armed_deal).clone();
    if deal_id.is_empty() {
        return Err(LyquidError::LyquorRuntime(
            "e2_propose: no armed deal (e2_arm required)".into(),
        ));
    }
    let entries: Vec<EvidenceEntry> = ctx.network.evidence_log.get(&deal_id).cloned().unwrap_or_default();
    let shape_ok = match ctx.network.deals.get(&deal_id) {
        Some(deal) => {
            if !matches!(&deal.state, DealState::Disputed) {
                return Err(LyquidError::LyquorRuntime(format!(
                    "e2_propose: deal {deal_id} is not Disputed"
                )));
            }
            committee::check_evidence_shape(&entries, deal)
        }
        None => {
            return Err(LyquidError::LyquorRuntime(format!(
                "e2_propose: no such deal: {deal_id}"
            )))
        }
    };
    let verdict_code: u8 = if shape_ok { 0 } else { 1 };
    let ts_ms = lyquor_api::systime()?;
    let node = ctx.node_id.to_string();
    lyquid::println!(
        "e2_propose: node={} deal={} verdict={} (shape_ok={}, entries={}, avg_num={}, target.seq_id={:?})",
        node,
        deal_id,
        verdict_code,
        shape_ok,
        entries.len(),
        avg_num,
        target.seq_id
    );
    // W1-B2 编译修复同款（probe 先例）：wasm 目标下 Err 型参需显式标注（E0282）。
    Ok::<VerdictProposal, LyquidError>(VerdictProposal { deal_id, verdict_code, node, ts_ms })
}

/// 两阶段聚合（**字面名** = 平台宏契约，ldk syntax.rs:447）。
///
/// 语义（诚实优先）：
/// - inputs < avg_num → None（等更多提案；平台在后续响应到达时再调）；
/// - 提案间 deal/verdict **不一致 → None（拒证）**——委员会未达成一致就不出证；
/// - 无可解码提案 → None（拒绝为未知内容背书）；
/// - 一致 → `CertifiedCallParams { origin: ZERO, method: committee_verdict_certified,
///   input: encode_by_fields!(deal_id, verdict_code), target }`——字段名即
///   回调解码契约（P6）。
#[method::instance(group = oracle::two_phase::cert_verdict)]
fn aggregate(ctx: &_) -> LyquidResult<Option<CertifiedCallParams>> {
    let init = decode_by_fields!(ctx.init, avg_num: u16, target: OracleTarget)
        .ok_or_else(|| LyquidError::LyquorRuntime("e2_aggregate: failed to decode init params".into()))?;
    if init.target.seq_id != lyquor_api::sequence_backend_id()? {
        return Ok(None);
    }
    if ctx.inputs.len() < init.avg_num as usize {
        return Ok(None);
    }
    let mut seen: Vec<(String, u8)> = Vec::new();
    for i in ctx.inputs {
        if let Some(p) = lyquor_primitives::decode_object::<VerdictProposal>(&i.input) {
            lyquid::println!(
                "e2_aggregate: input from {} -> deal={} verdict={} (ts_ms={})",
                i.from,
                p.deal_id,
                p.verdict_code,
                p.ts_ms
            );
            seen.push((p.deal_id, p.verdict_code));
        }
    }
    if seen.is_empty() {
        lyquid::println!("e2_aggregate: REFUSE — no decodable proposal in {} input(s)", ctx.inputs.len());
        return Ok(None);
    }
    let (deal_id, verdict_code) = seen[0].clone();
    if seen.iter().any(|(d, v)| *d != deal_id || *v != verdict_code) {
        // 拒证：委员会未达成一致（诚实语义，风险 R5 的处置即此）
        lyquid::println!("e2_aggregate: REFUSE — proposals disagree: {:?}", seen);
        return Ok(None);
    }
    lyquid::println!(
        "e2_aggregate: agreed deal={} verdict={} from {} input(s) (avg_num={})",
        deal_id,
        verdict_code,
        ctx.inputs.len(),
        init.avg_num
    );
    let method = E2_CERTIFIED_METHOD.into();
    let input = encode_by_fields!(deal_id: String = deal_id, verdict_code: u8 = verdict_code).into();
    Ok(Some(CertifiedCallParams {
        origin: Address::ZERO,
        method,
        input,
        target: init.target, // LVM: this lyquid's committee_verdict_certified
    }))
}

/// **cert 门控的资金路径**：认证回调（`probe_on_certified` 的生产化）。
///
/// 平台在进入函数体**之前**已按 dest epoch 的 oracle 配置校验证书；函数体内
/// 把 `ctx.cert.signers`（RAW `Vec<SignerID>` = u32，primitives/src/oracle.rs:65）
/// 经 `ctx.signer_node_id(u64)`（runtime/mod.rs:560）逐节点映射为 NodeID 显示串，
/// 作为 `CommitteeCertWire.signers` 交给共享 helper → `core::validate_cert`
/// 四查（全员 ∈ committee_members + 去重 + |signers| ≥ threshold +
/// evidence_root 匹配）→ `core::apply_verdict` → `apply_payout`（真实结算）。
///
/// **门禁不在地址面**：认证回调 origin = ZERO（s2_oracle.rs:148），地址制
/// require 必然 fail-closed；认证来源 = 证书本身。`committee_members` 里配置的
/// 正是真实 NodeID 串（`e2_configure` 同源），伪造 signers 过不了成员检查——
/// 这正是「多节点认证替换单点签署」的信任升级点（路线① 同 helper 的差异）。
///
/// 取证（console，node1）：RAW signers、逐节点映射、verdict、deal_id，以及
/// helper 的 `apply_verdict: … misconduct=[…]` 累计视图。
#[method::network(group = oracle::certified::cert_verdict::two_phase)]
fn committee_verdict_certified(ctx: &mut _, deal_id: DealId, verdict_code: u8) -> LyquidResult<bool> {
    let signer_ids = ctx.cert.signers.clone();
    lyquid::println!(
        "committee_verdict_certified: cert.signers RAW = {:?} (Vec<SignerID>=Vec<u32>, len={}) deal={} verdict={}",
        signer_ids,
        signer_ids.len(),
        deal_id,
        verdict_code
    );
    let mut signers: Vec<AgentId> = Vec::new();
    for signer_id in signer_ids {
        match ctx.signer_node_id(signer_id as u64) {
            Some(nid) => {
                lyquid::println!("committee_verdict_certified: signer {} -> {}", signer_id, nid);
                signers.push(nid.to_string());
            }
            // 映射失败的 signer 不进入证书集（不猜测身份）——少一个签名最多
            // 触发阈值拒证（fail-closed），绝不冒充某个成员。
            None => {
                lyquid::println!(
                    "committee_verdict_certified: signer {} -> <unmapped> (excluded from cert signers)",
                    signer_id
                );
            }
        }
    }
    let state = &mut *ctx.network;
    let cert = committee::CommitteeCertWire { verdict_code, signers: signers.clone() };
    crate::apply_cert_and_payout(state, deal_id.clone(), cert)?;
    lyquid::println!(
        "committee_verdict_certified: applied deal={} verdict={} signers={:?} (signers must be distinct NodeIDs among committee_members)",
        deal_id,
        verdict_code,
        signers
    );
    Ok(true)
}

/// 单次认证回合驱动（镜像 probe_run_round s2_oracle.rs:195-223）：
/// `propose_and_certify` + `submit_certified_call!`。
///
/// **仅 node1 单次触发**（propose 经 UPC 广播自带全节点提案，protocol.rs:312/:316）；
/// **禁多次触发**：首回合裁决已把 deal 推离 Disputed，core.rs:199 门必败。
/// **通道 = cast call**（S2 §3/§4 实证：cast send status 1 但内层提交静默丢失）。
/// 返回 false = oracle 未激活 / aggregate 拒证（无内层调用产生）。
#[method::instance(export = eth)]
pub fn e2_run_verdict_round(ctx: &mut _) -> LyquidResult<bool> {
    let target = OracleTarget {
        seq_id: lyquor_api::sequence_backend_id()?,
        target: OracleServiceTarget::LVM(ctx.lyquid_id),
    };
    let o = ctx.network.cert_verdict.clone();
    lyquid::println!(
        "e2_run_verdict_round: node={} starting propose_and_certify (avg_num={})",
        ctx.node_id,
        E2_AVG_NUM
    );
    // init 字段名是契约：propose/aggregate 解 `avg_num`/`target`（见模块头）。
    let call = o.propose_and_certify(
        &mut ctx,
        target,
        lyquor_primitives::encode_by_fields!(avg_num: u16 = E2_AVG_NUM, target: OracleTarget = target).into(),
        None,
        None,
    )?;
    match call {
        Some(call) => {
            let _ = submit_certified_call!(call)?;
            lyquid::println!("e2_run_verdict_round: certified call submitted to the sequencing backend");
            Ok(true)
        }
        None => {
            lyquid::println!(
                "e2_run_verdict_round: no certified call produced (oracle inactive or aggregate refused)"
            );
            Ok(false)
        }
    }
}
