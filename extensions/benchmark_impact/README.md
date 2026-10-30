# Delivery retries and downstream memory use

This is a new **development pilot**, separate from the released v0.3.0 working
paper. It is not held-out confirmation or evidence of Q1 submission readiness.
The released paper and original experiments remain unchanged.

The question is whether repeated delivery changes answers despite unchanged
source evidence, and which controls prevent that while preserving legitimate
later observations. Duplicate evidence, idempotency and occurrence identity
have substantial prior art; a new algorithm or breakthrough is not established.
The closest-source audit is in `literature/contribution_assessment.txt`.

## Current execution state

The fixed development selection contains 24 questions from public LoCoMo and
full cleaned LongMemEval-S histories, across 14 participant scopes. Two native
raw-document participants use Mem0 `infer=False` and a persisted LlamaIndex
vector index. No extraction model is used in these native writes. This scope
does not reproduce inferred-memory defaults or managed cloud services.

The version-2 native campaign completed 308 processes, including 84 actual
post-effect/pre-acknowledgement exit-87 cuts. An independent implementation
audited 196 retained stores and 11,520 candidate rows. All original physical
record IDs and payload/vector fingerprints survive; native delivery repetition
adds copies, and both sequential admission guards suppress those copies.
These are controlled failure schedules, not measured production failure rates.

Of 24 questions per backend, distinct selected source events decrease for 20
Mem0 and 16 LlamaIndex cases after retries. Annotated answer-support coverage
decreases for 1 of 23 available Mem0 cases and 4 of 23 LlamaIndex cases; one
unanswerable case per backend has null support. These are descriptive pilot
comparisons; the two backends share questions and public embedding technology.
They do not establish reader correctness harm.

Reader collection is in progress: requested Sol 6.1 through authorized personal
Codex access, and pinned local Qwen3-4B-4bit weights. The 336 condition contexts
reduce to 149 distinct complete prompts. Two Sol repeats and one deterministic
Qwen repeat are planned per distinct prompt; identical-prompt aliases reuse
the same responses and are not independent samples.

**The auxiliary grading calibration failed.** The first actual Sol calibration
matched 12/12 authored task labels and 10/12 current-conflict labels. Two
numerical-error fixtures were incorrectly called current-state conflicts.
Expected labels and failures are retained. This blocks definitive semantic or
stale-state efficacy claims; pilot task judgements remain exploratory. No
same-study automated judge is presented as human or independent peer review.

## Protocol and evidence

`development_pilot_v2/protocol.json`, its SHA file, frozen source copies,
`reader_protocol.json`, `grading_protocol.json` and `analysis_plan.json`
separate participant inputs from evaluator labels. The internal freeze was
made before benchmark reader calls; this is not external preregistration.
Reader prompts hide backend, intervention arm, question category and gold
locations. They use a common 60-candidate pool, at most 10 whole records and
12,000 UTF-8 bytes for the serialized evidence array, not an asserted token
budget.

The first attempted full campaign is preserved as `development_pilot_v1`.
Concurrent initialization of a shared embedding cache caused a harness error;
no reader or grading calls were made in that version. Version 2 uses a separate
manifest-bound cache per sequential backend/history participant. See
`abandoned_run.json` and the retained frozen version-1 sources.

`worker_review_pilot_v2.json` is the independent physical audit.
`worker_review.md` explains runtime and negative-test coverage. The hosted
boundary-check workflow is configured for 57 offline methods, which passed
locally; the new hosted run is still pending. Native model/storage
campaigns are explicitly outside that hosted job's scope; local native
feasibility covers another six methods. Repeated tests are not new samples.

Raw native stores and embedding caches are kept out of Git because of size;
they are retained locally for a separately verified research archive. They must
not be replaced by reconstructed values or described as already downloadable
until an archive has actually been published and verified.

## Reproduction entry points

`fetch_public_data.py` downloads only public pinned URLs to an external cache
and rejects mismatching files. `data.py` constructs the participant/evaluator
boundary. `pipeline.py` prepares a fresh output directory, executes the native
campaign and constructs contexts. `reader.py` collects frozen reader outputs.
`grade.py` calibrates and grades blinded archived responses. `summarize_pilot.py`
reports descriptive paired outcomes, failures and the failed auxiliary gate.
Never overwrite a frozen run or edit its sources to force a verification pass.

This independent study uses public or newly authored data and authorized
personal/local model access. It uses no employer application code, private
conversations, company API keys or hosted company services. See
`THIRD_PARTY_DATA.md` for dataset attribution, modifications and upstream terms.
