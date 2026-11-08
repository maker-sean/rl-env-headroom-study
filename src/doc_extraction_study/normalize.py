"""Normalization for comparing extracted field values to CORD ground truth.

Every rule here is justified by a measured property of the CORD v2 validation
split, recorded in docs/DATA_NOTES.md. Nothing is normalized on a hunch.
"""
from __future__ import annotations

import re
import unicodedata

# CORD amounts are whole Rupiah. Across the validation split every observed
# price format is a digit-group pattern with ',' or '.' as a THOUSANDS
# separator ('##,###', '##.###', '#.###', 'Rp ##,###', ...). No format uses a
# decimal subunit. So both separators are stripped.
_CURRENCY = re.compile(r"(?i)\b(rp|idr|usd|php|myr)\b|[^\w.,\-]")
_NOT_NUM = re.compile(r"[^0-9.,\-]")
# A trailing 2-digit group after a single separator, with no other separator,
# is treated as a decimal subunit (e.g. "16.50"). Flagged, not silently eaten.
_TRAILING_DECIMAL = re.compile(r"^(\d+)[.,](\d{2})$")

MAX_AMOUNT = 10**12


class AmountParse:
    """Result of parsing an amount, carrying whether it looked decimal."""

    __slots__ = ("value", "looked_decimal")

    def __init__(self, value: int | None, looked_decimal: bool = False):
        self.value = value
        self.looked_decimal = looked_decimal

    def __repr__(self) -> str:
        return f"AmountParse({self.value!r}, looked_decimal={self.looked_decimal})"

    def __eq__(self, other) -> bool:
        if isinstance(other, AmountParse):
            return (self.value, self.looked_decimal) == (other.value, other.looked_decimal)
        return NotImplemented


def parse_amount(raw) -> AmountParse:
    """Parse a money value from ground truth or model output to whole units.

    Accepts JSON numbers and strings. Returns AmountParse(None) when there is
    no parseable number, which callers treat as "field absent", never as zero.
    """
    if raw is None:
        return AmountParse(None)
    if isinstance(raw, bool):
        return AmountParse(None)
    if isinstance(raw, int):
        return AmountParse(raw if abs(raw) <= MAX_AMOUNT else None)
    if isinstance(raw, float):
        if raw != raw or raw in (float("inf"), float("-inf")):
            return AmountParse(None)
        return AmountParse(round(raw) if abs(raw) <= MAX_AMOUNT else None,
                           looked_decimal=raw != round(raw))

    s = unicodedata.normalize("NFKC", str(raw)).strip()
    s = _CURRENCY.sub(" ", s)
    s = _NOT_NUM.sub("", s).strip()
    negative = s.startswith("-")
    s = s.lstrip("-").strip(".,")
    if not s:
        return AmountParse(None)

    # One rule for every separator convention, applied to the whole string.
    #
    # CORD mixes conventions inside one dataset: "60.000" is Indonesian
    # sixty thousand, "63,000.00" is comma-thousands with cents, and
    # "9.500,00" is dot-thousands with comma-cents. An earlier version matched
    # only a single trailing 2-digit group against the whole string, so a value
    # carrying BOTH a thousands separator and cents fell through to stripping
    # every separator: "63,000.00" became 6300000 and "9.500,00" became
    # 950000, each a factor of 100 too large. Every tier, frontier included,
    # was then scored wrong on those documents for reading them correctly.
    #
    # The rule: split on separators. A final group of exactly two digits is a
    # subunit and is dropped; a final group of three digits is a thousands
    # group and is kept. Anything else keeps all digits.
    groups = re.split(r"[.,]", s)
    if len(groups) >= 2 and len(groups[-1]) == 2 and all(g.isdigit() for g in groups):
        whole = "".join(groups[:-1])
        if not whole.isdigit():
            return AmountParse(None)
        val = int(whole)
        if val > MAX_AMOUNT:
            return AmountParse(None)
        return AmountParse(-val if negative else val,
                           looked_decimal=int(groups[-1]) != 0)

    digits = s.replace(",", "").replace(".", "")
    if not digits.isdigit():
        return AmountParse(None)
    val = int(digits)
    if val > MAX_AMOUNT:
        return AmountParse(None)
    return AmountParse(-val if negative else val)


def amount(raw) -> int | None:
    """parse_amount, discarding the decimal flag."""
    return parse_amount(raw).value


# Quantity formats measured in CORD: '#', '#x', 'x#', '# x', '#X', '#Prs',
# '#Gls', '###', '#.##'. The unit suffix carries no scoring information.
_QTY = re.compile(r"(\d+(?:[.,]\d+)?)")


