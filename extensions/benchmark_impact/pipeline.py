"""Frozen development-pilot orchestration; outcomes are not confirmatory data."""
from __future__ import annotations
from dataclasses import asdict
from pathlib import Path
import argparse,collections,concurrent.futures,hashlib,json,os,shutil,subprocess,sys,time
import data

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
BACKENDS=('mem0_raw','llama_index');STORAGE_MODES=('native_retry','event_admission','content_admission')
READER_ARMS=('clean','retry','event_admission','content_admission','read_event_dedup','no_context','oracle_support')
BYTE_BUDGET=12000;RETURNED_LIMIT=10;CANDIDATE_LIMIT=60
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+'\n')
def interpreter(backend):return ROOT/('.venv-memory' if backend=='mem0_raw' else '.venv-impact')/'bin/python'
def source_files():return [HERE/p for p in ('data.py','memory_worker.py','pipeline.py','reader.py','grade.py','analysis_plan.json')]+[ROOT/'extensions/replanning_contracts/mem0_reference/experiment.py']
def prepare(out,cache):
 out.mkdir(parents=True,exist_ok=False)
 episodes,questions,pilot,split=data.corpus(cache)
 grouped=collections.defaultdict(list)
 for q in pilot:grouped[q.episode_scope].append(q)
 for scope,qs in grouped.items():
  ep=episodes[scope].participant();write(out/'participants'/f'{scope}.json',ep)
  write(out/'queries'/f'{scope}.json',[{'invocation':q.key,'question':q.question} for q in qs])
  sources=sorted({e['source_id'] for e in ep['events']})
  retry=[s for s in sources if int(data.stable('pilot-fault-v1',scope,s),16)%4==0]
  if not retry:retry=[min(sources,key=lambda s:data.stable('pilot-fault-v1',scope,s))]
  write(out/'retry_sources'/f'{scope}.json',retry)
 write(out/'evaluator_questions.json',[asdict(q) for q in pilot]);write(out/'split.json',split)
 # Fresh caches are bound to actual embedding files and both runtime metadata.
 embedding={'embedding_files':json.loads((ROOT/'extensions/replanning_contracts/mem0_reference/embedding_files.json').read_text()),
  'impact_runtime':json.loads((HERE/'environment_impact.json').read_text()),
  'mem0_runtime':json.loads((ROOT/'extensions/replanning_contracts/mem0_reference/results/frozen_spec.json').read_text())['environment'],
  'behavior':'Native embedding APIs cached by backend/action/text; no vector or ranking values fabricated. New cache per protocol.'}
 verified=[]
 for row in embedding['embedding_files']['files']:
  if '/snapshots/' not in row['cache_relative_path']:continue
  p=Path('/tmp/beyond-recall-bge-model')/row['cache_relative_path']
  if sha(p)!=row['sha256']:raise ValueError('Actual cached embedding asset differs: '+row['cache_relative_path'])
  verified.append(row['cache_relative_path'])
 embedding['verified_snapshot_assets_before_prepare']=verified
 write(out/'embedding_manifest.json',embedding)
 spec={'prepared_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'phase':'Development pilot, not held-out confirmation or an external preregistration',
  'source_hashes':{str(p.relative_to(ROOT)):sha(p) for p in source_files()},'dataset_hashes':data.PINNED,
  'protected_release':{'study.py':sha(ROOT/'study.py'),'results/cases.jsonl':sha(ROOT/'results/cases.jsonl'),'manuscript/main.pdf':sha(ROOT/'manuscript/main.pdf')},
  'participants':len(grouped),'questions':len(pilot),'backends':BACKENDS,'storage_modes':STORAGE_MODES,'reader_arms':READER_ARMS,
  'raw_api_scope':'Mem0 infer=False and native persisted LlamaIndex vector index; no extraction LLM, no vendor default-inferred-memory or managed-service comparison.',
  'native_implementation_note':'Both use real local BGE; native Mem0 hybrid retrieval versus LlamaIndex dense retrieval. They share some public embedding/provider code; they are not independent storage-theory replications.',
  'embedding_cache_scope':'Separate manifest-bound cache per backend/source-history scope, reused only by that participant sequentially; no concurrently initialized shared cache.',
  'controls':'One native baseline is closed and cloned, preserving original physical IDs. Admission controls apply after common historical provisioning; no original observations are retroactively deduplicated. Authored sequential lookup guards are not concurrent uniqueness guarantees.',
  'fault_schedule':'Select approximately25% of source occurrences by frozen SHA rule, independent of questions/gold. One controlled redelivery commits then actually exits87 before logical batch acknowledgement; fresh process redelivers the same set once more. No network packets or mid-commit failures are simulated.',
  'snapshot_bound':'Fail rather than truncate if 3x original event count exceeds10000. Original native source records and after-cut stores retained.',
  'retrieval':{'common_candidate_limit':CANDIDATE_LIMIT,'context_record_limit':RETURNED_LIMIT,'context_utf8_byte_budget':BYTE_BUDGET,'token_budget_claim':False,'read_dedup':'Collapse native retry candidate pool by logical event ID, not literal text; all arms use the same candidate limit.'},
  'question_date':'Full-row question date provided only to reader query context; never oracle dates or evaluator labels to ingestion.',
  'oracle':'Oracle support uses evaluator gold event locations as a labelled diagnostic; it is not an admissible deployed memory method or official benchmark score.',
  'no_context':'A no-retrieval reader control diagnoses guessing/parametric knowledge; it is not proof of training-set contamination.',
  'unanswerable':'Positive answer-support coverage is null for unanswerable cases and cases with unresolved gold locations; abstention is separate.',
  'inference_units':'Questions are nested in LoCoMo conversations and LME evidence components. Background sources can be shared; no IID industry failure rate or significance claim follows from call count.',
  'input_files':{str(p.relative_to(out)):sha(p) for group in ['participants','queries','retry_sources'] for p in sorted((out/group).glob('*.json'))},
  'evaluator_sha256':sha(out/'evaluator_questions.json'),'split_sha256':sha(out/'split.json'),'embedding_manifest_sha256':sha(out/'embedding_manifest.json')}
 write(out/'protocol.json',spec);(out/'protocol.sha256').write_text(sha(out/'protocol.json')+'\n');print(json.dumps({'prepared':str(out),'participants':len(grouped),'questions':len(pilot),'protocol_sha256':sha(out/'protocol.json')}))

