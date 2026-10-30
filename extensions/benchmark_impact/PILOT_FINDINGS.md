# Concrete findings and remaining limits

Aditya Mantri — independent research. This report extends the public working
study with a development pilot; it is not a journal acceptance claim, external
peer review or held-out confirmation.

## A directly inspectable answer failure

The released LongMemEval question asks how many of Emma's recipes the user has
tried. Its reference answer is **3**. The dated source history says **2** on
May 29 and **3** on May 30. With clean LlamaIndex retrieval, both Sol 6.1 and
Qwen answer **3**. After controlled delivery repetition, the selected context
has six duplicate event slots and omits the May 30 count; both readers answer
**2**. Every original stored record remains present and unchanged.

Sol produces the same clean-correct/retry-incorrect task transition in both
repeats. Source-event dedup restores the clean LlamaIndex prompt. Because the
complete prompt bytes are then identical, the protocol explicitly reuses the
archived clean response; this is input restoration, not a new recovery model
generation. The raw question key is `f65dcff812445376dbc709ef`.

## Finite-pilot task outcomes

All 447 distinct reader requests and all 75 grading batches completed. Those
responses map to 1,008 condition observations through documented prompt aliases.
They are not 1,008 independent questions. The underlying development set has
24 questions, with shared conversations and background sessions.

Automated task grading flags seven backend/reader/question loss combinations
across four underlying questions and eleven dependent repeat transitions.
It flags no gains in this task label. Retrieval-time event dedup restores the
clean task label in every flagged combination. Five LlamaIndex combinations
restore byte-identical clean prompts and reuse responses; two Mem0 combinations
use different dedup prompts and separately collected responses.

These labels remain **exploratory**. The authored calibration matched 12/12
task labels but only 10/12 current-conflict labels. The failed auxiliary gate
is retained; no definitive stale-state or semantic-efficacy claim follows.
Sol is a same-study judge, including of its own outputs, without human
adjudication. One Qwen out-of-context citation remains recorded.

The published LoCoMo token metric is reported separately. It does not uniformly
decrease: Qwen's Mem0 token score increases while its task labels are unchanged
on those LoCoMo questions. Token overlap, annotated support and semantic task
correctness measure different things. No significance test, population failure
rate or superiority of an elaborate repair is established.

## A second, mechanically verified layer

Visible duplicate removal need not restore the original ranking. It restores
all 24 dense LlamaIndex contexts here, but 16/24 Mem0 contexts retain different
event sets at the common returned-candidate budget. This comparison concerns
context identity, not a residual task loss: task labels still recover.

A separately frozen, explicitly post-hoc diagnostic repeats all 24 Mem0 queries
on copies of clean and replayed stores. With a full candidate pool, 10/24 selected
event sets and 17/24 event orders still differ after event dedup. Original-point
semantic scores and entity contributions remain stable; normalized BM25 and
final scores change in all 24 queries. All ten changed sets contain a strict
lost/gained score-order reversal, rather than only a tie-order change.

The pinned local Qdrant implementation computes inverse document frequency
from physical sparse-vector document counts:

`idf(t) = log(1 + (N - df(t) + 0.5) / (df(t) + 0.5))`.

Extra physical copies change `N` and term document frequencies although the
logical source-event set is unchanged. Mem0 combines semantic similarity with
query-normalized BM25 additively; the tested path is not reciprocal-rank fusion.
Mem0 internally over-fetches four times the requested limit. The full-pool
diagnostic removes that candidate truncation as an explanation of the residual.

In a second counterfactual, duplicate records remain searchable, but Qdrant's
native IDF corpus parameter uses the original clean physical IDs. All 24 full-pool
contexts and all original-point score components return to clean values within
the declared numerical tolerance. This is a mechanism diagnostic using known
clean IDs, not an oracle-free deployed method or a new IDF algorithm.

The independent auditor reconciles native payloads, point membership, score
equations and 12,320 original-point comparisons. The 120 diagnostic queries
reuse the same 24 questions; they are not additional task samples. See
`worker_review_ranking_audit.md` and the two post-hoc protocol directories.

## What is novel, and what is established

Duplicate documents distorting IDF and relevance ranking are established IR;
[Frieder, Grossman and Chowdhury (2003)](https://ir.cs.georgetown.edu/publications/downloads/NCA03-Keynote.pdf)
discuss this explicitly in section 2. Recent duplicate-evidence studies,
including CUE-R and Schelpe's byte-exact-deduplication study, are mandatory close
comparisons. The latter also studies an indexed high-redundancy corpus.

The candidate contribution is a reproducible **native delivery replay → stored
multiplicity → corpus-statistics drift/selection change → task outcome** trace,
with distinct storage, retrieval and answer contracts. It is a bounded systems
measurement and conformance contribution. New mathematical principles, first
discovery of duplicate harm, a novel deduplication algorithm, natural production
incidence and Q1 readiness are not established. The complete source-grounded
novelty assessment is in `literature/posthoc_ranking_probe_v1_audit/`.

The storage participants are local Mem0 `infer=False` and persisted raw-document
LlamaIndex. This does not reproduce inferred-memory defaults or managed services.
The recovery boundary is an actual worker exit after native effects but before
the study's logical batch acknowledgement, not a network-packet or mid-commit
failure. Full independent confirmation and external expert assessment remain
necessary before a strong journal submission claim.
