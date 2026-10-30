# Suggested bounded manuscript material

A cross-backend extension instantiated four application contracts on actual
SQLite and Redis: separate effect/receipt commits, a grouped prepared-new-write
path, in-primitive receipt/type preflight plus grouped writes, and a single-record
envelope. All arms used the same durable caller binding of operation identity to
literal body, expected target version, and authority epoch; all guarded version
and epoch at the actual effect. The envelope performed one application key/row
replacement, without a physical-write-count claim. The finite matrix declared
104 cells (13 histories × 4 profiles × 2 backends); 96 were executable and eight
were retained as N/A where the arm lacked the fault boundary. The run used 154
fresh request processes and ten actual client exits at declared semantic barriers.
These counts are separate from the paper's earlier experiments.

The informative provider witness is not a new Redis discovery. After caller
entry validation, a real receipt-storage error left a committed effect without a
usable receipt in the grouped Redis Lua application path, whereas explicit SQLite
rollback removed the preceding effect in its grouped transaction. In-primitive
receipt/type checks prevented this particular fault in both backends. The weaker
grouped path deliberately lacks that reread; it is not the strongest vendor
implementation and the contrast is not a one-factor causal ablation. Scripts
that inspect the same receipt hash inside the atomic primitive would detect an
already invalid hash before their write. A separate valid-schema SQLite trigger
check shows that type/schema preflight does not predict all later runtime errors.

The extension also separates effect safety from response semantics. All 96
executed cells had no duplicate or stale-epoch effects. In all eight revoke-before-
retry cells, the retained receipt returned historical acknowledgement while the
current value remained invisible at the new authority epoch. In split-only client
exits after effect commit but before receipt commit, literal retry encountered a
stale expected version instead of silently rebasing or duplicating the write.
Explicit receipt GC likewise removed historical acknowledgement evidence in all
arms; these intentional removals must not be counted as incidental defect rates.
In native two-process same-ID cases, preflight/envelope receipt rereads yielded
one apply and one historical acknowledgement; weaker prepared paths could yield
one apply and one version conflict without a duplicate effect.

An independent checker reconstructed finite expected histories and statuses,
checked prepared journals and process stdout/barriers, opened all 48 SQLite
files read-only, and independently replayed the native Redis append-only effects
from an empty base RDB to all 72 final keys, including every key mutation sequence and the native multi-write group boundaries. A separate graceful Redis restart
preserved those keys exactly; it is not a power-loss test. Twenty-one focused tests,
including twelve forged-evidence rejection checks, passed. Neither these witnesses
nor the model agreement constitute formal proof, live-agent memory-quality
measurement, a production performance comparison, or a novel concurrency algorithm.
