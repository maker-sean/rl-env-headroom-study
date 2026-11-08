# Friction log

Tooling friction hit while building and running this environment, recorded as
it happened. Each entry states what was tried, what happened, what was
expected, and a suggested fix, so every one is a reproduction note rather than
a review. Severity is **blocker** (cannot proceed without a workaround),
**annoying** (costs real time) or **papercut** (small but avoidable). Things
that worked are logged too, as `W-` entries.

Versions: `verifiers` 0.4.1, `prime` CLI 0.20.0, gateway
`https://api.pinference.ai/api/v1`. Entries are append-only; where a later
finding contradicted an earlier entry, the correction is appended to it rather
than replacing it.

---

## F-001 | 2026-11-05 20:40 EST | Phase 0 | blocker

**Tried:** Followed Prime's own Hub tutorial to learn how to define and publish
an environment. `https://docs.primeintellect.ai/tutorials-environments/create.md`
states that it describes the verifiers v0 workflow, that v0 is deprecated, that
v0 environments appear under "Legacy" on the Hub, and that new environments
should be built on verifiers v1. It links to a v1 guide.

**Happened:** The linked v1 guide,
`https://docs.primeintellect.ai/verifiers/v1/getting_started`, returns **HTTP 404**.

**Expected:** A working link to the current guide.

**Suggested fix:** Fix the link. Then invert the tutorial: make v1 the default
path and move v0 behind a "legacy" disclosure. A deprecation notice that points
to a 404 is worse than no notice, because it tells the builder they are on the
wrong path without showing them the right one.

---

## F-002 | 2026-11-05 20:41 EST | Phase 0 | blocker (upgraded from annoying, see F-007)

**Tried:** Read documentation for `prime lab setup`, the command that scaffolds a
working environment workspace.

**Happened:** `prime lab` is not documented anywhere on the docs site. Checked
the docs index (`llms.txt`), the CLI reference
(`https://docs.primeintellect.ai/cli-reference/introduction.md`), the
`PrimeIntellect-ai/prime` README, and the platform overview. The only mentions
are two parenthetical asides: "(for example a `prime lab setup` workspace)" in
`tutorials-environments/create.md` and again in `evaluating.md`.

**Expected:** A page describing what `prime lab setup` creates, since the docs
reference its output as a precondition.

**Suggested fix:** Document `prime lab`, or stop referencing it as a precondition.

**Resolution, 2026-11-05 21:0x EST:** The command is not undocumented. It has been
**removed**. See F-007. Severity upgraded accordingly.

---

## F-003 | 2026-11-05 20:44 EST | Phase 0 | annoying

**Tried:** Determine the current environment-definition API before writing code.

**Happened:** Found three mutually inconsistent descriptions live at the same
time. `https://docs.primeintellect.ai/verifiers/tasksets.md` documents verifiers
v1: `import verifiers.v1 as vf`, with `Taskset`, `Task`, `TaskData`, and
`@vf.reward(weight=...)`. `tutorials-environments/create.md` documents v0 with a
`load_environment()` entrypoint returning `vf.Environment`. The hosted-training
page `https://docs.primeintellect.ai/hosted-training/environment-model.md` also
still describes environments as exposing `load_environment()`. The platform
overview describes an environment as "dataset + harness + rubric", which is the
v0 framing, and v1 has no `Rubric` class at all.

**Expected:** One current answer, with older framings clearly marked.

**Suggested fix:** Add a dated "which API am I on" page, and stamp every page
with the verifiers version it applies to. The migration is clearly mid-flight;
say so openly rather than leaving the reader to discover it by contradiction.

---

## F-004 | 2026-11-05 20:48 EST | Phase 0 | annoying

**Tried:** Estimate cost before committing, which is the first thing any
enterprise team does.

**Happened:** `https://www.primeintellect.ai/pricing` returns **HTTP 404**. There
is no public pricing page. Hosted training GPU rates are available only through
`prime train models`, which requires an account and a login. The billing doc
states, verbatim: "Rates are set per GPU type and change over time, so they live
in the CLI rather than in these docs."

**Expected:** Published rates, or at least a range.

**Suggested fix:** Publish a pricing page. "Rates change" is an argument for
publishing a live table, not for publishing nothing. The inference catalog
already proves Prime can do this well: see W-001.

