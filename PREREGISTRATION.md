# Pre-registration

Committed before the claim run. The design below is locked; changing any of it
after results are seen must be recorded as a deviation in this file, not edited
away.

**Status of predictions:** complete. Claude's seven (P1 to P7) and Sean's five
(S1 to S5) were all committed before any model run against the `test` split.
P2 and S4 disagree about the frontier condition delta; that disagreement is
recorded below rather than resolved in advance.

## Disclosure: a model run happened before this file was committed

CLAUDE.md requires pre-registration before any model run. A 3-rollout smoke
test ran before this file existed. Disclosed in full:

- `qwen/qwen3.5-9b`, `ocr_text`, temperature 0.7, 3 documents, 1 sample each
- Documents: `validation` split, indices 0 to 2
- Rewards observed: 0.8313, 0.8125, 0.5600
- Purpose: verify the rollout path end to end; it was not a measurement

**Why the claim run is still clean:** the smoke test used the `validation`
split, which is the development set. Every claim in this study is made on the
`test` split, which has never been run against a model and whose ground truth
has never been inspected. The contamination is bounded to the dev set, which is
why it was held separate from the start.

## Locked design

| item | value |
|---|---|
| Dataset | CORD v2 (`naver-clova-ix/cord-v2`), CC-BY-4.0 |
| Claim split | `test`, n=100, untouched until the full run |
| Dev split | `validation`, n=100, used for prompt/verifier development and the pilot |
| Train split | `800 docs`, unused; reserved in case the conditional RL phase proceeds |
| Conditions | `ocr_text` and `image`, same documents, same prompt |
| Prompt | `prompts.py` `PROMPT_VERSION = v1.0.0`, byte-identical across models and conditions |
| Image encoding | JPEG quality 90, `max_edge=1280` |
| Temperature | **0.7**, fixed for every model and condition |
| Samples per document | **10** |
| Tiers | small `qwen/qwen3.5-9b`, mid `qwen/qwen3-vl-30b-a3b-instruct`, frontier `anthropic/claude-opus-5.5` |
| Rubric weights | `scalar_f1` 0.45, `line_item_f1` 0.35, `grounding` 0.15, `schema_valid` 0.05 |
| Budget | $15.00 authorized to 99%; Sean tops off if exceeded |

**Temperature rationale.** 0.7, not 0, because variance across samples and
pass@k are listed metrics and both collapse by construction at temperature 0.
"Fixed temperature" and "measure variance" are compatible only above 0.

**Reference baseline.** `read_total_only` scores **0.330** mean on the
validation split (`results/verifier_selftest.json`): the score for reading the
single largest number on the page and shotgunning the rest. Any tier near this
has demonstrated little.

## Primary outcome

The **condition delta**, `reward(ocr_text) - reward(image)`, per tier. This
decomposes total error into a reading component and a
reasoning/formatting component, which a single accuracy number cannot.

## Secondary outcome, pre-registered for S5

**Cost per correct document**, per tier and condition:

    measured_cost_usd / (documents with doc_exact_match == 1)

Computed from exact `num_input_tokens` and `num_output_tokens` recorded on every
trace, priced at the rates in `provenance/MODEL_TIERS.md`. Spend is measured,
never estimated. Reported alongside cost per document and mean reward, so the
routing argument in S5 is decided on measured numbers.

## Claude's predictions

Stated before any run on `test`. Point estimates, scored against the full run.

### P1. Mean reward by tier and condition

| tier | ocr_text | image |
|---|---|---|
| small (qwen3.5-9b) | 0.74 | 0.46 |
| mid (qwen3-vl-30b-a3b) | 0.82 | 0.63 |
| frontier (claude-opus-5.5) | 0.90 | 0.81 |

### P2. The condition delta widens as models get smaller

Predicted delta: small **0.28**, mid **0.19**, frontier **0.09**. Reading the
page, not reasoning about it, is where small models lose most. If the deltas
come out roughly equal across tiers, this prediction is wrong and the headroom
story changes substantially.

