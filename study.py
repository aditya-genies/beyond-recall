#!/usr/bin/env python3
"""Standalone synthetic study of decision replay, effect addresses and receipts.
Uses only Python's standard library. No service or proprietary source is loaded.
"""
from __future__ import annotations
import argparse, concurrent.futures, contextlib, hashlib, itertools, json, os, secrets
import sqlite3, subprocess, sys, time
from pathlib import Path

HISTORIES = (
 'normal','redelivery_fixed','redelivery_drift',
 'exit_after_prepare_fixed','exit_after_prepare_drift',
 'exit_after_first_put_fixed','exit_after_first_put_drift',
 'lost_put_reply_fixed','lost_put_reply_drift',
 'exit_after_effects_fixed','exit_after_effects_drift',
 'exit_after_finalize_drift','bounded_input','superseded_input',
 'reset_before_retry','reset_during_effects','lost_delete_reply')
PROFILES = ('insert','revise','retire','mixed')
FACTS = ['tone=concise','unit=metric','topic=cycling']
POLICIES = [f'D{d}P{p}R{r}' for d,p,r in itertools.product((0,1),repeat=3)]


def js(x): return json.dumps(x,sort_keys=True,separators=(',',':'))
def fingerprint(x): return hashlib.sha256(js(x).encode()).hexdigest()
def flags(policy): return tuple(policy[i]=='1' for i in (1,3,5))
def db(path):
 c=sqlite3.connect(str(path),timeout=20)
 c.execute('PRAGMA synchronous=FULL')
 c.execute('PRAGMA journal_mode=DELETE')
 return c

@contextlib.contextmanager
def managed_db(path):
 c=db(path)
 try:
  with c:yield c
 finally:c.close()

def emit(event,**kw): print(js(dict(event=event,**kw)),flush=True)

def setup(folder,profile,history):
 folder.mkdir(parents=True,exist_ok=False)
 with managed_db(folder/'recovery.sqlite') as c:
  c.executescript('CREATE TABLE epoch_state (epoch INTEGER); INSERT INTO epoch_state VALUES(0);\nCREATE TABLE conversation(turn INTEGER,enabled INTEGER,epoch INTEGER,facts TEXT);\nCREATE TABLE decisions(intent TEXT PRIMARY KEY,epoch INTEGER,body TEXT);\nCREATE TABLE receipts(intent TEXT PRIMARY KEY,epoch INTEGER,decision TEXT,outcome TEXT);')
  c.execute('INSERT INTO conversation VALUES(1,1,0,?)',(js(FACTS),))
  if history=='bounded_input': c.execute('INSERT INTO conversation VALUES(2,1,0,?)',(js(['topic=future']),))
  if history=='superseded_input':
   c.execute('UPDATE conversation SET turn=0')
   c.execute('INSERT INTO conversation VALUES(1,0,0,?)',(js(['topic=retracted']),))
 with managed_db(folder/'effects.sqlite') as c:
  c.executescript('CREATE TABLE records(address TEXT PRIMARY KEY,fact TEXT,origin TEXT,epoch INTEGER);\nCREATE TABLE committed_actions(serial INTEGER PRIMARY KEY AUTOINCREMENT,attempt INTEGER,kind TEXT,address TEXT,fact TEXT,origin TEXT,epoch INTEGER);')
  if profile in ('revise','mixed'):c.execute('INSERT INTO records VALUES(?,?,?,0)',('existing-unit','unit=imperial','fixture'))
  if profile in ('retire','mixed'):c.execute('INSERT INTO records VALUES(?,?,?,0)',('retired-entry','obsolete=yes','fixture'))

def rows(folder):
 with managed_db(folder/'effects.sqlite') as c:return [dict(zip(('address','fact','origin','epoch'),x)) for x in c.execute('SELECT * FROM records ORDER BY address')]

def reset(folder,residue):
 with managed_db(folder/'recovery.sqlite') as c:c.execute('UPDATE epoch_state SET epoch=1')
 with managed_db(folder/'effects.sqlite') as c:
  c.execute("DELETE FROM records WHERE origin='fixture'" if residue else 'DELETE FROM records')

