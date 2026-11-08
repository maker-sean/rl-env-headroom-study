"""Failure taxonomy with counts and real examples. No model calls.

Phase 3 requires 2 to 3 concrete examples per failure category, not just
counts. Examples are drawn from distinct documents (one per document per
category) so a single pathological receipt cannot supply all of them.

Usage: uv run python scripts/14_failure_examples.py
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, "src")
from datasets import load_dataset
from doc_extraction_study.cord import ocr_text, parse_ground_truth
from doc_extraction_study.normalize import ocr_text_digits
from doc_extraction_study.scoring import parse_prediction, score

CELLS = [
    ("small", "ocr_text", "full-test-ocr_text-qwen3.5-9b"),
    ("small", "image", "full-test-image-qwen3.5-9b"),
    ("mid", "ocr_text", "full-test-ocr_text-qwen3-vl-30b-a3b-instruct"),
    ("mid", "image", "full-test-image-qwen3-vl-30b-a3b-instruct"),
    ("frontier", "ocr_text", "full-test-ocr_text-claude-opus-5.5"),
    ("frontier", "image", "full-test-image-claude-opus-5.5"),
]
PER_CATEGORY = 3

ds = load_dataset("naver-clova-ix/cord-v2", split="test")
truth, digits = {}, {}
for i, row in enumerate(ds):
    did = f"test-{i:03d}"
    truth[did] = parse_ground_truth(row["ground_truth"], did)
    digits[did] = ocr_text_digits(ocr_text(row["ground_truth"]))


def reply_of(tr):
    for n in reversed(tr.get("nodes") or []):
        m = n.get("message") or n
        if m.get("role") == "assistant" and m.get("content"):
            return m["content"]
    return None


def magnitude_ratio(a, b):
    """The power of ten the prediction dropped, if any.

    Indonesian receipts write 60.000 for sixty thousand. A model that reads the
    separator as a decimal point emits the JSON number 60.0, losing a factor of
    1000. A truncated-cents variant loses 10 or 100 instead (82.000 -> 8200).
    """
    if not a or not b:
        return None
    r = a / b
    for scale in (1000, 100, 10):
        if abs(r - scale) < scale * 0.06:
            return scale
    return None


counts = defaultdict(lambda: defaultdict(int))
examples = defaultdict(lambda: defaultdict(dict))   # cat -> cell -> doc -> example

for tier, cond, dname in CELLS:
    cell = f"{tier}|{cond}"
    for line in (Path("outputs") / dname / "traces.jsonl").read_text().splitlines():
        if not line.strip():
            continue
        ep = json.loads(line)
        data = (ep.get("task") or {}).get("data") or {}
        tr = (ep.get("traces") or [{}])[0]
        did = json.loads(data["truth_json"])["doc_id"]
        t = truth[did]
        reply = reply_of(tr)
        res = score(reply, t, digits[did])
        pred = parse_prediction(reply, did).receipt
        ts = t.scalars()
        ps = pred.scalars() if pred else {}

        def note(cat, payload):
            counts[cat][cell] += 1
            if did not in examples[cat][cell] and len(examples[cat][cell]) < PER_CATEGORY:
                examples[cat][cell][did] = {"doc": did, **payload}

        # 1. magnitude: thousands separator read as a decimal point
        hit = None
        for f in ("total", "subtotal", "tax", "discount", "service_charge"):
            sc = magnitude_ratio(ts.get(f), ps.get(f)) if f in ts and f in ps else None
            if sc:
                hit = (f, ts[f], ps[f], sc)
                break
        if hit is None and pred:
            for ti, pi in zip(t.line_items, pred.line_items):
                sc = magnitude_ratio(ti.price, pi.price)
                if sc:
                    hit = ("line_item_price", ti.price, pi.price, sc)
                    break
        if hit:
            note(f"magnitude_{hit[3]}x",
                 {"field": hit[0], "truth": hit[1], "pred": hit[2]})

        # 2. invented subtotal on a receipt that prints only a total
        if (res.metrics.get("scalar_detail") or {}).get("invented_subtotal"):
            note("invented_subtotal", {"truth_scalars": ts, "pred_scalars": ps})

        # 3. missed tax
        if (res.metrics.get("scalar_detail") or {}).get("missed_tax"):
            note("missed_tax", {"truth_scalars": ts, "pred_scalars": ps})

        # 4. item name not matched
        if pred:
            tn = [i.name for i in t.line_items]
            pn = [i.name for i in pred.line_items]
            ld = res.metrics.get("line_item_detail") or {}
            if ld.get("fn") and set(tn) != set(pn):
                note("item_name_mismatch", {"truth_names": tn[:5], "pred_names": pn[:5]})

            # 5. over-extraction: more line items claimed than the receipt has
            if len(pred.line_items) >= len(t.line_items) + 3:
                note("item_over_extraction",
                     {"n_true": len(t.line_items), "n_pred": len(pred.line_items),
                      "truth_names": tn[:5], "pred_names": pn[:8]})

            # 6. price wrong on an item whose name matched
            if ld.get("price_wrong_on_matched"):
                note("price_wrong_on_matched",
                     {"truth_items": [(i.name, i.price) for i in t.line_items][:4],
                      "pred_items": [(i.name, i.price) for i in pred.line_items][:4]})

        # 7. unparseable reply
        if res.metrics.get("format_tier") == "invalid":
            note("unparseable", {"reply_head": (reply or "")[:160]})

ORDER = [f"{t}|{c}" for t, c, _ in CELLS]
print("FAILURE TAXONOMY: rollouts out of 1000 per cell\n")
print(f"{'category':<24}" + "".join(f"{c.replace('|', ' '):>22}" for c in ORDER))
print("-" * (24 + 22 * len(ORDER)))
CATS = ("magnitude_1000x", "magnitude_100x", "magnitude_10x",
        "invented_subtotal", "missed_tax", "item_name_mismatch",
        "item_over_extraction", "price_wrong_on_matched", "unparseable")
for cat in CATS:
    print(f"{cat:<24}" + "".join(f"{counts[cat][c]:>22}" for c in ORDER))

print("\n\nREAL EXAMPLES (distinct documents)\n")
for cat in CATS:
    print(f"--- {cat} " + "-" * (70 - len(cat)))
    shown = 0
    for cell in ORDER:
        for did, ex in examples[cat][cell].items():
            if shown >= PER_CATEGORY:
                break
            print(f"  [{cell}] {json.dumps(ex, ensure_ascii=False)}")
            shown += 1
        if shown >= PER_CATEGORY:
            break
    if not shown:
        print("  none observed")
    print()

Path("results/failure_taxonomy.json").write_text(json.dumps(
    {"counts": {k: dict(v) for k, v in counts.items()},
     "examples": {k: {c: list(v.values()) for c, v in cells.items()}
                  for k, cells in examples.items()}}, indent=2, ensure_ascii=False))
print("wrote results/failure_taxonomy.json")
