"""Verifier self-test on real CORD data. Must pass before any model run.

Three gates, from CLAUDE.md:
  1. Ground truth scores 100%.
  2. Deliberately corrupted outputs score low.
  3. Degenerate strategies that try to game the verifier earn only a small,
     documented floor.

Writes results/verifier_selftest.json so every figure quoted elsewhere traces
back to a run of this script.
"""
import json, random, subprocess, sys
from pathlib import Path
from statistics import mean

sys.path.insert(0, "src")
from datasets import load_dataset

from doc_extraction_study.cord import SCALAR_FIELDS, ocr_text, parse_ground_truth
from doc_extraction_study.normalize import ocr_text_digits
from doc_extraction_study.scoring import REWARD_WEIGHTS, score

SEED = 20261105
random.seed(SEED)


def serialize(r, **overrides):
    obj = {"line_items": [{"name": i.name, "quantity": i.quantity,
                           "unit_price": i.unit_price, "price": i.price}
                          for i in r.line_items]}
    for f in SCALAR_FIELDS:
        if getattr(r, f) is not None:
            obj[f] = getattr(r, f)
    obj.update(overrides)
    return json.dumps(obj)


# ---- corruptions. Each takes the truth and returns a model reply string. ----

def c_perfect(r, ocr):
    return serialize(r)

def c_digit_shift(r, ocr):
    o = json.loads(serialize(r))
    for f in SCALAR_FIELDS:
        if f in o and isinstance(o[f], int):
            o[f] = o[f] + 100
    for it in o["line_items"]:
        if isinstance(it.get("price"), int):
            it["price"] += 100
    return json.dumps(o)

def c_swap_fields(r, ocr):
    o = json.loads(serialize(r))
    if "subtotal" in o and "total" in o:
        o["subtotal"], o["total"] = o["total"], o["subtotal"]
    elif "total" in o:
        o["tax"] = o.pop("total")
    return json.dumps(o)

def c_invent_fields(r, ocr):
    o = json.loads(serialize(r))
    for f in SCALAR_FIELDS:
        o.setdefault(f, 12345)
    return json.dumps(o)

def c_drop_items(r, ocr):
    o = json.loads(serialize(r))
    o["line_items"] = o["line_items"][:1]
    return json.dumps(o)

def c_zero_everything(r, ocr):
    o = json.loads(serialize(r))
    for f in SCALAR_FIELDS:
        if f in o:
            o[f] = 0
    for it in o["line_items"]:
        it["price"] = 0
    return json.dumps(o)

def c_broken_json(r, ocr):
    return serialize(r)[:-3]

def c_prose_only(r, ocr):
    return "The receipt shows several items and a total. I could not parse it precisely."

# ---- gaming strategies ----

def g_valid_empty(r, ocr):
    return '{"line_items": []}'

def g_all_nulls(r, ocr):
    return json.dumps({"line_items": [], **{f: None for f in SCALAR_FIELDS}})

def g_digit_spam(r, ocr):
    return json.dumps({"line_items": [{"name": f"ITEM{i}", "price": int(v)}
                                      for i, v in enumerate(sorted(ocr))]})

def g_copy_total_everywhere(r, ocr):
    t = r.total if r.total is not None else 0
    return json.dumps({"line_items": [{"name": "X", "price": t}],
                       **{f: t for f in SCALAR_FIELDS}})


CORRUPTIONS = {
    "ground_truth": c_perfect, "digit_shift_+100": c_digit_shift,
    "swapped_fields": c_swap_fields, "invented_all_fields": c_invent_fields,
    "dropped_line_items": c_drop_items, "zeroed_all_amounts": c_zero_everything,
    "truncated_json": c_broken_json, "prose_no_json": c_prose_only,
}
# Degenerate strategies that produce no real extraction. These must stay at a
# small, documented floor.
GAMING = {
    "valid_but_empty": g_valid_empty, "all_nulls": g_all_nulls,
    "digit_spam": g_digit_spam,
}
# NOT a hack: this one genuinely reads the total correctly and shotguns the
# rest. It is the score a model earns for reading only the biggest number on
# the page, so it belongs in the results as a reference line. Any model whose
# score is near this baseline has demonstrated little beyond finding the total.
BASELINES = {
    "read_total_only": g_copy_total_everywhere,
}


def git_rev():
    try:
        rev = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain"],
                               capture_output=True, text=True).stdout.strip()
        return f"{rev}{'-dirty' if dirty else ''}"
    except Exception:
        return "unknown"


