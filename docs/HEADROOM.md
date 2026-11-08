# Headroom: capability gaps versus specification gaps

Phase 3 item 3. Every number here comes from `results/`, measured by
re-scoring the 6,000 saved rollouts of the claim run. No model was re-run, so
these are free counterfactuals (`scripts/15_headroom_ablations.py`,
`results/headroom_ablations.json`).

## Method

An **ablation** changes one named thing about scoring or about the prediction
and re-scores everything. If an ablation recovers reward, the failure it
targets was a *specification* gap: the model's output was usable and the task
definition or the output contract threw it away. If no ablation recovers it,
it is a *capability* gap. The ablations are deliberately generous: they are
upper bounds on what a fix could be worth, not forecasts.

## Result

Mean reward, and the gain over the measured baseline:

| ablation | small ocr | small img | mid ocr | mid img | frontier ocr | frontier img |
|---|---|---|---|---|---|---|
| baseline (measured) | 0.7272 | 0.7169 | 0.7985 | 0.8203 | 0.9121 | 0.9208 |
| forgive invented `subtotal` | +0.0210 | +0.0245 | +0.0379 | +0.0223 | +0.0001 | +0.0000 |
| fuzzy item names | +0.0292 | +0.0368 | +0.0174 | +0.0276 | +0.0116 | +0.0170 |
| accept a bare JSON array | +0.0000 | +0.0020 | +0.0000 | +0.0000 | +0.0000 | +0.0000 |
| **both specification fixes** | **+0.0502** | **+0.0633** | **+0.0553** | **+0.0499** | **+0.0117** | **+0.0170** |

**The headline.** Specification fixes are worth four to five times more to the
open and mid tiers than to the frontier, so they close part of the tier gap
without training anything:

| gap | measured | after specification fixes | share that was specification |
|---|---|---|---|
| frontier over mid, ocr | 0.1136 | 0.0700 | 38% |
| frontier over mid, image | 0.1006 | 0.0676 | 33% |
| frontier over small, ocr | 0.1849 | 0.1465 | 21% |
| frontier over small, image | 0.2040 | 0.1577 | 23% |

About a third of the mid-to-frontier gap on this task is not capability. It is
one ambiguous schema decision and one name-formatting convention.

## The three gaps, named

### 1. Specification: `subtotal` on a receipt that prints only a total

Worth **+0.0379** to the mid tier on OCR text and **+0.0001** to the frontier.
The largest single scalar error in five of six cells: 282 of 1,000 mid-tier
rollouts emit `subtotal` equal to `total` on receipts where CORD annotates only
a total (`test-001`: truth `{total: 91000}`, prediction
`{subtotal: 91000, total: 91000}`).

This is defensible model behaviour. On a single-line receipt the subtotal and
the total *are* the same number, and the prompt never says whether to report a
field the document does not print. The frontier model happens to resolve the
ambiguity the way CORD's annotators did; the smaller models do not. That is a
measurement of instruction-following, not of extraction.

**What closes it:** one sentence in the prompt. It was not changed for this
study because the prompt is pre-registered and byte-identical across models;
changing it after seeing results would invalidate the comparison. It was
instead pre-registered separately as deviation D7 and run on its own.

**Measured, not projected.** D7 added one rule and re-ran the mid tier on OCR
text for $0.2024: reward **0.7985 to 0.8301**, +0.0316 with a 95% interval of
[+0.0176, +0.0460] excluding zero, and document exact match **0.360 to
0.497**. `invented_subtotal` fell from 282 to 53 of 1,000 rollouts and
`missed_subtotal` stayed at 0, so the sentence recovered 83% of the +0.0379
bound below with no over-correction. The bound in the table was a real
forecast, not just a ceiling.

### 2. Capability: the Indonesian thousands separator

Not recoverable by any ablation, and a pure scale story:

| | small ocr | small img | mid ocr | mid img | frontier ocr | frontier img |
|---|---|---|---|---|---|---|
| 1000x magnitude error | 141 | 138 | 4 | 3 | **0** | **0** |

The receipt prints `60.000` for sixty thousand. The 9B model emits the JSON
number `60.0`, reading the separator as a decimal point and losing a factor of
1,000 (`test-000`: truth 60000, prediction 60). This happens on 14% of 9B
rollouts, 0.4% of 30B rollouts, and 0 of 2,000 frontier rollouts.

It is also the most consequential error class in the set: a wrong name is a
data-quality issue, a value wrong by 1,000x is a financial one. No prompt
change fixes it, because the model is not confused about the instruction.

**What closes it:** training data, and the kind is specific. Not more receipts,
but receipts whose correct answer *requires* resolving a separator convention,
paired so that `60.000` and `60.00` appear in the same batch with different
right answers. CORD's `train` split (800 documents, unused here) supplies the
images; the reward already discriminates, since this error costs scalar F1,
item F1, and grounding at once. This is the clearest case in the study for an
RL run over a prompt change, and it is why the conditional training phase
targets a 4B in the same family as the small tier.

### 3. Benchmark ceiling: not the model's to close

Two limits sit in the labels, and no model or training run moves them.

- **Under-annotation of zero-priced items.** About 9 of 100 `test` documents
  print more quantity-prefixed item lines than CORD annotates, usually
  zero-priced bundle components (`test-099` prints 7 item lines, 6 at price 0;
  CORD records 1). A model that reads them is scored as over-extracting. This
  caps line-item F1, the component Sean's prediction S2 correctly identified
  as the lowest in all six cells.
- **Ground truth that fails its own arithmetic** on roughly 9% of evaluable
  documents, which is why arithmetic consistency is reported as a metric here
  and never rewarded (`docs/DATA_NOTES.md`). `test-099` reconciles only if a
  printed `PEMBULATAN 2` rounding line is included, which the schema has no
  field for.

**What this means for an eval:** document exact match against CORD has a
ceiling below 1.0 that is a property of the dataset. The frontier's 0.674 is
not 0.326 away from a solved task. Any claim of the form "the model gets 67% of
documents perfect" needs this stated, which is why it is stated here.

## What is left that is genuinely capability

After the specification fixes and setting aside the benchmark ceiling, the
frontier-over-mid gap is still 0.070 on OCR text. It sits in:

- **Item name transcription**, worth +0.0174 to +0.0276 to the mid tier under
  fuzzy matching but still the lowest component everywhere after it
  (`line_item_f1` 0.736 mid, 0.849 frontier). Partly transcription of Indonesian
  abbreviations (`J.STB PROMO` read as `J.STB`), partly real item boundary
  errors on multi-line items.
- **Missed `tax`**: 62 of 1,000 mid-tier OCR rollouts against 0 of 1,000
  frontier, concentrated on receipts where the tax line is labelled
  `PAJAK PPN 10 %` rather than a recognisable keyword.
- **Price assignment on an item whose name matched**: 99 mid against 6 frontier
  on OCR text, which is a layout-association failure rather than a reading one.

All three are addressable with training data from the unused 800-document
`train` split, and all three are already separately scored by the verifier, so
an RL run would get gradient on each rather than on an undifferentiated total.

## Format is not a bottleneck, by two independent routes

Prediction P5 said so and was the one prediction of mine that held. Both
checks agree:

- Parseable output on 99.5% to 100% of rollouts in every cell. The only
  invalid replies anywhere are 5 of 1,000 in small-tier image.
- Accepting a bare JSON array, the single format the verifier rejects, is worth
  **+0.0020** on that one cell and **+0.0000** everywhere else.

Anyone attributing open-weight failure on this task to "it cannot follow the
format" is wrong, and the number that shows it is +0.002.