### P3. The dominant failure is inventing `subtotal`

Emitting a `subtotal` on receipts that print only a total will be the single
largest contributor to `scalar_fp` across all three tiers, exceeding every
other scalar error category. Observed in 2 of 3 smoke rollouts. Scored on
`test` by counting `scalar_fp` attributable to `subtotal`.

### P4. The small model in the image condition lands near the lazy baseline

Small-tier `image` mean reward will be within **0.15** of the 0.330
`read_total_only` baseline. If true, the honest reading is that a 9B model
given a receipt photograph is barely beating "find the biggest number."

### P5. Format compliance is not the bottleneck

All three tiers produce parseable JSON matching the schema on **more than 95%**
of rollouts (`format_tier` in `clean`, `fenced`, or `embedded`). Prediction:
schema compliance explains almost none of the tier gap, and anyone attributing
small-model failure to "it can't follow the format" is wrong.

### P6. Document exact match is far lower than mean reward

`doc_exact_match` on `ocr_text`: small below **0.15**, frontier below **0.45**.
Partial credit hides how rarely a whole receipt is fully correct, which matters
for any workflow that cannot tolerate a single wrong field.

### P7. Line-item name transcription is a measurable slice of item error

On `image`, `line_item_f1_fuzzy_names` exceeds strict `line_item_f1` by at least
**0.05** for every tier, meaning a real share of item failures are name
transcription rather than missed items.

## Sean's predictions

Supplied by Sean before any run on `test`, drawn from his production experience
leading DocIQ at Capital One. These are his, not Claude's.

### S1. Frontier ceiling

`anthropic/claude-opus-5.5` scores at least **0.90** mean reward on `ocr_text`
and at least **0.85** on `image`. No model reaches 0.95, because line items cap
it.

### S2. Line items are the hardest field for every tier

`line_item_f1` is the lowest-scoring reward component for all three models.
Names, quantities, and multi-line items are where extraction breaks in
production too.

### S3. Inventing values shrinks with scale but does not disappear

The frontier model still emits at least one value not printed on the receipt on
at least **5%** of documents. Scored from `grounding`: documents where
`values_grounded < values_emitted`.

### S4. OCR beats images for small models; images match or beat OCR for frontier

OCR text helps a 9B model, but a frontier model reads the image better than OCR
transcribes it, so OCR errors become a handicap. Predicted condition delta
(`ocr_text` minus `image`): **positive for small, zero or negative for
frontier**.

This is the Textract-versus-vision-model question, as a falsifiable claim.

### S5. Cost per correct document favors the mid tier

The frontier tier costs at least **20x** more per document than the mid tier
while scoring less than **0.15** higher. Therefore a router sending easy
documents to the mid tier wins on cost per correct document.

## Registered disagreement: S4 contradicts Claude's P2

This is deliberate and worth preserving, because the two predictions cannot both
be right.

| | small delta | frontier delta |
|---|---|---|
| Claude P2 | +0.28 | **+0.09** (OCR still better) |
| Sean S4 | positive | **<= 0** (image equal or better) |

Both agree the small tier does better on OCR text. They disagree on the
frontier: Claude predicts OCR remains an advantage at every scale, Sean predicts
the advantage inverts because a frontier model reads the page better than the
OCR engine transcribes it. The frontier condition delta decides it, and whoever
is wrong produces the more interesting paragraph.

## A priori note on S5, recorded before results

S5 may be harder to satisfy than its price ratio suggests, and this is noted now
so it cannot look like hindsight. On list price the frontier tier is 20x the mid
tier on input ($4.00 vs $0.200 per Mtok) and 28.6x on output ($20.00 vs $0.700),
so "at least 20x per document" is nearly automatic in the `ocr_text` condition.

