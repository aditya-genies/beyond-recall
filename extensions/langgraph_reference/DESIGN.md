# Native execution-framework reference

This extension compares the independent study's D1P1R1 contract with a native
LangGraph integration. It is not an implemented commercial memory agent or a
live-model benchmark. The frozen `study.py`, original 528 rows and reproduction
remain unchanged; extension runs have a separate denominator.

## Native versus application responsibilities

A real `StateGraph` has `choose_decision` and `apply_effects` nodes. A real
`SqliteSaver` stores the literal operations/targets and terminal outcome, using
`durability="sync"`. The coordinator's application decision/receipt tables stay
empty. A logging-only subclass delegates every write to native `super()` methods.
Generation eligibility, the shared source predicate, stable effect addresses,
cleanup and selection of the completed-checkpoint fast path are explicit
application integration logic. The separate effect store remains outside native
checkpoint transactions.

LangGraph's official [checkpointer guide](https://docs.langchain.com/oss/python/langgraph/checkpointers)
describes super-step checkpoints, synchronous persistence before the next step,
and empty `next` for completion. Its [persistence guide](https://docs.langchain.com/oss/python/langgraph/persistence)
distinguishes thread checkpoints from cross-thread stores. The official
[SQLite reference](https://reference.langchain.com/python/langgraph.checkpoint.sqlite/SqliteSaver)
identifies this backend as a local synchronous implementation. Those facilities
motivate this integration; they do not automatically supply memory-effect
idempotency, source eligibility or reset semantics. Accessed 2026-10-29.

## Semantic barrier correspondence

- After prepare: exit at effects-node entry, after the native planner-result
  checkpoint. This preserves the first plan across a changed-tape retry.
- First put / unavailable put or delete response: terminate or raise inside the
  effects node after the external SQLite transaction. Resume may repeat effects.
- After effects: exit before the effects node returns. Its completion has not yet
  been checkpointed, matching effects-without-terminal-receipt recovery.
- After finalization: exit only after native invocation returns and a completed
  checkpoint is observed. Completed redelivery explicitly reads that checkpoint.
- Reset before retry / between effects: execute the same generation guard and
  effect-ledger reset/cleanup rules used by every original factorial policy.

The native backend also writes input and super-step/task bookkeeping. These
writes are logged separately and excluded from participant put/delete W. Native
checkpoint-store settings may differ from the original coordinator settings;
there is no I/O latency, throughput or storage-overhead comparison. No process is
terminated within a checkpoint commit. Concurrent intents, checkpoint failure,
retention deletion, power loss and remote-provider durability remain untested.
The completed-checkpoint read path is chosen application behavior, not a claim
that every invocation on an existing LangGraph thread deduplicates input.
