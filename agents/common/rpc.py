"""Node access for agents.

Two transports, one interface:

  NodeClient — talks to the Lyquor devnet node over the ETH JSON-RPC 2.0 API
               (W1-B2 S4: envelope verified against the multi v0.8.1 devnet,
               evidence + probe matrix archived in workflow-out/w1b2-s4-rpc.md).
               Envelope, verified by probes, not assumptions:
                 POST  {base}/api  with {"jsonrpc":"2.0","id",...}
                 reads  = eth_call   [{to, data}, "latest"]
                 writes = eth_sendTransaction [{from, to, data}] — the node
                          signs with its dev backend for the `from` account
                          (dual-sender decision gate passed: anvil #0 AND #1;
                          §B-①), so per-call sender selection is just the
                          `from` field. eth_estimateGas is NOT usable on
                          lyquid contracts (§B-③④b) and not needed: the node
                          auto-gasses sends without a gas field.
                 receipt = eth_getTransactionReceipt, `status == "0x1"`.
               Method names on the wire are the BARE Ethereum-ABI function
               names of the lyquid's exported fns (e.g. "deal_info(string)"),
               routed by 4-byte selectors pinned in _SELECTORS below (frozen
               from `cast sig` output; cross-checked against the LyteLog
               selector bytes of the T1 receipts, w1b2-s4-rpc.md §B-⓪).
               CAVEAT (measured, T1 A-1 note 3): `status == "0x1"` means the
               transaction was sequenced, NOT that the lyquid method returned
               Ok — a method Err is swallowed by the platform and the tx still
               lands (non-revert semantics, implementation.md §③). Callers
               that need success must read back state (create_deal does;
               keeper.py re-checks deal_info/balance_of).

  FakeNode   — in-process mirror of the Lyquid's semantics for orchestration
               smoke tests (dev velocity before the devnet is wired). The
               SOURCE OF TRUTH for deal semantics is the Rust `core` module +
               its tests; FakeNode deliberately mirrors, and demo.py prints a
               banner saying so.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field

from agents.common.protocol import evidence_root

DEFAULT_NODE = os.environ.get("TB_NODE", "http://127.0.0.1:10087")

# ---------------------------------------------------------------------------
# ETH-side constants (all values measured on the multi v0.8.1 devnet; sources
# cited per line — reproducible via the commands in workflow-out/w1b2-s4-rpc.md)
# ---------------------------------------------------------------------------

# anvil deterministic dev account #0 (BROKER on-chain). Address verified two
# ways: `eth_accounts` listing (w1b2-s4-rpc.md §A-0) and the `from` field of
# receipts for txs signed by the #0 dev key (§B-②).
DEFAULT_SENDER = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"

# Role key table (R1 S4 收尾; 来源 = w1b2-s4-rpc.md §A-0 eth_accounts + §B-②
# 回执 from 验证). The node's dev signer backend signs per the `from` field
# (module docstring), so the Python side never holds a private key — the
# "#0/#1/#2 私钥" story resolves to ADDRESS SELECTION on the wire. The #0 key
# still lives only in the shaker deploy command line.
BROKER_ADDR = DEFAULT_SENDER            # anvil#0（create_deal/faucet/committee_config 发送方）
ALICE_ADDR = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"  # anvil#1 = buyer（B-① 双 sender 已验）
BOB_ADDR = "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"    # anvil#2 = seller（sender 首验 = R1 demo，D6）

# Selector + wire-type table. Source: `cast sig "<sig>"` in the multi-tools
# container, 2026-10-25 (w1b2-s4-rpc.md §B-⓪); faucet/fund/create_deal bytes
# additionally cross-checked against the LyteLog data of the T1 receipts.
# Types are exactly what the export=eth wire面 accepts (u128 domain values
# travel as uint128/uint64 per lib.rs edge conversions — R1#1).
_ABI: dict[str, tuple[str, tuple[str, ...], str | None]] = {
    # sig: (selector, param types, return type)
    "faucet(string,uint128)": ("b540def8", ("string", "uint128"), None),
    "create_deal(string,string,uint128,uint16,string,string,uint64,uint8)": (
        "bd827024",
        ("string", "string", "uint128", "uint16", "string", "string", "uint64", "uint8"),
        None,
    ),
    "fund(string)": ("73451f65", ("string",), None),
    "notarize(string,string,string,string)": ("b1fecd5a", ("string",) * 4, None),
    "submit_deliverable(string,string)": ("7ecc9d46", ("string", "string"), None),
    "complete(string)": ("ad932b5c", ("string",), None),
    "claim_timeout(string)": ("786cfc8f", ("string",), "bool"),
    "cancel(string)": ("0b4f3f3d", ("string",), None),
    "open_dispute(string,string)": ("a48ab911", ("string", "string"), None),
    # R2 路线①：apply_committee_verdict 的 wire 面由结构体扁平化为
    # (string,uint8,string[])。selector 实取（multi-tools 容器，2026-10-29，
    # R2 T5 wire 探针）：`cast sig "apply_committee_verdict(string,uint8,string[])"`
    # → 0xa32974e3；同一批探针复核 open_dispute 的 a48ab911 未漂移。
    "apply_committee_verdict(string,uint8,string[])": (
        "a32974e3",
        ("string", "uint8", "string[]"),
        None,
    ),
    "committee_config(string[],uint32)": ("15df3c73", ("string[]", "uint32"), None),
    "deal_info(string)": ("ec78f86e", ("string",), "string"),
    "evidence_entries_json(string)": ("16417010", ("string",), "string"),
    "balance_of(string)": ("3e6b4459", ("string",), "uint128"),
    "due_deals(uint64)": ("4704839a", ("uint64",), "string[]"),
    # R1 恢复导出（lib.rs assess_brief 4×string 形态）。selector 实取：
    # `cast sig "assess_brief(string,string,string,string)"` → 0x3297eeb6
    #（multi-tools 容器，2026-10-29，R1 T3）。
    "assess_brief(string,string,string,string)": (
        "3297eeb6",
        ("string",) * 4,
        "string",
    ),
}

# R2 路线①（R1 的排除注记已被取代）：apply_committee_verdict 的结构体 wire 参数
# （CommitteeCertWire）在 ldk v0.8.1 无 EthAbiType（plan R3），故 lib.rs 已把它扁平化
# 为 (string,uint8,string[]) 并 eth 导出——上一行的 selector 即实取冻结值。对抗流自
# R2 起在真 devnet 上跑（不再是「仅 sim」形态）。


class NodeError(RuntimeError):
    """A JSON-RPC error object came back (transport accepted, call failed).

    Carries the raw error verbatim — no collapsing into a generic message
    (the error text is the only on-chain diagnostic: e.g.
    `Execution error: Barrel(Lyquid(LyquidRuntime("no such deal"))).`)."""

    def __init__(self, method: str, error: dict):
        self.method = method
        self.code = error.get("code")
        self.message = error.get("message")
        self.data = error.get("data")
        extra = f" data={self.data!r}" if self.data is not None else ""
        super().__init__(f"{method}: rpc error {self.code}: {self.message}{extra}")


class TxError(RuntimeError):
    """Receipt came back with status != 0x1 (transport-level failure)."""


# ---------------------------------------------------------------------------
# Minimal Ethereum-ABI codec (pure stdlib; covers exactly the _ABI type set:
# string / uint8..uint128 / bool / string[] — no tuples, no nested arrays).
# ---------------------------------------------------------------------------


def _word(v: int) -> bytes:
    return int(v).to_bytes(32, "big")


def _pad32(b: bytes) -> bytes:
    return b + b"\x00" * ((32 - len(b) % 32) % 32)


def _enc_value(t: str, v) -> bytes:
    if t == "string":
        b = str(v).encode()
        return _word(len(b)) + _pad32(b)  # length word + padded payload
    if t == "string[]":
        # R2 修正（编码器缺陷，与 _decode_ret 同源错误）：元素偏移必须相对「长度字
        # 之后」的 tail 起点（标准 ABI），旧实现把长度字也算进了 head_size，导致每个
        # 偏移多 0x20。R1 的 committee_config(string[],uint32) 因此从未真正配置成功
        # （无 getter，读不回来，正常/超时流也不依赖），R2 对抗流首次依赖时才暴露。
        # 修正后与 `cast calldata` 逐字节一致（见 workflow-out/_r2-adversarial-raw.txt 附录）。
        items = list(v)
        head_size = 32 * len(items)          # one offset per item, from the tail start
        out = _word(len(items))
        tails = []
        off = head_size
        for it in items:
            out += _word(off)
            tb = _enc_value("string", it)
            tails.append(tb)
            off += len(tb)
        return out + b"".join(tails)
    if t.startswith("uint"):
        return _word(int(v))
    if t == "bool":
        return _word(1 if v else 0)
    raise ValueError(f"unsupported ABI type: {t}")


def _is_dynamic(t: str) -> bool:
    return t in ("string", "string[]")


def _encode_args(types: tuple[str, ...], values: tuple) -> bytes:
    if len(types) != len(values):
        raise ValueError(f"arity mismatch: {types} vs {values}")
    head, tail, head_size = b"", b"", 32 * len(types)
    for t, v in zip(types, values):
        if _is_dynamic(t):
            head += _word(head_size + len(tail))  # offset to this value's tail
            tail += _enc_value(t, v)
        else:
            head += _enc_value(t, v)
    return head + tail


def _decode_ret(t: str, hexdata: str):
    data = bytes.fromhex(hexdata[2:] if hexdata.startswith("0x") else hexdata)
    if t == "string":
        off = int.from_bytes(data[0:32], "big")
        ln = int.from_bytes(data[off:off + 32], "big")
        return data[off + 32:off + 32 + ln].decode()
    if t == "string[]":
        # R2 修正（编码器缺陷，R1 未暴露）：动态数组的元素偏移是相对「长度字之后
        # 的起点」（ABI 标准），不是相对数组基址。R1 只在 due_deals 上见过空数组
        # （[] 不触发偏移解析），非空返回在 R2 T6-A 首次出现时被误读为 32 字节的
        # 零串——实测原文：0x20 | len=1 | 0x20 | 0x06 | "deal-1"（word[2]=0x20
        # 只有按 tail = base+32 解释才落到 word[3] 的长度字）。修正后与 cast 的
        # 标准解码一致。
        base = int.from_bytes(data[0:32], "big")
        n = int.from_bytes(data[base:base + 32], "big")
        tail = base + 32                      # element offsets are relative to here
        out = []
        for i in range(n):
            eo = int.from_bytes(data[tail + 32 * i:tail + 32 * (i + 1)], "big")
            ln = int.from_bytes(data[tail + eo:tail + eo + 32], "big")
            out.append(data[tail + eo + 32:tail + eo + 32 + ln].decode())
        return out
    if t == "bool":
        return int.from_bytes(data[0:32], "big") == 1
    if t.startswith("uint"):
        return int.from_bytes(data[0:32], "big")
    raise ValueError(f"unsupported return type: {t}")


def _sig_types(sig: str) -> tuple[str, ...]:
    inner = sig[sig.index("(") + 1:sig.index(")")]
    return tuple(t for t in inner.split(",") if t)


# ---------------------------------------------------------------------------
# NodeClient
# ---------------------------------------------------------------------------


class NodeClient:
    """ETH JSON-RPC transport with the same method face as FakeNode.

    `sender` is the default EIP-55 address used for guarded writes; every
    mutating wrapper also accepts keyword-only `sender=` for per-call role
    selection (demo maps ALICE/BOB to dev accounts #1/#2 — the on-chain
    Buyer/Seller guards compare `ctx.caller.to_string()` exactly, lib.rs:624).
    """

    def __init__(self, base_url: str = DEFAULT_NODE, contract: str | None = None,
                 sender: str | None = None):
        self.base_url = base_url.rstrip("/")
        contract = contract or os.environ.get("TB_CONTRACT")
        if not contract:
            raise ValueError(
                "contract address required: pass --contract <addr> or set TB_CONTRACT")
        self.contract = contract
        self.sender = sender or DEFAULT_SENDER

    # -- transport core ----------------------------------------------------

    def _rpc(self, method: str, params: list):
        import requests  # imported lazily so sim mode needs no deps

        payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        r = requests.post(f"{self.base_url}/api", json=payload, timeout=30)
        r.raise_for_status()
        body = r.json()
        if "error" in body:
            raise NodeError(method, body["error"])
        return body.get("result")

    def block_number(self) -> int:
        return int(self._rpc("eth_blockNumber", []), 16)

    def _view(self, sig: str, args: tuple, frm: str | None = None):
        sel, types, ret = _ABI[sig]
        data = "0x" + sel + _encode_args(types, args).hex()
        call = {"to": self.contract, "data": data}
        if frm:
            call["from"] = frm
        raw = self._rpc("eth_call", [call, "latest"])
        return _decode_ret(ret, raw) if ret else None

    def _send(self, sig: str, args: tuple, sender: str | None = None):
        """Write path: eth_sendTransaction + receipt wait.

        Returns when receipt.status == "0x1". NOTE the measured caveat in the
        module docstring: 0x1 = sequenced, not necessarily method-Ok. Methods
        that must prove effect read back afterwards (create_deal / keeper)."""
        sel, types, _ret = _ABI[sig]
        data = "0x" + sel + _encode_args(types, args).hex()
        txh = self._rpc("eth_sendTransaction",
                        [{"from": sender or self.sender, "to": self.contract, "data": data}])
        deadline = time.time() + 60
        receipt = None
        while time.time() < deadline:
            receipt = self._rpc("eth_getTransactionReceipt", [txh])
            if receipt is not None:
                break
            time.sleep(0.5)
        if receipt is None:
            raise TxError(f"{sig}: no receipt within 60s (tx {txh})")
        if receipt.get("status") != "0x1":
            raise TxError(f"{sig}: tx {txh} status={receipt.get('status')} receipt={receipt}")
        return receipt

    def _addr(self, sender: str | None) -> str:
        return sender or self.sender

    # -- convenience wrappers mirroring the Lyquid surface ------------------

    def faucet(self, agent: str, amount: int, *, sender: str | None = None):
        self._send("faucet(string,uint128)", (agent, amount), sender)

    def nudge(self, *, sender: str | None = None):
        """Benign zero-value faucet to self — one automined block (设计输入⑤).

        The timeout flow needs the chain to advance past a deal's deadline;
        with automine the only reliable clock tick is "land a transaction".
        Amount 0 keeps the ledger untouched (faucet has no guards, lib.rs:241).
        R0 keeper evidence used the same technique externally; R1 bakes it in.
        """
        self._send("faucet(string,uint128)", (self._addr(sender), 0), sender)

    def discover_deals(self, limit: int = 10_000) -> list[str]:
        """Existing deal ids, probed deal-1 upward until the first gap.

        Same discovery loop `create_deal` uses (no on-chain enumeration is
        guaranteed: due_deals is advisory-only and unverified on the wire,
        plan D9), so the keeper can run without `--deals` (设计输入①)."""
        out: list[str] = []
        n = 1
        while n <= limit and self._deal_exists(f"deal-{n}"):
            out.append(f"deal-{n}")
            n += 1
        if n > limit:
            raise RuntimeError("deal id probe overflow (>%d deals)" % limit)
        return out

    def create_deal(self, buyer, seller, amount, fee_bps, terms_d, acceptance_d,
                    est_ms, est_conf, *, sender: str | None = None) -> str:
        # deal_id discovery (plan R1#3 fallback algorithm): eth_sendTransaction
        # cannot return the lyquid's return value, so probe existing ids from
        # deal-1 upward for the pre-call max, then verify the expected successor
        # appeared and belongs to the buyer we passed (read-back = the success
        # proof, per the status!=Ok caveat).
        n = 1
        while n <= 10_000 and self._deal_exists(f"deal-{n}"):
            n += 1
        if n > 10_000:
            raise RuntimeError("deal id probe overflow (>10k deals)")
        expected = f"deal-{n}"
        self._send("create_deal(string,string,uint128,uint16,string,string,uint64,uint8)",
                   (buyer, seller, amount, fee_bps, terms_d, acceptance_d, est_ms, est_conf),
                   sender)
        info = self._poll_deal(expected)
        if info.get("buyer") != buyer:
            raise RuntimeError(
                f"{expected} exists but buyer={info.get('buyer')!r} != {buyer!r}; refusing to guess")
        return expected

    def _deal_exists(self, deal_id: str) -> bool:
        try:
            self.deal_info(deal_id)
            return True
        except NodeError:
            return False

    def _poll_deal(self, deal_id: str, attempts: int = 10) -> dict:
        # consensus finality retry: the write is sequenced before we get here,
        # but give the read path a few ticks (automine: usually first try).
        last: Exception | None = None
        for _ in range(attempts):
            try:
                return self.deal_info(deal_id)
            except NodeError as e:  # pragma: no cover - finality window
                last = e
                time.sleep(0.4)
        raise last  # type: ignore[misc]

    def fund(self, deal_id, *, sender: str | None = None):
        self._send("fund(string)", (deal_id,), sender)

    def notarize(self, deal_id, frm, to, payload_digest, *, sender: str | None = None):
        # FakeNode returns the entry seq; the ETH write path has no return
        # value (receipt-only), and no flow consumes the seq — documented
        # asymmetry, same as claim_timeout's bool below.
        self._send("notarize(string,string,string,string)", (deal_id, frm, to, payload_digest),
                   sender)
        return True

    def submit_deliverable(self, deal_id, d, *, sender: str | None = None):
        self._send("submit_deliverable(string,string)", (deal_id, d), sender)

    def complete(self, deal_id, *, sender: str | None = None):
        self._send("complete(string)", (deal_id,), sender)

    def claim_timeout(self, deal_id, *, sender: str | None = None) -> bool:
        # Permissionless (Access::Anyone) — the on-chain guard re-derives
        # eligibility; a non-due/terminal deal errors on-chain ( swallowed by
        # the platform: status stays 0x1). keeper.py therefore re-checks
        # deal_info after sending; see its idempotency note.
        self._send("claim_timeout(string)", (deal_id,), sender)
        return True

    def cancel(self, deal_id, *, sender: str | None = None):
        self._send("cancel(string)", (deal_id,), sender)

    def open_dispute(self, deal_id, reason_digest, *, sender: str | None = None):
        self._send("open_dispute(string,string)", (deal_id, reason_digest), sender)

    def apply_committee_verdict(self, deal_id, cert, caller=None, *, sender: str | None = None):
        """cert is the DOMAIN-level triple (verdict_code, evidence_root, signers).

        R2 路线①：链上方法已 eth 导出（扁平 wire `(string,uint8,string[])`）。
        本包装保持与 FakeNode 完全相同的域三元组接口——两种传输同调用形态是
        sim transcript 零漂移的结构保证（plan §6-2-3）；内部把域三元组扁平化，
        `evidence_root` 只在客户端同源预检里用一次（镜像链上 into_domain 的
        证据根折叠）：root 过期就在这里早失败，省掉一笔必被拒的交易。

        `sender or caller`：demo 以既有形态 `(deal_id, cert, <principal>)` 调用，
        principal 位置即 broker 地址，同时充当交易发送方——链上两侧守卫
        （caller ∈ members ∧ caller ∈ signers）都以本交易的 sender 为准。
        `sender or caller or self.sender` 的回落链与 notarize/claim_timeout
        同款。"""
        verdict_code, cert_root, signers = cert
        if evidence_root(self.evidence_entries(deal_id)) != cert_root:
            raise RuntimeError("committee cert evidence_root mismatch (client-side precheck)")
        self._send("apply_committee_verdict(string,uint8,string[])",
                   (deal_id, int(verdict_code), list(signers)),
                   sender or caller or self.sender)
        # 回执无返回值（与 notarize/claim_timeout 同款不对称注记）：效果由调用方
        # 读回 deal_info/balance_of 复核（status=="0x1" ≠ 方法 Ok，模块 docstring）。
        return True

    def committee_config(self, members, threshold, *, sender: str | None = None):
        self._send("committee_config(string[],uint32)", (list(members), int(threshold)), sender)

    def deal_info(self, deal_id) -> dict:
        return json.loads(self._view("deal_info(string)", (deal_id,),
                                     frm=self._addr(None)))

    def evidence_entries(self, deal_id) -> list:
        """Mirror of the chain's evidence_entries_json getter."""
        return json.loads(self._view("evidence_entries_json(string)", (deal_id,),
                                     frm=self._addr(None)))

    def balance_of(self, agent, *, sender: str | None = None) -> int:
        # wire面 is uint128 (R1#1 edge conversion at the balance_of signature).
        return self._view("balance_of(string)", (agent,), frm=self._addr(sender or self.sender))

    def due_deals(self, now: int | None = None, *, sender: str | None = None) -> list:
        # `now` defaults to the current block height (the chain treats it as
        # advisory-only; money movement re-derives time in claim_timeout).
        # 实测注记（R1 T5-3，w1b2-r1-demo-timeout.md 附录）：wire 面**可路由**，
        # `cast call "due_deals(uint64) returns (string[])"` 返回合法 ABI
        # string[]（全终态实例上为 []）；D9 的 FuncNotFound 未复现。语义仍只列
        # Funded 且过 deadline 的 deal，故 demo/keeper 的枚举走 discover_deals。
        if now is None:
            now = self.block_number()
        return self._view("due_deals(uint64)", (int(now),), frm=self._addr(sender or self.sender))

    def assess_brief(self, brief_json: str, base_url: str = "", api_key: str = "",
                     model: str = "", *, sender: str | None = None) -> dict:
        """Instance-side LLM assessment over eth_call (R1 S3 恢复的导出面).

        `brief_json` = DealBrief four-field JSON string. Mode contract: empty
        `base_url` OR `api_key` => HeuristicModel replay (lib.rs:625-635);
        both non-empty => real backend. Returns the parsed report dict
        (`qualification_score`/`risks`/`est_duration_ms`/`est_confidence`).

        Trust hole (documented, lib.rs doc): the backend params travel in the
        eth_call calldata, so any chain reader sees `api_key`. Demo-only;
        never log or archive the key. eth_call runs node-locally, so the
        instance `assessment_cache` write does not reach consensus (R1 note).
        """
        raw = self._view("assess_brief(string,string,string,string)",
                         (brief_json, base_url, api_key, model),
                         frm=self._addr(sender or self.sender))
        return json.loads(raw)


