# Can the RL phase actually run? Measured 2026-11-05 22:12 EST

All figures read from the authenticated CLI, which is the only place they exist:
`prime train models`. Nothing here is from documentation, because Prime
publishes no pricing page (FRICTION.md F-004).

## Measured GPU rates

| GPU | $/GPU-hr | capacity |
|---|---|---|
| `RTX_PRO_6000B_96GB` | **$3.89** | available |
| `H100_80GB` | **$4.79** | available |

"Rate fixed at dispatch; billed per GPU-hour from when pods are ready, prorated
to the second." Hosted RL needs at least **2 GPUs** (1 train + 1 inference), so
the floor is **$7.78/hr** on RTX_PRO or **$9.58/hr** on H100.

## The blocking constraint: trainable and servable barely overlap

Hosted training is **full-parameter only**; LoRA was retired. A before/after
comparison therefore needs a model that is both (a) pre-cached for training and
(b) servable on the inference gateway, so it can be measured before and after.

Of **16** trainable models, only **6** are servable:

| trainable model | servable | images | fits 2-GPU full-param |
|---|---|---|---|
| `meta-llama/Llama-3.2-1B-Instruct` | yes | **no** | **yes** |
| `meta-llama/Llama-3.2-3B-Instruct` | yes | **no** | **yes** |
| `Qwen/Qwen3.5-9B` | yes | yes | no, too large |
| `Qwen/Qwen3.8-27B` | yes | yes | no |
| `Qwen/Qwen3.5-35B-A3B` | yes | yes | no |
| `Qwen/Qwen3.6-35B-A3B` | yes | yes | no |

Not servable at all: `Qwen3.5-0.8B`, `Qwen3.5-2B`, `Qwen3.5-4B`,
`Qwen3-30B-A3B`, `Qwen3.5-122B-A10B`, `Qwen3.5-397B-A17B-FP8`, both Nemotrons,
`MiniMax-M2.5`, `Qwen3-0.6B-Reverse-Text-SFT`.

**The small trainable models cannot be evaluated.** Qwen3.5 at 0.8B, 2B and 4B
are pre-cached for training and return HTTP 404 "The model does not exist" from
the inference API. They are trainable but unmeasurable, which makes them
useless for a before/after study.

Full-parameter RL on `Qwen/Qwen3.5-9B`, the small eval tier, needs roughly
9B x 16 bytes for weights, gradients and Adam state before activations, which
exceeds one 80GB card, so it cannot run at the 2-GPU floor.

## Consequence for the study

The only viable before/after candidates are **Llama-3.2-1B and Llama-3.2-3B**,
and both are **text-only**. So:

1. **The RL phase runs on the `ocr_text` condition.** This was already the plan,
   now it is forced rather than chosen.
2. **A fourth eval tier is required** to produce the "before" number, because the
   trainable model is not one of the three pre-registered tiers. Cost to add
   `meta-llama/Llama-3.2-3B-Instruct` ($0.0509/$0.335 per Mtok) on OCR text at
   100 docs x 10 samples: roughly **$0.05**. Negligible.
3. **The claim narrows.** It becomes "can RL lift a 3B text-only model on OCR
   text toward the frontier", not "can a small VLM match a frontier model on
   receipt photographs". Still a complete loop; a smaller claim.

## Cost bands

| item | low | high |
|---|---|---|
| Eval run, 3 tiers, both conditions, 100 docs x 10 samples | $10.55 | $14.87 |
| Add Llama-3.2-3B as before-tier, OCR only | $0.05 | $0.05 |
| **RL run, 2 GPUs, RTX_PRO at $3.89/GPU-hr** | **$7.78** (1 hr) | **$23.34** (3 hr) |
| Re-eval after training, OCR only | $0.05 | $0.05 |
| **TOTAL** | **$18.43** | **$38.31** |

Duration is the dominant unknown. Prime publishes no hosted-run durations. The
self-hosted prime-rl README offers only loose analogues: Alphabet Sort "on a
single H100 GPU in just over an hour" for a 4B with LoRA, Wordle "on 2-4 H100
GPUs in a few hours".

