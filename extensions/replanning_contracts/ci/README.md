# Replanning-contract CI scope

`.github/workflows/replanning-contracts.yml` is a separate workflow; the existing
`reproduce.yml` remains unchanged. It runs on relevant pushes, pull requests and
manual dispatch, with read-only repository permission, pinned checkout/setup/
artifact actions, Python 3.14.3, step/job timeouts and no model credentials.
Successful local command validation does **not** mean hosted GitHub Actions passed.

## Archived evidence job

The job installs `mem0_reference/requirements-runtime.lock.txt` from public PyPI
and the exact public Mem0 Git commit, then runs `pip check`. It executes the nine
existing controlled/live/retrieval negative-fixture tests and the unchanged
controlled and live archive-checker CLIs. These inspect SQLite/Qdrant point data,
source hashes, returned identities, recorded prompts/responses, process witnesses
and derived counts. They make no fresh model or embedding calls. Previously
recorded model calls are evidence being inspected, not calls made by CI.

Retrieval's full CLI calls `verify_runtime()`, which requires the original macOS
Python build string and SQLite 3.51.2. Ubuntu cannot honestly satisfy that check.
The workflow therefore calls the unchanged `audit()` and
`verify_reproduction()` functions directly, recording `runtime_integrity.status`
as **NOT_RUN**, the actual/frozen runtimes and the reason. It does not monkeypatch
or weaken the checker. The controlled checker independently checks the installed
native Mem0 and Qdrant decoder source hashes; the retrieval step checks all six
frozen package versions. Raw-store/query reconciliation covers the 1,008 archived
searches and the retained 16-store computational reproduction. CI does not rerun
BGE inference, retrieval ranking, native searches or any live-model experiment.

The unchanged MemTX trace checker has no output option and writes beside its
inputs. CI copies its directory to runner-temporary storage before executing it,
so archived evidence is preserved. This checks the 24 existing traces; it does
not download/execute MemTX, rerun its upstream tests or reinterpret the recorded
optional-dependency/test failures as passes.

## Native backend job

A separate environment installs the exact `redis==8.1.0` pin. It runs the existing
21 backend/negative-checker tests, checks archived physical SQLite databases and
native Redis AOF, then reproduces the frozen matrix in a new ignored output
folder. The frozen runner owns a fresh Redis container, network, authenticated
loopback port and AOF volume, and fresh SQLite files. Its official Redis 7.2.17
image is pinned by an OCI index digest that advertises both Linux amd64 and arm64.
No existing database or remote Docker context is used. Docker must be available
through a local Unix socket; a missing runtime is a job failure, not a silent skip.

The independent verifier checks every reproduced raw state, child outcome and
native AOF mutation/group. A comparison step requires the same declared/executed/
N/A counts, attempt/exit counts and per-backend/profile aggregate outcomes as the
archive. Race winner identities and raw file bytes need not match. The expected
matrix remains 104 declared cells, 96 executed and eight N/A; 154 request processes
and ten abrupt client exits. Reproduction is a separate computational check,
not 96 additional statistical samples. This remains a finite local contract
study, without power-loss, cluster, throughput or vendor-ranking claims.

Both jobs check that tracked frozen inputs were not rewritten and retain reports
on failure. The backend job additionally uploads the complete new raw campaign
so native database/AOF verification can be repeated. No source driver, protocol,
archived data or original result denominator is modified by this workflow.

## Dependency-file chronology

`mem0_reference/requirements.lock.txt` is preserved as historical initial/bootstrap
evidence. It does not describe the completed execution environment: it omits the
six frozen packages and contains an earlier Pydantic pin. On the author's explicit
instruction, the new `requirements-runtime.lock.txt` was derived **after the
campaign** from the actual current public research environment's `pip freeze`.
Only Mem0's local archive URL was replaced with its verified public Git commit
`26cdefb46600c0fa5953c4b5ee5003c125539fc4`. This new lock is a version/source-pin
reconstruction, not a retroactive prospective environment freeze or a wheel-hash
lock. A fresh local install of that file and `pip check` succeeded. The six
versions match the already frozen controlled-study metadata, and the archive
checker confirms the installed native source hashes.

`local_validation.json` records the commands actually exercised locally, their
results, and platform limits. GitHub runner provisioning, action execution,
Ubuntu dependency installation and artifact upload require a hosted run and
remain unclaimed until that run completes. Workflow settings follow the
[official GitHub workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax).