def quantity(raw) -> float | None:
    """Parse a line-item quantity. Keeps fractions ('1.5' kg) as floats."""
    if raw is None or isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)):
        if isinstance(raw, float) and raw != raw:
            return None
        return float(raw)
    s = unicodedata.normalize("NFKC", str(raw))
    m = _QTY.search(s)
    if not m:
        return None
    t = m.group(1)
    # A single separator with 1-2 trailing digits is a decimal, else thousands.
    if re.fullmatch(r"\d+[.,]\d{1,2}", t):
        return float(t.replace(",", "."))
    return float(t.replace(",", "").replace(".", ""))


_WS = re.compile(r"\s+")
_PUNCT = re.compile(r"[^\w\s]")
# A leading quantity token duplicated into the name: "1 REAL GANACHE", "2x Kopi".
_LEADING_QTY = re.compile(r"^\s*(\d+)\s*[xX]?\s+(?=\S)")


def item_name(raw, quantity: float | None = None) -> str:
    """Canonical form of a line-item name for matching.

    Case-folded, punctuation removed, whitespace collapsed. CORD names carry
    modifier noise ('+Hot', '(L)') that should not block a match on the dish.

    A leading quantity duplicated into the name is stripped, but ONLY when it
    equals the item's declared `quantity`. Measured on the dev split, 45% of
    one model's predicted names were of the form "1 REAL GANACHE" alongside
    `quantity: 1`, which is a formatting duplication rather than a different
    item; strict matching scored those zero despite correct items and prices.

    The equality condition is what keeps this safe: a genuine name beginning
    with a number, such as "3 Cheese Pizza" on a single-unit line, is left
    alone because 3 != 1. With `quantity=None` nothing is stripped.
    """
    if raw is None:
        return ""
    s = unicodedata.normalize("NFKC", str(raw))
    if quantity is not None:
        m = _LEADING_QTY.match(s)
        if m:
            try:
                if float(m.group(1)) == float(quantity):
                    s = s[m.end():]
            except (TypeError, ValueError):
                pass
    s = s.casefold()
    s = _PUNCT.sub(" ", s)
    return _WS.sub(" ", s).strip()


# Grounding is deliberately LENIENT. A value wrongly judged ungrounded
# penalizes a CORRECT extraction, which is the costlier error; a value wrongly
# judged grounded only slightly weakens the hallucination signal, and the spam
# dilution in scoring.grounding already guards the strategy that exploits it.
#
# Real CORD formats that broke earlier attempts, each found by the rule that
# ground truth must score 1.0 on every document:
#   doc 77/90  "Rp 58000.00", "70000.00"   explicit cents; '.' is not thousands
#   doc 78     "Subtotal 154 000"           a space IS a thousands separator
#   (earlier)  "16,500\n1 EGG TART"         a newline must never fuse numbers
#   doc 10/26  "1 40.000", "2x 4.000 8.000" a space must ALSO never fuse a
#              quantity to a price. Treating space as an in-token separator
#              turned "1 40.000" into "140000" and lost the real value 40000.
#              It fixed 1 document and broke 28.
#
# Resolution: a token spans digits joined only by '.' or ','. Spaces end a
# token. The space-as-thousands reading is added as an EXTRA candidate, and
# only when the following group is exactly three digits, which is what a
# thousands group looks like and what a quantity never looks like.
_IN_TOKEN = ".,"
_TOKEN = re.compile(r"\d(?:[.,]?\d)*")
_TRAILING_CENTS = re.compile(r"[.,](\d{2})$")
_SPACE_RUN = re.compile(r"^[ \u00a0\u202f]$")


def _digit_candidates(token: str) -> set[str]:
    """Plausible numeric readings of one OCR token."""
    out: set[str] = set()
    joined = re.sub(r"[.,]", "", token)
    if joined:
        out.add(joined)
        # "58000.00", "5272.73": a trailing 2-digit group after '.' or ',' may
        # be a decimal subunit, so the whole-units reading is also a candidate.
        if _TRAILING_CENTS.search(token) and len(joined) > 2:
            out.add(joined[:-2])
    out.update(g for g in re.findall(r"\d+", token) if g)
    return out


def ocr_text_digits(text: str) -> set[str]:
    """Digit runs appearing in a document's OCR, for the grounding check.

    Newlines and spaces are token boundaries, so a quantity never fuses to the
    price beside it. Within a token, '.' and ',' are read generously. Runs stay
    strings to avoid leading-zero collisions.
    """
    out: set[str] = set()
    for line in unicodedata.normalize("NFKC", text or "").splitlines():
        matches = list(_TOKEN.finditer(line))
        for m in matches:
            out |= _digit_candidates(m.group(0))
        # Space-separated thousands: "154 000" -> 154000. Only when the second
        # group is exactly 3 digits and exactly one space separates them.
        for a, b in zip(matches, matches[1:]):
            gap = line[a.end():b.start()]
            if len(gap) == 1 and _SPACE_RUN.match(gap) and len(b.group(0)) == 3 \
                    and b.group(0).isdigit():
                out.add(re.sub(r"[.,]", "", a.group(0)) + b.group(0))
    return out
