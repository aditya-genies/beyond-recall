"""Freeze an evidence-based claim ledger for the new public-source extensions."""
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
MEM=HERE/'mem0_reference'


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path):return json.loads(Path(path).read_text())
def evidence(*paths):return [dict(path=p,sha256=digest(ROOT/p)) for p in paths]


retrieval=load(MEM/'retrieval_results/verification.json')
live=load(MEM/'live_verification.json')
controlled=load(MEM/'verification.json')
memtx=load(HERE/'memtx_reference/audit_summary.json')
reproduction=retrieval['computational_reproduction']
assert all(r['status']=='PASS' for r in [retrieval,live,controlled,memtx,reproduction])
assert retrieval['exact_target_present_count']==retrieval['native_search_calls']==1008
assert reproduction['identical_per_query_metric_cells']==1008
assert reproduction['retained_states_checked']==16
less=sum(r['cells_with_fewer_distinct_literals'] for r in retrieval['paired_literal_exposure'])
assert less==201
assert all(all(r[k] for k in ['baseline_point_blobs_preserved','literal_set_matches_baseline',
    'all_new_points_are_literal_baseline_copies','new_literal_vectors_match_baseline_tolerance_1e_6'])
    for r in retrieval['raw_state_comparisons'])

claims=[
 dict(id='C1_conditional_admission',status='Supported conditional counting argument and pinned-source counterexample',
  safe_wording='Exact-text duplicate suppression can inherit a bounded retrieval window when only retrieved records supply its existing-hash set.',
  exact_statement='Let N distinct already-stored fact hashes be eligible for redelivery, and let U be the distinct existing hashes presented to admission. Under the tested same-scope sequential ADD path, if every fact outside U is re-emitted once and no other filter rejects it, N-|U| repeated records survive. Since |U|<=k, this is at least max(0,N-k).',
  conditions=['Distinct exact-text hashes, fixed scope, already stored facts and sequential delivery',
    'Re-emission assumption must be explicit; arbitrary natural model outputs need not satisfy it',
    'The exact N-|U| statement is about the specified admission path, not all memory APIs'],
  false_or_overgeneralizing=['Mem0 necessarily inserts N-k duplicates on every retry.',
    'Every store larger than k must duplicate facts.', 'MD5 is globally broken.',
    'The elementary counting bound is a new recovery theorem.', 'The vendor promised request exactly-once semantics.'],
  evidence=evidence('extensions/replanning_contracts/mem0_reference/results/frozen_spec.json',
    'extensions/replanning_contracts/mem0_reference/verification.json',
    'extensions/replanning_contracts/literature/mem0_pinned_source_manifest.json')),
 dict(id='C2_controlled_source_sweep',status='Supported finite parameter sweep',
  safe_wording='A 96-cell controlled-extraction sweep through the pinned Mem0 OSS path separates exact fact content from physical multiplicity, with hash and real BGE embedding factors and two authored interventions.',
  conditions=['96 parameterized executions, not 96 independent model trials',
    'Widened candidate and exact-admission arms are authored sequential controls',
    'The fact-set check is exact literal equality in authored fixtures'],
  false_or_overgeneralizing=['Controls are production-ready concurrent deduplication fixes.',
    'Passing fact-set checks proves semantic memory correctness.', 'The sweep estimates production incidence.'],
  evidence=evidence('extensions/replanning_contracts/mem0_reference/results/summary.json',
    'extensions/replanning_contracts/mem0_reference/verification.json')),
 dict(id='C3_fresh_model_witness',status='Supported bounded integration witness; source review relies on the separate live checker',
  safe_wording='The live adapter records 28 successful Codex CLI requests configured as gpt-6.1-sol, comprising four baseline requests and 24 fresh-model retry requests; another 24 retries reuse recorded results without a new request.',
  conditions=['Native Mem0 prompt content is delivered through the documented Codex CLI adapter, not a stock hosted Mem0 LLM provider',
    'Requested model configuration is recorded; no independent attestation of a hidden backend weight revision',
    'Four workers exit after the add API has committed; this models lost acknowledgement, not a crash inside arbitrary database commit steps',
    'One requested model/harness and finite authored source batches; no population model-error rate',
    'The aged-context fresh native arm has one nonidentical literal among its additions; semantic equivalence is not graded'],
  false_or_overgeneralizing=['Twenty-eight independent production incidents.',
    'All 48 retries are fresh model calls.', 'The model weights were independently verified.',
    'The experiment validates arbitrary crash consistency inside Mem0.'],
  evidence=evidence('extensions/replanning_contracts/mem0_reference/live_verification.json',
    'extensions/replanning_contracts/mem0_reference/live_results/summary.json')),
 dict(id='C4_posthoc_retrieval_exposure',status='Independently recomputed; complete finite coverage',
  safe_wording='The post hoc retrieval probe queries all 84 baseline literal facts in four frozen states at budgets 5, 10 and 20, producing 1008 registered search cells. All exact queried strings remain present. Native retry stores can return fewer distinct literal strings despite this preserved target presence.',
  observed=dict(registered_cells=1008,unique_baseline_literal_queries=84,exact_target_present_cells=1008,
    cells_with_duplicate_slots=213,cells_with_fewer_distinct_literals_than_baseline=201),
  conditions=['Protocol frozen before searches, but designed after duplicate writes were observed',
    'Only selected fresh-context stores, all baseline facts, identical native BGE+BM25 reader, threshold zero and native optional-spaCy fallback',
    'Exact stored text is the query: this is a literal exposure probe, not a semantic QA benchmark',
    'Additional record identities/timestamps are part of the observed duplicate-bearing state; multiplicity alone is not separately manipulated while all metadata is held fixed',
    'Queries and budgets are dependent; no confidence interval or natural-workload rate follows'],
  false_or_overgeneralizing=['Recall or answer quality fell in 213 queries.',
    'Duplicate slots always displace distinct context.', 'All 213 duplicate-bearing cells have lower literal diversity.',
    'The probe demonstrates agent harm, semantic diversity loss or measured token waste.'],
  evidence=evidence('extensions/replanning_contracts/mem0_reference/retrieval_results/protocol.json',
    'extensions/replanning_contracts/mem0_reference/retrieval_results/verification.json')),
 dict(id='C5_specific_budget_result',status='Supported exact arithmetic',
  safe_wording='For the 40-fact state at budget 10, the native retry store returns 400 slots across 40 queries but only 247 summed per-query distinct literal strings, versus 400 in baseline and both controls. Mean per-query distinct strings are 6.175 versus 10; all 40 targets remain present.',
  conditions=['The sum is over per-query distinct counts, not 247 globally different facts',
    'At 12 facts/budget 20, duplicates fill spare slots without reducing the 12 distinct literals; this negative boundary should be reported'],
  false_or_overgeneralizing=['38.25 percent QA harm or target-recall loss.',
    '153 globally unique facts were lost.', 'All budgets show diversity deterioration.'],
  evidence=evidence('extensions/replanning_contracts/mem0_reference/retrieval_results/verification.json')),
 dict(id='C6_computational_reproduction',status='Supported retained raw-after evidence',
  safe_wording='A frozen retention wrapper reproduces the same 1008-cell computation, retaining all 16 copies after clients close. All per-query metrics and ordered IDs match, and persisted point blobs/history remain unchanged.',
  conditions=['2016 native search invocations across original and reproduction, but only 1008 unique registered cells',
    'Computational reproduction of the same data/code, not independent experimental samples',
    'Original temporary after-stores were deleted; only the reproduction has retained raw after-stores',
    'Checker verifies raw membership, literal metrics, coverage and integrity; it does not independently recompute native rankings, BGE inference or BM25 scores'],
  false_or_overgeneralizing=['2016 independent observations.',
    'The original deleted copies are now directly audited.', 'The checker proves the semantic correctness of native search.'],
  evidence=evidence('extensions/replanning_contracts/mem0_reference/retrieval_reproduction/retention_protocol.json',
    'extensions/replanning_contracts/mem0_reference/retrieval_reproduction/retained_manifest.json',
    'extensions/replanning_contracts/mem0_reference/retrieval_results/verification.json')),
 dict(id='C7_memtx_boundaries',status='Supported bounded primary-description/code discrepancy',
  safe_wording='At the pinned MemTX commit, the tested old transactions retrieve a post-begin record absent from their captured snapshots; two empty-snapshot authority variants supersede a post-begin rival where nonempty-snapshot controls reject it temporally. These disagree with the paper snapshot-read and pre-authority rejection descriptions in the tested boundaries.',
  conditions=['Eight read cases, eight old-writer cases and eight fresh-writer controls; no arbitrary state-space theorem',
    'Fresh-transaction correction is intended and the paper itself discusses retry escaping transaction-local temporal protection',
    'The paper explicitly permits partial commit; arbitrary multi-record predicate serializability is not the tested contract',
    '94 original core unit tests pass; optional full-suite tau2 collection failure remains disclosed'],
  false_or_overgeneralizing=['All snapshot isolation or all MemTX lifecycle invariants fail.',
    'Passing the source tests establishes complete conformance.', 'Classical write skew is a new MemTX defect.',
    'The probes refute every formal or bounded invariant claimed in the paper.'],
  evidence=evidence('extensions/replanning_contracts/memtx_reference/audit_summary.json',
    'extensions/replanning_contracts/memtx_reference/results/provenance.json',
    'extensions/replanning_contracts/literature/memtx_contract_audit.json')),
 dict(id='C8_prior_art_and_remaining_novelty',status='Broad principles established; narrow implementation evidence remains',
  safe_wording='The contribution is a conditional exact-hash admission counterexample, independent raw-evidence checks and a bounded public implementation conformance study. Stable receipts, retained decisions, fencing, memory lifecycles and classical isolation principles are prior art.',
  closest_sources=['Mem0 discussion 6726 and MiniMem public code-reading note: bounded semantic candidate visibility, while assuming literal MD5 suppression',
    'Mem0 issues 6515 and 7612: concurrent hash TOCTOU and expiry/reinsertion are separate reported mechanisms',
    'TOKI: memory operator histories, isolation preconditions and retained judge decisions',
    'MemTX: memory lifecycle, validation/action gating and explicit snapshot/temporal descriptions',
    'Cordon and verified concurrency work: composed tool effects and read-generate-write isolation',
    'GEM/MemState, revoked-memory evaluation and execution-state unlearning: history, derived state and forgetting',
    'RIFL, Beldi, quiescence/receipt-enforcement work and official durable-execution contracts: identity, decision logging, safe reclamation and protected-effect admission'],
  false_or_overgeneralizing=['First benchmark beyond memory recall.', 'New epoch-plus-receipt recovery protocol.',
    'Exhaustive academic coverage.', 'Leading-journal readiness follows from the number of tests, model calls or citations.'],
  evidence=evidence('extensions/replanning_contracts/literature/overlap_matrix.json',
    'extensions/replanning_contracts/literature/primary_source_index.json',
    'extensions/replanning_contracts/literature/new_claim_map.json')),
]

