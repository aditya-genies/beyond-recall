# MemTX: bounded snapshot-contract observations

The unmodified public `MemTXManager` at commit `4e1124ccd5fd384857463020e3497aa73ec93be6` exhibits two bounded paper/code conformance discrepancies in these synthetic probes. These concern transaction snapshot reads and the empty-snapshot stale-write path. They are not counterexamples to its separately stated action-gating or cascading-repair invariants, nor evidence about model quality, all MemTX behaviors, or a new snapshot-isolation principle.

## Stated contract and source identity

The [v2 paper](https://arxiv.org/html/2607.23929v2), section 3.2, describes start-time visible-record snapshots and rejection of a same-slot rival committed after that snapshot before authority comparison. Section 3.6 describes reads under the transaction snapshot. No latest-read or empty-snapshot exception was found in those descriptions. The source's experiment registry maps `memtx` to `MemTXManager`; `MemTXScopeGuard` is a separate `memtx_sg` variant.

The complete public commit archive was downloaded externally and every one of its 1,255 tracked blobs matched the pinned Git tree. The archive SHA-256 is `0309e7422da5205cb2650a72c9d650d7935d8d9a0a34d39e1d86a4e09e14fe1a`. The paper PDF SHA-256 is `70a55fada7121a5d47fae3185fd09dca18d69826020dcb165323c044c65b1944`. `freeze.json` pins the protocol, our original adapter/checker, all tracked source-file hashes, initial environment versions and archive identity before any baseline execution. Its SHA-256 is `9e7e2e1e8e3b6f9be28f173e4046e0eb9e0d14733a639149274b6145202eedea`.

## Observation 1: an open transaction reads a later commit

All eight read cases return B's newly committed `newer-B` record from A even though A began before B and that ID is absent from A's captured snapshot. The eight cases span four mapped risk tiers and two initial states, empty or containing one unrelated visible anchor. A has no staged writes. The query, requester, purpose, high top-k bound, lack of permission restrictions and absence of revocations avoid own-write, truncation and dynamic-removal explanations. A's pre-commit read matches its captured IDs. A fresh transaction C, opened after B commits, captures and retrieves B in all eight positive controls.

The implementation's [`retrieve()`](https://github.com/lxy1134/MEMTX_/blob/4e1124ccd5fd384857463020e3497aa73ec93be6/src/memtx/memtx_manager.py#L136) applies current lifecycle, permission, revocation and causal filters to the current store. These observations are compatible with a latest-readable-state API. They conflict with the paper's separate start-time snapshot-read description; an author clarification of intentional API semantics would determine whether to call this an implementation or documentation defect. No claim is made about full SQL snapshot isolation or every isolation level.

## Observation 2: an empty initial snapshot changes stale-write handling

The write probes use explicit contradictory alternatives for one single-valued synthetic room's `door_state`: A's older observation is `closed`, B's later observation is `open`. Entity, attribute, scope and overlapping validity bounds are identical; confidence is 1.0. Actual transaction start and staged-record creation times, declared observation times, complete snapshots, API returns and states are retained. In old-A cases, A opens and stages before B opens and commits; A commits last.

- With an unrelated record in A's initial snapshot, all four authority/source variants reject A with `temporal_override`, preserving B.
- With A's initial snapshot empty, the equal-authority/same-source and higher-A-authority variants instead commit A and mark B `superseded`. These are the two final-state overwrites observed among the eight old-A cases.
- The other two empty-snapshot variants reject A on ordinary authority or user-review grounds. They do not overwrite B; the mismatch there is the rejection path rather than a harmful final-state change.
- In all eight fresh-A controls, A begins after B's commit and includes B in its snapshot. The authority-based outcomes are intentional policy controls, not additional discrepancies. “Empty/nonempty” in the initial-condition labels refers to the presence of the unrelated anchor; fresh-A snapshots always contain B.

The bounded mechanism matches the [`SemanticConflictDetector.detect()`](https://github.com/lxy1134/MEMTX_/blob/4e1124ccd5fd384857463020e3497aa73ec93be6/src/memtx/conflict_detector.py#L127) guard: stale-rival rejection is conditional on the snapshot set being nonempty, so an empty captured snapshot reaches ordinary source-authority handling. The fresh controls and the unrelated-anchor contrast distinguish this from a general claim that authority-based corrections are forbidden.

## Baseline tests and installation controls

The first environment installed the authors' requirements without source patches under Python 3.12.13. Every installed version is retained in `freeze.json`.

1. The full original test invocation stops during collection because `tau2` is absent. The pinned full archive lacks `third_party/tau2-bench`; its test imports that optional package unconditionally. This is recorded as one collection error, not a skip or a passing suite.
2. An explicitly reported follow-up excluding only `tests/test_tau2_adapter.py` executes 85 passing tests and encounters nine setup errors in the separate official-MemState adapter. Those errors trace to missing `httpx`, despite the requirements-only installation.
3. The additional vendored imports were resolved by installing `httpx` and `pydantic-settings`, without editing baseline source. The subsequent unchanged non-tau2 invocation passes all 94 executed tests, with zero failures, errors or skips. These 94 unique tests, including the MemTX protocol/property tests, are not added to the repeated earlier pass counts. The full suite remains subject to the missing-tau2 collection boundary.

`unit_tests/report.json`, `environment_amendment.json` and `unit_tests/dependency_followup.json` preserve exact commands, test IDs, all counts, failure/skip messages and both environment version sets. Raw upstream pytest output and JUnit files remain in the external cache, with their hashes retained here, to avoid vendoring upstream source excerpts from tracebacks. The successful protocol tests support a functioning baseline installation; they do not establish the snapshot properties probed here. The separate core snapshot/stale API traces were not rewritten after the dependency amendment.

## Evidence and reproducibility

`results/traces.json` contains all 24 cases with every API call and complete observed store state. `results/verification.json` is produced by our separate trace-only checker, which imports neither MemTX nor adapter execution functions. Its PASS means fixture, membership, ordering, state and classification consistency, not satisfaction of the paper's snapshot contract or external replication. No cases were dropped and no live model was called. All tracked upstream files remain byte-identical; no old study, manuscript, visibility or remote state was changed.

To reproduce, extract the external pinned source archive into a fresh external parent directory and install its requirements. For the final optional-MemState test environment additionally install `httpx==0.28.1` and `pydantic-settings==2.16.2`. Copy only this directory's `PROTOCOL.md`, `probe.py`, `check.py` and `freeze.json` into a fresh scratch directory; existing result and external raw-log directories are deliberately not overwritten. Then run:

```sh
python probe.py run --source /path/to/external/MEMTX_full_4e1124c
python check.py
python probe.py unit-tests --source /path/to/external/MEMTX_full_4e1124c
```

The full/test follow-up commands and exact package versions should be read alongside the reported counts. Neither the reproduction instructions nor this report copy the baseline implementation into the companion repository.
