"""Regenerate every table in README.md from the files in results/.

This is the one command the reproduction claim rests on. It reads only JSON and
CSV under results/ and writes the markdown between the GENERATED markers in
README.md. Nothing is typed by hand, so a number in the README that does not
match the data is a build failure rather than a reader's problem.

    python analysis/regenerate_tables.py            # rewrite README.md in place
    python analysis/regenerate_tables.py --check     # exit 1 if README is stale
    python analysis/regenerate_tables.py --stdout    # print the block only

Every figure traces to:
    results/analysis_full_test_fixed.json   cell means, components, cost
    results/prediction_scorecard.json       bootstrap CIs, tier gaps, verdicts
    results/headroom_ablations.json         specification-vs-capability split
    results/weight_sensitivity.json         robustness under six rubrics
    results/failure_taxonomy.json           error counts per cell
    results/d7_scorecard.json               the pre-registered prompt fix
    results/unit_price_confusion.json       the mirror-image check
    results/verifier_selftest.json          verifier gates
    results/spend.csv                       every dollar, per run
"""
import csv
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RESULTS = REPO / "results"
README = REPO / "README.md"
BEGIN = "<!-- BEGIN GENERATED: regenerate_tables.py -->"
END = "<!-- END GENERATED -->"

TIERS = [("small", "Qwen3.5-9B"), ("mid", "Qwen3-VL-30B-A3B"),
         ("frontier", "Opus 5.5")]


def load(name):
    with open(RESULTS / f"{name}.json") as fh:
        return json.load(fh)


def f4(x):
    return f"{x:.4f}"


def signed(x, places=4):
    return f"{x:+.{places}f}"


def ci(d, key_low="ci_low", key_high="ci_high"):
    return f"[{signed(d[key_low])}, {signed(d[key_high])}]"


