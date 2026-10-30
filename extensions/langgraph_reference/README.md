# Native LangGraph execution-framework reference

This is an additional execution-framework comparison, not a commercial memory
agent or live-model baseline. The original 528-case factorial campaign remains
unchanged. This extension runs its own 66 matched profile/history cells against
the original D1P1R1 policy using the same independent synthetic inputs, decision
tape, generation rules and separate effect ledger.

## Recorded result

All 66 native cases pass content, physical cardinality, selected terminal
conformance, decision continuity and final acknowledgement. They produce 66
planning invocations and 275 committed participant put/delete calls across 116
worker subprocess attempts, including 32 abrupt exits. All seven case-level
metric values match D1P1R1 in every matched cell. The verifier observes 260 actual
native checkpoint rows. The application coordinator decision and receipt tables
remain empty: native checkpoints contain the plan and terminal result.

These observations concern matched semantic barriers, not failure during a
checkpoint write. Generation cancellation before resume can leave an unfinished
native checkpoint; the external application guard cancels the stale attempt.
This is explicit integration behavior, not a claim that every internal graph
state is completed or that LangGraph supplies generation authority automatically.

## Reproduction

From the repository root, create an isolated environment using public packages:

```sh
python3 -m venv .venv-framework
.venv-framework/bin/python -m pip install --index-url https://pypi.org/simple \
  -r extensions/langgraph_reference/requirements.lock.txt
.venv-framework/bin/python -W error::ResourceWarning -m unittest -v \
  extensions.langgraph_reference.test_native
.venv-framework/bin/python extensions/langgraph_reference/runner.py campaign \
  --out extensions/langgraph_reference/my-results --workers 4
.venv-framework/bin/python extensions/langgraph_reference/verify_results.py \
  --results extensions/langgraph_reference/my-results \
  --out extensions/langgraph_reference/my-verification.json
```

The recorded environment uses Python 3.14.3, SQLite 3.51.2, LangGraph 1.2.18,
langgraph-checkpoint 4.3.1, langgraph-checkpoint-sqlite 3.1.2 and langchain-core
1.7.3. Installed public source files and dependency versions have recorded hashes.
The reference's framework SQLite backend uses WAL; the original fixture/effect
connections use their unchanged settings. No latency, I/O throughput or storage
performance is compared.

## What is native and what is supplied

A real `StateGraph` runs `choose_decision -> apply_effects`. A real `SqliteSaver`
with `durability="sync"` persists the planner result before the effects node. A
completed native checkpoint is the receipt-like result used on redelivery. A
logging-only subclass delegates all persistence to the native implementation.
It does not implement a private checkpoint format or recovery dictionary.

Source eligibility, literal target bindings, stable effect addresses, generation
checks, cleanup, choosing the correct thread identity and selecting the terminal
checkpoint fast path are application logic. The external effects are outside
native checkpoint transactions. `DESIGN.md` records the exact barrier mapping,
public primary documentation and excluded histories.

The nine focused tests include a real abrupt child exit and fresh-process
resume, independent native-state verification, completed checkpoint reuse,
generation changes, unavailable replies, deterministic repeated effect state,
and detection of a plan altered through the public native update API. Native
checkpoint identifiers/timestamps/PIDs are not claimed byte-deterministic.

## Evidence files

- `results/frozen_spec.json`: source/version pins, graph and integration scope.
- `results/cases.jsonl`, `results/summary.json`, `results/state/`: new run evidence.
- `verification.json`: independent original-metric and native-checkpoint audit.
- `tests.log`, `tests.json`: nine focused test-method outcomes.
- `preservation.json`: unchanged original-source/result checksum verification.
- `provenance.json`, `requirements.lock.txt`: public dependency/source provenance.

The comparison supplies evidence that native framework persistence can implement
this selected application contract. Equal outcomes do not establish broad system
equivalence, framework superiority, semantic memory quality, arbitrary crash
safety, concurrency isolation or production reliability.

The two-node decomposition is intentionally matched to the original plan/apply
protocol. Per-operation tasks or additional graph nodes could change replayed
work counts and are not evaluated here. W parity is not framework optimality.
