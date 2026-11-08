"""Probe which CALLABLE models actually accept image input.

The catalog's specs.modalities.input claims image support for 87 models, but
the same catalog lists models the gateway refuses to serve (see
scripts/06_probe_model_availability.py). Claimed capability is therefore
measured, not read. Sends one 8x8 PNG with max_tokens=1.
"""
import base64, io, json, os, time
from pathlib import Path
import urllib.error, urllib.request

from PIL import Image

BASE = "https://api.pinference.ai/api/v1"
KEY = json.load(open(os.path.expanduser("~/.prime/config.json")))["api_key"]

CANDIDATES = [
    "qwen/qwen3.5-9b", "qwen/qwen3.8-27b", "qwen/qwen3.6-35b-a3b",
    "google/gemma-4-26b-a4b-it", "google/gemma-4-31b-it",
    "z-ai/glm-5.3-flash", "deepseek/deepseek-v4.1-flash",
    "moondream/moondream3.1-9b-a2b",
    "qwen/qwen3-vl-30b-a3b-instruct", "google/gemma-3-27b-it",
    "mistralai/mistral-small-2603", "openai/gpt-5-nano",
    "anthropic/claude-haiku-4.5", "anthropic/claude-sonnet-5.5",
    "anthropic/claude-opus-5.5",
]

buf = io.BytesIO()
Image.new("RGB", (8, 8), (255, 255, 255)).save(buf, format="PNG")
DATA_URL = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def probe(model, retries=2):
    body = json.dumps({
        "model": model, "max_tokens": 1,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": "what color?"},
            {"type": "image_url", "image_url": {"url": DATA_URL}},
        ]}],
    }).encode()
    for attempt in range(retries + 1):
        req = urllib.request.Request(
            f"{BASE}/chat/completions", data=body,
            headers={"Authorization": f"Bearer {KEY}",
                     "Content-Type": "application/json"})
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                d = json.loads(r.read())
            u = d.get("usage") or {}
            return {"image_ok": True, "latency_s": round(time.time() - t0, 2),
                    "in_tok": u.get("prompt_tokens"), "attempts": attempt + 1}
        except urllib.error.HTTPError as e:
            raw = e.read().decode()[:500]
            msg = raw
            try:
                msg = json.loads(raw)["error"]["message"][:200]
            except Exception:
                pass
            if e.code == 429 and attempt < retries:
                time.sleep(4 * (attempt + 1))
                continue
            return {"image_ok": False, "status": e.code, "error": msg,
                    "attempts": attempt + 1}
        except Exception as e:
            return {"image_ok": False, "status": None,
                    "error": f"{type(e).__name__}: {e}"[:200], "attempts": attempt + 1}


results = {}
print(f"{'model':<36} {'image':<9} {'in_tok':>7} {'try':>4}  note")
print("-" * 98)
for m in CANDIDATES:
    r = probe(m)
    results[m] = r
    if r["image_ok"]:
        print(f"{m:<36} {'ACCEPTS':<9} {str(r['in_tok']):>7} {r['attempts']:>4}")
    else:
        print(f"{m:<36} {'REJECTS':<9} {'-':>7} {r['attempts']:>4}  "
              f"[{r.get('status')}] {r['error'][:52]}")

ok = [m for m, r in results.items() if r["image_ok"]]
print(f"\naccepts images: {len(ok)}/{len(CANDIDATES)}")
print("  " + "\n  ".join(ok))
Path("provenance/image_support.json").write_text(json.dumps(
    {"probed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "results": results}, indent=2))
print("\nwrote provenance/image_support.json")