**CLAUDE.md forbids manual intervention on a live run**, so a run that overshoots
cannot be killed to save money. The budget must therefore cover the top of the
band, not the middle.

## AMENDMENT, 2026-11-05 22:25 EST: in-run eval reopens Qwen3.5-4B

The analysis above assumed the "before" and "after" numbers must come from the
public inference API. **They do not.** A prime-rl training run can evaluate the
policy it is training, inside the run, using the run's own inference server.

From `https://docs.primeintellect.ai/prime-rl/training.md`, the documented knobs
are `[[orchestrator.eval.source]]` plus `orchestrator.eval.interval` ("Eval
environments and cadence (default every 100 steps)"), surfacing metrics
`eval/<env>/all/<agent>/reward/mean`. The documented eval-source block is:

```toml
[eval]
interval = 25
[eval.select]
limit = 32
[[eval.source]]
name = "reverse-text"
env.taskset.id = "reverse-text"
env.agent.harness.id = "null"
env.agent.runtime.type = "subprocess"
```

And the docs state the base model is evaluated **before the first step**
(disable with `eval.skip_first_step`), which is exactly the "before" number.
That sentence appears in the SFT section, so for RL it is implied by shared
machinery rather than stated; it must be confirmed on the first run.

Note that Prime's own example sets `env.agent.harness.id = "null"`, which
independently confirms the harness fix in FRICTION.md F-015.

### Consequence: the RL target changes

| | previous plan | amended plan |
|---|---|---|
| Model | `meta-llama/Llama-3.2-3B-Instruct` | **`Qwen/Qwen3.5-4B`** |
| Vision | text-only | **yes, natively** |
| Family vs small eval tier (`qwen3.5-9b`) | different vendor | **same family** |
| Before/after source | public inference API | **in-run eval, step 0 vs final** |
| Fourth eval tier needed | yes | **no** |

`Qwen/Qwen3.5-4B` is in the training cache (`prime train models`) and on Hugging
Face is tagged `Image-Text-to-Text`, "Causal Language Model with Vision
Encoder", Apache-2.0, 262,144 context. The whole Qwen3.5 series is unified
multimodal: there are no separate `-VL` repos, and text-only serving is a flag
(`--language-model-only`), not a different checkpoint.

So the story becomes **"RL on a 4B model from the same family as the 9B eval
tier, both vision-capable"**, which is a real scaling-and-training narrative
rather than a detour through a text-only Llama chosen only because it happened
to be servable.

**Still unconfirmed, to check on the first dispatch:** that `[orchestrator.eval]`
works on a *hosted* run (the hosted examples never show it), that the step-0
base eval fires for RL as it does for SFT, and which inference server the in-run
eval uses. Also unchanged: no documented path deploys a trained checkpoint on
Prime, so anything beyond in-run eval means downloading the checkpoint,
converting DCP to safetensors, and serving it on your own GPU.

**Namespace note.** The two catalogs use different IDs for the same weights:
training takes `Qwen/Qwen3.5-9B`, inference takes `qwen/qwen3.5-9b`. Probed both
casings for 4B, 2B and 0.8B: all return 404 from the inference API, so the
earlier finding stands and in-run eval is the only route for those sizes.

## Recommendation

$20 does not reliably fund the full loop. **$40 does**, with margin.

A cheaper variant: train `Llama-3.2-1B-Instruct` instead of 3B. It is smaller
and faster per step, plausibly finishing nearer the 1-hour end, for a total
around $25 to $30. The tradeoff is that a 1B baseline is so weak that a large
relative gain may still leave it far from useful, which weakens the
"small owned model" argument even if the training works.

Either way, cap `max_steps` explicitly so wall-clock is bounded by
configuration rather than by hope, and pass `--size` on the volume: the default
is 5 TiB at $460.80/month (FRICTION.md F-005).
