// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// TrustBridge — 纯 EVM 对照实验（R3 目标 B）。
///
/// 与 Lyquid escrow 的**逐能力最小对照**（plan §4.2），不是最优 Solidity 实现：
///   建单/托管   createDeal + fund() payable     ↔  create_deal + fund（network fn）
///   证据公证    notarize（msg.sender 隐式自署）  ↔  notarize（from==caller 自署名）
///   交付/完成   submitDeliverable + complete     ↔  submit_deliverable + complete
///   超时        claimTimeout（block.timestamp）  ↔  claim_timeout（slot 域，Anyone）
///   取消        cancel                           ↔  cancel（Buyer）
///   争议        openDispute                      ↔  open_dispute（BuyerOrSeller）
///   委员会配置  committeeConfig（deployer 门）    ↔  committee_config（broker 门）
///   裁决送达    applyVerdict(dealId, code, sigs) ↔  路线② oracle certified call
///               **k-of-n ECRECOVER 自建**            （平台自带 propose/certify/
///                                                      signers/内层上链全套）
///   裁决效果    同一 Payout 语义（分账/退款/misconduct 计数映射）
///
/// 诚实边界（报告须注明）：
///   * 委员会成员由 **deployer 管理的地址表**承载；「谁认证委员会本身」在 EVM 侧
///     没有平台机制，只能靠部署者信任 + 链下成员治理（Lyquid 路线② 由平台
///     oracle dest cert 承担）；
///   * 签名聚合 = 自建 ECRECOVER 循环（去重 + ∈ 成员 + ≥ threshold），而 Lyquid
///     侧这部分是平台能力——代码量对比的核心论点即在此；
///   * 签名是**对摘要的原始 secp256k1 签名**（无 EIP-191 前缀），脚本用
///     `cast wallet sign --no-hash <digest>` 生成；
///   * evidenceRoot 是 keccak256 链式折叠（含位置），与 core::evidence_root 的
///     FNV-1a 链折叠**语义对齐**（顺序敏感、全量证据绑定）而**算法族不同**；
///   * 超时域是秒（block.timestamp），Lyquid 是 slot；时间源的信任假设不同。

