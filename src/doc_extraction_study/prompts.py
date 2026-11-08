"""The single fixed prompt, shared by both input conditions.

Held identical across conditions and models so that the image-versus-OCR delta
measures the input format and nothing else. Any change here invalidates
comparisons against earlier runs, so the prompt is versioned.
"""

PROMPT_VERSION = "v1.0.0"

SYSTEM_PROMPT = """\
You extract structured data from retail receipts. Reply with a single JSON \
object and nothing else: no explanation, no markdown fence.

Schema:
{
  "line_items": [
    {"name": string, "quantity": number|null, "unit_price": number|null, "price": number|null}
  ],
  "subtotal": number|null,
  "tax": number|null,
  "service_charge": number|null,
  "discount": number|null,
  "total": number|null
}

Rules:
- "line_items" is required. Include one entry per item line on the receipt.
- "price" is the amount charged for that line, after any per-line quantity.
- "unit_price" is the per-unit amount, only when the receipt states it separately.
- Amounts are whole numbers in the receipt's currency. Write 16500, not "16,500" \
or 16500.00. Do not include a currency symbol.
- Omit a top-level field, or set it to null, when the receipt does not show it. \
Do not infer, compute, or estimate a value that is not printed on the receipt.
- Copy item names as printed.
"""

OCR_USER_PROMPT = """\
Receipt text, as produced by OCR, one line per row of the receipt:

{ocr_text}
"""

IMAGE_USER_PROMPT = "Extract the fields from this receipt image."

# ---------------------------------------------------------------- variants
#
# Post-hoc prompt variant, registered as deviation D7. The headroom ablation
# measured that forgiving an invented `subtotal` is worth +0.0379 to the mid
# tier and +0.0001 to the frontier, which says the failure is an ambiguous
# specification rather than a reading error. This variant tests that claim by
# resolving the ambiguity in the prompt and re-running one cell.
#
# One sentence is added to Rules. Everything else is byte-identical to
# v1.0.0, and no number from a variant run enters the claim table.

SUBTOTAL_RULE = (
    '- Report "subtotal" only when the receipt prints a subtotal line of its '
    'own. If the receipt prints only a total, set "subtotal" to null, even '
    'when a subtotal would equal that total.\n'
)

_ANCHOR = "- Copy item names as printed.\n"
assert _ANCHOR in SYSTEM_PROMPT, "prompt variant anchor missing"
SYSTEM_PROMPT_SUBTOTAL = SYSTEM_PROMPT.replace(_ANCHOR, SUBTOTAL_RULE + _ANCHOR)
assert SYSTEM_PROMPT_SUBTOTAL != SYSTEM_PROMPT

PROMPTS = {
    PROMPT_VERSION: SYSTEM_PROMPT,
    "v1.1.0-subtotal": SYSTEM_PROMPT_SUBTOTAL,
}