def make_plan(facts,profile,alternative):
 latest={f.split('=',1)[0]:f for f in facts}
 facts=list(latest.values())
 if alternative:facts=[('topic=running' if f.startswith('topic=') else f) for f in facts]
 put=lambda f,target=None:dict(kind='put',fact=f,target=target)
 tone=next(f for f in facts if f.startswith('tone=')); unit=next(f for f in facts if f.startswith('unit=')); topic=next(f for f in facts if f.startswith('topic='))
 if profile=='insert':return [put(tone),put(unit),put(topic)]
 if profile=='revise':return [put(unit,'existing-unit'),put(tone),put(topic)]
 if profile=='retire':return [dict(kind='delete',target='retired-entry'),put(tone),put(unit),put(topic)]
 return [put(unit,'existing-unit'),put(tone),dict(kind='delete',target='retired-entry'),put(topic)]

def worker(a):
 folder=Path(a.directory); D,P,R=flags(a.policy); intent='intent-alpha'; epoch=0
 c=db(folder/'recovery.sqlite');e=db(folder/'effects.sqlite')
 def current():return c.execute('SELECT epoch FROM epoch_state').fetchone()[0]
 def cleanup():
  with e:e.execute('DELETE FROM records WHERE origin=? AND epoch=?',(intent,epoch))
  emit('cleanup',intent=intent,epoch=epoch)
 def die(point):
  if a.fault==point:emit('abrupt_exit',point=point);os._exit(87)
 try:
  if current()!=epoch:
   cleanup();emit('ack',intent=intent,outcome='cancelled');return 0
  if R:
   receipt=c.execute('SELECT outcome FROM receipts WHERE intent=? AND epoch=?',(intent,epoch)).fetchone()
   if receipt:emit('receipt_hit',intent=intent);emit('ack',intent=intent,outcome=receipt[0]);return 0
  saved=c.execute('SELECT body FROM decisions WHERE intent=? AND epoch=?',(intent,epoch)).fetchone() if P else None
  if saved:
   plan=json.loads(saved[0]);emit('decision_loaded',intent=intent,digest=fingerprint(plan))
  else:
   # This actual query is identical for every factorial variant.
   source=c.execute('SELECT facts FROM conversation WHERE enabled=1 AND epoch=? AND turn<=? ORDER BY turn',(epoch,1)).fetchall()
   facts=[f for x in source for f in json.loads(x[0])]
   emit('source_selected',intent=intent,facts=facts)
   plan=make_plan(facts,a.profile,a.alternative)
   emit('decision_chosen',intent=intent,digest=fingerprint(plan),operations=plan)
   die('before_decision_store')
   if P:
    with c:c.execute('INSERT INTO decisions VALUES(?,?,?)',(intent,epoch,js(plan)))
    emit('decision_stored',intent=intent,digest=fingerprint(plan))
  die('after_prepare')
  put_count=0
  for slot,op in enumerate(plan):
   if op['kind']=='put':
    target=op['target'] or (hashlib.sha256(f'{intent}|slot={slot}'.encode()).hexdigest()[:24] if D else secrets.token_hex(12))
    with e:
     e.execute('INSERT OR REPLACE INTO records VALUES(?,?,?,?)',(target,op['fact'],intent,epoch))
     e.execute('INSERT INTO committed_actions(attempt,kind,address,fact,origin,epoch) VALUES(?,?,?,?,?,?)',(a.attempt,'put',target,op['fact'],intent,epoch))
    put_count+=1;emit('effect_committed',intent=intent,slot=slot,kind='put',address=target,fact=op['fact'])
    if put_count==1:
     die('after_first_put')
     if a.fault=='lost_put_reply':raise RuntimeError('controlled committed put with unavailable reply')
     if a.fault=='reset_handshake':
      (folder/'reset-ready').write_text('ready')
      deadline=time.monotonic()+15
      while not (folder/'reset-continue').exists():
       if time.monotonic()>deadline:raise RuntimeError('reset handshake timeout')
       time.sleep(.005)
   else:
    target=op['target']
    with e:
     e.execute('DELETE FROM records WHERE address=?',(target,))
     e.execute('INSERT INTO committed_actions(attempt,kind,address,fact,origin,epoch) VALUES(?,?,?,?,?,?)',(a.attempt,'delete',target,None,intent,epoch))
    emit('effect_committed',intent=intent,slot=slot,kind='delete',address=target)
    if a.fault=='lost_delete_reply':raise RuntimeError('controlled committed delete with unavailable reply')
  if current()!=epoch:
   cleanup();outcome='cancelled'
  else:outcome='applied'
  die('after_effects')
  if R:
   with c:c.execute('INSERT OR REPLACE INTO receipts VALUES(?,?,?,?)',(intent,epoch,fingerprint(plan),outcome))
   emit('receipt_stored',intent=intent)
  # Retain any decision for BOTH R settings: receipt never changes retention.
  die('after_finalize')
  emit('ack',intent=intent,outcome=outcome);return 0
 except Exception as exc:
  emit('attempt_failed',error=str(exc));return 74
 finally:c.close();e.close()

