"""Hand-built edge cases for every reward function, plus gaming attempts."""
import json
import pytest
from helpers import as_model_output

from doc_extraction_study.cord import LineItem, Receipt
from doc_extraction_study.normalize import ocr_text_digits
from doc_extraction_study.scoring import (
    REWARD_WEIGHTS, consistency, grounding, line_item_f1, parse_prediction,
    recover_json, scalar_f1, score)


# A small hand-built receipt mirroring CORD validation doc 0.
def fixture() -> tuple[Receipt, set[str]]:
    r = Receipt(
        doc_id="fx",
        line_items=[
            LineItem("REAL GANACHE", 1.0, None, 16500),
            LineItem("EGG TART", 1.0, None, 13000),
            LineItem("PIZZA TOAST", 1.0, None, 16000),
        ],
        total=45500,
    )
    ocr = ocr_text_digits(
        "1 REAL GANACHE 16,500\n1 EGG TART 13,000\n1 PIZZA TOAST 16,000\n"
        "TOTAL 45,500\nCASH 50,000\nCHANGE 4,500")
    return r, ocr


# --------------------------------------------------------------- JSON recovery

def test_recover_json_tiers():
    assert recover_json('{"line_items": []}')[1] == "clean"
    assert recover_json('```json\n{"line_items": []}\n```')[1] == "fenced"
    assert recover_json('Here you go:\n{"line_items": []}\nHope that helps.')[1] == "embedded"
    assert recover_json("not json at all")[1] == "invalid"
    assert recover_json("")[1] == "invalid"
    assert recover_json(None)[1] == "invalid"


def test_recover_json_ignores_braces_inside_strings():
    obj, tier = recover_json('{"line_items": [{"name": "A } B", "price": 1}]}')
    assert tier == "clean"
    assert obj["line_items"][0]["name"] == "A } B"


def test_recover_json_rejects_a_bare_array():
    # The schema is an object. A top-level array is a format violation.
    assert recover_json('[{"name": "x"}]')[0] is None


# ------------------------------------------------------------------- scalar F1

def test_scalar_f1_perfect():
    t = Receipt("x", subtotal=100, tax=10, total=110)
    assert scalar_f1(t, t)[0] == 1.0


def test_scalar_f1_absent_field_must_stay_absent():
    truth = Receipt("x", total=110)
    # Inventing a tax the document does not have is a false positive.
    pred = Receipt("x", total=110, tax=10)
    f1, d = scalar_f1(pred, truth)
    assert d["fp"] == 1 and d["fn"] == 0 and f1 < 1.0


def test_scalar_f1_wrong_value_counts_as_both_fp_and_fn():
    truth = Receipt("x", total=110)
    pred = Receipt("x", total=999)
    f1, d = scalar_f1(pred, truth)
    assert (d["tp"], d["fp"], d["fn"], d["wrong_value"]) == (0, 1, 1, 1)
    assert d["wrong_value_fields"] == ["total"]
    assert d["invented_fields"] == [] and d["missed_fields"] == []
    assert f1 == 0.0


def test_scalar_f1_zero_is_not_absent():
    truth = Receipt("x", discount=0, total=110)
    pred = Receipt("x", total=110)
    _, d = scalar_f1(pred, truth)
    assert d["fn"] == 1, "a ground-truth 0 must be required, not treated as absent"


def test_scalar_f1_empty_prediction_scores_zero():
    truth = Receipt("x", subtotal=100, tax=10, total=110)
    assert scalar_f1(Receipt("x"), truth)[0] == 0.0


# ---------------------------------------------------------------- line item F1

def test_line_item_f1_perfect_and_order_independent():
    t, _ = fixture()
    assert line_item_f1(t, t)[0] == 1.0
    shuffled = Receipt("x", line_items=list(reversed(t.line_items)))
    assert line_item_f1(shuffled, t)[0] == 1.0, "item order must not matter"


def test_line_item_f1_dropped_item():
    t, _ = fixture()
    pred = Receipt("x", line_items=t.line_items[:2])
    f1, d = line_item_f1(pred, t)
    assert d["fn"] == 1 and d["fp"] == 0 and 0.0 < f1 < 1.0


def test_line_item_f1_invented_item():
    t, _ = fixture()
    pred = Receipt("x", line_items=t.line_items + [LineItem("GHOST CAKE", 1.0, None, 99000)])
    f1, d = line_item_f1(pred, t)
    assert d["fp"] == 1 and f1 < 1.0


def test_line_item_f1_wrong_price_on_matched_name():
    t, _ = fixture()
    bad = [LineItem(i.name, i.quantity, i.unit_price, i.price) for i in t.line_items]
    bad[0].price = 99999
    f1, d = line_item_f1(Receipt("x", line_items=bad), t)
    assert d["price_wrong_on_matched"] == 1
    assert d["tp"] == 2 and d["fp"] == 1 and d["fn"] == 1


