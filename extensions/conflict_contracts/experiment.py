#!/usr/bin/env python3
"""Bounded contract tests using actual SQLite transactions, not a novel protocol.

Four small store contracts expose replay/isolation obligations separately.
Successful effect receipts and versioned mutations commit in ONE transaction.
No whole-plan atomicity, distributed guarantee, or production claim is made.
"""
import argparse, hashlib, itertools, json, os, pathlib, sqlite3, subprocess, sys, time

MODES=('upsert','value_cas','version_cas','version_cas_dedup')
ROOT=pathlib.Path(__file__).resolve().parent
def canon(x):return json.dumps(x,sort_keys=True,separators=(',',':'))
def write(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+'\n')
def connect(p):
 c=sqlite3.connect(p,timeout=20);c.execute('PRAGMA synchronous=FULL');return c
def init(p):
 p.parent.mkdir(parents=True,exist_ok=True)
 c=connect(p)
 with c:c.executescript('''CREATE TABLE state (id TEXT PRIMARY KEY,value TEXT,version INTEGER NOT NULL);
 INSERT INTO state VALUES('unit','imperial',0);
 CREATE TABLE effects (serial INTEGER PRIMARY KEY,opid TEXT,body TEXT,before_value TEXT,before_version INTEGER,after_value TEXT,after_version INTEGER);
 CREATE TABLE receipts (opid TEXT PRIMARY KEY,body TEXT,result TEXT);''')
 c.close()
def operation(opid,value,version=0,expected='imperial'):
 return dict(opid=opid,id='unit',value=value,expected_version=version,expected_value=expected)
def apply(p,mode,op):
 c=connect(p);body=canon({k:v for k,v in op.items() if k!='opid'})
 try:
  c.execute('BEGIN IMMEDIATE')
  prior=c.execute('SELECT body,result FROM receipts WHERE opid=?',(op['opid'],)).fetchone() if mode=='version_cas_dedup' else None
  if prior:
   result=dict(status='replay' if prior[0]==body else 'identity_conflict',changed=False)
  else:
   value,version=c.execute('SELECT value,version FROM state WHERE id=?',(op['id'],)).fetchone()
   conflict=(mode=='value_cas' and value!=op['expected_value']) or (mode in ('version_cas','version_cas_dedup') and version!=op['expected_version'])
   if conflict:result=dict(status='version_conflict' if mode!='value_cas' else 'value_conflict',changed=False)
   else:
    c.execute('UPDATE state SET value=?,version=version+1 WHERE id=?',(op['value'],op['id']))
    c.execute('INSERT INTO effects(opid,body,before_value,before_version,after_value,after_version) VALUES(?,?,?,?,?,?)',(op['opid'],body,value,version,op['value'],version+1))
    result=dict(status='applied',changed=True)
    if mode=='version_cas_dedup':c.execute('INSERT INTO receipts VALUES(?,?,?)',(op['opid'],body,canon(result)))
  c.commit();return result
 except BaseException:c.rollback();raise
 finally:c.close()
def snapshot(p):
 c=connect(p)
 try:
  value,version=c.execute("SELECT value,version FROM state WHERE id='unit'").fetchone()
  effects=[dict(zip(('serial','opid','body','before_value','before_version','after_value','after_version'),x)) for x in c.execute('SELECT * FROM effects ORDER BY serial')]
  return dict(value=value,version=version,effects=effects,receipts=c.execute('SELECT COUNT(*) FROM receipts').fetchone()[0])
 finally:c.close()
def schedules():
 # A0 < A1 and B0 < B1; exactly six bounded sequential linearizations.
 return [p for p in itertools.permutations(('A0','A1','B0','B1')) if p.index('A0')<p.index('A1') and p.index('B0')<p.index('B1')]
def prepare(out):
 out.mkdir(parents=True,exist_ok=False)
 spec=dict(prepared_at_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
  source_sha256=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),modes=MODES,
  schedule_design='6 linearizations preserving first-before-retry for each of two intents, x 2 put/delete profiles x 4 contracts =48',
  witnesses=['own_committed_reply_lost','newer_write_between_commit_and_retry','foreign_write_before_first_effect','value_ABA','delete_recreate_ABA'],
  witness_design='5 specified witnesses x4 contracts =20',
  process_design='4 two-process races (same/distinct operation ids xput/delete) x4 contracts =16; arrival order uncontrolled, assertions invariant to either winner',
  total=84,source='Synthetic facts only; no external model or application code',
  assumptions='One target with monotonically increasing durable version, tombstone on deletion, atomic SQLite transactions, collision-free synthetic operation identities. Value null denotes a tombstone. Receipts retained forever for this bounded experiment.',
  contract='A receipt on exact successful replay acknowledges without mutation; first use requires expected version; changed arguments under same operation id rejected. Rejected operations are not stored as successful receipts.',
  limits='No distributed messages, mid-commit crash, arbitrary schedules, whole-plan atomicity, identity-allocation service, production performance, or new recovery algorithm claimed.')
 write(out/'frozen_spec.json',spec);print(json.dumps(spec,indent=2))
