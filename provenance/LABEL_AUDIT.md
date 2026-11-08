# Hand audit of CORD ground-truth labels

Both parser bugs in this study (D5, D6) were found after 6,000 rollouts had
been scored, and three automated gates had passed while the parser was still
wrong. The open question was whether a third bug was still in there. Gates
cannot answer it, because a gate proves the verifier is self-consistent, not
that it is right. A person reading the receipts can.

## Method

20 of the 100 `test` documents: the four that D5 and D6 touched, by name, then
16 drawn from the remaining 96 with seed 20261106. For each one, the
reconstructed page text, the page photograph, CORD's raw annotation strings and
the integers this repo parsed from them, with a verdict and per-row flags
recorded in the review page's store (`scripts/16_audit_sheet.py`, published at
`audit_review/index.html`).

Graded by Sean Mihm, 2026-11-07, all 20.

## Result: 19 correct, 1 flagged, 0 label bugs

| verdict | count |
|---|---|
| labels correct | 19 |
| label is wrong | 1 (`test-082`, resolved below) |
| cannot tell | 0 |

### The one flag, and what it actually found

`test-082` prints `Strawberry Log Cake 2x 105,000 210,000`. The note read:

> price of strawberry log 105,000 but qty 2 is 210000 so think label for price
> should be 105000 and quantity 2

The label is correct. CORD records `unitprice: "105,000"`, `cnt: "2x"`,
`price: "210,000"`, and this repo parses all three. The prompt defines `price`
as the amount charged for the line after quantity, so 210,000 is right, and the
arithmetic only closes that way: 115,000 + 60,000 + 210,000 = 385,000, the
printed subtotal.

**The flag was correct about what it was shown.** The review page's line-item
table displayed name, price and quantity and omitted `unit_price` entirely, so
the 105,000 printed on the receipt appeared in no column and looked unrecorded.
A reviewer could not have reached any other conclusion from that view. The
page now shows `CORD unitprice` and the parsed `unit_price`, highlighted
wherever the two amounts differ, which is exactly the case that is ambiguous
without them.

So the audit found a defect in the audit instrument rather than in the labels.
That is still a finding: a review tool that hides the field under review
produces false positives, and it would have produced false negatives just as
easily.

## The measurement it prompted

If a human reviewer could confuse the unit price with the line total, models
might too, and `line_item_f1` scores name and price only, so the confusion
would be buried inside `price_wrong_on_matched` rather than named. Re-matching
all 6,000 saved rollouts offline (`scripts/19_unit_price_confusion.py`,
`results/unit_price_confusion.json`):

| cell | items with a wrong price | of those, price equals unit_price | opportunities |
|---|---|---|---|
| small ocr | 234 | **0** | 135 |
| small image | 243 | **0** | 121 |
| mid ocr | 123 | **0** | 111 |
| mid image | 114 | **0** | 120 |
| frontier ocr | 12 | **0** | 130 |
| frontier image | 4 | **0** | 134 |

The counts above are **items**, not rollouts. `docs/HEADROOM.md` reports the
same failure as rollouts carrying at least one wrong price (155 / 99 / 6 on OCR
text), which is the smaller number because a rollout can get several items
wrong. Both are stated with their unit wherever they appear.

An opportunity is a matched item whose quantity exceeds one and whose unit
price differs from its line total: 18 such items across 11 of the 100 test
documents. **Not one rollout at any tier made this mistake**, with over 100
opportunities in every cell. Every model, including the 9B, reads
`2x 105,000 210,000` and reports the line total where the schema asks for it.
The prompt's one-sentence definition of `price` is being followed exactly.

This is the opposite shape to the `subtotal` finding: there the prompt was
silent and the models diverged, here the prompt is explicit and they agree. The
two together are the argument that the open-weight gap on this task is
specification-sensitive rather than comprehension-limited.

### A zero that was nearly reported as a finding

The first run of that script printed zero in every column, including the
wrong-price column, which was wrong: it read the model's reply from a
`last_reply` field that traces do not have, scored every rollout as
unparseable, and produced a clean table of zeros. The check that caught it was
comparing the wrong-price column against the failure taxonomy, where it should
have been in the hundreds. The script now asserts that column is non-zero
before reporting a share, so the same silent failure cannot pass again. Same
lesson as the harness default: the dangerous failures are the ones that return
a plausible number.

## What this bounds, and what it does not

20 of 100 documents with no label error found puts the 95% upper bound on the
per-document label error rate at about **14%**, by the rule of three. That is
not a small number, and it is the honest limit of a 20-document sample. What
the audit does establish is that D5 and D6 were not the visible tip of a
widespread annotation problem, and that the four documents they touched are now
correct when read by eye against the page.

The second audit question, whether the page prints more item lines than CORD
annotates, was not scored per document here. It is documented separately in
`docs/HEADROOM.md` as a benchmark ceiling affecting about 9 of 100 test
documents.
