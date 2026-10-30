# Beyond Recall

**Failure Semantics of Long-Term Memory in LLM Agents**  
Aditya Mantri · Independent Researcher · Working research artifact

A standalone, synthetic mechanism study of memory-update recovery. The experiment
uses Python's standard library and two separate local SQLite files. All inputs
are synthetic; no proprietary application code or nonpublic dataset is included.

## What the study tests

Eight factorial policies independently switch:

- **D** — stable addresses for inserted records;
- **P** — durably retained decisions and target bindings;
- **R** — a terminal receipt fast path.

Plan retention stays identical across receipt settings. The main suite contains
**528 unique structural cases**, with 66 cases per policy, **928 process attempts**
and **256 abrupt subprocess terminations**. Five additional probes examine
metadata erasure, an uncommitted decision and an intervening external write.

The retained-plan/stable-address pair passes all 66 selected terminal checks
with either receipt setting. Receipts reduce committed put/delete operations
from **317 to 275**. This separates final-state correctness from repeated work.
The selected terminal conjunction does not certify linearizability, semantic
memory truth, transient-read isolation or production reliability.

## Reproduce everything

No packages need installing for the experiment or its checks. Use Python 3.12 or
3.14 with SQLite available in the standard library:

```sh
python -W error::ResourceWarning -m unittest -v test_study
python study.py campaign --out my-results --workers 4
python checks/check_results.py --campaign my-results --out my-verification.json
python compare_results.py --candidate my-results
```

Use a new output directory. Compare aggregate outcomes, not random fresh record
addresses or database bytes. Repeated computational runs do not enlarge the
main statistical denominator.

Run a single checked case:

```sh
python run_one.py --policy D1P1R0 --profile mixed \
  --history redelivery_drift --out my-single-case
```

## Inspect the evidence

- [Frozen implementation](study.py) and [10 focused tests](test_study.py).
- [Primary summary](results/summary.json), [raw cases](results/cases.jsonl),
  [frozen specification](results/frozen_spec.json) and [five boundary probes](results/boundary_probes.json).
- `results/state/`: both SQLite files for every primary case.
- [Independent verifier](checks/check_results.py), [protocol audit](checks/audit_protocol.py)
  and [paired-factor contrasts](checks/factorial_contrasts.json).
- `reproduction/`: a separate complete software-environment reproduction.
- [Editable paper](manuscript/main.tex), [paper PDF](manuscript/main.pdf),
  [bibliography](refs.bib) and [figure sources](figures/).

The source hash and all final outcomes are checked independently of the
participant's metric functions. GitHub Actions reruns the tests and complete
campaign on Python 3.12 and 3.14. Both complete Ubuntu matrix jobs have passed, including raw-state verification
and equality against the frozen aggregate outcomes. Their evidence is archived
in `checks/github_actions/`; these repetitions are not pooled with the primary
case count.

## Scope and status

This is an independent controlled mechanism study and working paper. Decisions
are scripted, faults occur at named semantic barriers, and the external ledger
has explicit upsert/delete behavior. Abrupt process exit is exercised after
committed phases; power loss and interruption inside SQLite commit are not.
There is no live-model quality, natural drift-frequency, human-response,
clinical, deployed memory-system or poisoning-defense evaluation.

The repository is private. Its existence does not assert public artifact access,
peer-review acceptance or publication. Public academic sources are cited for
prior art; authorship alone is not grounds for adding unrelated citations.
