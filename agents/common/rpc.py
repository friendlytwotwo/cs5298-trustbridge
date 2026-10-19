"""Node access for agents.

Two transports, one interface:

  NodeClient — talks to the Lyquor devnet node (default http://127.0.0.1:10087,
               JSON-RPC at /lyquor/api per the docs). The exact call envelope
               (method naming, arg encoding for Vec/struct params) is
               SPIKE(W1-4): until then `call()` posts the obvious shape and the
               demo runs on FakeNode.

  FakeNode   — in-process mirror of the Lyquid's semantics for orchestration
               smoke tests (dev velocity before the devnet is wired). The
               SOURCE OF TRUTH for deal semantics is the Rust `core` module +
               its tests; FakeNode deliberately mirrors, and demo.py prints a
               banner saying so.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from agents.common.protocol import evidence_root

DEFAULT_NODE = os.environ.get("TB_NODE", "http://127.0.0.1:10087")


class NodeClient:
    def __init__(self, base_url: str = DEFAULT_NODE):
        self.base_url = base_url.rstrip("/")

    def call(self, method: str, *args):
        import requests  # imported lazily so sim mode needs no deps

        # SPIKE(W1-4): confirm envelope — method name mangling for #[method] fns,
        # arg serialization, error shape. Placeholder uses the obvious form.
        payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": list(args)}
        r = requests.post(f"{self.base_url}/lyquor/api", json=payload, timeout=10)
        r.raise_for_status()
        body = r.json()
        if "error" in body:
            raise RuntimeError(f"node error: {body['error']}")
        return body.get("result")

    # -- convenience wrappers mirroring the Lyquid surface --
    def faucet(self, agent: str, amount: int): return self.call("faucet", agent, amount)
    def create_deal(self, buyer, seller, amount, fee_bps, terms_d, acceptance_d, est_ms, est_conf):
        return self.call("create_deal", buyer, seller, amount, fee_bps, terms_d, acceptance_d, est_ms, est_conf)
    def fund(self, deal_id): return self.call("fund", deal_id)
    def notarize(self, deal_id, frm, to, payload_digest): return self.call("notarize", deal_id, frm, to, payload_digest)
    def submit_deliverable(self, deal_id, d): return self.call("submit_deliverable", deal_id, d)
    def complete(self, deal_id): return self.call("complete", deal_id)
    def claim_timeout(self, deal_id): return self.call("claim_timeout", deal_id)
    def cancel(self, deal_id): return self.call("cancel", deal_id)
    def open_dispute(self, deal_id, reason_digest): return self.call("open_dispute", deal_id, reason_digest)
    def apply_committee_verdict(self, deal_id, cert, caller=None):
        """cert is the DOMAIN-level triple (verdict_code, evidence_root, signers)
        (types.rs CommitteeCert shape, shared with FakeNode — two transports,
        one interface).

        SPIKE(W1-4): the Rust wire carries only 2 fields
        (CommitteeCertWire { verdict_code, signers }); the chain derives the
        root itself from its own evidence log (committee.rs into_domain). The
        root travels in the domain-level cert only until the real envelope
        lands. `caller` is carried by the connection identity on a real
        transport (lib.rs `caller_agent`); it is a placeholder here and is
        deliberately NOT sent.
        """
        return self.call("apply_committee_verdict", deal_id, cert)
    def committee_config(self, members, threshold): return self.call("committee_config", members, threshold)
    def deal_info(self, deal_id): return json.loads(self.call("deal_info", deal_id))
    def evidence_entries(self, deal_id):
        """Mirror of the chain's evidence_entries_json getter."""
        return json.loads(self.call("evidence_entries_json", deal_id))
    def balance_of(self, agent): return self.call("balance_of", agent)
    def due_deals(self, now): return self.call("due_deals", now)


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
