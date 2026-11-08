"""Probe which catalogued models are ACTUALLY callable.

The public catalog lists models that the gateway will not serve: a request for
qwen/qwen3-vl-8b-instruct is refused with "No allowed providers are available
for the selected model. Providers serving ...: parasail, but your request's
provider.only preference permits only: alibaba."

So callability has to be measured, not read. Each probe sends a 1-token
completion, which costs a fraction of a cent, and records the outcome.
"""
import json, os, sys, time
from pathlib import Path

import urllib.error, urllib.request

BASE = "https://api.pinference.ai/api/v1"
KEY = json.load(open(os.path.expanduser("~/.prime/config.json")))["api_key"]

CANDIDATES = [
    # hosted = Prime's own infrastructure
    ("qwen/qwen3.5-9b", "hosted"),
    ("qwen/qwen3.8-27b", "hosted"),
    ("qwen/qwen3.6-35b-a3b", "hosted"),
    ("google/gemma-4-26b-a4b-it", "hosted"),
    ("google/gemma-4-31b-it", "hosted"),
    ("openai/gpt-oss-120b", "hosted"),
    ("z-ai/glm-5.3-flash", "hosted"),
    ("deepseek/deepseek-v4.1-flash", "hosted"),
    ("moondream/moondream3.1-9b-a2b", "hosted"),
    # gateway routed
    ("qwen/qwen3-vl-8b-instruct", "gateway"),
    ("qwen/qwen3-vl-30b-a3b-instruct", "gateway"),
    ("qwen/qwen3-vl-235b-a22b-instruct", "gateway"),
    ("google/gemma-3-27b-it", "gateway"),
    ("mistralai/mistral-small-2603", "gateway"),
    ("openai/gpt-5-nano", "gateway"),
    ("anthropic/claude-haiku-4.5", "gateway"),
    ("anthropic/claude-sonnet-5.5", "gateway"),
    ("anthropic/claude-opus-5.5", "gateway"),
]


def probe(model: str) -> dict:
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 1,
    }).encode()
    req = urllib.request.Request(
        f"{BASE}/chat/completions", data=body,
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            d = json.loads(r.read())
        u = d.get("usage") or {}
        return {"ok": True, "latency_s": round(time.time() - t0, 2),
                "in_tok": u.get("prompt_tokens"), "out_tok": u.get("completion_tokens")}
    except urllib.error.HTTPError as e:
        raw = e.read().decode()[:400]
        msg = raw
        try:
            msg = json.loads(raw)["error"]["message"][:260]
        except Exception:
            pass
        return {"ok": False, "status": e.code, "error": msg,
                "latency_s": round(time.time() - t0, 2)}
    except Exception as e:
        return {"ok": False, "status": None, "error": f"{type(e).__name__}: {e}"[:260],
                "latency_s": round(time.time() - t0, 2)}


def main():
    results = {}
    print(f"{'model':<36} {'serving':<8} {'result':<9} {'lat':>6}  note")
    print("-" * 100)
    for model, serving in CANDIDATES:
        r = probe(model)
        results[model] = dict(r, serving=serving)
        if r["ok"]:
            print(f"{model:<36} {serving:<8} {'CALLABLE':<9} {r['latency_s']:>5}s  "
                  f"in={r['in_tok']} out={r['out_tok']}")
        else:
            print(f"{model:<36} {serving:<8} {'REFUSED':<9} {r['latency_s']:>5}s  "
                  f"[{r.get('status')}] {r['error'][:60]}")
    ok = [m for m, r in results.items() if r["ok"]]
    print(f"\ncallable: {len(ok)}/{len(CANDIDATES)}")
    Path("provenance").mkdir(exist_ok=True)
    Path("provenance/model_availability.json").write_text(json.dumps(
        {"probed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
         "base_url": BASE, "results": results}, indent=2))
    print("wrote provenance/model_availability.json")


if __name__ == "__main__":
    sys.exit(main())
