# Admission, retrieval exposure and recovery boundaries

This independent extension uses authored synthetic preferences, public source,
local storage and a personal Codex account. It contains no employer application
code, private conversations, internal PRs or company credentials. Its name is a
working directory label; it does not imply a new replanning algorithm.

The most informative observation is a conditional admission-to-retrieval chain:
the tested Mem0 path builds its literal suppression hashes from ten candidates;
re-emitted facts outside that window can create exact copies; those copies can
occupy retrieval slots even when every queried exact target remains present.
The counting argument and deduplication principles are established ideas. Public
Mem0 discussions already describe related semantic duplicate risks. The new
evidence must be read with the [closest-source audit](literature/mem0_antecedent_audit.json)
and [bounded claim ledger](new_study_claim_ledger.json).

## Separate evidence layers

- [Controlled native Mem0](mem0_reference/README.md): 96 parameterized executions,
  288 native adds; controlled extraction and hash/BGE embedding factors. All final
  fact sets match. The native 40-fact sequence has 40, 70 and 100 physical records.
- [Live native Mem0](mem0_reference/live_checker_review.md): 28 actual requested
  Sol 6.1 calls, four post-API worker exits and 48 fresh-process retries. Twenty-four
  retries reuse recorded responses and are not new model samples. Native fresh
  extraction adds 91 literal copies and one semantically ungraded formulation;
  both authored controls add none.
- [Retrieval exposure](mem0_reference/retrieval_checker_review.json): 1,008 native
  searches across all 84 baseline-fact queries, four store states and three
  budgets. All exact targets are present. At N40/K10, native returns 400 slots
  with 247 summed per-query distinct strings versus 400 in baseline/controls.
  There are 213 cells with duplicates but only 201 with reduced distinct strings.
  The after-close computational reproduction repeats these same samples.
- [MemTX](memtx_reference/REPORT.md): 24 traces inspect snapshot reads and an
  empty-snapshot stale-write branch in one pinned public implementation. The
  94 unchanged non-tau2 tests pass after documented dependency fixes; the full
  suite has a retained missing optional tau2 collection error. These probes do
  not refute the paper's action-gating or cascade-repair invariants.
- [SQLite/Redis](backends/README.md): 104 declared cells, 96 executed and eight
  explicit N/A cells; 154 fresh requests and ten actual client exits. Authored
  contracts distinguish grouping from rollback, and historical acknowledgement
  from current authority/visibility. This is not vendor ranking or new Redis
  behavior.

Counts from these layers and the earlier study are never pooled into a failure
rate, test score or independent sample count. Checkers validate evidence and
declared classifications; their PASS labels do not mean every tested system
satisfies every desired property. Expected failures and negative outcomes remain.

## Industry comparison and scope

The study tests documented consistency/recovery contracts and real public
implementations. It has no formal industry certification and does not claim to
have passed every industry standard. Default hosted Mem0, distributed Qdrant,
cluster Redis, power loss, semantic answer quality, downstream agent harm,
latency, token cost and population incidence are not tested. The exact-literal
queries and post hoc selected exposure states are deliberately narrow. Neither
more tests nor an implementation discrepancy alone establishes a leading-journal
contribution. Independent replication and broader useful generalization remain
open research requirements.

## Provenance and workflow

Each campaign freezes its own source/specification before its measured execution.
Designs were motivated by source inspection and earlier observations, not an
external preregistration. The backend design additionally followed a complete
development dry run; this is explicitly recorded. Native Mem0, public MemTX and
the original primary files are pinned without modifying their implementations.
The old primary engine and case hashes remain unchanged.

PaperOrchestra's literature, plot and skeptical-refinement workflow was continued
on the supplied experimental materials. User authorization explicitly allowed new
experiments and required named authorship, overriding the workflow's default
presentation-only refinement/anonymity choices. AI-assisted checking and writing
do not constitute external peer review or acceptance. The final paper's own
limitations and source/claim review govern the scientific interpretation.

Dependencies, embedding-file hashes and public source URLs are retained. Native
model prompts follow the upstream Apache license and attribution notice. Model
weights, third-party full papers, installed environments and unlicensed MemTX
implementation source are not redistributed. See individual instructions and
the separate hosted verification scope in [ci/README.md](ci/README.md).
