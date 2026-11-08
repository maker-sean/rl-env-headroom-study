"""Measure CORD v2 ground-truth properties that determine verifier design.

Three questions:
 1. How polymorphic is the schema (dict vs list sections)?
 2. What amount string formats occur, so normalization covers them?
 3. Does the ground truth itself satisfy the arithmetic consistency checks?
    If it does not, those checks cannot be scored as rewards.
"""
import json, re
from collections import Counter
from datasets import load_dataset

ds = load_dataset("naver-clova-ix/cord-v2", split="validation")

def as_list(v):
    if v is None: return []
    return v if isinstance(v, list) else [v]

AMOUNT_RE = re.compile(r"[^0-9.,\-]")
def parse_amount(s):
    """Indonesian receipts: ',' and '.' are both thousands separators."""
    if s is None: return None
    t = AMOUNT_RE.sub("", str(s)).strip().strip(".,-")
    if not t: return None
    t = t.replace(",", "").replace(".", "")
    try: return int(t)
    except ValueError: return None

shape = Counter(); amount_fmt = Counter(); cnt_fmt = Counter()
checks = Counter()
examples = {"items_vs_total": [], "subtotal_chain": []}

for i, row in enumerate(ds):
    p = json.loads(row["ground_truth"])["gt_parse"]
    shape["menu:" + ("list" if isinstance(p.get("menu"), list) else "dict")] += 1
    for sec in ("total", "sub_total"):
        if sec in p:
            shape[f"{sec}:" + ("list" if isinstance(p[sec], list) else "dict")] += 1

    items = as_list(p.get("menu"))
    for it in items:
        if not isinstance(it, dict): continue
        if "price" in it: amount_fmt[re.sub(r"\d", "#", str(it["price"]))] += 1
        if "cnt" in it:   cnt_fmt[re.sub(r"\d", "#", str(it["cnt"]))] += 1

    tot = p.get("total") or {}
    sub = p.get("sub_total") or {}
    tot = tot if isinstance(tot, dict) else {}
    sub = sub if isinstance(sub, dict) else {}

    total   = parse_amount(tot.get("total_price"))
    subtot  = parse_amount(sub.get("subtotal_price"))
    tax     = parse_amount(sub.get("tax_price"))
    service = parse_amount(sub.get("service_price"))
    disc    = parse_amount(sub.get("discount_price"))

    prices = [parse_amount(it.get("price")) for it in items if isinstance(it, dict)]
    prices = [x for x in prices if x is not None]
    item_sum = sum(prices) if prices else None

    # Check A: do line item prices sum to subtotal, or to total when no subtotal?
    target = subtot if subtot is not None else total
    if item_sum is not None and target is not None:
        checks["A_evaluable"] += 1
        if item_sum == target:
            checks["A_exact"] += 1
        else:
            if len(examples["items_vs_total"]) < 4:
                examples["items_vs_total"].append(
                    (i, prices, item_sum, {"subtotal": subtot, "total": total}))

    # Check B: subtotal + tax + service - discount == total
    if subtot is not None and total is not None:
        chain = subtot + (tax or 0) + (service or 0) - (disc or 0)
        checks["B_evaluable"] += 1
        if chain == total:
            checks["B_exact"] += 1
        elif len(examples["subtotal_chain"]) < 4:
            examples["subtotal_chain"].append(
                (i, {"subtotal": subtot, "tax": tax, "service": service,
                     "discount": disc, "computed": chain, "total": total}))

print("=== schema shape ==="); [print(f"  {k:<16} {v}") for k, v in shape.most_common()]
print("\n=== price string formats (# = digit) ===")
[print(f"  {k!r:<14} {v}") for k, v in amount_fmt.most_common(10)]
print("\n=== quantity string formats ===")
[print(f"  {k!r:<14} {v}") for k, v in cnt_fmt.most_common(10)]

print("\n=== GROUND-TRUTH arithmetic consistency ===")
a_e, a_x = checks["A_evaluable"], checks["A_exact"]
b_e, b_x = checks["B_evaluable"], checks["B_exact"]
print(f"  A: sum(line item prices) == subtotal-or-total")
print(f"     evaluable on {a_e}/100 docs, holds on {a_x} ({100*a_x/a_e:.0f}% of evaluable)")
print(f"  B: subtotal + tax + service - discount == total")
print(f"     evaluable on {b_e}/100 docs, holds on {b_x} ({100*b_x/b_e:.0f}% of evaluable)")

print("\n--- check A counterexamples ---")
for i, pr, s, t in examples["items_vs_total"]:
    print(f"  doc {i}: prices={pr} sum={s} vs {t}")
print("--- check B counterexamples ---")
for i, d in examples["subtotal_chain"]:
    print(f"  doc {i}: {d}")
