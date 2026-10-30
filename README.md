# Beyond Recall

**Recovery Contracts for Agent Memory Mutations**

Aditya Mantri · Independent Researcher · Working research manuscript

[Paper](manuscript/main.pdf) · [Download paper and complete reproducibility package](https://github.com/aditya-genies/beyond-recall/releases/tag/v0.3.0) · [Editable source](manuscript/main.tex) ·
[Review response](revisions/review1/response.txt) ·
[Current research readiness](extensions/replanning_contracts/review/journal_readiness.txt)

A standalone study using synthetic facts and public dependencies. No proprietary
application code, internal PRs, nonpublic conversations, or company credentials
are included. The author's supplied employment/education biography identifies
background; it does not assert an employer or university research affiliation.

## Delivery replay development pilot (separate working paper)

The versioned [development manuscript and reproducibility materials](revisions/benchmark_impact/)
report a second, separate public-history study of controlled post-effect memory
delivery replay. In one dated LongMemEval trace, the later recipe count remains
stored but moves from native rank 5 to 11; duplicated older events fill six of
ten context slots, and two readers answer 2 rather than the reference answer 3.
Across the finite 24-question pilot, event deduplication restores every
automated task label flagged as a loss, but does not always restore retrieval
order. A post-hoc fixed-IDF diagnostic restores all 24 Mem0 contexts in the
pinned local configuration. Duplicate-sensitive IDF is established IR prior
art, and the diagnostic uses clean IDs; neither is presented as a new algorithm.

This is exploratory development evidence, not external replication, a
population estimate, Q1 journal readiness, or peer review. The study has 24
questions from overlapping histories, a failed current-conflict grading
calibration, and a same-family automated judge. The original v0.3.0 paper and
its experiments remain separately versioned and are not pooled with this pilot.
Download the [compiled working paper](revisions/benchmark_impact/manuscript/main.pdf)
and inspect the [pilot findings and audits](extensions/benchmark_impact/PILOT_FINDINGS.md).

## New public-implementation findings

The [admission and recovery extension](extensions/replanning_contracts/README.md)
adds a specific native-pipeline mechanism: Mem0's tested write path checks exact
hashes only among ten retrieved candidates. Re-emitting a larger stored batch
can create exact copies. At N40/K10, the native retry state returns every queried
target but only **247 summed per-query distinct strings in 400 slots**, versus
400 in baseline and both authored interventions.

- **96 controlled executions / 288 native adds** isolate the candidate boundary;
  the 40-fact physical sequence is 40 → 70 → 100.
- **28 new actual Sol 6.1 requests**, four real worker exits after effects, and
  **48 fresh-process retries** add live recovery evidence. Twenty-four retries
  reuse responses and are not additional model calls. Native fresh retries add
  91 exact copies plus one ungraded literal formulation; controls add none.
- **1,008 post hoc native searches** retain all exact targets. An after-close
  computational reproduction matches every ordered result and metric; it repeats
  the same samples. Distinct strings are not semantic diversity or QA accuracy.
- **24 MemTX traces** inspect two snapshot-description boundaries in pinned
  public source; 94 unchanged non-tau2 tests pass. A missing optional dependency
  prevents labelling the full original suite passing.
- **96 executable SQLite/Redis cells**, plus eight declared N/A cells, compare
  authored recovery contracts and documented provider error semantics.

These findings refine known candidate-window and recovery issues. They do not
establish a new deduplication primitive, industry certification, natural failure
rate, journal acceptance or a first-discovery claim. See the
[claim ledger](extensions/replanning_contracts/new_study_claim_ledger.json) and
[closest prior art](extensions/replanning_contracts/literature/overlap_matrix.txt).

## Frozen original evidence

The frozen primary factorial independently switches stable insertion addresses
(D), retained literal decisions/target bindings (P), and completion receipts (R).
Plan retention stays the same under both receipt settings.

- **528 structural cases**, 66 per policy; **928 process attempts**, including
  **256 abrupt subprocess exits**. Attempts are components of cases.
- Five separate boundary probes expose metadata, preparation, and newer-writer
  assumptions.
- D1P1 passes all 66 selected terminal checks under either R setting; receipts
  reduce committed put/delete calls from **317 to 275**.
- A **66-case native LangGraph reference** matches all seven case-level metrics.
  It uses real checkpoints, with no primary coordinator decision/receipt rows.
- A **24-request Sol 6.1/Codex pilot** records literal operation lists. Seven of
  twelve same-prompt pairs differ; most differences concern synonymous labels or
  wording. This does not establish harmful semantic drift.
- **36 SQLite integrations** replay twelve recorded plan pairs through three
  address/plan controls. Two responses from one at-risk scenario demonstrate
  positional aliasing after a completed fact is omitted from a new plan.
- **84 conflict-contract cases**, including sixteen two-process races, separate
  historical success, version conflict, stale overwrite and value ABA.

These are separate experiments with distinct denominators. They are not pooled
into a benchmark score or population failure rate. No new recovery algorithm,
semantic-memory improvement, framework superiority, or acceptance is claimed.
Close prior art and remaining research gaps are documented openly.

## Reproduce the primary experiment

The original engine and checkers require Python 3.12 or 3.14 and standard
library SQLite:

    python3 -W error::ResourceWarning -m unittest -v test_study
    python3 study.py campaign --out my-results --workers 4
    python3 checks/check_results.py --campaign my-results --out my-verification.json
    python3 compare_results.py --candidate my-results

Use a fresh output directory. Compare scalar outcomes rather than random record
addresses or database bytes. Same-author environment/CI reproductions do not
enlarge the main denominator or constitute outside replication.

## Inspect or reproduce the extensions

- [Native LangGraph](extensions/langgraph_reference/README.md): dependency pins,
  native checkpoint provenance, tests, all 66 matched cases and verifier.
- [Live model pilot](extensions/sol_pilot/README.md): protocol, all prompts,
  raw final responses, usage, limitations and personal-Codex runner.
- [Plan identity integration](extensions/plan_binding/README.md): recorded plan
  pairs, controls, SQLite records/audits and counterexamples.
- [Conflict contracts](extensions/conflict_contracts/README.md): bounded schedule
  design, separate checker, version/tombstone assumptions and race witnesses.

Archived Sol outputs and downstream tests can be checked without model access.
Fresh model calls require the requested model on an authenticated personal Codex
account and may return different outputs. No model API-key fallback is used.

## Evidence and status

[Primary data](results/), [same-host reproduction](reproduction/),
[separate metric checker](checks/check_results.py),
[protocol audit](checks/audit_protocol.py), [figures](figures/), and
[provenance](PROVENANCE.json) preserve source/result pins. GitHub Actions
reproduces the primary campaign and runs extension checks; archived older CI
evidence is tied to its commit. The [expanded verification run](https://github.com/aditya-genies/beyond-recall/actions/runs/41003933924) passed all four jobs on Python 3.12 and 3.14, including the complete primary campaign and the four earlier extensions. The new [hosted verification](https://github.com/aditya-genies/beyond-recall/actions/runs/41009518307) passed both jobs, and the [original study workflow](https://github.com/aditya-genies/beyond-recall/actions/runs/41009518298) passed all four jobs on the tested workflow commit. Together they exercise all 71 distinct authored test methods. Full hosted native-backend evidence and archive checks are permanently retained as digest-verified ZIPs under checks/hosted_replanning/. See [CI scope](extensions/replanning_contracts/ci/README.md) and [verification record](checks/replanning_ci.json), including the initial rejected workflow and Ubuntu runtime limitation. Repeated runs are not additional independent samples.

This public repository accompanies a working manuscript. It has not been
accepted or published by a peer-reviewed journal. The study uses authored inputs, declared fault barriers and pinned public
implementations. Model evidence uses one requested alias/harness; the new live
requests and earlier pilot are separate campaigns.
The public artifact makes the claims inspectable; external replication and a
broader novel contribution remain necessary for a leading-journal case.
