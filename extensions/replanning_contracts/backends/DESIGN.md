# Cross-backend contract campaign — approved finite protocol

Status: parent reviewed and approved this finite protocol on 2026-10-29.
Implementation and focused checks precede the source/spec freeze and campaign.
No original experiment changes.

## Executable public backends

- SQLite 3.51.2 through Python 3.14.3, explicit `BEGIN IMMEDIATE`, `COMMIT` and
  rollback on an exception. The experiment owns a newly created file retained with its case evidence.
- Redis 7.2.17, official image digest
  `redis@sha256:2c933526722b4126a61d5c170f766dc159adf97682f0b1cbbc27b1666ba96d84`,
  using redis-py 8.1.0 and native `EVAL` (campaign); `WATCH`/`MULTI`/`EXEC`
  are additionally checked in the development feasibility probe. A fresh server,
  random study-only password, dedicated Docker bridge, loopback ephemeral port
  and fresh AOF volume are created; cleanup removes all three owned resources.
  Docker uses an empty temporary client-auth config and explicit local socket.

`development_feasibility.json` records six tiny capability probes, including an
actual WRONGTYPE after a successful script write and a controlled AOF restart.
These are development observations, not campaign cases. The initial unpublished
port attempt is retained separately; it contributed no scientific outcome.

## Shared logical request, state and outputs

One target and one authority domain per case. A prepared request consists of an
operation identifier, literal value/action, target identifier, expected target
version, expected authority epoch and a canonical body/digest. Preparation is a
durable body binding, separate from a successful receipt: a retry must not rebase
its version or replace arguments under the same prepared identifier. A legitimate
new decision needs a new identifier (or an explicitly different rebase contract).
All profiles share a durable caller-side prepared-body journal, checked on every
request before backend access. This journal, its records, and its source are
audited; no backend primitive receives credit for pre-success identity binding.

Keep separate: authority epoch, target version, visible record and its effect
origin, applied-effect history, and successful receipts. A reset/revoke changes
authority and removes current visibility while preserving the bounded experiment's
historical outcome evidence. Exact receipt lifetime is identical across profiles;
only the explicit-GC case removes it. A physical deletion of all metadata is a
different, excluded failure. Revocation increments authority epoch and clears value/visibility/origin while
holding target version fixed. Participant and foreign data writes increment
target version; epoch rejection cannot therefore be credited to a changed version.

An exact retained receipt returns **historical acknowledgement** without a new
mutation; it does not claim the value is still visible or permission is current.
Return current visibility/epoch observations separately. A changed-body request
must be classified distinctly from a legitimate stale-version/epoch conflict.

## Four authored implementation profiles

These are explicit application contracts, not best-in-class vendor defaults or
a one-factor causal ablation. The same prepared request and expected predicates
are used; backend primitive boundaries and error behavior differ.

1. **Split**: effect and successful receipt use separate commits/commands. Guard
   the effect's version/epoch in its native mutation primitive; do not silently
   confound split receipt placement with an unguarded target write.
2. **Grouped**: a prepared new-write path attempts effect then receipt in one
   SQLite transaction or one multi-write Redis Lua invocation. The caller's entry
   receipt/type inspection is outside this group. There is no in-group storage
   type preflight. This deliberately tests grouping writes after prevalidation,
   not the strongest possible Redis idempotency script.
3. **Preflight-grouped**: inside the same transaction/script, validate storage
   types/schema and repeat the receipt/semantic predicates before the first write.
   Then attempt the grouped writes. This is a bundle of validation placement and
   grouping; do not attribute differences solely to the word atomic.
4. **Single-envelope**: validate the full logical envelope and replace the
   record/version/epoch/success receipts in one application key/row
   replacement (not one physical disk write). External witness capture is not another participant mutation.
   Server-side conditional execution still guards expected version and epoch.

A robust script that HGETs the same receipt hash before mutating naturally raises
an already-present WRONGTYPE before the effect. The after-effect WRONGTYPE case
therefore belongs to the declared grouped **new-write** path after an external
entry inspection, not an impossible external interleaving inside `EVAL`. The
fixture corrupts receipt storage after entry, before that primitive. Redis then
executes the successful effect command and reaches the actual invalid HSET.
SQLite reaches an actual failing receipt statement under explicit rollback.
The preflight arm detects current invalid storage before a write.

## Proposed finite history matrix

