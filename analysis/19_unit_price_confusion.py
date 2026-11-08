"""Do models report the unit price where the schema asks for the line total?

Prompted by the hand audit: on `test-082` the receipt prints
`Strawberry Log Cake 2x 105,000 210,000`, and the schema says `price` is the
amount charged for the line after quantity (210,000) while `unit_price` is the
per-unit amount (105,000). A reviewer looking only at name and price could not
tell those apart, which is what the audit page hid and this script measures.

`line_item_f1` scores name and price only, so reporting the unit price as the
price is already counted as a wrong price. This breaks that bucket apart: how
much of `price_wrong_on_matched` is this one confusion rather than a misread
number? No model calls; all 6,000 saved rollouts are re-matched offline.

Usage: uv run python scripts/19_unit_price_confusion.py
Writes results/unit_price_confusion.json
"""
import json, sys
from pathlib import Path

sys.path.insert(0, "src")
from datasets import load_dataset
from doc_extraction_study.cord import parse_ground_truth
from doc_extraction_study.scoring import _match_items, parse_prediction

CELLS = [
    ("small", "ocr_text", "full-test-ocr_text-qwen3.5-9b"),
    ("small", "image", "full-test-image-qwen3.5-9b"),
    ("mid", "ocr_text", "full-test-ocr_text-qwen3-vl-30b-a3b-instruct"),
    ("mid", "image", "full-test-image-qwen3-vl-30b-a3b-instruct"),
    ("frontier", "ocr_text", "full-test-ocr_text-claude-opus-5.5"),
    ("frontier", "image", "full-test-image-claude-opus-5.5"),
]

def reply_of(tr):
    """The assistant's last message. Traces have no `last_reply` field; an
    earlier version of this script read one and silently scored every rollout
    as unparseable, printing a clean table of zeros."""
    for n in reversed(tr.get("nodes") or []):
        m = n.get("message") or n
        if m.get("role") == "assistant" and m.get("content"):
            return m["content"]
    return None


ds = load_dataset("naver-clova-ix/cord-v2", split="test")
truth = {}
for i, row in enumerate(ds):
    truth[f"test-{i:03d}"] = parse_ground_truth(row["ground_truth"], f"test-{i:03d}")

# How often is the distinction even observable? Only on a line whose quantity
# exceeds one AND whose unit price differs from its line total.
amb_items, amb_docs = 0, set()
for did, t in truth.items():
    for it in t.line_items:
        if (it.quantity or 0) > 1 and it.unit_price is not None \
                and it.price is not None and it.unit_price != it.price:
            amb_items += 1
            amb_docs.add(did)
print(f"documents where the distinction is observable: {len(amb_docs)}/100")
print(f"line items where it is observable: {amb_items}\n")

out = {"observable_docs": sorted(amb_docs), "observable_items": amb_items,
       "cells": {}}

hdr = (f"{'cell':<20} {'price_wrong':>12} {'=unit_price':>12} {'share':>7} "
       f"{'opportunities':>14}")
print(hdr); print("-" * len(hdr))
for tier, cond, dirname in CELLS:
    f = Path("outputs") / dirname / "traces.jsonl"
    wrong = unit_conf = opp = 0
    examples = []
    for line in f.read_text().splitlines():
        if not line.strip():
            continue
        ep = json.loads(line)
        did = (ep.get("task") or {}).get("data", {}).get("id", "")
        did = "test-" + did.split("-")[-1]
        tr = (ep.get("traces") or [{}])[0]
        pred = parse_prediction(reply_of(tr) or "", did)
        if not pred.valid:
            continue
        t = truth[did]
        pairs, _, _ = _match_items(pred.receipt.line_items, t.line_items, False)
        for p, tt in pairs:
            observable = ((tt.quantity or 0) > 1 and tt.unit_price is not None
                          and tt.price is not None and tt.unit_price != tt.price)
            if observable:
                opp += 1
            if p.price == tt.price:
                continue
            wrong += 1
            if observable and p.price == tt.unit_price:
                unit_conf += 1
                if len(examples) < 3 and did not in [e["doc"] for e in examples]:
                    examples.append({"doc": did, "item": tt.name,
                                     "truth_price": tt.price,
                                     "truth_unit_price": tt.unit_price,
                                     "pred_price": p.price,
                                     "qty": tt.quantity})
    assert wrong > 0 or tier == "frontier", (
        f"{tier}|{cond}: zero wrong prices contradicts the failure taxonomy; "
        "the replies are not being parsed")
    share = unit_conf / wrong if wrong else 0.0
    out["cells"][f"{tier}|{cond}"] = {
        "price_wrong_on_matched": wrong, "price_equals_unit_price": unit_conf,
        "share_of_price_wrong": share, "opportunities": opp,
        "rate_per_opportunity": (unit_conf / opp) if opp else None,
        "examples": examples,
    }
    print(f"{tier + '|' + cond:<20} {wrong:>12} {unit_conf:>12} "
          f"{share:>6.1%} {opp:>14}")

Path("results/unit_price_confusion.json").write_text(json.dumps(out, indent=2))
print("\nwrote results/unit_price_confusion.json")
