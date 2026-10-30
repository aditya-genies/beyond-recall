# Skeptical source and participant-boundary review

This is a same-study pre-pilot audit of a new, unfrozen benchmark-impact study.
It is not an external replication, an empirical effect result, or a journal
acceptance assessment. No model or embedding call was made. Work in this review
does not modify the released v0.3.0 source, data or PDF.

## Verified source facts and repairs

The independent auditor pins all three public input hashes separately from the
adapter. It checks all 510 episodes: 5,882 LoCoMo turns and 246,750 full-history
LongMemEval turns, including literal source/date/speaker/order, opaque identities,
per-occurrence source grouping, evaluator reference projections and component
membership. The current adapter passes. Thirty-one original fixture tests pass,
including label poisoning, temporal/source identity, source-pin tampering,
category-5 reference handling, split overlap and forged-payload controls.

The initial global LongMemEval `sessionID + turn-index` identity rule was unsafe:
13 repeated session occurrences within question histories produce 143 conflicting
turn occurrences, all with different dates. Across question histories, the 4,672
reused session occurrences preserve role/content but use different dates. The
revised adapter identifies a question-local session occurrence by question,
position and upstream session ID, then identifies a turn inside that occurrence.
A replay preserves those IDs/timestamps; a different authored occurrence receives
a different identity. This is established provenance engineering, not a new
algorithm. The tests verify replay identity and independent identical text.

Oracle and full-history files share all 500 question IDs, questions, answers,
types and answer-session **sets**. The 122 answer-session list differences are
order differences. All 500 question dates and all 948 matched session dates differ
between variants. Current projection uses the chosen full row's dates and its
query date; it must never borrow the oracle timeline. The oracle contains only
evidence sessions and is not a full-history retrieval workload. Unknown variants
now fail instead of silently selecting oracle data.

The permitted ingestion projection has only scope and five scalar event fields:
event ID, source ID, occurrence date, speaker and text. Counterfactual changes to
question/reference/category/answer-session labels and `has_answer` leave that
projection unchanged. LoCoMo's released `blip_caption`, when present, is appended
with an explicit released-caption marker. This is a disclosed text representation
of the supplied caption, not newly performed vision inference. Native memory
and reader inputs must use this projection rather than whole evaluator records.

All 446 LoCoMo category-5 references are an abstention target, not their
`adversarial_answer` distractor. Upstream evidence/antecedent locations remain
recorded. `validate_support_metric()` and negative tests require positive-support
coverage to be **null** for unanswerable questions and unresolved gold locations;
zero would falsely count an unscorable location as retrieval failure, and one
would falsely credit a distractor as positive support. Abstention is graded
separately. This assertion must also be enforced by the eventual output checker.

## Development versus confirmation

There are exactly 495 gold-evidence components in the 500-question LongMemEval
source. The deterministic development set uses 12 questions/components. Of the
488 gold-component-held-out questions, 204 share some full-history upstream
session with development; 216 distinct upstream sessions cross that boundary.
Removing every such question leaves **284 confirmation candidates** before any
outcome is observed: temporal 81, multi-session 76, knowledge-update 41,
single-session-user 38, assistant 31, preference 17; 16 have abstention IDs.
Their exact evaluator-only IDs are in `source_data_audit.json`.

These 284 are source-disjoint **from development**, not mutually independent
histories. Connecting any two of all 500 questions by any shared full-history
session yields one component of size 500. Reusing task-specific gold components
as a claim of full-history independence would be false. A naive cluster-by-any-
shared-source analysis has only one cluster and cannot support ordinary clustered
standard errors. Freeze an appropriate paired/descriptive analysis and explicit
source-reuse sensitivity before confirmation, and do not turn question/reader
repeats into independent population samples. LoCoMo similarly has ten original
conversation clusters; development reserves two. The eligible subset is not a
full official benchmark score. Missing evidence references remain visible and
unscorable for that metric, rather than becoming silent exclusions or failures.

## Memory-worker findings requiring protocol/execution checks

The read-only review of `memory_worker.py` confirms explicit raw-mode labels:
Mem0 uses `infer=False`, LlamaIndex uses persistent TextNodes, and authored guards
are sequential. These do not reproduce a default inferred-memory agent, and the
guards do not establish concurrent uniqueness.

Before pilot freeze, the following must be checked in the actual execution path:

1. **Fail-closed ingestion.** The current query path rejects unexpected fields;
   the reviewed ingestion path did not yet enforce episode/event allowlists
   before backend construction/writes. Extra fields can enter `study_body_sha256`
   even though native text uses only speaker/text. This is a schema-boundary gap,
   not evidence that plaintext gold answers have leaked. Validate the exact
   projection at the worker boundary before invoking native providers.
2. **Common starting state.** `initial` currently applies the passed admission
   mode. Exact-content admission can collapse legitimate same-text occurrences
   in original history. Enforce common native-once initialization followed by
   physical-ID-preserving per-backend clones before retry interventions, or use
   each method's own explicitly paired clean baseline. The planned second-source
   clone control must prove the same baseline identities, payloads and dates
   before retries. A retrieval-only filter cannot be credited with changing
   physical duplicate counts.
3. **Embedding provenance and cost scope.** Cache keys currently include model
   name, action kind and text, but not the loaded model artifact/config digest.
   Use a fresh cache tied to a frozen model/runtime/config manifest, or include
   that identity in the namespace. Record loaded public model-file hashes. A
   warm embedding cache and timings that exclude participant construction are
   valid controlled conditions when labelled; they are not native end-to-end
   cold embedding latency. Account for logical calls, cache hits and real
   inference separately before making work/cost claims.
4. **Temporal query and context parity.** Retrieval accepts text plus an opaque
   invocation key. The separate reader must receive the selected full-row query
   date, ordinary evidence dates, and equal declared candidate/context budgets.
   Complete-store admission versus retrieval suppression changes different
   stages; report their stage-specific coverage/work, not an opaque best-policy
   ranking. No expected IDs/reference/category should enter the reader prompt.

The root agent has accepted the source/date fixes, strict development-source
exclusion, null-support rule and need for authored grader calibration. The
remaining execution checks are not resolved merely by listing them here. No
pilot freeze or efficacy finding is certified by the projection audit.

## Retained development errors

`source_data_audit_initial.json` used the **already repaired** adapter hash and
reported ten LoCoMo alignment differences because this reviewer's first oracle
omitted the newly declared released-caption transformation. Those were auditor
implementation errors, not ten bad dataset episodes. The corrected oracle
passes the same adapter hash; the initial report/log remain unmodified.
`test_data_harness_attempt1.log` records an initial test-module path error, not a
failed semantic data test. Both are retained to prevent an invented clean history.
Early manual findings about raw repeated sessions and overlap are independently
recomputed in the final auditor, without requiring the old adapter to be relabelled
as a frozen experiment.

## Primary sources

- The pinned [LongMemEval README](https://github.com/xiaowu0162/LongMemEval/blob/9e0b455f4ef0e2ab8f2e582289761153549043fc/README.md)
  distinguishes oracle evidence-only histories, full histories, query dates,
  answer-session locations and `has_answer` annotations.
- The pinned [LoCoMo evaluator](https://github.com/snap-research/locomo/blob/3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376/task_eval/evaluation.py)
  treats category 5 as adversarial abstention rather than the distractor answer.
- PaperOrchestra's content-refinement DA protocol prioritizes causal evidence,
  baseline fairness, generalization and novelty. This design audit uses those
  attacks; it does not assign an opaque score or run a manuscript acceptance loop.
