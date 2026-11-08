"""The pre-registered prompt is fixed; a variant differs by exactly one rule.

Deviation D7 adds one sentence to test whether the `subtotal` failure is a
specification gap. These tests pin that the variant is a single-line addition
and nothing else, so a later edit cannot quietly change the comparison.
"""
from doc_extraction_study.prompts import (PROMPTS, PROMPT_VERSION,
                                          SUBTOTAL_RULE, SYSTEM_PROMPT,
                                          SYSTEM_PROMPT_SUBTOTAL)


def test_registered_prompt_is_the_default():
    assert PROMPTS[PROMPT_VERSION] is SYSTEM_PROMPT


def test_variant_adds_exactly_one_line():
    base = SYSTEM_PROMPT.splitlines()
    var = SYSTEM_PROMPT_SUBTOTAL.splitlines()
    assert len(var) == len(base) + 1
    added = [l for l in var if l not in base]
    assert added == [SUBTOTAL_RULE.rstrip("\n")]


def test_variant_removes_nothing():
    for line in SYSTEM_PROMPT.splitlines():
        assert line in SYSTEM_PROMPT_SUBTOTAL.splitlines()


def test_variant_keeps_the_schema_byte_identical():
    head = SYSTEM_PROMPT.split("Rules:")[0]
    assert SYSTEM_PROMPT_SUBTOTAL.split("Rules:")[0] == head
