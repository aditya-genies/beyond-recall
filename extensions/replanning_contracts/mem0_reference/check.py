#!/usr/bin/env python3
"""Read-only raw-store checker; imports no experiment or Mem0 metric functions."""
from __future__ import annotations
import argparse,ast,base64,collections,hashlib,importlib.metadata,io,json,math,pickle,sqlite3
from pathlib import Path

HERE=Path(__file__).resolve().parent
SIZES=(1,5,10,11,13,20,21,40)
EMBEDDERS=('hash_control','bge_small')
EXTRACTORS=('literal_reemit','visible_delta')
ARMS=('native_k10','widened_candidates','exact_admission')
NATIVE_MAIN_SHA='f329ca4a17af1fbefb32ac10d4cc7ae7ddbdb7435a87eb74c30915cff98b8b7c'
SOURCE_COMMIT='26cdefb46600c0fa5953c4b5ee5003c125539fc4'
PERSISTENCE_SHA='75febeac43d74f4ca706290a85b6a15f4d5ac3ecb0dfe96153614796c5e9478f'

class VerificationError(ValueError):pass
def require(condition,message):
    if not condition:raise VerificationError(message)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def md5(text):return hashlib.md5(text.encode()).hexdigest()
def load(path):return json.loads(Path(path).read_text())

class PointDecoder(pickle.Unpickler):
    """Only the two public data classes used by these local Qdrant points."""
    def find_class(self,module,name):
        if module=='qdrant_client.http.models.models' and name in {'PointStruct','SparseVector'}:
            from qdrant_client.http.models import models
            return getattr(models,name)
        raise VerificationError(f'Unexpected pickle class: {module}.{name}')

def decode(data):return PointDecoder(io.BytesIO(data)).load()

def sql_rows(path,query):
    connection=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True)
    connection.row_factory=sqlite3.Row
    try:
        require(connection.execute('PRAGMA integrity_check').fetchone()[0]=='ok','SQLite integrity failure')
        return [dict(r) for r in connection.execute(query)]
    finally:connection.close()

def raw_records(folder,embedder):
    path=folder/'qdrant/collection/study_memories/storage.sqlite'
    rows=sql_rows(path,'SELECT id,point FROM points ORDER BY rowid')
    points={}
    for row in rows:
        key=decode(base64.b64decode(row['id']))
        point=decode(row['point'])
        require(isinstance(key,str) and key==point.id,'Qdrant key/point identity mismatch')
        require(base64.b64encode(pickle.dumps(key,protocol=4)).decode()==row['id'],'Unexpected Qdrant key encoding')
        require(key not in points,'Duplicate physical point identity')
        payload=point.payload
        require(payload['user_id']=='synthetic-study-user','Wrong raw user scope')
        require(payload['hash']==md5(payload['data']),'Raw payload MD5 mismatch')
        vector=point.vector.get('') if isinstance(point.vector,dict) else point.vector
        dimension=32 if embedder=='hash_control' else 384
        require(isinstance(vector,list) and len(vector)==dimension,'Wrong physical dense-vector dimension')
        require(all(isinstance(x,(int,float)) and math.isfinite(x) for x in vector),'Nonfinite physical vector')
        if embedder=='hash_control':
            authored=[(b-127.5)/127.5 for b in hashlib.sha256(payload['data'].encode()).digest()]
            norm=math.sqrt(sum(x*x for x in authored))
            require(all(abs(a/norm-b)<1e-6 for a,b in zip(authored,vector)),'Hash-control physical vector mismatch')
        points[key]=payload
    return points