---

## F-005 | 2026-11-05 20:49 EST | Phase 0 | papercut

**Tried:** Read hosted-training volume documentation.

**Happened:** `prime train` volumes default to **5 TiB**. Volumes bill on
provisioned size from creation until deletion, used or not, at $0.09 per GiB per
month. The docs' own table puts 5 TiB at **$460.80 per month**.

**Expected:** A default that cannot quietly cost $460 per month.

**Suggested fix:** Default to something small, size the volume from the model and
checkpoint settings, or refuse to create a volume over some threshold without an
explicit flag. The docs do warn about this, which is good, but a warning in prose
is a weaker control than a safe default.

---

## F-006 | 2026-11-05 20:52 EST | Phase 0 | annoying

**Tried:** Get the list of served inference models and their prices from the docs,
to choose three model tiers.

**Happened:** `https://docs.primeintellect.ai/inference/models` returns **HTTP
404**. The dashboard at `https://app.primeintellect.ai/dashboard/inference`
returns HTTP 200 but is entirely client-rendered, so it yields no model data to
anything that is not a full browser.

**Expected:** A model catalog page in the docs.

**Suggested fix:** Render the catalog as a static docs page, generated from the
same endpoint that already serves it.

---

## W-001 | 2026-11-05 20:52 EST | Phase 0 | worked well

`GET https://api.pinference.ai/api/v1/models` returns the full inference catalog
as JSON, publicly, with no API key, including per-model `context_window`,
`max_output_tokens`, and `pricing.input_usd_per_mtok` /
`pricing.output_usd_per_mtok`, each carrying an `effective_at` date. 86 entries.

This is better than most providers do. Per-token prices with effective dates, in
a machine-readable form, with no auth wall, is exactly right. The only problem is
that nothing in the documentation points to it. See F-006.

---

## W-002 | 2026-11-05 20:55 EST | Phase 0 | worked well

Install was clean and fast, first try, no workarounds:

```
curl -LsSf https://astral.sh/uv/install.sh | sh
uv tool install prime
```

Result: uv 0.13.7, Prime CLI 0.20.0. Standing on uv rather than shipping a
bespoke installer is the right call and it shows.

---

## W-003 | 2026-11-05 20:56 EST | Phase 0 | worked well

The verifiers v1 reward API is genuinely good design. Rewards are decorated
methods on the task, `@vf.reward(weight=0.4)`, parameters are injected by name
from a small documented set (`trace`, `runtime`, `task`), and a reward may return
either a float or a dict of named components. `@vf.metric` records an
observational number without touching the reward. Weights can be overridden from
TOML without editing code.

Reading one task class tells you the whole scoring story. That is a real
improvement over a separate rubric object holding a parallel list of functions
and weights.

One design consequence worth noting, not a complaint: `trace.reward` is the
**sum** of `score * weight`, so there is no way to express a hard gate such as
"invalid JSON scores zero overall". Each reward function has to carry the
validity check itself. That is a reasonable tradeoff for composability, but it is
worth a line in the docs, because the obvious mental model of a rubric is a
pipeline with veto power.

---

## F-007 | 2026-11-05 21:09 EST | Phase 1 | blocker

**Tried:** Ran `prime lab setup` to create the workspace that Prime's own
tutorials name as the starting point, after installing the CLI fresh (v0.20.0).

**Happened:** The command is gone. `prime lab --help` reports the group itself as
`(deprecated)` with the message:

> Removed: Lab workspaces are no longer set up by the CLI.

All five subcommands (`setup`, `sync`, `doctor`, `hygiene`, `register-github`)
are marked removed. `hygiene` is special-cased to "exit 0 so existing
prime-lab-hygiene workflows keep passing", which confirms this was a real,
load-bearing workflow that was retired.

**Expected:** Either a working command, or docs that do not tell me to run it.

**Suggested fix, in priority order:**
1. Make the removal message name the replacement command. A deprecation that says
   "removed" without saying "use X instead" costs every single user the same
   search. This is a one-line change and it is the highest-leverage fix on this
   whole list.
2. Purge `prime lab setup` from the docs, same release.
3. Add a "start here" page that is tested in CI against the shipped CLI, so a
   removed command cannot stay in the onboarding path.

---

