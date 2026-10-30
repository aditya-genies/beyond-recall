"""Read-only scientific/citation review; writes only this review directory."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,re,urllib.request

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
M=ROOT/'extensions/replanning_contracts/mem0_reference'
OUT=HERE


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def record(p):return dict(path=str(Path(p).relative_to(ROOT)),sha256=sha(p))


sources=[ROOT/'manuscript'/x for x in ('main.tex','public_memory.tex','contract_portability.tex','plan_binding.tex','refs.bib')]
start_hashes={str(p.relative_to(ROOT)):sha(p) for p in sources}
texts={p.name:p.read_text() for p in sources}
citations={k.strip() for part in ('main.tex','public_memory.tex','contract_portability.tex','plan_binding.tex')
    for group in re.findall(r'\\cite\w*\{([^}]+)\}',texts[part]) for k in group.split(',')}
entries=re.findall(r'@\w+\s*\{\s*([^,]+)',texts['refs.bib'])
assert len(entries)==len(set(entries))==len(citations)==54
assert not citations-set(entries) and not set(entries)-citations

# Independently recompute the simple new numerical claims from recorded rows.
controlled=load(M/'results/cases.json')
count_errors=[]
for row in controlled:
    counts=[len(a['records']) for a in row['attempts']]
    expected=[row['n']]*3
    if row['arm']=='native_k10' and row['n']>10:
        expected=[row['n'],2*row['n']-10,3*row['n']-20]
    if counts!=expected:count_errors.append(row)
    assert all({r['memory'] for r in a['records']}=={r['memory'] for r in row['attempts'][0]['records']} for a in row['attempts'])
assert len(controlled)==96 and sum(len(r['attempts']) for r in controlled)==288 and not count_errors
assert sum(len(r['attempts'][-1]['records'])>r['n'] for r in controlled if r['arm']=='native_k10')==20

live=load(M/'live_results/results.json')
base,retries=live['baselines'],live['retries']
assert len(base)==4 and len(retries)==48
for b in base:
    assert b['child_returncode']==87 and len(b['after'])==b['n_requested_source_preferences']
    assert len({r['memory'] for r in b['after']})==b['n_requested_source_preferences']
fresh_native=[r for r in retries if r['arm']=='native_k10' and r['strategy']=='fresh_model']
retained_native=[r for r in retries if r['arm']=='native_k10' and r['strategy']=='recorded_model_result']
assert len(fresh_native)==len(retained_native)==8
def new_records(row):
    old={r['id']:r['memory'] for r in row['before']}
    return [r for r in row['after'] if r['id'] not in old],set(old.values())
def literal_copies(row):
    new,old=new_records(row)
    return sum(r['memory'] in old for r in new)
assert sum(literal_copies(r) for r in fresh_native)==91
assert sum(len(new_records(r)[0]) for r in fresh_native)==92
assert sum(literal_copies(r) for r in retained_native)==92
assert all(not new_records(r)[0] for r in retries if r['arm']!='native_k10')
assert all(r['child_returncode']==0 for r in retries)
assert sum(r['request_status']['additional_model_call'] for r in base+retries)==28

cases=load(M/'retrieval_results/cases.json')
assert len(cases)==1008
callkeys={(r['n_source_preferences'],r['state'],r['query'],r['budget']) for r in cases}
assert len(callkeys)==1008
baseline_queries={n:{x['memory'] for b in base if b['n_requested_source_preferences']==n for x in b['after']}
    for n in (8,12,24,40)}
expected={(n,state,q,k) for n,qs in baseline_queries.items() for q in qs
    for state in ('baseline','native_k10','widened_candidates','exact_admission') for k in (5,10,20)}
assert callkeys==expected and sum(map(len,baseline_queries.values()))==84
assert all(any(v['memory']==r['query'] for v in r['results']) for r in cases)
duplicate_cells=sum(len(r['results'])>len({v['memory'] for v in r['results']}) for r in cases)
bykey={(r['n_source_preferences'],r['state'],r['query'],r['budget']):r for r in cases}
lower_diversity=sum(len({v['memory'] for v in r['results']})<len({v['memory'] for v in bykey[r['n_source_preferences'],'baseline',r['query'],r['budget']]['results']}) for r in cases)
assert duplicate_cells==213 and lower_diversity==201
n40=[r for r in cases if r['n_source_preferences']==40 and r['budget']==10 and r['state']=='native_k10']
assert len(n40)==40 and sum(len(r['results']) for r in n40)==400
assert sum(len({v['memory'] for v in r['results']}) for r in n40)==247
assert min(len({v['memory'] for v in r['results']}) for r in n40)==5
reproduction=load(M/'retrieval_results/verification.json')['computational_reproduction']
assert reproduction['status']=='PASS' and reproduction['retained_states_checked']==16
assert reproduction['identical_per_query_metric_cells']==reproduction['identical_ordered_returned_identity_cells']==1008

backend=load(ROOT/'extensions/replanning_contracts/backends/final_verification.json')
assert [backend[k] for k in ['declared_cells','applicable_cells','not_applicable_cells','attempts','abrupt_exit_87']]==[104,96,8,154,10]
assert all(r['duplicate_effects']==r['stale_epoch_effects']==0 for r in backend['case_metrics'])
revoked=[r for r in backend['case_metrics'] if r['history']=='revoke_before_retry']
assert len(revoked)==8 and all(not r['current_visible'] and r['current_epoch']==1 and r['current_version']==1 and 'historical_ack' in r['request_statuses'] for r in revoked)
assert backend['native_aof_grouped_transactions_checked']==16
assert load(ROOT/'extensions/replanning_contracts/backends/results/restart_control.json')['key_count']==72
memtx=load(ROOT/'extensions/replanning_contracts/memtx_reference/audit_summary.json')
assert memtx['main_probe_summary']==dict(read_cases=8,read_cases_returning_post_begin_ids=8,
    fresh_read_controls=8,old_A_cases=8,old_A_rival_superseded=2,old_A_temporal_rejections=4,fresh_A_cases=8)
assert memtx['final_original_unit_tests']['passed']==94

docs=[('redis2026eval','https://redis.io/docs/latest/develop/programmability/eval-intro/'),
    ('redis2026transactions','https://redis.io/docs/latest/develop/using-commands/transactions/'),
    ('sqlite2026transactions','https://www.sqlite.org/lang_transaction.html')]
def fetch(rec):
    key,url=rec
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Public source evidence review/1.0'}),timeout=40) as response:
        body=response.read()
        return dict(key=key,url=url,final_url=response.geturl(),http_status=response.status,
            sha256=hashlib.sha256(body).hexdigest(),bytes=len(body),full_text_redistributed=False)
with ThreadPoolExecutor(max_workers=3) as pool:
    official_docs=list(pool.map(fetch,docs))
assert all(d['http_status']==200 for d in official_docs)

def entry(key):
    match=re.search(r'@\w+\s*\{\s*'+re.escape(key)+r'\s*,',texts['refs.bib'])
    start=match.end();depth=1;i=start
    while depth:
        if texts['refs.bib'][i]=='{':depth+=1
        elif texts['refs.bib'][i]=='}':depth-=1
        i+=1
    return texts['refs.bib'][start:i-1]
def field(text,key):
    match=re.search(r'\b'+key+r'\s*=\s*\{',text);i=match.end();start=i;depth=1
    while depth:
        if text[i]=='{':depth+=1
        elif text[i]=='}':depth-=1
        i+=1
    return text[start:i-1].strip('{}')
audits=load(ROOT/'extensions/replanning_contracts/literature/expanded_scholarly_source_audits.json')['records']
mapping={'li2026memtx':'2607.23929','wang2026toki':'2606.06240','shen2026revoked':'2609.08258',
    'yao2026forgetting':'2609.04875','zhu2026quiescence':'2609.21284','khan2026concurrency':'2606.17182',
    'chen2026cordon':'2606.17573','orogat2026memory':'2605.26252'}
metadata_checks=[]
for key,aid in mapping.items():
    a=next(r for r in audits if r['arxiv_id']==aid);b=entry(key)
    assert field(b,'title')==a['title'] and field(b,'author')==' and '.join(a['authors'])
    assert field(b,'doi').lower()==a['doi'].lower() and field(b,'eprint')==aid
    metadata_checks.append(dict(key=key,primary_identity_match=True,preprint_status_explicit=True))

evidence_paths=[
 'results/summary.json','results/cases.jsonl','results/frozen_spec.json','study.py',
 'extensions/replanning_contracts/mem0_reference/results/frozen_spec.json',
 'extensions/replanning_contracts/mem0_reference/results/cases.json',
 'extensions/replanning_contracts/mem0_reference/verification.json',
 'extensions/replanning_contracts/mem0_reference/live_results/protocol.json',
 'extensions/replanning_contracts/mem0_reference/live_results/results.json',
 'extensions/replanning_contracts/mem0_reference/live_verification.json',
 'extensions/replanning_contracts/mem0_reference/retrieval_results/protocol.json',
 'extensions/replanning_contracts/mem0_reference/retrieval_results/cases.json',
 'extensions/replanning_contracts/mem0_reference/retrieval_results/verification.json',
 'extensions/replanning_contracts/mem0_reference/retrieval_reproduction/retention_protocol.json',
 'extensions/replanning_contracts/mem0_reference/retrieval_reproduction/retained_manifest.json',
 'extensions/replanning_contracts/memtx_reference/freeze.json',
 'extensions/replanning_contracts/memtx_reference/results/traces.json',
 'extensions/replanning_contracts/memtx_reference/audit_summary.json',
 'extensions/replanning_contracts/backends/frozen_spec.json',
 'extensions/replanning_contracts/backends/final_verification.json',
 'extensions/replanning_contracts/backends/results/cases.jsonl',
 'extensions/replanning_contracts/backends/results/restart_control.json',
 'extensions/plan_binding/results/summary.json',
 'extensions/langgraph_reference/results/summary.json',
 'extensions/replanning_contracts/literature/expanded_scholarly_source_audits.json',
 'extensions/replanning_contracts/literature/pdf_identity_check.json',
 'extensions/replanning_contracts/literature/mem0_antecedent_audit.json']
checks=[
 dict(topic='Conditional admission formulas',lines=['manuscript/public_memory.tex:6','manuscript/public_memory.tex:11','manuscript/public_memory.tex:16'],
    outcome='PASS',finding='B=(X∩S)\\H(V) and the conditional lower bound max(0,N-k) are valid with the stated distinct-hash/re-emission assumptions. No unconditional equality or new theorem is claimed.'),
 dict(topic='Native prompt and cache distinctions',lines=['manuscript/public_memory.tex:33','manuscript/public_memory.tex:35','manuscript/public_memory.tex:37','manuscript/public_memory.tex:41'],
    outcome='PASS',finding='Fresh versus aged last-ten-message history, native per-message truncation, empty native Summary/Recently Extracted Memories, complete repeated source, retained baseline-response replay, requested alias and hidden harness settings are distinguished. The recommended default-empty clarification is now present.'),
 dict(topic='Controlled and live denominators',lines=['manuscript/main.tex:24','manuscript/public_memory.tex:19','manuscript/public_memory.tex:23','manuscript/public_memory.tex:39'],
    outcome='PASS',finding='96 cells/288 calls, 20 of 32 native cells, 28 requests/48 retries, 91 exact fresh copies plus one ungraded literal, 92 recorded-result copies and zero intervention additions reconcile.'),
 dict(topic='Retrieval metrics and selected states',lines=['manuscript/public_memory.tex:44','manuscript/public_memory.tex:46','manuscript/public_memory.tex:55','manuscript/public_memory.tex:57'],
    outcome='PASS',finding='All 84 literals × four states × three budgets appear exactly once. All 1008 exact targets pass. The 213/201 distinction, 400/247/153 totals, mean 6.175 and minimum 5 reconcile. The post hoc/fresh-state selection and original-versus-retained-reproduction limits are explicit.'),
 dict(topic='MemTX source fairness',lines=['manuscript/contract_portability.tex:6','manuscript/contract_portability.tex:8','manuscript/contract_portability.tex:10','manuscript/contract_portability.tex:12'],
    outcome='PASS',finding='24 trace units, eight read boundaries, two empty-snapshot overwrites, nonempty/fresh controls and 94 original non-tau2 tests reconcile. Distinct action/repair invariants, optional dependency failures, interpretation by authors and nonredistribution are preserved.'),
 dict(topic='Backend counts and semantics',lines=['manuscript/contract_portability.tex:15','manuscript/contract_portability.tex:17','manuscript/contract_portability.tex:19','manuscript/contract_portability.tex:21'],
    outcome='PASS',finding='104 declared/96 executed/eight inapplicable cells, 154 processes/ten exits, eight revoked historical acknowledgements, 48 SQLite files/72 Redis keys/16 AOF groups and 21 tests reconcile with supplied evidence. Redis isolation is separated from explicit SQLite rollback; profiles are authored bundles and graceful restart is not power loss.'),
 dict(topic='Prior art and bibliography',lines=['manuscript/main.tex:44','manuscript/main.tex:46','manuscript/main.tex:48','manuscript/main.tex:51','manuscript/main.tex:55'],
    outcome='PASS',finding='Eight new research-paper entries match primary PDF/HTML/DataCite audits and are labelled preprints. All 54 bibliography entries are cited with no missing/duplicate keys. Broad mechanisms and bounded-candidate antecedents are credited; no exhaustive-search or first-discovery claim appears. Earlier reference verification is inherited, not represented as freshly redone in this pass.'),
 dict(topic='Native reference and retained-receipt argument',lines=['manuscript/main.tex:203','manuscript/main.tex:207','manuscript/main.tex:220','manuscript/main.tex:232','manuscript/plan_binding.tex:9'],
    outcome='PASS',finding='Native application fast path, one effects-node design and unexplored per-operation tasks are explicit. The CAS/receipt argument requires successful retained binding, monotonic versions and atomic effect/receipt storage, and is not transferred to the primary split stores. The positional witness is attributed to a known adapter order/identity hazard.'),
]

end_hashes={str(p.relative_to(ROOT)):sha(p) for p in sources}
assert end_hashes==start_hashes, 'Manuscript changed during final review; refresh before issuing result'
report=dict(status='PASS_FOR_BOUNDED_WORKING_CLAIMS',reviewed_at_utc=datetime.now(timezone.utc).isoformat(),
    source_hashes=start_hashes,material_corrections=[],resolved_clarifications=[
      dict(path='manuscript/public_memory.tex',line=37,issue='Default-empty native Summary and Recently Extracted Memories are now stated.',status='RESOLVED')],
    author_identity_handling='User explicitly requested named author/background; this overrides the anonymity template. Public references and independent synthetic study materials only.',
    anti_leakage='PaperOrchestra anti-leakage constraint applied to claim review; no company implementation, private conversations or old campaign numbers used.',
    checks=checks,citation_gate=dict(entries=54,cited=54,undefined=[],uncited=[],new_primary_metadata_matches=metadata_checks),
    official_docs_fresh_check=official_docs,
    remaining_limits=['Post hoc retrieval self-queries and selected fresh-history stores do not establish held-out natural-workload generalization or semantic/QA harm.',
      'The counting bound is elementary; broader bounded-candidate dependence, stable identity, receipts, decision logs, fences and lifecycle correctness have close prior art.',
      'One requested model/harness and finite authored batches provide witnesses, not model error rates or independently attested backend model weights.',
      'Native baselines and backend profiles are scoped authored integrations, not framework optimality or vendor ranking.',
      'Same-author checkers and computational reproductions do not replace outside replication; server power loss, remote late commits, cluster consistency and scalable concurrent uniqueness remain untested.',
      'A leading-journal contribution is not established by this review or by counts. No acceptance score or publication guarantee is provided.'],
    review_scope='Scientific/source evidence review, not a rerun of experiments or a PDF layout review. Only review-owned files written.',
    evidence_manifest=[record(ROOT/p) for p in evidence_paths])
(OUT/'final_scientific_review.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
lines=['PASS_FOR_BOUNDED_WORKING_CLAIMS','',
    'No material correction is required in the reviewed final source snapshot. The default-empty native prompt-field clarification has been incorporated. This conclusion concerns bounded working claims, not journal readiness.',
    '', 'Reviewed source SHA-256:']
lines.extend(f'- {p}: {h}' for p,h in start_hashes.items())
lines+=['','Findings:']
for c in checks:lines+=[f"- {c['topic']} ({'; '.join(c['lines'])}): {c['finding']}"]
lines+=['','Remaining novelty and external-validity limits:']
lines.extend('- '+x for x in report['remaining_limits'])
lines+=['','Verification scope:',
    'The reviewer independently recomputed new arithmetic/coverage from archived rows and checked the supplied raw-store/provenance audit records. The three backend documentation pages were freshly opened/read and hashed; they support non-interleaving, runtime-error/rollback distinctions and explicit application rollback. Existing scholarly audits provide primary PDF/HTML/DataCite identities; old citations were not all freshly researched. No new experiment, model request, manuscript edit, acceptance score or expanded search was performed.']
(OUT/'final_scientific_review.txt').write_text('\n'.join(lines)+'\n')
print(json.dumps(dict(status=report['status'],material_corrections=0,cited_entries=54,reviewed_source_hashes=start_hashes),indent=2))
