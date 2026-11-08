"""Run the eval across model tiers and input conditions, then aggregate.

Every combination is a separate `vf-run` invocation, because the taskset's
`condition` is load-time config. Traces land in outputs/<run-name>/ and are
aggregated into results/.

Usage:
  uv run python scripts/09_run_eval.py --split validation --docs 20 --samples 3 --tag pilot
  uv run python scripts/09_run_eval.py --split test --docs 100 --samples 10 --tag full

Concurrency is held low and retries are enabled because Prime's hosted models
return 429 "Too many concurrent hosted model requests" even on a single
sequential request (FRICTION.md F-012).
"""
import argparse, json, os, subprocess, sys, time
from pathlib import Path
from statistics import mean, pstdev

TIERS = {
    "small":    "qwen/qwen3.5-9b",
    "mid":      "qwen/qwen3-vl-30b-a3b-instruct",
    "frontier": "anthropic/claude-opus-5.5",
}
CONDITIONS = ("ocr_text", "image")
PRICES = {  # USD per 1M tokens, from provenance/MODEL_TIERS.md
    "qwen/qwen3.5-9b": (0.063, 0.093),
    "qwen/qwen3-vl-30b-a3b-instruct": (0.200, 0.700),
    "anthropic/claude-opus-5.5": (4.000, 20.000),
}


def git_stamp() -> str:
    """Commit plus a dirty marker. Every result must trace to a tree state."""
    try:
        rev = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain"],
                               capture_output=True, text=True).stdout.strip()
        return f"{rev}{'-DIRTY' if dirty else ''}"
    except Exception:
        return "unknown"


def api_key() -> str:
    return json.load(open(os.path.expanduser("~/.prime/config.json")))["api_key"]


HARNESS = "null"


def run_one(model, condition, split, docs, samples, tag, temperature, concurrent,
            prompt_variant=None):
    name = f"{tag}-{split}-{condition}-{model.split('/')[-1]}"
    cmd = [
        "uv", "run", "vf-run", "doc-extraction-study",
        "-m", model, "-n", str(docs), "-r", str(samples),
        "--env.taskset.split", split,
        "--env.taskset.limit", str(docs),
        "--env.taskset.condition", condition,
        *(["--env.taskset.prompt_variant", prompt_variant]
          if prompt_variant else []),
        # MUST be null. vf-run defaults to the `bash` harness even for a
        # taskset with no tools, which prepends "You are a coding agent. You
        # have access to a bash tool..." before our system prompt and gives the
        # model tools. The mid tier then answered in prose and scored 0.0000 on
        # all 60 pilot rollouts. Prime's own eval-source examples use "null".
        "--env.agent.harness.id", "null",
        "--env.agent.runtime.type", "subprocess",
        "--env.agent.retries.max-retries", "4",
        "--sampling.temperature", str(temperature),
        "--sampling.max-tokens", "1500",
        "--max-concurrent", str(concurrent),
        "--run.name", name,
    ]
    env = dict(os.environ, PRIME_API_KEY=api_key(), PATH=os.environ["PATH"])
    t0 = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True, env=env)
    tail = (p.stdout or "").strip().splitlines()[-1:] or [(p.stderr or "")[-200:]]
    print(f"    {tail[0][:120]}  [{time.time()-t0:.0f}s]")
    return name, p.returncode


