# Beyond Recall

**Recovery Contracts for Agent Memory Mutations**

Aditya Mantri · Independent Researcher · Working research manuscript

[Paper](manuscript/main.pdf) · [Editable source](manuscript/main.tex) ·
[Review response](revisions/review1/response.txt) ·
[Journal readiness assessment](revisions/review1/journal_readiness.txt)

A standalone study using synthetic facts and public dependencies. No proprietary
application code, internal PRs, nonpublic conversations, or company credentials
are included. The author's supplied employment/education biography identifies
background; it does not assert an employer or university research affiliation.

## What the evidence supports

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
evidence is tied to its commit. The [expanded verification run](https://github.com/aditya-genies/beyond-recall/actions/runs/41003933924) passed all four jobs on Python 3.12 and 3.14, including the complete primary campaign and every extension.

This public repository accompanies a working manuscript. It has not been
accepted or published by a peer-reviewed journal. The study uses local SQLite,
declared semantic fault barriers, authored inputs, and one small model pilot.
The public artifact makes the claims inspectable; external replication and a
broader novel contribution remain necessary for a leading-journal case.
