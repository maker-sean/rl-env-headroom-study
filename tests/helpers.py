"""Shared helpers: serialize a canonical Receipt the way a perfect model would."""
import json
from doc_extraction_study.cord import SCALAR_FIELDS, Receipt


def as_model_output(r: Receipt, **overrides) -> str:
    obj = {
        "line_items": [
            {"name": i.name, "quantity": i.quantity,
             "unit_price": i.unit_price, "price": i.price}
            for i in r.line_items
        ]
    }
    for f in SCALAR_FIELDS:
        v = getattr(r, f)
        if v is not None:
            obj[f] = v
    obj.update(overrides)
    return json.dumps(obj)
