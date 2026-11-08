"""Build a hand-audit sheet: 20 CORD test receipts, printed text beside parsed labels.

Two verifier bugs (D5, D6) surfaced only after the claim run, both in the
ground-truth parser rather than in a model. Automated gates proved
self-consistency and missed them. This script produces an artifact a human can
check in half an hour: for each document, the reconstructed page text, the raw
CORD annotation strings, and the integer this repo parsed them into.

Selection is not random. The four documents the two bug fixes touched are
included by name, then 16 more are drawn with a fixed seed from the remaining
96, so the sheet is reproducible and covers the known-hard shapes.

Usage: uv run python scripts/16_audit_sheet.py
Writes results/audit_sheet.md, results/audit_sheet.json (the same content as
data, for the review page) and results/audit/<doc>.png
"""
import json, random, subprocess, sys
from pathlib import Path

sys.path.insert(0, "src")
from datasets import load_dataset

from doc_extraction_study.cord import (SCALAR_MAP, _one_name, _one_value,
                                       _as_list, ocr_text, parse_ground_truth)

SEED = 20261106
# The documents D5 and D6 changed. They are the reason this sheet exists.
KNOWN = ["test-013", "test-099", "test-047", "test-067"]
N_TOTAL = 20


def git_stamp() -> str:
    rev = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                         capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain"],
                           capture_output=True, text=True).stdout.strip()
    return f"{rev}{'-DIRTY' if dirty else ''}"


def main():
    ds = load_dataset("naver-clova-ix/cord-v2", split="test")
    ids = [f"test-{i:03d}" for i in range(len(ds))]
    rest = [i for i in ids if i not in KNOWN]
    rng = random.Random(SEED)
    picked = KNOWN + sorted(rng.sample(rest, N_TOTAL - len(KNOWN)))

    outdir = Path("results/audit")
    outdir.mkdir(parents=True, exist_ok=True)

    data = []
    L = []
    L.append("# Hand-audit sheet: 20 CORD v2 test receipts")
    L.append("")
    L.append(f"git `{git_stamp()}` | seed {SEED} | split `test` | "
             f"{N_TOTAL} of {len(ds)} documents")
    L.append("")
    L.append("Columns are: the raw string CORD annotates, and the integer this "
             "repo parsed it into. The audit question for each row is whether "
             "that integer is the amount the receipt actually prints.")
    L.append("")
    L.append("The second audit question is the annotation ceiling: count the "
             "item lines the page text prints and compare that to `items "
             "annotated`. Where the page prints more, exact match is capped "
             "below 1.0 for that document no matter what a model outputs.")
    L.append("")
    L.append("Page images are in `results/audit/`.")
    L.append("")
    L.append("| # | doc | items annotated | scalars | verdict (fill in) |")
    L.append("|---|---|---|---|---|")
    for n, doc in enumerate(picked, 1):
        i = int(doc.split("-")[1])
        truth = parse_ground_truth(ds[i]["ground_truth"], doc)
        L.append(f"| {n} | [{doc}](#{doc}) | {len(truth.line_items)} | "
                 f"{len(truth.scalars())} | |")
    L.append("")

    for n, doc in enumerate(picked, 1):
        i = int(doc.split("-")[1])
        row = ds[i]
        raw = json.loads(row["ground_truth"])
        parse = raw.get("gt_parse", {}) or {}
        truth = parse_ground_truth(row["ground_truth"], doc)
        page = ocr_text(row["ground_truth"])
        row["image"].save(outdir / f"{doc}.png")

        L.append(f"## {doc}")
        L.append("")
        if doc in KNOWN:
            L.append("**Touched by a bug fix.** Check this one first.")
            L.append("")
        L.append("### Page text, as the model saw it")
        L.append("")
        L.append("```")
        L.append(page)
        L.append("```")
        L.append("")
        L.append("### Scalars")
        L.append("")
        L.append("| field | CORD raw | parsed | matches the page? |")
        L.append("|---|---|---|---|")
        for (section, key), canonical in SCALAR_MAP.items():
            sec = parse.get(section)
            if not (isinstance(sec, dict) and key in sec):
                continue
            rawv = sec[key]
            mark = " **(list)**" if isinstance(rawv, list) else ""
            L.append(f"| {canonical} | `{json.dumps(rawv)}`{mark} | "
                     f"{getattr(truth, canonical)} | |")
        if not truth.scalars():
            L.append("| | *no scalar fields annotated* | | |")
        L.append("")
        L.append("### Line items")
        L.append("")
        L.append("| # | CORD nm | CORD unitprice | CORD price | parsed name | "
                 "unit_price | price | qty | matches the page? |")
        L.append("|---|---|---|---|---|---|---|---|---|")
        raws = [x for x in _as_list(parse.get("menu")) if isinstance(x, dict)]
        for k, (rw, it) in enumerate(zip(raws, truth.line_items), 1):
            nm, pr = rw.get("nm", ""), rw.get("price")
            mark = " **(list)**" if isinstance(nm, list) or isinstance(pr, list) else ""
            L.append(f"| {k} | `{json.dumps(nm)}`{mark} | "
                     f"`{json.dumps(rw.get('unitprice'))}` | `{json.dumps(pr)}` | "
                     f"{it.name} | {it.unit_price} | {it.price} | "
                     f"{it.quantity} | |")
        L.append("")
        data.append({
            "doc": doc, "touched": doc in KNOWN, "page": page,
            "page_lines": len([x for x in page.splitlines() if x.strip()]),
            "scalars": [
                {"field": canon, "raw": sec[key],
                 "parsed": getattr(truth, canon),
                 "is_list": isinstance(sec[key], list)}
                for (section, key), canon in SCALAR_MAP.items()
                if isinstance(sec := parse.get(section), dict) and key in sec],
            "items": [
                {"raw_nm": rw.get("nm", ""), "raw_price": rw.get("price"),
                 "raw_unitprice": rw.get("unitprice"),
                 "name": it.name, "price": it.price,
                 "unit_price": it.unit_price, "qty": it.quantity,
                 "is_list": isinstance(rw.get("nm"), list)
                            or isinstance(rw.get("price"), list)}
                for rw, it in zip(raws, truth.line_items)],
        })

        L.append(f"![{doc}](audit/{doc}.png)")
        L.append("")
        L.append("---")
        L.append("")

    dest = Path("results/audit_sheet.md")
    dest.write_text("\n".join(L))
    Path("results/audit_sheet.json").write_text(
        json.dumps({"seed": SEED, "git": git_stamp(), "split": "test",
                    "documents": data}, separators=(",", ":")))
    print(f"wrote {dest}  ({len(picked)} documents, "
          f"{len(list(outdir.glob('*.png')))} images in {outdir})")
    print("documents:", ", ".join(picked))


if __name__ == "__main__":
    sys.exit(main())
