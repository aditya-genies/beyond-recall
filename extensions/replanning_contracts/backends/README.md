# Public SQLite/Redis contract witnesses

This standalone extension executes the approved finite protocol in `DESIGN.md`.
It uses no company code, credentials, services or data. Its results are separate
from every earlier experiment; the denominators must not be pooled.

The frozen campaign contains **104 declared cells: 96 executed and 8 explicitly
not applicable**, with 154 fresh request processes and 10 actual `os._exit(87)`
terminations at declared client barriers. These are finite synthetic contract
witnesses, not a memory-quality benchmark, formal proof or vendor ranking.
The verifier's pass means every recorded outcome agrees with the independent
protocol oracle. Expected errors and incomplete effect/receipt pairs remain in
the raw data; it does not mean that all profiles satisfy every desired property.

## Main observations

- After caller entry inspection, the receipt-storage fault leaves one effect and
  no usable receipt for both split implementations. The grouped Redis Lua path
  also leaves that effect after a real WRONGTYPE; the grouped SQLite path executes
  an explicit rollback after a real failing receipt statement and leaves no
  effect. Both preflight paths prevent the effect for this specific fault.
- Grouped is an authored prepared-new-write baseline: its entry receipt/type
  check is outside the primitive. It is not the strongest Redis script, a vendor
  default, or a one-factor causal ablation. A script that reads the same receipt
  hash inside EVAL would observe this existing WRONGTYPE before its effect.
- All four profiles check version and authority epoch at the effect itself.
  Every entry→submission revoke control rejects the old epoch while version
  remains unchanged. No duplicate or stale-epoch effect occurs in these 96 cells.
- Exact retry after a committed operation and client death returns historical
  acknowledgement in all eight backend/profile cells. Retained receipts also
  acknowledge historical success after revocation while visibility remains false;
  they do not restore current permission or the visible value.
- A split-only committed effect/pre-receipt client death leaves one effect and no
  receipt. The exact retry is rejected by the unchanged request's stale expected
  version, rather than silently rebasing it or producing a duplicate effect.
- In same-ID two-process cases, the preflight/envelope primitive rereads the
  receipt and returns one apply plus one historical acknowledgement. The weaker
  grouped/split prepared paths can return one apply plus one version conflict.
  Both outcomes preserve one effect; no atomicity defect is inferred from the
  weaker path's different conflict response.
- Explicit receipt GC leaves one historical effect without its receipt in every
  profile. The aggregate missing-receipt count therefore includes intentional
  retention removal; it is not an overall defect rate.

The single-envelope arm has no separate receipt-storage target and no committed
internal effect-before-receipt boundary. These unavailable faults are N/A,
not successful experiments. The envelope is one **application key/row replacement**,
not one disk write. Caller identity binding is the same separately durable
prepared-body journal for every profile; it is not credited to the backend.

## Reproduce and verify

Run from the repository root with Docker available through a local Unix socket.
Install `requirements.txt` in a fresh virtual environment from public PyPI. The
published run used Python 3.14.3, SQLite 3.51.2, redis-py 8.1.0 and Redis 7.2.17
from the pinned official image digest in `frozen_spec.json`/`services.py`.
The checker needs only the standard library; execution needs the pinned client.

```bash
python -m unittest extensions.replanning_contracts.backends.test_backends -v
python -m extensions.replanning_contracts.backends.check \
  extensions/replanning_contracts/backends/results \
  --report /tmp/backends-verification.json
python -m extensions.replanning_contracts.backends.campaign run \
  extensions/replanning_contracts/backends/reproduced-results \
  --spec extensions/replanning_contracts/backends/frozen_spec.json
```

The runner refuses to overwrite an output directory and verifies the frozen
engine/protocol hashes before execution. It creates its own fresh authenticated
Redis container, dedicated network, loopback ephemeral port and AOF volume. It
uses an empty temporary Docker client-auth config and an explicit local socket;
no existing database or remote Docker context is used. Passwords/connection
configs are temporary and excluded from results. Cleanup records all three owned
resources removed. A separate graceful server restart compares all 72 completed
Redis keys exactly, adding no case to the denominator.

The independent checker imports no worker/adapter transition code. It checks the
literal finite histories, statuses, requests, durable caller journal, stdout and
actual child barrier sequences. It opens all 48 final SQLite databases read-only
and independently reduces the native Redis RESP AOF effects from an empty base
RDB to all 72 final keys, including every key mutation sequence and the native multi-write group boundaries. `final_verification.json` and `cell_metrics.csv` contain
separate dimensions, not an opaque success score. Twenty-one focused tests include
twelve negative evidence mutations, real backend errors, actual child restart and
two-process execution. The valid-schema SQLite trigger test specifically confirms
that preflight cannot anticipate arbitrary later runtime errors.

## Scope and retained development records

The phrase “validate the full logical envelope” in the frozen protocol is limited
to the declared valid record schema and implemented receipt/predicate checks.
This is not arbitrary corrupt-state/schema validation; see `scope_audit.json`.
Redis script atomic execution prevents interleaving and does not promise rollback
of writes preceding a runtime error. SQLite rollback here is explicit application
exception handling. These are known provider semantics, documented by
[Redis scripting](https://redis.io/docs/latest/develop/interact/programmability/eval-intro/),
[Redis transactions](https://redis.io/docs/latest/develop/using-commands/transactions/),
and [SQLite transactions](https://www.sqlite.org/lang_transaction.html).
AOF policy and the graceful restart do not establish power-loss or arbitrary
mid-commit durability; see [Redis persistence](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/).

`development_feasibility*.json` are explicitly development capability probes;
the initial port-publication attempt failed and is retained. Development dry-run
directories remain locally available and are ignored by default in releases.
They are not additional experimental samples. No throughput, latency, arbitrary
failure, remote cluster, erasure/unlearning or new distributed algorithm claim
is supported by this extension.
