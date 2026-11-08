# Model tier selection, measured

Selected 2026-11-05 21:53 EST. **Availability and image support were measured, not read.**
The public catalog lists models the gateway refuses to serve, so callability is
probed. Evidence: `provenance/model_availability.json`,
`provenance/image_support.json`, `provenance/pinference_models_20261105.json`.

Reproduce:
```
uv run python scripts/06_probe_model_availability.py
uv run python scripts/07_probe_image_support.py
```

## Final tiers

| Tier | Model ID | Size | Serving | $/Mtok in | $/Mtok out | callable | image |
|---|---|---|---|---|---|---|---|
| Small open | `qwen/qwen3.5-9b` | 9B | hosted | 0.063 | 0.093 | yes (1 retry) | yes |
| Mid open | `qwen/qwen3-vl-30b-a3b-instruct` | 30B A3B | gateway | 0.200 | 0.700 | yes | yes |
| Frontier | `anthropic/claude-opus-5.5` | undisclosed | gateway | 4.000 | 20.000 | yes | yes |

## What changed from the catalog-only selection, and why

My first picks came from reading the catalog. Two of three were wrong.

- **`qwen/qwen3-vl-8b-instruct` is not callable.** It is listed, priced, and
  flagged vision-capable, but a request returns HTTP 404: "No allowed providers
  are available for the selected model. Providers serving
  qwen/qwen3-vl-8b-instruct: parasail, but your request's provider.only
  preference permits only: alibaba." See F-011.
- **`qwen/qwen3-vl-235b-a22b-instruct` is not callable** for the same reason,
  which removes the optional fourth tier.

**Consequence: the same-family scaling comparison is not available.** The intent
was Qwen3-VL at 8B and 30B-A3B so the small-to-mid delta isolated scale rather
than architecture or vendor. Only the 30B-A3B of that family is servable, so the
small tier is a different family (Qwen3.5 9B). The small-to-mid delta therefore
confounds scale with family and must be reported that way, not as a scaling
result. This is a platform limitation rather than a design choice, and it is
reported as one wherever the small-to-mid delta appears.

The small tier is also 9B rather than the 1-8B band originally wanted. It is the
closest callable, image-capable, open-weight model, and at $0.063/$0.093 it is
the cheapest model in the entire catalog.

## Measured: image tokenization varies enormously by model

The same 8x8 PNG, as counted in each provider's `usage.prompt_tokens`:

| model | prompt tokens for an 8x8 PNG |
|---|---|
| `moondream/moondream3.1-9b-a2b` | 737 |
| `google/gemma-4-31b-it` | 274 |
| `google/gemma-3-27b-it` | 272 |
| `deepseek/deepseek-v4.1-flash` | 191 |
| `qwen/qwen3-vl-30b-a3b-instruct` | 77 |
| `z-ai/glm-5.3-flash` | 33 |
| `mistralai/mistral-small-2603` | 20 |
| `anthropic/claude-opus-5.5` | 15 |
| `openai/gpt-5-nano` | 11 |

A 49x spread on an identical image. This is why the cost forecast excludes image
tokens and why the pilot must measure them per model before the full run is
sized.

## Also probed and callable, held in reserve

`qwen/qwen3.8-27b`, `qwen/qwen3.6-35b-a3b`, `google/gemma-4-26b-a4b-it`,
`google/gemma-4-31b-it`, `google/gemma-3-27b-it`, `z-ai/glm-5.3-flash`,
`deepseek/deepseek-v4.1-flash`, `moondream/moondream3.1-9b-a2b`,
`mistralai/mistral-small-2603`, `openai/gpt-5-nano`,
`anthropic/claude-haiku-4.5`, `anthropic/claude-sonnet-5.5`. All accept images.

Refused: `qwen/qwen3-vl-8b-instruct` (404), `qwen/qwen3-vl-235b-a22b-instruct`
(404), `qwen/qwen3.5-9b` and `openai/gpt-oss-120b` (429, transient; both later
succeeded on retry).

## Explicitly avoided

`openai/gpt-5.4-pro` at $30/$180 per Mtok: 7.5x the input and 9x the output cost
of Opus 5.5, with no evidence here of a corresponding gain.
