"""A2A message protocol: the layer agents already speak (plain JSON messages,
A2A/MCP-shaped in the full story), whose DIGESTS get notarized on-chain.

Digest rule (must match the Lyquid side and stay x402-#2833-compatible):
    digest = sha256(canonical_json(envelope))
    canonical_json = json.dumps(..., sort_keys=True, separators=(",", ":"))
Each envelope carries kind/payload/from/to so the chain-side log can be
re-derived and verified by anyone (committee included).

Notarize authorship (连接身份 = `from` | connection identity = `from`):
    A notarized entry's `from` field is bound to the SUBMITTER's identity at
    the transport layer — whoever posts the transaction owns the authorship
    claim. The Rust node enforces `from == caller` (lib.rs notarize guard;
    the caller has a real identity only after W1), so every entry is
    caller-self-signed and the committee's attribution checks rest on trusted
    authorship. FakeNode simulates the same contract on demo terms: it
    accepts an entry only when `from` is one of the deal's three parties
    (buyer/seller/broker). The wire-level `from` parameter is kept so
    rpc.py:49 stays wire-compatible.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field


def canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(obj) -> str:
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


def envelope(kind: str, payload: dict, frm: str, to: str, deal_id: str | None = None) -> dict:
    return {"kind": kind, "payload": payload, "from": frm, "to": to, "deal_id": deal_id}


# ---------------------------------------------------------------------------
# Evidence-root folding (FNV-1a 64) — same spec as lyquid/src/core.rs
# ---------------------------------------------------------------------------

FNV1A64_OFFSET_BASIS = 0xcbf29ce484222325
FNV1A64_PRIME = 0x100000001b3
_U64_MASK = (1 << 64) - 1


def _fnv1a64_fold(data: bytes, state: int) -> int:
    """Fold `data` byte-by-byte into an in-progress FNV-1a 64 state.

    Split out so `evidence_root` can chain entries into one continuous fold.
    """
    for b in data:
        state = ((state ^ b) * FNV1A64_PRIME) & _U64_MASK
    return state


def fnv1a64(data: bytes) -> str:
    """FNV-1a 64 of `data`, as 16-char lowercase hex (core.rs spec, step 4)."""
    return f"{_fnv1a64_fold(data, FNV1A64_OFFSET_BASIS):016x}"


def evidence_root(entries) -> str:
    """Root digest over a deal's ordered evidence log (NOT cryptographic).

    Spec: core.rs `evidence_root` — start from the FNV-1a 64 offset basis,
    then for each entry IN SLICE ORDER fold the canonical string
    ``"{seq}|{from}|{to}|{payload_digest}|{slot}\\n"`` (UTF-8 bytes, field
    order = EvidenceEntry's declaration order in types.rs) into the state;
    return ``format!("{:016x}")``. Empty log folds to the offset basis itself
    ("cbf29ce484222325"). Order-sensitive by construction; deliberately NOT
    re-sorted by seq.

    `entries` is a sequence of JSON-shaped dicts with keys
    seq/from/to/payload_digest/slot — the same shape the chain's
    `evidence_entries_json` getter returns.

    Same-source semantics (see README trust table): the Rust node derives the
    cert root from, and re-validates it against, the SAME chain log slice —
    read/derive/verify share one source. Deliberate same-source, not
    independent verification; independence arrives with the W4 oracle
    certified-call, at which point this folds to sha256/merkle too.
    """
    state = FNV1A64_OFFSET_BASIS
    for e in entries:
        canonical = f"{e['seq']}|{e['from']}|{e['to']}|{e['payload_digest']}|{e['slot']}\n"
        state = _fnv1a64_fold(canonical.encode("utf-8"), state)
    return f"{state:016x}"


# ---------------------------------------------------------------------------
# Message payloads
# ---------------------------------------------------------------------------

@dataclass
class OfferBrief:
    """alice -> broker: what she wants to license."""
    buyer_agent: str
    work_ref: str            # e.g. song id / ISWC
    usage_scope: str         # e.g. "online-video, 12 months, EU"
    budget: int              # internal ledger units

    def payload(self) -> dict:
        return {
            "buyer_agent": self.buyer_agent,
            "work_ref": self.work_ref,
            "usage_scope": self.usage_scope,
            "budget": self.budget,
        }


@dataclass
class Assessment:
    """broker (LLM-assisted): qualification + duration estimate -> timeout."""
    qualification_score: int
    est_duration_ms: int
    est_confidence: int
    risks: list[str] = field(default_factory=list)


@dataclass
class RequestToSeller:
    """broker -> bob: license request under escrowed terms."""
    deal_id: str
    terms_digest: str
    amount: int
    timeout_slots: int


@dataclass
class Acceptance:
    """bob -> broker/alice: signed proof-of-agreement (signature TODO W3)."""
    deal_id: str
    terms_digest: str
    accepted: bool


@dataclass
class Deliverable:
    """bob -> alice: the license grant document (hash submitted on-chain)."""
    deal_id: str
    license_doc_digest: str
    grant_summary: str


@dataclass
class DisputeNotice:
    deal_id: str
    reason_digest: str
    claim: str


KIND_OFFER = "offer"
KIND_ASSESSMENT = "assessment"
KIND_REQUEST = "request-to-seller"
KIND_ACCEPTANCE = "acceptance"
KIND_DELIVERABLE = "deliverable"
KIND_RECEIPT = "receipt"
KIND_DISPUTE = "dispute"
