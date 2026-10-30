# From a bounded observation to a defensible journal study

This is a proposed next study, not a new result or a Q1-readiness certificate.
The released v0.3.0 paper, its data and its source remain unchanged. This phase
uses public or newly authored data and personal/local model access only.

## Central question

Does delivery repetition change an agent's answers or actions even though the
underlying evidence has not changed? Can a practical admission policy prevent
that change while still accepting legitimate later observations and corrections?

State-level replay invariance and decision-level stability are separate. A
stochastic reader need not produce identical words on repeated clean runs.
Compare paired task outcomes against a clean-repeat control, not just literal
answer equality. Physical duplicates, evidence coverage and reader accuracy are
separate measured outcomes. Repetition may help, harm or have no effect.

The contribution under investigation is a reproducible causal evaluation and
useful conditional findings across real memory systems. Event identity,
deduplication, replay logs and epoch fencing are established mechanisms; adding
their names does not make a new algorithm. Current novelty remains unproven.

## Evidence needed

1. **A generalizable phenomenon.** Use published conversational histories and
   their labelled questions, with independently implemented memory backends.
   Compare the identical logical history under clean delivery, repeated delivery,
   and actual post-effect/pre-acknowledgement worker cuts. Keep logical event
   timestamps and source identity unchanged on a delivery retry. Do not call
   synthetic delivery multiplicity the natural production failure rate.
2. **A causal explanation.** Preserve source provenance through native writes
   and retrieval. Trace admission, retained records, selected evidence and the
   reader's task outcome separately. Include captured-decision replay to isolate
   storage effects and separately labelled fresh-extraction trials to expose
   model variability. Neither regime is a substitute for the other.
3. **Useful behavior against strong baselines.** Compare native behavior,
   complete-store exact-text admission, retrieval-time duplicate suppression,
   retained extraction, and an event-identity/provenance control. Use native
   atomic uniqueness or the strongest documented equivalent where available.
   Explain which controls are authored adapters. Measure latency, work and
   visible context as well as correctness. Do not rank weak applications as
   the best capabilities of their vendors.
4. **Legitimate-update controls.** A repeated delivery of one event is different
   from a new observation with identical text. Include a genuine later correction,
   new independent corroboration, repeated content after expiry, and a new
   authorized occurrence after revocation. A forever-hash filter must not receive
   credit for suppressing legitimate new evidence. These identity distinctions
   are known prior art, not a proposed new theorem.

## Workload and evaluation design

LongMemEval and LoCoMo provide public source histories, questions, reference
answers and evidence annotations. Pin revisions and inspect licenses before
redistribution. Do not infer a dataset license from its evaluation-code license.
Keep upstream data outside this repository by default and publish URLs, hashes
and original transformations. LoCoMo's ten conversations are ten conversation
clusters, not thousands of independent units. LongMemEval session overlap must
be measured before selecting independent units.

Start with structural feasibility and a development pilot. Oracle/evidence-only
histories support development and conditional reader tests; they must never be
reported as a full-history retrieval benchmark. Evaluate full cleaned histories
in the confirmatory phase. LongMemEval-V2 offers agentic trajectories but its
largest multimodal haystacks and prescribed model endpoints require a separate
resource/adapter check; they are not yet a confirmed runnable baseline here.

The participant receives only permitted history text, dates and ordinary source
identity. Strip `has_answer`, gold evidence/session lists, reference answers,
question categories and evaluator IDs from participant ingestion. Reference
labels belong to a separate evaluator. Do not let questions guide historical
ingestion except in a separately declared query-aware method.

Before confirmation, freeze corpus revisions, development/held-out partitions,
preprocessing, arms, failure schedules, context/token budgets, reader prompts,
primary outcomes, meaningful effect/equivalence bounds and analysis. Set sample
size using pilot variation and independent episode counts, not an arbitrary
number of repeated calls. A public internal freeze is not external preregistration.

Primary outcomes should be paired changes in labelled QA/action correctness and
evidence-supported correctness. Secondary outcomes include stale-answer rate,
abstention, distinct source-event coverage, duplicate context slots, work,
latency and context tokens. Report repeated observations within episode/model
as dependent; use an appropriate clustered paired analysis and uncertainty.
Do not treat a nonsignificant difference as proof of equivalence.

Use deterministic grading where the reference supports it, frozen rubric
grading for open answers, and blinded adjudication of a sampled/disputed set.
Keep grader inputs and raw decisions. Sol 6.1 grading its own outputs is not
independent human validation or broad model-family evidence. Prepare a blinded
expert-review packet; do not invent reviewers or send it without authorization.

## Feasibility and sequence

- Existing native Mem0, local embeddings, process-failure harnesses and backend
  checkers can be reused with explicit new specifications.
- Personal Codex access supports the already authorized Sol 6.1 reader/extractor.
  No company API credentials or hosted company services may be used.
- Local hardware has 24 GiB memory and approximately 44 GiB free disk at this
  assessment. Additional open-weight readers and Graphiti are candidates, not
  tested installations. Do not promise multiple frontier model families through
  one subscription or describe native-default configurations as reproduced
  when a study model bridge changes them.
- First measure development-pilot throughput, model-call/token requirements,
  failure coverage and grader disagreement. Derive a realistic full-campaign
  resource estimate before scheduling a large run. No new model calls have been
  made in this structural feasibility phase.

## Decision gates

**Gate A — novelty.** Review the closest memory/retrieval and distributed-replay
work, including beneficial repetition, before asserting a gap. Discovery of an
equivalent study changes the question; it must not be hidden by renaming terms.

**Gate B — measurement.** Verify native API integration, leakage exclusion,
source/event identity, original and faulted histories, raw results and grading.
Retain failed runs, inapplicable conditions and installation limitations.

**Gate C — significance.** Determine which tasks and conditions show practical
changes, including gains, losses and negligible effects. A result about duplicate
slots alone does not establish decision harm. If the practical effect is small,
report that and reconsider the contribution instead of increasing apparent sample
count or cherry-picking a favorable scenario.

**Gate D — intervention.** Establish whether an intervention improves the chosen
outcomes against strong baselines while preserving fresh updates and acceptable
cost. Standard identity mechanisms remain standard, even if their application
is useful.

**Gate E — manuscript and outside review.** Write one coherent empirical story,
move unrelated exploratory witnesses to supplementary material, obtain critical
domain feedback, and verify a specific journal's scope/index/category/year.
Passing the earlier gates can support a credible submission; it cannot guarantee
editorial acceptance or a citation outcome.

## Primary sources checked for this design

- LongMemEval: https://github.com/xiaowu0162/LongMemEval
- LoCoMo: https://github.com/snap-research/locomo
- LongMemEval-V2: https://github.com/xiaowu0162/LongMemEval-V2
- Graphiti: https://github.com/getzep/graphiti
- Ke et al., *Bridging the Preference Gap between Retrievers and LLMs*:
  https://aclanthology.org/2024.acl-long.562/ (the framework permits repeated passage IDs alongside selection/order; it does not isolate ordinary ingestion retries).
- *Let Them Sleep: Recursive Self-Pruning Memory for Long-Horizon LLM Agents*:
  https://arxiv.org/abs/2610.25561 (recent related work to audit fully; abstract
  inspection is not an independent replication of its reported outcomes).
- Prior exact-repeat/concurrency/expiry antecedents remain recorded in
  `../replanning_contracts/literature/mem0_antecedent_audit.json`.

This design is not externally preregistered, not a final frozen protocol and
not evidence that the proposed effects or remedies have succeeded.