def aggregate(name):
    f = Path("outputs") / name / "traces.jsonl"
    if not f.exists():
        return None
    eps = [json.loads(l) for l in f.read_text().splitlines() if l.strip()]
    rows = []
    for ep in eps:
        data = (ep.get("task") or {}).get("data") or {}
        tr = (ep.get("traces") or [{}])[0]
        rw = {k: (v.get("score") if isinstance(v, dict) else v)
              for k, v in (tr.get("rewards") or {}).items()}
        wt = {k: (v.get("weight") if isinstance(v, dict) else None)
              for k, v in (tr.get("rewards") or {}).items()}
        total = sum((rw[k] or 0) * (wt[k] or 0) for k in rw if wt.get(k) is not None)
        mt = {}
        for k, v in (tr.get("metrics") or {}).items():
            val = v.get("value") if isinstance(v, dict) else v
            if isinstance(val, dict):
                mt.update(val)
            else:
                mt[k] = val
        rows.append({
            "doc_id": data.get("id"), "doc_index": data.get("doc_index"),
            "condition": data.get("condition"), "reward": total,
            "components": rw, "metrics": mt, "ok": tr.get("ok"),
            "stop": tr.get("stop_condition"),
            "in_tok": tr.get("num_input_tokens") or 0,
            "out_tok": tr.get("num_output_tokens") or 0,
        })
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="validation")
    ap.add_argument("--docs", type=int, default=20)
    ap.add_argument("--samples", type=int, default=3)
    ap.add_argument("--tag", default="pilot")
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--concurrent", type=int, default=2)
    ap.add_argument("--tiers", default="small,mid,frontier")
    ap.add_argument("--conditions", default="ocr_text,image")
    # Only a post-hoc run (deviation D7) passes this. Omitted, the taskset
    # uses the pre-registered prompt, so the claim path cannot change silently.
    ap.add_argument("--prompt-variant", default=None)
    a = ap.parse_args()

    want = [t.strip() for t in a.tiers.split(",") if t.strip()]
    conds = tuple(c.strip() for c in a.conditions.split(",") if c.strip())
    assert set(conds) <= set(CONDITIONS), conds
    stamp = git_stamp()
    out = {"tag": a.tag, "split": a.split, "docs": a.docs, "samples": a.samples,
           "temperature": a.temperature, "harness": HARNESS,
           "concurrent": a.concurrent, "tiers": TIERS, "prices": PRICES,
           "conditions": list(conds), "prompt_variant": a.prompt_variant,
           "git": stamp, "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
           "runs": {}}
    print(f"git={stamp}  split={a.split}  docs={a.docs}  samples={a.samples}  "
          f"T={a.temperature}  harness={HARNESS}  "
          f"prompt={a.prompt_variant or 'pre-registered'}\n")

    # Cheapest tier first: the frontier cell is ~93% of spend, so ordering it
    # last means a balance that runs out loses only that cell, and each cell is
    # an independent vf-run with its own traces file.
    order = [t for t in ("small", "mid", "frontier") if t in want]
    for tier in order:
        model = TIERS[tier]
        for cond in conds:
            print(f"  {tier:<9} {model:<34} {cond}")
            name, rc = run_one(model, cond, a.split, a.docs, a.samples, a.tag,
                               a.temperature, a.concurrent, a.prompt_variant)
            rows = aggregate(name)
            if not rows:
                out["runs"][f"{tier}|{cond}"] = {"error": "no traces", "rc": rc}
                continue
            good = [r for r in rows if r["ok"]]
            pin, pout = PRICES[model]
            cost = (sum(r["in_tok"] for r in rows) / 1e6 * pin
                    + sum(r["out_tok"] for r in rows) / 1e6 * pout)
            rewards = [r["reward"] for r in good]
            out["runs"][f"{tier}|{cond}"] = {
                "model": model, "run_name": name, "rollouts": len(rows),
                "ok": len(good), "failed": len(rows) - len(good),
                "reward_mean": round(mean(rewards), 4) if rewards else None,
                "reward_sd": round(pstdev(rewards), 4) if len(rewards) > 1 else None,
                "in_tok_total": sum(r["in_tok"] for r in rows),
                "out_tok_total": sum(r["out_tok"] for r in rows),
                "in_tok_per_call": round(mean([r["in_tok"] for r in rows]), 1),
                "measured_cost_usd": round(cost, 5),
                "rows": rows,
            }
            print(f"      n={len(good)}/{len(rows)}  reward={out['runs'][f'{tier}|{cond}']['reward_mean']}"
                  f"  in/call={out['runs'][f'{tier}|{cond}']['in_tok_per_call']}"
                  f"  cost=${cost:.4f}")

    Path("results").mkdir(exist_ok=True)
    dest = Path("results") / f"{a.tag}_{a.split}.json"
    dest.write_text(json.dumps(out, indent=2))
    out["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    total = sum(r.get("measured_cost_usd", 0) or 0 for r in out["runs"].values())
    out["measured_total_usd"] = round(total, 4)
    dest.write_text(json.dumps(out, indent=2))
    print(f"\nMEASURED TOTAL COST: ${total:.4f}")
    print(f"wrote {dest}")


if __name__ == "__main__":
    sys.exit(main())