def check_case(row,folder,facts):
    """Validate one add-only execution against raw SQLite and complete traces."""
    n=row['n'];expected=facts[:n];expected_set=set(expected)
    require(len(expected_set)==n,'Nonunique exact fixture facts')
    physical=raw_records(folder,row['embedder'])
    history=sql_rows(folder/'history.sqlite','SELECT rowid AS ordinal,* FROM history ORDER BY rowid')
    require(len(history)==len(physical),'Physical point/history count mismatch')
    history_ids=[h['memory_id'] for h in history]
    require(len(set(history_ids))==len(history_ids) and set(history_ids)==set(physical),'Physical point/history IDs mismatch')
    for h in history:
        require(h['event']=='ADD' and h['old_memory'] is None and h['is_deleted']==0,'History is not add-only')
        p=physical[h['memory_id']]
        require(h['new_memory']==p['data'] and h['created_at']==p['created_at'],'History/payload content mismatch')
    attempts=row['attempts'];require(len(attempts)==3,'Expected initial add and two redeliveries')
    before={};observations=[];history_cursor=0
    for ordinal,attempt in enumerate(attempts):
        require(attempt['attempt']==ordinal,'Attempt order mismatch')
        require(attempt['extraction_calls_this_attempt']==1 and attempt['search_calls_this_attempt']==1,'Call/search alignment mismatch')
        records=attempt['records'];ids=[r['id'] for r in records]
        require(len(set(ids))==len(ids),'Duplicate snapshot IDs')
        require(set(ids)<=set(physical),'Snapshot contains absent physical point')
        for rec in records:
            p=physical[rec['id']]
            for key,payload_key in [('memory','data'),('hash','hash'),('created_at','created_at'),('updated_at','updated_at'),('user_id','user_id'),('attributed_to','attributed_to')]:
                require(rec.get(key)==p.get(payload_key),f'Snapshot/payload {key} mismatch')
        current={r['id']:r for r in records};text_set={r['memory'] for r in records}
        require(set(before)<=set(current),'Add-only snapshot lost IDs')
        require(attempt['physical_records']==len(records),'physical_records metric mismatch')
        require(attempt['distinct_facts']==len(text_set),'distinct_facts metric mismatch')
        require(attempt['extra_copies']==len(records)-len(text_set),'extra_copies metric mismatch')
        require(attempt['fact_set_matches']==(text_set==expected_set),'fact_set_matches metric mismatch')
        require(text_set==expected_set,'Unexpected exact fact set')
        search=attempt['search'];candidates=search['returned']
        require(search['requested_top_k']==10,'Native requested top-k changed')
        k=10000 if row['arm']=='widened_candidates' else 10
        require(search['effective_top_k']==k,'Intervention top-k mismatch')
        require(search['filters']=={'user_id':'synthetic-study-user'},'Write search filter mismatch')
        require(len(candidates)==min(k,len(before)),'Candidate count mismatch')
        require(len({c['id'] for c in candidates})==len(candidates),'Duplicate candidate IDs')
        for c in candidates:
            require(c['id'] in before,'Candidate not in prior snapshot')
            require(c['text']==before[c['id']]['memory'],'Candidate text mismatch')
            require(c['hash']==md5(c['text'])==physical[c['id']]['hash'],'Candidate hash mismatch')
        source_message='user: Please remember these synthetic preferences:\n'+'\n'.join(expected)+'\n'
        require(search['query_sha256']==hashlib.sha256(source_message.encode()).hexdigest(),'Exact-source query hash mismatch')
        extraction=attempt['extraction'];visible={c['text'] for c in candidates}
        require(extraction['existing']==[{'id':str(i),'text':c['text']} for i,c in enumerate(candidates)],'Prompt candidate projection mismatch')
        emitted_before=[text for text in expected if row['extractor']=='literal_reemit' or text not in visible]
        require(extraction['emitted_before_admission_filter']==emitted_before,'Controlled extraction mismatch')
        before_facts={v['memory'] for v in before.values()}
        emitted=[t for t in emitted_before if t not in before_facts] if row['arm']=='exact_admission' else emitted_before
        require(extraction['emitted_texts']==emitted,'Admission filter mismatch')
        require(extraction['response']=={'memory':[{'id':str(i),'text':t,'attributed_to':'user','linked_memory_ids':[]} for i,t in enumerate(emitted)]},'Literal response mismatch')
        require(all(len(extraction[k])==64 for k in ['system_prompt_sha256','user_prompt_sha256']),'Prompt hash missing')
        candidate_hashes={c['hash'] for c in candidates}
        admitted=[];seen=set()
        for text in emitted:
            h=md5(text)
            if h not in candidate_hashes and h not in seen:admitted.append(text);seen.add(h)
        results=attempt['result']['results']
        require(all(r['event']=='ADD' for r in results),'Returned non-ADD event')
        require([r['memory'] for r in results]==admitted,'Returned ADD/extraction/hash reconciliation failed')
        new_ids=[r['id'] for r in results]
        require(len(set(new_ids))==len(new_ids) and not (set(new_ids)&set(before)),'Returned ADD identity reused')
        require(set(current)==set(before)|set(new_ids),'Snapshot/returned ADD identities mismatch')
        for result in results:require(current[result['id']]['memory']==result['memory'],'ADD/snapshot content mismatch')
        selected_history=history[history_cursor:history_cursor+len(results)]
        require([h['memory_id'] for h in selected_history]==new_ids,'ADD/history insertion order mismatch')
        history_cursor+=len(results)
        require(attempt['add_history_rows']==history_cursor,'add_history_rows metric mismatch')
        require(set(history_ids[:history_cursor])==set(current),'Cumulative history/snapshot mismatch')
        u=len(candidate_hashes & {md5(t) for t in expected})
        bound_applicable=ordinal>0 and before_facts==expected_set and row['arm']!='exact_admission'
        if bound_applicable:
            require(len(results)==n-u,'Conditional N-|U| count mismatch')
            require(len(results)>=max(0,n-k),'Conditional counting lower bound failed')
        observations.append(dict(attempt=ordinal,physical_records=len(current),distinct_facts=len(text_set),extra_copies=len(current)-len(text_set),fact_set_pass=text_set==expected_set,returned_adds=len(results),candidate_rows=len(candidates),candidate_distinct_hashes=u,effective_top_k=k,conditional_bound_applicable=bound_applicable,conditional_admitted_duplicates=len(results) if bound_applicable else None,query_sha256=search['query_sha256']))
        before=current
    require(history_cursor==len(history),'Unaccounted history ADD rows')
    require(set(before)==set(physical),'Final snapshot/physical point identities mismatch')
    return dict(embedder=row['embedder'],extractor=row['extractor'],arm=row['arm'],n=n,attempts=observations)

