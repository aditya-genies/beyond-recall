#!/usr/bin/env python3
"""Small, descriptive Codex/Sol pilot. No API key or company source is used.

Prepare freezes prompts and protocol before `run` makes any model requests.
An altered snapshot applies the first returned operation from baseline repeat 0.
This is input-driven replanning, separately counted from same-prompt variation.
"""
import argparse, concurrent.futures, hashlib, json, os, pathlib, shutil
import subprocess, tempfile, time

HERE = pathlib.Path(__file__).resolve().parent
MODEL = 'gpt-6.1-sol'
SCENARIOS = [
 ('preferences', [], 'Please remember that I prefer concise replies, metric units, and cycling as my favorite hobby.'),
 ('correction', [{'id':'unit-record','key':'units','value':'imperial'}], 'I now prefer metric units instead of imperial. I also prefer concise replies.'),
 ('retirement', [{'id':'diet-record','key':'diet','value':'vegetarian'}], 'Please forget the stored claim that I am vegetarian. Remember that I enjoy cycling.'),
 ('mixed', [{'id':'unit-record','key':'units','value':'imperial'},{'id':'diet-record','key':'diet','value':'vegetarian'}], 'I now use metric units. Forget the vegetarian claim. Please remember that I prefer concise replies.'),
 ('temporal_correction', [{'id':'city-record','key':'city','value':'Oslo'}], 'I moved from Oslo to Lisbon last month. Lisbon is my current home. Please remember that I like walking.'),
 ('conditional_preference', [{'id':'style-record','key':'reply_style','value':'detailed'}], 'For routine questions I prefer concise answers; for mathematical proofs I still want details. Please remember this distinction and that I prefer metric units.'),
]
SCHEMA = {'type':'object','properties':{'operations':{'type':'array','items':{
 'type':'object','properties':{'kind':{'type':'string','enum':['put','delete']},
 'target':{'type':['string','null']},'key':{'type':['string','null']},'value':{'type':['string','null']}},
 'required':['kind','target','key','value'],'additionalProperties':False}}},
 'required':['operations'],'additionalProperties':False}
INSTRUCTION = '''You maintain a small personal memory store. From the conversation and current records below, choose the memory mutations that you judge appropriate now. Do not use tools, read files, or discuss this task. Return only a JSON object with an operations array. Each operation has exactly four fields: kind (put or delete), target (an existing record id or null for a new record), key (a short fact name, or null for delete), and value (a string, or null for delete). Prefer updating an existing record when it represents the same fact. You may omit facts that are already represented adequately. Do not invent personal facts. The records are synthetic.\n'''

def dump(path,obj):
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(obj,indent=2,ensure_ascii=True)+'\n')

def digest(data): return hashlib.sha256(data).hexdigest()
def canonical(x): return json.dumps(x,sort_keys=True,separators=(',',':'))
def prompt(records,conversation):
 return INSTRUCTION+'\nCurrent records:\n'+json.dumps(records,sort_keys=True)+'\nConversation:\n'+conversation+'\n'

def prepare(out):
 out.mkdir(parents=True,exist_ok=False)
 frozen={'protocol_version':1,'requested_model':MODEL,'prepared_at_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
  'design':'6 synthetic scenarios x 2 snapshot conditions x 2 fresh-context repeats = 24 planned requests',
  'conditions':['original snapshot','snapshot after first operation from original repeat 0'],
  'partial_rule':'Apply first valid operation of original repeat 0; new records get deterministic pilot-only id. Use identical altered snapshot for both repeats. If baseline repeat 0 fails, record both partial trials as not runnable; do not replace the baseline.',
  'primary_observations':['exact normalized operation-list variation between identical-prompt repeats','exact normalized operation-list variation between original repeat 0 and each altered-snapshot repeat','schema validity','attempted tool events'],
  'normalization':'JSON key order/formatting ignored; ordered operations and literal string/target arguments retained. Unordered lists also compared as secondary observation. No semantic equivalence or accuracy inference.',
  'exclusions':'No failed request is discarded. No temperature, seed, exact backend snapshot or hidden system prompt control. No population drift-rate or model-quality estimate. All calls run through the Codex harness.',
  'reasoning_effort':'medium (requested)','timeout_seconds':180,'max_concurrent_requests':3,
  'schema':SCHEMA,'instruction':INSTRUCTION,'scenarios':[]}
 for name,records,conversation in SCENARIOS:
  p=prompt(records,conversation)
  frozen['scenarios'].append({'id':name,'records':records,'conversation':conversation,'original_prompt_sha256':digest(p.encode())})
  (out/(name+'-original.txt')).write_text(p)
 dump(out/'schema.json',SCHEMA);dump(out/'protocol.json',frozen)
 (out/'protocol.sha256').write_text(digest((out/'protocol.json').read_bytes())+'\n')
 print(json.dumps({'prepared':str(out),'planned_requests':24,'protocol_sha256':digest((out/'protocol.json').read_bytes())}))

