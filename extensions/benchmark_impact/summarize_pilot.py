"""Descriptive frozen-pilot summaries; no significance or population-rate claim."""
from __future__ import annotations
from pathlib import Path
import argparse,collections,json,statistics
import grade,pipeline,reader

def load(p):return json.loads(p.read_text())
def mean(values):
 values=[v for v in values if v is not None]
 return statistics.mean(values) if values else None

def summarize(out):
 pipeline.verify(out);pipeline.verify_native(out);spec=reader.verify(out);grade.verify_packet(out)
 questions={q['key']:q for q in load(out/'evaluator_questions.json')}
 contexts={r['case']:r for r in load(out/'contexts.json')}
 aliases=load(out/'reader_aliases.json');items=load(out/'grading_items.json')
 item_by_id={r['id']:r for r in items};decisions={};grade_failures=[]
 expected_batches={f'batch-{start:05d}' for start in range(0,len(items),6)}
 for name in sorted(expected_batches):
  folder=out/'grading_results'/name
  if not (folder/'status.json').exists():grade_failures.append({'batch':name,'status':'NOT_RUN'});continue
  status=load(folder/'status.json')
  if status['status']!='PASS':grade_failures.append({'batch':name,'status':status['status']});continue
  start=int(name.split('-')[1]);batch=items[start:start+6]
  for d in grade.validate_decisions(load(folder/'parsed.json'),batch):
   if d['id'] in decisions:raise ValueError('Duplicate grade identity')
   decisions[d['id']]=d
 graded={(item_by_id[k]['response_path'],item_by_id[k]['question_key']):v for k,v in decisions.items()}
 rows=[];transport_counts=collections.Counter()
 for model,repeats in [('sol',2),('qwen',1)]:
  for h in spec['input_hashes']:
   for repeat in range(repeats):
    p=out/'reader_results'/model/h/f'r{repeat}'/'status.json'
    transport_counts[model+'/'+(load(p)['status'] if p.exists() else 'NOT_RUN')]+=1
  for alias in aliases:
   q=questions[alias['question_key']];context=contexts[alias['case']]
   for repeat in range(repeats):
    folder=out/'reader_results'/model/alias['prompt_sha256']/f'r{repeat}'
    status=load(folder/'status.json') if (folder/'status.json').exists() else {'status':'NOT_RUN'}
    response=load(folder/'parsed.json') if status['status']=='PASS' else None
    path=str((folder/'parsed.json').relative_to(out));d=graded.get((path,q['key'])) if response is not None else None
    if response is not None:reader.validate(response,set(e['event_id'] for e in context['context']))
    rows.append({'case':alias['case'],'question_key':q['key'],'group':q['group'],'dataset':q['dataset'],'category':q['category'],'backend':alias['backend'],'arm':alias['arm'],'reader':model,'repeat':repeat,
     'prompt_sha256':alias['prompt_sha256'],'response_path':path,'reader_status':status['status'],'task_correct':None if d is None else d['task_correct'],
     'supported_task_correct':None if d is None else d['task_correct'] and d['evidence_supported']=='yes',
     'evidence_supported':None if d is None else d['evidence_supported'],'current_conflict_unvalidated':None if d is None else d['current_conflict'],
     'abstain':None if response is None else response['abstain'],'invalid_citation_count':None if response is None else len([c for c in response['cited_event_ids'] if c not in {e['event_id'] for e in context['context']}]),
     'locomo_token_proxy':grade.locomo_proxy(response['answer'],q['reference'],q['category']) if response is not None and q['dataset']=='locomo' else None,
     'context_serialized_utf8_bytes':len(json.dumps(context['context'],ensure_ascii=True,separators=(',',':')).encode()),**context['metrics']})
 groups=collections.defaultdict(list)
 for r in rows:groups[(r['backend'],r['reader'],r['dataset'],r['arm'])].append(r)
 summaries=[]
 for (backend,model,dataset,arm),group in sorted(groups.items()):
  by_question=collections.defaultdict(list)
  for row in group:by_question[row['question_key']].append(row)
  summaries.append({'backend':backend,'reader':model,'dataset':dataset,'arm':arm,'unique_questions':len(by_question),'condition_observations':len(group),
   'missing_reader':sum(r['reader_status']!='PASS' for r in group),'missing_grade':sum(r['task_correct'] is None for r in group),
   'task_correct_available_case':mean([mean([r['task_correct'] for r in rs]) for rs in by_question.values()]),
   'reader_failure_as_incorrect':mean([mean([False if r['reader_status']!='PASS' else r['task_correct'] for r in rs]) for rs in by_question.values()]),
   'supported_task_available_case':mean([mean([r['supported_task_correct'] for r in rs]) for rs in by_question.values()]),
   'locomo_token_proxy':mean([mean([r['locomo_token_proxy'] for r in rs]) for rs in by_question.values()]),
   'evidence_supported_counts':dict(collections.Counter(r['evidence_supported'] or 'missing' for r in group)),
   'current_conflict_unvalidated_counts':dict(collections.Counter(r['current_conflict_unvalidated'] or 'missing' for r in group)),
   'mean_context_serialized_utf8_bytes':mean([r['context_serialized_utf8_bytes'] for r in group]),
   'duplicate_event_slots':mean([r['duplicate_event_slots'] for r in group]),'positive_support_coverage':mean([r['positive_support_coverage'] for r in group])})
 paired=[]
 lookup={(r['backend'],r['reader'],r['question_key'],r['repeat'],r['arm']):r for r in rows}
 for backend in pipeline.BACKENDS:
  for model,repeats in [('sol',2),('qwen',1)]:
   for dataset in sorted({q['dataset'] for q in questions.values()}):
    for arm in ['retry','event_admission','content_admission','read_event_dedup']:
     counts=collections.Counter();deltas=[]
     for q in questions.values():
      if q['dataset']!=dataset:continue
      per_question=[]
      for repeat in range(repeats):
       a=lookup[(backend,model,q['key'],repeat,'clean')]['task_correct'];b=lookup[(backend,model,q['key'],repeat,arm)]['task_correct']
       if a is None or b is None:counts['missing']+=1;continue
       counts[f'{int(a)}_to_{int(b)}']+=1;per_question.append(int(b)-int(a))
      if per_question:deltas.append(mean(per_question))
     paired.append({'backend':backend,'reader':model,'dataset':dataset,'arm':arm,'unique_questions_with_paired_grades':len(deltas),'mean_paired_task_difference':mean(deltas),'dependent_question_repeat_transitions':dict(counts)})
 clean_variation=[]
 for backend in pipeline.BACKENDS:
  for dataset in sorted({q['dataset'] for q in questions.values()}):
   counts=collections.Counter()
   for q in questions.values():
    if q['dataset']!=dataset:continue
    a=lookup[(backend,'sol',q['key'],0,'clean')]['task_correct'];b=lookup[(backend,'sol',q['key'],1,'clean')]['task_correct']
    counts['missing' if a is None or b is None else f'{int(a)}_to_{int(b)}']+=1
   clean_variation.append({'backend':backend,'reader':'sol','dataset':dataset,'clean_repeat_task_transitions':dict(counts)})
 native_metrics=[]
 for backend in pipeline.BACKENDS:
  for episode in sorted((out/'participants').glob('*.json')):
   scope=episode.stem;base=out/'stores'/backend/scope
   phases=[('initial','native_once',base/'clean','initial')]
   for mode in pipeline.STORAGE_MODES:
    phases.extend([('cut-'+mode,mode,base/(mode+'-cut'),'retry'),('resume-'+mode,mode,base/mode,'retry')])
   for tag,mode,folder,action in phases:
    status=load(folder/(action+'_status.json'));receipts=load(folder/(action+'_receipts.json'));execution=load(out/'executions'/f'{backend}-{scope}-{tag}.json')
    native_metrics.append({'backend':backend,'scope':scope,'tag':tag,'mode':mode,'submitted_receipts':len(receipts),'receipt_outcomes':dict(collections.Counter(r['status'] for r in receipts)),
     'native_record_count_delta':status['after_count']-status['before_count'],'instrumented_application_phase_seconds':status['wall_seconds'],'whole_process_seconds':execution['wall_seconds']})
 pipeline.write(out/'native_phase_metrics.json',native_metrics)
 calibration=load(out/'grading_calibration_report.json')
 report={'phase':'Descriptive development pilot; NOT held-out confirmation or Q1-readiness evidence','grading_calibration':calibration,
  'semantic_claim_gate':'FAILED auxiliary calibration: task judgements exploratory; no definitive stale-state or semantic efficacy claim.' if calibration['status']!='PASS' else 'Authored calibration passed; same-family automated judgements remain unvalidated by humans.',
  'unique_request_status_counts':dict(transport_counts),'expected_unique_prompts':spec['unique_prompt_count'],'unique_questions':len(questions),'condition_observations':len(rows),'graded_unique_answer_question_pairs':len(decisions),'grade_failures':grade_failures,
  'summaries':summaries,'paired':paired,'clean_repeat_variation':clean_variation,
  'native_metrics':'native_phase_metrics.json: application phase includes native persistence and study witness export; whole-process time includes startup. Pure query application latency was not separately recorded. Record-count deltas are not physical disk-write counts.',
  'interpretation':'No p-values or population/IID interval; repetitions and shared-prompt aliases are dependent. Support annotations may be incomplete. Raw-document backends do not represent vendor inferred-memory defaults.'}
 pipeline.write(out/'observations.json',rows);pipeline.write(out/'pilot_summary.json',report)
 print(json.dumps({k:v for k,v in report.items() if k not in ('summaries','paired','grading_calibration')},indent=2))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();summarize(a.out.resolve())
