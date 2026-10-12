"""A2A message protocol: the layer agents already speak (plain JSON messages,
A2A/MCP-shaped in the full story), whose DIGESTS get notarized on-chain.

Digest rule (must match the Lyquid side and stay x402-#2833-compatible):
    digest = sha256(canonical_json(envelope))
    canonical_json = json.dumps(..., sort_keys=True, separators=(",", ":"))
Each envelope carries kind/payload/from/to so the chain-side log can be
re-derived and verified by anyone (committee included).
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
