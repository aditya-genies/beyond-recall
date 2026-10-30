# Case and witness schema

Every main row in `results/cases.jsonl` is one unique `(policy, profile, history)`
structural case. `case_catalog.csv` enumerates all 528 keys. These are specified
cases, not samples from a user or model population.

## Case fields

- `policy`: D/P/R bit string. D controls addresses of targetless puts; P retains
  the chosen operation list; R supplies a completed-intent receipt fast path.
- `profile`: insert, revise, retire or mixed. Their operation counts are 3, 3,
  4 and 4. Literal existing-target bindings remain fixed under either D setting.
- `history`: one of the 17 declared fault/control schedules. Lost-delete reply
  applies only to retire and mixed, leaving 66 cases per policy.
- `expected_facts`: the declared original-intent fact set, or the empty set for
  reset histories. This is a fixture oracle, not a natural-language truth judge.
- `physical_records`: terminal addressed rows, including origin and generation.
- `content_correct`: exact equality of terminal and expected fact sets. Identical
  physical duplicates deliberately collapse in this observation.
- `cardinality_correct`: equality of terminal row count and expected set size.
- `acknowledged`: final process exits normally and emits its acknowledgement.
- `selected_terminal`: conjunction of those three observations.
- `decision_continuity`: all observed chosen/loaded digests agree within each
  logical intent. This is separate from the terminal conjunction.
- `planning_invocations`: observed `decision_chosen` events.
- `committed_effect_calls`: committed participant puts/deletes from the audit.
  It includes repeated deletes of absent rows, and excludes reset/cleanup SQL,
  reads, coordinator work, tokens, monetary cost and elapsed time.
- `committed_actions`: independently inspectable effect-store audit rows.
- `attempts`: return codes, injected faults, tape setting, events and stderr for
  every fresh worker process in the case.

## Process events and state

Return code 0 reports a normal acknowledged outcome; 87 is abrupt `os._exit` at
an injected barrier; 74 reports a controlled committed-effect/reply exception.
The main exits occur after preparation, the first **put** (which can follow a
delete), all effects, or finalization. No interruption is inside SQLite commit.

`recovery.sqlite` stores conversation rows, the actual generation, retained
chosen decisions and optional receipts. P1 decisions remain after success for
both R settings. `effects.sqlite` stores memory rows and an audit committed in
the same single-store transaction as each put/delete. Participants never read
that audit to decide recovery. The checker does read it and the physical rows.
No transaction spans both databases.

The reset handshake changes real local generation state, deletes effect rows,
and permits the child to continue. Entry and post-loop checks provide the tested
terminal cleanup; they do not establish atomic visibility to transient readers.

## Five separate boundary probes

Receipt-only removal, decision-only removal, removal of both, a pre-store exit,
and an intervening external newer write are outside the 528-case product. The
last probe can pass the original-intent terminal oracle while overwriting the
newer value. Neither final content nor a receipt alone proves linearizability.

`reproduction/` and the archived GitHub Actions evidence repeat the same declared
cases. Their counts remain separate from the main coverage claim.
