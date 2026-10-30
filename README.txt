BEYOND RECALL — INDEPENDENT STUDY
Author: Aditya Mantri

This directory contains a newly authored standalone synthetic experiment, its
fresh results, and the author-named working manuscript. The experiment uses
Python's standard library and local SQLite only. It imports no application
repository or proprietary component and consumes no nonpublic conversation data.
Author background appears in the manuscript's author note only.

REPRODUCE THE MEASURED STUDY
  python3 study.py campaign --out my-results --workers 4
  python3 checks/check_results.py --campaign my-results \
      --out my-verification.json
  python3 -W error::ResourceWarning -m unittest -v test_study

The engine refuses to replace an existing completed campaign. Use a fresh output
path. There are 528 unique structural policy/history/profile cases, 66 per policy.
The archived results/ campaign contains 928 process attempts, with 256 abrupt
worker-process terminations at declared barriers. Five boundary probes follow
separately. Process attempts and repetitions are not independent samples.

Primary software environment: Python 3.12.13, SQLite 3.53.1, Darwin arm64.
Same-host reproduction: Python 3.14.3, SQLite 3.51.2. All policy aggregate metrics
and boundary scalar outcomes match. The same 10 focused tests pass in both
software environments. Reproduction counts are not combined into a larger N.
Random fresh record addresses differ; compare outcomes and counts, not raw bytes.

POLICY FACTORS
  D: stable addresses for inserted records, versus fresh random addresses.
  P: retain the chosen decision and literal target bindings durably.
  R: terminal receipt fast path suppressing a completed intent's redispatch.
P1 keeps its decision after success under both R settings. The experiment does
not give receipts an artificial final-state advantage by deleting only R0 plans.
All variants share source bounds, disabled-source checks and generation handling.

MAIN FINDING
  D1P1R0 and D1P1R1 both pass 66/66 selected terminal cases and continuity checks.
  Adding R changes recorded put/delete commits 317->275, with 66 planner calls in
  either variant. It suppresses work while final-state correctness stays equal.
  Other variants separate wrong contents, duplicate physical records and changed
  decisions. See results/summary.json and checks/factorial_contrasts.json.

MEASUREMENTS AND LIMITS
  Selected terminal = expected literal fact set + expected physical cardinality
  + final acknowledgement. Continuity is scored separately by logical intent.
  Put/delete counts include repeated committed puts/deletes, excluding reset,
  cleanup, reads and coordinator writes. They measure neither latency nor cost.
  The planner is scripted. There is no live-model quality, semantic truth,
  retrieval recall, production traffic, poisoning defense or user study.
  Abrupt os._exit occurs after committed semantic phases. This is not a power
  failure, mid-SQLite-commit failure, cloud network or multi-agent race campaign.
  The external-interleaving probe overwrites a newer external value even while
  the selected terminal conjunction passes. Final state is not linearizability.

FILES
  manuscript/main.tex, refs.bib, figures/: editable author-named paper project.
  study.py: frozen participant, driver and experiment specification.
  results/: primary raw cases, states, frozen specification and five probes.
  reproduction/: separate complete software-environment reproduction.
  checks/: independent verifier, factor analysis, tests and provenance audits.
  figures/: original renderers, measured images, captions and numerical checks.
  refs.bib: selected public academic bibliography and two implementation docs.
  literature/selected_primary_manifest.json: public primary-source provenance.
  inputs/: paper-writing ground truth and scope instructions.

The local literature working library also contains publicly retrieved papers
and unused background documents. They are not proprietary code or experimental
inputs. The distributable reproduction package includes only selected citation
metadata/links and the new study's own code/data/manuscript, excluding unused
background documents, private publication-review notes, installed environments
and development pilots. No external publication or submission was performed.