review=dict(prepared_at_utc=datetime.now(timezone.utc).isoformat(),
    scope='Independent evidence review of new public-source extensions, not a manuscript review or venue acceptance score.',
    main_manuscript_edited=False,additional_model_requests_by_reviewer=0,
    current_status='PASS within declared implementation and literal-exposure scope; no numerical correction currently required.',
    material_corrections_required=[],
    critical_interpretation_corrections=['Distinguish 213 duplicate-bearing cells from 201 cells with lower literal diversity.',
      'State N-|U| and conditional lower bound N-k, not unconditional equality on every replay.',
      'Retained after-state proof is from computational reproduction; preserve the original deletion limitation.',
      'State requested Codex model configuration, single harness and lost-ack cut after API completion.'],
    remaining_research_gap='A leading-journal contribution remains unestablished. The counting argument is elementary and the snapshot boundaries are implementation discrepancies. A stronger generalizable result needs cross-implementation evidence or a deeper characterization with meaningful end-task consequences and repair tradeoffs. No further experiment is required to validate the present narrow claims.',
    claim_ledger=claims)
(HERE/'new_study_claim_ledger.json').write_text(json.dumps(review,indent=2,ensure_ascii=False)+'\n')

notes='''Independent scientific review of the new study

The evidence supports a narrower public-implementation conformance paper. No numerical correction is presently required within the declared scope. This review does not establish leading-journal readiness or supply an acceptance score.

The strongest write-admission insight is conditional: when only a k-record retrieval cohort supplies the exact-text hash set, at most k distinct stored hashes are recognized there. If N distinct stored hashes are re-emitted without another suppressing filter, N-|U| copies survive, at least max(0,N-k). This is elementary counting. A model can emit fewer or no facts, so an unconditional “N-k duplicates on every retry” claim is false. The controlled sweep, real-embedding factor, raw Qdrant/history reconciliation and authored intervention arms make the implementation consequence concrete; they do not create a new recovery algorithm or establish a vendor exactly-once promise.

The live adapter provides a bounded integration witness: 28 successful Codex CLI requests configured as gpt-6.1-sol, four baselines plus 24 fresh retries, and 24 further recorded-result controls without new requests. Configuration is recorded, not independently attested backend weights. The worker cut occurs after the add API commits. It tests lost acknowledgement, not arbitrary crashes inside Mem0 commit. The aged-context arm includes one nonidentical literal; meaning is not graded.

The post hoc search probe covers all 84 baseline literals, four frozen fresh-context states and budgets 5/10/20: 1008 registered cells. All 1008 exact targets remain present. There are 213 duplicate-bearing cells but only 201 with fewer distinct literals than baseline. At N12/budget20, duplicates use spare slots while the same 12 literals remain present. At N40/budget10, native retry returns 400 slots with 247 summed per-query distinct strings (mean 6.175), versus 400 and mean 10 in baseline and both controls; all 40 targets remain present. Calling this target-recall loss, QA harm, semantic diversity loss or measured token waste would be false or untested.

All selected state comparisons preserve baseline point blobs and literal sets; new records are exact baseline-literal copies with matching dense vectors within 1e-6. Controls equal baseline. This removes a differing-content confound for the chosen fresh-context comparison. Added identities and timestamps remain part of the real duplicate-bearing state. The probe was designed after duplicate writes were observed, and literal self-queries are not natural-language workload generalization.

A source-frozen retention wrapper repeated the same computation and retained all 16 copies after native clients closed. Every per-query metric and ordered returned ID matches. Raw point blobs and histories remain unchanged. This is 2016 search invocations across two computations of the same 1008 registered cells, not 2016 independent samples. Original temporary after-stores were deleted; the stronger direct after-state audit applies to the reproduction. The independent checker imports no experiment metrics and recomputes coverage, returned membership/literals, all metrics and summaries. It does not recompute rankings, BGE inference or BM25 scores. Three authored negative-fixture test methods reject false literal/metric evidence, favorable query omission and frozen-database mutation.

The MemTX probes support bounded discrepancies with its explicit snapshot-read and pre-authority stale-rival descriptions. They do not refute all lifecycle invariants or establish a new isolation principle. Empty-snapshot versus anchored controls and fresh-writer controls are important. Fresh-transaction correction is intended and discussed by the authors. Partial commit is permitted. The 94 passing core unit tests coexist with the new boundary witnesses; the optional tau2 collection error remains disclosed.

Closest antecedents must remain prominent: Mem0 discussion 6726 and the MiniMem note already describe bounded semantic candidate visibility; issues 6515/7612 report separate concurrency/expiry hash problems. TOKI covers memory history contracts and retained judge decisions; MemTX covers lifecycle validation; Cordon and verified concurrency work address composed effects and long read-generate-write histories. GEM/MemState, revoked-memory evaluation and execution-state unlearning already extend evaluation beyond recall. RIFL, Beldi and authority/quiescence work establish stable identity, retained decisions, reclamation and fences. The narrower literal-hash consequence and actual source boundaries can be valuable empirical evidence, with no supported first-discovery claim.

The remaining journal-level research gap is generalizability and scientific depth, not additional counts alone. A shared cross-system failure characterization, independent replication, meaningful task consequences or principled repair tradeoffs would strengthen the work. The present evidence should be published and discussed at its actual bounded scope.
'''
(HERE/'new_study_scientific_review.txt').write_text(notes)

