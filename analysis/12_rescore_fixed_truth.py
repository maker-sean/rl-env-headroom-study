"""Re-score the claim run against re-parsed ground truth. No model calls.

Each trace stores the ground truth as it was parsed at run time, so a fix to
the CORD parser cannot be measured by re-scoring the stored truth: it has to
be rebuilt from the dataset. Four `test` documents had ground truth that the old parser got wrong: two
carried list-valued annotation fields it fused into a single number
(`provenance/cord_duplicate_fields.json`), and two carried a thousands
separator together with cents, which it read 100x too large. On all four, a
model emitting the correct value was scored wrong.

Usage: uv run python scripts/12_rescore_fixed_truth.py
"""
import json
import sys
from pathlib import Path
from statistics import mean

sys.path.insert(0, "src")
from datasets import load_dataset
from doc_extraction_study.cord import LineItem, Receipt, ocr_text, parse_ground_truth
from doc_extraction_study.normalize import ocr_text_digits
from doc_extraction_study.scoring import flat_metrics, score

CELLS = [
    ("small", "ocr_text", "full-test-ocr_text-qwen3.5-9b"),
    ("small", "image", "full-test-image-qwen3.5-9b"),
    ("mid", "ocr_text", "full-test-ocr_text-qwen3-vl-30b-a3b-instruct"),
    ("mid", "image", "full-test-image-qwen3-vl-30b-a3b-instruct"),
    ("frontier", "ocr_text", "full-test-ocr_text-claude-opus-5.5"),
    ("frontier", "image", "full-test-image-claude-opus-5.5"),
]
# Documents whose ground truth was wrong before the parser fixes.
#   test-013, test-099: list-valued CORD annotation fields fused (deviation D5)
#   test-047, test-067: a thousands separator plus cents, parsed 100x too large
#                       ("63,000.00" -> 6300000, "9.500,00" -> 950000) (D6)
AFFECTED = {"test-013", "test-099", "test-047", "test-067"}


def stored_truth(blob):
    d = json.loads(blob)
    return Receipt(doc_id=d["doc_id"],
                   line_items=[LineItem(**i) for i in d.get("line_items", [])],
                   subtotal=d.get("subtotal"), tax=d.get("tax"),
                   service_charge=d.get("service_charge"),
                   discount=d.get("discount"), total=d.get("total"))


def reply_of(tr):
    for n in reversed(tr.get("nodes") or []):
        m = n.get("message") or n
        if m.get("role") == "assistant" and m.get("content"):
            return m["content"]
    return None


ds = load_dataset("naver-clova-ix/cord-v2", split="test")
fixed, digits = {}, {}
for i, row in enumerate(ds):
    did = f"test-{i:03d}"
    fixed[did] = parse_ground_truth(row["ground_truth"], did)
    digits[did] = ocr_text_digits(ocr_text(row["ground_truth"]))

print(f"{'cell':<22}{'old':>9}{'new':>9}{'delta':>9}{'exact_old':>11}{'exact_new':>11}")
print("-" * 71)
out = {}
for tier, cond, d in CELLS:
    f = Path("outputs") / d / "traces.jsonl"
    old_t, new_t, old_e, new_e = [], [], [], []
    aff_old, aff_new = [], []
    for line in f.read_text().splitlines():
        if not line.strip():
            continue
        ep = json.loads(line)
        data = (ep.get("task") or {}).get("data") or {}
        tr = (ep.get("traces") or [{}])[0]
        reply = reply_of(tr)
        t_old = stored_truth(data["truth_json"])
        did = t_old.doc_id
        dig = set(data.get("ocr_digits") or [])
        r_old = score(reply, t_old, dig)
        r_new = score(reply, fixed[did], digits[did])
        old_t.append(r_old.total)
        new_t.append(r_new.total)
        old_e.append(r_old.metrics.get("doc_exact_match", 0.0))
        new_e.append(r_new.metrics.get("doc_exact_match", 0.0))
        if did in AFFECTED:
            aff_old.append(r_old.total)
            aff_new.append(r_new.total)
    rec = {"n": len(old_t),
           "old_mean": round(mean(old_t), 6), "new_mean": round(mean(new_t), 6),
           "old_exact": round(mean(old_e), 4), "new_exact": round(mean(new_e), 4),
           "affected_docs_old": round(mean(aff_old), 4) if aff_old else None,
           "affected_docs_new": round(mean(aff_new), 4) if aff_new else None,
           "n_affected_rollouts": len(aff_old)}
    out[f"{tier}|{cond}"] = rec
    print(f"{tier + '|' + cond:<22}{rec['old_mean']:>9.4f}{rec['new_mean']:>9.4f}"
          f"{rec['new_mean'] - rec['old_mean']:>+9.4f}"
          f"{rec['old_exact']:>11.3f}{rec['new_exact']:>11.3f}")

print(f"\nOn the {len(AFFECTED)} affected documents only "
      f"({len(AFFECTED) * 10} rollouts per cell):")
for k, v in out.items():
    print(f"  {k:<22} {v['affected_docs_old']:.4f} -> {v['affected_docs_new']:.4f} "
          f"({v['affected_docs_new'] - v['affected_docs_old']:+.4f})")

Path("results/rescore_fixed_truth.json").write_text(json.dumps(out, indent=2))
print("\nwrote results/rescore_fixed_truth.json")


# ---------------------------------------------------------------------------
# Emit a corrected aggregate file with the same shape as the runner's output,
# so the existing analyzer produces every downstream number (pass@k, taxonomy,
# cost per correct extraction) from the corrected ground truth.

src = json.load(open("results/full_test.json"))
fixed_doc = dict(src)
fixed_doc["source_of_truth"] = "re-parsed from CORD v2 after the list-valued field fix"
fixed_doc["rescored_from"] = "results/full_test.json"
fixed_doc["runs"] = {}

for tier, cond, d in CELLS:
    key = f"{tier}|{cond}"
    run = dict(src["runs"][key])
    rows = []
    for line in (Path("outputs") / d / "traces.jsonl").read_text().splitlines():
        if not line.strip():
            continue
        ep = json.loads(line)
        data = (ep.get("task") or {}).get("data") or {}
        tr = (ep.get("traces") or [{}])[0]
        did = json.loads(data["truth_json"])["doc_id"]
        res = score(reply_of(tr), fixed[did], digits[did])
        # The taskset's own flattening, not a reimplementation of it.
        met = flat_metrics(res)
        usage = tr.get("usage") or {}
        met["input_tokens"] = float(usage.get("num_input_tokens", 0) or 0)
        met["output_tokens"] = float(usage.get("num_output_tokens", 0) or 0)
        rows.append({"doc_id": f"{src['split']}-{cond}-{data.get('doc_index'):03d}",
                     "doc_index": data.get("doc_index"),
                     "condition": cond,
                     "reward": res.total,
                     "components": dict(res.rewards),
                     "metrics": met})
    run["rows"] = rows
    run["reward_mean"] = round(mean(r["reward"] for r in rows), 4)
    run["reward_sd"] = round(
        (sum((r["reward"] - mean(x["reward"] for x in rows)) ** 2
             for r in rows) / len(rows)) ** 0.5, 4)
    fixed_doc["runs"][key] = run

Path("results/full_test_fixed.json").write_text(json.dumps(fixed_doc, indent=1))
print("wrote results/full_test_fixed.json")
