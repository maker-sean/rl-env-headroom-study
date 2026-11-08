"""The verifiers v1 taskset: single-turn receipt field extraction from CORD v2.

Two conditions over the same documents and the same prompt:
  ``ocr_text``  the model is given CORD's ground-truth OCR words
  ``image``     the model is given the receipt photograph

The delta between them decomposes error into a reading component and a
reasoning/formatting component. That is the point of the study, so the prompt
is identical in both and lives in prompts.py under a version string.

Scoring lives in scoring.py as pure functions, unit tested independently of
this wiring. Reward weights come from scoring.REWARD_WEIGHTS.
"""
from __future__ import annotations

import json
from typing import Iterable, Literal

import verifiers.v1 as vf

from .cord import image_data_url, ocr_text, parse_ground_truth
from .normalize import ocr_text_digits
from .prompts import (IMAGE_USER_PROMPT, OCR_USER_PROMPT, PROMPT_VERSION,
                      PROMPTS)
from .scoring import (REWARD_WEIGHTS, ScoreResult, consistency_metrics,
                      extraction_detail_metrics, format_metrics, score)

DATASET = "naver-clova-ix/cord-v2"
Condition = Literal["ocr_text", "image"]


class DocExtractionData(vf.TaskData):
    """One receipt under one input condition. Ground truth never reaches the model."""

    truth_json: str = ""
    ocr_digits: list[str] = []
    condition: Condition = "ocr_text"
    doc_index: int = -1
    prompt_version: str = PROMPT_VERSION


class DocExtractionTask(vf.Task[DocExtractionData]):
    """Rewards and metrics for one receipt.

    `trace.reward` is the weighted SUM of the four components. There is no
    pipeline gate, so the invalid-JSON hard zero is implemented by every
    component returning 0.0, which scoring.score already does.
    """

    async def validate(self, runtime: vf.Runtime) -> bool | None:
        """Model-free gold check: the ground truth must score exactly 1.0.

        Runs under `vf-validate --only-gold` with no agent and no model, so it
        costs nothing and can gate every run. This is the same property the
        verifier self-test asserts over the whole split; having it here means
        `vf-validate` alone proves the environment, which matters because the
        documented local-eval command (`vf-eval`) does not exist in verifiers
        0.4.1.
        """
        truth = _truth_from_json(self.data.truth_json)
        result = score(truth.to_model_json(), truth, set(self.data.ocr_digits))
        return result.total == 1.0

    def _scored(self, trace: vf.Trace) -> ScoreResult:
        cache = getattr(self, "_score_cache", None)
        if cache is None:
            cache = self._score_cache = {}
        key = trace.id
        if key not in cache:
            truth = _truth_from_json(self.data.truth_json)
            cache[key] = score(trace.last_reply, truth, set(self.data.ocr_digits))
        return cache[key]

    # ---------------------------------------------------------- rewards

    @vf.reward(weight=REWARD_WEIGHTS["schema_valid"])
    async def schema_valid(self, trace: vf.Trace) -> float:
        return self._scored(trace).rewards["schema_valid"]

    @vf.reward(weight=REWARD_WEIGHTS["scalar_f1"])
    async def scalar_f1(self, trace: vf.Trace) -> float:
        return self._scored(trace).rewards["scalar_f1"]

    @vf.reward(weight=REWARD_WEIGHTS["line_item_f1"])
    async def line_item_f1(self, trace: vf.Trace) -> float:
        return self._scored(trace).rewards["line_item_f1"]

    @vf.reward(weight=REWARD_WEIGHTS["grounding"])
    async def grounding(self, trace: vf.Trace) -> float:
        return self._scored(trace).rewards["grounding"]

    # ---------------------------------------------------------- metrics
    # Observational only. Arithmetic consistency is here and NOT a reward
    # because CORD's own ground truth fails it on ~9% of evaluable documents
    # (tax-inclusive pricing plus rounding), so rewarding it would penalize
    # correct extractions. Measured in results/verifier_selftest.json.

    @vf.metric
    async def doc_exact_match(self, trace: vf.Trace) -> float:
        return self._scored(trace).metrics.get("doc_exact_match", 0.0)

    @vf.metric
    async def format_compliance(self, trace: vf.Trace) -> dict[str, float]:
        return format_metrics(self._scored(trace).metrics)

    @vf.metric
    async def consistency(self, trace: vf.Trace) -> dict[str, float]:
        return consistency_metrics(self._scored(trace).metrics)

    @vf.metric
    async def extraction_detail(self, trace: vf.Trace) -> dict[str, float]:
        return extraction_detail_metrics(self._scored(trace).metrics)

    @vf.metric
    async def usage(self, trace: vf.Trace) -> dict[str, float]:
        """Exact token counts, so spend is measured and never estimated."""
        return {
            "input_tokens": float(trace.num_input_tokens or 0),
            "output_tokens": float(trace.num_output_tokens or 0),
            "turns": float(trace.num_turns or 0),
        }


class DocExtractionConfig(vf.TasksetConfig):
    split: str = "validation"
    condition: Condition = "ocr_text"
    limit: int | None = None
    image_max_edge: int = 1280
    # The claim run is pinned to the pre-registered prompt. A variant is only
    # ever used for a post-hoc, separately reported run (deviation D7), and it
    # is recorded on every task so a trace carries the prompt it was run under.
    prompt_variant: str = PROMPT_VERSION


class DocExtractionTaskset(vf.Taskset[DocExtractionTask, DocExtractionConfig]):
    """Loads CORD v2 and emits one task per receipt under the chosen condition."""

    def load(self) -> Iterable[DocExtractionTask]:
        from datasets import load_dataset

        cfg = self.config
        ds = load_dataset(DATASET, split=cfg.split)
        n = len(ds) if cfg.limit is None else min(cfg.limit, len(ds))
        system_prompt = PROMPTS[cfg.prompt_variant]

        for i in range(n):
            row = ds[i]
            raw_gt = row["ground_truth"]
            truth = parse_ground_truth(raw_gt, f"{cfg.split}-{i:03d}")
            page_text = ocr_text(raw_gt)

            if cfg.condition == "ocr_text":
                user = vf.UserMessage(content=OCR_USER_PROMPT.format(ocr_text=page_text))
            else:
                user = vf.UserMessage(content=[
                    vf.TextContentPart(type="text", text=IMAGE_USER_PROMPT),
                    vf.ImageUrlContentPart(
                        type="image_url",
                        image_url=vf.ImageUrlSource(
                            url=image_data_url(row["image"], max_edge=cfg.image_max_edge)),
                    ),
                ])

            yield DocExtractionTask(
                DocExtractionData(
                    id=f"{cfg.split}-{cfg.condition}-{i:03d}",
                    idx=i,
                    doc_index=i,
                    condition=cfg.condition,
                    prompt=[vf.SystemMessage(content=system_prompt), user],
                    prompt_version=cfg.prompt_variant,
                    truth_json=json.dumps(truth.to_dict()),
                    # Grounding always references the document's own OCR, in
                    # both conditions: it asks whether a value is in the
                    # document, which does not depend on what the model saw.
                    ocr_digits=sorted(ocr_text_digits(page_text)),
                ),
                cfg.task,
            )


def _truth_from_json(blob: str):
    from .cord import LineItem, Receipt

    d = json.loads(blob)
    return Receipt(
        doc_id=d["doc_id"],
        line_items=[LineItem(**i) for i in d.get("line_items", [])],
        subtotal=d.get("subtotal"), tax=d.get("tax"),
        service_charge=d.get("service_charge"), discount=d.get("discount"),
        total=d.get("total"),
    )