def test_line_item_matching_is_one_to_one():
    # Two predicted copies of one real item must not both match it.
    t = Receipt("x", line_items=[LineItem("A", 1.0, None, 100)])
    pred = Receipt("x", line_items=[LineItem("A", 1.0, None, 100),
                                    LineItem("A", 1.0, None, 100)])
    _, d = line_item_f1(pred, t)
    assert d["tp"] == 1 and d["fp"] == 1


def test_fuzzy_names_are_reported_but_not_rewarded_by_default():
    t, _ = fixture()
    typo = [LineItem("REAL GANACHEE", 1.0, None, 16500),
            LineItem("EGG TART", 1.0, None, 13000),
            LineItem("PIZZA TOAST", 1.0, None, 16000)]
    pred = Receipt("x", line_items=typo)
    strict, _ = line_item_f1(pred, t, fuzzy=False)
    loose, _ = line_item_f1(pred, t, fuzzy=True)
    assert strict < loose == 1.0


# ------------------------------------------------------------------- grounding

def test_grounding_all_values_in_document():
    t, ocr = fixture()
    g, d = grounding(t, ocr, t)
    assert g == 1.0 and d["grounded"] == d["emitted"]


def test_grounding_catches_an_invented_number():
    t, ocr = fixture()
    bad = Receipt("x", line_items=list(t.line_items), total=77777)
    g, d = grounding(bad, ocr, t)
    assert g < 1.0 and d["grounded"] < d["emitted"]


def test_grounding_rejects_the_empty_prediction_hack():
    # HACK 1: emitting nothing has no ungrounded values. Naive precision would
    # be 1.0 and farm the whole weight for free.
    t, ocr = fixture()
    g, d = grounding(Receipt("x"), ocr, t)
    assert g == 0.0 and d["emitted"] == 0


def test_grounding_dilutes_the_digit_spam_hack():
    """HACK 2: copy every digit on the page into line items.

    Precision is 1.0 while field F1 stays near zero. A real receipt carries
    many digits that are not scored fields (date, phone, receipt number, cash,
    change), so the spammer emits far more values than the document contains.
    """
    truth = Receipt("x", line_items=[LineItem("NASI GORENG", 1.0, None, 25000)],
                    total=25000)
    ocr = ocr_text_digits(
        "WARUNG SEDERHANA\nJL MERDEKA 45\nTELP 021 5551234\n"
        "NO 00127 / 2 / 18\n12-03-2019 14:52\nKASIR 3\n"
        "1 NASI GORENG 25,000\nTOTAL 25,000\nCASH 50,000\nCHANGE 25,000\n"
        "NPWP 09.254.294.1-402\nTERIMA KASIH")
    # A smart spammer emits only runs that look like amounts: 3+ digits and no
    # leading zero, so every one of them grounds exactly.
    amounts = sorted(v for v in ocr if len(v) >= 3 and not v.startswith("0"))
    spam = Receipt("x", line_items=[LineItem(f"ITEM{i}", None, None, int(v))
                                    for i, v in enumerate(amounts)])
    g, d = grounding(spam, ocr, truth)
    assert d["grounded"] == d["emitted"], "every spammed value is on the page"
    assert d["emitted"] > d["expected"], "spam emits more than the document holds"
    assert d["spam_factor"] < 1.0
    assert g < 0.5, f"spam must not earn most of the grounding weight, got {g}"


def test_grounding_full_marks_for_an_honest_prediction_on_a_noisy_receipt():
    """The spam guard must not punish a correct extraction."""
    truth = Receipt("x", line_items=[LineItem("NASI GORENG", 1.0, None, 25000)],
                    total=25000)
    ocr = ocr_text_digits(
        "WARUNG SEDERHANA\nTELP 021 5551234\n12-03-2019 14:52\n"
        "1 NASI GORENG 25,000\nTOTAL 25,000\nCASH 50,000")
    g, d = grounding(truth, ocr, truth)
    assert g == 1.0 and d["spam_factor"] == 1.0


# ----------------------------------------------------- consistency is a METRIC

def test_consistency_is_never_a_reward_component():
    assert "consistency" not in REWARD_WEIGHTS
    assert not any("consist" in k for k in REWARD_WEIGHTS)


def test_consistency_tolerance_absorbs_documented_rounding():
    # CORD doc 2: subtotal 18181 + tax 1818 = 19999 against a total of 20000.
    r = Receipt("x", subtotal=18181, tax=1818, total=20000)
    c = consistency(r)
    assert c["chain_exact"] == 0.0
    assert c["chain_within_tol"] == 1.0


