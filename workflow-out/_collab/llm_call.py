#!/usr/bin/env python3
"""glm-dsh-collab manual orchestration driver (API direct calls).

Reads provider keys from ~/.zcode/v2/config.json (never prints them).
Both configured providers speak the Anthropic messages protocol:
  bigmodel -> https://open.bigmodel.cn/api/anthropic  (GLM-5.3 / GLM-5.3-Flash)
  deepseek -> https://api.deepseek.com/anthropic      (deepseek-flash)

Usage:
  python llm_call.py --provider deepseek --model deepseek-flash \
      --system-file sys.txt --user-file user.txt --out resp.txt [--max-tokens 8000]

Retry policy: on 429/5xx/timeout sleep 60s and retry, up to 3 attempts
(user standing instruction: retry every minute when blocked).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

CONFIG = Path.home() / ".zcode" / "v2" / "config.json"


def provider_base(provider: str) -> tuple[str, str, str]:
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    key = "builtin:bigmodel-coding-plan" if provider == "bigmodel" else "deepseek"
    if key not in cfg.get("provider", {}):
        key = provider
    p = cfg["provider"][key]
    if not p.get("enabled", True):
        raise SystemExit(f"provider {provider} disabled")
    base = (p.get("options") or {}).get("baseURL", "").rstrip("/")
    api = (p.get("options") or {}).get("apiKey", "")
    model_default = sorted(p.get("models", {}).keys())
    return base, api, (model_default[0] if model_default else "")


def call(provider: str, model: str, system: str, user: str, max_tokens: int) -> str:
    base, api, default_model = provider_base(provider)
    if not model:
        model = default_model
    url = f"{base}/v1/messages"
    body = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "content-type": "application/json",
            "x-api-key": api,
            "authorization": f"Bearer {api}",
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    last = ""
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                data = json.loads(r.read().decode("utf-8"))
            texts = [b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"]
            usage = data.get("usage", {})
            print(f"[{provider}/{model}] attempt {attempt} ok  in={usage.get('input_tokens')} out={usage.get('output_tokens')}", file=sys.stderr)
            return "".join(texts)
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:300]}"
        except Exception as e:  # noqa: BLE001
            last = f"{type(e).__name__}: {e}"
        print(f"[{provider}/{model}] attempt {attempt} failed: {last}", file=sys.stderr)
        if attempt < 3:
            time.sleep(60)
    raise SystemExit(f"all attempts failed: {last}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", required=True, choices=["deepseek", "bigmodel"])
    ap.add_argument("--model", default="")
    ap.add_argument("--system-file", required=True)
    ap.add_argument("--user-file", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-tokens", type=int, default=8000)
    a = ap.parse_args()
    system = Path(a.system_file).read_text(encoding="utf-8")
    user = Path(a.user_file).read_text(encoding="utf-8")
    out = call(a.provider, a.model, system, user, a.max_tokens)
    Path(a.out).write_text(out, encoding="utf-8")
    print(f"written: {a.out} ({len(out)} chars)")


if __name__ == "__main__":
    main()