contract Escrow {
    // ---------------------------------------------------------------------
    // Domain（镜像 lyquid types.rs 的字段语义）
    // ---------------------------------------------------------------------

    enum State {
        None,        // 不存在
        Qualified,   // 已建单，未托管
        Funded,      // 买方已托管，超时时钟起点 = fundedAt
        Submitted,   // 卖方已提交交付物摘要
        Disputed,    // 任一方开争议，资金冻结
        Settled,     // 终态：已分账
        Refunded     // 终态：已退款
    }

    struct Deal {
        address buyer;
        address seller;
        address broker;
        uint256 amount;
        uint16 feeBps;
        bytes32 termsDigest;
        bytes32 acceptanceDigest;
        uint64 estDurationMs;
        uint8 estConfidence;
        uint64 timeoutSecs;      // 秒域（Lyquid 为 slot 域）
        uint64 fundedAt;
        State state;
        bytes32 deliverableDigest; // bytes32(0) = 未提交
        bytes32 disputeReason;
    }

    struct Evidence {
        address from;          // notarize 的提交者 = msg.sender（自署名）
        address to;
        bytes32 payloadDigest;
        uint64 ts;
    }

    // ---------------------------------------------------------------------
    // Storage
    // ---------------------------------------------------------------------

    address public immutable deployer;
    uint256 public dealCounter;

    mapping(uint256 => Deal) private _deals;
    mapping(uint256 => Evidence[]) private _evidence;

    /// 委员会成员表（deployer 管理）。
    mapping(address => bool) public isCommitteeMember;
    address[] public committeeMembers;
    uint256 public threshold;

    /// reputation hook：Malicious 裁决对卖家计数 +1（core.rs 同语义）。
    mapping(address => uint256) public misconduct;

    event DealCreated(uint256 indexed dealId, address indexed buyer, address indexed seller, uint256 amount);
    event Funded(uint256 indexed dealId, uint256 amount);
    event Notarized(uint256 indexed dealId, uint256 seq, address indexed from, address indexed to);
    event Delivered(uint256 indexed dealId, bytes32 digest);
    event Completed(uint256 indexed dealId);
    event Cancelled(uint256 indexed dealId);
    event Disputed(uint256 indexed dealId);
    event TimedOut(uint256 indexed dealId);
    event VerdictApplied(uint256 indexed dealId, uint8 verdictCode, address[] signers);
    event CommitteeConfigured(uint256 threshold, address[] members);

    constructor() {
        deployer = msg.sender;
    }

    // ---------------------------------------------------------------------
    // 委员会配置（deployer 门）
    // ---------------------------------------------------------------------

    function committeeConfig(address[] calldata members, uint256 newThreshold) external {
        require(msg.sender == deployer, "not deployer");
        require(newThreshold > 0 && newThreshold <= members.length, "bad threshold");
        // 覆盖式配置（Lyquid committee_config 的 clear+insert 同语义）。
        for (uint256 i = 0; i < committeeMembers.length; i++) {
            isCommitteeMember[committeeMembers[i]] = false;
        }
        delete committeeMembers;
        for (uint256 i = 0; i < members.length; i++) {
            require(members[i] != address(0), "zero member");
            if (!isCommitteeMember[members[i]]) {
                isCommitteeMember[members[i]] = true;
                committeeMembers.push(members[i]);
            }
        }
        threshold = newThreshold;
        emit CommitteeConfigured(newThreshold, members);
    }

    // ---------------------------------------------------------------------
    // 建单 / 托管
    // ---------------------------------------------------------------------

    /// 建单：msg.sender 即 buyer（Lyquid create_deal 由 broker 代建，地址语义不同，
    /// 属对照边界——EVM 侧没有可信 broker 身份层，买家自建最诚实）。
    function createDeal(
        address seller,
        address broker,
        uint256 amount,
        uint16 feeBps,
        bytes32 termsDigest,
        bytes32 acceptanceDigest,
        uint64 estDurationMs,
        uint8 estConfidence
    ) external returns (uint256 id) {
        require(seller != address(0) && broker != address(0), "zero address");
        require(msg.sender != seller, "buyer == seller");
        require(amount > 0, "amount must be > 0");
        require(feeBps <= 10_000, "feeBps out of range");
        require(termsDigest != bytes32(0) && acceptanceDigest != bytes32(0), "empty digest");
        require(estConfidence <= 100, "estConfidence 0-100");

        dealCounter += 1;
        id = dealCounter;

        // 超时 = p90 估计 × 2 的安全系数（types.rs TIMEOUT_SAFETY_FACTOR 语义），
        // 毫秒 → 秒域，至少 1 秒。
        uint64 timeoutSecs = uint64((uint256(estDurationMs) * 2) / 1000);
        if (timeoutSecs == 0) {
            timeoutSecs = 1;
        }

        Deal storage d = _deals[id];
        d.buyer = msg.sender;
        d.seller = seller;
        d.broker = broker;
        d.amount = amount;
        d.feeBps = feeBps;
        d.termsDigest = termsDigest;
        d.acceptanceDigest = acceptanceDigest;
        d.estDurationMs = estDurationMs;
        d.estConfidence = estConfidence;
        d.timeoutSecs = timeoutSecs;
        d.state = State.Qualified;

        emit DealCreated(id, msg.sender, seller, amount);
    }

    /// 买方全额托管；金额必须与建单一致（msg.value == amount）。
    function fund(uint256 dealId) external payable {
        Deal storage d = _requireDeal(dealId);
        require(d.state == State.Qualified, "state");
        require(msg.sender == d.buyer, "buyer only");
        require(msg.value == d.amount, "msg.value != amount");
        d.fundedAt = uint64(block.timestamp);
        d.state = State.Funded;
        emit Funded(dealId, msg.value);
    }

    // ---------------------------------------------------------------------
    // 证据 / 交付 / 完成 / 超时 / 取消 / 争议
    // ---------------------------------------------------------------------

    /// append-only 公证：`from` 隐式 = msg.sender（自署名，Lyquid from==caller 同语义）。
    function notarize(uint256 dealId, address to, bytes32 payloadDigest) external returns (uint256 seq) {
        _requireDeal(dealId);
        seq = _evidence[dealId].length;
        _evidence[dealId].push(
            Evidence({from: msg.sender, to: to, payloadDigest: payloadDigest, ts: uint64(block.timestamp)})
        );
        emit Notarized(dealId, seq, msg.sender, to);
    }

    function submitDeliverable(uint256 dealId, bytes32 digest) external {
        Deal storage d = _requireDeal(dealId);
        require(d.state == State.Funded, "state");
        require(msg.sender == d.seller, "seller only");
        require(block.timestamp <= deadline(dealId), "deadline passed");
        d.deliverableDigest = digest;
        d.state = State.Submitted;
        emit Delivered(dealId, digest);
    }

    /// 买方同意结算 → 卖方得 (amount - fee)，broker 得 fee（core Payout::settle 同式）。
    function complete(uint256 dealId) external {
        Deal storage d = _requireDeal(dealId);
        require(d.state == State.Submitted, "state");
        require(msg.sender == d.buyer, "buyer only");
        d.state = State.Settled;
        uint256 fee = (d.amount * d.feeBps) / 10_000;
        _pay(d.seller, d.amount - fee);
        _pay(d.broker, fee);
        emit Completed(dealId);
    }

    /// permissionless（Lyquid claim_timeout: Anyone）；只允许 Funded（无证据）——
    /// 与 core 的「证据存在后只能走裁决/买方同意」一致。
    function claimTimeout(uint256 dealId) external {
        Deal storage d = _requireDeal(dealId);
        require(d.state == State.Funded, "state");
        require(block.timestamp >= deadline(dealId), "deadline not reached");
        d.state = State.Refunded;
        _pay(d.buyer, d.amount);
        emit TimedOut(dealId);
    }

    function cancel(uint256 dealId) external {
        Deal storage d = _requireDeal(dealId);
        require(d.state == State.Qualified || d.state == State.Funded, "state");
        require(msg.sender == d.buyer, "buyer only");
        bool wasFunded = d.state == State.Funded;
        d.state = State.Refunded;
        if (wasFunded) {
            _pay(d.buyer, d.amount);
        }
        emit Cancelled(dealId);
    }

    function openDispute(uint256 dealId, bytes32 reasonDigest) external {
        Deal storage d = _requireDeal(dealId);
        require(d.state == State.Funded || d.state == State.Submitted, "state");
        require(msg.sender == d.buyer || msg.sender == d.seller, "parties only");
        d.disputeReason = reasonDigest;
        d.state = State.Disputed;
        emit Disputed(dealId);
    }

    // ---------------------------------------------------------------------
    // 裁决：自建 k-of-n ECRECOVER（Lyquid 侧是平台能力）
    // ---------------------------------------------------------------------

    /// `sigs` 每项 = 对 `verdictDigest(dealId, verdictCode)` 的 65 字节原始签名。
    /// 校验 = ecrecover ∈ 成员 + 去重 + 计数 ≥ threshold（core::validate_cert 的
    /// 密码学等价物）；evidenceRoot 绑定当前全量证据（防事后追加/篡改/重排）。
    /// 调用者无门——认证完全来自签名集（对应 Lyquid certified call 的 origin=ZERO）。
    function applyVerdict(uint256 dealId, uint8 verdictCode, bytes[] calldata sigs) external {
        Deal storage d = _requireDeal(dealId);
        require(d.state == State.Disputed, "state");

        bytes32 digest = verdictDigest(dealId, verdictCode);
        address[] memory seen = new address[](sigs.length);
        uint256 count = 0;
        for (uint256 i = 0; i < sigs.length; i++) {
            address signer = _recover(digest, sigs[i]);
            require(signer != address(0), "bad signature");
            require(isCommitteeMember[signer], "non-member signer");
            for (uint256 j = 0; j < count; j++) {
                require(seen[j] != signer, "duplicate signer");
            }
            seen[count] = signer;
            count += 1;
        }
        require(count >= threshold, "insufficient committee signers");

        // 裁决效果（core.rs apply_verdict 同式）：Fulfilled → Settled 分账；
        // NotFulfilled/Malicious → 全额退款；Malicious 额外 misconduct[seller] += 1。
        if (verdictCode == 0) {
            d.state = State.Settled;
            uint256 fee = (d.amount * d.feeBps) / 10_000;
            _pay(d.seller, d.amount - fee);
            _pay(d.broker, fee);
        } else {
            d.state = State.Refunded;
            _pay(d.buyer, d.amount);
            if (verdictCode >= 2) {
                misconduct[d.seller] += 1;
            }
        }

        address[] memory signers = new address[](count);
        for (uint256 i = 0; i < count; i++) {
            signers[i] = seen[i];
        }
        emit VerdictApplied(dealId, verdictCode, signers);
    }

    /// 待签摘要 = keccak256(abi.encode(dealId, verdictCode, evidenceRoot))。
    function verdictDigest(uint256 dealId, uint8 verdictCode) public view returns (bytes32) {
        return keccak256(abi.encode(dealId, verdictCode, evidenceRoot(dealId)));
    }

    /// 链上证据的顺序敏感 keccak 链折叠（含位置）——绑定契约对齐 core.rs:225-231
    /// 的「root 必须等于**当前全量证据**的折叠」，算法族不同（FNV-1a vs keccak）。
    function evidenceRoot(uint256 dealId) public view returns (bytes32 root) {
        root = keccak256("trustbridge/evidence-root/v1");
        Evidence[] storage log = _evidence[dealId];
        for (uint256 i = 0; i < log.length; i++) {
            root = keccak256(
                abi.encode(root, i, log[i].from, log[i].to, log[i].payloadDigest, log[i].ts)
            );
        }
    }

    // ---------------------------------------------------------------------
    // Views（数据采集面）
    // ---------------------------------------------------------------------

    /// 数据采集面（默认编译管线；8 返回值 + storage 指针会触发 Stack too deep，
    /// 与 Lyquid 侧 solc 参数上限的记录同族——故拆成小 view：金额/费率/角色
    /// 由各自 getter 读，避免 viaIR 依赖）。
    function dealInfo(uint256 dealId) external view returns (
        uint8 stateCode,
        bytes32 deliverableDigest,
        uint64 deadlineTs,
        uint256 evidenceCount_
    ) {
        Deal storage d = _requireDeal(dealId);
        return (uint8(d.state), d.deliverableDigest, deadline(dealId), _evidence[dealId].length);
    }

    function rolesOf(uint256 dealId) external view returns (address buyer, address seller, address broker) {
        Deal storage d = _requireDeal(dealId);
        return (d.buyer, d.seller, d.broker);
    }

    function amountOf(uint256 dealId) external view returns (uint256 amount, uint16 feeBps) {
        Deal storage d = _requireDeal(dealId);
        return (d.amount, d.feeBps);
    }

    function stateOf(uint256 dealId) external view returns (State) {
        return _requireDeal(dealId).state;
    }

    function deadline(uint256 dealId) public view returns (uint64) {
        Deal storage d = _requireDeal(dealId);
        if (d.fundedAt == 0) {
            return 0;
        }
        return d.fundedAt + d.timeoutSecs;
    }

    function evidenceCount(uint256 dealId) external view returns (uint256) {
        return _evidence[dealId].length;
    }

    function committeeSize() external view returns (uint256) {
        return committeeMembers.length;
    }

    // ---------------------------------------------------------------------
    // Internal
    // ---------------------------------------------------------------------

    function _requireDeal(uint256 dealId) private view returns (Deal storage d) {
        d = _deals[dealId];
        require(d.state != State.None, "no such deal");
    }

    function _pay(address to, uint256 amount) private {
        if (amount == 0) {
            return;
        }
        (bool ok, ) = payable(to).call{value: amount}("");
        require(ok, "transfer failed");
    }

    /// 65 字节 (r,s,v) → ecrecover；v 兼容 0/1 与 27/28。
    function _recover(bytes32 digest, bytes calldata sig) private pure returns (address) {
        require(sig.length == 65, "sig must be 65 bytes");
        bytes32 r;
        bytes32 s;
        uint8 v;
        assembly {
            r := calldataload(sig.offset)
            s := calldataload(add(sig.offset, 32))
            v := byte(0, calldataload(add(sig.offset, 64)))
        }
        if (v < 27) {
            v += 27;
        }
        if (v != 27 && v != 28) {
            return address(0);
        }
        // EIP-2 low-s（签名可延展性防护；cast 生成的签名满足）。
        if (uint256(s) > 0x7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF5D576E7357A4501DDFE92F46681B20A0) {
            return address(0);
        }
        return ecrecover(digest, v, r, s);
    }
}