def check_campaign(out,report_path):
    spec=load(out/'frozen_spec.json');spec_hash=sha(out/'frozen_spec.json')
    require((out/'spec.sha256').read_text().strip()==spec_hash,'Frozen spec digest mismatch')
    require(spec['source_commit']==SOURCE_COMMIT,'Wrong Mem0 source pin')
    require(spec['runner_sha256']==sha(HERE/'experiment.py'),'Frozen runner changed')
    require(spec['installed_main_sha256']==NATIVE_MAIN_SHA,'Wrong frozen native main digest')
    native=Path(importlib.metadata.distribution('mem0ai').locate_file('mem0/memory/main.py'))
    persistence=Path(importlib.metadata.distribution('qdrant-client').locate_file('qdrant_client/local/persistence.py'))
    require(sha(native)==NATIVE_MAIN_SHA,'Installed native main changed')
    require(sha(persistence)==PERSISTENCE_SHA,'Qdrant persistence decoder source changed')
    for package,version in spec['environment']['packages'].items():
        require(importlib.metadata.version(package)==version,f'Installed {package} version changed')
    for key,values in [('sizes',SIZES),('embedders',EMBEDDERS),('extractors',EXTRACTORS),('arms',ARMS)]:require(spec[key]==list(values),f'Frozen {key} changed')
    facts=spec['facts'];require(len(facts)==40 and len(set(facts))==len({md5(t) for t in facts})==40,'Invalid fixture/hash uniqueness')
    parsed=ast.parse((HERE/'experiment.py').read_text())
    literal_facts=next(ast.literal_eval(n.value) for n in parsed.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='FACTS' for t in n.targets))
    require(facts==literal_facts,'Frozen/source fixture facts differ')
    rows=load(out/'cases.json');keys=[(r['embedder'],r['extractor'],r['arm'],r['n']) for r in rows]
    wanted={(e,x,a,n) for e in EMBEDDERS for x in EXTRACTORS for a in ARMS for n in SIZES}
    require(len(keys)==len(set(keys))==96 and set(keys)==wanted,'Incomplete or repeated 96-case coverage')
    tracked=[out/'frozen_spec.json',out/'spec.sha256',out/'cases.json',out/'summary.json',out/'environment.json']
    for row in rows:
        folder=out/'state'/f"{row['embedder']}__{row['extractor']}__{row['arm']}__n{row['n']}"
        require(load(folder/'case.json')==row,'Per-case/aggregate row mismatch')
        tracked.extend([folder/'case.json',folder/'history.sqlite',folder/'qdrant/collection/study_memories/storage.sqlite'])
    digests={str(p.relative_to(out)):sha(p) for p in tracked}
    observations=[]
    for row in rows:
        folder=out/'state'/f"{row['embedder']}__{row['extractor']}__{row['arm']}__n{row['n']}"
        observations.append(check_case(row,folder,facts))
    groups=[]
    for e in EMBEDDERS:
        for x in EXTRACTORS:
            for a in ARMS:
                group=[r for r in observations if (r['embedder'],r['extractor'],r['arm'])==(e,x,a)]
                groups.append(dict(embedder=e,extractor=x,arm=a,executions=len(group),final_extra_copies=sum(r['attempts'][-1]['extra_copies'] for r in group),final_fact_set_passes=sum(r['attempts'][-1]['fact_set_pass'] for r in group)))
    summary=load(out/'summary.json');require(summary['parameterized_executions']==96 and summary['groups']==groups,'Summary/raw aggregate mismatch')
    require(all(sha(out/rel)==h for rel,h in digests.items()),'Raw files changed while being checked')
    report=dict(status='PASS',checker_sha256=sha(__file__),frozen_spec_sha256=spec_hash,runner_sha256=spec['runner_sha256'],native_main_sha256=sha(native),qdrant_persistence_sha256=sha(persistence),case_count=96,api_calls=288,
      verification='Separate implementation, no experiment or Mem0 metric-function imports; direct read-only Qdrant SQLite PointStruct decoding, history and recorded API reconciliation. Same study, not external replication.',
      interpretation='Controlled extractors, finite parameter executions; no live-model frequency, semantic accuracy, vendor exactly-once promise, or concurrent-admission guarantee.',
      final_fact_set_passes=sum(r['attempts'][-1]['fact_set_pass'] for r in observations),native_cells_with_extra_copies=sum(r['arm']=='native_k10' and r['attempts'][-1]['extra_copies']>0 for r in observations),groups=groups,cases=observations,
      raw_sha256=digests,raw_files_unchanged=True,
      coverage_limits=['Candidate membership, literal hashes and count reconciliation are verified; ranking is not independently recomputed.','Per-attempt states are reconstructed from final raw points, append-only history and returned ADD identities.','Dense vector dimensions/finiteness and hash-control vectors are verified; checker does not rerun BGE ONNX inference.'])
    report_path.write_text(json.dumps(report,indent=2)+'\n')
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,default=HERE/'results');parser.add_argument('--report',type=Path,default=HERE/'verification.json');args=parser.parse_args()
    result=check_campaign(args.out,args.report)
    print(json.dumps({k:result[k] for k in ['status','case_count','api_calls','final_fact_set_passes','native_cells_with_extra_copies']},indent=2))
