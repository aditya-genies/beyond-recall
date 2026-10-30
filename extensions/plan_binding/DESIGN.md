# Recorded-plan address-binding follow-up

This is a **posthoc exploratory integration follow-up**, designed after inspecting the already recorded model outputs in `extensions/sol_pilot/registered/`. It is not preregistered, makes no additional model requests, and is separate from the frozen primary campaign and the pilot's before-call protocol. The model response archive is the only source of plans.

## Question and complete case set

Can a replanned remaining operation list reuse a completed operation's positional address? Take original repeat 0 in each of the six archived scenarios as the original plan, and each of that scenario's two partial-snapshot responses as a recovery plan. Include all 12 pairs without filtering. Each pair has three SQLite integrations, for 36 integrations total; these are paired constructed controls, not independent population samples.

Commit the first original operation, close the database connection, and require the public record snapshot to equal the exact archived partial input before recovery. Then execute one of:

1. `replan_positional`: the recorded partial response, assigning each targetless put its stable address from the intent and its zero-based position in the newly returned list.
2. `replan_fresh`: the identical partial response, using disjoint fresh addresses for targetless puts in this recovery execution.
3. `retained_positional`: the entire original repeat-0 plan with its original positional addresses, including replay of the first operation.

Every arm uses the same original records, original first committed operation, partial snapshot, and named-target bindings. There are no completion receipts in this extension. Each operation is one actual SQLite transaction, with its before/after record and operation recorded in the same transaction. The coordinator is this finite replay program, not a model or durable-execution framework. The follow-up tests no abrupt process death, mid-commit fault, storage failure, or semantic memory quality.

## Address control

The physical stable targetless address is `pos:` followed by SHA-256 of canonical JSON `["positional-v1", intent, slot]`. The intent is the scenario name and `slot` counts every operation, including named puts and deletes. A fresh recovery address is `fresh:` followed by SHA-256 of `["fresh-v1", case_id, slot]`; the disjoint namespace guarantees freshness without attributing the effect to random collisions.

The pilot exposed a newly created first record as `<scenario>-first-effect`, rather than as a hash. A common bijective public-ID binding maps that opaque pilot ID to the actual stable slot-0 address. Named initial records have their own separate `named:` hash addresses. Named targets always resolve through this same binding in all arms. Thus `preferences-first-effect` is the public name of the already committed slot-0 record and a positional recovery slot 0 reaches **that same physical record**. This is necessary for a valid test; initializing an unrelated pilot ID alongside a new hash address would mask aliasing. Public-ID renaming is not itself the experimental factor, and the exact partial input is checked after projection from physical records.

## Observations frozen before replay

The primary observation is a **cross-key targetless overwrite of the completed prefix record**: a recovery targetless put resolves to that prefix's physical address while an existing record there has a different literal fact key. Report the exact before/after records, operation slots, and derived addresses. A hash collision is not required: the same `(intent, slot)` is deliberately reused for a different operation after replanning.

Also report prefix binding preservation (for an initial put, its address still holds its original fact key; for an initial delete, its target remains absent), and literal prefix-record preservation as a separate diagnostic. A changed value string, a synonymous key string, or a different operation list is **not graded as a semantic error**. No content-accuracy or final-terminal-conformance score is computed. No expected alias count is enforced as a success criterion.

## Falsification and checks

The fresh-address arm isolates address reuse while holding the replanned response fixed. The retained-plan arm checks the combined original decision/slot binding. Scenarios whose first operation is a named update or delete provide boundary cases where the completed prefix is not a targetless slot-0 record. The checker separately reconstructs all executions from archived raw response files, physical SQLite tables, and committed audit rows without importing participant execution or observation functions. Negative tests cover a mismatched partial snapshot, a same-key literal value change, and a fresh-address cross-key put. Freeze this design, runner, checker, tests, and all pilot input hashes before the first replay; execution must refuse a changed freeze or an existing output directory.

## Interpretation boundary

A positive case establishes that these actual recorded remaining plans can trigger this address-binding bug under the declared positional-address integration. It does not show that the model made an inappropriate remaining plan, that this is a model drift rate, that every stable-address system fails, or that a memory product uses these semantics. The semantic act of omitting an adequately represented prefix can be reasonable; blindly reusing list positions is the integration hazard. Existing primary results and raw pilot evidence must remain byte-identical.
