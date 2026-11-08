# How much of the gap between a small model and a frontier model is the model, and how much is the way you asked?

A single-turn RL environment for structured field extraction from real
receipts, built on [Prime Intellect's `verifiers`](https://github.com/PrimeIntellect-ai/verifiers)
v1 with a verifiable reward and a verifier that is tested before any model
runs. 6,000 scored rollouts across three model tiers and two input modalities,
with predictions committed before dispatch.

**Environment on the Prime Intellect Hub:**
[`maker-sean/doc-extraction-study`](https://app.primeintellect.ai/dashboard/environments/maker-sean/doc-extraction-study)

The headline result is that a measurable share of the open-weight model's
deficit was not capability at all. It was my prompt being ambiguous in a way
the frontier model happened to resolve correctly. I measured that share by
re-scoring saved rollouts, predicted what fixing it would recover, wrote the
prediction down, fixed the prompt, and re-ran. The fix delivered 83% of the
predicted ceiling for $0.20.

## The question

Document extraction is usually reported as a single accuracy number, which
cannot tell you whether a model failed because it could not read the page or
because it did not understand what you asked for. Those have opposite
remedies: one needs training data, the other needs a better specification.

So the environment runs the same 100 held-out documents two ways, with one
fixed prompt:

- `ocr_text` gives the model the document's OCR words
- `image` gives the model the photograph

and the reward is decomposed per field, so every failure can be attributed
rather than averaged away.

## Results

Three tiers, two conditions, 100 held-out documents, 10 samples each at
T=0.7. Every table below is generated from the files in
[`results/`](results/) by
[`analysis/regenerate_tables.py`](analysis/regenerate_tables.py). Nothing here
is typed by hand.

<!-- BEGIN GENERATED: regenerate_tables.py -->

### Mean reward, and the effect of input modality

| tier | model | OCR text | page image | image minus OCR | 95% CI |
|---|---|---|---|---|---|
| Qwen3.5-9B | `qwen/qwen3.5-9b` | 0.7272 | 0.7169 | +0.0103 | [-0.0192, +0.0416] |
| Qwen3-VL-30B-A3B | `qwen/qwen3-vl-30b-a3b-instruct` | 0.7985 | 0.8203 | -0.0218 | [-0.0475, +0.0044] |
| Opus 5.5 | `anthropic/claude-opus-5.5` | 0.9121 | 0.9208 | -0.0087 | [-0.0287, +0.0110] |

Every interval spans zero. Minimum detectable effect by tier: 0.0304 / 0.0259 / 0.0198. Paired bootstrap over the same 100 documents, 10,000 resamples, seed 20261106.

### Scale gaps, which do not span zero

| gap | condition | gap | 95% CI |
|---|---|---|---|
| frontier-mid | ocr_text | +0.1136 | [+0.0825, +0.1459] |
| mid-small | ocr_text | +0.0713 | [+0.0292, +0.1163] |
| frontier-mid | image | +0.1006 | [+0.0741, +0.1292] |
| mid-small | image | +0.1034 | [+0.0564, +0.1539] |

Tier ordering holds under 6 of 6 reward rubrics, so it is not an artifact of the weights chosen.

### Document exact match and pass@k

A document counts only when every field is right. pass@k is over the 10 samples drawn per document.

| tier | condition | n | exact match (pass@1) | pass@3 | pass@5 | pass@10 |
|---|---|---|---|---|---|---|
| Qwen3.5-9B | `ocr_text` | 1,000 | 0.300 | 0.390 | 0.433 | 0.500 |
| Qwen3.5-9B | `image` | 1,000 | 0.276 | 0.363 | 0.402 | 0.450 |
| Qwen3-VL-30B-A3B | `ocr_text` | 1,000 | 0.360 | 0.386 | 0.393 | 0.400 |
| Qwen3-VL-30B-A3B | `image` | 1,000 | 0.413 | 0.454 | 0.468 | 0.490 |
| Opus 5.5 | `ocr_text` | 1,000 | 0.674 | 0.684 | 0.688 | 0.690 |
| Opus 5.5 | `image` | 1,000 | 0.664 | 0.675 | 0.680 | 0.690 |

### How much of the gap was my specification, not the model

Re-scoring saved rollouts under one named change at a time. The ablations are deliberately generous, so these are upper bounds.

| gap on OCR text | measured | upper bound after spec fixes | share specification |
|---|---|---|---|
| frontier over mid | 0.1136 | 0.0700 | 38% |
| frontier over small | 0.1849 | 0.1465 | 21% |

Forgiving an invented `subtotal` is worth +0.0379 to the mid tier and +0.0001 to the frontier. A fix worth something to the smaller model and nothing measurable to the frontier is a fix to the task, not to the model.

### The fix, pre-registered and re-run on `mid|ocr_text`

| quantity | before | after | change | 95% CI |
|---|---|---|---|---|
| mean reward | 0.7985 | 0.8301 | +0.0316 | [+0.0176, +0.0460] |
| doc exact match | 0.3600 | 0.4970 | +0.1370 | [+0.0700, +0.2080] |
| invented `subtotal` | 282 | 53 | -229 | not bootstrapped |
| missed `subtotal` | 0 | 0 | +0 | not bootstrapped |

One sentence added to the prompt, prompt version `v1.1.0-subtotal`, cost $0.2024. Missed subtotals did not rise, so there was no precision-recall trade: that is the evidence this was a specification gap and not a reading one.

### What remains, and it is capability

Counts are **rollouts of 1,000 per cell** carrying at least one such error, on OCR text.

| error | Qwen3.5-9B | Qwen3-VL-30B-A3B | Opus 5.5 |
|---|---|---|---|
| value wrong by 1000x (locale separator) | 141 | 4 | 0 |
| missed `tax` | 75 | 62 | 0 |
| price wrong on a matched item | 155 | 99 | 6 |
| item name mismatch | 311 | 233 | 151 |
| invented `subtotal` | 254 | 282 | 21 |
| unparseable reply | 0 | 0 | 0 |

The mirror image: where the prompt *is* explicit, that `price` means the line total rather than the per-unit amount, **0 rollouts of 6,000 confused the two**, with 135 opportunities in the richest cell across 18 observable items. Silent prompt and the models diverge; explicit prompt and even the 9B complies.

### Pre-registered predictions, scored

| author | predictions | hit | partial | miss |
|---|---|---|---|---|
| Claude | 7 | 1 | 2 | 4 |
| Sean | 5 | 3 | 1 | 1 |

### Cost, reliability, and the verifier's own gates

- Claim run: 6,000 rollouts, 0 failures, $20.58.
- All runs in this repo: 7,423 rollouts across 20 logged runs, $23.08 total, itemised in [`results/spend.csv`](results/spend.csv).
- Verifier gate: ground truth scores 1.0000 on all 100 validation documents (min 1.0000, max 1.0000).
- Every corruption and gaming strategy scores below ground truth; see [`results/verifier_selftest.json`](results/verifier_selftest.json).

<!-- END GENERATED -->

## What the results mean

**Modality does not matter at this task, at any tier.** Every image-minus-OCR
interval spans zero, so the claim is "no effect larger than roughly 0.03,"
which is what 100 documents buys. The OCR hand-off that document-AI pipelines
exist to eliminate costs nothing measurable here. The prediction this tested
asked for +0.09 to +0.28 and was wrong.

**Scale matters everywhere, and that one survives the weights.** Re-scoring
all 6,000 rollouts under six different reward rubrics leaves the tier ordering
intact in all six. The modality null is less robust: it holds under all six at
the frontier but breaks under two at the mid tier.

**A third of the open-weight gap was specification, not capability.** On
receipts that print only a total, the mid tier emits a `subtotal` equal to that
total in 282 of 1,000 rollouts. My prompt never said whether to report a field
the document does not print. The frontier model resolved that ambiguity the
way CORD's annotators did, and the smaller model did not, which is
instruction-following wearing an extraction label. Adding one sentence to the
prompt moved mean reward +0.0316 and document exact match from 0.360 to 0.497,
and crucially it did not start suppressing subtotals that *were* printed, so
there was no precision-recall trade.

**What is left is capability, and it has a clear training target.** The locale
failure is the clean case: CORD receipts are Indonesian and print `60.000` for
sixty thousand, and the 9B emits `60.0`. Per 1,000 rollouts on OCR text that
error appears **141 times for the 9B, 4 times for the 30B, and 0 times for Opus
5.5**. No ablation recovers any of it, so it is not a specification problem,
and a wrong item name is a data-quality defect while a value wrong by 1000x is
a financial one. The target is a deterministic integer, the reward is
already per-field, and the unused 800-document `train` split covers it.

## The harness default that silently zeroed a pilot

The most expensive thing I learned, and it cost minutes to fix and a whole
pilot to notice.

`verifiers` v1 resolves a taskset's harness with `default_harness_id()`, which
returns `"bash"` unless the taskset's own package exports a `Harness` subclass.
For a single-turn extraction task the `bash` harness is actively wrong: it
prepends "You are a coding agent. You have access to a bash tool..." ahead of
the task's system prompt and hands the model tools it has no use for.

I specified no harness, because the task has no tools. The 30B made a tool
call, received an empty result, answered in prose, and scored **0.0000 on all
60 pilot rollouts**. That reads as "the open-weight model cannot do structured
extraction," which is a finding somebody would publish. The small and frontier
tiers still emitted JSON, so their numbers looked plausible while being
measured under a coding-agent system prompt. The whole pilot was discarded at a
cost of $1.25.

Every other problem in `FRICTION.md` announced itself and cost minutes. This
one produced a plausible number, which is the only kind of failure that can
corrupt a result rather than delay it. I caught it by reading the request
payload after the output looked too clean to be real.

This package therefore exports `DocExtractionHarness`, a `NullHarness`
subclass, in
[`src/doc_extraction_study/harness.py`](src/doc_extraction_study/harness.py),
so the correct harness is the default with no flag to remember. Verified
against the package as published, installed from the Hub into a clean
environment: `default_harness_id("doc-extraction-study")` returns
`doc-extraction-study`, not `bash`, and a run with no harness flag logs
`harness=doc-extraction-study`, one turn, `stop=agent_completed`, with a
nonzero reward.

**If you are building a toolless taskset on verifiers v1**, export a
`NullHarness` subclass or pass `--env.agent.harness.id null`. A 0.0000 that
looks like a weak model is worth one look at the request payload.

## Data provenance

[CORD v2](https://huggingface.co/datasets/naver-clova-ix/cord-v2), 1,000 real
photographed receipts, **CC-BY-4.0**, verified from two independent sources with
the license text archived in
[`provenance/DATASET_LICENSE.md`](provenance/DATASET_LICENSE.md).

CORD contains no merchant name and no date: its publishers removed those fields
before release. They are out of scope, and **no synthetic fields are injected**,
so every scored target is real ground truth. Measured field coverage and schema
quirks are in [`docs/DATA_NOTES.md`](docs/DATA_NOTES.md).

## Rubric

A weighted sum, as verifiers v1 requires. Invalid JSON scores zero on every
component.

| component | weight | what it measures |
|---|---|---|
| `scalar_f1` | 0.45 | F1 over (field, value) pairs. Absent is a value, so inventing a field is a false positive |
| `line_item_f1` | 0.35 | F1 over line items; a true positive needs both the name and the price |
| `grounding` | 0.15 | Fraction of emitted numbers that appear in the document, diluted if the model emits more values than the document contains |
| `schema_valid` | 0.05 | Produced well-formed JSON matching the schema |

**Arithmetic consistency is measured but never rewarded.** CORD's own ground
truth satisfies the line-item sum on only 91% of evaluable documents and the
subtotal chain on 94%, because Indonesian receipts use tax-inclusive pricing
with rounding. Rewarding consistency would penalize correct extractions.

Because the weights are a choice, [`results/weight_sensitivity.json`](results/weight_sensitivity.json)
re-scores every rollout under six rubrics and reports which conclusions survive.

## The verifier is tested before any model runs

Three gates, in [`results/verifier_selftest.json`](results/verifier_selftest.json):

1. **Ground truth scores 1.0 on all 100 validation documents.** Two real bugs
   in my own ground-truth parser were caught by this rule alone.
2. **Every applicable corruption scores below ground truth.** Corruptions that
   are no-ops on a given document are reported as not applicable rather than
   counted as passes.
3. **Degenerate strategies earn at most 0.20.** Two reward hacks were found and
   closed: emitting nothing scored a free 1.0 on grounding, and copying every
   digit on the page scored perfect grounding precision.

A fourth figure is a **reference baseline**, not a gate: `read_total_only`
scores 0.330. That is what a model earns for reading the biggest number on the
page and shotgunning the rest. Any model scoring near it has demonstrated
little.

Two further bugs in the ground-truth parser surfaced *after* the run, one of
which scored correct frontier output as wrong, after three gates had passed on
100 documents. A gate proves self-consistency, not correctness. So 20 of the
100 test documents were then checked by hand against the receipt images:
19 clean, 0 label bugs, and the one flagged turned out to be a column the
review tool had hidden. See
[`provenance/LABEL_AUDIT.md`](provenance/LABEL_AUDIT.md).

## Reproduce

```bash
uv sync && uv pip install -e .
```

Regenerate every table in this README from the committed results, and fail if
any number has drifted:

```bash
uv run python analysis/regenerate_tables.py --check
```

Run the tests and the verifier gates, neither of which spends anything:

```bash
uv run pytest && uv run python analysis/04_verifier_selftest.py
```

Re-run the models, which does spend money, roughly $20 at the prices recorded
in [`provenance/`](provenance/):

```bash
uv run python analysis/09_run_eval.py --split test --samples 10
```

## Limitations

Stated plainly, because several of them bound the headline claims.

- **This is an evaluation, not a training result.** No RL training was run. The
  claim that the locale failure is a training target is an argument from the
  reward's shape and the unused train split, not a measurement.
- **One dataset, one language family.** CORD receipts are predominantly
  Indonesian. These are document-understanding results, not a claim about any
  particular document mix.
- **100 test documents.** The minimum detectable effect is roughly 0.02 to 0.03
  depending on tier, so "no modality effect" means no effect above that, not
  no effect.
- **The hand audit is 20 documents.** Zero label errors in 20 puts the 95%
  upper bound on the label error rate near 14%. That is what 20 documents buy.
- **The small-to-mid gap confounds scale with model family.** The intended
  small tier was not servable, so the small tier is a different family. It is
  reported as a tier gap, never as a scaling law.
- **The headroom ablations are upper bounds by construction.** They are
  deliberately generous. The pre-registered prompt re-run exists to test one of
  them against reality, and recovered 83% of its bound.
- **CORD has been public since 2019**, so the frontier score could be partly
  memorization. Exact match at 0.674 and disagreement with CORD's literal item
  names argue against it. The test I did not run is to perturb the printed
  amounts and see which value comes back.
- **Exact match carries a dataset ceiling.** About 9 of 100 documents print
  more item lines than CORD annotates, so the frontier's 0.674 is not 0.326
  from solved.

## Pre-registration

[`PREREGISTRATION.md`](PREREGISTRATION.md) holds the predictions as written
before any model ran, with the deviations appended afterwards and labelled.
Twelve predictions, all twelve scored in
[`results/prediction_scorecard.json`](results/prediction_scorecard.json),
including the five that missed. The prompt-fix re-run was pre-registered
separately and committed before dispatch.

## Repo map

| path | what |
|---|---|
| `src/doc_extraction_study/scoring.py` | the verifier: pure, testable scoring |
| `src/doc_extraction_study/taskset.py` | the verifiers v1 taskset, both conditions |
| `src/doc_extraction_study/normalize.py` | amount, quantity, name normalization |
| `src/doc_extraction_study/cord.py` | CORD to a canonical record, OCR reconstruction |
| `src/doc_extraction_study/prompts.py` | the fixed prompt, versioned, plus the one variant |
| `tests/` | 101 unit tests, including gaming attempts |
| `analysis/` | probes, the self-test, the eval runner, and every scorer |
| `analysis/regenerate_tables.py` | rebuilds this README's tables from `results/` |
| `results/` | every figure quoted anywhere traces here |
| `provenance/` | dataset license, model catalog snapshot, label audit |
| `audit_review/` | the page used to hand-audit 20 receipts against their labels |
| `docs/DATA_NOTES.md` | measured dataset properties and what they forced |
| `docs/HEADROOM.md` | the headroom ablations and what each one bounds |
| `docs/RL_FEASIBILITY.md` | what a training run would cost and what blocks it |
| `FRICTION.md` | tooling friction found while building, with repro steps |

## License

MIT for the code in this repository, see [`LICENSE`](LICENSE). CORD v2 is
CC-BY-4.0 and is not redistributed here; the loader fetches it. If you use
CORD, cite it as its authors ask:

> Park, S., Shin, S., Lee, B., Lee, J., Surh, J., Seo, M., Lee, H. *CORD: A
> Consolidated Receipt Dataset for Post-OCR Parsing.* Document Intelligence
> Workshop at NeurIPS, 2019.

Built with Claude Code.
