# Pre-pilot worker, grading and raw-native review

This is same-study checking of the new benchmark-impact study. It is not outside
replication, an official benchmark score or evidence of a reader benefit/harm.
This review made no LLM request. Tiny runtime tests used real cached public BGE
inference on authored synthetic strings; the completed-pilot audit made no model,
embedding or native query calls and did not rerun an experiment.

## Tests and native feasibility

`test_worker.py` has 32 tested methods: 15 worker/pipeline boundaries, six native
runtime methods, eight no-request grading methods and three independent raw-audit
forgery methods. All pass. The full initial worker suite passed 21 methods in one
run; the additional grading/auditor methods were then executed separately. Logs
preserve that chronology rather than claiming a single 32-method execution.

Both actual research runtimes were used: Mem0 through `.venv-memory` and
LlamaIndex through `.venv-impact`. The latest tiny native fixture run used 24
fresh subprocesses, including four actual `os._exit(87)` cuts and two expected
manifest-mismatch rejections. Each store fixture had its own newly created cache.
The four original events included two independent same-text occurrences and a
later correction. Direct SQLite/Qdrant point decoding and Llama docstore/vector
JSON inspection, rather than only worker snapshots, confirmed these behaviors:

- Closed baselines reopen and query with their original physical identities and
  event/body/source/date values. Byte-for-byte copied stores retain those IDs.
- A native retry of one source event yields 4→5→6 physical records across cut and
  fresh-process resumption; retained event admission yields 4→4→4.
- A legitimate new same-text occurrence plus a new correction adds two records
  under event admission, versus one under the exact-content control. This is an
  expected known tradeoff, not a discovered new algorithm or dataset effect.
- Cache manifest mismatch rejects without a native write; the original manifest
  reopens correctly afterward. Rejected construction releases its SQLite write
  transaction. An unbound preexisting vector cache cannot be relabelled.

Boundary tests also reject evaluator fields before provider construction, reject
non-native initialization modes and replay writes to the clean arm, enforce the
exact 12,000-byte serialized evidence-array limit, preserve whole records,
require the frozen split hash, and reject incomplete/mislabeled native execution
records and false completion counts. Those checks were repaired by the root
agent before the applicable freeze. The reader's query-date/blinded prompt and
out-of-context-citation retention policy are exercised without generating output.

All 80 files in the recorded local public embedding manifest hash-match during
this review. This is an artifact inspection, not a traced loader proof. The
current pipeline additionally verifies recorded snapshot assets before preparation
and fixes the public cache path. Runtime tests bind caches to a tiny test manifest;
they do not substitute it for the study's model-artifact manifest.

## Grading checks and actual calibration failure

Mocked transport tests accept grader `decisions` rather than forcing the reader's
answer schema, reject wrong coverage/IDs/fields/types/enums, and retain invalid
results as `ERROR`. Backend, arm, reader identity, expected labels and human
fixture names do not enter the judge payload. Calibration IDs are opaque. A
shared physical answer is graded separately for each question/reference pair.
Frozen item packets protect references, contexts, aliases, split, responses and
items; tampering prevents judge invocation. Mocked transport is explicitly not a
model observation.

The LoCoMo proxy matched 65 authored comparisons across categories 1–5 against
AST-extracted functions from the pinned public evaluator. The test avoids its
BERT import and imports only the required stemmer/normalization dependencies.
This validates the published token proxy transcription, not semantic accuracy.

Version 2's actual first personal Sol calibration request is retained separately.
Of twelve authored fixtures, task correctness matches 12/12 and current-conflict
matches 10/12. The judge incorrectly calls the 19-versus-18-day tolerance example
and the 80-versus-18-day wrong answer current-state conflicts. Expected labels
remain unchanged: an ordinary factual/count error is not necessarily a stale
current-state assertion. The auxiliary calibration gate is **failed**. No
independent human or broad-family validation follows from the task matches, and
no evidence-supported label was independently calibrated by these fixtures.
Exploratory task/throughput collection must retain this gate and cannot become a
definitive semantic/stale-state efficacy claim. A later repair requires an
explicitly different development/confirmatory version.

## Independent completed version-2 native audit

`worker_review_pilot_audit.py` checks the retained native artifacts read-only.
It first emitted `NOT_READY` while only 256 execution manifests existed and did
not inspect in-progress stores; that report is retained separately. After the
completion marker, the independent audit **passes** protocol
`dd5280476348b1b60ec9bd91626b6b909b8ae4697233f1a6f8a0a8631035d9ea`:

- 14 source-history scopes, 28 native participants, 308 execution manifests and
  84 actual expected exit-87 results;
- all 196 clean/cut/resumed native stores, covering 14,320 original event records
  across the two backend copies and 3,840 replayed events per delivery across
  those copies;
- native counts N→N+M→N+2M and both admission controls N→N→N in every scope;
- preserved original physical IDs and complete Qdrant point-byte or Llama
  node-plus-vector fingerprints through every cut/resumption;
- unchanged logical event IDs, literal bodies, source occurrences, dates and
  body digests; exact receipt/snapshot reconciliation and zero recorded extractor
  calls in the declared raw-document paths;
- all 11,520 candidate rows from 192 retained query invocations match persisted
  physical identities/payloads. Candidate ranking is not independently recomputed.

The independent auditor derives expectations from the frozen participant/retry
inputs and source-selection rule. It does not import transition/metric functions
from the worker or pipeline. Its shared raw-store reader functions live in the
test module; their code is separate from the adapters being checked. Negative
fixtures reject changed dates/bodies/sources/multiplicity, absent or forged
candidate records, nonfinite scores and premature completion assumptions.

Version 1's partial native run exposed a shared-cache first-open WAL-initialization
race. The root agent retained that partial run and frozen sources, with no reader
or grader calls. Version 2 uses one cache per backend/history scope; sequential
phase processes share it, parallel scopes do not. Earlier successful serial tiny
fixtures did not establish cross-scope concurrency safety. This history must not
be replaced with an invented all-pass first attempt.

## Descriptive summary review

The updated summary code averages repeats within questions before questions,
reports paired transitions and clean-repeat variation, retains missing outcomes,
and distinguishes available cases from reader-failure-as-incorrect sensitivity.
Shared-prompt aliases are dependent, not extra requests. Its failed-calibration
gate remains explicit. The reviewed repairs avoid attaching grades to failed
reader statuses, report auxiliary yes/no/uncertain counts separately, and derive
serialized context bytes plus application-phase versus whole-process timing from
retained artifacts. No significance, population/IID interval or vendor default
claim is supported by these descriptive pilot summaries.

## Retained development errors and scope

`worker_review_unit_initial.log` retains two genuine verifier-forgery failures
that the root fixed (false completion counts and backend labels). The first test
invocation's module-path mistake and an early grading fixture missing the newly
required grading-protocol hash are retained as test-harness errors, not system
failures. The initial native test round used one cache per backend fixture; the
subsequent reported round strengthened this to a new cache per individual store
fixture. No count is pooled across those development rounds.

The released v0.3.0 source, data and PDF were not changed by this review. Root
owns execution changes/freezes; this reviewer owns tests, audit code and review
notes only. There is no opaque quality score or publication-readiness certificate.
