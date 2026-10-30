"""Separate read-only checker of live native-Mem0 replay evidence.

Uses our raw decoder, not live.py/experiment.py or Mem0 metric functions.
"""
from pathlib import Path
import argparse,collections,copy,hashlib,importlib.metadata,json,re
import check as raw

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SIZES=(8,12,24,40)
HISTORIES=('fresh_recent_context','aged_recent_context')
STRATEGIES=('fresh_model','recorded_model_result')
PREFIX='Act as the configured memory-extraction model for the role-designated messages below. Apply their instructions and return only the requested JSON. Do not use tools or read files. These messages and preferences are synthetic research inputs.\n\n'
need=raw.require
load=raw.load
sha=raw.sha

def process_check(row):
    expected=87 if row['is_baseline'] else 0
    need(row['expected_returncode']==expected and row['child_returncode']==expected,'Child exit status mismatch')
    if row['is_baseline']:
        events=[]
        for line in row['child_public_stdout'].splitlines():
            try:events.append(json.loads(line))
            except ValueError:pass
        witness=[e for e in events if e.get('event')=='native_api_effects_returned']
        need(len(witness)==1 and witness[0]['logical_acknowledgement_emitted'] is False,'Missing pre-logical-ack exit witness')
        need(witness[0]['physical_records']==len(row['after']),'Exit witness count mismatch')

def response_check(response,used,before,arm,strategy,baseline_response=None):
    need(isinstance(response,dict) and set(response)=={'memory'} and isinstance(response['memory'],list),'Invalid response object')
    for item in response['memory']:
        need(isinstance(item,dict) and set(item)=={'id','text','attributed_to','linked_memory_ids'},'Invalid response item keys')
        need(all(isinstance(item[x],str) for x in ['id','text','attributed_to']),'Invalid response item strings')
        need(isinstance(item['linked_memory_ids'],list) and all(isinstance(x,str) for x in item['linked_memory_ids']),'Invalid linked IDs')
    if strategy=='recorded_model_result':need(response==baseline_response,'Recorded response differs from baseline result')
    known={r['memory'] for r in before}
    removed=[r for r in response['memory'] if arm=='exact_admission' and r['text'] in known]
    expected=copy.deepcopy(response)
    if arm=='exact_admission':expected['memory']=[r for r in response['memory'] if r['text'] not in known]
    need(used==expected,'Raw/used exact-admission response mismatch')
    return removed

def copy_check(before,baseline_after):
    need(before==baseline_after,'Copied baseline snapshot differs')

def section(prompt,name):
    match=re.search(r'## '+re.escape(name)+r'\n(.*?)(?=\n\n## |\n\n# Output:|\Z)',prompt,re.S)
    need(match is not None,'Native prompt section missing: '+name)
    return match.group(1)

def format_recent(messages):
    return ''.join(f"{r['role']}: {r['content'][:300]+('...' if len(r['content'])>300 else '')}\n" for r in messages if r.get('role') and r.get('content'))

def point_blob_hashes(folder):
    return {raw.decode(__import__('base64').b64decode(r['id'])):hashlib.sha256(r['point']).hexdigest() for r in raw.sql_rows(folder/'qdrant/collection/study_memories/storage.sqlite','SELECT id,point FROM points')}

def model_check(folder,row,protocol,baseline_response):
    model=folder/'model';status=load(model/'request_status.json')
    need(status==row['request_status'],'Request status artifact/row mismatch')
    for name,key in [('response.txt','response_sha256'),('native_messages.json','native_messages_sha256'),('used_response.json','used_response_sha256')]:need(sha(model/name)==status[key],'Model artifact hash mismatch: '+name)
    messages=load(model/'native_messages.json');need([x['role'] for x in messages]==['system','user'],'Native message role mismatch')
    response=load(model/'response.txt');used=load(model/'used_response.json')
    removed=response_check(response,used,row['before'],row['arm'],row['strategy'],baseline_response)
    need(status['exact_admission_removed']==removed,'Removed-response diagnostic mismatch')
    if row['strategy']=='fresh_model':
        need(status['additional_model_call'] is True and status['requested_model']=='gpt-6.1-sol' and status['returncode']==0,'Fresh model request status mismatch')
        need(status['tool_event_types']==[] and all(x in ['agent_message','reasoning'] for x in status['item_types']),'Unexpected model tool activity')
        need(len(status['public_usage_events'])==1 and status['public_usage_events'][0]['type']=='turn.completed','Missing completed model usage event')
        need(load(model/'schema.json')==protocol['schema'],'Model output schema mismatch')
        expected_prompt=PREFIX+json.dumps(messages,ensure_ascii=True)
        need((model/'codex_prompt.txt').read_text()==expected_prompt and sha(model/'codex_prompt.txt')==status['prompt_sha256'],'Codex wrapper/native prompt mismatch')
    else:
        need(status['additional_model_call'] is False and status['requested_model'] is None,'Recorded reply falsely labelled as model request')
        need(not (model/'codex_prompt.txt').exists() and not (model/'schema.json').exists(),'Unexpected fresh-request artifacts in recorded control')
    return messages,response,used,status