The `image` condition may not cooperate. Measured on an identical 8x8 PNG,
`anthropic/claude-opus-5.5` consumed **15** prompt tokens while
`qwen/qwen3-vl-30b-a3b-instruct` consumed **77** (`provenance/image_support.json`).
If that roughly 5x ratio holds on real receipts, the frontier tier's token
count per image is far lower, which could compress the effective cost ratio
well below 20x. S5 could therefore be true on OCR text and false on images.
The pilot measures real per-model image tokenization, so this resolves on data.

## Decision rules, fixed in advance

1. **Pilot first.** 20 documents, 3 samples, both conditions, all tiers, on
   `validation`. Its only purposes are to measure real per-model image
   tokenization and to confirm spend matches forecast. **No claim is drawn from
   the pilot.**
2. **Full-run sizing comes from measured pilot cost**, not from the forecast. If
   the measured projection for 100 docs x 10 samples exceeds the authorized
   budget, frontier sampling drops to 5 and pass@k is reported at k<=5 across
   all tiers for comparability. That fallback is chosen now, not after seeing
   results.
3. **No manual intervention on a live run.** Changes wait for the next run.
4. **A failed rollout is reported, never silently retried into the numbers.**
   Rollout counts are reported as ok/total per cell.
5. **Every prediction above is scored and reported, including the ones that
   fail.** A prediction that fails is a finding.

## Known limitations, stated in advance

- CORD receipts are predominantly Indonesian. Results transfer as
  document-understanding findings, not as a claim about any particular
  document mix.
- CORD has no merchant name and no date, so those fields are out of scope.
- The small-to-mid comparison **confounds scale with model family**, because
  `qwen/qwen3-vl-8b-instruct` is listed in Prime's catalog but is not callable
  (FRICTION.md F-011). The intended same-family 8B-to-30B scaling comparison
  was not available.
- Arithmetic consistency is reported as a metric and never rewarded, because
  CORD's own ground truth fails it on roughly 9% of evaluable documents
  (`docs/DATA_NOTES.md`).
- n=100 documents is the dataset's clean held-out ceiling, not a budget choice.


---

## Deviations

Recorded as required. Each entry says what changed, why, and whether any
result on the `test` split had been seen (none had).

### D1. 2026-11-05 22:25 EST — harness specified; first pilot discarded

**Change.** The locked design did not name a harness. It now specifies
`null`, implemented as an exported `NullHarness` subclass so it is the
package default.

**Why.** `vf-run` defaults to the `bash` harness, which prepends a coding-agent
system prompt and exposes tools. The first pilot therefore measured a different
task than the one specified. `qwen/qwen3-vl-30b-a3b-instruct` scored 0.0000 on
all 60 rollouts; the other two tiers were contaminated but scored plausibly.
See FRICTION.md F-015.

**Disposition.** The first pilot is discarded, retained at
`outputs/INVALID-bash-harness/` and
`results/INVALID_pilot_validation_bash_harness.json`. The pilot ran on
`validation`, the dev set. **No `test`-split result had been produced, so no
prediction was made or amended with knowledge of claim data.**

**Not a prediction change.** P1 to P7 and S1 to S5 are unaltered.

### D2. 2026-11-05 22:25 EST — RL target changed to `Qwen/Qwen3.5-4B`

**Change.** The conditional training phase will target `Qwen/Qwen3.5-4B` rather
than a text-only Llama, and needs no fourth eval tier.

**Why.** Prime's training runs support in-run evals
(`[[orchestrator.eval.source]]`, base model evaluated before the first step), so
the before/after numbers do not require the public inference API. That reopens
the Qwen3.5 sizes, which are trainable but not servable. `Qwen3.5-4B` is
natively vision-capable and in the same family as the small eval tier, which the
Llama was not. See `docs/RL_FEASIBILITY.md`.

**Disposition.** Decided before any `test`-split run. The eval tiers in the
locked design are unchanged; this concerns only the conditional training phase.