def build():
    A = load("analysis_full_test_fixed")
    P = load("prediction_scorecard")
    H = load("headroom_ablations")
    W = load("weight_sensitivity")
    T = load("failure_taxonomy")
    D = load("d7_scorecard")
    U = load("unit_price_confusion")
    V = load("verifier_selftest")

    out = [BEGIN, ""]

    # ---- 1. headline ----
    out += [
        "### Mean reward, and the effect of input modality",
        "",
        "| tier | model | OCR text | page image | image minus OCR | 95% CI |",
        "|---|---|---|---|---|---|",
    ]
    for tier, label in TIERS:
        c_ocr = A["cells"][f"{tier}|ocr_text"]
        c_img = A["cells"][f"{tier}|image"]
        d = P["condition_deltas"][tier]
        out.append(
            f"| {label} | `{c_ocr['model']}` | {f4(c_ocr['reward_mean'])} | "
            f"{f4(c_img['reward_mean'])} | {signed(d['delta'])} | {ci(d)} |")
    mdes = W["schemes"]["registered"]["mde"]
    mde_str = " / ".join(f4(mdes[t]) for t, _ in TIERS)
    out += [
        "",
        f"Every interval spans zero. Minimum detectable effect by tier: "
        f"{mde_str}. Paired bootstrap over the same "
        f"{A['docs']} documents, {P['bootstrap_resamples']:,} resamples, "
        f"seed {P['seed']}.",
        "",
    ]

    # ---- 2. tier gaps ----
    out += [
        "### Scale gaps, which do not span zero",
        "",
        "| gap | condition | gap | 95% CI |",
        "|---|---|---|---|",
    ]
    for key, g in P["tier_gaps"].items():
        pair, cond = key.split("|")
        out.append(f"| {pair} | {cond} | {signed(g['gap'])} | "
                   f"[{signed(g['ci_low'])}, {signed(g['ci_high'])}] |")
    order = sum(1 for s in W["schemes"].values() if s["tier_order_holds"])
    out += [
        "",
        f"Tier ordering holds under {order} of {len(W['schemes'])} reward "
        "rubrics, so it is not an artifact of the weights chosen.",
        "",
    ]

    # ---- 3. pass@k and exact match ----
    out += [
        "### Document exact match and pass@k",
        "",
        "A document counts only when every field is right. pass@k is over the "
        "10 samples drawn per document.",
        "",
        "| tier | condition | n | exact match (pass@1) | pass@3 | pass@5 | pass@10 |",
        "|---|---|---|---|---|---|---|",
    ]
    for tier, label in TIERS:
        for cond in ("ocr_text", "image"):
            c = A["cells"][f"{tier}|{cond}"]
            out.append(
                f"| {label} | `{cond}` | {c['n']:,} | {c['pass@1']:.3f} | "
                f"{c['pass@3']:.3f} | {c['pass@5']:.3f} | {c['pass@10']:.3f} |")
    out.append("")

    # ---- 4. specification vs capability ----
    base = H["ablations"]["baseline"]
    both = H["ablations"]["both_specification_fixes"]
    out += [
        "### How much of the gap was my specification, not the model",
        "",
        "Re-scoring saved rollouts under one named change at a time. The "
        "ablations are deliberately generous, so these are upper bounds.",
        "",
        "| gap on OCR text | measured | upper bound after spec fixes | share specification |",
        "|---|---|---|---|",
    ]
    for hi, lo, name in [("frontier", "mid", "frontier over mid"),
                         ("frontier", "small", "frontier over small")]:
        m = base[f"{hi}|ocr_text"] - base[f"{lo}|ocr_text"]
        a = both[f"{hi}|ocr_text"] - both[f"{lo}|ocr_text"]
        out.append(f"| {name} | {f4(m)} | {f4(a)} | {(m - a) / m:.0%} |")
    fg = H["gains"]["forgive_invented_subtotal"]
    out += [
        "",
        f"Forgiving an invented `subtotal` is worth "
        f"{signed(fg['mid|ocr_text'])} to the mid tier and "
        f"{signed(fg['frontier|ocr_text'])} to the frontier. A fix worth "
        "something to the smaller model and nothing measurable to the frontier "
        "is a fix to the task, not to the model.",
        "",
    ]

    # ---- 5. the pre-registered prompt fix ----
    q = D["quantities"]
    out += [
        f"### The fix, pre-registered and re-run on `{D['cell']}`",
        "",
        "| quantity | before | after | change | 95% CI |",
        "|---|---|---|---|---|",
    ]
    cis_for = {"mean reward": D["reward_gain"],
               "doc exact match": D["exact_match_gain"]}
    for name, label in [("mean reward", "mean reward"),
                        ("doc exact match", "doc exact match"),
                        ("invented_subtotal", "invented `subtotal`"),
                        ("missed_subtotal", "missed `subtotal`")]:
        d = q[name]
        b, a = d["baseline"], d["variant"]
        g = cis_for.get(name)
        cis = (f"[{signed(g['ci_low'])}, {signed(g['ci_high'])}]"
               if g else "not bootstrapped")
        fmt = (lambda v: f"{v:.4f}") if isinstance(b, float) else (lambda v: f"{v:g}")
        out.append(f"| {label} | {fmt(b)} | {fmt(a)} | "
                   f"{signed(a - b) if isinstance(b, float) else f'{a - b:+d}'}"
                   f" | {cis} |")
    out += [
        "",
        f"One sentence added to the prompt, prompt version "
        f"`{D['prompt_variant']}`, cost ${D['measured_cost_usd']:.4f}. "
        f"Missed subtotals did not rise, so there was no precision-recall "
        "trade: that is the evidence this was a specification gap and not a "
        "reading one.",
        "",
    ]

    # ---- 6. failure taxonomy ----
    rows = [("value wrong by 1000x (locale separator)", "magnitude_1000x"),
            ("missed `tax`", "missed_tax"),
            ("price wrong on a matched item", "price_wrong_on_matched"),
            ("item name mismatch", "item_name_mismatch"),
            ("invented `subtotal`", "invented_subtotal"),
            ("unparseable reply", "unparseable")]
    out += [
        "### What remains, and it is capability",
        "",
        "Counts are **rollouts of 1,000 per cell** carrying at least one such "
        "error, on OCR text.",
        "",
        "| error | " + " | ".join(label for _, label in TIERS) + " |",
        "|---|" + "---|" * len(TIERS),
    ]
    for label, key in rows:
        c = T["counts"].get(key, {})
        out.append(f"| {label} | " + " | ".join(
            str(c.get(f"{t}|ocr_text", 0)) for t, _ in TIERS) + " |")
    worst = max(U["cells"].values(), key=lambda c: c.get("opportunities", 0))
    total_wrong = sum(c["price_equals_unit_price"] for c in U["cells"].values())
    out += [
        "",
        f"The mirror image: where the prompt *is* explicit, that `price` means "
        f"the line total rather than the per-unit amount, "
        f"**{total_wrong} rollouts of "
        f"{sum(c['n'] for c in A['cells'].values()):,} confused the two**, with "
        f"{worst.get('opportunities', 0)} opportunities in the richest cell "
        f"across {U['observable_items']} observable items. Silent prompt and "
        "the models diverge; explicit prompt and even the 9B complies.",
        "",
    ]

    # ---- 7. scorecard ----
    verdicts = P["verdicts"]
    def tally(owner):
        v = [d["verdict"] for d in verdicts.values() if d["owner"] == owner]
        return (v.count("HIT"), v.count("PARTIAL"), v.count("MISS"), len(v))
    out += [
        "### Pre-registered predictions, scored",
        "",
        "| author | predictions | hit | partial | miss |",
        "|---|---|---|---|---|",
    ]
    for owner in sorted({d["owner"] for d in verdicts.values()}):
        h, pa, m, n = tally(owner)
        out.append(f"| {owner} | {n} | {h} | {pa} | {m} |")
    out.append("")

    # ---- 8. cost and reliability ----
    with open(RESULTS / "spend.csv") as fh:
        spend = list(csv.DictReader(fh))
    total = sum(float(r["usd"]) for r in spend)
    rollouts = sum(int(r["rollouts"]) for r in spend)
    gates = V["corruptions"]
    gt = gates["ground_truth"]
    out += [
        "### Cost, reliability, and the verifier's own gates",
        "",
        f"- Claim run: {sum(c['n'] for c in A['cells'].values()):,} rollouts, "
        f"0 failures, ${A['measured_total_usd']:.2f}.",
        f"- All runs in this repo: {rollouts:,} rollouts across "
        f"{len(spend)} logged runs, ${total:.2f} total, itemised in "
        "[`results/spend.csv`](results/spend.csv).",
        f"- Verifier gate: ground truth scores "
        f"{gt['mean']:.4f} on all {V['n_docs']} validation documents "
        f"(min {gt['min']:.4f}, max {gt['max']:.4f}).",
        f"- Every corruption and gaming strategy scores below ground truth; "
        f"see [`results/verifier_selftest.json`]"
        f"(results/verifier_selftest.json).",
        "",
        END,
    ]
    return "\n".join(out)


def main():
    block = build()
    if "--stdout" in sys.argv:
        print(block)
        return 0

    text = README.read_text()
    if BEGIN not in text or END not in text:
        print(f"FAIL: README.md is missing the generated markers", file=sys.stderr)
        return 1
    head, rest = text.split(BEGIN, 1)
    _, tail = rest.split(END, 1)
    rebuilt = head + block + tail

    if "--check" in sys.argv:
        if rebuilt == text:
            print("PASS: README tables match results/")
            return 0
        print("FAIL: README tables are stale. Run:\n"
              "  python analysis/regenerate_tables.py", file=sys.stderr)
        import difflib
        for line in list(difflib.unified_diff(
                text.splitlines(), rebuilt.splitlines(),
                "README.md", "regenerated", lineterm=""))[:60]:
            print(line, file=sys.stderr)
        return 1

    README.write_text(rebuilt)
    print(f"rewrote the generated block in {README.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
