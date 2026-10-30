"""Independent source/projection auditor for the new benchmark-impact study.

Reads public pinned data only, invokes the adapter under test, and derives its
mapping, collision and split checks independently. No model/native memory API.
Reports contain source hashes/counts, never upstream conversation text.
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
EXPECTED_HASHES={
 'locomo10.json':'79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4',
 'longmemeval_oracle.json':'821a2034d219ab45846873dd14c14f12cfe7776e73527a483f9dac095d38620c',
 'longmemeval_s_cleaned.json':'d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442'}
EVENT_FIELDS={'event_id','source_id','occurred_at','speaker','text'}

class AuditError(ValueError):pass

def require(condition,message):
 if not condition:raise AuditError(message)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'))
def read_pinned(cache):
 result={}
 for name,expected in EXPECTED_HASHES.items():
  path=Path(cache)/name;require(sha(path)==expected,'Public input digest differs: '+name)
  result[name]=json.loads(path.read_text())
 return result

def validate_payload(payload):
 require(set(payload)=={'scope','events'},'Participant episode contains evaluator/unknown fields')
 require(isinstance(payload['scope'],str) and re.fullmatch(r'[0-9a-f]{24}',payload['scope']) is not None,'Invalid opaque participant scope')
 require(isinstance(payload['events'],list),'Events must be a list')
 seen={}
 for event in payload['events']:
  require(set(event)==EVENT_FIELDS,'Participant event contains evaluator/unknown fields')
  require(all(isinstance(event[key],str) for key in EVENT_FIELDS),'Participant event fields must be scalar strings')
  require(all(re.fullmatch(r'[0-9a-f]{24}',event[key]) is not None for key in ('event_id','source_id')),'Participant identity is not the declared opaque encoding')
  identity=event['event_id']
  require(identity not in seen,'Repeated participant event identity'+(' with conflicting payload' if identity in seen and seen[identity]!=event else ''))
  seen[identity]=event
 return True

def validate_support_metric(question,positive_support_coverage):
 """Retained upstream antecedent references are not positive answer support."""
 if question.unanswerable or question.missing_gold_locations:
  require(positive_support_coverage is None,'Unanswerable/missing-gold evidence cannot receive positive-support coverage')
 else:
  require(positive_support_coverage is None or (type(positive_support_coverage) in (int,float) and 0<=positive_support_coverage<=1),'Invalid positive-support coverage')
 return True

def validate_alignment(payload,raw):
 """raw entries are (source occurrence, date, speaker, text), in source order."""
 validate_payload(payload)
 require(len(payload['events'])==len(raw),'Projection changed source turn count')
 source_to_id={};id_to_source={}
 for event,(source,date,speaker,text) in zip(payload['events'],raw):
  require((event['occurred_at'],event['speaker'],event['text'])==(str(date),str(speaker),str(text)),
          'Participant date/speaker/text/order differs from selected raw history')
  if source in source_to_id:require(source_to_id[source]==event['source_id'],'One source occurrence has multiple source IDs')
  if event['source_id'] in id_to_source:require(id_to_source[event['source_id']]==source,'Different source occurrences share a participant source identity')
  source_to_id[source]=event['source_id'];id_to_source[event['source_id']]=source
 return True

def locomo_flat(row):
 conv=row['conversation'];raw=[];locations={}
 sessions=sorted((k for k in conv if re.fullmatch(r'session_\d+',k)),key=lambda k:int(k.split('_')[1]))
 for session in sessions:
  for turn in conv[session]:
   require(turn['dia_id'] not in locations,'Raw LoCoMo dialog identifier is repeated')
   locations[turn['dia_id']]=len(raw)
   text=str(turn['text']);caption=turn.get('blip_caption')
   if isinstance(caption,str) and caption.strip():text+='\nReleased image caption: '+caption
   raw.append(((row['sample_id'],session),conv[session+'_date_time'],turn['speaker'],text))
 return raw,locations

def lme_flat(row):
 require(len(row['haystack_dates'])==len(row['haystack_session_ids'])==len(row['haystack_sessions']),'Raw LME session lists are unaligned')
 return [((row['question_id'],index,sid),date,turn['role'],turn['content'])
  for index,(sid,date,turns) in enumerate(zip(row['haystack_session_ids'],row['haystack_dates'],row['haystack_sessions']))
  for turn in turns]

def component_partition(rows,field):
 require(len({r['question_id'] for r in rows})==len(rows),'Repeated raw question ID')
 parent={r['question_id']:r['question_id'] for r in rows};seen={}
 def find(key):
  while parent[key]!=key:parent[key]=parent[parent[key]];key=parent[key]
  return key
 for row in rows:
  for sid in set(row[field]):
   if sid in seen:parent[find(row['question_id'])]=find(seen[sid])
   else:seen[sid]=row['question_id']
 groups=defaultdict(set)
 for key in parent:groups[find(key)].add(key)
 return {frozenset(group) for group in groups.values()}

def split_observations(rows,questions,split):
 byqid={row['question_id']:row for row in rows};bykey={q.key:q for q in questions}
 require(len(bykey)==len(questions),'Evaluation question key collision')
 devgroups=set(split['lme_development_evidence_components'])
 dev={q.source_question_id for q in questions if q.dataset=='longmemeval' and q.group in devgroups}
 declared_held={bykey[key].source_question_id for key in split['held_out_question_keys'] if bykey[key].dataset=='longmemeval'}
 held={q.source_question_id for q in questions if q.dataset=='longmemeval' and q.group not in devgroups}
 require(declared_held<=held,'Declared held-out question is outside the gold-component holdout')
 require(not(dev&held),'Development question appears in held-out set')
 dev_sources={sid for qid in dev for sid in byqid[qid]['haystack_session_ids']}
 held_sources={sid for qid in held for sid in byqid[qid]['haystack_session_ids']}
 dev_gold={sid for qid in dev for sid in byqid[qid]['answer_session_ids']}
 held_gold={sid for qid in held for sid in byqid[qid]['answer_session_ids']}
 require(not(dev_gold&held_gold),'Development and held-out answer-source overlap')
 excluded={qid for qid in held if dev_sources.intersection(byqid[qid]['haystack_session_ids'])}
 strict=held-excluded
 return dict(development_questions=len(dev),held_out_gold_component_questions=len(held),declared_held_out_questions=len(declared_held),
  shared_full_history_session_ids=len(dev_sources&held_sources),shared_gold_session_ids=len(dev_gold&held_gold),
  full_history_overlap_held_questions=len(excluded),strict_source_disjoint_candidate_questions=len(strict),
  strict_candidate_categories=dict(Counter(byqid[qid]['question_type'] for qid in strict)),
  strict_candidate_abstention_questions=sum(qid.endswith('_abs') for qid in strict),
  strict_candidate_question_ids=sorted(strict),excluded_due_to_development_source_overlap_question_ids=sorted(excluded),
  interpretation='Gold-evidence components and full-history source overlap are different partitions. Strict candidates exclude all overlap with development, not overlap among confirmation questions.')

def source_observations(oracle,full):
 old={r['question_id']:r for r in oracle};new={r['question_id']:r for r in full}
 require(len(old)==len(oracle) and len(new)==len(full) and set(old)==set(new),'Oracle/full question identities differ or repeat')
 for qid,row in new.items():
  for key in ('question','answer','question_type'):require(row[key]==old[qid][key],'Oracle/full question metadata differs: '+key)
  require(set(row['answer_session_ids'])==set(old[qid]['answer_session_ids']),'Oracle/full answer-session set differs')
 repeated=Counter();cross=Counter();by_sid={};matched=Counter();raw_duplicates=[]
 for qid,row in new.items():
  seen={};seen_sessions=set();orow=old[qid];oracle_sessions={sid:(date,turns) for sid,date,turns in zip(orow['haystack_session_ids'],orow['haystack_dates'],orow['haystack_sessions'])}
  for sid,date,turns in zip(row['haystack_session_ids'],row['haystack_dates'],row['haystack_sessions']):
   if sid in seen_sessions:repeated['repeated_session_occurrences']+=1
   seen_sessions.add(sid)
   normalized=[(turn['role'],turn['content']) for turn in turns];serialized=canonical(normalized)
   if sid in by_sid:
    cross['reused_session_occurrences']+=1;cross['reused_session_date_mismatches']+=by_sid[sid][0]!=date;cross['reused_session_content_mismatches']+=by_sid[sid][1]!=serialized
   else:by_sid[sid]=(date,serialized)
   if sid in oracle_sessions:
    odate,oturns=oracle_sessions[sid];matched['matched_session_occurrences']+=1;matched['oracle_full_session_date_mismatches']+=odate!=date
    matched['oracle_full_session_content_mismatches']+=normalized!=[(t['role'],t['content']) for t in oturns]
   for index,turn in enumerate(turns):
    key=(sid,index);payload=(date,turn['role'],turn['content'])
    if key in seen:
     repeated['repeated_global_sid_turn_occurrences']+=1
     repeated['conflicting_global_sid_turn_occurrences']+=seen[key]!=payload
     if len(raw_duplicates)<3:raw_duplicates.append(dict(question_id=qid,upstream_session_id=sid,turn_index=index,first_date=seen[key][0],later_date=date))
    else:seen[key]=payload
 return dict(questions=len(full),unique_upstream_session_ids=len(by_sid),
  oracle_full_question_date_mismatches=sum(row['question_date']!=old[qid]['question_date'] for qid,row in new.items()),
  oracle_full_answer_session_set_mismatches=0,oracle_full_answer_session_list_order_mismatches=sum(row['answer_session_ids']!=old[qid]['answer_session_ids'] for qid,row in new.items()),
  within_question_reused_raw_identity=dict(repeated),cross_question_reuse=dict(cross),oracle_full_session_comparison=dict(matched),
  identity_collision_metadata_examples=raw_duplicates,
  gold_evidence_components=len(component_partition(full,'answer_session_ids')),
  all_history_overlap_component_sizes=sorted(map(len,component_partition(full,'haystack_session_ids')),reverse=True))

def run(cache):
 try:from . import data
 except ImportError:import data
 adapter_before=sha(HERE/'data.py');raw=read_pinned(cache)
 locomo=raw['locomo10.json'];oracle=raw['longmemeval_oracle.json'];full=raw['longmemeval_s_cleaned.json']
 episodes,questions,selected,split=data.corpus(cache,'full');issues=[];counts=Counter()
 lq=defaultdict(list);mq={}
 for q in questions:
  if q.dataset=='locomo':lq[q.group].append(q)
  else:require(q.source_question_id not in mq,'Repeated adapted LME question');mq[q.source_question_id]=q
 require(len(episodes)==len(locomo)+len(full),'Adapter episode cardinality differs')
 for row in locomo:
  raw_events,locations=locomo_flat(row);qs=lq[row['sample_id']]
  require(len(qs)==len(row['qa']),'LoCoMo question count differs');payload=episodes[qs[0].episode_scope].participant()
  try:validate_alignment(payload,raw_events)
  except AuditError as error:issues.append(dict(dataset='locomo',scope=qs[0].episode_scope,issue=str(error)))
  for index,q in enumerate(qs):
   source=row['qa'][index];unanswerable=int(source['category'])==5
   require(q.source_question_id==str(index) and q.question==source['question'] and q.category==str(source['category']),'LoCoMo evaluation mapping differs')
   require(q.unanswerable==unanswerable,'LoCoMo adversarial label differs')
   if unanswerable:
    require(q.reference=='Not mentioned in the conversation.' and q.reference!=source['adversarial_answer'],'LoCoMo distractor was used as gold reference');counts['locomo_category5_not_distractor_gold']+=1
   else:require(q.reference==str(source['answer']),'LoCoMo reference differs')
   wanted=tuple(payload['events'][locations[str(v).strip()]]['event_id'] for v in source.get('evidence',[]) if str(v).strip() in locations)
   missing=tuple(str(v).strip() for v in source.get('evidence',[]) if str(v).strip() not in locations)
   require(q.expected_events==wanted and q.missing_gold_locations==missing,'LoCoMo evidence projection differs')
  counts['locomo_episodes']+=1;counts['locomo_events']+=len(raw_events)
 for row in full:
  q=mq[row['question_id']];payload=episodes[q.episode_scope].participant()
  try:validate_alignment(payload,lme_flat(row))
  except AuditError as error:issues.append(dict(dataset='longmemeval',source_question_id=q.source_question_id,issue=str(error)))
  require(q.question==row['question'] and q.reference==str(row['answer']) and q.category==row['question_type'] and q.unanswerable==q.source_question_id.endswith('_abs'),'LME evaluation mapping differs')
  if not hasattr(q,'question_date') or q.question_date!=row['question_date']:issues.append(dict(dataset='longmemeval',source_question_id=q.source_question_id,issue='Full-row question_date absent or mismatched in query/evaluator interface'))
  flagged=[];by_answer_session=[];offset=0
  for sid,turns in zip(row['haystack_session_ids'],row['haystack_sessions']):
   for turn in turns:
    event_id=payload['events'][offset]['event_id'];offset+=1
    if turn.get('has_answer') is True:flagged.append(event_id)
    if sid in set(row['answer_session_ids']):by_answer_session.append(event_id)
  require(q.expected_events==tuple(flagged or by_answer_session),'LME evaluator-only gold event mapping differs')
  require(q.missing_gold_locations==tuple(str(s) for s in row['answer_session_ids'] if s not in set(row['haystack_session_ids'])),'LME missing evidence-session mapping differs')
  counts['lme_episodes']+=1;counts['lme_events']+=offset
 adapted=defaultdict(set)
 for qid,q in mq.items():adapted[q.group].add(qid)
 require({frozenset(v) for v in adapted.values()}==component_partition(full,'answer_session_ids'),'Adapter evidence component partition differs from full answer-source overlap')
 observed=source_observations(oracle,full);observed_split=split_observations(full,questions,split)
 require(sha(HERE/'data.py')==adapter_before,'Adapter changed during this audit; rerun on one source version')
 return dict(status='PASS' if not issues else 'BLOCK_PILOT_FREEZE',adapter_sha256=adapter_before,auditor_sha256=sha(__file__),input_sha256=EXPECTED_HASHES,
  missing_gold_location_questions=dict(Counter(q.dataset for q in questions if q.missing_gold_locations)),
  missing_gold_location_references=dict(Counter(q.dataset for q in questions for _ in q.missing_gold_locations)),
  released_locomo_captions=sum(isinstance(turn.get('blip_caption'),str) and bool(turn['blip_caption'].strip()) for row in locomo for key,value in row['conversation'].items() if re.fullmatch(r'session_\d+',key) for turn in value),
  model_calls=0,raw_data_redistributed=False,published_v0_3_0_modified=False,projection_counts=dict(counts),projection_findings=issues,
  source_observations=observed,development_split=observed_split,
  scope='Same-study independent mapping/status checks and source measurements, not outside replication, model observations, grading or confirmatory effects.',
  evaluator_warning='Unanswerable/adversarial antecedent locations must not be treated as positive answer support or a substitute for abstention scoring.')

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--cache',type=Path,required=True);parser.add_argument('--report',type=Path,required=True);args=parser.parse_args()
 result=run(args.cache);args.report.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
 print(json.dumps({k:v for k,v in result.items() if k not in ('development_split','projection_findings','input_sha256')},indent=2))
 if result['projection_findings']:raise SystemExit(1)
