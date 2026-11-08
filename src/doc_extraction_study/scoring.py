"""The verifier: scores a model's JSON extraction against CORD ground truth.

Pure functions, no verifiers/network dependency, so every rule is unit testable
against ground truth and against deliberately corrupted outputs.

Design decisions and why:

* **Reward components are a weighted sum** (verifiers v1 sums score*weight), so
  an invalid-JSON "hard zero" is implemented by every component returning 0.0
  when parsing fails, not by a pipeline gate.
* **Arithmetic consistency is NOT rewarded.** Measured on the CORD validation
  split, the ground truth itself satisfies the line-item sum on only 91% of
  evaluable docs and the subtotal chain on 94%, because Indonesian receipts use
  tax-inclusive pricing with rounding. Rewarding consistency would impose a ~9%
  false-penalty floor on correct extractions. It is reported as a metric.
* **Absent is a value.** A field missing from the ground truth must also be
  missing from the prediction. Emitting it is a false positive. This is how the
  hallucination penalty enters field F1, and `grounding` adds a second,
  independent check against the document's own OCR digits.
* **Format compliance is measured, not punished.** JSON is recovered through
  documented tiers (clean, fenced, embedded) and the tier is recorded as a
  metric, so "could not follow the output format" is separable from "could not
  read the document".
"""
from __future__ import annotations

import difflib
import json
import re
from dataclasses import dataclass, field

from .cord import SCALAR_FIELDS, LineItem, Receipt
from .normalize import amount, item_name, parse_amount, quantity

REWARD_WEIGHTS = {
    "schema_valid": 0.05,
    "scalar_f1": 0.45,
    "line_item_f1": 0.35,
    "grounding": 0.15,
}
assert abs(sum(REWARD_WEIGHTS.values()) - 1.0) < 1e-9

FUZZY_NAME_THRESHOLD = 0.85
CONSISTENCY_TOLERANCE = 1  # whole Rupiah, absorbs documented rounding

_FENCE = re.compile(r"```(?:json|JSON)?\s*(.*?)\s*```", re.DOTALL)


# --------------------------------------------------------------------------
# JSON recovery
# --------------------------------------------------------------------------

def _balanced_object(text: str) -> str | None:
    """First balanced {...} run, ignoring braces inside JSON strings."""
    start = text.find("{")
    while start != -1:
        depth, in_str, esc = 0, False, False
        for i in range(start, len(text)):
            c = text[i]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
                continue
            if c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
        start = text.find("{", start + 1)
    return None


def recover_json(reply: str | None) -> tuple[dict | None, str]:
    """Return (parsed object, format tier).

    Tiers: ``clean`` (whole reply is the object), ``fenced`` (inside a markdown
    code fence), ``embedded`` (a balanced object amid other text), ``invalid``.
    """
    if reply is None:
        return None, "invalid"
    text = reply.strip()
    if not text:
        return None, "invalid"

    try:
        obj = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        pass
    else:
        # The whole reply is valid JSON. If it is not an object it is a format
        # violation, and must NOT be rescued by digging an object out of it:
        # a top-level array would otherwise score as its first element.
        return (obj, "clean") if isinstance(obj, dict) else (None, "invalid")

    for m in _FENCE.finditer(text):
        try:
            obj = json.loads(m.group(1))
            if isinstance(obj, dict):
                return obj, "fenced"
        except (json.JSONDecodeError, ValueError):
            continue

    candidate = _balanced_object(text)
    if candidate:
        try:
            obj = json.loads(candidate)
            if isinstance(obj, dict):
                return obj, "embedded"
        except (json.JSONDecodeError, ValueError):
            pass
    return None, "invalid"


# --------------------------------------------------------------------------
# Prediction normalization
# --------------------------------------------------------------------------

REQUIRED_KEYS = {"line_items"}
KNOWN_KEYS = {"line_items", *SCALAR_FIELDS}


@dataclass
class Prediction:
    valid: bool
    tier: str
    receipt: Receipt | None = None
    extra_keys: list[str] = field(default_factory=list)
    looked_decimal: int = 0
    violations: list[str] = field(default_factory=list)


