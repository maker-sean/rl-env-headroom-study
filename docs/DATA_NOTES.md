# Measured properties of CORD v2, and what they forced

Every number here comes from a script in `scripts/` run against
`naver-clova-ix/cord-v2`, split `validation` (n=100), on 2026-11-05. The
`test` split (n=100) has deliberately NOT been inspected and stays held out
until the pre-registered run.

Reproduce with:
```
uv run python scripts/02_probe_consistency.py
uv run python scripts/03_verify_cord_layer.py
uv run python scripts/04_verifier_selftest.py
```

## Field coverage in ground truth

| canonical field | CORD source | present |
|---|---|---|
| total | `total.total_price` | 98/100 |
| subtotal | `sub_total.subtotal_price` | 67/100 |
| tax | `sub_total.tax_price` | 47/100 |
| service_charge | `sub_total.service_price` | 13/100 |
| discount | `sub_total.discount_price` | 6/100 |
| line items | `menu[]` (`nm`, `cnt`, `unitprice`, `price`) | 100/100 |

Line items per document: min 1, max 11, mean 2.2.

**No merchant name and no transaction date exist.** CORD's publishers removed
`store_info`, `payment_info`, and `etc` before release. Those fields are out
of scope; no synthetic values are injected, so every scored target is real
ground truth.

Because coverage is sparse for `service_charge` and `discount`, correctly
*omitting* a field is a large part of the task. Scoring treats absent as a
value: emitting a field the document does not have is a false positive.

## Schema quirks that forced code

1. **`menu` is polymorphic.** A dict when the receipt has one item, a list
   when it has several: 46 dict, 54 list. Any consumer must normalize.
2. **Amount strings use both separators as thousands.** Observed formats:
   `##,###` (110), `##.###` (46), `#.###` (17), `###,###` (13), `#,###` (11),
   `#` (9), `###.###` (3), `Rp ##,###` (2), `###` (2), `Rp ###,###` (1).
3. **Quantity strings carry units.** `#` (172), `#x` (7), `x#` (7), `# x` (6),
   `#Prs` (6), `#X` (5), `###` (2), `#.##` (1), `#Gls` (1), `# X` (1).

## The finding that changed the rubric: ground truth is not self-consistent

| check | evaluable | holds |
|---|---|---|
| sum(line item prices) == subtotal, else total | 99/100 | **90 (91%)** |
| subtotal + tax + service - discount == total | 65/100 | **61 (94%)** |

Counterexamples, verbatim from the probe:

- doc 2: subtotal 18,181 + tax 1,818 = 19,999 against total 20,000. The
  receipt prints a round total and back-computes the rest, so rounding leaves
  it off by one.
- doc 77: subtotal 5,800,000 + tax 527,273 = 6,327,273 against total 5,800,000.
  Tax is **included** in the total, so adding it double-counts.
- doc 13: 41,363 against 41,364. Off by one.
- doc 8: line prices [19,500, 0] sum 19,500 against subtotal and total 11,700.

This is Indonesian tax-inclusive pricing (PPN folded into the displayed price)
plus rounding to round totals.

**Consequence: arithmetic consistency is a metric, never a reward.** Rewarding
it would put a roughly 9% false-penalty floor on perfectly correct extractions,
and the verifier would score 0.91 on ground truth instead of 1.0. This is a
direct amendment to the verifier specification in CLAUDE.md, which listed
consistency checks as part of scoring. The checks are still computed and
reported, with a 1-unit tolerance that absorbs the documented rounding.

The wider point, worth stating in any write-up: **"verifiable" does not
mean "self-consistent."** A reward that looks checkable by construction can
still disagree with the labels roughly one time in eleven.

## Two bugs the "ground truth must score 1.0" rule caught

Both were in the grounding check's digit extraction, and both would have
silently penalized correct extractions.

1. **Newline fusion.** Stripping all whitespace turned `16,500\n1 EGG TART`
   into the single run `165001`, so two real values looked ungrounded.
2. **Space fusion.** Fixing (1) by treating a space as a thousands separator
   turned `1 40.000` into `140000`, losing the real price `40000`. That fix
   repaired 1 document and broke 28. Ground-truth score went from 0.9972 to
   0.9869 mean, which is how it was caught.

Final rule: a numeric token spans digits joined only by `.` or `,`; spaces and
newlines end a token; the space-as-thousands reading is an extra candidate only
when the next group is exactly three digits. Explicit cents (`58000.00`,
`5272.73`) add a whole-units candidate.

Grounding is deliberately **lenient**, because a value wrongly judged
ungrounded penalizes a correct extraction, while a value wrongly judged
grounded only weakens the hallucination signal, and the spam dilution already
guards the strategy that exploits it.

After both fixes: ground truth scores **1.0 on all 100 documents**, min = max = 1.0.

## Input encoding for the image condition

CORD pages are 864x1296 RGB. Encoded at `max_edge=1280` (effectively native):

| encoding | data-URL chars | vs PNG |
|---|---|---|
| PNG | 1,391,414 | 100% |
| JPEG q95 | 293,591 | 21.1% |
| **JPEG q90 (chosen)** | **177,195** | **12.7%** |
| JPEG q85 | 129,019 | 9.3% |
| JPEG q90 @1024 | 113,811 | 8.2% |

JPEG q90 at 1280 is the default. Digit legibility is the capability the image
condition exists to measure, so quality must not be lowered without re-running.