def record_case(out,name,mode,ops,kind,metadata=None):
 folder=out/'state'/f'{mode}__{name}';folder.mkdir(parents=True)
 p=folder/'store.sqlite';init(p);observations=[]
 for op in ops:observations.append(dict(operation=op,result=apply(p,mode,op)))
 row=dict(case=name,mode=mode,kind=kind,observations=observations,snapshot=snapshot(p),metadata=metadata or {})
 write(folder/'case.json',row);return row
def run_witness(out,name,mode):
 a=operation('A','metric');b=operation('B','foreign',1,'metric');c=operation('C','imperial',1,'foreign')
 if name=='own_committed_reply_lost':ops=[a,a]
 elif name=='newer_write_between_commit_and_retry':ops=[a,b,a]
 elif name=='foreign_write_before_first_effect':ops=[operation('B','foreign'),a]
 elif name=='value_ABA':ops=[operation('B','foreign'),c,a]
 else:ops=[operation('B',None),operation('C','imperial',1,None),a]
 return record_case(out,name,mode,ops,'witness')
def race(out,mode,verb,same):
 name=f'race_{verb}_{"same" if same else "distinct"}_identity';folder=out/'state'/f'{mode}__{name}';folder.mkdir(parents=True)
 p=folder/'store.sqlite';init(p);children=[]
 ops=[operation('A',None if verb=='delete' else 'metric'),operation('A' if same else 'B',None if verb=='delete' else ('metric' if same else 'foreign'))]
 for i,op in enumerate(ops):
  write(folder/f'op{i}.json',op)
  cmd=[sys.executable,str(pathlib.Path(__file__).resolve()),'child','--out',str(folder),'--mode',mode,'--index',str(i)]
  children.append(subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True))
 deadline=time.monotonic()+20
 while not all((folder/f'ready{i}').exists() for i in (0,1)):
  if time.monotonic()>deadline:
   for child in children:child.kill()
   raise RuntimeError('race rendezvous timeout')
  time.sleep(.005)
 (folder/'go').write_text('go')
 observations=[]
 for i,child in enumerate(children):
  stdout,stderr=child.communicate(timeout=25)
  if child.returncode:raise RuntimeError(f'child failed: {stderr}')
  observations.append(dict(operation=ops[i],result=json.loads(stdout),returncode=child.returncode))
 row=dict(case=name,mode=mode,kind='process_race',observations=observations,snapshot=snapshot(p),metadata={'same_identity':same,'verb':verb,'rendezvous':'both fresh processes ready before releasing writes; SQLite serializes transactions; winner not controlled'})
 write(folder/'case.json',row);return row
def run(out):
 spec=json.loads((out/'frozen_spec.json').read_text())
 assert spec['source_sha256']==hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()
 rows=[]
 for mode in MODES:
  for verb in ('put','delete'):
   ops={'A':operation('A',None if verb=='delete' else 'metric'),'B':operation('B',None if verb=='delete' else 'foreign')}
   for order in schedules():rows.append(record_case(out,'schedule_'+verb+'_'+'-'.join(order),mode,[ops[x[0]] for x in order],'schedule',{'order':order,'verb':verb}))
  for name in spec['witnesses']:rows.append(run_witness(out,name,mode))
  for verb,same in itertools.product(('put','delete'),(True,False)):rows.append(race(out,mode,verb,same))
 assert len(rows)==spec['total'];write(out/'cases.json',rows)
 write(out/'environment.json',dict(python=sys.version,sqlite=sqlite3.sqlite_version,platform=sys.platform))
 print(json.dumps({'recorded_cases':len(rows),'database_files':len(list((out/'state').rglob('store.sqlite')))}))
def child(out,mode,index):
 op=json.loads((out/f'op{index}.json').read_text());(out/f'ready{index}').write_text('ready')
 end=time.monotonic()+20
 while not (out/'go').exists():
  if time.monotonic()>end:raise RuntimeError('child rendezvous timeout')
  time.sleep(.005)
 print(canon(apply(out/'store.sqlite',mode,op)),flush=True)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('action',choices=['prepare','run','child']);a.add_argument('--out',required=True,type=pathlib.Path);a.add_argument('--mode',choices=MODES);a.add_argument('--index',type=int);v=a.parse_args();v.out=v.out.resolve()
 if v.action=='prepare':prepare(v.out)
 elif v.action=='run':run(v.out)
 else:child(v.out,v.mode,v.index)
