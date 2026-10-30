# Separate Mem0 evidence check

The checker reproduces all 96 parameter executions and 288 native add-call observations from the archived Qdrant SQLite points, append-only history, recorded candidates, extraction responses and returned ADDs. All final exact fact sets match; 20 of the 32 native-k10 parameter cells contain extra physical copies. All three forgery tests pass by rejecting their deliberately falsified evidence. They construct their own toy databases and never copy or mutate campaign data.

The native `get_all` call uses the supported filters/top_k/show_expired API. It is a list/scroll operation, so the snapshot and sequential exact-admission control do not accidentally reuse the ten-record write search. The 10,000-row bound exceeds every store in this finite campaign. The installed native main file matches the pinned public source. The critical prompt, native history, vector adapter and factory files were also compared directly with the external pinned source; those hashes are in `checker_provenance.json`.

For the conditional counting observation, let F contain N already-stored exact strings with distinct hashes and let U be the distinct hashes from F represented in the k-row write-time candidate window. Then |U| <= k. If extraction emits every fact outside U, embeddings succeed, candidate-window and within-batch hashes are the only rejection rules, and all admitted writes persist, the replay adds N-|U| duplicate physical facts, at least max(0,N-k). The checker verifies the exact N-|U| equality on applicable recorded replay attempts. Ranking cannot place more than k distinct facts into k rows. This is an elementary conditional set-counting observation, not a new theorem, estimate of natural model behavior or unconditional vendor guarantee.

The two controls change different stages. Widening candidates is an authored wrapper intervention; it is not presented as a stock configuration flag. The global exact-admission control filters the controlled response inside the study callback using a complete sequential read; it is not an atomic native admission API or a multi-writer deduplication protocol. Both controlled extractors deliberately ignore last-message context for duplicate suppression, even though the native prompt includes that context. A live-model follow-up is therefore separate evidence. Matching outcomes under hash-control and BGE embeddings do not establish equal retrieval quality or additional independent failure types.

The checker verifies candidate membership/hashes against the prior physical snapshot and validates the exact source-query hash, but does not independently recompute ranking. It decodes actual persisted dense vectors, checks dimensions/finiteness, and recomputes hash-control vectors. It does not rerun BGE ONNX inference. Earlier per-attempt states are reconstructed from final physical records, add-only history and returned identities; the experiment did not retain separate database files at each attempt boundary. These boundaries are stated in `verification.json`.

The checker imports no experiment functions or Mem0 metric functions. Its Qdrant dependency is restricted decoding of the public PointStruct and SparseVector serialization. It is a separately authored checker within the same study, not independent external replication. The checker was authored after the campaign and after its aggregate outcomes were shared; the original experiment freeze remains unchanged.

Run from the artifact root using the memory environment:

```sh
python extensions/replanning_contracts/mem0_reference/check.py
python -W error::ResourceWarning -m unittest discover \
  -s extensions/replanning_contracts/mem0_reference -p test_check.py -v
```

The default check writes a new metadata report at `mem0_reference/verification.json`, outside the raw results directory. All 96 per-case JSON files, Qdrant and history databases, aggregate cases, summary and freeze files are read only and hash-guarded against changes during checking.
