# Independent adversarial audit of the conflict-contract extension

## Disposition

The frozen engine and its 84 cases support the stated bounded contract examples.
No engine or raw-result correction was needed. The original checker had material
assurance gaps; the revised checker closes them and all recorded summaries and
witness values remain unchanged. Engine SHA-256 remains
`4555c55a83b5a2c734a50592f584e54bc24955be707467755088d91b93f9660d`.

The 84 cases are separate from the original 528 and the native reference's 66:
48 specified sequential call linearizations, 20 named witnesses, and 16 actual
two-process rendezvous cases. The six A0<A1/B0<B1 call orders exhaust that small
call-order model, not arbitrary concurrent-program schedules. There is one
uncontrolled execution for each race condition; no race-frequency, fairness,
throughput or production-reliability inference follows.

## Confirmed checker gap and repair

Before revision, changing a recorded plain-version-CAS conflict to `replay`
passed verification without changing its database. The accepted forgery is
recorded in `checker_gap_demonstration.json`. The checker previously mostly
trusted status strings, compared only the serialized effect-list length, omitted
receipt result validation, and did not establish the exact 84-case/source pin.
Those gaps could corrupt scientific replay/conflict summaries even with a valid
effect ledger.

The revised `check.py` does not import the participant. It independently specifies
the four operation contracts and expected fixtures, then requires every observed
status, changed flag, complete state/effect snapshot and receipt body/result to
match the contract. Sequential calls are checked in declared order. A two-process
case must match at least one of its possible transaction orders; observation-list
order is not mistaken for commit order. It also checks exact structural coverage,
manifest/source hash, child-operation files, successful child exits and rendezvous
artifacts. Databases are opened read-only.

Reports now require an explicit `--report` destination, keeping derived audit
output separate from the frozen archive:

```sh
python3 extensions/conflict_contracts/check.py \
  --out extensions/conflict_contracts/results \
  --report extensions/conflict_contracts/audit_verification.json
python3 -W error::ResourceWarning -m unittest -v \
  extensions.conflict_contracts.test_contracts \
  extensions.conflict_contracts.test_audit
```

All 19 methods pass: eight existing contract tests and eleven new audit checks.
Eight new checks reject falsified status/receipt/snapshot/identity/coverage/source
records; one confirms read-only verification; one injects an SQLite receipt-insert
abort and verifies rollback of the mutation and effect audit. The rollback test is
a bounded transaction-error check, not a process/power-loss experiment or another
case in the 84-row scientific archive. An additional boundary check confirms that
a rejected operation does not bind its identity before a successful receipt exists.

## Scientific interpretation and important boundaries

- In the newer-write witness, unconditional upsert restores the original value
  while overwriting a later accepted write. An original-value predicate can reward
  that outcome. This extension checks a scalar original-intent content condition;
  it does not rerun the entire main campaign's C/K/T measurement.
- The version precondition supplies stale-write rejection. The atomic operation
  receipt supplies recognition of a previously successful operation after a newer
  write, without issuing it again. Do not attribute both properties to receipt
  presence alone.
- The tested version-CAS interface returns a conflict on its own successful
  reissue. This is a property of that interface, not a general impossibility result
  for every CAS-based reconciliation design.
- The effect-store receipt is per operation and commits atomically with that
  operation in one SQLite transaction. It differs from the original factorial
  R mechanism, a whole-intent completion receipt in a separate coordinator file.
  The new guarantee must not be transferred to the original separate-store receipt.
- Changed-argument rejection binds a successful operation's retained receipt. A
  rejected CAS attempt stores no identity reservation, so the same identifier can
  later succeed with revised arguments/preconditions. The frozen specification's
  unqualified changed-arguments sentence must be read with this scope; no frozen
  file is rewritten. A new unit boundary check confirms this behavior explicitly.
- Here acknowledgement means the operation API's applied/replay outcome. A child
  may exit normally while returning a legitimate precondition conflict; process
  exit success is not the main campaign's acknowledgement metric.
- The named lost-reply witnesses reissue a committed call, modeling an unavailable
  response. They do not actually drop a network response or terminate a process at
  a transport boundary. The two-process races are actual subprocess executions.
- A delete is a value-null tombstone; the state row and durable monotone version
  remain. Delete/recreate ABA protection depends on retaining that version. A
  physically deleted/recreated record whose version resets is not evaluated.
- Value-CAS correctly implements a weaker value predicate. Its acceptance after
  ABA demonstrates that predicate's lack of a version-history requirement; it is
  not an implementation failure relative to its own declared contract.
- Atomic mutation/audit/receipt placement is visible in the one-database transaction
  and supported by the injected-abort test and SQLite semantics. No mid-commit
  process crash, distributed atomic settlement, whole-plan transaction, receipt
  reclamation, multiple targets or arbitrary interleaving proof is tested.
- Receipts are retained indefinitely for this finite experiment, identifiers are
  synthetic and collision-free by assumption, and versions never decrease.

These are familiar precondition, deduplication, transaction and ABA distinctions,
not a newly invented concurrency algorithm. The useful contribution is making
which invariant an oracle rewards—and which recovery evidence a contract
recognizes—explicit and reproducible. The independent ledger/model checker is
stronger evidence consistency, not a formal proof of arbitrary executions.
