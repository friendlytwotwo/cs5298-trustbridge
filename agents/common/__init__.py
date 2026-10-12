"""TrustBridge agent-side shared library.

Modules:
    protocol — message types + canonical JSON + sha256 digests (what gets notarized)
    rpc      — node client (real devnet transport + FakeNode sim for smoke tests)
    llm      — pluggable LLM (ScriptedMock for replay, OpenAI-compat for live)
"""
