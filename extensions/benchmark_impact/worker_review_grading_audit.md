# Completed development-pilot grading and aggregation audit

**PASS for provenance, coverage, joins, arithmetic, and retention of the failed calibration gate.** This is a read-only independent same-study audit, not outside peer review, new grading, or a held-out experiment. No model, native retrieval, or embedding request was made. Frozen execution sources, model answers, references, and judge labels were preserved.

Run the auditor from the repository root:

```sh
.venv-impact/bin/python extensions/benchmark_impact/worker_review_grading_audit.py
```

The machine-readable report is `worker_review_grading_audit.json`; its 2,322 input hashes bind the inspected artifacts. `worker_review_grading_audit.log` records the successful execution. Seven meaningful checker fixtures reject duplicated, absent, unrequested, malformed, or extra-label decisions and accept the valid control (`worker_review_grading_checker_tests.log`). An earlier auditor-only `KeyError` is retained in `worker_review_grading_audit_initial_schema.log`: the unfrozen summarizer had just renamed the metric-discrepancy fields to distinguish rounding. The checker was aligned to those more explicit names; no producer source or evidence was changed.

## Verified denominators and derivations

- **75 primary grading requests, 447 decisions**, plus a separately retained one-request/12-fixture authored calibration. Every primary decision has exactly one requested ID and the strict output fields/types/enums.
- **447 physical reader requests** (298 Sol, 149 Qwen), **149 unique complete prompt byte strings**, **336 condition aliases**, **1008 dependent reader/repeat/condition observations**, and **24 unique questions**. These denominators cannot be interchanged or summed into new independent samples.
- Every grading item ID binds the exact parsed-response file bytes and question identity. The packet's response and protocol hashes match. All expected response–question pairs occur exactly once, including the rule for distinct questions sharing prompt bytes.
- Every retained grader prompt matches the frozen rubric, category rule, deterministic blind ordering, answer, reference, date, and evidence. Its payload excludes backend, intervention, and answering-reader identity. Every raw grader JSON result parses to the recorded decisions, and every raw reader final text parses to its recorded answer. Empty retained tool-event summaries and permitted item types match; raw CLI event streams were not retained.
- All **56 aggregate groups**, **32 paired contrast groups**, clean Sol repeat transitions, **196 native application-phase rows**, and all 1008 observation joins/metrics match an independently implemented derivation. There are no missing reader or primary grading outcomes. The corrected-vs-frozen token metric has zero differences beyond 1e-12, with 131 rounding-only inequalities and maximum absolute difference 1.1102230246251565e-16.
- Native timings are reconciled to their raw execution/status records. The application phase includes persistence and study witness export; process time includes startup. These are neither pure retrieval latency nor physical disk-write counts, and this reconciliation adds no performance experiment.

## Observed transitions and required interpretation

Retry has **seven backend × reader × question combinations** with a clean-correct/retry-incorrect automated task label, spread over **four unique questions**. Counting Sol repeats separately gives **11 dependent repeat transitions**. There are no incorrect-to-correct retry transitions in this pilot. All seven combinations have a correct read-event-deduplicated label.

Five of those seven combinations are LlamaIndex cases where dedup restores exactly the clean complete prompt and deliberately aliases the same archived clean response. This is an input-restoration counterfactual, **not five fresh recovery-generation experiments**. The two Mem0 combinations have different clean/dedup prompts. Shared prompts, Sol repeats, shared conversations and background histories remain dependent. Clean Sol task labels agree across its two repeats in all 48 backend/question cases; that does not establish output determinism, reader-population reliability, or a fixed hosted-model snapshot.

The primary descriptive retry-minus-clean task differences, with 12 questions per dataset and Sol repeats averaged within question, reconcile exactly: Mem0/Sol −1/12 LoCoMo and 0 LongMemEval; Mem0/Qwen 0 LoCoMo and −1/12 LongMemEval; LlamaIndex/Sol −2/12 LoCoMo and −1/12 LongMemEval; LlamaIndex/Qwen −1/12 in each dataset. These are exploratory same-family automated labels, not validated semantic accuracies or population effects.

The authored calibration is still **CALIBRATION_MISMATCH**: all 12 task labels match the authored expectations, but two current-conflict labels do not. The summary explicitly retains `FAILED auxiliary calibration` and withholds definitive semantic/stale-state efficacy claims. Evidence-support labels were not independently calibrated against expert judgements. The observation counts for those auxiliary labels are retained as unvalidated automated outputs, not used to certify correctness. No expected labels were changed to make the gate pass.

## Concrete public-source witness

`worker_review_recipe_case.json` and `worker_review_recipe_case.md` trace LongMemEval question `45dc21b6` (study key `f65dcff812445376dbc709ef`) through pinned original full history, physical LlamaIndex records, native candidates, contexts, all reader answers and inherited task labels.

Its official reference is **3 recipes**. A May 29 statement reports two; the May 30 update reports three. The later statement remains in the replayed physical store and native top60 result at **rank 11**, but duplicate copies occupy six of the ten final context slots. Both readers therefore receive the older count and return two. Clean and event-deduplicated contexts contain the update and yield the archived answer three. This supports a directly inspectable finite displacement mechanism, without claiming all pilot losses are temporal conflicts or treating the failed auxiliary judge as validated.

No material aggregation correction is required. The standing interpretation constraints above are necessary for publication prose.
