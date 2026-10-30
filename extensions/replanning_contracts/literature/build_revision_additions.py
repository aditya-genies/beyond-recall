"""Generate proposed citation additions from audited public metadata only."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CACHE = Path('/tmp/beyond-recall-public-literature-20261029')
NOW = datetime.now(timezone.utc).isoformat()

SELECTION = [
 ('2607.23929', 'li2026memtx', 'essential', 'Actual tested public reference and its snapshot/temporal contract.'),
 ('2606.06240', 'wang2026toki', 'essential', 'Memory-specific history, operator isolation and retained judge decisions.'),
 ('2609.08258', 'shen2026revoked', 'essential', 'Closest five-system memory revocation evaluation; retain default-filter distinction.'),
 ('2609.04875', 'yao2026forgetting', 'essential', 'Forgetting includes derived state and pending plans, with restorable-execution assumptions.'),
 ('2609.21284', 'zhu2026quiescence', 'essential', 'Direct root-epoch, protected-effect fence, exact-binding and receipt antecedent.'),
 ('2606.17182', 'khan2026concurrency', 'essential', 'Direct formal treatment of long read–generate–write histories and snapshot insufficiency.'),
 ('2606.17573', 'chen2026cordon', 'essential', 'Composed semantic transactions, lineage and effect outbox precede per-plan recovery framing.'),
 ('2605.26252', 'orogat2026memory', 'essential', 'Governed memory trajectory and state-level correctness are established conceptual framing.'),
 ('2610.15991', 'liu2026receipt', 'context_if_receipt_enforcement_discussed', 'Use only if the revised paper discusses acknowledgement versus revocation enforcement.'),
 ('2610.00347', 'zhu2026succession', 'context_if_authority_lifetime_discussed', 'Use only if generation rollback or authority lifetime remains substantive; omit otherwise.'),
]
audits = {r['arxiv_id']: r for r in json.loads((HERE / 'expanded_scholarly_source_audits.json').read_text())['records']}
entries = []
claims = []
for aid, key, priority, reason in SELECTION:
    r = audits[aid]
    fields = dict(author=' and '.join(r['authors']), title='{' + r['title'] + '}',
        year='2026', howpublished='arXiv preprint', archivePrefix='arXiv', eprint=aid,
        doi=r['doi'], url=f'https://arxiv.org/abs/{aid}v{r["arxiv_version"]}',
        note='Version ' + r['arxiv_version'] + '; preprint')
    entries.append((key, 'research_preprint', fields))
    claims.append(dict(bibtex_key=key, priority=priority, reason=reason,
        grounded_claim=r['scope'], must_not_claim=r['not_established'],
        primary_locations=r['locations'], evidence=r['evidence'],
        metadata_status='PDF title and author surnames matched DataCite; primary HTML/body sections reviewed.',
        peer_review_status='Not independently verified; cite as preprint rather than infer acceptance from a template header.',
        distribution='Only URLs, hashes, metadata and auditor prose; no full text.'))

PROJECTS = [
 ('mem0contributors2026oss', 'tested_runtime', dict(author='{Mem0 contributors}',
  title='{Mem0}: Python memory implementation', year='2026',
  howpublished='Public source repository',
  url='https://github.com/mem0ai/mem0/blob/26cdefb46600c0fa5953c4b5ee5003c125539fc4/mem0/memory/main.py',
  note='Python package mem0ai 2.2.1; commit 26cdefb46600c0fa5953c4b5ee5003c125539fc4; accessed 2026-10-29'),
  'Identify the tested OSS source; its inferred-ingestion path differs from the earlier Mem0 paper and managed-platform documentation.',
  ['mem0_pinned_source_manifest.json', 'runtime_project_fetch_manifest.json']),
 ('memtx2026code', 'tested_artifact', dict(author='{lxy1134}',
  title='{MemTX}---Code and Data', year='2026', howpublished='Public source repository',
  url='https://github.com/lxy1134/MEMTX_/tree/4e1124ccd5fd384857463020e3497aa73ec93be6',
  note='Commit 4e1124ccd5fd384857463020e3497aa73ec93be6; accessed 2026-10-29'),
  'Identify the exact public manager/detector used by the independent adapter. The owner handle is attribution, not an inferred paper-author list.',
  ['baseline_repository_audit.json', '../memtx_reference/results/provenance.json']),
 ('qdrant2026client', 'tested_runtime', dict(author='{Qdrant contributors}',
  title='{Qdrant} Python Client', year='2026', howpublished='Software release',
  url='https://github.com/qdrant/qdrant-client/tree/v1.20.0',
  note='Version 1.20.0; local-mode client used in this study; accessed 2026-10-29'),
  'Identify local Qdrant persistence/client runtime, not a distributed server evaluation.',
  ['runtime_project_fetch_manifest.json']),
 ('qdrant2026fastembed', 'tested_runtime', dict(author='{Qdrant contributors}',
  title='{FastEmbed}', year='2026', howpublished='Software release',
  url='https://github.com/qdrant/fastembed/tree/v0.9.1',
  note='Version 0.9.1; accessed 2026-10-29'),
  'Identify ONNX embedding inference runtime; no embedding-quality result is claimed.',
  ['runtime_project_fetch_manifest.json']),
 ('baai2023bgesmall', 'model_identity', dict(author='{BAAI}',
  title='{bge-small-en-v1.5}: Model Card', year='2023', howpublished='Official model card',
  url='https://huggingface.co/BAAI/bge-small-en-v1.5',
  note='384-dimensional English embedding model; accessed 2026-10-29'),
  'Identify the real embedding model. A model-card citation does not pin the specific FastEmbed ONNX files or establish semantic deduplication quality.',
  ['runtime_project_fetch_manifest.json']),
 ('oleson2026recency', 'direct_public_antecedent', dict(author='{PhilOleson}',
  title='Design: mention-and-recency-aware retrieval', year='2026',
  howpublished='Mem0 GitHub Discussion 6726',
  url='https://github.com/mem0ai/mem0/discussions/6726',
  note='Posted 2026-08-02; accessed 2026-10-29'),
  'Direct public antecedent for top-ten candidate visibility. It treats literal MD5 suppression as a separate protection; no inspected literal N-minus-k batch witness.',
  ['focused_issue_fetch_manifest.json', 'mem0_antecedent_audit.json']),
 ('nie2026mem0reading', 'direct_public_antecedent', dict(author='{jianglong-nie}',
  title='{Mem0}', year='2026', howpublished='MiniMem public code-reading note',
  url='https://github.com/jianglong-nie/MiniMem/blob/56da9878747104aefc29a51d178cff22d5bf6870/references/paper-reading/Mem0.md',
  note='Public repository commit dated 2026-07-30; source-inspection date stated inside the note differs; accessed 2026-10-29'),
  'Public July-30 antecedent describes bounded extraction context and semantic duplicate accumulation. Do not substitute its internal June inspection date for verified public availability.',
  ['mem0_additional_antecedent_manifest.json', 'mem0_pinned_source_manifest.json']),
 ('corespeed2026mem0audit', 'optional_public_antecedent', dict(author='{corespeed-io}',
  title='{Mem0} token-efficient algorithm: source and benchmark audit', year='2026',
  howpublished='Lore public source audit',
  url='https://github.com/corespeed-io/lore/blob/b71e22464880a832560305a10e525f4dd3a3284f/docs/research/mem0-token-efficient-algorithm-audit.md',
  note='Public repository commit dated 2026-08-08; accessed 2026-10-29'),
  'Optional corroborating antecedent for the ten-candidate/hash/UUID pipeline; not peer-reviewed evidence or a causal replay experiment.',
  ['mem0_additional_antecedent_manifest.json', 'mem0_pinned_source_manifest.json']),
]
for key, kind, fields, scope, files in PROJECTS:
    entries.append((key, kind, fields))
    claims.append(dict(bibtex_key=key, priority=kind, grounded_claim=scope,
        evidence_files=[dict(path=f, sha256=hashlib.sha256((HERE / f).read_bytes()).hexdigest()) for f in files],
        peer_review_status='Software, model card or public discussion/audit; not a peer-reviewed research paper.',
        distribution='Full source remains external; repository contains metadata and hashes only.'))


def bibentry(key, fields):
    lines = ['@misc{' + key + ',']
    lines.extend('  ' + name + ' = {' + val + '},' for name, val in fields.items())
    lines[-1] = lines[-1].removesuffix(',')
    lines.append('}')
    return '\n'.join(lines)

(HERE / 'additions.bib').write_text('% Proposed additions only; main bibliography is unchanged.\n'
    '% Ten verified preprints; eight essential, two conditional on retained discussion.\n'
    '% Runtime/artifact/public-note entries are classified separately in new_claim_map.json.\n\n'
    + '\n\n'.join(bibentry(k, f) for k, _, f in entries) + '\n')

empirical_files = [
 'extensions/replanning_contracts/mem0_reference/results/frozen_spec.json',
 'extensions/replanning_contracts/mem0_reference/results/summary.json',
 'extensions/replanning_contracts/mem0_reference/verification.json',
 'extensions/replanning_contracts/memtx_reference/audit_summary.json',
 'extensions/replanning_contracts/memtx_reference/results/provenance.json',
]
map_data = dict(prepared_utc=NOW, source_cutoff='2026-10-29 inclusive',
    task_scope='Proposed additions and a short amendment only; no main paper or bibliography edits.',
    writing_isolation='Exact PaperOrchestra anti-leakage prompt reapplied; only current independent public-source audits and fresh independent experiment artifacts used. Named author instruction remains an explicit user exception.',
    index_verification='Primary PDF/HTML/landing identities cross-checked with DataCite. Semantic Scholar was not used in this pass; no S2 IDs or abstract fields are fabricated.',
    research_preprints=10, essential_preprints=8, conditional_preprints=2,
    nonpaper_entries=len(PROJECTS), records=claims,
    current_experimental_evidence=[dict(path=f, sha256=hashlib.sha256((ROOT / f).read_bytes()).hexdigest()) for f in empirical_files],
    permitted_new_claims=[
      'For the pinned sequential OSS path, a candidate-derived exact-hash set has at most k distinct existing hashes. Conditional on N distinct-hash facts being re-emitted without additional suppression, at least max(0,N-k) survive this check. The bound is elementary counting, not a new recovery theorem.',
      'The controlled Mem0 parameter sweep tests physical cardinality separately from exact fact-set equality, and intervention arms identify the candidate-bound dependency. These are finite parameter executions, not independent natural model trials.',
      'Actual pinned MemTX API probes can be compared with the explicit snapshot-read and pre-authority temporal-rejection wording. Limit the label to the tested paper/code boundaries; do not claim all lifecycle invariants or all snapshot behavior fail.',
    ],
    prohibitions=[
      'No first memory lifecycle benchmark, new epoch/receipt protocol, novel write-skew principle or universal exactly-once guarantee.',
      'No live-model result, frequency or incidence claim: the 28 planned requests and 24 recorded-result controls are pending at this writing boundary.',
      'No managed Mem0 Platform extrapolation from OSS, and no distributed Qdrant-server claim from local mode.',
      'No claim authored widened-candidate/exact-admission controls are stock options or concurrent production fixes.',
      'No claim passing source tests proves complete conformance; the MemTX optional tau2 collection error remains disclosed.',
      'No natural-incidence confidence interval from 96 parameter cells and no journal readiness inferred from test or citation count.',
    ],
    interpretation='The narrower evidence advances an empirical implementation-contract study. Established mechanisms and broad principles remain prior art; high-journal novelty requires a stronger generalizable contribution and replication, not counts alone.')
(HERE / 'new_claim_map.json').write_text(json.dumps(map_data, indent=2, ensure_ascii=False) + '\n')

amendment = r'''Proposed related-work amendment (current evidence only; no live-model outcomes)

Memory correctness already extends beyond recall. GEM/MemState frames memory as a governed state trajectory, while TOKI specifies bitemporal operators, isolation preconditions and retained judge decisions \citep{orogat2026memory,wang2026toki}. MemTX adds a belief lifecycle, staged validation, action gating and cascading repair \citep{li2026memtx}. Revocation evaluation and execution-state unlearning separately show why suppressing a stored record need not remove its downstream influence \citep{shen2026revoked,yao2026forgetting}. These works precede our lifecycle and history framing; our MemTX experiment instead checks two narrowly stated boundaries in its pinned public implementation \citep{memtx2026code}.

The underlying recovery principles are also established. Formal agent-concurrency work treats long read--generate--write histories and snapshot insufficiency; Cordon validates composed tool flows using lineage, shadow state and an effect outbox \citep{khan2026concurrency,chen2026cordon}. Root-scoped quiescence already combines epochs, protected-effect fencing and immutable effect bindings under explicit mediation assumptions \citep{zhu2026quiescence}. These mechanisms, together with the durable-execution literature discussed above, prevent attributing algorithmic novelty to our receipt or decision controls.

Public Mem0 discussions and source-reading notes already identify the top-ten candidate window as a limit on semantic duplicate recognition \citep{oleson2026recency,nie2026mem0reading}. Our narrower question concerns exact-text hash suppression in the tested OSS inferred-ingestion path \citep{mem0contributors2026oss}: when the same candidate set supplies the exact-hash check, re-emitting more distinct stored hashes than the set can hold permits repeated physical records. We distinguish that conditional capacity witness from semantic retrieval accuracy, concurrent insertion races, and any vendor exactly-once promise. The experiment evaluates logical fact content and physical multiplicity separately, with controlled extraction and targeted interventions.

Optional only if the revised discussion retains these questions:
Acknowledgement and receiver persistence are distinct from protected-effect prevention in the C0--C5 revocation outcome contract \citep{liu2026receipt}. Authority-succession work separately treats rollback, fresh generations and root-lifetime authority conservation \citep{zhu2026succession}; these are further antecedents rather than new mechanisms of our study.

Methods citation note:
Cite Qdrant local mode, FastEmbed and the BGE-small model card for runtime/model identity \citep{qdrant2026client,qdrant2026fastembed,baai2023bgesmall}. Those references establish neither semantic deduplication quality nor distributed-server behavior. The optional Lore audit \citep{corespeed2026mem0audit} corroborates the public pipeline reading and need not be added if it contributes no distinct point.

Scientific interpretation:
The new evidence is a conditional literal-dedup capacity counterexample and a bounded MemTX paper/code conformance audit. The broad mechanisms are prior art. More cells, live-model calls, passing tests or references do not alone establish a leading-journal contribution. The amendment contains no result from the pending live-model campaign.
'''
(HERE / 'related_work_amendment.txt').write_text(amendment)

keys = [k for k, _, _ in entries]
cited = set(k.strip() for group in re.findall(r'\\cite\w*\{([^}]+)\}', amendment) for k in group.split(','))
main_keys = set(re.findall(r'@\w+\s*\{\s*([^,]+)', (ROOT / 'refs.bib').read_text()))
errors = []
if len(keys) != len(set(keys)): errors.append('duplicate proposed keys')
if set(keys) & main_keys: errors.append('proposed keys collide with existing main bibliography: ' + str(sorted(set(keys) & main_keys)))
if cited - set(keys): errors.append('undefined amendment keys: ' + str(sorted(cited - set(keys))))
bib = (HERE / 'additions.bib').read_text()
depth = 0
for char in bib:
    if char == '{': depth += 1
    if char == '}': depth -= 1
    if depth < 0: errors.append('unbalanced BibTeX closing brace'); break
if depth: errors.append('unbalanced BibTeX braces')
validation = dict(prepared_utc=NOW, status='PASS' if not errors else 'FAIL', errors=errors,
    entry_count=len(keys), preprint_count=10, essential_preprint_count=8,
    optional_preprint_count=2, other_source_count=len(PROJECTS),
    proposed_keys=keys, main_bibliography_modified=False,
    undefined_citation_keys=sorted(cited - set(keys)),
    coverage_note='All ten proposed papers appear in either the core amendment or explicitly conditional sentences. Conditional entries should be omitted if the associated discussion is removed; no citation-count padding is recommended.',
    output_hashes={f:hashlib.sha256((HERE / f).read_bytes()).hexdigest() for f in ['additions.bib','new_claim_map.json','related_work_amendment.txt']})
(HERE / 'revision_additions_validation.json').write_text(json.dumps(validation,indent=2) + '\n')
print(json.dumps(validation,indent=2))
