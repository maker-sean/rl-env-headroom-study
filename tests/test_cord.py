"""CORD ground-truth parsing."""
import json

from doc_extraction_study.cord import parse_ground_truth

# --- Regression: list-valued CORD annotation fields (found by the gold gate on
# --- the test split, which the validation split could not have surfaced).

def test_duplicate_subtotal_annotation_is_not_fused():
    """CORD test-013 prints its subtotal twice: ["46.636", "46.636"].

    Stringifying the list fused the digits into 4663646636, which then failed
    the grounding check because no such number appears on the receipt.
    """
    gt = json.dumps({"gt_parse": {
        "menu": [{"nm": "BASO KUAH", "cnt": "1", "price": "43.636"},
                 {"nm": "A.MINERAL GELAS", "cnt": "1", "price": "3.000"}],
        "sub_total": {"subtotal_price": ["46.636", "46.636"], "tax_price": "4.664"},
        "total": {"total_price": "51.300"}}})
    r = parse_ground_truth(gt, "test-013")
    assert r.subtotal == 46636
    assert r.tax == 4664
    assert r.total == 51300
    # the arithmetic the fused value destroyed
    assert r.subtotal + r.tax == r.total


def test_disagreeing_duplicate_takes_first_printed_value():
    """CORD test-099 carries tax ["6,818", "0"]: a real tax line then a zero one.

    Fusing produced 68180, which coincidentally equalled that receipt's
    subtotal, so the fused value looked grounded and the gold gate scored it
    1.0. The corruption was silent; only the first element is the printed tax.
    """
    gt = json.dumps({"gt_parse": {
        "menu": [{"nm": "X", "cnt": "1", "price": "68.182"}],
        "sub_total": {"subtotal_price": "68.182", "tax_price": ["6,818", "0"]},
        "total": {"total_price": "75.000"}}})
    r = parse_ground_truth(gt, "test-099")
    assert r.tax == 6818
    assert r.tax != r.subtotal


def test_split_name_annotation_is_joined_not_truncated():
    """validation-037 carries nm ["-", "Gyro Platter Regular"]: a bullet plus
    the name. Taking the first element alone would yield "-"."""
    gt = json.dumps({"gt_parse": {
        "menu": {"nm": ["-", "Gyro Platter Regular"], "price": "50,000"},
        "total": {"total_price": "50,000"}}})
    r = parse_ground_truth(gt, "validation-037")
    assert r.line_items[0].name == "- Gyro Platter Regular"
