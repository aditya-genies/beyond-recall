"""Build bounded, public-source research notes; do not redistribute source text."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
CACHE = Path('/tmp/beyond-recall-public-literature-20261029')
NOW = datetime.now(timezone.utc).isoformat()


def save(name, data):
    (HERE / name).write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')


def evidence(key):
    for name in ('new_scholarly_fetch_manifest.json', 'expanded_primary_fetch_manifest.json',
                 'focused_issue_fetch_manifest.json', 'mem0_additional_antecedent_manifest.json',
                 'mem0_pinned_source_manifest.json'):
        for record in json.loads((HERE / name).read_text())['records']:
            if record['key'] == key:
                return {k: record[k] for k in ('key', 'url', 'retrieved_utc', 'http_status',
                        'status', 'sha256', 'bytes') if k in record}
    raise KeyError(key)


PAPERS = {
 '2607.23929': {
  'locations': ['§§3.1–3.6', '§§4–6', 'Appendices C, G, H'],
  'scope': 'Belief lifecycle, risk-tiered visibility, per-record validate-and-commit, action gating and typed cascade repair. Its public manager is a useful CPU baseline. The paper permits partial commit and identifies fresh-transaction retry and undeclared provenance as protection boundaries.',
  'overlap': ['Memory-specific transactional semantics and lifecycle fault suites are existing work.', 'Post-snapshot stale-write rejection precedes authority comparison in the stated protocol.'],
  'not_established': ['General arbitrary multi-record predicate serializability.', 'Durable OS-process recovery or an atomically enforced remote sink fence.'],
  'code': 'https://github.com/lxy1134/MEMTX_/tree/4e1124ccd5fd384857463020e3497aa73ec93be6',
  'code_status': 'Pinned public source verified; no license identified. Selected source was inspected; sibling subsequently fetched the full archive and executed independent probes. See separate probe artifact for results.'},
 '2609.21284': {
  'locations': ['Formal assurance model', 'Root-scoped revocation and protected-effect admission', 'Exact rebind and durable conformance evaluation'],
  'scope': 'Root epochs, protected-effect fences, effect-envelope identity, receipt obligations and exact rebind address revocation during asynchronous execution. Evaluated effects are provider-free local-ledger effects under complete mediation and monotone durable authority assumptions.',
  'overlap': ['Epoch plus receipt plus immutable effect binding is directly prior art.', 'Historical accepted effects and currently authorized new effects are explicitly separated.'],
  'not_established': ['Automatic mediation of arbitrary remote providers.', 'Memory extraction or arbitrary semantic duplicate equivalence.'],
  'code': None, 'code_status': 'No author implementation URL located in inspected primary PDF/HTML/landing page or focused title search. A cited third-party specification is not its artifact.'},
 '2609.08258': {
  'locations': ['§3.3', 'Appendix B.3', 'Appendix C'],
  'scope': 'Five-system empirical revocation study connects memory exposure to unsafe downstream actions. Mem0 default expiry filtering hides expired records; the exposed arm intentionally includes them. Natural write-back and propagation extensions are Graphiti-specific.',
  'overlap': ['Revocation persistence and retrieval-to-action failure are established empirical questions.', 'Default versus exposed or bypassed filtering must be controlled.'],
  'not_established': ['All five default configurations fail.', 'Concurrent write/delete ordering, receipt reclamation or process-crash recovery.'],
  'code': 'https://github.com/VulcanLab/Memory-Rebirth-Attack/tree/c28e96f1b885b71bb470dfdc1011b2435025aac0',
  'code_status': 'Pinned public source, Apache-2.0. Full experiment requires Neo4j/model endpoints; pyproject includes a sibling editable Graphiti dependency. Standalone guard selfchecks are narrower.'},
 '2609.04875': {
  'locations': ['Runtime-state target and dependency model', 'Prefix restoration and sanitized replay', 'Assumptions and limitations'],
  'scope': 'Forgetting changes transcript, derived memory, pending plans and caches through provenance-selected restoration and replay. The target is counterfactual execution state, assuming reproducible transitions, recorded tool observations and restorable environments.',
  'overlap': ['Deleting a memory row alone does not erase derived plans or runtime influence.', 'Sanitized replay and dependency-aware forgetting are existing mechanisms.'],
  'not_established': ['Undoing arbitrary irreversible external effects.', 'Receipt identity lifetimes or exactly-once mutation admission.'],
  'code': None, 'code_status': 'No author artifact URL located in inspected primary sources/focused title search; reference links to other agent projects are not this implementation.'},
 '2606.06240': {
  'locations': ['Operator isolation preconditions', 'Keyed judge log and replay consistency', 'Appendix C.4 and PostgreSQL experiments'],
  'scope': 'Bitemporal memory operators specify winner/audit semantics and isolation preconditions. A keyed materialized judge decision stabilizes replay within its schedule model. PostgreSQL concurrency experiments distinguish real isolation from reference annotations.',
  'overlap': ['Memory-specific history contracts, retained nondeterministic judge decisions and multi-writer isolation are direct antecedents.', 'Write skew and unsafe operator composition are already analyzed.'],
  'not_established': ['A general arbitrary remote-effect revocation protocol.', 'Availability of the advertised author repository at audit time.'],
  'code': 'https://github.com/ZenAlexa/toki-bitemporal-memory',
  'code_status': 'Advertised repository returned HTTP 404 through GitHub and API. This is an availability observation, not evidence of fabrication or nonexistence.'},
 '2606.17182': {
  'locations': ['§§I–III', '§§VI–VII', 'Snapshot-insufficiency observation', 'Realizability and refinement limitations'],
  'scope': 'Formal detectors and guarded runtimes cover stale generation, causal cascades, tool-registry changes and effect ordering. The paper explicitly treats the anomalies as classical. Higher-level executable verification and live-runtime deployments have different assurance scopes.',
  'overlap': ['A small agent concurrency model or write-skew example is not a new principle.', 'Read–generate–write histories and snapshot insufficiency already have direct formal treatment.'],
  'not_established': ['Every deployed runtime implements every verified level.', 'A public author artifact URL from the inspected primary links.'],
  'code': None, 'code_status': 'Primary body describes an artifact bundle and runnable twins; no author hosting URL located among inspected links. Do not treat descriptions as a runnable baseline obtained by us.'},
 '2606.17573': {
  'locations': ['§§3.1–3.5', '§§4.4–4.6', '§§5–6.5'],
  'scope': 'Semantic transactions bind result lineage, shadow local state, delegated authority and an effect outbox. Composed validation precedes release. Opaque or unsupported external effects can require audit and compensation rather than full containment.',
  'overlap': ['Whole-task semantic validation before external release and an outbox are existing agent mechanisms.', 'Per-operation safety does not imply composed-plan safety.'],
  'not_established': ['Automatic reversibility or semantic visibility for arbitrary external services.', 'A public author implementation URL located in inspected primary links.'],
  'code': None, 'code_status': 'Paper reports an implementation; no author code URL located in inspected primary links. Conference template text alone does not establish acceptance.'},
 '2605.26252': {
  'locations': ['§§3.1–3.4', '§4', '§5 research agenda'],
  'scope': 'GEM treats governed memory as an evolving state trajectory with version, dependency, provenance and active-state correctness. MemState demonstrates it on Kuzu. Several native-engine and trajectory-benchmark goals are research agenda rather than completed universal guarantees.',
  'overlap': ['History-aware memory correctness and trajectory-level evaluation are prior conceptual work.', 'Current-value recall alone misses provenance, revision and footprint requirements.'],
  'not_established': ['A distributed revocation fence or durable operation-receipt protocol.', 'A fully implemented native engine for all proposed operators.'],
  'code': 'https://github.com/CoDS-GCS/MemState',
  'code_status': 'Author URL found in primary paper. Not fetched or executed in this bounded audit; no pinned runnable-baseline claim.'},
 '2610.15991': {
  'locations': ['§§3.1–3.5', '§§4–5', '§7', 'Appendix D'],
  'scope': 'A bounded C0–C5 monitor distinguishes revocation publication and receiver persistence from protected-effect prevention. The primary body includes real Keycloak/gateway and file/PostgreSQL effect surfaces, with frozen gateway/call/window contracts.',
  'overlap': ['Acknowledgement or persisted revocation is insufficient evidence of enforcement.', 'Independent effect oracles and scope-frozen outcomes already have a direct agent-tool study.'],
  'not_established': ['Unbounded, all-provider revocation completion.', 'Memory semantic deduplication or a universal identity scheme.'],
  'code': None, 'code_status': 'This audit verifies the primary description, not a downloaded executable author baseline.'},
 '2610.00347': {
  'locations': ['Assurance assumptions', '§§4–6', '§§7–8'],
  'scope': 'Generation identity, atomic predecessor fencing/successor activation and root-lifetime authority conservation prevent rollback from reminting authority. Guarantees assume complete mediation, authenticated records, durable monotone state and complete lineage.',
  'overlap': ['Epoch rollback and fresh generation versus repeated logical occurrence are not unexplored authority problems.', 'Atomic admission and durable authority state are existing assumptions/mechanisms.'],
  'not_established': ['Unmediated arbitrary provider enforcement.', 'Semantic equivalence of extracted memory facts.'],
  'code': None, 'code_status': 'Primary model and evaluation description reviewed; no obtained runnable-baseline claim.'},
}

catalog = []
for aid, audit in PAPERS.items():
    key = aid.replace('.', '_')
    meta = json.loads((CACHE / (key + '_datacite.json')).read_text())['data']['attributes']
    catalog.append(dict(arxiv_id=aid, title=meta['titles'][0]['title'],
        authors=[c['name'] for c in meta['creators']], doi=meta['doi'],
        arxiv_version=meta.get('version'), publication_status='arXiv primary preprint; this audit does not certify peer review',
        verification='arXiv landing/PDF/HTML plus DataCite title/author metadata; targeted full-body sections inspected',
        evidence=[evidence(key + suffix) for suffix in ('_abs', '_html', '_pdf', '_datacite')], **audit))
save('expanded_scholarly_source_audits.json', dict(reviewed_utc=NOW,
    scope='Focused closest-work audit, not exhaustive academic coverage. Summaries are auditor prose, not source abstracts.',
    full_text_or_code_redistributed=False, records=catalog))

matrix = [
 ('stable_receipts', ['RIFL', 'Beldi', 'Permission to Retry', 'LIMBO', 'Verified Tool Calls'],
  'Stable logical identity, a retained completion/effect record and logged nondeterministic decisions are established recovery mechanisms.',
  'An implementation comparison may expose violated preconditions; combining these mechanisms is not a new algorithm.'),
 ('changed_plan_binding', ['Beldi', 'TOKI', 'Temporal deterministic replay', 'LangGraph durable execution order documentation', 'AWS idempotency guidance'],
  'Regenerating or compacting a plan while retaining positional identities can bind a different operation to an old identity. Replay keys and retained decisions directly precede this question.',
  'A fresh-model witness can illustrate the known order/identity hazard, not establish its first discovery.'),
 ('revocation_fence', ['Root-Scoped Quiescence (2609.21284)', 'Revocation Is Not Complete at Receipt (2610.15991)', 'Chubby', 'Hazelcast FencedLock', 'Temporal MCP cancellation docs'],
  'Revocation or cancellation must reach protected-effect admission; an old worker or completed transport acknowledgement is insufficient.',
  'A memory API with no promised quiescence has a feature boundary, not automatically a contract defect.'),
 ('immutable_binding_current_authority', ['Root-Scoped Quiescence (2609.21284)', 'Authority Succession (2610.00347)', 'ACRFence', 'RIFL'],
  'Immutable accepted-operation binding and monotone current authority answer different questions; epochs, exact rebind and historical obligations already make this distinction.',
  'Dedup-before-fence can return historical success without new mutation; fence-before-dedup can deny. Typed status contracts are required before declaring either incorrect.'),
 ('memory_history_lifecycle', ['MemTX', 'TOKI', 'MemState/GEM', 'Revoked but Still Authoritative (2609.08258)', 'Execution-State Unlearning (2609.04875)', 'Memora', 'TimlMemBench'],
  'Lifecycle changes, stale writes, dependency repair, memory exposure and trajectory correctness already extend evaluation beyond recall.',
  'No first beyond-recall memory benchmark claim is supportable from this audit.'),
 ('multi_record_constraints', ['Classical SQL write skew', 'Serializable snapshot isolation', 'Verified Concurrency Anomalies (2606.17182)', 'TOKI', 'Cordon', 'Agentic Transaction'],
  'Independently valid conditional writes can jointly violate a predicate; per-key linearizability and snapshot isolation do not supply arbitrary multi-record serializability.',
  'Write skew is classical. A MemTX partial-commit path should not be scored against an unclaimed whole-plan invariant.'),
 ('identity_lifetime_reuse', ['RIFL safe reclamation', 'AWS DynamoDB TransactWriteItems token window', 'Stripe API v1 idempotency', 'Temporal Nexus retention', 'Authority Succession'],
  'Dedup state has an explicit validity/reclamation scope. Legitimate later occurrences and stale earlier retries must be distinguished.',
  'Reexecution after an advertised retention window is not a violation. Permanent content-hash suppression is not equivalent to operation identity.'),
 ('public_implementation_conformance', ['MemTX primary/code pair', 'Mem0 public issues/discussions', 'Jepsen', 'Elle'],
  'Independent histories and effect/cardinality oracles can test whether a pinned implementation realizes a narrowly stated contract.',
  'A bounded discrepancy is useful evidence but does not by itself establish a new protocol, general prevalence or journal readiness.'),
 ('bounded_retrieval_dedup', ['Mem0 discussion #6726', 'MiniMem public Mem0 code-reading note', 'Lore pinned-source audit', 'Mem0 issue #6515', 'Mem0 issue #7612'],
  'Write-time semantic duplicate recognition is publicly described as candidate bounded; concurrency and expiration separately affect exact-hash handling.',
  'A conditional sequential literal N−k capacity witness is narrower than these reports, but broad retrieval-to-write dependence is already described.')
]
save('overlap_matrix.json', dict(reviewed_utc=NOW, source_cutoff='2026-10-29 inclusive',
    no_exhaustiveness_claim=True, no_new_recovery_algorithm_claim=True,
    terminology={'standard':'No formal industry standard or certification is claimed. Jepsen is a testing practice/tool; linearizability and serializability are mathematical correctness conditions; vendor contracts are product-specific.'},
    records=[dict(id=k, antecedents=a, established=e, residual_or_caveat=r) for k,a,e,r in matrix]))

hypotheses = [
 dict(id='H1_memtx_snapshot_read', status='Independently probed by sibling; consult its frozen raw artifact, not this literature file for counts.',
  question='Does an old transaction retrieve a new unrelated committed record absent from its captured snapshot?',
  prediction='The pinned retrieve path scans current lifecycle-visible records, so the post-begin record may be returned despite the paper snapshot-read wording.',
  falsifier='Old transaction excludes the record while a fresh transaction includes it, or a primary latest-read exception is located.',
  controls=['Four risk tiers', 'Empty and nonempty start snapshots', 'Unrelated new slot, no revocation ambiguity', 'Fresh transaction'],
  contribution_bound='A pinned description/implementation conformance discrepancy, not a new isolation principle.'),
 dict(id='H2_memtx_empty_snapshot', status='Independently probed by sibling; consult its frozen raw artifact.',
  question='Does an empty snapshot bypass the pre-authority stale-rival rejection applied to a nonempty snapshot?',
  prediction='A same-source or higher-authority old writer can supersede a post-begin rival when the start set is empty, while the anchored version aborts.',
  falsifier='Both anchored and empty starts reject all post-begin conflicting candidates before authority comparison.',
  controls=['Equal same-source, higher, lower and equal different-source authorities', 'Unequal values in same entity/attribute/scope', 'Overlapping validity and sufficient evidence', 'Fresh-after-rival correction controls'],
  contribution_bound='An empty-set sentinel boundary under the explicitly stated temporal rule; fresh-transaction authority correction is intended and the paper itself discusses that escape.'),
 dict(id='H3_mem0_literal_capacity', status='Parent-owned experiment in progress; no result inferred here.',
  question='Can sequential exact-text replay of N unique already-stored facts evade exact-hash suppression when only k existing results feed the hash set?',
  prediction='Conditional on N valid facts with distinct exact-text hashes being re-emitted and no additional suppression, at most k can match that set; at least max(0,N−k) writes survive. This is a conditional capacity bound, not a model-quality claim.',
  falsifier='Pinned production path supplies a complete exact-hash index or another global exact-text suppression step before commit, or controlled replay produces fewer accepted writes for a documented additional reason.',
  controls=['N=9,10,11,20,40 with fixed k=10', 'Literal hashes and physical cardinality independently counted', 'Single writer excludes known TOCTOU race', 'Top-k trace captured, not inferred from a final search', 'Age recent conversation context out before fresh-model confirmation', 'Change only candidate bound or exact lookup in causal controls', 'Keep inferred/raw paths separate; do not mix stores'],
  contribution_bound='Known bounded candidate mechanism, potentially a narrower measured literal-repeat consequence. No first claim or exactly-once vendor promise.'),
 dict(id='H4_expiry_identity_scope', status='Proposed discriminator; related Mem0 #7612 is already reported.',
  question='Does an exact-content index preserve legitimate later writes after old content expires or is revoked?',
  prediction='A global forever-hash index can improve replay suppression while suppressing a legitimate new occurrence; a declared occurrence/epoch/window contract distinguishes the cases.',
  falsifier='The declared contract intentionally treats all lifetime repeats as the same event, or active/expired and new-occurrence controls are all correctly distinguished.',
  controls=['Historical replay versus fresh occurrence', 'Active versus expired versus deleted record', 'Same versus new authority epoch', 'Explicit retention boundary'],
  contribution_bound='Lifetime tradeoff is prior art in RIFL and API contracts; a new universal identity scheme is not presumed.'),
 dict(id='H5_revoke_inflight_write', status='Proposed contract probe, not a new protocol.',
  question='Can a pending memory write admitted before delete/revoke recreate an authoritative record after the barrier?',
  prediction='An API without sink-enforced epoch admission may allow the write, but this is a defect only if quiescence or terminal deletion was promised.',
  falsifier='Protected sink atomically checks the new epoch with effect acceptance; pending old writes are rejected in the declared boundary.',
  controls=['Admission before and after barrier', 'Receipt lookup before/after fence', 'Historical-success acknowledgement versus new effect', 'Fresh authorized post-barrier occurrence'],
  contribution_bound='Revocation fencing, stale-worker prevention and acknowledgement/effect separation are directly prior art.'),
 dict(id='H6_composed_constraints', status='Known negative control; low novelty.',
  question='Do independently committed conditional mutations preserve a declared multi-record semantic invariant?',
  prediction='Per-record CAS or snapshot reads can allow classical write skew unless the read/predicate set is validated or the whole plan is serialized.',
  falsifier='Serializable whole-plan baseline or atomic constraint validation rejects the conflicting schedule.',
  controls=['Declared whole-plan versus per-operation oracle', 'Disjoint write sets sharing a predicate', 'Serializable reference', 'Aborts and legitimate action availability'],
  contribution_bound='Do not relabel classical write skew or a permitted partial commit as a new defect.')
]
save('falsifiable_hypotheses.json', dict(reviewed_utc=NOW, experiments_executed_by_this_audit=False,
    coverage='Questions and falsifiers, not success guarantees or population estimates.', records=hypotheses))

mem0_sources = [
 dict(id='discussion6726', url='https://github.com/mem0ai/mem0/discussions/6726', type='First-person public design discussion; not peer-reviewed evidence',
  summary='Identifies top-ten write-time candidate visibility as a limit on semantic recurrence recognition. Separately assumes exact repeats are caught by MD5; no literal N−k batch experiment was found in the inspected body.', evidence=evidence('mem0_discussion6726')),
 dict(id='issue6515', url='https://github.com/mem0ai/mem0/issues/6515', type='Public issue with reported reproducer; not rerun in this audit',
  summary='Reports same-fact concurrent calls reading stale pre-insert hashes and inserting distinct UUIDs. This is a TOCTOU race, distinct from sequential candidate capacity.', evidence=evidence('mem0_issue6515')),
 dict(id='issue7612', url='https://github.com/mem0ai/mem0/issues/7612', type='Public issue with reported real-backend reproducer; not rerun here',
  summary='Reports expired records suppressing a fresh inferred write of the same fact while default reads hide the old record. It demonstrates why exact-content identity needs an explicit validity scope.', evidence=evidence('mem0_issue7612')),
 dict(id='issue4896', url='https://github.com/mem0ai/mem0/issues/4896', type='Public issue and maintainer response',
  summary='Maintainer distinguishes intentional ADD-only contradiction history from exact-text MD5 duplicate suppression. Neither means that inferred ingestion promises request exactly-once semantics.', evidence=evidence('mem0_issue4896')),
 dict(id='minimem_note', url='https://github.com/jianglong-nie/MiniMem/blob/56da9878747104aefc29a51d178cff22d5bf6870/references/paper-reading/Mem0.md', type='Independent public source-reading note; primary evidence of an antecedent claim, not primary evidence for all Mem0 behavior',
  summary='Describes top-ten extraction context and growth of paraphrastic duplicates, while treating MD5 as exact-repeat protection. The file cites June inspection; verifiable repository history is July 30, 2026, commit 56da9878747104aefc29a51d178cff22d5bf6870.', evidence=evidence('minimem_pinned_audit')),
 dict(id='lore_note', url='https://github.com/corespeed-io/lore/blob/main/docs/research/mem0-token-efficient-algorithm-audit.md', type='Independent pinned-source audit; primary evidence of an antecedent analysis',
  summary='An August-dated audit distinguishes OSS from managed platform and lists ten retrieved records, exact hashing and batch UUID insertion. The inspected passage does not derive or test the literal batch-capacity bound.', evidence=evidence('lore_mem0_audit')),
 dict(id='platform_architecture', url='https://github.com/mem0ai/mem0/blob/26cdefb46600c0fa5953c4b5ee5003c125539fc4/skills/mem0/references/architecture.md', type='Official managed-platform architecture document; platform/OSS scope differs',
  summary='Describes hash duplicate prevention for managed v3. Its top-level platform scope prevents transferring every statement into a guarantee for the tested OSS path.', evidence=evidence('mem0_architecture_pinned')),
]
save('mem0_antecedent_audit.json', dict(reviewed_utc=NOW,
    scope='Focused public issue, discussion, audit-note and pinned-source search; absence of an identical witness is not proof of first discovery.',
    source_cutoff='2026-10-29 inclusive', full_text_or_code_redistributed=False,
    pinned_commit='26cdefb46600c0fa5953c4b5ee5003c125539fc4',
    pinned_source=[evidence('mem0_main_pinned'), evidence('mem0_prompt_pinned')],
    source_locations=[dict(path='mem0/memory/main.py', locations=['881–1034 sync inferred add', '2556–2710 async counterpart'],
        observation='One top_k=10 existing_results cohort supplies both extraction context and existing_hashes; current-batch hashes are separate and accepted facts receive new UUIDs.'),
        dict(path='mem0/configs/prompts.py', locations=['503', '511', '578'],
        observation='Prompt suppression is a separate model-dependent defense; it does not transform a partial exact-hash set into a complete index.')],
    strongest_antecedent='Discussion #6726 explicitly states the bounded candidate dependency; MiniMem independently states its semantic duplicate consequence.',
    remaining_question='Measure literal replay and derive its conditional capacity bound; no universal deduplication or exactly-once promise is inferred.',
    records=mem0_sources))

# Distinguish inherited verification from new fetches; never imply fresh checks.
study_root = HERE.parents[2]
prior = json.loads((study_root / 'literature/selected_primary_manifest.json').read_text())['files']
prior_keys = {'lee2015implementing', 'zhang2020fault', 'marla2026permission',
    'li2026where', 'mansoor2026verified', 'zheng2026acrfence', 'sun2026agentic',
    'zhou2026timlmembench', 'uddin2026memora', 'langchainGraphAPI', 'featonbyIdempotentAPIs'}
inherited = [dict(key=r['key'], url=r['url'], sha256=r['sha256'],
    verification_provenance='Inherited from the existing public-reference audit/catalog; not freshly fetched in this extension pass.',
    full_text_included_in_repository=False) for r in prior if r['key'] in prior_keys]
doc_keys = ['mem0_delete', 'mem0_add_v3', 'letta_blocks', 'letta_detach',
    'temporal_replay', 'temporal_mcp', 'temporal_nexus', 'hazelcast_fencedlock',
    'aws_idempotent_window', 'stripe_idempotency', 'jepsen_linearizability',
    'jepsen_serializability', 'chubby', 'sql_isolation']
save('primary_source_index.json', dict(reviewed_utc=NOW,
    scope='Evidence index for the overlap matrix; inclusion is not a request to add every source to the manuscript bibliography.',
    new_scholarly_records=[dict(arxiv_id=r['arxiv_id'], title=r['title'], evidence=r['evidence']) for r in catalog],
    official_docs_and_classical_landing_pages=[evidence(k) for k in doc_keys],
    supplementary_method_source=dict(title='Elle: Inferring Isolation Anomalies from Experimental Observations',
        evidence=[evidence('elle_abs'), evidence('elle_pdf')],
        review_scope='Supplementary primary method reference; not one of the ten newly audited close agent/memory papers.'),
    inherited_public_primary_sources=inherited,
    mem0_antecedents=[dict(id=r['id'], url=r['url'], evidence=r['evidence']) for r in mem0_sources]))

lines = [
 'Focused recovery/replanning prior-art audit',
 'Cutoff: 2026-10-29 inclusive. Public sources only. No exhaustive-coverage claim.',
 '',
 'Conclusion: an epoch + immutable binding + receipt protocol is not a defensible new mechanism here. RIFL/Beldi, current authority-quiescence work, TOKI, Cordon and formal agent-concurrency work cover the central principles. A new bounded model or a write-skew example alone would duplicate existing theory. The better research question is whether specific public memory implementations realize their narrowly stated history contracts, and which shared implementation preconditions account for discrepancies.',
 '',
 'Closest newly verified work:',
]
for r in catalog:
    lines.extend([f"- {r['title']} ({r['arxiv_id']}, v{r['arxiv_version']}): {r['scope']}",
                  f"  Primary: https://arxiv.org/abs/{r['arxiv_id']}", f"  Artifact: {r['code_status']}"])
lines += ['', 'Overlap and residual scope:']
for key, antecedents, established, residual in matrix:
    lines += [f'- {key}: {established}', f'  Antecedents: {"; ".join(antecedents)}.', f'  Boundary: {residual}']
lines += ['', 'Runnable baseline:',
 'Use the actual MemTX manager pinned at 4e1124ccd5fd384857463020e3497aa73ec93be6 for stated snapshot/stale-writer contracts. Do not claim arbitrary read-set serializability or remote durability. Full-source acquisition and suite execution are in the independent sibling artifact; this literature audit executed no third-party experiment. No license was identified, so retain public URLs/hashes and original adapters only.',
 'Revoked-memory harness is Apache-2.0 but requires Graphiti/Neo4j/model services and includes a sibling editable path. Its default-filter controls are essential. TOKI is conceptually closer for retained judge/transaction contracts, but its advertised author repository returned 404. Availability observations must not be called fabrication.',
 '', 'Mem0 specific novelty check:',
 'The bounded retrieval dependence is already discussed in #6726 and a July-30 public MiniMem note. The latter internally dates its inspection to June; only July-30 repository publication was verified. Both concentrate on semantic recurrence and assume literal MD5 protection. The narrower candidate is a conditional exact-text N−k capacity witness through the current real path. #6515 already reports concurrent hash TOCTOU duplicates; #7612 already reports expired records suppressing fresh writes. Separate these mechanisms, versions and evidence types.',
 '', 'Falsifiable next questions:']
for h in hypotheses:
    lines += [f"- {h['id']}: {h['question']}", f"  Falsifier: {h['falsifier']}", f"  Scope: {h['contribution_bound']}"]
lines += ['', 'Research bar:',
 'A few correct reproductions or implementation discrepancies can justify an artifact/empirical contribution, but do not establish high-journal novelty. A stronger study needs an independent contract/oracle, negative controls, matched baselines, versions and seeds, causal interventions, and replication across more than one implementation. Report nonviolations and intentional boundaries as well as failures. No impact or acceptance guarantee follows.',
 '', 'Terminology:',
 'Jepsen is testing practice/tooling; linearizability and serializability are mathematical correctness conditions. Vendor API documentation supplies product-specific contracts. This audit identifies no formal industry certification standard satisfied by the artifact.',
 '', 'Evidence handling:',
 'Only public source URLs, metadata, SHA-256 values and bounded auditor summaries are distributed. Full papers and third-party code remain in a temporary non-distributed cache. arXiv title/author metadata was cross-checked with DataCite; no Semantic Scholar ID, DOI abstract or code-availability assertion was fabricated. Preprint availability is not peer-review verification.',
]
(HERE / 'overlap_matrix.txt').write_text('\n'.join(lines) + '\n')
(HERE / 'falsifiable_hypotheses.txt').write_text('\n\n'.join(
    f"{h['id']}\nQuestion: {h['question']}\nPrediction: {h['prediction']}\nFalsifier: {h['falsifier']}\nControls: {'; '.join(h['controls'])}.\nStatus: {h['status']}\nContribution bound: {h['contribution_bound']}" for h in hypotheses) + '\n')

checks = dict(created_utc=NOW, scholarly_records=len(catalog),
    scholarly_evidence_records=sum(len(r['evidence']) for r in catalog),
    all_scholarly_fetches_http_200=all(e.get('http_status') == 200 for r in catalog for e in r['evidence']),
    all_scholarly_evidence_hashes_present=all(len(e.get('sha256', '')) == 64 for r in catalog for e in r['evidence']),
    pdf_identity_check='pdf_identity_check.json: all ten extracted titles and author surnames match DataCite in the first two pages.',
    source_summaries_are_auditor_prose=True, third_party_text_redistributed=False,
    output_hashes={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(HERE.glob('*'))
        if p.is_file() and p.name in ['expanded_scholarly_source_audits.json', 'overlap_matrix.json',
            'overlap_matrix.txt', 'falsifiable_hypotheses.json', 'falsifiable_hypotheses.txt',
            'mem0_antecedent_audit.json', 'primary_source_index.json']})
save('audit_validation.json', checks)
print(json.dumps(checks, indent=2))
