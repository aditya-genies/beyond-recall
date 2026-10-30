# Final read-only reader and official-metric audit

The audit passes all **447 completed reader requests**: 298 Sol and 149 Qwen
statuses, all recorded PASS, across 149 distinct task prompts and 336 condition
aliases. These are reader calls only; calibration and grading calls are separate.
This audit made no requests, generation, embedding or native retrieval calls.
Initial inventory found 368 statuses and was labelled NOT_READY, not a partial
correctness certificate; the final report requires all 447.

For every condition, the auditor independently rebuilds the task prompt from the
frozen instruction, selected question/date and permitted evidence fields. All
frozen input hashes, prompt bytes, output schemas, context budgets and complete
alias mappings match. Every archived request prompt matches its frozen input.
All 447 raw final texts parse to their recorded result under the frozen rule:
Sol JSON directly; Qwen permits only the documented surrounding code fence.
No Qwen output actually needed fence removal. Invalid citation lists reconcile
exactly with context event-ID allowlists: Sol has zero; Qwen has one physical
response with one invalid citation. That valid-schema response is retained as an
outcome, not discarded as an API failure.

The Sol statuses report no tool-event types; their item types are limited to the
permitted agent-message/reasoning categories. Complete raw CLI stdout was not
archived by the frozen reader, so absence of tool activity is checked against
those retained summaries rather than independently replaying a raw event stream.
The audit verifies submitted task-prompt bytes, not unexposed serving/system
instructions or an immutable Sol backend snapshot. Shared-prompt aliases remain
dependent reuse, not additional model calls. Artifact hashes and these bounds are
in `worker_review_reader_v2.json`.

## Explicit metric correction

The frozen `grade.py` token proxy uses Python's `re` for article word boundaries;
the pinned LoCoMo source uses the third-party `regex` package. The earlier 65
fixtures did not exercise this distinction. Combining marks and joiners expose
real global non-equivalence: 104 of 140 authored Unicode/category comparisons
differ for the frozen implementation. For example, the decomposed synthetic
prediction `a\u0301` versus reference `\u0301` scores 1 in the frozen proxy and 0
in the official source functions. This is an evaluator implementation issue,
not a new model behavior or an observed benchmark error rate.

`corrected_official_metric.py` is a separately versioned development-analysis
correction using the official `regex` semantics. Six pure tests pass all 205
comparisons (65 earlier fixtures plus 140 Unicode comparisons) against selected
AST-extracted official functions. The upstream file is pinned to commit
`3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376`, SHA-256
`8e3be5d57ff2ff9ec5cd05939592f468c5f3f1fd95d13e431932bdf6bf0fd6fd`.
No BERT or model is imported by the comparison. Recorded analysis versions are
NLTK 3.10.4, NumPy 2.5.4 and regex 2026.9.29; this checks source-function behavior
in that environment, not an entire original upstream dependency/runtime setup.

Every actual LoCoMo pilot output was also compared: **504 condition scores**,
from 237 physical response files. The corrected helper matches the official
source for all. The frozen proxy has **zero material measured differences** at
absolute tolerance 1e-12. There are 131 bit-level rounding-only differences,
with maximum absolute difference 1.1102230246251565e-16. Exact inequality must
not be reported as 131 meaningful Unicode corrections. Both frozen and corrected
values remain in the audit and analysis; the known global bug remains disclosed
even though no material score changes occur in this pilot.

No frozen driver, protocol, input, reader response or parsed output was changed.
Only a new analysis helper, tests and audit reports were authored. No full
reader/generation rerun is warranted by this evaluator correction. It does not
repair or relax the separately failed current-conflict calibration, establish
semantic accuracy, or support a publication-readiness claim.