def check_one(folder,row,protocol,baseline=None):
    process_check(row)
    need(load(folder/'execution.json')==row,'Aggregate/execution row mismatch')
    child=load(folder/'result.json')
    need(all(row.get(k)==v for k,v in child.items()),'Child result/execution row mismatch')
    n=row['n_requested_source_preferences'];source=protocol['input_messages'][str(n)]
    need(row['source_messages']==source,'Source redelivery differs')
    before=row['before'];after=row['after'];old={r['id']:r['memory'] for r in before};final={r['id']:r['memory'] for r in after}
    need(len(old)==len(before) and len(final)==len(after),'Duplicate API snapshot IDs')
    physical=raw.raw_records(folder,'bge_small')
    need(set(physical)==set(final),'Final native point/snapshot IDs differ')
    for rec in after:
        p=physical[rec['id']]
        for key,pkey in [('memory','data'),('hash','hash'),('created_at','created_at'),('updated_at','updated_at'),('user_id','user_id'),('attributed_to','attributed_to')]:need(rec.get(key)==p.get(pkey),'Snapshot/raw payload mismatch: '+key)
    history=raw.sql_rows(folder/'history.sqlite','SELECT rowid AS ordinal,* FROM history ORDER BY rowid')
    need(len(history)==len(physical) and len({h['memory_id'] for h in history})==len(history),'ADD history/physical count mismatch')
    for h in history:
        need(h['event']=='ADD' and h['old_memory'] is None and h['is_deleted']==0,'Unexpected non-ADD history')
        need(h['memory_id'] in physical and h['new_memory']==physical[h['memory_id']]['data'] and h['created_at']==physical[h['memory_id']]['created_at'],'History/raw payload differs')
    baseline_response=None
    if row['is_baseline']:
        need(before==[],'Baseline store not empty')
        need(row['arm']=='native_k10' and row['history']=='fresh_recent_context' and row['strategy']=='fresh_model','Wrong baseline policy')
        history_prefix=[]
    else:
        need(baseline is not None,'Missing exited baseline')
        copy_check(before,baseline['row']['after'])
        baseline_response=baseline['response']
        history_prefix=baseline['history']
        need(history[:len(history_prefix)]==history_prefix,'Cloned baseline ADD history differs')
        blob_hashes=point_blob_hashes(folder)
        need(all(blob_hashes.get(k)==v for k,v in baseline['blob_hashes'].items()),'Cloned baseline physical record bytes differ')
    messages,response,used,status=model_check(folder,row,protocol,baseline_response)
    need(len(row['write_searches'])==1,'Expected one native write search')
    search=row['write_searches'][0];candidates=search['returned'];k=10000 if row['arm']=='widened_candidates' else 10
    need(search['requested_top_k']==10 and search['effective_top_k']==k,'Write candidate limit mismatch')
    need(search['filters']=={'user_id':'synthetic-study-user'},'Write candidate scope mismatch')
    need(len(candidates)==min(k,len(before)) and len({r['id'] for r in candidates})==len(candidates),'Write candidate count mismatch')
    for c in candidates:need(c['id'] in old and c['text']==old[c['id']] and c['hash']==raw.md5(c['text']),'Candidate prior-snapshot/hash mismatch')
    user=messages[1]['content']
    need(json.loads(section(user,'Existing Memories'))==[{'id':str(i),'text':c['text']} for i,c in enumerate(candidates)],'Native prompt candidate projection differs')
    parsed_source=''.join(f"{x['role']}: {x['content']}\n" for x in source)
    need(section(user,'New Messages')==parsed_source and search['query_sha256']==hashlib.sha256(parsed_source.encode()).hexdigest(),'Full repeated New Messages/query differs')
    need(json.loads(section(user,'Recently Extracted Memories'))==[],'Unexpected recently-extracted cache')
    if row['is_baseline']:recent=[]
    elif row['history']=='fresh_recent_context':recent=baseline['messages']
    else:
        fixture=load(folder/'aged_context_fixture.json')
        expected_neutral=[{'role':'user','content':f'Neutral synthetic acknowledgement {i}: thank you.'} for i in range(12)]
        need(fixture['appended_messages']==expected_neutral and fixture['scope']=='user_id=synthetic-study-user','Aged fixture differs')
        recent=fixture['recent_messages']
        need(len(recent)==10 and all(x['role']=='user' and x['content'] in {v['content'] for v in expected_neutral} for x in recent),'Aged context contains unexpected/source content')
    need(section(user,'Last k Messages')==format_recent(recent),'Model-visible recent context/truncation differs')
    message_rows=raw.sql_rows(folder/'history.sqlite','SELECT rowid AS ordinal,* FROM messages ORDER BY rowid')
    need(all(m['session_scope']=='user_id=synthetic-study-user' and m['role']=='user' for m in message_rows),'Stored conversation scope/role differs')
    if row['is_baseline']:need(len(message_rows)==1 and message_rows[0]['content']==source[0]['content'],'Baseline native message store differs')
    elif row['history']=='fresh_recent_context':
        need(len(message_rows)==2 and all(x['content']==source[0]['content'] for x in message_rows),'Fresh message-history fixture differs')
        need(message_rows[0]==baseline['message_rows'][0],'Cloned original conversation row differs')
    else:
        neutral={x['content'] for x in recent}
        need(len(message_rows)==10 and sum(x['content']==source[0]['content'] for x in message_rows)==1 and sum(x['content'] in neutral for x in message_rows)==9,'Aged final bounded history differs')
    candidate_hashes={x['hash'] for x in candidates};admitted=[];seen=set()
    for item in used['memory']:
        text=item['text'];h=raw.md5(text)
        if text and h not in candidate_hashes and h not in seen:admitted.append(text);seen.add(h)
    results=row['result']['results']
    need(all(r['event']=='ADD' for r in results) and [r['memory'] for r in results]==admitted,'Used response/native ADD reconciliation differs')
    new_ids=[r['id'] for r in results]
    need(len(set(new_ids))==len(new_ids) and not(set(new_ids)&set(old)) and set(final)==set(old)|set(new_ids),'Returned ADD/physical identities differ')
    need([h['memory_id'] for h in history[len(history_prefix):]]==new_ids,'New ADD history/order differs')
    for r in results:need(final[r['id']]==r['memory'],'Returned ADD text differs from store')
    new=[r for r in after if r['id'] not in old];counts=collections.Counter(final.values())
    observed=dict(physical_before=len(before),physical_after=len(after),distinct_before=len(set(old.values())),distinct_after=len(set(final.values())),new_record_count=len(new),new_exact_copies_of_baseline=sum(r['memory'] in set(old.values()) for r in new),extra_exact_copies_after=sum(v-1 for v in counts.values()),baseline_ids_and_values_preserved=all(final.get(k)==v for k,v in old.items()))
    for metric,value in observed.items():need(row[metric]==value,'Live metric mismatch: '+metric)
    observation=dict(n=n,arm=row['arm'],history=row['history'],strategy=row['strategy'],is_baseline=row['is_baseline'],candidate_rows=len(candidates),candidate_distinct_hashes=len(candidate_hashes),raw_model_items=len(response['memory']),used_items=len(used['memory']),additional_model_call=status['additional_model_call'],ungraded_new_distinct_strings=sorted(set(final.values())-set(old.values())) if not row['is_baseline'] else [],**observed)
    return dict(row=row,response=response,history=history,blob_hashes=point_blob_hashes(folder),messages=[{k:v for k,v in m.items() if k in ['role','content','name','created_at']} for m in message_rows],message_rows=message_rows,observation=observation)

