"""Verify the CORD layer round-trips real data correctly."""
import sys; sys.path.insert(0, "src")
from collections import Counter
from datasets import load_dataset
from doc_extraction_study.cord import parse_ground_truth, ocr_text, SCALAR_FIELDS

ds = load_dataset("naver-clova-ix/cord-v2", split="validation")
cov, n_items, empty_ocr = Counter(), [], 0
for i, row in enumerate(ds):
    r = parse_ground_truth(row["ground_truth"], f"val-{i:03d}")
    for f in SCALAR_FIELDS:
        if getattr(r, f) is not None:
            cov[f] += 1
    n_items.append(len(r.line_items))
    t = ocr_text(row["ground_truth"])
    if not t.strip():
        empty_ocr += 1

print(f"docs: {len(ds)}  |  docs with empty OCR: {empty_ocr}")
print(f"line items per doc: min={min(n_items)} max={max(n_items)} mean={sum(n_items)/len(n_items):.1f}")
print("\nscalar field coverage in ground truth:")
for f in SCALAR_FIELDS:
    print(f"  {f:<16} {cov[f]:>3}/100")

r0 = parse_ground_truth(ds[0]["ground_truth"], "val-000")
print(f"\n--- canonical doc 0 ---\n{r0.to_dict()}")
print(f"\n--- reconstructed OCR text, doc 0 ---\n{ocr_text(ds[0]['ground_truth'])}")
