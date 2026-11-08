"""Inspect CORD v2 ground truth to design the extraction schema.

Downloads only the validation split (the dev set). The test split stays
untouched until the pre-registered run.
"""
import json
from collections import Counter
from datasets import load_dataset

ds = load_dataset("naver-clova-ix/cord-v2", split="validation")
print(f"validation rows: {len(ds)}")
print(f"columns: {ds.column_names}")

gt = json.loads(ds[0]["ground_truth"])
print(f"\ntop-level ground_truth keys: {sorted(gt)}")
print(f"meta: {json.dumps(gt.get('meta', {}))}")

img = ds[0]["image"]
print(f"image: {type(img).__name__} size={img.size} mode={img.mode}")

# Which gt_parse sections and leaf keys actually occur, and how often
sections, leaves, menu_keys = Counter(), Counter(), Counter()
for row in ds:
    g = json.loads(row["ground_truth"])
    p = g.get("gt_parse", {})
    for sec, val in p.items():
        sections[sec] += 1
        if isinstance(val, dict):
            for k in val:
                leaves[f"{sec}.{k}"] += 1
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, dict):
                    for k in item:
                        menu_keys[f"{sec}.{k}"] += 1

print(f"\ngt_parse sections across {len(ds)} docs:")
for s, c in sections.most_common():
    print(f"  {s:<14} {c:>4} docs ({100*c/len(ds):.0f}%)")
print("\nleaf keys in dict sections:")
for k, c in leaves.most_common():
    print(f"  {k:<28} {c:>4} ({100*c/len(ds):.0f}%)")
print("\nkeys inside list sections (line items):")
for k, c in menu_keys.most_common():
    print(f"  {k:<28} {c:>4} occurrences")

print("\n--- full gt_parse of doc 0 ---")
print(json.dumps(gt["gt_parse"], indent=2, ensure_ascii=False)[:1800])

print("\n--- OCR: valid_line structure of doc 0 (first 2 lines) ---")
for line in gt.get("valid_line", [])[:2]:
    print(f"  category={line.get('category')} group_id={line.get('group_id')}")
    for w in line.get("words", [])[:4]:
        print(f"    text={w.get('text')!r} is_key={w.get('is_key')} row_id={w.get('row_id')}")
