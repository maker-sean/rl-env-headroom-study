"""Phase 3 analysis: results table, pass@k, variance, cost, failure taxonomy,
and a scorecard for every pre-registered prediction.

Usage: uv run python scripts/11_analyze.py results/full_test.json

Reads the aggregated run file for rewards/metrics/cost and the raw traces for
latency. Writes results/analysis_<tag>_<split>.json. Every number printed here
comes from those files; nothing is estimated.
"""
import json, math, sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, pstdev

SCALARS = ("subtotal", "tax", "service_charge", "discount", "total")
COMPONENTS = ("schema_valid", "scalar_f1", "line_item_f1", "grounding")
TIERS = ("small", "mid", "frontier")
CONDS = ("ocr_text", "image")


def pass_at_k(n: int, c: int, k: int) -> float:
    """Unbiased pass@k: probability >=1 of k sampled rollouts is correct."""
    if k > n:
        return float("nan")
    if n - c < k:
        return 1.0
    return 1.0 - math.comb(n - c, k) / math.comb(n, k)


def latency_by_cell(tag, split):
    out = {}
    for d in sorted(Path("outputs").glob(f"{tag}-{split}-*")):
        f = d / "traces.jsonl"
        if not f.exists():
            continue
        model_s, agent_s = [], []
        for line in f.read_text().splitlines():
            if not line.strip():
                continue
            tr = (json.loads(line).get("traces") or [{}])[0]
            t = tr.get("timing") or {}
            ag = t.get("agent") or {}
            md = (ag.get("model") or {}).get("duration")
            if md is not None:
                model_s.append(md)
            if ag.get("start") and ag.get("end"):
                agent_s.append(ag["end"] - ag["start"])
        if model_s:
            out[d.name] = {"model_s_mean": mean(model_s),
                           "model_s_p50": sorted(model_s)[len(model_s)//2],
                           "model_s_p95": sorted(model_s)[int(len(model_s)*0.95)-1],
                           "agent_s_mean": mean(agent_s) if agent_s else None}
    return out


def main(path):
    d = json.load(open(path))
    tag, split = d["tag"], d["split"]
    runs = d["runs"]
    lat = latency_by_cell(tag, split)
    A = {"source": path, "git": d.get("git"), "split": split, "tag": tag,
         "docs": d["docs"], "samples": d["samples"],
         "temperature": d["temperature"], "harness": d.get("harness"),
         "cells": {}}

    print(f"git={d.get('git')}  split={split}  docs={d['docs']}  "
          f"samples={d['samples']}  T={d['temperature']}  harness={d.get('harness')}")
    mt = d.get("measured_total_usd")
    if mt is None:
        mt = sum((v.get("measured_cost_usd") or 0) for v in runs.values())
    print(f"measured total cost: ${mt:.4f}\n")
    A["measured_total_usd"] = round(mt, 4)

    # ---------------- main table ----------------
    print("RESULTS  (mean over all rollouts)")
    hdr = f"{'tier':<9} {'cond':<9} {'n':>7} {'reward':>8} {'sd':>6} " + \
          " ".join(f"{c[:9]:>9}" for c in COMPONENTS) + f" {'exact':>7}"
    print(hdr); print("-" * len(hdr))
    for t in TIERS:
        for c in CONDS:
            v = runs.get(f"{t}|{c}")
            if not v or "rows" not in v:
                print(f"{t:<9} {c:<9} MISSING"); continue
            rows = v["rows"]
            n = len(rows)
            rew = [r["reward"] for r in rows]
            comps = {k: mean([(r["components"].get(k) or 0.0) for r in rows]) for k in COMPONENTS}
            exact = mean([(r["metrics"].get("doc_exact_match") or 0.0) for r in rows])
            print(f"{t:<9} {c:<9} {n:>7} {mean(rew):>8.4f} {pstdev(rew):>6.3f} " +
                  " ".join(f"{comps[k]:>9.4f}" for k in COMPONENTS) + f" {exact:>7.3f}")
            # per-doc grouping for pass@k and within-doc variance
            byd = defaultdict(list)
            for r in rows:
                byd[r["doc_index"]].append(r)
            within = [pstdev([x["reward"] for x in g]) for g in byd.values() if len(g) > 1]
            pk = {}
            for k in (1, 3, 5, 10):
                vals = []
                for g in byd.values():
                    nn = len(g)
                    cc = sum(1 for x in g if (x["metrics"].get("doc_exact_match") or 0) == 1.0)
                    p = pass_at_k(nn, cc, k)
                    if not math.isnan(p):
                        vals.append(p)
                pk[f"pass@{k}"] = mean(vals) if vals else None
            cost = v["measured_cost_usd"]
            n_correct = sum(1 for r in rows if (r["metrics"].get("doc_exact_match") or 0) == 1.0)
            cellname = f"{tag}-{split}-{c}-{v['model'].split('/')[-1]}"
            A["cells"][f"{t}|{c}"] = {
                "model": v["model"], "n": n, "docs": len(byd),
                "reward_mean": mean(rew), "reward_sd": pstdev(rew),
                "within_doc_sd_mean": mean(within) if within else None,
                "components": comps, "doc_exact_match": exact,
                "n_exact": n_correct, **pk,
                "cost_usd": cost,
                "cost_per_rollout": cost / n,
                "cost_per_correct": (cost / n_correct) if n_correct else None,
                "in_tok_per_call": v["in_tok_per_call"],
                "latency": lat.get(cellname),
            }

    # ---------------- deltas ----------------
    print("\nPRIMARY OUTCOME: condition delta (ocr_text minus image)")
    print(f"{'tier':<9} {'ocr':>8} {'image':>8} {'delta':>8}")
    print("-" * 36)
    deltas = {}
    for t in TIERS:
        a, b = A["cells"].get(f"{t}|ocr_text"), A["cells"].get(f"{t}|image")
        if not (a and b):
            continue
        deltas[t] = a["reward_mean"] - b["reward_mean"]
        print(f"{t:<9} {a['reward_mean']:>8.4f} {b['reward_mean']:>8.4f} {deltas[t]:>+8.4f}")
    A["condition_deltas"] = deltas

    # ---------------- pass@k, variance, cost, latency ----------------
    print("\nPASS@K on document exact match, within-doc variance, cost, latency")
    print(f"{'cell':<20} {'p@1':>7} {'p@3':>7} {'p@5':>7} {'p@10':>7} "
          f"{'sd(doc)':>8} {'$/roll':>9} {'$/correct':>10} {'lat_s':>7}")
    print("-" * 94)
    for t in TIERS:
        for c in CONDS:
            v = A["cells"].get(f"{t}|{c}")
            if not v: continue
            L = (v.get("latency") or {}).get("model_s_mean")
            lat_s = f"{L:.2f}" if L else "n/a"
            cpc = v["cost_per_correct"]
            cpc_s = f"{cpc:.4f}" if cpc else "n/a"
            def fmt(x):
                return f"{x:.3f}" if isinstance(x, float) and not math.isnan(x) else "n/a"
            print(f"{t+'|'+c:<20} {fmt(v['pass@1']):>7} {fmt(v['pass@3']):>7} "
                  f"{fmt(v['pass@5']):>7} {fmt(v['pass@10']):>7} "
                  f"{(v['within_doc_sd_mean'] or 0):>8.3f} {v['cost_per_rollout']:>9.5f} "
                  f"{cpc_s:>10} {lat_s:>7}")

    # ---------------- failure taxonomy ----------------
    print("\nFAILURE TAXONOMY (counts over rollouts)")
    tax = {}
    for t in TIERS:
        for c in CONDS:
            v = runs.get(f"{t}|{c}")
            if not v or "rows" not in v: continue
            rows = v["rows"]; n = len(rows)
            inv = Counter(); mis = Counter(); wrg = Counter()
            fmt = Counter(); item_name_err = 0; item_price_err = 0; ungrounded = 0
            for r in rows:
                m = r["metrics"]
                for f in SCALARS:
                    if (m.get(f"invented_{f}") or 0) == 1.0: inv[f] += 1
                    if (m.get(f"missed_{f}") or 0) == 1.0: mis[f] += 1
                    if (m.get(f"wrong_{f}") or 0) == 1.0: wrg[f] += 1
                for k in ("clean", "fenced", "embedded", "invalid"):
                    if (m.get(f"format_{k}") or 0) == 1.0: fmt[k] += 1
                item_price_err += int(m.get("item_price_wrong") or 0)
                nm_unmatched = (m.get("n_pred_items") or 0) - (m.get("item_name_matched") or 0)
                item_name_err += int(max(0, nm_unmatched))
                if (m.get("values_grounded") or 0) < (m.get("values_emitted") or 0):
                    ungrounded += 1
            tax[f"{t}|{c}"] = {
                "n": n, "invented": dict(inv), "missed": dict(mis), "wrong_value": dict(wrg),
                "format": dict(fmt), "item_name_unmatched": item_name_err,
                "item_price_wrong": item_price_err,
                "rollouts_with_ungrounded_value": ungrounded,
                "pct_rollouts_with_ungrounded_value": ungrounded / n,
            }
            top_inv = ", ".join(f"{k}={x}" for k, x in inv.most_common(3)) or "none"
            top_mis = ", ".join(f"{k}={x}" for k, x in mis.most_common(3)) or "none"
            print(f"  {t+'|'+c:<20} invented[{top_inv}]  missed[{top_mis}]  "
                  f"name_unmatched={item_name_err}  price_wrong={item_price_err}  "
                  f"ungrounded={ungrounded}/{n}")
    A["taxonomy"] = tax

    # Spend log, required by CLAUDE.md: measured, never estimated.
    # Spend log, required by CLAUDE.md: measured, never estimated. Keyed on
    # the run, so re-running the analyzer (or analyzing a re-scored copy of
    # the same rollouts) updates a row instead of billing the study twice.
    spend = Path("results/spend.csv")
    hdr = "run_tag,split,git,tier,condition,model,rollouts,in_tokens,out_tokens,usd\n"
    existing = {}
    if spend.exists():
        for ln in spend.read_text().splitlines():
            if not ln.strip() or ln.startswith("run_tag"):
                continue
            existing[tuple(ln.split(",")[:5])] = ln + "\n"
    added = 0
    for key, v in runs.items():
        if "rows" not in v:
            continue
        t, c = key.split("|")
        k = (tag, split, str(d.get("git")), t, c)
        row = (f"{tag},{split},{d.get('git')},{t},{c},{v['model']},"
               f"{v['rollouts']},{v['in_tok_total']},{v['out_tok_total']},"
               f"{v['measured_cost_usd']:.6f}\n")
        if k not in existing:
            added += 1
        existing[k] = row
    spend.write_text(hdr + "".join(existing.values()))
    print(f"spend log: {len(existing)} rows ({added} new) in {spend}")

    Path("results").mkdir(exist_ok=True)
    # A re-scored copy of a run is a distinct analysis and gets its own file.
    suffix = "_fixed" if Path(path).stem.endswith("_fixed") else ""
    dest = Path("results") / f"analysis_{tag}_{split}{suffix}.json"
    dest.write_text(json.dumps(A, indent=2, default=str))
    print(f"\nwrote {dest}")
    return A


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "results/full_test.json")
