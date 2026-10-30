"""Post-hoc native ranking diagnostic on copies, not new benchmark samples.

The pilot found that visible-event dedup restored dense LlamaIndex contexts,
while some Mem0 hybrid contexts still differed. Inspect full-pool native score
components to distinguish candidate truncation from corpus-dependent scoring.
No original store, frozen source, model output or reference label is changed.
"""
from pathlib import Path
import hashlib,json,shutil,sqlite3,tempfile,time,argparse,os
import memory_worker as worker
import pipeline

def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):pipeline.write(p,x)

def run(pilot,out):
 pipeline.verify(pilot);pipeline.verify_native(pilot);out.mkdir(parents=True,exist_ok=False)
 for key in list(os.environ):
  if key.endswith('_API_KEY') or key in ('HF_TOKEN','HUGGING_FACE_HUB_TOKEN'):os.environ.pop(key)
 os.environ.update(HF_HUB_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',MEM0_TELEMETRY='false',FASTEMBED_CACHE_PATH='/tmp/beyond-recall-bge-model',OMP_NUM_THREADS='2')
 import mem0.memory.main,mem0.utils.scoring,mem0.vector_stores.qdrant
 import qdrant_client.local.local_collection
 sources=[Path(__file__),Path(worker.__file__),Path(mem0.memory.main.__file__),Path(mem0.utils.scoring.__file__),Path(mem0.vector_stores.qdrant.__file__),Path(qdrant_client.local.local_collection.__file__)]
 protocol={'phase':'Post-hoc mechanistic diagnostic after seeing pilot context-set differences, before interpreting task grades; not held-out confirmation.',
  'pilot_protocol_sha256':sha(pilot/'protocol.json'),'pilot_contexts_sha256':sha(pilot/'contexts.json'),
  'source_hashes':{p.name:sha(p) for p in sources},
  'selection':'All24pilot questions/14scopes, Mem0 raw participant only. LlamaIndex visible-event dedup comparison uses retained pilot contexts.',
  'interventions':'Copies of existing clean and native_retry stores; native explain=True queries at top_k60 and10000. Full pool removes finite semantic/keyword candidate truncation. No model extraction, original-store mutations or new task samples.',
  'attribution':'Report score-component changes and contextual differences separately. Do not assume a fusion algorithm or attribute all ranking changes to IDF without matching component evidence.',
  'claim_limit':'This diagnostic does not establish reader harm, novelty, production incidence or vendor-cloud behavior.'}
 write(out/'protocol.json',protocol);(out/'protocol.sha256').write_text(sha(out/'protocol.json')+'\n')
 reports=[]
 for ep in sorted((pilot/'participants').glob('*.json')):
  scope=ep.stem;queries=load(pilot/'queries'/ep.name);results={}
  with tempfile.TemporaryDirectory(prefix='independent-ranking-probe-') as temporary:
   temp=Path(temporary)
   for state in ('clean','native_retry'):
    folder=temp/state;shutil.copytree(pilot/'stores/mem0_raw'/scope/state,folder)
    source=sqlite3.connect((pilot/'embedding_caches/mem0_raw'/(scope+'.sqlite')).resolve().as_uri()+'?mode=ro',uri=True);target=sqlite3.connect(temp/(state+'-cache.sqlite'))
    try:source.backup(target)
    finally:source.close();target.close()
    participant=worker.Mem0Participant(folder,temp/(state+'-cache.sqlite'),pilot/'embedding_manifest.json')
    try:
     before=participant.cache.conn.execute('SELECT COUNT(*) FROM embeddings').fetchone()[0];state_results=[]
     for query in queries:
      for limit in (60,10000):
       started=time.monotonic();rows=participant.memory.search(query['question'],filters={'user_id':worker.USER},top_k=limit,threshold=0,show_expired=False,explain=True)['results']
       state_results.append({'invocation':query['invocation'],'requested_top_k':limit,'wall_seconds':time.monotonic()-started,'rows':rows})
     after=participant.cache.conn.execute('SELECT COUNT(*) FROM embeddings').fetchone()[0]
     if before!=after:raise ValueError('Unexpected dense-query cache miss; retain diagnostics before interpretation')
     write(out/'queries'/f'{scope}-{state}.json',state_results);results[state]=state_results
    finally:participant.close()
  for query in queries:
   detail={}
   for limit in (60,10000):
    a=next(r['rows'] for r in results['clean'] if r['invocation']==query['invocation'] and r['requested_top_k']==limit)
    b=next(r['rows'] for r in results['native_retry'] if r['invocation']==query['invocation'] and r['requested_top_k']==limit)
    original={r['id']:r for r in a};replayed={r['id']:r for r in b};common=set(original)&set(replayed)
    shifts={field:sum(abs(original[i]['score_details'][field]-replayed[i]['score_details'][field])>1e-12 for i in common) for field in ('semantic_score','bm25_score','entity_boost','max_possible_score','final_score')}
    def context(rows):return pipeline.select_context([participant.convert(r) for r in rows],True)
    ca=context(a);cb=context(b);ia=[r['event_id'] for r in ca];ib=[r['event_id'] for r in cb]
    detail[str(limit)]={'common_original_point_scores':len(common),'component_changes_at_1e12':shifts,'same_selected_event_order':ia==ib,'same_selected_event_set':set(ia)==set(ib),'clean_context':ca,'retry_context':cb}
   reports.append({'scope':scope,'question_key':query['invocation'],'diagnostic':detail})
  print(json.dumps({'ranking_probe_scope_finished':scope}),flush=True)
 write(out/'report.json',{'phase':protocol['phase'],'protocol_sha256':sha(out/'protocol.json'),'native_search_calls':sum(len(load(p)) for p in (out/'queries').glob('*.json')),'questions':len(reports),'cases':reports})

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--pilot',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();run(a.pilot.resolve(),a.out.resolve())
