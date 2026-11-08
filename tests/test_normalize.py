"""Hand-built edge cases for every normalization rule."""
import pytest
from doc_extraction_study.normalize import (
    amount, item_name, ocr_text_digits, parse_amount, quantity)


@pytest.mark.parametrize("raw,expected", [
    # Both separators are thousands separators in CORD (measured).
    ("16,500", 16500), ("16.500", 16500), ("1.500", 1500), ("1,234,567", 1234567),
    ("45500", 45500), (45500, 45500), (45500.0, 45500),
    ("Rp 45,500", 45500), ("IDR 45.500", 45500), ("  16,500  ", 16500),
    ("-5,000", -5000),
    # Absent must never become zero: that would silently invent a field.
    (None, None), ("", None), ("   ", None), ("abc", None), ("-", None),
    (".", None), (",", None), (True, None), (False, None),
    (float("nan"), None), (float("inf"), None),
])
def test_amount(raw, expected):
    assert amount(raw) == expected


def test_amount_zero_is_a_real_value_not_absent():
    assert amount("0") == 0
    assert amount(0) == 0


def test_trailing_two_digit_group_is_flagged_as_decimal():
    # "16.50" is ambiguous; treated as a decimal and flagged, not silently eaten.
    p = parse_amount("16.50")
    assert (p.value, p.looked_decimal) == (16, True)
    # A 3-digit group is unambiguous thousands, never flagged.
    assert parse_amount("16.500") == parse_amount("16,500")
    assert parse_amount("16,500").looked_decimal is False


def test_float_with_fraction_is_flagged():
    assert parse_amount(16500.75).looked_decimal is True
    assert parse_amount(16500.0).looked_decimal is False


def test_absurd_magnitude_rejected():
    assert amount("9" * 30) is None


@pytest.mark.parametrize("raw,expected", [
    ("1", 1.0), ("1 x", 1.0), ("x1", 1.0), ("2X", 2.0), ("x 2", 2.0),
    ("3Prs", 3.0), ("1Gls", 1.0), ("10", 10.0), (2, 2.0), (2.0, 2.0),
    ("1.5", 1.5), ("1,5", 1.5), ("1.500", 1500.0),
    (None, None), ("abc", None), ("", None), (True, None),
])
def test_quantity(raw, expected):
    assert quantity(raw) == expected


@pytest.mark.parametrize("a,b", [
    ("REAL GANACHE", "real ganache"),
    ("  REAL   GANACHE  ", "real ganache"),
    ("Real-Ganache", "real ganache"),
    ("REAL GANACHE (L)", "real ganache l"),
])
def test_item_name_canonicalizes(a, b):
    assert item_name(a) == item_name(b)


def test_item_name_keeps_distinct_items_distinct():
    assert item_name("EGG TART") != item_name("PIZZA TOAST")
    assert item_name(None) == ""


def test_ocr_digits_strip_separators():
    d = ocr_text_digits("1 REAL GANACHE 16,500\nTOTAL 45.500")
    assert {"16500", "45500", "1"} <= d


# ---------------------------------------------------------------------------
# Grounding candidate generation. These cases come from real CORD documents
# that broke a strict reading; see the module note in normalize.py.
# ---------------------------------------------------------------------------

def test_ocr_digits_never_fuse_across_a_newline():
    """The original bug: "16,500\\n1 EGG" became the single run "165001"."""
    d = ocr_text_digits("1 REAL GANACHE 16,500\n1 EGG TART 13,000")
    assert "165001" not in d
    assert {"16500", "13000"} <= d


def test_ocr_digits_handle_explicit_cents():
    """CORD doc 77/90: "Rp 58000.00" must ground the value 58000."""
    assert "58000" in ocr_text_digits("*2 Cheese Tart Rp 58000.00")
    assert "70000" in ocr_text_digits("Total Due 70000.00")
    # CORD labels truncate the subunit: OCR "5272.73", ground truth 5272.
    assert "5272" in ocr_text_digits("Total Tax Included: Rp 5272.73")


def test_ocr_digits_handle_space_as_thousands_separator():
    """CORD doc 78: "Subtotal 154 000" must ground the value 154000."""
    d = ocr_text_digits("Subtotal 154 000")
    assert "154000" in d and "154" in d


def test_ocr_digits_leniency_is_bounded_to_the_document():
    """Leniency must not ground a number that is simply not on the page."""
    d = ocr_text_digits("1 NASI GORENG 25,000\nTOTAL 25,000")
    assert "99999" not in d
    assert "77777" not in d


# --- Regression: values carrying BOTH a thousands separator and cents.
# --- Found when all three tiers, frontier included, disagreed with ground
# --- truth by exactly 100x on the same two test documents.

def test_comma_thousands_with_dot_cents():
    """CORD test-047 prints "63,000.00". Stripping both separators gave
    6300000, so every model was scored wrong for answering 63000."""
    assert amount("63,000.00") == 63000
    assert amount("45,000.00") == 45000


def test_dot_thousands_with_comma_cents():
    """CORD test-067 prints "9.500,00", the European convention, in the same
    dataset that writes "60.000" for sixty thousand."""
    assert amount("9.500,00") == 9500


def test_three_digit_final_group_is_still_thousands():
    """The fix must not reinterpret the Indonesian majority convention."""
    assert amount("60.000") == 60000
    assert amount("28.182") == 28182
    assert amount("1.234.567") == 1234567
    assert amount("16,500") == 16500


def test_two_digit_final_group_remains_a_subunit():
    assert amount("16.50") == 16
    assert amount("100.00") == 100
    assert parse_amount("16.50").looked_decimal is True
    assert parse_amount("100.00").looked_decimal is False