def validate(obj,records):
 if not isinstance(obj,dict) or set(obj)!={'operations'} or not isinstance(obj['operations'],list): raise ValueError('invalid top level')
 known={r['id'] for r in records}
 for op in obj['operations']:
  if not isinstance(op,dict) or set(op)!={'kind','target','key','value'}: raise ValueError('invalid operation fields')
  if op['kind'] not in ('put','delete'): raise ValueError('invalid kind')
  if op['target'] is not None and (not isinstance(op['target'],str) or op['target'] not in known): raise ValueError('unknown target')
  if op['kind']=='delete':
   if op['target'] is None or op['key'] is not None or op['value'] is not None: raise ValueError('invalid delete')
  elif not isinstance(op['key'],str) or not isinstance(op['value'],str): raise ValueError('invalid put')
 return obj['operations']

def apply_first(records,operations,name):
 records=[dict(r) for r in records]
 if operations:
  op=operations[0];target=op['target'] or name+'-first-effect'
  records=[r for r in records if r['id']!=target]
  if op['kind']=='put':records.append({'id':target,'key':op['key'],'value':op['value']})
 return sorted(records,key=lambda r:r['id'])

def run_one(out,cli,scenario,condition,repeat,records):
 name=scenario['id'];trial=f'{name}-{condition}-{repeat}';folder=out/'trials'/trial;folder.mkdir(parents=True,exist_ok=False)
 p=prompt(records,scenario['conversation']);(folder/'prompt.txt').write_text(p)
 env=dict(os.environ)
 for key in list(env):
  if key.endswith('_API_KEY') or key in ('OPENAI_BASE_URL','OPENAI_API_BASE','CODEX_THREAD_ID','CODEX_SESSION_ID'):env.pop(key)
 result={'trial':trial,'scenario':name,'condition':condition,'repeat':repeat,'requested_model':MODEL,
  'prompt_sha256':digest(p.encode()),'records':records,'started_at_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
 with tempfile.TemporaryDirectory(prefix='memory-study-fresh-') as cwd:
  cmd=[cli,'exec','--model',MODEL,'--ephemeral','--ignore-user-config','--skip-git-repo-check','--sandbox','read-only',
   '--json','--config','project_doc_max_bytes=0','--config','model_reasoning_effort="medium"','--cd',cwd,
   '--output-schema',str(out/'schema.json'),'-o',str(folder/'response.txt'),'-']
  start=time.monotonic()
  try:
   r=subprocess.run(cmd,input=p,text=True,capture_output=True,env=env,timeout=180)
   stdout,stderr=r.stdout,r.stderr;result['returncode']=r.returncode
  except subprocess.TimeoutExpired as e:
   stdout=e.stdout or '';stderr=e.stderr or ''
   if isinstance(stdout,bytes):stdout=stdout.decode(errors='replace')
   if isinstance(stderr,bytes):stderr=stderr.decode(errors='replace')
   result['returncode']=None;result['error']='timeout'
  result['wall_seconds']=round(time.monotonic()-start,3)
  # Only public-facing events are retained: final outputs/usage/attempted tools.
  # Reasoning text, local paths, session ids and harness diagnostics are omitted.
  events=[];tool_events=[]
  for line in stdout.splitlines():
   try:e=json.loads(line)
   except ValueError:continue
   kind=e.get('type','');item=e.get('item',{})
   if item.get('type') in ('command_execution','mcp_tool_call','web_search','file_change'):
    tool_events.append({'event_type':kind,'item_type':item['type']})
   if kind=='turn.completed':events.append({'type':kind,'usage':e.get('usage')})
   if kind in ('error','turn.failed'):events.append({'type':kind,'message':'harness request failed; inspect local diagnostics'})
  result['public_events']=events;result['tool_events']=tool_events
  response=(folder/'response.txt').read_text() if (folder/'response.txt').exists() else ''
  result['response_sha256']=digest(response.encode());result['schema_valid']=False
  try:
   operations=validate(json.loads(response),records)
   result.update(schema_valid=True,operations=operations,normalized_operations_sha256=digest(canonical(operations).encode()))
  except (ValueError,TypeError) as e:result['parse_error']=str(e)
  # Diagnostics remain outside repository/release; do not print auth/config content.
  private=pathlib.Path(tempfile.gettempdir())/'beyond-recall-sol-diagnostics';private.mkdir(exist_ok=True)
  (private/(trial+'.stderr.txt')).write_text(stderr)
 dump(folder/'result.json',result)
 print(json.dumps({'trial':trial,'valid':result['schema_valid'],'returncode':result['returncode'],'seconds':result['wall_seconds']}),flush=True)
 return result

def run(out,cli):
 protocol=json.loads((out/'protocol.json').read_text())
 assert digest((out/'protocol.json').read_bytes())==(out/'protocol.sha256').read_text().strip()
 assert protocol['requested_model']==MODEL
 dump(out/'harness.json',{'cli_version':subprocess.check_output([cli,'--version'],text=True).strip(),
  'requested_model':MODEL,'auth':'Existing personal Codex account; no API key used',
  'configuration':'Fresh temporary cwd, ephemeral sessions, ignored user config, project documents disabled, read-only, requested medium reasoning; no resumed conversations',
  'backend_model_snapshot':'not exposed by retained CLI events','temperature':'not controlled','seed':'not controlled',
  'system_prompt':'Codex harness, not controlled; user/project instructions disabled where exposed',
  'provenance':'Raw final responses, prompts and usage are archived; hidden reasoning, local paths/session ids and local diagnostics are intentionally excluded.'})
 results=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
  jobs=[pool.submit(run_one,out,cli,s,'original',r,s['records']) for s in protocol['scenarios'] for r in (0,1)]
  for job in concurrent.futures.as_completed(jobs):results.append(job.result())
  by_trial={r['trial']:r for r in results}
  jobs=[]
  for s in protocol['scenarios']:
   base=by_trial[s['id']+'-original-0']
   if not base['schema_valid'] or base['returncode']!=0:
    for repeat in (0,1):results.append({'trial':f'{s["id"]}-partial-{repeat}','scenario':s['id'],'condition':'partial','repeat':repeat,'not_run':'baseline repeat 0 unavailable'})
    continue
   records=apply_first(s['records'],base['operations'],s['id'])
   jobs.extend(pool.submit(run_one,out,cli,s,'partial',r,records) for r in (0,1))
  for job in concurrent.futures.as_completed(jobs):results.append(job.result())
 results.sort(key=lambda r:r['trial']);dump(out/'results.json',results)
 summarize(out)

def summarize(out):
 results=json.loads((out/'results.json').read_text());valid=[r for r in results if r.get('schema_valid') and r.get('returncode')==0 and not r.get('tool_events')]
 index={r['trial']:r for r in valid};same=[];changed=[]
 for name,_,_ in SCENARIOS:
  for condition in ('original','partial'):
   a=index.get(f'{name}-{condition}-0');b=index.get(f'{name}-{condition}-1')
   if a and b:
    assert a['prompt_sha256']==b['prompt_sha256']
    same.append({'scenario':name,'condition':condition,'literal_different':a['operations']!=b['operations'],
     'unordered_different':sorted(map(canonical,a['operations']))!=sorted(map(canonical,b['operations']))})
  a=index.get(name+'-original-0')
  for repeat in (0,1):
   b=index.get(f'{name}-partial-{repeat}')
   if a and b:changed.append({'scenario':name,'partial_repeat':repeat,'prompt_changed':a['prompt_sha256']!=b['prompt_sha256'],'literal_different':a['operations']!=b['operations']})
 summary={'planned_requests':24,'recorded_trials':len(results),'valid_tool_free_successes':len(valid),
  'same_prompt_pairs':len(same),'same_prompt_literal_variation_pairs':sum(x['literal_different'] for x in same),
  'same_prompt_unordered_variation_pairs':sum(x['unordered_different'] for x in same),
  'changed_snapshot_comparisons':len(changed),'changed_snapshot_literal_changes':sum(x['literal_different'] for x in changed),
  'same_prompt_details':same,'changed_snapshot_details':changed,
  'interpretation':'Descriptive Codex-harness observations. Literal differences do not establish semantic disagreement, error, harmful drift, or population incidence. Altered snapshots are different inputs. No inferential test is warranted.'}
 dump(out/'summary.json',summary);print(json.dumps(summary,indent=2))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','run','summarize']);p.add_argument('--out',type=pathlib.Path,required=True);p.add_argument('--cli',default=shutil.which('codex'));a=p.parse_args();a.out=a.out.resolve()
 if a.action=='prepare':prepare(a.out)
 elif a.action=='run':
  if not a.cli:raise SystemExit('Pass --cli path to authenticated Codex CLI; no API key fallback is implemented.')
  run(a.out,a.cli)
 else:summarize(a.out)
