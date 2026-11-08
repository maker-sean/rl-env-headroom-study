"""Headroom ablations: how much reward would each specific fix recover?

No model calls. Each ablation edits the prediction or the scoring in one
narrow, named way and re-scores all 6,000 saved rollouts. The gain is an upper
bound on what that fix could recover, which separates a capability gap (no
ablation recovers it) from a specification gap (an ablation recovers it for
free).

The ablations are deliberately generous to the model. They answer "what is the
most this could be worth", not "what would it score".

Usage: uv run python scripts/15_headroom_ablations.py
"""
import json
import sys
from pathlib import Path
from statistics import mean

sys.path.insert(0, "src")
from datasets import load_dataset
from doc_extraction_study.cord import ocr_text, parse_ground_truth
from doc_extraction_study.normalize import ocr_text_digits
from doc_extraction_study.scoring import (FUZZY_NAME_THRESHOLD, line_item_f1,
                                          parse_prediction, recover_json, score,
                                          scalar_f1, grounding)

CELLS = [
    ("small", "ocr_text", "full-test-ocr_text-qwen3.5-9b"),
    ("small", "image", "full-test-image-qwen3.5-9b"),
    ("mid", "ocr_text", "full-test-ocr_text-qwen3-vl-30b-a3b-instruct"),
    ("mid", "image", "full-test-image-qwen3-vl-30b-a3b-instruct"),
    ("frontier", "ocr_text", "full-test-ocr_text-claude-opus-5.5"),
    ("frontier", "image", "full-test-image-claude-opus-5.5"),
]
W = {"schema_valid": 0.05, "scalar_f1": 0.45, "line_item_f1": 0.35, "grounding": 0.15}

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


def rescore(pred, t, dig, fuzzy=False, forgive_invented_subtotal=False):
    """Recompute the weighted total from a prediction receipt."""
    if pred is None:
        return 0.0
    ps, ts = dict(pred.scalars()), dict(t.scalars())
    if forgive_invented_subtotal and "subtotal" in ps and "subtotal" not in ts:
        ps.pop("subtotal")

        class _P:
            pass
        shim = _P()
        shim.scalars = lambda: ps
        s_score, _ = scalar_f1(shim, t)
    else:
        s_score, _ = scalar_f1(pred, t)
    i_score, _ = line_item_f1(pred, t, fuzzy=fuzzy)
    g_score, _ = grounding(pred, dig, t)
    return (W["schema_valid"] * 1.0 + W["scalar_f1"] * s_score
            + W["line_item_f1"] * i_score + W["grounding"] * g_score)


ABL = ["baseline", "forgive_invented_subtotal", "fuzzy_item_names",
       "accept_bare_array", "both_specification_fixes"]
res = {a: {} for a in ABL}

for tier, cond, dname in CELLS:
    cell = f"{tier}|{cond}"
    acc = {a: [] for a in ABL}
    for line in (Path("outputs") / dname / "traces.jsonl").read_text().splitlines():
        if not line.strip():
            continue
        ep = json.loads(line)
        data = (ep.get("task") or {}).get("data") or {}
        tr = (ep.get("traces") or [{}])[0]
        did = json.loads(data["truth_json"])["doc_id"]
        t, dig = truth[did], digits[did]
        reply = reply_of(tr)
        base = score(reply, t, dig)
        acc["baseline"].append(base.total)

        pred = parse_prediction(reply, did).receipt
        acc["forgive_invented_subtotal"].append(
            rescore(pred, t, dig, forgive_invented_subtotal=True) if pred else base.total)
        acc["fuzzy_item_names"].append(
            rescore(pred, t, dig, fuzzy=True) if pred else base.total)

        # A reply that is a valid JSON *array* of line items is currently
        # invalid (hard zero). Accepting it as {"line_items": [...]} costs
        # nothing at inference time and is a format decision, not a capability.
        if pred is None:
            obj, _ = recover_json(reply)
            arr = None
            if obj is None:
                try:
                    cand = json.loads((reply or "").strip())
                    if isinstance(cand, list):
                        arr = cand
                except Exception:
                    arr = None
            if arr is not None:
                p2 = parse_prediction(json.dumps({"line_items": arr}), did).receipt
                acc["accept_bare_array"].append(rescore(p2, t, dig) if p2 else base.total)
            else:
                acc["accept_bare_array"].append(base.total)
            acc["both_specification_fixes"].append(acc["accept_bare_array"][-1])
        else:
            acc["accept_bare_array"].append(base.total)
            acc["both_specification_fixes"].append(
                rescore(pred, t, dig, fuzzy=True, forgive_invented_subtotal=True))
    for a in ABL:
        res[a][cell] = mean(acc[a])

ORDER = [f"{t}|{c}" for t, c, _ in CELLS]
print("HEADROOM ABLATIONS: mean reward, and gain over baseline\n")
print(f"{'ablation':<30}" + "".join(f"{c.replace('|', ' '):>22}" for c in ORDER))
print("-" * (30 + 22 * len(ORDER)))
for a in ABL:
    row = "".join(f"{res[a][c]:>22.4f}" for c in ORDER)
    print(f"{a:<30}{row}")
print()
for a in ABL[1:]:
    row = "".join(f"{res[a][c] - res['baseline'][c]:>+22.4f}" for c in ORDER)
    print(f"{'gain: ' + a:<30}{row}")

Path("results/headroom_ablations.json").write_text(json.dumps(
    {"weights": W, "ablations": res,
     "gains": {a: {c: res[a][c] - res["baseline"][c] for c in ORDER}
               for a in ABL[1:]}}, indent=2))
print("\nwrote results/headroom_ablations.json")
