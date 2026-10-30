# Independent audit of the two post-hoc ranking diagnostics

**Verdict: PASS for the retained, bounded mechanism evidence.** No inconsistency was found between the physical stores, archived query results, score arithmetic, reports, or protocol/source hashes. This is an independent same-study audit, not outside replication or peer review. The auditor made no native search, embedding, model, or network request and changed no producer source, original store, or probe output.

Reproduce from the repository root with the existing pinned public runtime:

```sh
.venv-memory/bin/python extensions/benchmark_impact/worker_review_ranking_audit.py --self-test
.venv-memory/bin/python extensions/benchmark_impact/worker_review_ranking_audit.py
```

`worker_review_ranking_audit.json` contains the machine-readable derivation, six negative/control fixture tests are recorded in `worker_review_ranking_checker_tests.log`, and `worker_review_ranking_audit.log` contains the actual audit command output. The JSON binds 170 inspected inputs by SHA-256. The auditor implements context selection and arithmetic separately from the producer helpers. It opens the physical SQLite databases with `mode=ro` and restricts point-pickle decoding to the two expected public Qdrant data classes.

## What was checked

All 24 development questions and all 14 participant source scopes are present exactly once per declared query condition. The first probe has 96 retained native calls (24 questions × two physical states × two requested budgets). The fixed-IDF probe has 24 further retained calls. These are **120 technical query invocations over the same 24 questions**, not 120 independent task samples, new benchmark examples, or held-out confirmation.

The audit checked 33,970 first-probe rows and 18,770 fixed-IDF rows. Every physical ID exists in the appropriate native store; all output body, logical event/source/date/digest, user/role, hash, and timestamp fields match the native point payload. Each full-pool output contains exactly every physical point in its corresponding store, including every replay duplicate. Thus “full pool” is verified by identity-set equality, not inferred just from the requested number 10000. Across the 14 scopes there are 7,160 clean physical points and 11,000 replayed points; the largest store has 927 points. Native internal candidate bounds at this requested budget exceed those sizes. The final 10-record/12000-byte context selection remains in force.

All original point bytes match both the replayed stores and the fingerprint recorded in the earlier independent pilot audit. Every repeated occurrence has exactly the original dense and sparse vectors and preserves its literal event body, source, and logical date. The known-clean ID set used in the fixed-IDF intervention equals the independently read clean physical IDs. Recomputing sparse-document counts/frequencies from stored vectors gives identical clean and fixed-corpus `N`/`df`, while ordinary replay changes the physical corpus statistics.

All 48 K60 state/question outputs reproduce the original pilot's physical ordering, payloads, and scores within 1e-12. Independently selected K60 clean and replay-deduplicated contexts exactly match the retained pilot contexts. The retained LlamaIndex clean/read-event-deduplicated contexts are identical on all 24 questions; this audit does not rerun LlamaIndex.

## Numerical reconciliation and interpretation

The original probe's additive scorer is **not reciprocal-rank fusion**. In every first-probe row the entity boost is zero and the divisor is two. The audit independently verifies `raw = semantic + normalized_BM25 + entity`, `final = min(raw/divisor, 1)`, the reported final score, the zero semantic threshold, and descending output order. It does not substitute the producer scorer to check itself.

K60 changes selected event sets for 16/24 questions and selected event orders for 19/24; the same original-point scores can be paired for 944 rows. Full-pool selection changes event sets for 10/24 and orders for 17/24, with 12,320 original-point comparisons. In each of the 24 questions at least one paired original point changes its normalized BM25 and final score. No paired original point changes semantic score, entity boost, or divisor beyond 1e-12.

Additional **post-hoc arithmetic**, not a new query experiment: 23/24 questions exhibit a strict original-point score-order reversal with margins greater than 1e-12 in each direction. Each of the ten changed full-pool event sets has a strict reversal between an event lost from selection and an event gained. Those ten set changes cannot be explained solely by physical duplicate tie ordering. This does not establish answer-quality harm.

The fixed-IDF control restores all five reported original-point components in all 12,320 comparisons within 1e-12. All 24 selected event orders and sets return to clean. Every replay duplicate remains present in the full native result lists. The pinned source confirms that the intervention changes the sparse query's IDF-statistics corpus while the ordinary query eligibility filter stays separate; dense queries and additive ranking are unchanged. Together, these observations support the conditional mechanism claim that physical corpus-statistic drift explains the measured residual full-pool differences in this local configuration. Final-context deduplication alone does not undo that drift.

## Standing scope boundaries and wording requirements

- These diagnostics were designed after observing pilot context differences. The all-24 selection and source hashes were recorded in each diagnostic protocol before its queries. They are post-hoc mechanism checks, not preregistered confirmation of the main study.
- The native known-clean-ID intervention is an **oracle mechanism control**, not an oracle-free deployment method or a new IDF algorithm. A new execution policy is not evaluated here.
- Raw sparse query vectors and unnormalized keyword scores were not archived. The audit verifies stored-vector corpus statistics, source routing, normalized explanation arithmetic, component restoration, and membership; it does not independently reconstruct every per-term sparse dot product.
- The result is for pinned Mem0 raw-document mode (public commit `26cdefb46600c0fa5953c4b5ee5003c125539fc4`; package reports 2.2.1), FastEmbed 0.9.1, and Qdrant client 1.20.0 **local mode**. Local source comments about server behavior are not evidence of a server/cloud/cluster experiment.
- The 12,320 comparisons reuse physical points across questions and are not independent statistical samples. Context/order differences and restoration do not establish reader harm, production incidence, vendor-default deficiencies, or novelty.
- `component_changes_at_1e12` is an abbreviated producer field name; its actual comparison tolerance is **1e-12**, as verified from source and arithmetic. Use the correct numeric notation in prose.
- The auditor's zero-call property is direct. Producer zero-extractor/no-new-embedding claims are supported by the inspected offline source path, close-time extractor assertion, and cache-count assertions, rather than an independently retained network trace.

No source or result correction is required. The boundaries above should accompany interpretation, particularly the oracle and local-mode scope.
