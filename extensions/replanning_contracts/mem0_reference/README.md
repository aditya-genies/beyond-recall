# Native Mem0 admission and retrieval evidence

The tested public source is Mem0 commit
`26cdefb46600c0fa5953c4b5ee5003c125539fc4` (package version 2.2.1).
Only the synchronous inferred-ingestion path is executed. Native admission code
is unchanged. Study callback/provider injection and two explicitly authored
interventions are visible in `experiment.py` and `live.py`.

## Archive verification without model access

Use a fresh environment with the actual measured versions in
`requirements-runtime.lock.txt`. The earlier `requirements.lock.txt` is the
initial bootstrap installation record and does not describe the final runtime;
it is preserved for chronology. Public Git source replaces its local install
path in the final lock. No company keys or API-key fallback are required.

From the repository root:

```sh
python extensions/replanning_contracts/mem0_reference/check.py \
  --report /tmp/mem0-controlled-verification.json
python extensions/replanning_contracts/mem0_reference/check_live.py \
  --report /tmp/mem0-live-verification.json
python extensions/replanning_contracts/mem0_reference/check_retrieval.py \
  --reproduction extensions/replanning_contracts/mem0_reference/retrieval_reproduction \
  --report /tmp/mem0-retrieval-verification.json
python -m unittest discover -v \
  -s extensions/replanning_contracts/mem0_reference -p 'test_*.py'
```

The controlled/live checkers verify pinned installed implementation/runtime
packages as well as raw read-only stores and recorded responses. The retrieval
CLI additionally checks exact original Python/SQLite runtime identity, including
platform-specific Python text. On another platform this check must report the
mismatch; do not silently relabel archive audit as native-runtime reproduction.
`ci/README.md` in the parent directory describes the hosted raw-evidence check and its
explicitly unrun original-runtime comparison. Three separate checker modules
each include three meaningful forged-evidence/negative-fixture tests.

## Controlled reproduction

The frozen design is `results/frozen_spec.json`; raw data are `results/cases.json`
and the 96 native state/history folders. Each cell uses one initial call and two
exact-source redeliveries. The two extraction callbacks are deliberately
controlled, not synthetic data presented as LLM outputs. BGE is real local ONNX
inference, while the separate hash embedding factor is nonsemantic.

Prewarm public FastEmbed BGE and BM25 assets before execution. Measured controlled
execution sets offline mode and blocks external network connections. Set
`FASTEMBED_CACHE_PATH` to the prepared cache, then use fresh outputs:

```sh
python extensions/replanning_contracts/mem0_reference/experiment.py prepare \
  --out extensions/replanning_contracts/mem0_reference/my-results
python extensions/replanning_contracts/mem0_reference/experiment.py run \
  --out extensions/replanning_contracts/mem0_reference/my-results
python extensions/replanning_contracts/mem0_reference/check.py \
  --out extensions/replanning_contracts/mem0_reference/my-results \
  --report /tmp/mem0-reproduction-verification.json
```

Each fresh preparation freezes its current environment/source; compare scalar
outcomes and source identity rather than random UUIDs, wall-clock times or DB
bytes. `embedding_files.json` records downloaded asset hashes after preparation;
the retrieval protocol did not separately freeze all transitive dependencies or
attest loaded model-file bytes. Do not turn that manifest into a stronger claim.
Optional spaCy was absent and native fallback remained active.

## Live recovery and retrieval exposure

`live_results/protocol.json` freezes four baseline batches and 48 retries. The
baseline worker calls actual native ingestion and exits with code 87 after the
API returns committed effects, before logical acknowledgement. Retried stores
are copies preserving the original identities. Twenty-eight actual personal
Codex requests use the requested `gpt-6.1-sol` alias with native role-designated
prompts and strict output schema. Exact backend snapshot, hidden harness prompt,
temperature and seed are unknown. Twenty-four recorded-result retries reuse the
baseline model response; these are explicit recovery controls, not new calls.

Fresh model repetitions may differ. All prompts, raw/used final responses,
request statuses and native stores are preserved, with no hidden reasoning,
personal CLI diagnostics, session identifiers or credentials. The aged N40
native fresh response adds one new literal formulation; it remains ungraded,
not hidden or called an error. The fresh-history/native state has only exact
copies and is deliberately selected for the later mechanism probe.

Fresh live execution is optional, needs the personal Codex CLI and may consume
the user's subscription. `live.py --help` describes its explicit prepare/run
actions; use a new output directory and the installed CLI path. No live requests
are made by archive verification or hosted CI.

`retrieval_results/protocol.json` is post hoc to live writes and frozen before
the 1,008 searches: all 84 baseline literal queries × four states × budgets
5/10/20. There is no query subsampling, answer-generation task or semantic
adjudication. Every exact target is present. Duplicate slots and paired loss of
distinct strings are separate metrics; spare capacity is not displaced evidence.

`retain_retrieval.py` froze a wrapper before repeating the same computation into
`retrieval_reproduction/`. It changes only deletion/retention of the sixteen
temporary after-close reader copies. Ordered result IDs and all metrics match;
the retained raw stores are unchanged. This is computational reproduction by
the same study, not additional independent experimental samples. It makes no
additional model requests. Source hashes and the wrapper protocol expose what
was and was not changed.

Literal uniqueness is not semantic uniqueness; target presence is not QA
accuracy. The complete-store filter is sequential and not a concurrency fix.
Widening candidates to 10,000 is an authored search wrapper, not a stock Mem0
setting. No vendor exactly-once promise, default-hosted behavior, production
incident rate or model superiority is asserted.
