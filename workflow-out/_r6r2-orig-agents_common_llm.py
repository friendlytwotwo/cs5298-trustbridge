"""Pluggable LLM for agent-side (and assessor-mirroring) calls.

B1 reproducibility rule: tests and CI always run on ScriptedLLM (deterministic
replay); live OpenAI-compatible backends are opt-in via TB_LLM=openai for the
recorded demo only. This mirrors the Lyquid-side `AssessmentModel` seam.
"""

from __future__ import annotations

import json
import os
from typing import Protocol


class LLM(Protocol):
    def complete_json(self, prompt: str) -> str: ...


class ScriptedLLM:
    """Pops pre-recorded responses in order; raises when the script runs dry
    (so a drifted orchestration fails loudly instead of silently improvising)."""

    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    def complete_json(self, prompt: str) -> str:
        if not self._responses:
            raise RuntimeError(f"script exhausted; unexpected prompt:\n{prompt[:200]}")
        return self._responses.pop(0)


class OpenAICompatLLM:
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout_s: int = 30,
    ):
        self.base_url = (base_url or os.environ.get("TB_LLM_BASE_URL", "")).rstrip("/")
        self.api_key = api_key or os.environ.get("TB_LLM_API_KEY", "")
        self.model = model or os.environ.get("TB_LLM_MODEL", "gpt-4o-mini")
        self.timeout_s = timeout_s
        if not self.base_url:
            raise RuntimeError("set TB_LLM_BASE_URL / TB_LLM_API_KEY / TB_LLM_MODEL")

    def complete_json(self, prompt: str) -> str:
        import requests

        r = requests.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
                "temperature": 0,
            },
            timeout=self.timeout_s,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


def get_llm() -> LLM:
    mode = os.environ.get("TB_LLM", "script").lower()
    if mode == "openai":
        return OpenAICompatLLM()
    return ScriptedLLM(DEFAULT_ASSESSMENT_SCRIPT)


# The broker assessor's recorded script: mirrors lyquid/src/assessor.rs
# `HeuristicModel` output so sim and Rust stay in lockstep.
DEFAULT_ASSESSMENT_SCRIPT = [
    json.dumps(
        {
            "qualification_score": 75,
            "risks": ["heuristic-mode"],
            "est_duration_ms": 60_000,
            "est_confidence": 40,
        }
    )
]


ASSESSOR_PROMPT_HEAD = (
    "You are the risk assessor of an agent-to-agent licensing marketplace.\n"
    "Score the BUYER agent's qualification and estimate fulfillment duration.\n"
    "Be conservative on duration: the number drives an enforceable on-chain\n"
    "timeout; overestimation delays refunds, underestimation causes spurious\n"
    "refunds. Respond ONLY with JSON:\n"
    '{"qualification_score": 0-100, "risks": ["..."], '
    '"est_duration_ms": <p90 ms>, "est_confidence": 0-100}\n'
)


def build_assessor_prompt(brief: dict) -> str:
    return ASSESSOR_PROMPT_HEAD + "\n" + json.dumps(brief, sort_keys=True)