## W-004 | 2026-11-05 21:09 EST | Phase 1 | worked well

`prime --help` opens with this, before the usage block:

> IMPORTANT: If you are AI, ALWAYS use --plain when using the prime CLI to get a
> terse version of the content without any design elements designed for humans.
> For any list-style query, use --output json and pipe to jq. You get the json
> schema for any list command by using --help.

Every command group repeats `--plain` with "USE THIS IF YOU ARE AI."

This is the most forward-looking thing I have seen in the product. Prime has
recognized that a large share of CLI invocations now come from coding agents, and
rather than leaving them to parse Rich-formatted box drawings, they put the
machine-readable path in the help text where an agent will actually read it. It
worked on me: I switched to `--plain` immediately.

Worth contrasting with F-006: the CLI is designed for agent consumption, while
the docs site publishes the inference catalog only through a client-rendered
dashboard that no agent can read. The instinct exists but has not reached the
whole surface.

---

## F-008 | 2026-11-05 21:09 EST | Phase 1 | annoying

**Tried:** Choose three model tiers, which requires knowing which models accept
image input, since half this study feeds receipt photographs.

**Happened:** `GET /api/v1/models` does carry the answer, in
`specs.modalities.input`, as `["text","image","file"]`. 87 of 137 models are
vision-capable. But this is documented nowhere, the field is absent from the
docs' own API reference description of the models endpoint, and 8 of 137 entries
have `specs: null` so cannot be classified at all. The 22 `hosted` models use a
**different** field name, `input_modalities`, for the same information.

**Expected:** One documented field name, populated on every entry.

**Suggested fix:** Normalize to one field, populate it everywhere, and document
it. Then add a filter: `prime inference models --modality image`.

---

## F-009 | 2026-11-05 21:34 EST | Phase 1 | blocker

**Tried:** Followed Prime's Hub tutorial commands to scaffold an environment and
run it locally, against a clean install of `verifiers` 0.4.1 (latest on PyPI).

**Happened:** Neither command exists. The installed console scripts are
`vf-validate`, `vf-run`, `vf-debug`, `vf-gepa`. Missing:

- `vf-init`, which `tutorials-environments/create.md` gives as the scaffold
  step: "`uvx --from verifiers vf-init <your-env-name>`"
- `vf-eval`, which the same page gives as the local test step
  ("`uv run vf-eval my-environment`") and which `evaluating.md` also names

**Expected:** The documented commands to exist in the documented package.

**Suggested fix:** Test the documented commands against the released package in
CI. A docs example that names a console script which the package does not
install is mechanically detectable, and it is the single cheapest class of
first-run failure to eliminate.

---

## F-010 | 2026-11-05 21:34 EST | Phase 1 | annoying

**Tried:** Discover the configuration flags for my own taskset. My
`TasksetConfig` subclass adds `split`, `condition`, `limit`, and
`image_max_edge`.

**Happened:** `vf-validate --help` lists only base-class fields
(`--taskset.id`, `--taskset.system-prompt`, `--taskset.task.*`). My own fields
appear nowhere. They nonetheless **work**: `--taskset.limit 5` produced
"validating 5/5 task(s)" where the default produces 100, and
`--taskset.condition image` switched conditions. A nonexistent field is
correctly rejected with "Extra inputs are not permitted", which proves the
parser is validating against the subclass.

**Expected:** `--help` to enumerate the fields of the taskset actually named on
the command line, since the parser already knows them.

**Suggested fix:** Resolve the taskset before rendering help and include its
config schema. Failing that, print the resolved config at startup so the
accepted fields are at least visible once.

---

## W-005 | 2026-11-05 21:34 EST | Phase 1 | worked well

`vf-validate <taskset> --only-gold` runs the task's `validate()` with **no
agent and no model**, so it costs nothing:

```
INFO validating 5/5 task(s) from doc-extraction-study on the subprocess runtime (gold)
INFO idx=0 valid=True reason=valid (0.0s)
"valid_rate": 1.0
```

This is exactly the right primitive. It let me prove the environment
end-to-end, in both input conditions, through the real loader and CLI, on a
wallet with a $0.00 balance. It also means "ground truth scores 100%" can gate
every future run as a cheap precondition rather than a manual discipline.

