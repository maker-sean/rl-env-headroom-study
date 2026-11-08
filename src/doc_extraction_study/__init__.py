from .harness import DocExtractionHarness, DocExtractionHarnessConfig
from .taskset import (DocExtractionConfig, DocExtractionData, DocExtractionTask,
                      DocExtractionTaskset)

__all__ = [
    "DocExtractionTaskset", "DocExtractionTask", "DocExtractionData",
    "DocExtractionConfig",
    # Exported so verifiers' default_harness_id() resolves to this instead of
    # `bash`, which would inject a coding-agent system prompt. See harness.py.
    "DocExtractionHarness", "DocExtractionHarnessConfig",
]
