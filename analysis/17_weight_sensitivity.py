"""Does any conclusion depend on the reward weights I chose?

The rubric weights (scalar_f1 0.45, line_item_f1 0.35, grounding 0.15,
schema_valid 0.05) were pre-registered but not derived from anything. A
reviewer is entitled to ask whether the findings are an artifact of them.

No model calls: the per-component scores of all 6,000 saved rollouts are
re-weighted under alternative schemes and every headline conclusion is
re-tested. Writes results/weight_sensitivity.json.

Usage: uv run python scripts/17_weight_sensitivity.py
"""
import json, random, sys
from collections import defaultdict
from pathlib import Path
from statistics import mean

SRC = "results/full_test_fixed.json"
SEED, B = 20261106, 10000
COMPONENTS = ("schema_valid", "scalar_f1", "line_item_f1", "grounding")
TIERS = ("small", "mid", "frontier")
CONDS = ("ocr_text", "image")

SCHEMES = {
    "registered": {"schema_valid": 0.05, "scalar_f1": 0.45,
                   "line_item_f1": 0.35, "grounding": 0.15},
    "equal": {k: 0.25 for k in COMPONENTS},
    "scalars_only": {"schema_valid": 0.0, "scalar_f1": 1.0,
                     "line_item_f1": 0.0, "grounding": 0.0},
    "line_items_only": {"schema_valid": 0.0, "scalar_f1": 0.0,
                        "line_item_f1": 1.0, "grounding": 0.0},
    "no_grounding": {"schema_valid": 0.05, "scalar_f1": 0.53,
                     "line_item_f1": 0.42, "grounding": 0.0},
    "grounding_heavy": {"schema_valid": 0.05, "scalar_f1": 0.25,
                        "line_item_f1": 0.20, "grounding": 0.50},
}

d = json.load(open(SRC))
R = {k: v["rows"] for k, v in d["runs"].items()}


def reweight(rows, w):
    return [sum((r["components"].get(c) or 0.0) * w[c] for c in COMPONENTS)
            for r in rows]


def by_doc(rows, w):
    """Mean re-weighted reward per document, the unit the bootstrap resamples."""
    g = defaultdict(list)
    for r, v in zip(rows, reweight(rows, w)):
        g[r["doc_index"]].append(v)
    return {k: mean(v) for k, v in g.items()}


def paired_ci(a_rows, b_rows, w):
    """Paired bootstrap over documents, identical to scripts/13."""
    A, Bd = by_doc(a_rows, w), by_doc(b_rows, w)
    keys = sorted(set(A) & set(Bd))
    diffs = [A[k] - Bd[k] for k in keys]
    rng = random.Random(SEED)
    boots = []
    n = len(diffs)
    for _ in range(B):
        boots.append(mean(diffs[rng.randrange(n)] for _ in range(n)))
    boots.sort()
    return mean(diffs), boots[int(0.025 * B)], boots[int(0.975 * B) - 1]


out = {"source": SRC, "git": d.get("git"), "seed": SEED,
       "bootstrap_resamples": B, "schemes": {}}

print(f"source={SRC}  git={d.get('git')}  "
      f"bootstrap={B} paired resamples over documents, seed {SEED}\n")

hdr = (f"{'scheme':<17} " + " ".join(f"{t[:4]+'|'+c[:3]:>9}" for t in TIERS for c in CONDS)
       + "   tier order")
print(hdr); print("-" * len(hdr))
for name, w in SCHEMES.items():
    means = {f"{t}|{c}": mean(reweight(R[f"{t}|{c}"], w)) for t in TIERS for c in CONDS}
    order_ok = all(means[f"frontier|{c}"] > means[f"mid|{c}"] > means[f"small|{c}"]
                   for c in CONDS)
    print(f"{name:<17} " + " ".join(f"{means[f'{t}|{c}']:>9.4f}" for t in TIERS
                                    for c in CONDS)
          + ("   holds" if order_ok else "   BREAKS"))

    deltas, gaps = {}, {}
    for t in TIERS:
        o, lo, hi = paired_ci(R[f"{t}|ocr_text"], R[f"{t}|image"], w)
        deltas[t] = {"delta": o, "ci_low": lo, "ci_high": hi,
                     "spans_zero": lo <= 0 <= hi}
    for c in CONDS:
        for hi_t, lo_t in (("frontier", "mid"), ("mid", "small")):
            o, lo, hi = paired_ci(R[f"{hi_t}|{c}"], R[f"{lo_t}|{c}"], w)
            gaps[f"{hi_t}-{lo_t}|{c}"] = {"gap": o, "ci_low": lo, "ci_high": hi,
                                          "excludes_zero": lo > 0}
    out["schemes"][name] = {"weights": w, "cell_means": means,
                            "tier_order_holds": order_ok,
                            "condition_deltas": deltas, "tier_gaps": gaps}

print("\nCONCLUSION 1: every condition delta spans zero")
for name, s in out["schemes"].items():
    bad = [t for t, v in s["condition_deltas"].items() if not v["spans_zero"]]
    print(f"  {name:<17} {'holds' if not bad else 'BREAKS for ' + ','.join(bad)}"
          + "   " + "  ".join(f"{t}={v['delta']:+.4f}"
                              for t, v in s["condition_deltas"].items()))

print("\nCONCLUSION 2: every tier gap excludes zero")
for name, s in out["schemes"].items():
    bad = [k for k, v in s["tier_gaps"].items() if not v["excludes_zero"]]
    print(f"  {name:<17} {'holds' if not bad else 'BREAKS for ' + ','.join(bad)}")

print("\nMINIMUM DETECTABLE EFFECT on the condition delta")
print("  half-width of the 95% interval, the smallest effect this design "
      "could have called non-zero")
for name, s in out["schemes"].items():
    hw = {t: (v["ci_high"] - v["ci_low"]) / 2 for t, v in s["condition_deltas"].items()}
    out["schemes"][name]["mde"] = hw
    print(f"  {name:<17} " + "  ".join(f"{t}={v:.4f}" for t, v in hw.items()))

Path("results/weight_sensitivity.json").write_text(json.dumps(out, indent=2))
print("\nwrote results/weight_sensitivity.json")
