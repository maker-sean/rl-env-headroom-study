# Short literature review

Five real papers, and what this study adds to each.

**Depth of reading, stated so the citations are not overclaimed.** These were
located by web search on 2026-11-06 and read at the level of abstract, arXiv
listing page, and the search engine's extracted fragments. They were not read
in full. Where a number appears below it is the paper's own reported figure as
surfaced by that search, not a figure this study verified. Nothing in this
study's results depends on any of them.

---

### 1. CORD: A Consolidated Receipt Dataset for Post-OCR Parsing
Park et al., NeurIPS 2019 Document Intelligence Workshop.
<https://mlanthology.org/neuripsw/2019/park2019neuripsw-cord> ·
<https://github.com/clovaai/cord>

The dataset this study runs on: 1,000 Indonesian receipts, 800/100/100, CC-BY-4.0.
The repository notes that some label classes from the original paper were
removed before release for Indonesian legal reasons.

**What this study adds.** Two ground-truth defects in the released `test` split
that bear on anyone scoring against it: annotation fields are *list-valued*
when a field is printed twice (`subtotal_price: ["46.636", "46.636"]`), and the
split mixes separator conventions, carrying `63,000.00` and `9.500,00`
alongside the Indonesian `60.000`. Both silently corrupt a naive parser, and
both are recorded with document ids in `provenance/cord_duplicate_fields.json`
and deviations D5 and D6. Separately, roughly 9% of `test` documents print more
item lines than the annotation records, usually zero-priced bundle components,
so line-item F1 against CORD has a ceiling set by the labels rather than by the
model. A model that reads those lines is marked wrong for being right.

### 2. OCR-free Document Understanding Transformer (Donut)
Kim et al., arXiv:2111.15664, ECCV 2022. <https://arxiv.org/abs/2111.15664>

Argues the OCR-then-parse pipeline carries avoidable cost, language
inflexibility, and error propagation, and maps the document image straight to
structured output instead. CORD is one of its benchmarks, so this is the
dataset's own lineage.

**What this study adds.** Donut's premise, that pixels beat an OCR hand-off, is
tested here as a controlled A/B on the *same* documents with the same prompt,
against three general-purpose models rather than a trained document model. The
answer is that it does not matter: the condition delta is statistically
indistinguishable from zero at every tier (small +0.0103, mid -0.0218,
frontier -0.0087, all 95% intervals spanning zero, paired bootstrap over 100
documents). The error that OCR propagates and the error a vision model makes
are, on this task, the same size. That is a null result against a widely
assumed effect, and it is the study's primary outcome.

### 3. Tülu 3: Pushing Frontiers in Open Language Model Post-Training
Lambert et al., arXiv:2411.15124. <https://arxiv.org/abs/2411.15124>

Introduces Reinforcement Learning with Verifiable Rewards: replace the learned
reward model with a programmatic check, on tasks whose outcomes can be verified,
such as mathematics and instruction following.

**What this study adds.** A verifiable reward for a task where the verifier is
the hard part. Mathematics has one right answer; a receipt has a schema, fuzzy
item names, locale-dependent numbers, and ground truth that fails its own
arithmetic on about 9% of documents. The contribution is the adversarial
pass: the reward was attacked before any model ran, and two hacks were found
and closed (an empty prediction earned full grounding credit, and dumping every
digit on the page earned perfect grounding precision), with a documented
degenerate floor of 0.050 and a reference baseline of 0.330 for reading only
the total. The broader finding is about the limits of such gates: three gates
passed on 100 documents while the verifier was still wrong, because a gate
proves self-consistency, not correctness. The bug that mattered was found by
noticing an implausible pattern in the *frontier* column of a failure taxonomy.

### 4. OmniDocBench: Benchmarking Diverse PDF Document Parsing
Ouyang et al., arXiv:2412.07626, CVPR 2025. <https://arxiv.org/abs/2412.07626>

Multi-level document-parsing evaluation across nine document types, scoring
pipeline tools and end-to-end VLMs with edit distance, CDM, and TEDS.

**What this study adds.** Decision metrics rather than parsing-quality metrics.
Edit distance says how close a parse is; it does not say whether a document can
be processed without a human. This study reports document exact match
(frontier 0.674 on OCR text, against a mean reward of 0.912, so partial credit
hides how rarely a whole receipt is right), pass@k from 10 samples at fixed
temperature, within-document variance, and cost per *correct* document rather
than per call. The last one changes the answer: on list price the frontier tier
is 41x the mid tier per document, but because it is right more often, it is
only about 22x per correct document. Both framings support routing, and the
honest one is weaker than the headline.

### 5. Pixels for Programs? A Cross-Provider Case Study of Input-Token Accounting
Bhalgami, arXiv:2607.21672. <https://arxiv.org/abs/2607.21672>

Measures provider-reported input tokens for the same content as text and as an
image across providers, reports image-to-text ratios of 0.135, 0.194 and 0.242,
and is careful that this is an accounting artifact, not a compute or money
saving.

**What this study adds.** The same accounting problem on the cost axis this
study has to price, and in the opposite direction. Measured on an identical
8x8 PNG through one gateway, `claude-opus-5.5` was billed 15 prompt tokens
where `qwen3-vl-30b-a3b-instruct` was billed 77, a 5x spread
(`provenance/image_support.json`). That was pre-registered as a threat to
prediction S5, because a frontier model billed far fewer image tokens could
compress the cost ratio below the 20x the prediction required. On real
receipts the spread did not hold: 1,529 against 1,142 input tokens per call,
1.34x, and the cost ratio stayed at 33.9x in the image condition. Recorded
because the prediction was pre-registered with that risk named in advance.

---

## What the study adds overall

One sentence: the measurable gap on this task is **scale**, not input modality,
and the expensive half of building the environment was the verifier, not the
agent.

- **A null primary outcome**, pre-registered, with intervals. Condition does
  not matter at any tier; tier gaps do (frontier over mid +0.1136
  [+0.0825, +0.1459] on OCR text).
- **A failure taxonomy that found a verifier bug the gates could not**, which
  is the transferable methodological point.
- **A locale failure mode that is purely a scale story**: an Indonesian
  thousands separator read as a decimal point, costing a factor of 1,000, on
  14% of 9B rollouts, 0.4% of 30B rollouts, and 0 of 2,000 frontier rollouts.
- **Hallucination is close to absent at the frontier** on this task
  (mean per-rollout grounding precision 0.9992, an ungrounded value on 1% of
  documents), which
  refuted a pre-registered prediction of at least 5%. The frontier's remaining
  grounding loss is over-extraction of numbers that *are* on the page, not
  invention, and those are different product problems.