### D3. 2026-11-05 22:31 EST — test-split hygiene during training, and cross-path comparability

Locked **before** any training run is dispatched.

#### Test split is not evaluated during training

In-run evals (`[[orchestrator.eval.source]]`) point at **`validation` only**.
The `test` split is never evaluated during training, so checkpoint selection
cannot tune on it.

- **Checkpoint selection:** the checkpoint is chosen on `validation`, by the
  in-run eval at `orchestrator.eval.interval = 25`.
- **Test is run exactly once**, on the single selected checkpoint, after
  training completes. One number, reported whatever it says.
- If the chosen checkpoint turns out worse than the base model on `test`, that
  is the result. No second checkpoint is tried against `test`.

Verified in `configs/rl_qwen3.5-4b.toml`: both the train source and the eval
source name `split`, train uses `train` (limit 300), eval uses `validation`
(limit 100). The config passes `prime train validate` against hosted runtime
commit `0956a8858005019b7b16d26898142063ec1bb5e8`.

#### Comparability of the 4B's in-run numbers with the gateway tiers

The 4B's before/after comes from Prime's **training-side** inference, while the
three eval tiers ran through the **public gateway**. These are different serving
paths, so the numbers are not automatically comparable.

What is pinned identical, and confirmed accepted by the hosted schema:

| | gateway eval run | in-run eval |
|---|---|---|
| prompt | `prompts.py` v1.0.0 | same taskset, same prompt |
| harness | `null` (`DocExtractionHarness`) | `env.agent.harness.id = "null"` |
| temperature | 0.7 | `env.agent.sampling.temperature = 0.7` |
| scoring | this package's `@vf.reward` methods | same taskset, same rewards |
| condition | `ocr_text` / `image` | `ocr_text` |