retrieval_notes=dict(status='PASS',checker='check_retrieval.py',
    checker_sha256=digest(MEM/'check_retrieval.py'),wrapper_sha256=digest(MEM/'retain_retrieval.py'),
    tests_sha256=digest(MEM/'test_check_retrieval.py'),test_log_sha256=digest(MEM/'retrieval_check_tests.txt'),
    verification_sha256=digest(MEM/'retrieval_results/verification.json'),
    negative_fixture_test_methods=3,negative_fixture_methods_passed=3,
    original_registered_cells=1008,computational_reproduction_cells=1008,independent_sample_count_claim=None,
    exact_target_presence=1008,duplicate_bearing_cells=213,lower_literal_diversity_cells=201,
    raw_after_stores_retained=16,ordered_id_cells_matching=1008,
    protected_original_inputs_unchanged=True,
    design_review=['Post hoc causal exposure probe of complete authored literal query set, not independent workload generalization.',
      'Same selected-state literal content, preserved baseline point blobs and matching new-copy vectors remove differing-content confounding.',
      'All 84 baseline literals used; no favorable query selection within the frozen selected states.',
      'Exact self-query target presence and literal diversity are separate outcomes.',
      'Duplicate slots need not displace unique literals when the budget has spare capacity.',
      'Current native/helper/runtime hashes match earlier frozen evidence; the retrieval protocol did not independently pin loaded model-file digests.',
      'Original deleted temporary after-state is not recovered; reproduction after-state is directly checked.'],
    source_checks=retrieval['runtime_integrity'])
(MEM/'retrieval_checker_review.json').write_text(json.dumps(retrieval_notes,indent=2)+'\n')
print(json.dumps(dict(status='PASS',claims=len(claims),original_search_cells=1008,
    all_exact_targets_present=True,duplicate_bearing_cells=213,lower_literal_diversity_cells=201,
    retained_reproduction_stores=16,negative_fixture_test_methods=3),indent=2))