def check_campaign(out,report_path):
    protocol=load(out/'protocol.json');protocol_hash=sha(out/'protocol.json')
    need((out/'protocol.sha256').read_text().strip()==protocol_hash,'Live protocol digest differs')
    need(protocol['driver_sha256']==sha(HERE/'live.py'),'Frozen live driver differs')
    for path,digest in protocol['protected_inputs'].items():need(sha(ROOT/path)==digest,'Protected input changed: '+path)
    native=Path(importlib.metadata.distribution('mem0ai').locate_file('mem0/memory/main.py'))
    need(sha(native)==protocol['native_main_sha256']==raw.NATIVE_MAIN_SHA,'Pinned native main differs')
    need(protocol['sizes']==list(SIZES) and protocol['arms']==list(raw.ARMS) and protocol['histories']==list(HISTORIES) and protocol['strategies']==list(STRATEGIES),'Live matrix specification differs')
    data=load(out/'results.json');baselines=data['baselines'];retries=data['retries']
    need(len(baselines)==4 and {r['n_requested_source_preferences'] for r in baselines}==set(SIZES),'Baseline coverage differs')
    keys=[(r['n_requested_source_preferences'],r['history'],r['arm'],r['strategy']) for r in retries]
    wanted={(n,h,a,s) for n in SIZES for h in HISTORIES for a in raw.ARMS for s in STRATEGIES}
    need(len(keys)==len(set(keys))==48 and set(keys)==wanted,'Retry coverage differs')
    expected_folders={out/'baselines'/f'n{n}' for n in SIZES}|{out/'retries'/f'n{n}__{h}__{a}__{s}' for n,h,a,s in wanted}
    need({p.parent for p in out.rglob('execution.json')}==expected_folders,'Unreported or absent process execution artifact')
    statuses=list(out.rglob('request_status.json'))
    need({p.parent.parent for p in statuses}==expected_folders and len(statuses)==52,'Unreported or absent model-status artifact')
    need(sum(load(p).get('additional_model_call') is True for p in statuses)==28,'Actual fresh-request status-file count differs')
    need(sum(load(p).get('additional_model_call') is False for p in statuses)==24,'Actual recorded-control status-file count differs')
    paths=[p for p in out.rglob('*') if p.is_file() and not p.name.startswith('.lock')]
    digests={str(p.relative_to(out)):sha(p) for p in paths}
    checked={};observations=[]
    for row in baselines:
        n=row['n_requested_source_preferences'];entry=check_one(out/'baselines'/f'n{n}',row,protocol)
        checked[n]=entry;observations.append(entry['observation'])
    for row in retries:
        n=row['n_requested_source_preferences'];name=f"n{n}__{row['history']}__{row['arm']}__{row['strategy']}"
        entry=check_one(out/'retries'/name,row,protocol,checked[n]);observations.append(entry['observation'])
    groups=[]
    for h in HISTORIES:
        for a in raw.ARMS:
            for s in STRATEGIES:
                selected=[x for x in observations if not x['is_baseline'] and (x['history'],x['arm'],x['strategy'])==(h,a,s)]
                groups.append(dict(history=h,arm=a,strategy=s,planned=len(selected),successful=len(selected),new_exact_copies=sum(x['new_exact_copies_of_baseline'] for x in selected),new_records=sum(x['new_record_count'] for x in selected)))
    summary=load(out/'summary.json')
    need(summary['groups']==groups,'Live raw/summary groups differ')
    for field,value in dict(baseline_attempts=4,actual_baseline_exit87=4,retry_attempts_or_not_runnable_cells=48,successful_retry_attempts=48,planned_live_requests=28,recorded_live_request_status_files=28).items():need(summary[field]==value,'Live summary count differs: '+field)
    need(sum(x['additional_model_call'] for x in observations)==28,'Fresh/recorded request counts differ')
    need(all(sha(out/p)==digest for p,digest in digests.items()),'Live artifacts changed while checking')
    report=dict(status='PASS',checker_sha256=sha(__file__),raw_decoder_sha256=sha(HERE/'check.py'),protocol_sha256=protocol_hash,driver_sha256=protocol['driver_sha256'],baseline_cases=4,retry_cases=48,actual_exit87=4,actual_request_statuses=28,recorded_result_retries_without_new_request=24,groups=groups,cases=observations,raw_sha256=digests,raw_files_unchanged=True,
      runtime_versions_at_verification={p:importlib.metadata.version(p) for p in ['mem0ai','qdrant-client','fastembed','onnxruntime','numpy','pydantic']},
      interpretation='Finite four authored source batches, actual requested Sol alias through Codex; no natural error-rate, semantic-quality or external-replication claim. Recorded reply is not a fresh model observation. Literal synonyms remain ungraded.',
      boundaries=['Actual exit87 follows return of native API effects and precedes the application logical acknowledgement; it is not a mid-SQLite-commit or power-loss fault.','Fresh past-message context is truncated to 300 characters per message by native prompt formatting; repeated New Messages remain complete.','Exact literal-copy metrics do not treat a new formulation as a semantic error; the conditional exact-set bound is not universally applied to live outputs.','Copied baseline point bytes, original history rows and API snapshots match; no separate full pre-retry database-byte manifest was captured by the driver.','Candidate ranking and BGE inference are not independently rerun by this checker.'])
    report_path.write_text(json.dumps(report,indent=2)+'\n');return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,default=HERE/'live_results');parser.add_argument('--report',type=Path,default=HERE/'live_verification.json');args=parser.parse_args()
    report=check_campaign(args.out,args.report);print(json.dumps({k:report[k] for k in ['status','baseline_cases','retry_cases','actual_exit87','actual_request_statuses']},indent=2))