def main():
    ds = load_dataset("naver-clova-ix/cord-v2", split="validation")
    docs = []
    for i, row in enumerate(ds):
        truth = parse_ground_truth(row["ground_truth"], f"val-{i:03d}")
        docs.append((truth, ocr_text_digits(ocr_text(row["ground_truth"]))))

    out = {"seed": SEED, "git": git_rev(), "n_docs": len(docs),
           "weights": REWARD_WEIGHTS, "split": "cord-v2/validation",
           "corruptions": {}, "gaming": {}, "baselines": {}}

    for label, fn in {**CORRUPTIONS, **GAMING, **BASELINES}.items():
        totals, comps = [], {k: [] for k in REWARD_WEIGHTS}
        skipped = 0
        for truth, ocr in docs:
            reply = fn(truth, ocr)
            # A corruption that leaves the perfect output unchanged is not
            # applicable to this document and must not be scored as a
            # corruption. Dropping to one line item is a no-op on the 46% of
            # CORD receipts with a single item; swapping fields is a no-op when
            # only one scalar is present.
            if label in CORRUPTIONS and label != "ground_truth" \
                    and reply == c_perfect(truth, ocr):
                skipped += 1
                continue
            res = score(reply, truth, ocr)
            totals.append(res.total)
            for k, v in res.rewards.items():
                comps[k].append(v)
        if not totals:
            rec = {"n_applicable": 0, "note": "not applicable to any document"}
        else:
            rec = {"n_applicable": len(totals), "n_not_applicable": skipped,
                   "mean": round(mean(totals), 4),
                   "min": round(min(totals), 4), "max": round(max(totals), 4),
                   "components": {k: round(mean(v), 4) for k, v in comps.items()}}
        bucket = ("gaming" if label in GAMING
                  else "baselines" if label in BASELINES else "corruptions")
        out[bucket][label] = rec

    Path("results").mkdir(exist_ok=True)
    Path("results/verifier_selftest.json").write_text(json.dumps(out, indent=2))

    # GATE 1 runs on EVERY split, not only the dev split.
    #
    # Corruption and gaming gates only need documents; the gold check needs
    # the documents a claim is made on. Two CORD `test` documents carried
    # list-valued annotation fields that `validation` happens not to contain
    # (`provenance/cord_duplicate_fields.json`), so a gold check confined to
    # the dev split could not have found the parser bug they exposed, and one
    # of the two was silent even then: the fused value coincidentally matched
    # another number on the same receipt, so it looked grounded.
    gold = {}
    for sp in ("validation", "test"):
        sc = []
        for i, row in enumerate(load_dataset("naver-clova-ix/cord-v2", split=sp)):
            t = parse_ground_truth(row["ground_truth"], f"{sp}-{i:03d}")
            r = score(t.to_model_json(), t,
                      ocr_text_digits(ocr_text(row["ground_truth"])))
            sc.append(round(r.total, 6))
        gold[sp] = {"n": len(sc), "min": min(sc), "max": max(sc),
                    "mean": round(mean(sc), 6),
                    "below_1": [f"{sp}-{i:03d}" for i, v in enumerate(sc) if v < 1.0]}
    out["gold_by_split"] = gold
    Path("results/verifier_selftest.json").write_text(json.dumps(out, indent=2))

    gt = out["corruptions"]["ground_truth"]
    print(f"git={out['git']}  seed={SEED}  docs={out['n_docs']}  "
          f"split={out['split']}\n")
    print("GATE 1: ground truth must score 1.0 on every document, EVERY split")
    gate1 = True
    for sp, g in gold.items():
        ok = g["min"] == 1.0 and g["max"] == 1.0
        gate1 = gate1 and ok
        print(f"  {sp:<11} n={g['n']:>3}  mean={g['mean']}  min={g['min']}  "
              f"max={g['max']}  {'ok' if ok else 'FAIL ' + str(g['below_1'])}")
    print(f"  -> {'PASS' if gate1 else 'FAIL'}\n")

    print("GATE 2: every applicable corruption must score below ground truth")
    print(f"  {'corruption':<24} {'n':>4} {'mean':>7} {'min':>7} {'max':>7}")
    gate2 = True
    for k, v in out["corruptions"].items():
        if k == "ground_truth":
            continue
        if not v.get("n_applicable"):
            print(f"  {k:<24} {'0':>4}  not applicable to any document")
            continue
        ok = v["max"] < 1.0
        gate2 &= ok
        print(f"  {k:<24} {v['n_applicable']:>4} {v['mean']:>7.3f} "
              f"{v['min']:>7.3f} {v['max']:>7.3f}  {'ok' if ok else 'TOO HIGH'}")
    print(f"  -> {'PASS' if gate2 else 'FAIL'}\n")

    print("GATE 3: degenerate strategies earn only a small documented floor")
    print(f"  {'strategy':<24} {'mean':>7} {'max':>7}")
    gate3 = True
    for k, v in out["gaming"].items():
        ok = v["max"] <= 0.25
        gate3 &= ok
        print(f"  {k:<24} {v['mean']:>7.3f} {v['max']:>7.3f}  {'ok' if ok else 'TOO HIGH'}")
    print(f"  -> {'PASS' if gate3 else 'FAIL'}\n")

    print("REFERENCE BASELINE (not a gate): the score for reading only the total")
    for k, v in out["baselines"].items():
        print(f"  {k:<24} mean={v['mean']:.3f}  min={v['min']:.3f}  max={v['max']:.3f}")
        print(f"  {'':<24} components={v['components']}")
    print("  Any model scoring near this has shown little beyond finding the total.")

    print("\nwrote results/verifier_selftest.json")
    return 0 if (gate1 and gate2 and gate3) else 1


if __name__ == "__main__":
    sys.exit(main())
