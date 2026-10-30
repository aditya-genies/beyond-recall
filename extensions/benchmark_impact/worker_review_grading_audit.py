"""Read-only audit of completed pilot grading, aggregation, and one public witness.

No grader/model request or new label is produced. Labels are checked for exact
coverage, blinding, provenance and joins; aggregation is implemented separately.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from corrected_official_metric import locomo_proxy


class AuditError(ValueError):pass
def need(test,message):
 if not test:raise AuditError(message)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def mean(values):
 values=[v for v in values if v is not None]
 return statistics.mean(values) if values else None
def equivalent(a,b):
 if isinstance(a,dict):return isinstance(b,dict) and set(a)==set(b) and all(equivalent(a[k],b[k]) for k in a)
 if isinstance(a,list):return isinstance(b,list) and len(a)==len(b) and all(equivalent(x,y) for x,y in zip(a,b))
 if isinstance(a,float):return type(b) in (int,float) and math.isfinite(b) and abs(a-b)<=1e-12
 return type(a)==type(b) and a==b
def decision_rows(value,items):
 need(isinstance(value,dict) and set(value)=={'decisions'} and isinstance(value['decisions'],list),'Wrong grade envelope')
 rows=value['decisions'];ids=[]
 for row in rows:
  need(isinstance(row,dict) and set(row)=={'id','task_correct','current_conflict','evidence_supported','reason'},'Unexpected decision fields')
  need(type(row['task_correct']) is bool and isinstance(row['id'],str) and isinstance(row['reason'],str),'Wrong grade scalar type')
  need(row['current_conflict'] in ('yes','no','uncertain') and row['evidence_supported'] in ('yes','no','uncertain'),'Wrong grade auxiliary label')
  ids.append(row['id'])
 need(len(ids)==len(set(ids))==len(items) and set(ids)=={r['id'] for r in items},'Grade identity/coverage mismatch')
 return rows
def rubric(q):
 if q['unanswerable']:return 'Correct only if the response recognizes that the requested information is unavailable or the question is unanswerable.'
 if q['dataset']=='longmemeval':
  base='Correct if the response contains the complete required answer or an equivalent answer; a subset alone is insufficient.'
  if q['category']=='knowledge-update':return base+' Previous information may accompany the required updated answer when marked as previous. Contradictory simultaneous current assertions do not constitute an equivalent complete answer. This explicit contradiction rule is an adapted clarification, not a verbatim official scoring rule.'
  if q['category']=='temporal-reasoning':return base+' Preserve the official rubric tolerance for off-by-one day/week/month counts.'
  if q['category']=='single-session-preference':return 'Correct if the response correctly recalls and uses the relevant personal preference; it need not satisfy every point in the reference rubric.'
  return base
 return 'Semantic task label: answer must supply the reference information; allow equivalent wording. This is an adapted Sol judgement, separate from official category-specific stemmed token F1.'


def audit(out):
 files={}
 def tracked(relative):
  p=out/relative;files[str(relative)]=sha(p);return load(p)
 for stem in ('protocol','reader_protocol','grading_protocol','grading_packet'):
  need((out/(stem+'.sha256')).read_text().strip()==sha(out/(stem+'.json')),'Protocol/packet sidecar differs: '+stem)
 protocol=tracked('protocol.json');reader=tracked('reader_protocol.json');grading=tracked('grading_protocol.json');packet=tracked('grading_packet.json')
 need(packet['items_sha256']==sha(out/'grading_items.json') and packet['source_protocol_sha256']==sha(out/'protocol.json') and packet['reader_protocol_sha256']==sha(out/'reader_protocol.json') and packet['grading_protocol_sha256']==sha(out/'grading_protocol.json'),'Packet linkage mismatch')
 for relative,digest in protocol['source_hashes'].items():need(sha(HERE.parents[1]/relative)==digest,'Frozen source hash differs: '+relative)
 need(grading['source_sha256']==sha(HERE/'grade.py') and reader['reader_source_sha256']==sha(HERE/'reader.py'),'Grader/reader source changed')
 need(reader['contexts_sha256']==sha(out/'contexts.json') and reader['aliases_sha256']==sha(out/'reader_aliases.json') and protocol['evaluator_sha256']==sha(out/'evaluator_questions.json'),'Reader/evaluator linkage differs')
 questions_list=tracked('evaluator_questions.json');questions={q['key']:q for q in questions_list}
 contexts_list=tracked('contexts.json');contexts={r['case']:r for r in contexts_list};aliases=tracked('reader_aliases.json')
 need(len(questions)==24 and len(contexts)==len(contexts_list)==len(aliases)==336,'Question/context/alias coverage differs')
 need({a['case'] for a in aliases}==set(contexts),'Alias/context IDs differ')
 by_prompt=defaultdict(dict)
 for alias in aliases:
  row=contexts[alias['case']];q=questions[alias['question_key']]
  need(all(alias[k]==row[k] for k in ('case','question_key','backend','arm')),'Alias context join differs')
  need(row['question']==q['question'] and row['question_date']==q['question_date'],'Context query/date differs')
  ip=out/'reader_inputs'/alias['prompt_sha256']/'prompt.txt'
  need(sha(ip)==alias['prompt_sha256'],'Reader prompt content address differs')
  evidence=row['context'];ids={e['event_id'] for e in evidence};expected=set(q['expected_events'])
  coverage=None if q['unanswerable'] or q['missing_gold_locations'] or not expected else len(ids&expected)/len(expected)
  calculated=dict(context_records=len(evidence),distinct_event_ids=len(ids),distinct_exact_strings=len({e['text'] for e in evidence}),duplicate_event_slots=len(evidence)-len(ids),positive_support_coverage=coverage)
  need(calculated==row['metrics'],'Context metric definition differs')
  by_prompt[alias['prompt_sha256']][q['key']]=alias
 need(set(by_prompt)==set(reader['input_hashes']) and len(by_prompt)==149,'Unique prompt coverage differs')
 items=tracked('grading_items.json');itemmap={r['id']:r for r in items}
 need(len(items)==len(itemmap)==447,'Grading item identity count differs')
 desired_pairs=set();response_data={};transport=Counter()
 for model,repeats in (('sol',2),('qwen',1)):
  for h in reader['input_hashes']:
   for repeat in range(repeats):
    relative=f'reader_results/{model}/{h}/r{repeat}';status=tracked(relative+'/status.json');response=tracked(relative+'/parsed.json')
    transport[model+'/'+status['status']]+=1;need(status['status']=='PASS','Reader missing/error retained in claimed complete data')
    need(set(response)=={'answer','cited_event_ids','abstain'} and isinstance(response['answer'],str) and type(response['abstain']) is bool and isinstance(response['cited_event_ids'],list) and all(isinstance(c,str) for c in response['cited_event_ids']),'Reader schema differs')
    need(status['prompt_sha256']==sha(out/relative/'prompt.txt')==h,'Physical response prompt hash differs')
    need((out/relative/'prompt.txt').read_bytes()==(out/'reader_inputs'/h/'prompt.txt').read_bytes(),'Physical response prompt differs')
    text=(out/relative/'response.txt').read_text();files[relative+'/response.txt']=sha(out/relative/'response.txt')
    need(status['response_sha256']==sha(out/relative/'response.txt'),'Reader response hash differs')
    if model=='qwen' and text.strip().startswith('```'):
     lines=text.strip().splitlines();text='\n'.join(lines[1:-1]) if lines[-1].strip()=='```' else text
    need(json.loads(text)==response,'Raw reader text/parsed response differs')
    if model=='sol':need(status['returncode']==0 and status['tool_event_types']==[] and set(status['item_types'])<={'agent_message','reasoning'},'Unexpected retained reader tool/status event')
    path=relative+'/parsed.json';need(packet['response_hashes'][path]==sha(out/path),'Response/packet digest mismatch');response_data[path]=(response,status)
    for key in by_prompt[h]:desired_pairs.add((path,key))
 actual_pairs=set()
 for item in items:
  q=questions[item['question_key']];path=item['response_path'];response,_=response_data[path];h=Path(path).parts[2]
  alias=by_prompt[h][q['key']];context=contexts[alias['case']]
  need(item['id']==hashlib.sha256((path+sha(out/path)+q['key']).encode()).hexdigest()[:24],'Grade item identity not bound to response bytes/question')
  for key in ('question','question_date','reference','dataset','category','unanswerable'):need(item[key]==q[key],'Grading question/ref/category join differs')
  need(item['answer']==response['answer'] and item['evidence']==context['context'] and item['response_sha256']==sha(out/path),'Grader answer/evidence/digest differs')
  actual_pairs.add((path,q['key']))
 need(len(actual_pairs)==len(items) and actual_pairs==desired_pairs,'Answer-question pair coverage differs')
 need(set(packet['response_hashes'])==set(response_data),'Packet response coverage differs')
 decisions={};batches=[]
 def check_batch(relative,batch):
  status=tracked(relative+'/status.json');parsed=tracked(relative+'/parsed.json');folder=out/relative
  need(status['status']=='PASS' and status['returncode']==0 and status['tool_event_types']==[] and set(status['item_types'])<={'agent_message','reasoning'},'Grading status/tool summary differs')
  prompt=(folder/'prompt.txt').read_text();files[relative+'/prompt.txt']=sha(folder/'prompt.txt')
  need(status['prompt_sha256']==sha(folder/'prompt.txt') and prompt.startswith(grading['rubric']),'Grading prompt/hash/rubric differs')
  payload=json.loads(prompt[len(grading['rubric']):]);wanted=[]
  for item in batch:wanted.append({k:item[k] for k in ('id','question','question_date','reference','answer','evidence')}|{'task_rubric':rubric(item)})
  wanted.sort(key=lambda i:hashlib.sha256(('grading-order-v1'+i['id']).encode()).hexdigest())
  need(payload==wanted and prompt==grading['rubric']+json.dumps(wanted,ensure_ascii=True,separators=(',',':')),'Grading payload/blinding/order differs')
  need(status['response_sha256']==sha(folder/'response.txt'),'Grading raw-response hash differs');files[relative+'/response.txt']=sha(folder/'response.txt')
  need(json.loads((folder/'response.txt').read_text())==parsed,'Raw/parsed grade differs')
  need(tracked(relative+'/schema.json')==grading['schema'],'Grade output schema differs')
  return decision_rows(parsed,batch)
 wanted_batches={f'batch-{start:05d}' for start in range(0,len(items),6)}
 need({p.name for p in (out/'grading_results').glob('batch-*')}==wanted_batches,'Extra/missing primary grading batch')
 for start in range(0,len(items),6):
  relative=f'grading_results/batch-{start:05d}';batch=items[start:start+6];rows=check_batch(relative,batch);batches.append(relative)
  for row in rows:need(row['id'] not in decisions,'Repeated decision ID');decisions[row['id']]=row
 need(len(decisions)==447,'Primary decision coverage differs')
 calibration=tracked('grading_calibration.json');need(grading['calibration_sha256']==sha(out/'grading_calibration.json'),'Calibration input pin differs')
 cal_decisions={d['id']:d for d in check_batch('grading_results/calibration',calibration)};mismatches=[]
 for item in calibration:
  for label in ('task_correct','current_conflict'):
   if cal_decisions[item['id']][label]!=item['expected_'+label]:mismatches.append(dict(id=item['id'],label=label,expected=item['expected_'+label],observed=cal_decisions[item['id']][label]))
 cal_report=tracked('grading_calibration_report.json')
 need(cal_report['mismatches']==mismatches and cal_report['status']=='CALIBRATION_MISMATCH' and len(calibration)==12 and len(mismatches)==2 and all(m['label']=='current_conflict' for m in mismatches),'Failed calibration has been changed or misreported')
 by_pair={(itemmap[k]['response_path'],itemmap[k]['question_key']):d for k,d in decisions.items()}
 observations=tracked('observations.json');expected_keys=set();lookup={};derived=[]
 for alias in aliases:
  q=questions[alias['question_key']];context=contexts[alias['case']]
  for model,repeats in (('sol',2),('qwen',1)):
   for repeat in range(repeats):
    path=f"reader_results/{model}/{alias['prompt_sha256']}/r{repeat}/parsed.json";response,status=response_data[path];d=by_pair[path,q['key']]
    key=(alias['backend'],model,q['key'],repeat,alias['arm']);need(key not in expected_keys,'Repeated condition observation key');expected_keys.add(key)
    row=dict(case=alias['case'],question_key=q['key'],group=q['group'],dataset=q['dataset'],category=q['category'],backend=alias['backend'],arm=alias['arm'],reader=model,repeat=repeat,
             prompt_sha256=alias['prompt_sha256'],response_path=path,reader_status='PASS',task_correct=d['task_correct'],supported_task_correct=d['task_correct'] and d['evidence_supported']=='yes',evidence_supported=d['evidence_supported'],current_conflict_unvalidated=d['current_conflict'],
             abstain=response['abstain'],invalid_citation_count=sum(c not in {e['event_id'] for e in context['context']} for c in response['cited_event_ids']),
             locomo_token_proxy=locomo_proxy(response['answer'],q['reference'],q['category']) if q['dataset']=='locomo' else None,
             context_serialized_utf8_bytes=len(json.dumps(context['context'],ensure_ascii=True,separators=(',',':')).encode()),**context['metrics'])
    derived.append(row);lookup[key]=row
 actual_lookup={(r['backend'],r['reader'],r['question_key'],r['repeat'],r['arm']):r for r in observations}
 need(len(observations)==len(actual_lookup)==len(derived)==1008 and set(actual_lookup)==expected_keys,'Condition observation coverage differs')
 for key,row in lookup.items():need(equivalent(row,{k:actual_lookup[key][k] for k in row}),'Observation label/metric/join differs')
 summaries=[];grouped=defaultdict(list)
 for row in derived:grouped[row['backend'],row['reader'],row['dataset'],row['arm']].append(row)
 for (backend,model,dataset,arm),rows in sorted(grouped.items()):
  by_question=defaultdict(list)
  for row in rows:by_question[row['question_key']].append(row)
  qmean=lambda field:mean([mean([r[field] for r in rs]) for rs in by_question.values()])
  summaries.append(dict(backend=backend,reader=model,dataset=dataset,arm=arm,unique_questions=len(by_question),condition_observations=len(rows),missing_reader=0,missing_grade=0,
    task_correct_available_case=qmean('task_correct'),reader_failure_as_incorrect=qmean('task_correct'),supported_task_available_case=qmean('supported_task_correct'),locomo_token_proxy=qmean('locomo_token_proxy'),
    evidence_supported_counts=dict(Counter(r['evidence_supported'] for r in rows)),current_conflict_unvalidated_counts=dict(Counter(r['current_conflict_unvalidated'] for r in rows)),
    mean_context_serialized_utf8_bytes=mean([r['context_serialized_utf8_bytes'] for r in rows]),duplicate_event_slots=mean([r['duplicate_event_slots'] for r in rows]),positive_support_coverage=mean([r['positive_support_coverage'] for r in rows])))
 paired=[];clean_variation=[];losses=[];gains=[]
 for backend in ('mem0_raw','llama_index'):
  for model,repeats in (('sol',2),('qwen',1)):
   for dataset in sorted({q['dataset'] for q in questions.values()}):
    for arm in ('retry','event_admission','content_admission','read_event_dedup'):
     counts=Counter();deltas=[]
     for q in questions.values():
      if q['dataset']!=dataset:continue
      per_q=[]
      for repeat in range(repeats):
       a=lookup[backend,model,q['key'],repeat,'clean'];b=lookup[backend,model,q['key'],repeat,arm];counts[f"{int(a['task_correct'])}_to_{int(b['task_correct'])}"]+=1;per_q.append(int(b['task_correct'])-int(a['task_correct']))
       if arm=='retry' and a['task_correct']!=b['task_correct']:
        dedup=lookup[backend,model,q['key'],repeat,'read_event_dedup'];record=dict(backend=backend,reader=model,repeat=repeat,question_key=q['key'],dataset=dataset,dedup_task_correct=dedup['task_correct'],dedup_reuses_clean_prompt=a['prompt_sha256']==dedup['prompt_sha256'])
        (losses if a['task_correct'] else gains).append(record)
      deltas.append(mean(per_q))
     paired.append(dict(backend=backend,reader=model,dataset=dataset,arm=arm,unique_questions_with_paired_grades=len(deltas),mean_paired_task_difference=mean(deltas),dependent_question_repeat_transitions=dict(counts)))
  for dataset in sorted({q['dataset'] for q in questions.values()}):
   counts=Counter()
   for q in questions.values():
    if q['dataset']==dataset:
     a=lookup[backend,'sol',q['key'],0,'clean']['task_correct'];b=lookup[backend,'sol',q['key'],1,'clean']['task_correct'];counts[f'{int(a)}_to_{int(b)}']+=1
   clean_variation.append(dict(backend=backend,reader='sol',dataset=dataset,clean_repeat_task_transitions=dict(counts)))
 summary=tracked('pilot_summary.json')
 need(equivalent(summaries,summary['summaries']) and equivalent(paired,summary['paired']) and equivalent(clean_variation,summary['clean_repeat_variation']),'Aggregate mean/transition derivation differs')
 need(summary['grading_calibration']==cal_report and summary['semantic_claim_gate'].startswith('FAILED auxiliary calibration'),'Calibration gate was lost in summary')
 need(summary['condition_observations']==1008 and summary['graded_unique_answer_question_pairs']==447 and summary['unique_questions']==24 and summary['expected_unique_prompts']==149 and summary['grade_failures']==[] and summary['unique_request_status_counts']==dict(transport),'Summary denominators/status differ')
 metric=summary['token_metric_development_correction'];differences=[abs(r['locomo_token_proxy']-r['frozen_development_proxy']) for r in observations if r['locomo_token_proxy'] is not None]
 need(metric['material_tolerance']==1e-12 and metric['measured_material_differences']==sum(v>1e-12 for v in differences)==0 and metric['measured_bit_level_inequalities']==sum(v!=0 for v in differences) and metric['maximum_absolute_difference']==max(differences),'Metric correction discrepancy count differs')
 phases=tracked('native_phase_metrics.json');phase_map={(r['backend'],r['scope'],r['tag']):r for r in phases};wanted_phase_keys=set()
 for backend in ('mem0_raw','llama_index'):
  for ep in sorted((out/'participants').glob('*.json')):
   scope=ep.stem;base=Path('stores')/backend/scope;settings=[('initial','native_once',base/'clean','initial')]
   for mode in ('native_retry','event_admission','content_admission'):settings.extend([('cut-'+mode,mode,base/(mode+'-cut'),'retry'),('resume-'+mode,mode,base/mode,'retry')])
   for tag,mode,folder,action in settings:
    key=backend,scope,tag;wanted_phase_keys.add(key);status=tracked(str(folder/(action+'_status.json')));receipts=tracked(str(folder/(action+'_receipts.json')));execution=tracked(f'executions/{backend}-{scope}-{tag}.json')
    expected=dict(backend=backend,scope=scope,tag=tag,mode=mode,submitted_receipts=len(receipts),receipt_outcomes=dict(Counter(r['status'] for r in receipts)),native_record_count_delta=status['after_count']-status['before_count'],instrumented_application_phase_seconds=status['wall_seconds'],whole_process_seconds=execution['wall_seconds'])
    need(equivalent(expected,phase_map[key]),'Native phase aggregation differs')
 need(len(phases)==len(phase_map)==196 and set(phase_map)==wanted_phase_keys,'Native phase coverage differs')
 witness=recipe_witness(out,questions,contexts,lookup,response_data)
 need(all(sha(out/relative)==digest for relative,digest in files.items()),'An audited input changed while this audit ran')
 result=dict(status='PASS',phase='Independent same-study read-only grading/aggregation audit; no regrading or new request',auditor_sha256=sha(__file__),summary_sha256=sha(out/'pilot_summary.json'),summarizer_sha256=sha(HERE/'summarize_pilot.py'),input_files_unchanged_during_audit=True,
  source_protocol_sha256=sha(out/'protocol.json'),reader_protocol_sha256=sha(out/'reader_protocol.json'),grading_protocol_sha256=sha(out/'grading_protocol.json'),grading_packet_sha256=sha(out/'grading_packet.json'),
  primary_grade_batches=len(batches),primary_decisions=len(decisions),authored_calibration_items=len(calibration),authored_calibration_requests=1,calibration_mismatches=mismatches,
  physical_reader_requests=dict(transport),unique_prompts=149,condition_aliases=336,dependent_condition_observations=len(derived),unique_questions=len(questions),aggregate_groups=len(summaries),paired_groups=len(paired),native_application_phases=len(phases),
  loss_repeat_transitions=len(losses),loss_backend_reader_question_combinations=len({(r['backend'],r['reader'],r['question_key']) for r in losses}),loss_unique_questions=len({r['question_key'] for r in losses}),gain_repeat_transitions=len(gains),all_loss_combinations_dedup_task_correct=all(r['dedup_task_correct'] for r in losses),
  loss_combinations_reusing_clean_prompt=len({(r['backend'],r['reader'],r['question_key']) for r in losses if r['dedup_reuses_clean_prompt']}),losses=losses,gains=gains,
  clean_sol_task_repeat_disagreements=sum(sum(v for k,v in r['clean_repeat_task_transitions'].items() if k in ('0_to_1','1_to_0')) for r in clean_variation),
  evidence_supported_counts=dict(Counter(r['evidence_supported'] for r in derived)),current_conflict_unvalidated_counts=dict(Counter(r['current_conflict_unvalidated'] for r in derived)),input_sha256=files,
  interpretation=['The failed auxiliary calibration is retained: task labels are exploratory and current-state labels are unvalidated; no definitive semantic/stale-state efficacy result.',
                  '447 physical answers, 447 answer-question grades and 1008 aliased condition observations are distinct dependent denominators.',
                  'Clean/dedup identical prompts reuse the same archived response; input restoration is not a new recovery generation.',
                  'Observed clean Sol task-label repeat agreement does not establish reader determinism or stable backend snapshot.',
                  'Native application phase includes persistence plus witness export; whole-process time includes startup; neither is pure query latency or a physical disk-write count.',
                  'Decision reasons and evidence labels remain automated, same-study, same-family judgements, not independent human peer review.',
                  'Retained empty tool-event summaries are checked; raw CLI event streams were not archived.'])
 return result,witness


def recipe_witness(out,questions,contexts,lookup,response_data):
 key='f65dcff812445376dbc709ef';q=questions[key];need(q['reference']=='3' and q['source_question_id']=='45dc21b6','Recipe reference/identity differs')
 source=Path('/tmp/beyond-recall-benchmark-feasibility-20261029/longmemeval_s_cleaned.json')
 need(sha(source)=='d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442','Public full-history source SHA differs')
 raw=next(row for row in load(source) if row['question_id']==q['source_question_id']);need(raw['question']==q['question'] and str(raw['answer'])==q['reference'] and raw['question_date']==q['question_date'],'Recipe upstream question/answer/date differs')
 ep=load(out/'participants'/f"{q['episode_scope']}.json");events={e['event_id']:e for e in ep['events']};gold=[events[i] for i in q['expected_events']]
 raw_evidence=[]
 for position,(sid,date,turns) in enumerate(zip(raw['haystack_session_ids'],raw['haystack_dates'],raw['haystack_sessions'])):
  for turn_index,turn in enumerate(turns):
   for event in gold:
    if event['text']==turn['content']:
     need(event['speaker']==turn['role'] and event['occurred_at']==date and turn.get('has_answer') is True,'Recipe public turn provenance differs')
     raw_evidence.append(dict(event_id=event['event_id'],upstream_session_id=sid,session_position=position,turn_index=turn_index,date=date,speaker=turn['role'],full_text_sha256=hashlib.sha256(turn['content'].encode()).hexdigest()))
 need(len(raw_evidence)==2,'Recipe gold occurrence coverage differs')
 old='f36100b59a26e63666fe32cd';new='c013be29cdabd2738e96a10d';states={};ctx={}
 for state,arm in (('clean','clean'),('native_retry','retry')):
  folder=out/'stores/llama_index'/q['episode_scope']/state;doc=load(folder/'storage/docstore.json')['docstore/data'];vector=load(folder/'storage/default__vector_store.json')['embedding_dict'];need(set(doc)==set(vector),'Recipe physical doc/vector IDs differ')
  candidates=next(r['candidates'] for r in load(folder/'candidates.json') if r['invocation']==key)
  for candidate in candidates:
   node=doc[candidate['physical_id']]['__data__'];need(candidate['text']==node['text'] and candidate['event_id']==node['metadata']['study_event_id'],'Recipe candidate differs from physical record')
  states[state]=dict(physical_records=len(doc),older_evidence_records=sum(w['__data__']['metadata']['study_event_id']==old for w in doc.values()),latest_evidence_records=sum(w['__data__']['metadata']['study_event_id']==new for w in doc.values()),older_native_candidate_ranks=[i+1 for i,r in enumerate(candidates) if r['event_id']==old],latest_native_candidate_ranks=[i+1 for i,r in enumerate(candidates) if r['event_id']==new])
 for arm in ('clean','retry','read_event_dedup','event_admission','content_admission','no_context','oracle_support'):
  case=next(c for c in contexts.values() if c['question_key']==key and c['backend']=='llama_index' and c['arm']==arm)
  ctx[arm]=dict(case=case['case'],event_ids=[e['event_id'] for e in case['context']],metrics=case['metrics'],context_sha256=hashlib.sha256(json.dumps(case['context'],ensure_ascii=True,separators=(',',':')).encode()).hexdigest())
 need(ctx['clean']['event_ids']==ctx['read_event_dedup']['event_ids'] and new in ctx['clean']['event_ids'] and new not in ctx['retry']['event_ids'],'Recipe context mechanism differs')
 need(states['native_retry']['latest_native_candidate_ranks']==[11] and ctx['retry']['metrics']['duplicate_event_slots']==6,'Recipe duplicate displacement differs')
 answers=[]
 for model,repeats in (('sol',2),('qwen',1)):
  for repeat in range(repeats):
   for arm in ('clean','retry','read_event_dedup','event_admission','content_admission','no_context','oracle_support'):
    r=lookup['llama_index',model,key,repeat,arm];response,status=response_data[r['response_path']]
    need(r['task_correct']==(arm not in ('retry','no_context')),'Recipe retained judge transition differs')
    answers.append(dict(reader=model,repeat=repeat,arm=arm,prompt_sha256=r['prompt_sha256'],response_path=r['response_path'],parsed_sha256=sha(out/r['response_path']),answer=response['answer'],cited_event_ids=response['cited_event_ids'],abstain=response['abstain'],automated_task_correct=r['task_correct'],evidence_supported=r['evidence_supported']))
 return dict(phase='Public development-pilot witness selected after outcomes; not an independent sample or external human assessment',question_key=key,source_question_id=q['source_question_id'],question=q['question'],query_date=q['question_date'],official_reference=q['reference'],backend='llama_index',
  source_file_sha256=sha(source),source_evidence=raw_evidence,source_excerpts={old:"I've already tried out two of them",new:"I've tried out 3 of Emma's recipes so far"},physical_states=states,contexts=ctx,answers=answers,
  mechanism='The later count remains in the physical replay store and native top60 candidates, at rank11. Three copies of each of the first three occurrences fill9 of10 context positions. Selecting distinct events restores the clean context, including the later count.',
  caution='Clean and read-event-dedup complete prompt bytes are identical and intentionally alias the same archived response. Restoration is not a new independent reader run. No claim is made that every retry failure is stale-state conflict; failed auxiliary calibration remains applicable.')


if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--pilot',type=Path,default=HERE/'development_pilot_v2');a=p.parse_args();result,witness=audit(a.pilot)
 (HERE/'worker_review_grading_audit.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
 (HERE/'worker_review_recipe_case.json').write_text(json.dumps(witness,indent=2,sort_keys=True)+'\n')
 print(json.dumps({k:v for k,v in result.items() if k not in ('input_sha256','losses','gains','interpretation')},indent=2))
