"""Build a bounded source/claim audit without task answers, grades or model calls."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, re

HERE=Path(__file__).resolve().parent
LITERATURE=HERE.parent
STUDY=LITERATURE.parent
ROOT=STUDY.parents[1]
CACHE=Path('/tmp/beyond-recall-benchmark-impact-literature-20261029')
SITE=ROOT/'.venv-memory/lib/python3.14/site-packages'

def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,obj): (HERE/name).write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n')
def norm(s):return re.sub(r'[^a-z0-9]','',s.lower())

r=load(STUDY/'posthoc_ranking_probe_v1/report.json')
f=load(STUDY/'posthoc_fixed_idf_v1/report.json')
recomputed={}
for pool in ['60','10000']:
    ds=[row['diagnostic'][pool] for row in r['cases']]
    recomputed[pool]={
      'questions':len(ds),
      'different_selected_event_sets':sum(not row['same_selected_event_set'] for row in ds),
      'different_selected_event_orders':sum(not row['same_selected_event_order'] for row in ds),
      'questions_with_component_changes':{k:sum(row['component_changes_at_1e12'][k]>0 for row in ds) for k in ds[0]['component_changes_at_1e12']},
      'summed_common_original_point_comparisons':sum(row['common_original_point_scores'] for row in ds)}
fixed={
 'questions':len(f['cases']),
 'different_event_sets':sum(not row['same_selected_event_set'] for row in f['cases']),
 'different_event_orders':sum(not row['same_selected_event_order'] for row in f['cases']),
 'questions_with_component_changes':{k:sum(row['component_changes_at_1e12'][k]>0 for row in f['cases']) for k in f['cases'][0]['component_changes_at_1e12']},
 'summed_original_point_comparisons':sum(row['original_points_compared'] for row in f['cases'])}
assert len(r['cases'])==len(f['cases'])==24
assert len({row['scope'] for row in r['cases']})==14
assert {(row['scope'],row['question_key']) for row in r['cases']}=={(row['scope'],row['question_key']) for row in f['cases']}
assert fixed['different_event_sets']==f['different_event_sets']
assert fixed['different_event_orders']==f['different_event_orders']
assert fixed['questions_with_component_changes']==f['questions_with_component_changes']
write('reported_counter_recheck.json',{
 'prepared_utc':datetime.now(timezone.utc).isoformat(),
 'scope':'Recompute supplied case counters only. This does not substitute for the independent raw-store/vector/trace audit.',
 'reader_answers_or_grades_read':False,'model_calls':0,
 'ranking_probe':recomputed,'fixed_idf':fixed,
 'denominators':'24 pilot questions in 14 scopes; repeated original-point/query comparisons are not distinct documents or independent task samples.',
 'independent_evidence_audit_status_at_review':'Reported by parent as in progress; not asserted passed here.'})

fetch=load(HERE/'fetch_manifest.json')
idx=load(HERE/'index_fetch_manifest.json')
new=[
 {'key':'frieder2003scalable','title':'On Scalable Information Retrieval Systems',
  'authors':['Ophir Frieder','David Grossman','Abdur Chowdhury'],'year':2003,
  'doi':'10.1109/NCA.2003.1201162','url':'https://ir.cs.georgetown.edu/publications/downloads/NCA03-Keynote.pdf',
  'source_prefix':'frieder2003','pdf_pages':5,'locations':['§2, PDF pp.1–2'],
  'summary':'Maintaining duplicate documents changes collection term frequencies and IDF, distorting retrieval relevance; this is an explicit antecedent to the proposed mechanism.',
  'scope_limit':'No LLM-memory runtime, delivery-failure injection, or native fixed-IDF recovery diagnostic is presented.',
  'metadata_resolution':'Crossref page range 241–245 and three-author order match the primary five-page paper. Do not confuse the distinct single-author CIKM 2002 same-title abstract.'},
 {'key':'robertson2009probabilistic','title':'The Probabilistic Relevance Framework: BM25 and Beyond',
  'authors':['Stephen Robertson','Hugo Zaragoza'],'year':2009,'doi':'10.1561/1500000019',
  'url':'https://www.ccs.neu.edu/home/vip/teach/IRcourse/IR_surveys/robertson_foundations.pdf',
  'source_prefix':'robertson2009','pdf_pages':59,'locations':['§3.1, equation (3.3), printed pp.348–349','§3.4'],
  'summary':'The probabilistic retrieval account makes collection size and document frequency explicit inputs to IDF/BM25. Fixed document content therefore does not imply fixed lexical scores after collection changes.',
  'scope_limit':'Use as mathematical foundation, not a new empirical retry benchmark or proof that all duplication worsens QA.',
  'metadata_resolution':'Primary PDF prints volume 3, number 4, pages 333–389. Current Crossref and OpenAlex instead attach volume 4, issues 1–2, pages 1–174 to the matching title/DOI. Preserve this conflict; bibliography fields below follow the printed primary work.'},
 {'key':'schelpe2026byte','title':'Byte-Exact Deduplication in Retrieval-Augmented Generation: A Three-Regime Empirical Analysis Across Public Benchmarks',
  'authors':['Sietse Schelpe'],'year':2026,'doi':'10.48550/arXiv.2605.09611',
  'url':'https://arxiv.org/abs/2605.09611v1','source_prefix':'2605_09611','pdf_pages':26,
  'locations':['§§2.5, 3.1–3.3','§4.5b','§§5.1,5.6'],
  'summary':'Defines byte-exact filtering over retrieved chunks. It acknowledges indexed duplicates and describes a triple-indexed synthetic corpus (§5.1); its scaling condition also triples a saturated retrieved set (§3.3).',
  'scope_limit':'No traced ordinary-delivery-failure→physical-corpus→original-record-IDF chain or clean-IDF counterfactual was located in the inspected body. Its output-quality claims concern its own regimes; filtering a retrieved multiset is not rebuilding the canonical retrieval corpus.',
  'metadata_resolution':'Version-1 landing/PDF and DataCite agree on title, sole author and May 10, 2026 submission; no peer-reviewed venue is asserted.'}]
for x in new:
 prefix=x['source_prefix']
 pdf=next(t for t in fetch['records'] if t['key']==prefix+'_pdf')
 x['pdf_sha256']=pdf['sha256'];x['third_party_full_text_redistributed']=False
 oa=load(CACHE/(x['key']+'_openalex.json'))
 x['openalex']={'id':oa['id'],'title':oa['title'],'doi':oa['doi'],
   'exact_normalized_title_match':norm(oa['title'])==norm(x['title']),
   'year_match':oa['publication_year']==x['year']}
 assert x['openalex']['exact_normalized_title_match'] and x['openalex']['year_match']
 s2=next(t for t in idx['records'] if t['key']==x['key']+'_s2')
 x['semantic_scholar']={'verified':False,'status':s2['status'],'error':s2.get('error'),
 'note':'Public title request returned HTTP429; no fabricated S2 identifier or abstract is supplied.'}
 x['abstract']=None
 x['verification_status']='Primary full text and DOI identity checked; exact-title OpenAlex corroboration. S2 unavailable. Bibliographic-field conflict explicitly retained where present.'
write('new_source_metadata.json',{'prepared_utc':datetime.now(timezone.utc).isoformat(),
 'source_cutoff':'2026-10-29 inclusive for cited prior work; this focused diagnostic audit was prepared October 30 UTC.',
 'source_body_cache':'external only; filenames and hashes in fetch_manifest.json',
 'exhaustive_coverage_claimed':False,'papers':new})

old=load(LITERATURE/'source_claim_map.json')['papers']
selected=['jain2026cuer','brouillette2026balance','ross2026redundancy','ke2024bridging']
comparators=[]
newmaps={
 'jain2026cuer':('§§4.6,5.4–5.5,7','Evidence DUPLICATE is applied after a BM25 top-five retrieval. This is direct prior art for duplicate-evidence interventions, not an upstream corpus-statistics experiment.','No native recovery/corpus mutation or IDF restoration diagnostic described.'),
 'brouillette2026balance':('§§3.1–3.3,5–6','RNG-Score studies diversification on fixed embedded candidate pools. Its strict closer-neighbor condition deliberately leaves exactly coincident copies unsuppressed.','No novelty claim for redundancy/diversity tradeoffs; do not score this near-copy method as a failed exact-copy filter.'),
 'ross2026redundancy':('§§3.1–3.4,4.1','Constructed reader contexts compare exact repeats, paraphrases and diverse-genre evidence. This directly precedes broad claims about redundant context effects.','Context construction is distinct from native failed-delivery admission and dynamic lexical statistics.'),
 'ke2024bridging':('§§3–4,5.3','The learned bridge jointly selects/orders passages and permits repeated IDs. Repetition is not uniformly undesirable.','No isolated repetition-only causal result; no physical retry/IDF intervention.')}
for key in selected:
 x=next(x for x in old if x['key']==key);loc,summary,limit=newmaps[key]
 comparators.append({'key':key,'title':x['title'],'url':x['url'],'pdf_sha256':x['pdf_sha256'],
 'locations':loc,'summary':summary,'scope_limit':limit,'verification_provenance':'Existing full-text audit and metadata in ../source_claim_map.json; body spot-checked again for this question.'})
write('overlap_matrix.json',{'scope':'Focused closest-source audit, not proof of global absence.',
 'new_primary_sources':[{'key':x['key'],'details':'new_source_metadata.json'} for x in new],'existing_close_comparators':comparators,
 'industry_implementation':{'url':'https://qdrant.tech/documentation/manage-data/indexing/#idf-modifier',
 'body_sha256':next(x['sha256'] for x in fetch['records'] if x['key']=='qdrant_indexing_docs'),
 'location':'IDF Modifier','summary':'Official documentation explicitly treats IDF as a function of currently stored documents; current defaults are shard-wide, with optional corpus scoping. The local runtime examined here counts live physical sparse-vector points.',
 'scope_limit':'Docs explain intended scoring, not a vendor exactly-once promise. Local and server deletion/index-maintenance semantics differ; do not extrapolate this local probe to cloud behavior.'}})

claims=[
 {'id':'C1','status':'ESTABLISHED_PRIOR_ART','claim':'Duplicates can change IDF and scores of unchanged documents.','basis':['frieder2003scalable §2','robertson2009probabilistic §3.1','Qdrant IDF docs/runtime'],'forbidden_upgrade':'New IR mechanism, first discovery, or unexpected mathematical principle.'},
 {'id':'C2','status':'BOUNDED_EMPIRICAL_WITNESS_PENDING_RAW_AUDIT','claim':'In this pinned Mem0 raw/Qdrant-local pilot, ordinary post-commit redelivery admits extra physical records; all 24 queries have some original-record BM25/final changes while compared semantic/entity components stay fixed.','basis':['posthoc_ranking_probe_v1/report.json; counters independently re-added here'],'forbidden_upgrade':'All records changed, semantic corruption, or production incidence.'},
 {'id':'C3','status':'BOUNDED_EMPIRICAL_WITNESS_PENDING_RAW_AUDIT','claim':'At nonbinding full retrieval depth, later source-event dedup still yields different sets in 10/24 questions and different orders in 17/24 under the study packing rule.','basis':['posthoc_ranking_probe_v1/report.json'],'forbidden_upgrade':'10/24 QA failures, missing relevant facts, universal inadequacy of all read-time dedup or 24 independent domains.'},
 {'id':'C4','status':'CAUSAL_MECHANISM_DIAGNOSTIC_PENDING_RAW_AUDIT','claim':'Keeping duplicate points searchable while restricting native IDF statistics to known clean physical IDs restores all compared original BM25/final components within 1e-12 and all 24 clean event orders/sets.','basis':['posthoc_fixed_idf_v1/protocol.json','posthoc_fixed_idf_v1/report.json','probe_fixed_idf.py'],'forbidden_upgrade':'Deployable oracle-free remedy, new IDF algorithm, preregistered held-out confirmation, or new task samples.'},
 {'id':'C5','status':'REFERENCE_CONTRAST_ONLY','claim':'Dense-only LlamaIndex read-event dedup reportedly restores 24/24 retained pilot contexts.','basis':['Parent-reported retained pilot comparison; not independently recomputed in this literature audit.'],'forbidden_upgrade':'Dense retrieval is always retry-invariant, dense is superior, or this cross-engine comparison alone isolates IDF.'},
 {'id':'C6','status':'IMPLEMENTATION_VERIFIED','claim':'This native Mem0 path uses fixed query-length sigmoid BM25 normalization and additive semantic/BM25/entity scoring, with a semantic gate.','basis':['mem0/utils/scoring.py','mem0/memory/main.py _search_vector_store'],'forbidden_upgrade':'RRF, min/max-normalized fusion, or a guarantee shared by every Mem0 release/configuration.'},
 {'id':'C7','status':'UNSUPPORTED','claim':'The changed contexts harm or help answer correctness, safety, user outcomes, tokens or latency.','basis':['No reader grades or performance outcomes inspected.'],'forbidden_upgrade':'Infer value/harm from context-set difference or literal diversity alone.'},
 {'id':'C8','status':'UNSUPPORTED','claim':'No prior work has connected duplicate ingestion, retrieval or RAG quality; this is publication-ready by novelty/count alone.','basis':['Direct classical IDF antecedent plus close RAG studies; targeted search is not exhaustive.'],'forbidden_upgrade':'First/breakthrough/new algorithm/acceptance forecast.'},
 {'id':'C9','status':'KNOWN_SYSTEMS_DESIGN_PRINCIPLE','claim':'Preventing repeated delivery admission requires an operation/event identity contract with explicit retention/lifetime semantics; exact-content filtering conflates legitimate same-content events.','basis':['Existing RFC9110, agentmemory, PLUR and durable-execution literature audit.'],'forbidden_upgrade':'New idempotency protocol or treat all same-text observations as one event.'}]
write('claim_ledger.json',{'claims':claims,
 'conditional_math':{'source':'Qdrant local _compute_idf; algebraic rearrangement, not a new theorem.',
 'idf':'I(N,d)=ln((N-d+0.5)/(d+0.5)+1)=ln((N+1)/(d+0.5))',
 'duplicate_increment':'I(N+m,d+a)-I(N,d)=ln((N+m+1)/(N+1))-ln((d+a+0.5)/(d+0.5)), where m extra physical sparse-vector documents are admitted and a of them contain the query term (0<=a<=m).',
 'implication':'Different term frequencies can change relative lexical contributions without changing original vectors. Score/rank changes are conditional; duplication need not change a given order, and either QA direction or no effect is possible.',
 'composition':'Collapsing source-event copies after native scoring changes the returned multiset but does not retroactively recompute the IDF statistics used to rank originals. This noncommutation is established reasoning, not a new recovery algorithm.'},
 'remaining_limits':['Same 24 pilot questions in 14 scopes; post-hoc diagnostics and counterfactuals reuse them.','Known clean physical IDs are an oracle for the counterfactual.','Physical duplicate IDs are distinguished from legitimate fresh observations with identical bytes.','Ranking and context changes alone do not measure evidence usefulness, reader outcomes or independent corroboration.','Full-pool evidence must be checked against actual stored/candidate counts by the independent raw auditor.','Pinned Mem0 2.2.1 installed from the public source cache; qdrant-client1.20.0/fastembed0.9.1 local runtime. Do not generalize to all versions or cloud services.']})

files=[STUDY/'probe_ranking.py',STUDY/'probe_fixed_idf.py',STUDY/'memory_worker.py',STUDY/'pipeline.py',
 *[STUDY/'posthoc_ranking_probe_v1'/x for x in ['protocol.json','protocol.sha256','report.json','summary.json']],
 *[STUDY/'posthoc_fixed_idf_v1'/x for x in ['protocol.json','protocol.sha256','report.json']],
 SITE/'mem0/memory/main.py',SITE/'mem0/utils/scoring.py',SITE/'mem0/vector_stores/qdrant.py',SITE/'qdrant_client/local/local_collection.py',
 LITERATURE/'source_claim_map.json',LITERATURE/'cue_r_protocol_audit.json']
write('source_hashes.json',{'prepared_utc':datetime.now(timezone.utc).isoformat(),
 'source_files':[{'path':str(p.relative_to(ROOT)),'sha256':sha(p)} for p in files],
 'public_third_party_bodies':[{'key':r['key'],'url':r['url'],'sha256':r['sha256'],'full_text_in_checkout':False,'external_cache_filename':r['cache_filename']} for r in fetch['records'] if r.get('sha256')],
 'audit_read_boundary':'Protocols, native source, score/context report fields and public literature only; no generated reader-answer or grade files read.',
 'no_manuscript_edits':True,'model_calls_by_this_agent':0})

(HERE/'additions.bib').write_text('''% Proposed additions only. No main bibliography is edited.
% Robertson bibliographic-field conflict is recorded in new_source_metadata.json.
@inproceedings{frieder2003scalable,
  author = {Frieder, Ophir and Grossman, David and Chowdhury, Abdur},
  title = {On Scalable Information Retrieval Systems},
  booktitle = {Second IEEE International Symposium on Network Computing and Applications},
  pages = {241--245},
  year = {2003},
  doi = {10.1109/NCA.2003.1201162},
  url = {https://ir.cs.georgetown.edu/publications/downloads/NCA03-Keynote.pdf}
}
@article{robertson2009probabilistic,
  author = {Robertson, Stephen and Zaragoza, Hugo},
  title = {The Probabilistic Relevance Framework: {BM25} and Beyond},
  journal = {Foundations and Trends in Information Retrieval},
  volume = {3},
  number = {4},
  pages = {333--389},
  year = {2009},
  doi = {10.1561/1500000019},
  url = {https://www.ccs.neu.edu/home/vip/teach/IRcourse/IR_surveys/robertson_foundations.pdf}
}
@misc{schelpe2026byte,
  author = {Schelpe, Sietse},
  title = {Byte-Exact Deduplication in Retrieval-Augmented Generation: A Three-Regime Empirical Analysis Across Public Benchmarks},
  year = {2026},
  eprint = {2605.09611},
  archivePrefix = {arXiv},
  primaryClass = {cs.CL},
  doi = {10.48550/arXiv.2605.09611},
  url = {https://arxiv.org/abs/2605.09611v1},
  note = {Version 1, preprint}
}
''')
print(json.dumps({'status':'BUILT_BOUNDED_NOVELTY_AUDIT','new_sources':len(new),'existing_close_comparators':len(comparators),'full_pool_sets_different':recomputed['10000']['different_selected_event_sets'],'fixed_idf_sets_different':fixed['different_event_sets'],'reader_grades_read':False,'model_calls':0}))
