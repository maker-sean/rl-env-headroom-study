"""Score the D7 prompt variant against the predictions committed before it ran.

The variant run was scored live by the taskset at a commit that already
contained both parser fixes, so its rewards are directly comparable to
`results/full_test_fixed.json`, which is the same 6,000 rollouts re-scored with
those fixes. No re-scoring is applied here.

Uncertainty is the paired bootstrap over documents used everywhere else in this
study: 10,000 resamples, seed 20261106, the same 100 test documents in both
cells.

Usage: uv run python scripts/18_score_d7.py
Writes results/d7_scorecard.json
"""
import json, random, sys
from collections import defaultdict
from pathlib import Path
from statistics import mean

BASE_SRC = "results/full_test_fixed.json"
VAR_SRC = "results/promptfix_test.json"
CELL = "mid|ocr_text"
SEED, B = 20261106, 10000

base = json.load(open(BASE_SRC))
var = json.load(open(VAR_SRC))
b_rows = base["runs"][CELL]["rows"]
v_rows = var["runs"][CELL]["rows"]


def by_doc(rows, key):
    g = defaultdict(list)
    for r in rows:
        g[r["doc_index"]].append(key(r))
    return {k: mean(v) for k, v in g.items()}


def paired(a_rows, b_rows, key=lambda r: r["reward"]):
    A, Bd = by_doc(a_rows, key), by_doc(b_rows, key)
    keys = sorted(set(A) & set(Bd))
    diffs = [A[k] - Bd[k] for k in keys]
    rng = random.Random(SEED)
    n = len(diffs)
    boots = sorted(mean(diffs[rng.randrange(n)] for _ in range(n)) for _ in range(B))
    return mean(diffs), boots[int(0.025 * B)], boots[int(0.975 * B) - 1]


def count(rows, metric):
    return sum(1 for r in rows if (r["metrics"].get(metric) or 0) == 1.0)


def em(rows):
    return mean((r["metrics"].get("doc_exact_match") or 0.0) for r in rows)


b_mean, v_mean = mean(r["reward"] for r in b_rows), mean(r["reward"] for r in v_rows)
gain, lo, hi = paired(v_rows, b_rows)
em_gain, em_lo, em_hi = paired(v_rows, b_rows,
                               key=lambda r: r["metrics"].get("doc_exact_match") or 0.0)

print(f"base git={base.get('git')}  variant git={var.get('git')}  "
      f"prompt={var.get('prompt_variant')}")
print(f"cell={CELL}  n_base={len(b_rows)}  n_variant={len(v_rows)}  "
      f"bootstrap={B} paired over documents, seed {SEED}\n")

print(f"{'quantity':<26} {'baseline':>10} {'variant':>10} {'change':>10}")
print("-" * 60)
rows_out = {}
for label, fn in (("mean reward", lambda rs: mean(r["reward"] for r in rs)),
                  ("scalar F1", lambda rs: mean(r["components"]["scalar_f1"] for r in rs)),
                  ("line-item F1", lambda rs: mean(r["components"]["line_item_f1"] for r in rs)),
                  ("grounding", lambda rs: mean(r["components"]["grounding"] for r in rs)),
                  ("doc exact match", em)):
    bv, vv = fn(b_rows), fn(v_rows)
    rows_out[label] = {"baseline": bv, "variant": vv, "change": vv - bv}
    print(f"{label:<26} {bv:>10.4f} {vv:>10.4f} {vv - bv:>+10.4f}")
for m in ("invented_subtotal", "missed_subtotal", "wrong_subtotal",
          "invented_total", "missed_tax"):
    bc, vc = count(b_rows, m), count(v_rows, m)
    rows_out[m] = {"baseline": bc, "variant": vc, "change": vc - bc}
    print(f"{m + ' /1000':<26} {bc:>10} {vc:>10} {vc - bc:>+10}")

print(f"\nmean reward gain {gain:+.4f}  95% CI [{lo:+.4f},{hi:+.4f}]"
      f"  {'spans zero' if lo <= 0 <= hi else 'excludes zero'}")
print(f"exact match gain {em_gain:+.4f}  95% CI [{em_lo:+.4f},{em_hi:+.4f}]"
      f"  {'spans zero' if em_lo <= 0 <= em_hi else 'excludes zero'}")

# ---- the four predictions, as written in PREREGISTRATION.md D7 -------------
inv_b, inv_v = count(b_rows, "invented_subtotal"), count(v_rows, "invented_subtotal")
mis_v = count(v_rows, "missed_subtotal")
em_v = em(v_rows)
preds = {
    "D7-A": ("gain of +0.0150 to +0.0379", 0.0150 <= gain <= 0.0379,
             f"measured {gain:+.4f} [{lo:+.4f},{hi:+.4f}], ablation bound +0.0379"),
    "D7-B": ("invented_subtotal below 100/1000", inv_v < 100,
             f"{inv_b} -> {inv_v} of 1,000 rollouts"),
    "D7-C": ("missed_subtotal rises above 0 but stays at or below 40/1000",
             0 < mis_v <= 40, f"{mis_v} of 1,000 rollouts"),
    "D7-D": ("exact match 0.380 to 0.420", 0.380 <= em_v <= 0.420,
             f"measured {em_v:.3f}"),
}
print("\nPREDICTIONS")
for pid, (text, ok, detail) in preds.items():
    print(f"  {pid}  {'HIT ' if ok else 'MISS'}  {text}\n        {detail}")

if gain < 0.010:
    rule = ("1: the ablation overestimated what a prompt can recover. The "
            "specification framing is reported as partly wrong and the headroom "
            "numbers lose their claim to be reachable.")
elif gain >= 0.030:
    rule = ("2: the specification diagnosis is confirmed. The headroom table is "
            "reported as reachable, not merely an upper bound.")
else:
    rule = ("3: partial. A specification gap a prompt closes only in part; the "
            "residue is named.")
if lo <= 0 <= hi:
    rule += " The interval spans zero and is reported as spanning zero."
print(f"\nDECISION RULE {rule}")

Path("results/d7_scorecard.json").write_text(json.dumps(
    {"base_source": BASE_SRC, "variant_source": VAR_SRC,
     "base_git": base.get("git"), "variant_git": var.get("git"),
     "prompt_variant": var.get("prompt_variant"), "cell": CELL,
     "seed": SEED, "bootstrap_resamples": B,
     "measured_cost_usd": var.get("measured_total_usd"),
     "quantities": rows_out,
     "reward_gain": {"gain": gain, "ci_low": lo, "ci_high": hi},
     "exact_match_gain": {"gain": em_gain, "ci_low": em_lo, "ci_high": em_hi},
     "predictions": {k: {"text": t, "hit": ok, "detail": dd}
                     for k, (t, ok, dd) in preds.items()},
     "decision_rule": rule}, indent=2))
print("\nwrote results/d7_scorecard.json")
