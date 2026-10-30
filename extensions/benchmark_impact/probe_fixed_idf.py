"""Declared post-hoc fixed-corpus IDF counterfactual, on store copies only.

Uses Qdrant's native IdfCorpusParams API to compute keyword IDF from the
original clean physical IDs, while duplicate points remain searchable.
The clean ID set is diagnostic information, not a deployable/oracle-free policy.
"""
from pathlib import Path
import argparse,hashlib,json,os,shutil,sqlite3,tempfile,types
import memory_worker as worker
import pipeline

def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):pipeline.write(p,x)

def run(pilot,probe,out):
 pipeline.verify(pilot);pipeline.verify_native(pilot);out.mkdir(parents=True,exist_ok=False)
 for key in list(os.environ):
  if key.endswith('_API_KEY') or key in ('HF_TOKEN','HUGGING_FACE_HUB_TOKEN'):os.environ.pop(key)
 os.environ.update(HF_HUB_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',MEM0_TELEMETRY='false',FASTEMBED_CACHE_PATH='/tmp/beyond-recall-bge-model',OMP_NUM_THREADS='2')
 from qdrant_client.http import models
 import mem0.vector_stores.qdrant,qdrant_client.local.local_collection
 protocol={'phase':'Post-hoc diagnostic counterfactual after full-pool ranking probe; not new task samples or held-out confirmation.',
  'runner_sha256':sha(Path(__file__)),'worker_sha256':sha(Path(worker.__file__)),'pilot_protocol_sha256':sha(pilot/'protocol.json'),
  'parent_probe_protocol_sha256':sha(probe/'protocol.json'),'parent_report_sha256':sha(probe/'report.json'),
  'native_qdrant_adapter_sha256':sha(Path(mem0.vector_stores.qdrant.__file__)),'native_idf_implementation_sha256':sha(Path(qdrant_client.local.local_collection.__file__)),
  'selection':'All24pilot questions/14scopes, full native top_k10000. No questions selected by score/answer outcome.',
  'intervention':'Replayed store copies retain every duplicate point; only sparse query search_params.idf is scoped via native IdfCorpusParams to original clean physical IDs. Dense search, query, embeddings, point payloads, semantic threshold and native additive scoring unchanged.',
  'oracle_limit':'Uses the known clean physical-ID corpus as a mechanism diagnostic. Not claimed as a deployable remedy or a new IDF algorithm.',
  'expected_falsifier':'If corpus statistics explain the residual full-pool scoring drift, original-point BM25/final components should return to clean values. Report any remaining context or tie-order differences without suppressing them.'}
 write(out/'protocol.json',protocol);(out/'protocol.sha256').write_text(sha(out/'protocol.json')+'\n');reports=[]
 for episode in sorted((pilot/'participants').glob('*.json')):
  scope=episode.stem;queries=load(pilot/'queries'/episode.name);original_ids=sorted(r['physical_id'] for r in load(pilot/'stores/mem0_raw'/scope/'clean/initial_snapshot.json'))
  baseline={r['invocation']:r['rows'] for r in load(probe/'queries'/f'{scope}-clean.json') if r['requested_top_k']==10000}
  with tempfile.TemporaryDirectory(prefix='independent-fixed-idf-') as temporary:
   temp=Path(temporary);folder=temp/'replayed';shutil.copytree(pilot/'stores/mem0_raw'/scope/'native_retry',folder)
   source=sqlite3.connect((pilot/'embedding_caches/mem0_raw'/(scope+'.sqlite')).resolve().as_uri()+'?mode=ro',uri=True);target=sqlite3.connect(temp/'cache.sqlite')
   try:source.backup(target)
   finally:source.close();target.close()
   participant=worker.Mem0Participant(folder,temp/'cache.sqlite',pilot/'embedding_manifest.json')
   corpus=models.Filter(must=[models.HasIdCondition(has_id=original_ids)])
   def fixed_keyword(store,query,top_k=5,filters=None):
    if not store._has_bm25_slot:raise ValueError('Expected native BM25 sparse slot')
    encoded=store._encode_bm25(query)
    if encoded is None:raise ValueError('Expected native sparse query')
    return store.client.query_points(collection_name=store.collection_name,query=encoded,using='bm25',query_filter=store._create_filter(filters) if filters else None,limit=top_k,search_params=models.SearchParams(idf=models.IdfCorpusParams(corpus=corpus))).points
   participant.memory.vector_store.keyword_search=types.MethodType(fixed_keyword,participant.memory.vector_store)
   try:
    before=participant.cache.conn.execute('SELECT COUNT(*) FROM embeddings').fetchone()[0];native=[]
    for query in queries:
     rows=participant.memory.search(query['question'],filters={'user_id':worker.USER},top_k=10000,threshold=0,show_expired=False,explain=True)['results'];native.append({'invocation':query['invocation'],'rows':rows})
     a={r['id']:r for r in baseline[query['invocation']]};b={r['id']:r for r in rows};assert set(a)<=set(b)
     changes={f:sum(abs(a[i]['score_details'][f]-b[i]['score_details'][f])>1e-12 for i in a) for f in ('semantic_score','bm25_score','entity_boost','max_possible_score','final_score')}
     context=lambda items:pipeline.select_context([participant.convert(r) for r in items],True)
     ca=context(list(a.values()));cb=context(rows);ia=[r['event_id'] for r in ca];ib=[r['event_id'] for r in cb]
     reports.append({'question_key':query['invocation'],'scope':scope,'original_points_compared':len(a),'component_changes_at_1e12':changes,'same_selected_event_order':ia==ib,'same_selected_event_set':set(ia)==set(ib),'clean_context':ca,'fixed_idf_context':cb})
    assert before==participant.cache.conn.execute('SELECT COUNT(*) FROM embeddings').fetchone()[0]
    write(out/'queries'/f'{scope}.json',native)
   finally:participant.close()
  print(json.dumps({'fixed_idf_scope_finished':scope}),flush=True)
 report={'phase':protocol['phase'],'protocol_sha256':sha(out/'protocol.json'),'native_search_calls':len(reports),'questions':len(reports),'different_event_sets':sum(not r['same_selected_event_set'] for r in reports),'different_event_orders':sum(not r['same_selected_event_order'] for r in reports),'questions_with_component_changes':{f:sum(r['component_changes_at_1e12'][f]>0 for r in reports) for f in reports[0]['component_changes_at_1e12']},'cases':reports}
 write(out/'report.json',report);print(json.dumps({k:v for k,v in report.items() if k!='cases'},indent=2))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--pilot',type=Path,required=True);p.add_argument('--parent-probe',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();run(a.pilot.resolve(),a.parent_probe.resolve(),a.out.resolve())