def invoke(folder,policy,profile,attempt,fault='',alternative=False):
 cmd=[sys.executable,str(Path(__file__).resolve()),'worker','--directory',str(folder),'--policy',policy,'--profile',profile,'--attempt',str(attempt),'--fault',fault]
 if alternative:cmd.append('--alternative')
 proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 if fault=='reset_handshake':
  end=time.monotonic()+18
  while not (folder/'reset-ready').exists() and proc.poll() is None:
   if time.monotonic()>end:proc.kill();raise RuntimeError('parent reset handshake timed out')
   time.sleep(.005)
  if (folder/'reset-ready').exists():reset(folder,False);(folder/'reset-continue').write_text('continue')
 out,err=proc.communicate(timeout=25)
 events=[json.loads(line) for line in out.splitlines() if line.strip()]
 return dict(attempt=attempt,returncode=proc.returncode,fault=fault,alternative=alternative,events=events,stderr=err,acknowledged=proc.returncode==0 and any(x['event']=='ack' for x in events))

def metrics(folder,attempts,expected):
 physical=rows(folder); facts={x['fact'] for x in physical}; expected=set(expected)
 by_intent={}
 for attempt in attempts:
  for x in attempt['events']:
   if x['event'] in ('decision_chosen','decision_loaded'):by_intent.setdefault(x['intent'],[]).append(x['digest'])
 continuity=all(len(set(v))<=1 for v in by_intent.values())
 ack=bool(attempts[-1]['acknowledged'])
 with managed_db(folder/'effects.sqlite') as c:commits=[dict(zip(('serial','attempt','kind','address','fact','origin','epoch'),x)) for x in c.execute('SELECT * FROM committed_actions ORDER BY serial')]
 chosen=sum(x['event']=='decision_chosen' for a in attempts for x in a['events'])
 content=facts==expected;cardinality=len(physical)==len(expected)
 return dict(expected_facts=sorted(expected),physical_records=physical,content_correct=content,cardinality_correct=cardinality,acknowledged=ack,selected_terminal=content and cardinality and ack,decision_continuity=continuity,planning_invocations=chosen,committed_effect_calls=len(commits),committed_actions=commits,attempts=attempts)

def run_case(root,policy,profile,history):
 folder=root/'state'/f'{policy}__{profile}__{history}';setup(folder,profile,history)
 fault=''
 if history.startswith('exit_after_prepare'):fault='after_prepare'
 if history.startswith('exit_after_first_put') or history=='reset_before_retry':fault='after_first_put'
 if history.startswith('lost_put_reply'):fault='lost_put_reply'
 if history.startswith('exit_after_effects'):fault='after_effects'
 if history.startswith('exit_after_finalize'):fault='after_finalize'
 if history=='reset_during_effects':fault='reset_handshake'
 if history=='lost_delete_reply':fault='lost_delete_reply'
 attempts=[invoke(folder,policy,profile,0,fault)]
 if history=='reset_before_retry':reset(folder,True)
 repeat=history.startswith('redelivery') or not attempts[0]['acknowledged']
 if repeat:attempts.append(invoke(folder,policy,profile,1,alternative='drift' in history))
 expected=[] if history.startswith('reset_') else FACTS
 return dict(policy=policy,profile=profile,history=history,**metrics(folder,attempts,expected))

