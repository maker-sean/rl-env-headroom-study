"""The package's default harness: single-turn direct answering.

This exists for one reason. `verifiers.v1` resolves a taskset's default harness
with `default_harness_id()`, which returns `"bash"` unless the taskset's own
package exports a `Harness` subclass. For a taskset with no tools, the `bash`
harness is actively wrong: it prepends

    "You are a coding agent. You have access to a bash tool for running shell
     commands. You also have an edit tool for single-occurrence string
     replacement in a file."

ahead of the task's system prompt and exposes bash and edit tools. In the first
pilot that silently redefined the task. `qwen/qwen3-vl-30b-a3b-instruct` made a
tool call, received an empty result, then answered in prose, scoring **0.0000 on
all 60 rollouts**, which reads as a model failure rather than a harness
misconfiguration. The small and frontier tiers still emitted JSON, so their
numbers looked plausible while being measured under a coding-agent system
prompt. The whole pilot had to be discarded.

Exporting this subclass makes the correct harness the default for anyone who
installs the environment from the Environments Hub and simply runs
`vf-run doc-extraction-study`, with no flag to remember.
"""
from __future__ import annotations

from verifiers.v1.harnesses.null.harness import NullHarness, NullHarnessConfig


class DocExtractionHarnessConfig(NullHarnessConfig):
    """Unmodified; present so the harness has its own config type."""


class DocExtractionHarness(NullHarness):
    """Direct single-turn answering: no tools, no injected agent persona."""


__all__ = ["DocExtractionHarness", "DocExtractionHarnessConfig"]
