"""CORD v2 to a canonical receipt record, plus reconstructed OCR text.

CORD v2 (naver-clova-ix/cord-v2) is CC-BY-4.0. See provenance/DATASET_LICENSE.md.
Field availability and schema quirks are measured, see docs/DATA_NOTES.md.
"""
from __future__ import annotations

import base64
import io
import json
from dataclasses import dataclass, field, asdict

from .normalize import amount, quantity

# gt_parse section.key -> canonical scalar field name.
SCALAR_MAP = {
    ("sub_total", "subtotal_price"): "subtotal",
    ("sub_total", "tax_price"): "tax",
    ("sub_total", "service_price"): "service_charge",
    ("sub_total", "discount_price"): "discount",
    ("total", "total_price"): "total",
}
SCALAR_FIELDS = ("subtotal", "tax", "service_charge", "discount", "total")


@dataclass
class LineItem:
    name: str
    quantity: float | None = None
    unit_price: int | None = None
    price: int | None = None


@dataclass
class Receipt:
    doc_id: str
    line_items: list[LineItem] = field(default_factory=list)
    subtotal: int | None = None
    tax: int | None = None
    service_charge: int | None = None
    discount: int | None = None
    total: int | None = None

    def scalars(self) -> dict[str, int]:
        """Present scalar fields only. Absent means absent, never zero."""
        return {f: getattr(self, f) for f in SCALAR_FIELDS if getattr(self, f) is not None}

    def to_dict(self) -> dict:
        return asdict(self)

    def to_model_json(self) -> str:
        """The reply a perfect model would produce for this receipt.

        Used by the gold check (`Task.validate`) and the verifier self-test, so
        both exercise exactly the schema the prompt asks the model for.
        """
        obj = {
            "line_items": [
                {"name": i.name, "quantity": i.quantity,
                 "unit_price": i.unit_price, "price": i.price}
                for i in self.line_items
            ]
        }
        for f in SCALAR_FIELDS:
            v = getattr(self, f)
            if v is not None:
                obj[f] = v
        return json.dumps(obj)


def _one_value(v):
    """CORD repeats an annotation when a field is printed more than once.

    `sub_total.subtotal_price` arrives as `["46.636", "46.636"]` on a receipt
    that prints its subtotal twice, and `sub_total.tax_price` as
    `["6,818", "0"]` when a zero-rated tax line follows the real one. Passing
    the list straight to `amount()` stringified it and fused the digits:
    `46636` became `4663646636`, and `6818` became `68180`.

    The first element is the first occurrence in reading order, which is the
    printed value. Documents where the elements disagree are recorded in
    `provenance/cord_duplicate_fields.json` rather than silently resolved.
    """
    if isinstance(v, list):
        return v[0] if v else None
    return v


def _one_name(v):
    """A list-valued `nm` is one name split across annotation boxes.

    Validation document 37 carries `["-", "Gyro Platter Regular"]`, a bullet
    and the name, so the parts are joined rather than reduced to the first.
    """
    if isinstance(v, list):
        return " ".join(str(x) for x in v if x is not None)
    return v


def _as_list(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def parse_ground_truth(ground_truth: str, doc_id: str) -> Receipt:
    """Build the canonical record from a CORD `ground_truth` JSON string.

    CORD sections are polymorphic: `menu` is a dict when the receipt has one
    item and a list when it has several (46/54 split on the validation set).
    Sub-items (`menu.sub`, 4 occurrences) are not scored and are dropped.
    """
    gt = json.loads(ground_truth)
    parse = gt.get("gt_parse", {}) or {}
    r = Receipt(doc_id=doc_id)

    for raw_item in _as_list(parse.get("menu")):
        if not isinstance(raw_item, dict):
            continue
        r.line_items.append(
            LineItem(
                name=str(_one_name(raw_item.get("nm", "")) or ""),
                quantity=quantity(_one_value(raw_item.get("cnt"))),
                unit_price=amount(_one_value(raw_item.get("unitprice"))),
                price=amount(_one_value(raw_item.get("price"))),
            )
        )

    for (section, key), canonical in SCALAR_MAP.items():
        sec = parse.get(section)
        if isinstance(sec, dict) and key in sec:
            setattr(r, canonical, amount(_one_value(sec[key])))
    return r


def ocr_text(ground_truth: str) -> str:
    """Reconstruct readable page text from CORD's word-level OCR.

    Words are grouped into rows by `row_id`, rows ordered top to bottom by the
    minimum y of their quads, words left to right by minimum x. This is the
    OCR-text condition's model input: it contains the same information a good
    OCR engine would hand downstream, and no ground-truth field labels.
    """
    gt = json.loads(ground_truth)
    rows: dict[object, list[tuple[float, float, str]]] = {}
    for line in gt.get("valid_line", []) or []:
        for w in line.get("words", []) or []:
            text = (w.get("text") or "").strip()
            if not text:
                continue
            q = w.get("quad") or {}
            xs = [q.get(k) for k in ("x1", "x2", "x3", "x4") if q.get(k) is not None]
            ys = [q.get(k) for k in ("y1", "y2", "y3", "y4") if q.get(k) is not None]
            rows.setdefault(w.get("row_id"), []).append(
                (min(ys) if ys else 0.0, min(xs) if xs else 0.0, text)
            )
    ordered = sorted(rows.values(), key=lambda ws: min(w[0] for w in ws))
    return "\n".join(" ".join(t for _, _, t in sorted(ws, key=lambda w: w[1])) for ws in ordered)


def image_data_url(pil_image, fmt: str = "JPEG", max_edge: int | None = 1280,
                   quality: int = 90) -> str:
    """Encode a CORD page image as a data URL for the image condition.

    JPEG at quality 90 rather than PNG: a receipt photograph encodes to roughly
    a tenth the bytes with no measurable loss of digit legibility, and PNG put
    1.37 MB of base64 in every request. Digit legibility is the capability the
    image condition exists to measure, so the quality setting is recorded in
    the run manifest and must not be lowered without re-running.

    CORD pages are about 864x1296, so max_edge=1280 is effectively native.
    """
    from PIL import Image

    img = pil_image
    if max_edge and max(img.size) > max_edge:
        scale = max_edge / max(img.size)
        img = img.resize(
            (max(1, round(img.width * scale)), max(1, round(img.height * scale))),
            Image.LANCZOS,
        )
    if img.mode != "RGB":
        img = img.convert("RGB")
    buf = io.BytesIO()
    if fmt.upper() == "JPEG":
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        mime = "image/jpeg"
    else:
        img.save(buf, format="PNG", optimize=True)
        mime = "image/png"
    return f"data:{mime};base64,{base64.b64encode(buf.getvalue()).decode()}"