What **cannot** be pinned: the inference server itself (in-run vLLM versus the
gateway's serving stack), and any chat-template or tokenizer differences between
them.

**Therefore:** the 4B's before/after delta is valid on its own terms, since both
sides come from the same path. Placing the 4B's absolute score beside the 9B or
Opus requires the calibration below, and without it the cross-path comparison is
reported with an explicit caveat and **not** used as a headline number.

#### Calibration run, optional and costed

`Qwen3.5-9B` is the only model present in **both** the training cache
(`Qwen/Qwen3.5-9B`) and the inference gateway (`qwen/qwen3.5-9b`). So:

1. Dispatch a short run on `Qwen/Qwen3.5-9B` with the same eval source.
2. Read its **step-0** eval, which is the base model on the training-side path.
3. Compare to the 9B's measured gateway score on the same documents.

The difference is the cross-path calibration constant, measured rather than
assumed. If it is small, the 4B can be placed beside the other tiers directly.
If it is large, that is itself a finding worth reporting: two serving paths on
one platform disagreeing about the same model.

Cost: full-parameter 9B needs more than one 80GB card, so this needs roughly
3 GPUs (2 train + 1 inference) for a short run. At \$3.89/GPU-hr that is about
**\$6 for half an hour**. Not dispatched without explicit approval.

**Still unconfirmed until first dispatch:** that `[orchestrator.eval]` runs on
hosted (the hosted doc examples never show it, though the schema accepts it),
and that the step-0 base eval fires for RL as it is documented to for SFT. If
step-0 does not fire, the "before" number must come from a separate eval-only
dispatch, and that changes the cost.

### D4. 2026-11-05 22:38 EST — quantity-aware item-name normalization

**Change.** `item_name()` now strips a leading integer token from a line-item
name, but only when that integer equals the item's declared `quantity`.
Applied symmetrically to prediction and ground truth.

**Why, with the mechanism measured on the dev split.** 45% of
`qwen/qwen3-vl-30b-a3b-instruct`'s predicted item names began with a digit:
it emitted `"1 REAL GANACHE"` *and* `quantity: 1`, duplicating the quantity
into the name. The item and the price were correct. Strict matching scored
those items zero, costing 35% of the rubric for a formatting convention rather
than an extraction error.

The equality condition is the safeguard: a genuine name beginning with a
number, such as "3 Cheese Pizza" on a single-unit line, is untouched because
3 != 1. Covered by tests.

**Effect, measured by re-scoring the saved dev-split traces (no new model
calls):**

| cell | total before | total after | line_item_f1 before | after |
|---|---|---|---|---|
| frontier ocr_text | 0.9448 | 0.9448 | 0.8833 | 0.8833 |
| frontier image | 0.9355 | 0.9355 | 0.8833 | 0.8833 |
| mid ocr_text | 0.7144 | 0.8136 | 0.4899 | 0.7732 |
| mid image | 0.8058 | 0.8233 | 0.7150 | 0.7650 |
| small ocr_text | 0.7734 | 0.7831 | 0.6792 | 0.7069 |
| small image | 0.7547 | 0.7547 | 0.7500 | 0.7500 |

**Why this is a fix and not a loosening:** the frontier tier is unchanged to
four decimal places on both conditions. It never duplicated the quantity, so
there was nothing to recover. A change that raised every tier would be evidence
of a weakened verifier; a change that moves only the tiers exhibiting the
specific formatting behaviour is evidence of a corrected one. Ground truth
still scores 1.0 on all 100 dev documents and all three self-test gates pass.

**This overturns the primary outcome on the dev split.** Before the fix the mid
tier appeared to do markedly better on images than on OCR text (delta -0.091).
After the fix that gap nearly vanishes:

| tier | delta before | delta after |
|---|---|---|
| small | +0.0187 | +0.0284 |
| mid | **-0.0914** | **-0.0097** |
| frontier | +0.0093 | +0.0093 |

So the apparent "images beat text at mid scale" result was almost entirely an
artifact of my own name matching. Had the claim run gone first, the headline
would have been an artifact.

**Disposition.** Decided on dev-split evidence, before any `test`-split run.
Predictions P1 to P7 and S1 to S5 are unaltered. The dev numbers above are
calibration, not claims.

### D5. 2026-11-06 — CORD list-valued annotation fields fused into one number

Found **after** the claim run finished, by a gate that had never been run on
the claim split. Reported here with the before and after on every cell.

**The bug.** CORD repeats an annotation when a field is printed more than once,
so `sub_total.subtotal_price` arrives as a *list*. `parse_ground_truth` passed
the list to `amount()`, which stringified it and fused the digits:

| document | CORD annotation | parsed as | correct |
|---|---|---|---|
| `test-013` | `["46.636", "46.636"]` | 4663646636 | 46636 |
| `test-099` | `["6,818", "0"]` | 68180 | 6818 |

On those two documents a model emitting the **correct** value was scored wrong.

**Why the dev split could not catch it.** No `validation` document has a
list-valued *scored* scalar (`provenance/cord_duplicate_fields.json`: 1
affected validation document, and its affected fields are `creditcardprice`,
`etc` and a `menu.nm`, none of which is scored). Gate 1 passed 100/100 on
`validation` and was never run on `test`, because `test` was being held
untouched. Holding the claim split back protected it from tuning and hid a
parser bug in it.

**One of the two was silent even to the gate.** `test-013` was caught because
4663646636 appears nowhere on the receipt, so the grounding check failed it.
`test-099`'s fused tax, 68180, happened to equal that receipt's subtotal, so it
*looked* grounded and gold scored a clean 1.0000. The gold gate catches a
corrupted ground truth only when the corruption makes a value ungrounded. That
is a real limit of the check, not a property of this dataset.

**Fix.** First element for numeric fields, space-join for names (CORD
`validation-037` carries `nm: ["-", "Gyro Platter Regular"]`, where the first
element alone would be `"-"`). Three regression tests, named after the real
documents. Gate 1 now runs on **every split**, which is the durable fix:
`scripts/04_verifier_selftest.py` reports `validation` and `test` separately
and both must be 1.0.

**Effect on the claim numbers**, measured by re-scoring all 6,000 saved
rollouts against re-parsed ground truth with no model calls
(`scripts/12_rescore_fixed_truth.py`, `results/rescore_fixed_truth.json`):

| cell | before | after | delta |
|---|---|---|---|
| small ocr_text | 0.7194 | 0.7214 | +0.0020 |
| small image | 0.7064 | 0.7090 | +0.0026 |
| mid ocr_text | 0.7949 | 0.7974 | +0.0025 |
| mid image | 0.8107 | 0.8132 | +0.0025 |
| frontier ocr_text | 0.9005 | 0.9030 | +0.0025 |
| frontier image | 0.9093 | 0.9118 | +0.0025 |

On the 2 affected documents alone the gain is about +0.125 per cell. Spread
over 100 documents it is +0.0025, and it is **the same for every tier**, so no
tier ordering, condition delta, or prediction verdict changes sign. Reported
because it happened, not because it mattered.

**Disposition.** The claim numbers are the corrected ones
(`results/full_test_fixed.json`, analysed in
`results/analysis_full_test_fixed.json`). The uncorrected run is retained at
`results/full_test.json`. No model was re-run, no checkpoint was selected on
`test`, and no prediction was amended: all twelve were scored once, on the
corrected data, in `results/prediction_scorecard.json`.

### D6. 2026-11-06 — thousands separator together with cents parsed 100x too large

Found the same day as D5, by the failure taxonomy rather than by a gate, and
it is the more serious of the two because **it scored correct model output as
wrong at every tier, including the frontier.**

**How it surfaced.** The taxonomy counts a "magnitude" category: a predicted
value that is an exact power of ten away from ground truth. The 100x row came
out at exactly 20 rollouts in nearly every cell, frontier included. Twenty
rollouts is two documents times ten samples, and when all three tiers agree
against the label on the same two documents, the label is the suspect.

**The bug.** CORD mixes separator conventions inside one dataset:

| document | prints | old parse | correct | every model answered |
|---|---|---|---|---|
| `test-047` | `63,000.00` | 6300000 | 63000 | 63000 |
| `test-067` | `9.500,00` | 950000 | 9500 | 9500 |

`parse_amount` matched a trailing 2-digit subunit only against the *whole*
string, so a value carrying both a thousands separator and cents fell through
to stripping every separator. The Indonesian majority convention (`60.000` is
sixty thousand) was handled; comma-thousands-with-cents and the European
`9.500,00` were not.

**Fix.** One rule for every convention: split on separators, drop a final group
of exactly two digits as a subunit, keep a final group of three as a thousands
group. Four regression tests, including two that pin the majority convention so
the fix cannot reinterpret it.

**Why neither gate caught it.** Gate 1 compares ground truth against itself, so
a mis-parse that is *consistent* between the truth record and the OCR digit set
is invisible to it: `6300000` was wrong but self-consistent, and the OCR digit
candidates already offered `63000`, so grounding passed too. Gate 2 and 3
corrupt a prediction and check the score falls, which this does not touch. The
check that found it was the failure taxonomy, where an implausible pattern in
the *frontier* column was the signal. A gate proves the verifier is
self-consistent; it does not prove the verifier is right.

**Effect on the claim numbers** (re-scoring all 6,000 saved rollouts, both D5
and D6 applied, no model calls):

| cell | before | after | delta |
|---|---|---|---|
| small ocr_text | 0.7194 | 0.7272 | +0.0078 |
| small image | 0.7064 | 0.7169 | +0.0105 |
| mid ocr_text | 0.7949 | 0.7985 | +0.0036 |
| mid image | 0.8107 | 0.8203 | +0.0096 |
| frontier ocr_text | 0.9005 | 0.9121 | +0.0116 |
| frontier image | 0.9093 | 0.9208 | +0.0116 |

On the 4 affected documents the frontier gains +0.29, the largest correction of
any tier, because it was the tier most often right about them. Document exact
match on frontier ocr_text moves 0.654 to 0.674.

**What it changes.** No prediction verdict flips and no tier ordering changes.
S1's frontier-on-OCR claim moves from 0.9005, which sat on its 0.90 threshold,
to 0.9121, which clears it more comfortably, though the interval still spans
it. The direction of every condition delta is unchanged.

**Disposition.** Claim numbers are the corrected ones. Both bugs are recorded
with their before and after rather than silently folded in, and the uncorrected
run is retained at `results/full_test.json`.

### D7. 2026-11-06 — post-hoc prompt variant, pre-registered before dispatch

**Status at the time of writing: not yet run.** This section is committed
before the model call, which is the only thing that makes it a prediction.

**What changes.** One sentence is added to the Rules block of the system
prompt, and nothing else (`tests/test_prompts.py` pins that the variant adds
exactly one line and removes none):

> Report "subtotal" only when the receipt prints a subtotal line of its own. If
> the receipt prints only a total, set "subtotal" to null, even when a subtotal
> would equal that total.

**Why.** The headroom ablation measured that forgiving an invented `subtotal`
is worth +0.0379 to the mid tier and +0.0001 to the frontier
(`results/headroom_ablations.json`). That asymmetry is the study's evidence
that the failure is an ambiguous specification rather than a reading error.
An ablation is a counterfactual in the scorer, though, not a measurement of a
model. This run tests the claim where it would actually be fixed: in the
prompt.

**Scope.** One cell: mid tier (`qwen/qwen3-vl-30b-a3b-instruct`), `ocr_text`,
test split, 100 documents, 10 samples, T=0.7, harness null. Forecast $0.20,
from the $0.19528 the identical baseline cell measured. One run. No second
variant and no iteration on the wording: if the result is disappointing, that
is the result.

**Test-split reuse, declared.** The test split now has two uses. Use 1 is the
claim run and is the sole source of every number in the claim table and the
prediction scorecard. Use 2 is this variant, reported in its own section and
labelled post-hoc. The variant is not compared across tiers, does not enter
the claim table, and does not change any scorecard verdict. The prompt-fixed
cell is not a competitor to the frontier number, because the frontier was
never offered the same sentence.

**Baseline to beat**, mid `ocr_text` on test, corrected for D5 and D6
(`results/analysis_full_test_fixed.json`):

| quantity | baseline |
|---|---|
| mean reward | 0.7985 |
| scalar F1 | 0.8353 |
| document exact match | 0.360 |
| `invented_subtotal` | 282 / 1000 rollouts |
| `missed_subtotal` | 0 / 1000 rollouts |
| `wrong_subtotal` | 9 / 1000 rollouts |
| ablation upper bound | 0.8365 (+0.0379) |

**Predictions, in order of what they would teach.**

- **D7-A, primary.** Mean reward rises to between 0.8135 and 0.8365, a gain of
  +0.0150 to +0.0379: somewhere between 40% and 100% of the ablation bound.
  Point prediction +0.0250. A prompt sentence should recover most but not all
  of a counterfactual that forgives the error outright.
- **D7-B.** `invented_subtotal` falls below 100 of 1,000 rollouts, from 282.
- **D7-C, the risk.** `missed_subtotal` rises from 0, because a model told to
  suppress an unprinted subtotal may also suppress a printed one. It stays at
  or below 40 of 1,000. Above 40, the sentence over-corrects and the net gain
  is smaller than the invented-field drop suggests.
- **D7-D.** Document exact match rises from 0.360 to between 0.380 and 0.420.

**Decision rules, fixed in advance.**

1. Gain below +0.010: the ablation overestimated what a prompt can recover,
   and the specification framing is reported as partly wrong. The headroom
   numbers stay as upper bounds and lose their claim to be reachable.
2. Gain of +0.030 or more: the specification diagnosis is confirmed, and the
   headroom table is reported as reachable, not merely as an upper bound.
3. Between +0.010 and +0.030: partial. Reported as a specification gap that a
   prompt closes only in part, with the residue named.
4. Uncertainty is a paired bootstrap over the 100 documents against the
   baseline cell, 10,000 resamples, seed 20261106, the same procedure as every
   other delta in this study. A gain whose interval spans zero is reported as
   spanning zero whatever its point estimate.

#### D7 result, 2026-11-06

Run complete: 1,000/1,000 rollouts ok, $0.2024 measured against a $0.20
forecast, 4,544s. Scored by `scripts/18_score_d7.py` into
`results/d7_scorecard.json`. The run stamp reads `7cfb7f1-DIRTY`; the dirty
marker is the smoke test's own outputs, and `git diff 7cfb7f1 HEAD -- src/` is
empty, so the taskset and the scorer are byte-identical to the pre-registered
commit.

| quantity | baseline | variant | change |
|---|---|---|---|
| mean reward | 0.7985 | 0.8301 | **+0.0316** |
| scalar F1 | 0.8353 | 0.9014 | +0.0661 |
| line-item F1 | 0.7363 | 0.7310 | -0.0054 |
| grounding | 0.7660 | 0.7910 | +0.0249 |
| document exact match | 0.3600 | 0.4970 | **+0.1370** |
| `invented_subtotal` | 282 | 53 | -229 |
| `missed_subtotal` | 0 | 0 | 0 |
| `wrong_subtotal` | 9 | 6 | -3 |

Mean reward gain **+0.0316, 95% CI [+0.0176, +0.0460], excluding zero**.
Exact match gain **+0.1370 [+0.0700, +0.2080], excluding zero**.

**Decision rule 2 fires.** The gain is at or above +0.030, so the
specification diagnosis is confirmed and the headroom table is reported as
reachable rather than only as an upper bound. The sentence recovered 83% of
the +0.0379 the ablation said was available.

**Predictions: 2 hit, 2 miss.**

- **D7-A HIT.** +0.0316, inside the predicted +0.0150 to +0.0379.
- **D7-B HIT.** `invented_subtotal` fell to 53 of 1,000, below the predicted
  100.
- **D7-C MISS, and the interesting one.** I predicted the sentence would
  over-correct, suppressing some genuinely printed subtotals, and that
  `missed_subtotal` would rise from 0 to at most 40 of 1,000. It stayed at
  exactly **0**. There was no precision-recall trade at all: the model was not
  confused about which receipts print a subtotal, only about whether to report
  one that is not printed. That distinction is what makes this a specification
  gap rather than a reading gap, and the prediction that failed is what
  demonstrates it.
- **D7-D MISS, by a wide margin in the model's favour.** I predicted exact
  match between 0.380 and 0.420; it reached **0.4970**. Exact match is
  all-or-nothing per document, so one spurious field is enough to lose it:
  removing a single error class flips far more documents to perfect than its
  weighted reward contribution suggests. A +0.0316 reward gain carried a
  +0.1370 exact-match gain, a 38% relative improvement on the metric a user of
  such a system would actually care about.

**What it changes.** The mid tier's OCR reward moves 0.7985 to 0.8301, so the
frontier-over-mid gap narrows from 0.1136 to 0.0820: **one sentence closed 28%
of it** for $0.2024. Stated carefully, because the comparison is not
like-for-like: the frontier was never offered the same sentence. The ablation
puts its gain from the same change at +0.0001, so a fair re-run would move the
frontier almost not at all, but that run was not made.

**What it does not change.** No claim-table number, no condition delta, no
prediction verdict from the main study. The claim table remains the first use
of the test split. Line-item F1 moved -0.0054, the one component that did not
improve, which is consistent with the sentence touching only the `subtotal`
decision.