def verify(out):
 spec=json.loads((out/'protocol.json').read_text())
 assert sha(out/'protocol.json')==(out/'protocol.sha256').read_text().strip()
 for rel,h in spec['source_hashes'].items():assert sha(ROOT/rel)==h,rel
 for rel,h in spec['protected_release'].items():assert sha(ROOT/rel)==h,rel
 for rel,h in spec['input_files'].items():assert sha(out/rel)==h,rel
 assert sha(out/'embedding_manifest.json')==spec['embedding_manifest_sha256']
 assert sha(out/'evaluator_questions.json')==spec['evaluator_sha256']
 assert sha(out/'split.json')==spec['split_sha256']
 return spec

def invoke(out,backend,scope,folder,action,mode,tag,cut=False):
 cache=out/'embedding_caches'/backend/(scope+'.sqlite');cache.parent.mkdir(parents=True,exist_ok=True)
 cmd=[str(interpreter(backend)),str(HERE/'memory_worker.py'),action,'--backend',backend,'--mode',mode,'--folder',str(folder),
  '--cache',str(cache),'--embedding-manifest',str(out/'embedding_manifest.json'),
  '--episode',str(out/'participants'/f'{scope}.json'),'--retry-sources',str(out/'retry_sources'/f'{scope}.json'),
  '--queries',str(out/'queries'/f'{scope}.json'),'--output',str(folder/'candidates.json'),'--redeliveries','1','--limit',str(CANDIDATE_LIMIT)]
 if cut:cmd.append('--cut')
 env=dict(os.environ);env.update(HF_HUB_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',MEM0_TELEMETRY='false',FASTEMBED_CACHE_PATH='/tmp/beyond-recall-bge-model')
 started=time.monotonic();result=subprocess.run(cmd,capture_output=True,text=True,timeout=900,env=env)
 diag=Path('/tmp/beyond-recall-impact-native-diagnostics');diag.mkdir(exist_ok=True);(diag/f'{backend}-{scope}-{tag}.stderr').write_text(result.stderr)
 report={'backend':backend,'scope':scope,'action':action,'mode':mode,'tag':tag,'returncode':result.returncode,'expected_returncode':87 if cut else 0,'wall_seconds':round(time.monotonic()-started,4),'stdout':result.stdout}
 write(out/'executions'/f'{backend}-{scope}-{tag}.json',report)
 if result.returncode!=report['expected_returncode']:raise RuntimeError(f'Native participant failed: {backend}/{scope}/{tag}; public status and private diagnostics retained')
 return report

def build_one(out,backend,scope):
 base=out/'stores'/backend/scope/'clean'
 if base.exists():raise FileExistsError(base)
 base.mkdir(parents=True)
 invoke(out,backend,scope,base,'initial','native_once','initial')
 invoke(out,backend,scope,base,'query','native_once','query-clean')
 for mode in STORAGE_MODES:
  folder=base.parent/mode;shutil.copytree(base,folder)
  invoke(out,backend,scope,folder,'retry',mode,'cut-'+mode,True)
  # Capture the actual after-exit native stores before fresh-process resumption.
  cut=base.parent/(mode+'-cut');shutil.copytree(folder,cut)
  invoke(out,backend,scope,folder,'retry',mode,'resume-'+mode)
  invoke(out,backend,scope,folder,'query',mode,'query-'+mode)
 print(json.dumps({'native_finished':backend,'scope':scope}),flush=True)

def native(out,workers):
 spec=verify(out);scopes=sorted(p.stem for p in (out/'participants').glob('*.json'))
 # Each sequential participant pipeline owns a cache. Concurrent participants
 # never race to initialize or write the same cache database.
 with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
  futures=[pool.submit(build_one,out,b,s) for b in BACKENDS for s in scopes]
  for f in concurrent.futures.as_completed(futures):f.result()
 write(out/'native_completion.json',{'status':'COMPLETE','participants':len(scopes)*len(BACKENDS),'actual_expected_exit87':len(scopes)*len(BACKENDS)*len(STORAGE_MODES),'source_protocol_sha256':sha(out/'protocol.json')})

def select_context(rows,dedup=False):
 chosen=[];seen=set();used=2 # JSON evidence-array brackets; commas counted below.
 for row in rows:
  if dedup and row['event_id'] in seen:continue
  if len(chosen)>=RETURNED_LIMIT:break
  item={'event_id':row['event_id'],'source_id':row['source_id'],'date':row['occurred_at'],'text':row['text']}
  encoded=json.dumps(item,ensure_ascii=True,separators=(',',':')).encode()
  cost=len(encoded)+(1 if chosen else 0)
  if used+cost>BYTE_BUDGET:continue # Whole records only; no false partial-support credit.
  chosen.append(item);seen.add(row['event_id']);used+=cost
 return chosen

def verify_native(out):
 completion=json.loads((out/'native_completion.json').read_text())
 assert completion['status']=='COMPLETE' and completion['source_protocol_sha256']==sha(out/'protocol.json')
 expected={}
 scopes=sorted(p.stem for p in (out/'participants').glob('*.json'))
 assert completion['participants']==len(scopes)*len(BACKENDS),'Native participant count differs'
 assert completion['actual_expected_exit87']==len(scopes)*len(BACKENDS)*len(STORAGE_MODES),'Native cut count differs'
 for backend in BACKENDS:
  for scope in scopes:
   def add(tag,action,mode,code):
    expected[f'{backend}-{scope}-{tag}.json']={'backend':backend,'scope':scope,'action':action,'mode':mode,'tag':tag,'returncode':code,'expected_returncode':code}
   add('initial','initial','native_once',0)
   add('query-clean','query','native_once',0)
   for mode in STORAGE_MODES:
    add('cut-'+mode,'retry',mode,87)
    add('resume-'+mode,'retry',mode,0)
    add('query-'+mode,'query',mode,0)
 actual={p.name for p in (out/'executions').glob('*.json')}
 assert actual==set(expected),'Native execution coverage incomplete or duplicated'
 for name,labels in expected.items():
  row=json.loads((out/'executions'/name).read_text())
  for key,value in labels.items():assert row[key]==value,(name,key)
 return completion

def contexts(out):
 verify(out);verify_native(out);questions=json.loads((out/'evaluator_questions.json').read_text());all_rows=[]
 for q in questions:
  scope=q['episode_scope'];episode=json.loads((out/'participants'/f'{scope}.json').read_text())
  for backend in BACKENDS:
   tables={mode:{r['invocation']:r['candidates'] for r in json.loads((out/'stores'/backend/scope/mode/'candidates.json').read_text())} for mode in ['clean',*STORAGE_MODES]}
   for arm in READER_ARMS:
    mode={'retry':'native_retry','read_event_dedup':'native_retry'}.get(arm,arm)
    if arm=='no_context':selected=[]
    elif arm=='oracle_support':
     selected=select_context([{'event_id':e['event_id'],'source_id':e['source_id'],'occurred_at':e['occurred_at'],'text':e['speaker']+': '+e['text']} for e in episode['events'] if e['event_id'] in set(q['expected_events'])]) if not q['unanswerable'] else []
    else:selected=select_context(tables[mode][q['key']],arm=='read_event_dedup')
    gold=set(q['expected_events']);visible={r['event_id'] for r in selected}
    all_rows.append({'case':data.stable('case',backend,q['key'],arm),'question_key':q['key'],'backend':backend,'arm':arm,'question':q['question'],'question_date':q['question_date'],'context':selected,
     'metrics':{'context_records':len(selected),'distinct_event_ids':len(visible),'distinct_exact_strings':len({r['text'] for r in selected}),'duplicate_event_slots':len(selected)-len(visible),'positive_support_coverage':None if q['unanswerable'] or q['missing_gold_locations'] or not gold else len(gold&visible)/len(gold)}})
 write(out/'contexts.json',all_rows);print(json.dumps({'context_cells':len(all_rows),'questions':len(questions),'native_backends':len(BACKENDS),'arms':len(READER_ARMS)}))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','native','contexts']);p.add_argument('--out',type=Path,required=True);p.add_argument('--cache',type=Path);p.add_argument('--workers',type=int,default=2);a=p.parse_args();a.out=a.out.resolve()
 if a.action=='prepare':prepare(a.out,a.cache)
 elif a.action=='native':native(a.out,a.workers)
 else:contexts(a.out)