Thirteen histories x four profiles x two backends = 104 declared cells before
capability exclusions. Every excluded cell is retained with `applicable=false`
and a reason. With the exclusions below, 96 applicable cells are proposed.
No performance sampling or repeated-renaming inflation is used. Every request
uses a fresh OS process. The lost-reply and split cut use actual `os._exit(87)`
at declared semantic barriers; they are not network packet loss. A separate
post-campaign graceful Redis restart compares every completed key byte-for-byte,
then exports native AOF data. This control adds no case to the denominator.

1. Normal apply.
2. Real/injected error before the first effect (no state change expected).
3. Receipt storage error after entry inspection: Redis WRONGTYPE / SQLite failing
   receipt statement. N/A for both single-envelope cells, which have no separate
   receipt key/table. Other arms preserve observed failures rather than forcing
   rollback equivalence.
4. Exact retry after a fully committed operation and unavailable client reply.
5. Changed body under the prepared identifier after a successful receipt.
6. Stale target version after a foreign accepted mutation.
7. A newer accepted mutation between the original commit and its exact retry.
8. Revoke/delete after client entry validation, before backend submission.
   All arms recheck the mutation predicate in the primitive; this is a fencing
   control, not an impossible pause inside an atomic script/transaction.
9. Client termination after the effect commit but before a separate receipt
   commit. Applicable only to Split: the other six backend/profile cells are N/A.
   Do not split an atomic unit to manufacture this barrier.
10. Revoke/delete after finalization, followed by exact historical retry.
11. Explicit successful-receipt garbage collection, followed by exact retry.
12. Two fresh processes issuing the same prepared identifier/body.
13. Two fresh processes issuing distinct identifiers for the same expected version.

A separate post-validation **inside primitive** external-revoke pause is not
representable in EVAL or a held SQLite write transaction. It must not be relabeled
the external-entry control in history 8. If root needs this comparison, introduce
an explicitly weaker entry-only-fencing profile and a separate denominator.

## Independent oracle and evidence

Do not collapse the result into one success score. Check separately:

- literal chosen-body/target-version continuity;
- accepted effect count by operation identity (separate foreign writes/revokes);
- receipt/effect coupling and duplicate-free effects;
- historical acknowledgement, including after current authority is revoked;
- current visible value and current generation/authority;
- stale-epoch effects, even if filtered from current visibility;
- state left after backend command/script errors and client termination.

Read raw SQLite rows or Redis key/envelope snapshots plus native return statuses.
The checker implements a distinct transition model and compares every result,
not just aggregate counts. The two-process cases must fit a legal ordering of
the actual backend primitives, not observation-list order. Keep returned outcomes,
error types, backend script/source hashes and all N/A records. On an exception,
the response changed field is unknown (`null`); only the physical-state oracle
classifies committed effects. The Redis checker independently reduces the native
RESP append-only command stream from an empty base RDB and compares all final
keys; the SQLite checker opens every final database read-only. A successful
historical acknowledgement after revoke is not itself a violation.

Successful effect/receipt coupling under valid commands does not imply rollback
on every runtime error. Redis script isolation, SQLite explicit rollback, AOF
configuration and single-command replacement are different guarantees. No
mid-commit power-loss, remote cluster, performance, receipt-reclamation theorem,
whole-plan atomicity or new concurrency algorithm is claimed.

## Public primary sources consulted

- [Redis scripting](https://redis.io/docs/latest/develop/interact/programmability/eval-intro/):
  server-side scripts execute without command interleaving; script cache is not
  a durable database.
- [Redis transactions](https://redis.io/docs/latest/develop/using-commands/transactions/):
  runtime errors do not cause SQL-style rollback; WATCH conditions EXEC.
- [Redis Lua API](https://redis.io/docs/latest/develop/programmability/lua-api/):
  pass accessed keys explicitly and keep input/state in the Redis keyspace.
- [SQLite transactions](https://www.sqlite.org/lang_transaction.html): explicit
  transaction boundaries and rollback behavior.
- [Redis persistence](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/):
  AOF policy is separate from execution atomicity and does not prove host failure
  behavior in these tests.
- [Official Redis releases](https://github.com/redis/redis/releases) and
  [official image tags](https://hub.docker.com/_/redis/tags?name=7.2.): runtime pin.

Consulted 2026-10-29 study-local date. These are known provider semantics, not
claimed first discoveries. All company services/credentials/code remain excluded.
