"""Re-score saved traces with the current verifier. No model calls, no spend.

Model replies are persisted in each run's traces.jsonl, so a verifier change
can be evaluated against already-collected rollouts for free. Used to measure
the effect of a scoring fix without re-running anything.

Usage: uv run python scripts/10_rescore_traces.py outputs/<prefix>
"""
import json, sys
from pathlib import Path
from statistics import mean, pstdev

sys.path.insert(0, "src")
from doc_extraction_study.cord import LineItem, Receipt
from doc_extraction_study.scoring import score


def truth_from(blob):
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


prefix = sys.argv[1]
dirs = sorted(Path("outputs").glob(Path(prefix).name + "*"))
print(f"{'cell':<46} {'old':>8} {'new':>8} {'delta':>8} {'item_old':>9} {'item_new':>9}")
print("-" * 92)
out = {}
for d in dirs:
    f = d / "traces.jsonl"
    if not f.exists():
        continue
    old_tot, new_tot, old_item, new_item = [], [], [], []
    for line in f.read_text().splitlines():
        if not line.strip():
            continue
        ep = json.loads(line)
        data = (ep.get("task") or {}).get("data") or {}
        tr = (ep.get("traces") or [{}])[0]
        rw = {k: (v.get("score") if isinstance(v, dict) else v)
              for k, v in (tr.get("rewards") or {}).items()}
        wt = {k: (v.get("weight") if isinstance(v, dict) else None)
              for k, v in (tr.get("rewards") or {}).items()}
        old = sum((rw[k] or 0) * (wt[k] or 0) for k in rw if wt.get(k) is not None)
        old_tot.append(old)
        old_item.append(rw.get("line_item_f1") or 0.0)
        res = score(reply_of(tr), truth_from(data["truth_json"]),
                    set(data.get("ocr_digits") or []))
        new_tot.append(res.total)
        new_item.append(res.rewards["line_item_f1"])
    if not old_tot:
        continue
    name = d.name.replace("pilot2-validation-", "")
    out[name] = {"old": mean(old_tot), "new": mean(new_tot),
                 "new_sd": pstdev(new_tot) if len(new_tot) > 1 else 0.0,
                 "item_old": mean(old_item), "item_new": mean(new_item), "n": len(new_tot)}
    print(f"{name:<46} {mean(old_tot):>8.4f} {mean(new_tot):>8.4f} "
          f"{mean(new_tot)-mean(old_tot):>+8.4f} {mean(old_item):>9.4f} {mean(new_item):>9.4f}")
Path("results").mkdir(exist_ok=True)
Path("results/rescore_pilot2.json").write_text(json.dumps(out, indent=2))
print("\nwrote results/rescore_pilot2.json")