def summarize(cases):
 result=[]
 for policy in POLICIES:
  group=[x for x in cases if x['policy']==policy]
  result.append(dict(policy=policy,structural_cases=len(group),content_pass=sum(x['content_correct'] for x in group),cardinality_pass=sum(x['cardinality_correct'] for x in group),selected_terminal_pass=sum(x['selected_terminal'] for x in group),decision_continuity_pass=sum(x['decision_continuity'] for x in group),acknowledged=sum(x['acknowledged'] for x in group),planning_invocations=sum(x['planning_invocations'] for x in group),committed_effect_calls=sum(x['committed_effect_calls'] for x in group),process_attempts=sum(len(x['attempts']) for x in group),abrupt_exits=sum(a['returncode']==87 for x in group for a in x['attempts'])))
 return result

def boundary_probes(out):
 reports=[];p='D1P1R1';profile='mixed'
 for deletion in ('receipt_only','decision_only','both'):
  f=out/'boundary_state'/deletion;setup(f,profile,'normal');attempts=[invoke(f,p,profile,0)]
  with managed_db(f/'recovery.sqlite') as c:
   if deletion in ('receipt_only','both'):c.execute('DELETE FROM receipts')
   if deletion in ('decision_only','both'):c.execute('DELETE FROM decisions')
  attempts.append(invoke(f,p,profile,1,alternative=True));reports.append(dict(probe=deletion,**metrics(f,attempts,FACTS)))
 f=out/'boundary_state'/'before_decision_store';setup(f,profile,'normal');attempts=[invoke(f,p,profile,0,'before_decision_store'),invoke(f,p,profile,1,alternative=True)];reports.append(dict(probe='before_decision_store',outside_prepared_decision_guarantee=True,**metrics(f,attempts,FACTS)))
 f=out/'boundary_state'/'external_interleaving';setup(f,profile,'normal');attempts=[invoke(f,p,profile,0,'after_first_put')]
 with managed_db(f/'effects.sqlite') as c:c.execute("UPDATE records SET fact='unit=newer-external-value' WHERE address='existing-unit'")
 attempts.append(invoke(f,p,profile,1));m=metrics(f,attempts,FACTS);reports.append(dict(probe='external_interleaving',newer_external_write_preserved=any(x['fact']=='unit=newer-external-value' for x in m['physical_records']),**m))
 (out/'boundary_probes.json').write_text(json.dumps(reports,indent=2)+'\n')
 return reports

def campaign(a):
 root=Path(a.out);root.mkdir(parents=True,exist_ok=True)
 if (root/'cases.jsonl').exists():raise RuntimeError('Refusing to replace an existing campaign')
 tasks=[(p,q,h) for p in POLICIES for q in PROFILES for h in HISTORIES if h!='lost_delete_reply' or q in ('retire','mixed')]
 spec=dict(policies=POLICIES,histories=HISTORIES,profiles=PROFILES,structural_cases=len(tasks),source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),plan_retention='Plans retained after completion for both receipt settings',seed_data=FACTS,python=sys.version.split()[0],sqlite=sqlite3.sqlite_version,clock='finite specified schedules; no statistical sampling',power_loss_tested=False,effect_call_definition='Committed participant put/delete operations; excludes reset and cleanup SQL mutations',source_control_definition='Latest selected fact per attribute; bounded and disabled-source controls affect the decision if their filters are removed')
 (root/'frozen_spec.json').write_text(json.dumps(spec,indent=2)+'\n')
 print('FROZEN',len(tasks),'structural cases',spec['source_sha256'],flush=True)
 cases=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as ex:
  future={ex.submit(run_case,root,*t):t for t in tasks}
  for f in concurrent.futures.as_completed(future):
   cases.append(f.result())
   if len(cases)%64==0:print('completed',len(cases),flush=True)
 cases.sort(key=lambda x:(x['policy'],x['profile'],x['history']))
 (root/'cases.jsonl').write_text(''.join(js(x)+'\n' for x in cases))
 summary=summarize(cases);(root/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
 boundary_probes(root)
 print(json.dumps(summary,indent=2))

if __name__=='__main__':
 p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
 q=sub.add_parser('worker');q.add_argument('--directory',required=True);q.add_argument('--policy',required=True,choices=POLICIES);q.add_argument('--profile',required=True,choices=PROFILES);q.add_argument('--attempt',type=int,required=True);q.add_argument('--fault',default='');q.add_argument('--alternative',action='store_true')
 q=sub.add_parser('campaign');q.add_argument('--out',required=True);q.add_argument('--workers',type=int,default=4)
 args=p.parse_args();sys.exit(worker(args) if args.command=='worker' else campaign(args))