def test_consistency_reports_none_when_not_evaluable():
    c = consistency(Receipt("x", total=100))
    assert c["chain_exact"] is None


# ----------------------------------------------------------------- score total

def test_ground_truth_scores_exactly_one():
    t, ocr = fixture()
    res = score(as_model_output(t), t, ocr)
    assert res.total == pytest.approx(1.0)
    assert res.metrics["doc_exact_match"] == 1.0
    assert res.metrics["format_tier"] == "clean"


@pytest.mark.parametrize("reply", [
    "", "   ", None, "I cannot read this receipt.",
    '{"line_items": [}', '{"line_items":', "[1,2,3]",
])
def test_invalid_output_is_a_hard_zero(reply):
    t, ocr = fixture()
    res = score(reply, t, ocr)
    assert res.total == 0.0
    assert all(v == 0.0 for v in res.rewards.values())


def test_missing_required_key_is_a_hard_zero():
    t, ocr = fixture()
    assert score('{"total": 45500}', t, ocr).total == 0.0


def test_corruptions_all_score_below_ground_truth():
    t, ocr = fixture()
    perfect = score(as_model_output(t), t, ocr).total
    corruptions = {
        "digit_shift": as_model_output(t, total=45600),
        "invented_field": as_model_output(t, tax=4550),
        "dropped_item": json.dumps({
            "line_items": [{"name": i.name, "quantity": i.quantity,
                            "price": i.price} for i in t.line_items[:1]],
            "total": t.total}),
        "zeroed_prices": json.dumps({
            "line_items": [{"name": i.name, "quantity": i.quantity, "price": 0}
                           for i in t.line_items], "total": 0}),
        "swapped_names": json.dumps({
            "line_items": [{"name": "EGG TART", "quantity": 1, "price": 16500},
                           {"name": "REAL GANACHE", "quantity": 1, "price": 13000},
                           {"name": "PIZZA TOAST", "quantity": 1, "price": 16000}],
            "total": t.total}),
    }
    for name, reply in corruptions.items():
        got = score(reply, t, ocr).total
        assert got < perfect, f"{name} scored {got}, not below {perfect}"


def test_gaming_floors_are_small_and_measured():
    """Document the exact floor each degenerate strategy can earn."""
    t, ocr = fixture()
    floors = {
        "valid_but_empty": score('{"line_items": []}', t, ocr).total,
        "nulls_everywhere": score(json.dumps(
            {"line_items": [], "subtotal": None, "tax": None, "total": None}), t, ocr).total,
        "digit_spam": score(json.dumps({"line_items": [
            {"name": f"I{i}", "price": int(v)} for i, v in enumerate(sorted(ocr))]}),
            t, ocr).total,
    }
    for name, got in floors.items():
        assert got <= 0.25, f"{name} earns {got:.3f}, too high a floor"
    # The schema_valid weight is a deliberate, documented floor for producing
    # well-formed JSON at all. Nothing else may be farmed.
    assert floors["valid_but_empty"] == pytest.approx(REWARD_WEIGHTS["schema_valid"])


def test_prose_wrapped_json_still_scores_but_records_the_tier():
    t, ocr = fixture()
    res = score(f"Sure! Here is the extraction:\n\n{as_model_output(t)}\n\nLet me know.",
                t, ocr)
    assert res.total == pytest.approx(1.0)
    assert res.metrics["format_tier"] == "embedded"


# ---------------------------------------------------------------------------
# Per-field attribution, needed to score pre-registered prediction P3
# ("the dominant failure is inventing `subtotal`").
# ---------------------------------------------------------------------------

def test_invented_field_is_attributed_by_name():
    truth = Receipt("x", total=100)
    pred = Receipt("x", total=100, subtotal=100)
    _, d = scalar_f1(pred, truth)
    assert d["invented_fields"] == ["subtotal"]
    assert d["invented_subtotal"] == 1.0
    assert d["invented_tax"] == 0.0
    assert d["missed_fields"] == []


def test_missed_field_is_attributed_by_name():
    truth = Receipt("x", total=100, tax=10)
    pred = Receipt("x", total=100)
    _, d = scalar_f1(pred, truth)
    assert d["missed_fields"] == ["tax"]
    assert d["missed_tax"] == 1.0
    assert d["invented_fields"] == []


def test_wrong_value_is_attributed_separately_from_invented():
    truth = Receipt("x", total=100, subtotal=90)
    pred = Receipt("x", total=100, subtotal=999)
    _, d = scalar_f1(pred, truth)
    assert d["wrong_value_fields"] == ["subtotal"]
    assert d["wrong_subtotal"] == 1.0
    # A wrong value is NOT an invented field: the document does have a subtotal.
    assert d["invented_fields"] == []
