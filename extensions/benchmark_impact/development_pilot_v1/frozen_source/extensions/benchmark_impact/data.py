"""Pinned public benchmark adapters with a participant/evaluator boundary.

Raw benchmark files stay in an external cache. No project/company inputs are read.
Question labels and gold locations are never fields of a ParticipantEpisode.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from collections import Counter, defaultdict
import hashlib,json,re

PINNED={
 'locomo10.json':'79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4',
 'longmemeval_oracle.json':'821a2034d219ab45846873dd14c14f12cfe7776e73527a483f9dac095d38620c',
 'longmemeval_s_cleaned.json':'d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442'}

def digest_bytes(b):return hashlib.sha256(b).hexdigest()
def stable(*parts):return digest_bytes(json.dumps(parts,ensure_ascii=True,separators=(',',':')).encode())[:24]
def load_pinned(cache,name):
 p=Path(cache)/name;b=p.read_bytes()
 if digest_bytes(b)!=PINNED[name]:raise ValueError('Dataset digest differs: '+name)
 return json.loads(b)

@dataclass(frozen=True)
class Event:
 event_id:str
 source_id:str
 occurred_at:str
 speaker:str
 text:str
 def participant(self):return asdict(self)

@dataclass(frozen=True)
class ParticipantEpisode:
 scope:str
 events:tuple[Event,...]
 def participant(self):return {'scope':self.scope,'events':[e.participant() for e in self.events]}

@dataclass(frozen=True)
class EvaluationQuestion:
 key:str
 dataset:str
 group:str
 source_question_id:str
 question:str
 reference:str
 category:str
 expected_events:tuple[str,...]
 missing_gold_locations:tuple[str,...]
 unanswerable:bool
 episode_scope:str
 question_date:str

def make_event(dataset,source,turn,date,speaker,text):
 # IDs name occurrences, not literal content. Same-text independent turns differ.
 return Event(stable('event',dataset,source,turn),stable('source',dataset,source),str(date),str(speaker),str(text))

def locomo_rows(rows):
 episodes={};questions=[]
 for row in rows:
  sid=row['sample_id'];conv=row['conversation'];events=[];locations={}
  keys=sorted((k for k,v in conv.items() if re.fullmatch(r'session_\d+',k) and isinstance(v,list)),key=lambda x:int(x.split('_')[-1]))
  for sess in keys:
   date=conv[sess+'_date_time']
   for i,turn in enumerate(conv[sess]):
    text=str(turn['text'])
    if isinstance(turn.get('blip_caption'),str) and turn['blip_caption'].strip():text+='\nReleased image caption: '+turn['blip_caption']
    e=make_event('locomo',sid+'/'+sess,turn['dia_id'],date,turn['speaker'],text);events.append(e)
    if turn['dia_id'] in locations:raise ValueError('Duplicate LoCoMo dialog identity')
    locations[turn['dia_id']]=e.event_id
  scope=stable('scope','locomo',sid);episodes[scope]=ParticipantEpisode(scope,tuple(events))
  for i,q in enumerate(row['qa']):
   unanswerable=int(q['category'])==5
   # adversarial_answer is a distractor, never a reference correctness label.
   reference='Not mentioned in the conversation.' if unanswerable else str(q['answer'])
   raw=[str(v).strip() for v in q.get('evidence',[])]
   questions.append(EvaluationQuestion(stable('question','locomo',sid,i),'locomo',sid,str(i),str(q['question']),reference,str(q['category']),tuple(locations[v] for v in raw if v in locations),tuple(v for v in raw if v not in locations),unanswerable,scope,''))
 return episodes,questions

def evidence_components(rows):
 parent={r['question_id']:r['question_id'] for r in rows};seen={}
 def find(x):
  while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
  return x
 for r in rows:
  for sid in r['answer_session_ids']:
   if sid in seen:parent[find(r['question_id'])]=find(seen[sid])
   else:seen[sid]=r['question_id']
 groups=defaultdict(list)
 for key in parent:groups[find(key)].append(key)
 return {key:stable('lme-evidence-component',*sorted(members)) for members in groups.values() for key in members}

def lme_rows(rows,groups):
 episodes={};questions=[]
 for r in rows:
  qid=r['question_id'];events=[];gold=[];known=set()
  if not (len(r['haystack_session_ids'])==len(r['haystack_dates'])==len(r['haystack_sessions'])):raise ValueError('Unaligned sessions')
  for position,(sid,date,turns) in enumerate(zip(r['haystack_session_ids'],r['haystack_dates'],r['haystack_sessions'])):
   occurrence=stable('history-occurrence',qid,position,sid)
   for i,turn in enumerate(turns):
    e=make_event('longmemeval',occurrence,i,date,turn['role'],turn['content']);events.append(e);known.add(sid)
    if turn.get('has_answer') is True:gold.append(e.event_id)
  scope=stable('scope','longmemeval',qid);episodes[scope]=ParticipantEpisode(scope,tuple(events))
  # Session-level references remain evaluator-only if no turn flag is provided.
  if not gold:
   wanted={stable('source','longmemeval',stable('history-occurrence',qid,j,sid)) for j,sid in enumerate(r['haystack_session_ids']) if sid in r['answer_session_ids']}
   gold=[e.event_id for e in events if e.source_id in wanted]
  missing=tuple(str(s) for s in r['answer_session_ids'] if s not in known)
  questions.append(EvaluationQuestion(stable('question','longmemeval',qid),'longmemeval',groups[qid],qid,str(r['question']),str(r['answer']),str(r['question_type']),tuple(gold),missing,qid.endswith('_abs'),scope,str(r['question_date'])))
 return episodes,questions

def select_development(locomo_questions,lme_questions):
 locomo_groups=sorted({q.group for q in locomo_questions},key=lambda x:stable('development-v1',x))[:2]
 chosen=[]
 for group in locomo_groups:
  for category in ('1','2','4'):
   pool=sorted((q for q in locomo_questions if q.group==group and q.category==category and not q.missing_gold_locations),key=lambda q:stable('pilot-v1',q.key))
   chosen.extend(pool[:2])
 dev_lme=[]
 for cat in sorted({q.category for q in lme_questions}):
  pool=sorted((q for q in lme_questions if q.category==cat and not q.missing_gold_locations),key=lambda q:stable('development-v1',q.group,q.key))
  groups=[]
  for q in pool:
   if q.group not in groups:groups.append(q.group)
   if len(groups)==2:break
  dev_lme.extend(groups)
  chosen.extend(next(q for q in pool if q.group==g) for g in groups)
 dev_lme=set(dev_lme)
 held=[q.key for q in locomo_questions if q.group not in locomo_groups]+[q.key for q in lme_questions if q.group not in dev_lme]
 return chosen,{'locomo_development_conversations':locomo_groups,'lme_development_evidence_components':sorted(dev_lme),'development_question_keys':[q.key for q in chosen],'held_out_question_keys':held}

def corpus(cache,lme_variant='full'):
 if lme_variant not in ('full','oracle'):raise ValueError('Unknown LongMemEval variant')
 loc=load_pinned(cache,'locomo10.json');oracle=load_pinned(cache,'longmemeval_oracle.json')
 lme=load_pinned(cache,'longmemeval_s_cleaned.json' if lme_variant=='full' else 'longmemeval_oracle.json')
 groups=evidence_components(oracle);le,lq=locomo_rows(loc);me,mq=lme_rows(lme,groups)
 selected,split=select_development(lq,mq)
 return {**le,**me},lq+mq,selected,split

def audit(cache):
 episodes,questions,pilot,split=corpus(cache)
 problems=[]
 for ep in episodes.values():
  seen={}
  for e in ep.events:
   if set(e.participant())!={'event_id','source_id','occurred_at','speaker','text'}:problems.append('Participant field leak')
   if e.event_id in seen:problems.append('Repeated participant occurrence identity')
   seen[e.event_id]=e.participant()
 groups={q.group for q in pilot};held={q.group for q in questions if q.key in set(split['held_out_question_keys'])}
 if groups&held:problems.append('Development/held-out evidence cluster overlap')
 return {'status':'PASS' if not problems else 'FAIL','errors':problems,'datasets':dict(Counter(q.dataset for q in questions)),
  'episodes':len(episodes),'pilot_questions':len(pilot),'pilot_categories':dict(Counter(q.dataset+'/'+q.category for q in pilot)),
  'lme_evidence_components':len({q.group for q in questions if q.dataset=='longmemeval'}),'development_groups':len(groups),'held_out_questions':len(split['held_out_question_keys']),
  'missing_gold_location_questions':dict(Counter(q.dataset for q in questions if q.missing_gold_locations)),
  'input_hashes':PINNED,'split':split,'model_observations':0,'variant':'Full cleaned LongMemEval-S, not oracle histories'}

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--cache',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args()
 x=audit(a.cache);a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(x,indent=2)+'\n')
 print(json.dumps({k:v for k,v in x.items() if k not in ('split','input_hashes')},indent=2))
 if x['status']!='PASS':raise SystemExit(1)