def parse_prediction(reply: str | None, doc_id: str = "pred") -> Prediction:
    """Validate and canonicalize a model reply into a Receipt."""
    obj, tier = recover_json(reply)
    if obj is None:
        return Prediction(valid=False, tier=tier, violations=["unparseable"])

    violations = [f"missing:{k}" for k in sorted(REQUIRED_KEYS - set(obj))]
    raw_items = obj.get("line_items")
    if raw_items is None:
        raw_items = []
    if not isinstance(raw_items, list):
        violations.append("line_items:not_a_list")
        raw_items = []

    if violations:
        return Prediction(valid=False, tier=tier, violations=violations)

    r = Receipt(doc_id=doc_id)
    decimals = 0
    for raw in raw_items:
        if not isinstance(raw, dict):
            violations.append("line_item:not_an_object")
            continue
        p = parse_amount(raw.get("price"))
        u = parse_amount(raw.get("unit_price"))
        decimals += int(p.looked_decimal) + int(u.looked_decimal)
        r.line_items.append(
            LineItem(
                name=str(raw.get("name", "") or ""),
                quantity=quantity(raw.get("quantity")),
                unit_price=u.value,
                price=p.value,
            )
        )
    for f in SCALAR_FIELDS:
        if f in obj:
            a = parse_amount(obj[f])
            decimals += int(a.looked_decimal)
            setattr(r, f, a.value)

    return Prediction(
        valid=True,
        tier=tier,
        receipt=r,
        extra_keys=sorted(set(obj) - KNOWN_KEYS),
        looked_decimal=decimals,
        violations=violations,
    )


# --------------------------------------------------------------------------
# Scoring
# --------------------------------------------------------------------------

def _f1(tp: int, fp: int, fn: int) -> float:
    if tp == 0:
        return 0.0 if (fp or fn) else 1.0
    prec = tp / (tp + fp)
    rec = tp / (tp + fn)
    return 0.0 if (prec + rec) == 0 else 2 * prec * rec / (prec + rec)


def scalar_f1(pred: Receipt, truth: Receipt) -> tuple[float, dict]:
    """F1 over (field, value) pairs. A wrong value is both an FP and an FN.

    Per-field attribution is reported because prediction P3 is about one
    specific field (inventing `subtotal` on receipts that print only a total),
    and a bare FP count cannot score it.
    """
    p, t = pred.scalars(), truth.scalars()
    both = p.keys() & t.keys()
    tp = sum(1 for k in both if p[k] == t[k])
    wrong_fields = sorted(k for k in both if p[k] != t[k])
    invented_fields = sorted(p.keys() - t.keys())   # emitted, not in the document
    missed_fields = sorted(t.keys() - p.keys())     # in the document, not emitted
    wrong = len(wrong_fields)
    fp = len(invented_fields) + wrong
    fn = len(missed_fields) + wrong
    detail = {
        "tp": tp, "fp": fp, "fn": fn, "wrong_value": wrong,
        "invented_fields": invented_fields,
        "missed_fields": missed_fields,
        "wrong_value_fields": wrong_fields,
    }
    # Flat per-field flags so they aggregate as metrics without parsing lists.
    for f in SCALAR_FIELDS:
        detail[f"invented_{f}"] = float(f in invented_fields)
        detail[f"missed_{f}"] = float(f in missed_fields)
        detail[f"wrong_{f}"] = float(f in wrong_fields)
    return _f1(tp, fp, fn), detail


def _match_items(pred: list[LineItem], truth: list[LineItem], fuzzy: bool):
    """One-to-one greedy match on normalized name. Returns (pairs, unmatched)."""
    remaining = list(enumerate(truth))
    pairs, unmatched_pred = [], []
    for pi, p in enumerate(pred):
        # Quantity-aware on both sides, symmetrically.
        pname = item_name(p.name, p.quantity)
        hit = next((idx for idx, (_, t) in enumerate(remaining)
                    if item_name(t.name, t.quantity) == pname), None)
        if hit is None and fuzzy and pname:
            best, best_r = None, 0.0
            for idx, (_, t) in enumerate(remaining):
                r = difflib.SequenceMatcher(
                    None, pname, item_name(t.name, t.quantity)).ratio()
                if r > best_r:
                    best, best_r = idx, r
            if best is not None and best_r >= FUZZY_NAME_THRESHOLD:
                hit = best
        if hit is None:
            unmatched_pred.append(pi)
        else:
            pairs.append((p, remaining.pop(hit)[1]))
    return pairs, unmatched_pred, [t for _, t in remaining]


