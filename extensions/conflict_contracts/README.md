# Bounded conflict and replay contracts

Synthetic facts and actual local SQLite transactions compare unconditional
upsert, value comparison, monotonic-version comparison, and version comparison
with a per-operation receipt atomically stored with its mutation. These are
established techniques, not a proposed new algorithm.

Coverage: 48 bounded first-before-retry linearizations, 20 named witnesses, and
16 two-process races =84 cases. Six sequential orders preserve first-before-retry
for each of two intents. Race participants rendezvous before writing; SQLite
serializes transactions and either process may win. Reply-loss witnesses model
a reissued call after a commit; no transport packet is dropped. Value null is
a tombstone retaining its version.

Three obligations are distinct:
- Original-intent content equality can reward overwriting a newer value.
- A version guard rejects stale writes but cannot alone acknowledge its own
  historical successful effect after an uncertain reply.
- An atomic retained receipt acknowledges that effect without overwriting a
  newer value. Value-only comparison misses ABA changes.

A successful receipt binds its operation identity and arguments. A rejected
comparison stores no binding, so an identity can be reused with changed arguments
before its first success. The frozen specification's unqualified rejection phrase
requires this condition; see audit.json.

Receipts are retained for the bounded run. Successful receipts/mutations commit
in one transaction; versions are durable and monotonic. No whole-plan atomicity,
distributed exactly-once guarantee, reclamation, mid-commit crash testing, or
production performance is claimed.

Run focused tests and verify archived evidence:

    python3 -W error::ResourceWarning -m unittest -v extensions.conflict_contracts.test_contracts
    python3 extensions/conflict_contracts/check.py --out extensions/conflict_contracts/results

Reproduce into a fresh directory:

    python3 extensions/conflict_contracts/experiment.py prepare --out extensions/conflict_contracts/my-results
    python3 extensions/conflict_contracts/experiment.py run --out extensions/conflict_contracts/my-results
    python3 extensions/conflict_contracts/check.py --out extensions/conflict_contracts/my-results

The separate verifier reconstructs transitions from raw SQLite effects without
importing the participant. New races can choose different winners. Source was
frozen before execution; subsequent checker improvements do not change the
engine or archived cases.