Two notes. First, `--only-noop` is a thoughtful companion: it scores the
untouched task, which catches a rubric that pays out for doing nothing. That is
the reward-hacking floor, promoted to a first-class check. Second, this
primitive is the answer to F-009: the documented local-eval command does not
exist, but a better one does, and it is not mentioned in the Hub tutorial at
all. Pointing `create.md` at `vf-validate` would fix the tutorial and surface
the best tool in the box at the same time.

---

## F-011 | 2026-11-05 21:53 EST | Phase 1 | blocker

**Tried:** Ran the first smoke test against `qwen/qwen3-vl-8b-instruct`, chosen
as the small tier by reading Prime's own public model catalog
(`GET /api/v1/models`), which lists it with a price, a 262,144 context window,
and `specs.modalities.input` of `["text","image","file"]`.

**Happened:** All three rollouts failed with HTTP 404:

> No allowed providers are available for the selected model. Providers serving
> qwen/qwen3-vl-8b-instruct: parasail, but your request's provider.only
> preference permits only: alibaba.

`qwen/qwen3-vl-235b-a22b-instruct` fails identically. A direct probe of 18
candidates found 14 callable and 4 refused.

**Expected:** A model listed in the catalog to be callable, or to carry a field
saying it is not.

**Suggested fix, in priority order:**
1. Add an `available` or `providers` field to each catalog entry. The gateway
   already knows which providers serve a model, since the error message names
   them. Surfacing it is nearly free.
2. Make the provider preference overridable per request, or default it to "any
   provider that serves this model" rather than one inferred from the ID prefix.
   Refusing a request because the caller's implicit preference excludes the only
   provider is a routing default, not a capability limit.
3. Failing both, filter uncallable models out of the catalog response.

---

## F-012 | 2026-11-05 21:53 EST | Phase 1 | annoying

**Tried:** Probed 18 models with a single `max_tokens=1` request each,
sequentially, no concurrency.

**Happened:** `qwen/qwen3.5-9b` and `openai/gpt-oss-120b` returned HTTP 429:
"Too many concurrent hosted model requests. Try again shortly." Both succeeded
on a later retry.

**Expected:** A single sequential 1-token request not to be rate limited.

**Suggested fix:** Distinguish "you exceeded your concurrency" from "the fleet
is saturated" in the error, and include a `Retry-After`. Then make `vf-run`
retry 429s with backoff by default; it already has a `--retries` config, but a
capacity 429 on a shared fleet is the platform's condition to absorb, not the
user's to discover.

---

## F-013 | 2026-11-05 21:53 EST | Phase 1 | papercut

**Tried:** Reused working `vf-validate` flags with `vf-run`:
`--taskset.limit 3 --taskset.condition ocr_text --runtime.type subprocess`.

**Happened:** Rejected. `vf-run` wants `--env.taskset.limit`,
`--env.taskset.condition`, and `--env.agent.runtime.type`. The same
configuration sits under a different prefix in each command.

**Expected:** One namespace, or the same one in both.

**Suggested fix:** Accept both prefixes, or print the resolved config tree on
`--help` for the named taskset so the correct path is visible once.

---

## W-006 | 2026-11-05 21:53 EST | Phase 1 | worked well

Cost observability is genuinely good. Every inference call appears in
`prime wallet` as an itemized row with a request ID and an amount to four
decimal places:

```
2026-11-06 02:48  inference (<32-char request id>)  $0.0002
```

And `vf-run` records exact `num_input_tokens` and `num_output_tokens` on every
trace. Together these mean spend can be **measured per rollout** rather than
estimated, which is what a cost claim in a report needs. All probing plus the
first smoke run cost $0.0003 in total.

---

## F-014 | 2026-11-05 22:12 EST | Phase 2 | blocker

**Tried:** Plan a hosted RL run that could be measured before and after, which
needs a model that is both pre-cached for training (`prime train models`) and
servable on the inference gateway (`/v1/models`).

**Happened:** Of **16** trainable models, only **6** are servable. The small
ones that would make a cheap RL run possible, `Qwen/Qwen3.5-0.8B`,
`Qwen/Qwen3.5-2B` and `Qwen/Qwen3.5-4B`, are all pre-cached for training and
all return HTTP 404 "The model 'qwen/qwen3.5-4b' does not exist" from the
inference API.

