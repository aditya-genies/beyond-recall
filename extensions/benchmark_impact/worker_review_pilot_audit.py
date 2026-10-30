"""Read-only independent raw native-store audit of benchmark-impact pilot artifacts.

No model/native API is called, no upstream history is redistributed in reports,
and no method from pipeline/memory_worker is used to derive expected transitions.
"""
from __future__ import annotations
import argparse
import base64
from collections import Counter
import hashlib
import io
import json
import math
from pathlib import Path
import sqlite3
import sys

if __package__:
 from .test_worker import physical_records,RestrictedPointDecoder
else:
 sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
 from extensions.benchmark_impact.test_worker import physical_records,RestrictedPointDecoder

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
BACKENDS=('mem0_raw','llama_index');MODES=('native_retry','event_admission','content_admission')
EVENT_FIELDS={'event_id','source_id','occurred_at','speaker','text'}

class AuditError(ValueError):pass

def need(test,message):
 if not test:raise AuditError(message)
def load(path):return json.loads(Path(path).read_text())
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def object_sha(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def stable(*values):return hashlib.sha256(json.dumps(values,ensure_ascii=True,separators=(',',':')).encode()).hexdigest()[:24]
def safe(base,relative):
 path=(base/relative).resolve();need(path.is_relative_to(base.resolve()),'Artifact escapes its declared root');return path

def full_fingerprints(folder,backend):
 """Per-ID full Qdrant point bytes / Llama node and dense-vector fingerprints."""
 if backend=='mem0_raw':
  database=folder/'qdrant/collection/study_memories/storage.sqlite'
  connection=sqlite3.connect(database.resolve().as_uri()+'?mode=ro',uri=True)
  try:
   need(connection.execute('PRAGMA integrity_check').fetchone()[0]=='ok','Native SQLite integrity check failed')
   result={}
   for key,blob in connection.execute('SELECT id,point FROM points'):
    identity=RestrictedPointDecoder(io.BytesIO(base64.b64decode(key))).load()
    point=RestrictedPointDecoder(io.BytesIO(blob)).load()
    need(identity==point.id and identity not in result,'Native Qdrant key/point identity differs or repeats')
    need(point.payload.get('user_id')=='independent-benchmark-participant','Native Qdrant user scope differs')
    result[identity]=hashlib.sha256(blob).hexdigest()
   return result
  finally:connection.close()
 doc=load(folder/'storage/docstore.json')['docstore/data'];vector=load(folder/'storage/default__vector_store.json')['embedding_dict']
 need(set(doc)==set(vector),'Llama docstore/vector physical identity sets differ')
 return {identity:object_sha({'node':wrapped,'vector':vector[identity]}) for identity,wrapped in doc.items()}

def verify_records(records,events,expected_counts):
 counts=Counter(record['event_id'] for record in records.values())
 need(counts==Counter(expected_counts),'Physical event multiplicities differ from independent expectation')
 for physical,record in records.items():
  need(record['physical_id']==physical,'Physical map key/record ID mismatch')
  event=events[record['event_id']]
  need(record['text']==event['speaker']+': '+event['text'],'Native literal body differs from participant event')
  need(record['source_id']==event['source_id'] and record['occurred_at']==event['occurred_at'],'Native replay source or logical date changed')
  need(record['body_sha256']==object_sha(event),'Native event body digest differs')

def verify_candidates(path,questions,records):
 rows=load(path);wanted={q['invocation'] for q in questions}
 need(len(rows)==len(wanted) and {row['invocation'] for row in rows}==wanted,'Candidate query invocation coverage differs')
 total=0;logical_duplicate_slots=0
 for row in rows:
  candidates=row['candidates'];need(len(candidates)<=60,'Native common candidate bound exceeded')
  ids=[candidate['physical_id'] for candidate in candidates];need(len(set(ids))==len(ids),'Repeated physical identity in one native candidate list')
  for candidate in candidates:
   need(candidate['physical_id'] in records,'Candidate identity is absent from the persisted native store')
   native=records[candidate['physical_id']]
   for key in ('text','event_id','source_id','occurred_at','body_sha256'):need(candidate[key]==native[key],'Native candidate/persisted payload differs: '+key)
   score=candidate.get('score');need(type(score) in (int,float) and math.isfinite(score),'Native score is missing or nonfinite')
  total+=len(candidates);logical_duplicate_slots+=len(candidates)-len({candidate['event_id'] for candidate in candidates})
 return dict(query_invocations=len(rows),candidate_rows=total,duplicate_logical_event_slots=logical_duplicate_slots)

def expected_jobs(scopes):
 jobs={}
 for backend in BACKENDS:
  for scope in scopes:
   def add(tag,action,mode,code):jobs[f'{backend}-{scope}-{tag}.json']=dict(backend=backend,scope=scope,action=action,mode=mode,tag=tag,returncode=code,expected_returncode=code)
   add('initial','initial','native_once',0);add('query-clean','query','native_once',0)
   for mode in MODES:add('cut-'+mode,'retry',mode,87);add('resume-'+mode,'retry',mode,0);add('query-'+mode,'query',mode,0)
 return jobs

def verify_status(path,before,after,submitted,initial,cut,backend,mode):
 status=load(path)
 need(status['backend']==backend and status['mode']==mode,'Native status backend/mode differs')
 need(status['phase']==('initial' if initial else 'retry'),'Native status phase differs')
 need(status['before_count']==before and status['after_count']==after,'Native recorded counts differ from physical transitions')
 need(status['submitted_events']==submitted and status['redeliveries']==1,'Native recorded submission multiplicity differs')
 need(status['extraction_calls']==0,'Worker reports an extractor call in raw-document mode')
 need((status['fault'] is not None)==cut,'Native declared cut status differs')


def audit(out):
 out=Path(out).resolve();completion=out/'native_completion.json'
 if not completion.exists():
  return dict(status='NOT_READY',reason='Native completion marker absent; in-progress stores were not inspected.',execution_manifests_present=len(list((out/'executions').glob('*.json'))),model_calls=0,native_queries_or_remeasurement=0)
 protocol=load(out/'protocol.json');protocol_sha=sha(out/'protocol.json')
 need(protocol_sha==(out/'protocol.sha256').read_text().strip(),'Frozen pilot protocol SHA differs')
 for relative,expected in protocol['source_hashes'].items():need(sha(safe(ROOT,relative))==expected,'Frozen source changed: '+relative)
 for relative,expected in protocol['protected_release'].items():need(sha(safe(ROOT,relative))==expected,'Protected published artifact changed: '+relative)
 for relative,expected in protocol['input_files'].items():need(sha(safe(out,relative))==expected,'Frozen participant/query/retry input changed: '+relative)
 for name,key in [('embedding_manifest.json','embedding_manifest_sha256'),('evaluator_questions.json','evaluator_sha256'),('split.json','split_sha256')]:need(sha(out/name)==protocol[key],'Frozen input manifest changed: '+name)
 scopes=sorted(path.stem for path in (out/'participants').glob('*.json'));done=load(completion)
 need(protocol['participants']==len(scopes),'Declared source-history participant scope count differs')
 need(done==dict(status='COMPLETE',participants=len(scopes)*2,actual_expected_exit87=len(scopes)*6,source_protocol_sha256=protocol_sha),'Native completion fields/counts differ')
 jobs=expected_jobs(scopes);actual={path.name for path in (out/'executions').glob('*.json')}
 need(actual==set(jobs),'Native execution manifest coverage differs')
 for name,expected in jobs.items():
  row=load(out/'executions'/name)
  for key,value in expected.items():need(row[key]==value,'Native execution identity/phase/returncode differs: '+name+'/'+key)
 cases=[];totals=Counter()
 for scope in scopes:
  payload=load(out/'participants'/f'{scope}.json');need(set(payload)=={'scope','events'} and payload['scope']==scope,'Participant/evaluator field at episode boundary')
  events={event['event_id']:event for event in payload['events']};need(len(events)==len(payload['events']),'Repeated original event identity')
  need(all(set(event)==EVENT_FIELDS for event in events.values()),'Evaluator field at event boundary')
  n=len(events);sources=sorted({event['source_id'] for event in events.values()});retry=load(out/'retry_sources'/f'{scope}.json')
  chosen=[source for source in sources if int(stable('pilot-fault-v1',scope,source),16)%4==0]
  if not chosen:chosen=[min(sources,key=lambda source:stable('pilot-fault-v1',scope,source))]
  need(retry==chosen,'Source retry schedule differs from frozen non-gold SHA rule')
  replay=[event for event in payload['events'] if event['source_id'] in set(retry)];m=len(replay)
  questions=load(out/'queries'/f'{scope}.json');need(all(set(q)=={'invocation','question'} for q in questions),'Evaluator field in native retrieval request')
  base_counts={identity:1 for identity in events};cut_counts={identity:1+int(event['source_id'] in retry) for identity,event in events.items()};final_counts={identity:1+2*int(event['source_id'] in retry) for identity,event in events.items()}
  for backend in BACKENDS:
   parent=out/'stores'/backend/scope;clean=parent/'clean';baseline=physical_records(clean,backend);fingerprints=full_fingerprints(clean,backend)
   verify_records(baseline,events,base_counts);need(len(baseline)==n,'Common baseline count differs')
   need(set(fingerprints)==set(baseline),'Baseline physical/fingerprint identity sets differ')
   verify_status(clean/'initial_status.json',0,n,n,True,False,backend,'native_once')
   initial=load(clean/'initial_receipts.json');need(len(initial)==n and [r['event_id'] for r in initial]==list(events),'Initial receipt event coverage/order differs')
   need(all(r['status']=='applied' and r['physical_id'] in baseline for r in initial),'Common baseline receipt/physical identity differs')
   clean_snapshot=load(clean/'initial_snapshot.json');need({r['physical_id'] for r in clean_snapshot}==set(baseline),'Initial snapshot/physical IDs differ')
   for row in clean_snapshot:
    for key,value in baseline[row['physical_id']].items():need(row[key]==value,'Initial snapshot/physical payload differs')
   candidates=verify_candidates(clean/'candidates.json',questions,baseline)
   record=dict(scope=scope,backend=backend,original_events=n,replayed_events_per_delivery=m,baseline_physical_records=len(baseline),baseline_record_fingerprint=object_sha(fingerprints),clean_candidates=candidates,modes={})
   for mode in MODES:
    for phase,folder,counts in [('cut',parent/(mode+'-cut'),cut_counts if mode=='native_retry' else base_counts),('resumed',parent/mode,final_counts if mode=='native_retry' else base_counts)]:
     native=physical_records(folder,backend);verify_records(native,events,counts);full=full_fingerprints(folder,backend)
     need(set(full)==set(native),'Native node/vector/fingerprint identity sets differ')
     need(set(baseline)<=set(native),'Original physical IDs disappeared')
     need(all(full[identity]==digest for identity,digest in fingerprints.items()),'Original full native point/node/vector payload changed')
     expected=len(events)+(m if phase=='cut' else 2*m) if mode=='native_retry' else n
     need(len(native)==expected,'Native count transition differs')
     before=n if phase=='cut' else (n+m if mode=='native_retry' else n)
     verify_status(folder/'retry_status.json',before,expected,m,False,phase=='cut',backend,mode)
     receipt=load(folder/'retry_receipts.json');need(len(receipt)==m and [r['event_id'] for r in receipt]==[e['event_id'] for e in replay],'Replay receipt coverage/order differs')
     expected_status={'native_retry':'applied','event_admission':'suppressed_event_replay','content_admission':'suppressed_exact_content'}[mode]
     need(all(r['status']==expected_status for r in receipt),'Replay admission result differs from declared mode')
     if mode=='native_retry':need(len({r['physical_id'] for r in receipt})==m and all(r['physical_id'] in native and r['physical_id'] not in baseline for r in receipt),'Returned replay physical IDs differ')
     snapshot=load(folder/'retry_snapshot.json');need(len(snapshot)==len(native) and {r['physical_id'] for r in snapshot}==set(native),'Replay snapshot/physical cardinalities differ')
     for row in snapshot:
      for key,value in native[row['physical_id']].items():need(row[key]==value,'Replay snapshot/physical payload differs')
     result=dict(physical_records=len(native),original_records_preserved=True,original_record_fingerprint=object_sha({identity:full[identity] for identity in baseline}),all_replay_event_bodies_sources_dates_preserved=True,recorded_extraction_calls=0)
     if phase=='resumed':result['candidates']=verify_candidates(folder/'candidates.json',questions,native)
     record['modes'][mode+'/'+phase]=result;totals['native_stores_checked']+=1
   cases.append(record);totals['native_stores_checked']+=1
   totals['original_events_across_native_participants']+=n;totals['replay_events_per_delivery_across_native_participants']+=m
 need(sha(out/'protocol.json')==protocol_sha,'Pilot protocol changed during audit')
 return dict(status='PASS',phase='Independent same-study raw native evidence audit, no native/model API invocation',protocol_sha256=protocol_sha,source_history_scopes=len(scopes),native_participants=len(cases),execution_manifests=len(jobs),actual_expected_exit87=sum(row['returncode']==87 for row in jobs.values()),
  totals=dict(totals),cases=cases,auditor_sha256=sha(__file__),model_calls=0,native_queries_or_remeasurement=0,
  interpretation='Raw event/physical-state/count/clone/receipt/candidate consistency only. No reader quality, causal decision harm, official benchmark score, outside replication or definitive auxiliary-grading claim.')

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);parser.add_argument('--report',type=Path,required=True);args=parser.parse_args()
 try:report=audit(args.out)
 except Exception as error:
  report=dict(status='FAIL',error_type=type(error).__name__,error=str(error),model_calls=0,native_queries_or_remeasurement=0)
 args.report.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k!='cases'},indent=2))
 if report['status']=='FAIL':raise SystemExit(1)