def line_item_f1(pred: Receipt, truth: Receipt, fuzzy: bool = False) -> tuple[float, dict]:
    """F1 over line items. A true positive needs a name match AND a price match."""
    pairs, unmatched_pred, unmatched_truth = _match_items(
        pred.line_items, truth.line_items, fuzzy)
    tp = sum(1 for p, t in pairs if p.price == t.price)
    price_wrong = len(pairs) - tp
    fp = len(unmatched_pred) + price_wrong
    fn = len(unmatched_truth) + price_wrong
    qty_pairs = [(p, t) for p, t in pairs if t.quantity is not None]
    qty_ok = sum(1 for p, t in qty_pairs if p.quantity == t.quantity)
    return _f1(tp, fp, fn), {
        "tp": tp, "fp": fp, "fn": fn,
        "name_matched": len(pairs),
        "price_wrong_on_matched": price_wrong,
        "qty_correct": qty_ok, "qty_evaluable": len(qty_pairs),
    }


def _numeric_values(r: Receipt) -> list[int]:
    values = [getattr(r, f) for f in SCALAR_FIELDS if getattr(r, f) is not None]
    for it in r.line_items:
        values += [v for v in (it.price, it.unit_price) if v is not None]
        if it.quantity is not None and float(it.quantity).is_integer():
            values.append(int(it.quantity))
    return values


def grounding(pred: Receipt, ocr_digits: set[str],
              truth: Receipt | None = None) -> tuple[float, dict]:
    """Are the prediction's numbers actually in the document?

    An independent hallucination check: a number appearing nowhere in the
    document was invented, whether or not it happens to be wrong.

    Two reward hacks found during the Phase 1 gaming exercise are closed here.

    1. **Emit nothing.** An empty prediction has no ungrounded values, so a
       naive precision would score 1.0 and farm the full weight for free.
       Emitting no numbers now scores 0.0, because no CORD receipt is empty
       (minimum 1 line item, 98% carry a total).
    2. **Dump every digit on the page.** Copying all document digits into
       line items makes precision 1.0 while field F1 stays near zero. The
       score is therefore scaled by ``min(1, expected / emitted)``, so
       claiming far more values than the document contains dilutes it.
       Grounding measures whether claims are in the document, and 30 grounded
       claims where 4 exist is not good grounding.
    """
    values = _numeric_values(pred)
    if not values:
        return 0.0, {"emitted": 0, "grounded": 0, "spam_factor": 0.0}
    grounded = sum(1 for v in values if str(abs(v)) in ocr_digits)
    precision = grounded / len(values)
    expected = len(_numeric_values(truth)) if truth is not None else len(values)
    spam = 1.0 if expected >= len(values) else max(expected, 1) / len(values)
    return precision * spam, {
        "emitted": len(values), "grounded": grounded,
        "expected": expected, "spam_factor": spam,
    }


def consistency(r: Receipt, tol: int = CONSISTENCY_TOLERANCE) -> dict:
    """METRIC ONLY. Ground truth fails these, so they are never rewarded."""
    prices = [i.price for i in r.line_items if i.price is not None]
    item_sum = sum(prices) if prices else None
    target = r.subtotal if r.subtotal is not None else r.total
    out: dict[str, float | None] = {}
    if item_sum is not None and target is not None:
        out["items_sum_exact"] = float(item_sum == target)
        out["items_sum_within_tol"] = float(abs(item_sum - target) <= tol)
    else:
        out["items_sum_exact"] = out["items_sum_within_tol"] = None
    if r.subtotal is not None and r.total is not None:
        chain = r.subtotal + (r.tax or 0) + (r.service_charge or 0) - (r.discount or 0)
        out["chain_exact"] = float(chain == r.total)
        out["chain_within_tol"] = float(abs(chain - r.total) <= tol)
    else:
        out["chain_exact"] = out["chain_within_tol"] = None
    return out


@dataclass
class ScoreResult:
    rewards: dict[str, float]
    metrics: dict
    total: float