So Prime will train models it will not serve. Of the 6 that are servable, the
only two small enough for the 2-GPU full-parameter floor are
`Llama-3.2-1B` and `Llama-3.2-3B`, and **both are text-only**.

**Expected:** A model I can train on the platform to be a model I can evaluate
on the platform.

**Suggested fix, in priority order:**
1. **Serve what you train.** Every model in the training cache should have an
   inference endpoint, even a slow or cold-start one. Without it, "train your
   own model here" has no measurable outcome on the platform.
2. **Bring back LoRA, or state the smallest full-parameter run per model.** The
   2-GPU floor combined with full-parameter-only quietly excludes every model
   above roughly 4B from a cheap experiment, and nothing in the docs says so.
   A column in `prime train models` giving minimum GPUs per model would have
   saved this entire investigation.
3. Mark the train/serve intersection in both catalogs, so the viable set is one
   command away instead of a join the user has to perform.

---

## F-015 | 2026-11-05 22:25 EST | Phase 2 | blocker (silent failure)

**Tried:** Ran the 20-document pilot with `vf-run`, specifying the taskset,
model, split, condition, temperature and concurrency. I did not specify a
harness, because the taskset has no tools and the task is a single-turn
extraction: there is nothing for a harness to do.

**Happened:** `vf-run` defaulted to the **`bash` harness** and prepended this
to every request, ahead of the task's own system prompt:

> You are a coding agent. You have access to a bash tool for running shell
> commands. You also have an edit tool for single-occurrence string replacement
> in a file.

It also exposed bash and edit tools. The trace node sequence was
`system, system, user, assistant(tool_call), tool(""), assistant(prose)`:
the model made a tool call, got an empty result, and then described the receipt
in English instead of returning JSON.

`qwen/qwen3-vl-30b-a3b-instruct` scored **0.0000 on all 60 rollouts, standard
deviation 0.0**. The small and frontier tiers still emitted JSON and scored
0.804 and 0.945, so they looked entirely plausible while being measured under a
coding-agent persona they were never meant to have.

**Expected:** A taskset with no tools to default to a harness that does not
inject tools or a persona. `null` exists and is exactly that.

**Why the default is `bash`:** `default_harness_id()` returns `"bash"` unless
the taskset's own package exports a `Harness` subclass. So the default is
"coding agent" for every environment whose author did not know to export one.

**Fix applied here:** `src/doc_extraction_study/harness.py` exports a two-line
`NullHarness` subclass, which makes `default_harness_id` resolve to this
environment's own harness. Verified with no flags:
`harness=doc-extraction-study`, node roles `system, user, assistant`, one
system message, no injected persona.

**Suggested fix, in priority order:**
1. **Default to `null` when the taskset declares no tools.** The information is
   already available: the taskset's `toolsets()` is empty. Defaulting a
   tool-free task to a tool-using coding agent cannot be right.
2. **Log the resolved harness and any injected system prompt at run start.**
   One line naming the harness and saying "harness appends a system prompt"
   would have cost me nothing instead of a discarded pilot. `APPENDS_SYSTEM_PROMPT`
   is already a declared capability flag on every harness; surface it.
3. Document the export-a-Harness-subclass mechanism in the environment
   authoring guide. It is the difference between a published environment that
   works for the next person and one that silently misreports.

## F-016 | 2026-11-06 | Phase 4 | annoying

**Tried:** Prepared to publish the finished environment to the Hub with
`prime env push`, which is the action that turns a local taskset into something
another builder can run.

**Happened:** The account has no username. `prime whoami` reports:

```
Username  Not set
Name      <account email>
```

`prime config --help` lists 16 setters (`set-api-key`, `set-team-id`,
`set-base-url`, `set-ssh-key-path` and so on) and none of them sets the
username. `prime profile` does not exist. `prime env push --help` offers
`--owner` and `--team` but no way to establish the identity those slugs resolve
against, and no `--dry-run`.

**Expected:** Either a `prime config set-username`, or an account that is usable
for publishing the moment `prime login` succeeds.

**Not verified:** whether `prime env push` actually fails without a username.
Confirming it means publishing, and there is no dry run, so this entry claims
only what `whoami` and `config --help` show: the field is empty and the CLI
cannot set it.