# ---------------------------------------------------------------------------
# FakeNode — orchestration smoke mode (semantics mirror rust core)
# ---------------------------------------------------------------------------

SLOT_MS = 400
SAFETY = 2


@dataclass
class _Evidence:
    seq: int
    frm: str
    to: str
    payload_digest: str
    slot: int


@dataclass
class _Deal:
    buyer: str
    seller: str
    broker: str
    amount: int
    fee_bps: int
    terms_digest: str
    est_duration_ms: int
    timeout_slots: int
    state: str = "Qualified"          # Qualified/Funded/Submitted/Disputed/Settled/Refunded
    funded_slot: int | None = None
    deliverable_digest: str | None = None
    committee_cert: tuple | None = None


class FakeNode:
    """Clock is manual: `tick()` advances one slot; watcher polls due_deals."""

    def __init__(self):
        self.slot = 0
        self.deals: dict[str, _Deal] = {}
        self.balances: dict[str, int] = {}
        self.evidence: dict[str, list[_Evidence]] = {}
        self.committee = ["node-1", "node-2", "node-3", "node-4"]
        self.threshold = 3
        self.misconduct: dict[str, int] = {}
        self._n = 0

    # -- clock --
    def tick(self, n: int = 1):
        self.slot += n

    def _deadline(self, d: _Deal):
        return None if d.funded_slot is None else d.funded_slot + d.timeout_slots

    # -- surface mirroring NodeClient --
    def faucet(self, agent, amount): self.balances[agent] = self.balances.get(agent, 0) + amount

    def create_deal(self, buyer, seller, amount, fee_bps, terms_d, acceptance_d, est_ms, est_conf):
        # lib.rs:189 mirror: u128 there can only be == 0; Python ints admit
        # negatives too, so the same guard is spelled `<= 0`. (The rest of
        # lib.rs's platform-side input validation is deliberately NOT
        # mirrored here — known non-mirrored item, see plan §三.B.)
        if amount <= 0:
            raise RuntimeError("amount must be > 0")
        self._n += 1
        did = f"deal-{self._n}"
        self.deals[did] = _Deal(
            buyer=buyer, seller=seller, broker="agent-broker", amount=amount, fee_bps=fee_bps,
            terms_digest=terms_d, est_duration_ms=est_ms,
            timeout_slots=max(1, est_ms * SAFETY // SLOT_MS),
        )
        return did

    def fund(self, deal_id):
        d = self.deals[deal_id]
        assert d.state == "Qualified", d.state
        if self.balances.get(d.buyer, 0) < d.amount:
            raise RuntimeError("insufficient balance")
        self.balances[d.buyer] -= d.amount
        d.state, d.funded_slot = "Funded", self.slot
        return True

    def notarize(self, deal_id, frm, to, payload_digest):
        # lib.rs notarize guard mirror ("self-signed only"): anyone may
        # submit, but the entry's `from` must be the submitter. A real node
        # enforces from == caller (connection identity, post-W1); the sim has
        # no caller concept, so it approximates the same contract with deal
        # party membership.
        d = self.deals.get(deal_id)
        if d is None:
            # Deliberate sim-side TIGHTENING: no deal -> no party set to
            # anchor authorship on, so pre-deal notarization is refused
            # (a real node appends into a per-deal log regardless).
            raise RuntimeError("no such deal: cannot establish authorship")
        if frm not in (d.buyer, d.seller, d.broker):
            raise RuntimeError("notarize is self-signed only (sim): from must be a deal party")
        log = self.evidence.setdefault(deal_id, [])
        log.append(_Evidence(len(log), frm, to, payload_digest, self.slot))
        return log[-1].seq

    def submit_deliverable(self, deal_id, dd):
        d = self.deals[deal_id]
        dl = self._deadline(d)
        assert d.state == "Funded", d.state
        assert dl is not None and self.slot <= dl, "deadline passed"
        d.deliverable_digest, d.state = dd, "Submitted"
        return True

    def complete(self, deal_id):
        d = self.deals[deal_id]
        assert d.state == "Submitted", d.state
        fee = d.amount * d.fee_bps // 10_000
        self.balances[d.seller] = self.balances.get(d.seller, 0) + d.amount - fee
        self.balances[d.broker] = self.balances.get(d.broker, 0) + fee
        d.state = "Settled"
        return True

    def claim_timeout(self, deal_id):
        d = self.deals[deal_id]
        dl = self._deadline(d)
        assert d.state == "Funded", d.state          # guard: no evidence submitted
        assert dl is not None and self.slot >= dl, "deadline not reached"
        self.balances[d.buyer] = self.balances.get(d.buyer, 0) + d.amount
        d.state = "Refunded"
        return True

    def cancel(self, deal_id):
        d = self.deals[deal_id]
        assert d.state in ("Qualified", "Funded"), d.state
        if d.state == "Funded":
            self.balances[d.buyer] = self.balances.get(d.buyer, 0) + d.amount
        d.state = "Refunded"
        return True

    def open_dispute(self, deal_id, reason_digest):
        d = self.deals[deal_id]
        assert d.state in ("Funded", "Submitted"), d.state
        d.state = "Disputed"
        return True

    def apply_committee_verdict(self, deal_id, cert, caller):
        verdict_code, cert_root, signers = cert   # domain triple: (verdict, evidence_root, signers)
        d = self.deals[deal_id]
        assert d.state == "Disputed", d.state
        # lib.rs:365-368 mirror: the caller must sit on the committee AND
        # have signed the certificate personally (require(Access::Committee)
        # + caller-in-signers).
        if caller not in self.committee:
            raise RuntimeError("caller not a committee member")
        if caller not in signers:
            raise RuntimeError("caller must be among the certificate signers")
        # core.rs validate_cert mirror: no duplicates, all signers are
        # members, threshold reached.
        if len(set(signers)) != len(signers):
            raise RuntimeError("invalid signer set (duplicate signers)")
        for s in signers:
            if s not in self.committee:
                raise RuntimeError(f"non-member signer: {s}")
        if len(signers) < self.threshold:
            raise RuntimeError(f"insufficient committee signers: got {len(signers)}, need {self.threshold}")
        # Same-source root check (lib.rs:369-371 mirror: read-derive-verify on
        # one slice): the root is folded from THIS node's own evidence log and
        # compared against the cert. Deliberately same-source, NOT independent
        # verification — see the README trust table; independence arrives with
        # the W4 oracle certified-call.
        folded = evidence_root(self.evidence_entries(deal_id))
        if cert_root != folded:
            raise RuntimeError("committee cert evidence_root mismatch (MissingCert mirror)")
        verdict = {0: "Fulfilled", 1: "NotFulfilled", 2: "Malicious"}[verdict_code]
        # payout / misconduct / final state — verified aligned with core.rs in
        # plan §三.A3 (fee floor, zero-payout qualified-cancel, single-point
        # misconduct bump, verdict->state mapping); unchanged here.
        if verdict == "Fulfilled":
            fee = d.amount * d.fee_bps // 10_000
            self.balances[d.seller] = self.balances.get(d.seller, 0) + d.amount - fee
            self.balances[d.broker] = self.balances.get(d.broker, 0) + fee
            d.state = "Settled"
        else:
            self.balances[d.buyer] = self.balances.get(d.buyer, 0) + d.amount
            d.state = "Refunded"
            if verdict == "Malicious":
                self.misconduct[d.seller] = self.misconduct.get(d.seller, 0) + 1
        return True

    def committee_config(self, members, threshold):
        self.committee, self.threshold = list(members), int(threshold)

    def deal_info(self, deal_id):
        d = self.deals[deal_id]
        return {
            "id": deal_id, "buyer": d.buyer, "seller": d.seller, "amount": d.amount,
            "state": d.state, "timeout_slots": d.timeout_slots, "deadline_slot": self._deadline(d),
        }

    def evidence_entries(self, deal_id):
        """JSON shape of the deal's evidence log (mirror of the chain's
        evidence_entries_json getter; unknown deal -> empty list, same as
        lib.rs's unwrap_or_default). Field is spelled `from` on the wire,
        `frm` in the dataclass."""
        return [
            {"seq": e.seq, "from": e.frm, "to": e.to, "payload_digest": e.payload_digest, "slot": e.slot}
            for e in self.evidence.get(deal_id, [])
        ]

    def balance_of(self, agent): return self.balances.get(agent, 0)

    def due_deals(self, now=None):
        now = self.slot if now is None else now
        return [
            did for did, d in self.deals.items()
            if d.state == "Funded" and self._deadline(d) is not None and now >= self._deadline(d)
        ]