def score(reply: str | None, truth: Receipt, ocr_digits: set[str]) -> ScoreResult:
    """Score one model reply. `total` is the weighted sum, in [0, 1]."""
    pred = parse_prediction(reply, doc_id=truth.doc_id)

    if not pred.valid:
        rewards = {k: 0.0 for k in REWARD_WEIGHTS}
        return ScoreResult(
            rewards=rewards,
            metrics={
                "format_tier": pred.tier,
                "schema_violations": pred.violations,
                "doc_exact_match": 0.0,
            },
            total=0.0,
        )

    r = pred.receipt
    s_f1, s_detail = scalar_f1(r, truth)
    l_f1, l_detail = line_item_f1(r, truth, fuzzy=False)
    l_f1_fuzzy, _ = line_item_f1(r, truth, fuzzy=True)
    g, g_detail = grounding(r, ocr_digits, truth)

    rewards = {
        "schema_valid": 1.0,
        "scalar_f1": s_f1,
        "line_item_f1": l_f1,
        "grounding": g,
    }
    total = sum(rewards[k] * w for k, w in REWARD_WEIGHTS.items())
    exact = float(s_f1 == 1.0 and l_f1 == 1.0
                  and len(r.line_items) == len(truth.line_items))

    return ScoreResult(
        rewards=rewards,
        metrics={
            "format_tier": pred.tier,
            "doc_exact_match": exact,
            "scalar_detail": s_detail,
            "line_item_detail": l_detail,
            "line_item_f1_fuzzy_names": l_f1_fuzzy,
            "grounding_detail": g_detail,
            "extra_keys": pred.extra_keys,
            "pred_looked_decimal": pred.looked_decimal,
            "consistency_pred": consistency(r),
            "consistency_truth": consistency(truth),
            "n_pred_items": len(r.line_items),
            "n_true_items": len(truth.line_items),
        },
        total=total,
    )


# ---------------------------------------------------------------------------
# Metric flattening, shared by the taskset and by offline re-scoring.
#
# These names are the contract the analysis scripts read. They lived inside
# `taskset.py`'s `@vf.metric` methods until an offline re-score reimplemented
# the flattening by hand, used the raw `scoring` keys instead of these, and
# silently produced a failure taxonomy of zeros. One definition, two callers.

def extraction_detail_metrics(m: dict) -> dict[str, float]:
    """Per-field and per-item detail, flat, for the failure taxonomy."""
    s = m.get("scalar_detail") or {}
    l = m.get("line_item_detail") or {}
    g = m.get("grounding_detail") or {}
    out = {
        "scalar_tp": s.get("tp", 0), "scalar_fp": s.get("fp", 0),
        "scalar_fn": s.get("fn", 0),
        **{k: v for k, v in s.items()
           if k.startswith(("invented_", "missed_", "wrong_"))
           and isinstance(v, float)},
        "item_tp": l.get("tp", 0), "item_fp": l.get("fp", 0),
        "item_fn": l.get("fn", 0),
        "item_name_matched": l.get("name_matched", 0),
        "item_price_wrong": l.get("price_wrong_on_matched", 0),
        "qty_correct": l.get("qty_correct", 0),
        "qty_evaluable": l.get("qty_evaluable", 0),
        "values_emitted": g.get("emitted", 0),
        "values_grounded": g.get("grounded", 0),
        "n_pred_items": m.get("n_pred_items", 0),
        "n_true_items": m.get("n_true_items", 0),
        "pred_looked_decimal": m.get("pred_looked_decimal", 0),
        "line_item_f1_fuzzy_names": m.get("line_item_f1_fuzzy_names", 0.0),
    }
    return {k: float(v) for k, v in out.items()}


def format_metrics(m: dict) -> dict[str, float]:
    tier = m.get("format_tier", "invalid")
    return {f"format_{t}": float(tier == t)
            for t in ("clean", "fenced", "embedded", "invalid")}


def consistency_metrics(m: dict) -> dict[str, float]:
    c = m.get("consistency_pred") or {}
    return {k: float(v) for k, v in c.items() if v is not None}


def flat_metrics(result) -> dict[str, float]:
    """Every metric the runner records for a rollout, flat. Mirrors the
    taskset's `@vf.metric` methods exactly."""
    m = result.metrics
    out = {"doc_exact_match": float(m.get("doc_exact_match", 0.0))}
    out.update(consistency_metrics(m))
    out.update(extraction_detail_metrics(m))
    out.update(format_metrics(m))
    return out