**Suggested fix:** Add `prime config set-username`. Failing that, have
`prime login` print the one web action still outstanding, since it already knows
the field is unset.

**Correction, 2026-11-07, after reading the CLI source:** the claim above that
the CLI cannot set the username is **wrong**, and the "Not verified" note was
the tell. `prime env push` does set it. On the API error for a missing slug it
prompts for a username and `PATCH`es `/user/slug`
(`prime_cli/commands/env.py:1016-1051`, CLI 0.20.0). What is true is narrower
and still worth fixing: the only route is inside `push`, it is reachable only by
hitting the error, and it is an interactive `typer.prompt`, so a non-interactive
or CI push has no way through and no documented way to set the field first.
`prime config` still has no setter and `prime whoami` still reports the field
without saying where to fill it. I published by setting the username on the web
profile instead, so I never saw the prompt. Severity drops from "gated" to
"undiscoverable and interactive-only".

---

## F-017 | 2026-11-07 | Phase 4 | annoying

**Tried:** Worked out what `prime env push` uploads, so that a repository
holding work in progress alongside the environment could be published safely.

**Happened:** It uploads two artifacts, and only one of them is governed by the
project's own build configuration.

1. `uv build --wheel`, then it uploads the wheel. That contains exactly what
   `[tool.hatch.build.targets.wheel]` declares. For this project, 10 files
   under `src/doc_extraction_study`.
2. Then it builds a **second, separate source archive** by walking the working
   tree itself (`prime_cli/commands/env.py:417 _collect_archive_files`, CLI
   0.20.0) and uploads that too. It honors `.gitignore`. From the top level it
   takes only `README.md`, `pyproject.toml` and root-level `*.py`. Every
   subdirectory below that it walks in full.

Two consequences follow, and I found both the hard way. A
`[tool.hatch.build.targets.sdist] exclude` has no effect on any of it, because
the hatch sdist target is never built. And because the top-level rule and the
recursion rule differ, whether a file ships depends on which directory it sits
in, which is not a safe thing to hold in your head while publishing.

**Expected:** The publish command to print what it is about to upload, or to
upload only the artifact the build config declares.

**Not verified:** whether the archive walker's behaviour is intentional or
incidental. This entry describes what CLI 0.20.0 does, not what it is meant to
do.

**Repro:**

```python
# Lists the real archive contents without publishing anything.
from pathlib import Path
from prime_cli.commands.env import _collect_archive_files
for f in _collect_archive_files(Path(".")):
    print(f.relative_to(Path(".").resolve()))
```

**Fix applied here:** everything not intended for publication lives in a single
gitignored directory, since `.gitignore` is the one guard that applies to the
artifact that actually ships, and a pre-push check calls the collector above and
fails on anything outside a reviewed allowlist.

**Suggested fix:** print the manifest and total size for **both** artifacts and
confirm before upload, document that the source archive is built from the
working tree rather than from the declared package, and add a `--dry-run`.
There is currently no way to see the file list before it is uploaded.

---

## F-018 | 2026-11-07 | Phase 4 | annoying

**Tried:** `prime env push --visibility PUBLIC --runtime v1` on a project whose
package lives at `src/doc_extraction_study/`, the src layout that the Python
Packaging Authority's own packaging guide recommends.

**Happened:**

```
Environment name: doc-extraction-study
Error: No environment Python file found
Unexpected error: 1
```

The file exists. The package imports. `uv build` produces a correct wheel from
it, and `vf-run` has executed 7,000 rollouts against it. The abort comes from a
pre-flight check that looks for a `*.py` at the project root, or a top-level
directory containing `__init__.py` (`prime_cli/commands/env.py:917-932`, CLI
0.20.0). A src-layout package sits at `src/<name>/__init__.py`, one level
deeper than the check looks, so the check misses it and the push stops before
the build it would have run successfully.

**Expected:** Either the check reads `pyproject.toml`, which already names the
package in `[tool.hatch.build.targets.wheel] packages`, or it looks one level
down, or the error names what it looked for.

**Suggested fix:** resolve the package from `pyproject.toml` rather than by
globbing, or glob `*/*/__init__.py` as well. At minimum, make the error say
"looked for `*.py` at the project root or `*/__init__.py`" so the cause is
visible.

---
