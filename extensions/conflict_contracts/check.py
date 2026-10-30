#!/usr/bin/env python3
"""Independent finite-contract model and read-only SQLite evidence checker.

Does not import the participant. Reports are written only to an explicit --report
path, preserving the frozen engine/result archive during verification.
"""
import argparse
import collections
import hashlib
import itertools
import json
import pathlib
import sqlite3

MODES=('upsert','value_cas','version_cas','version_cas_dedup')
WITNESSES=('own_committed_reply_lost','newer_write_between_commit_and_retry',
           'foreign_write_before_first_effect','value_ABA','delete_recreate_ABA')


def require(condition,message):
 if not condition:raise AssertionError(message)

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'))

def operation(identity,value,version=0,expected='imperial'):
 return dict(opid=identity,id='unit',value=value,expected_version=version,expected_value=expected)

def expected_cases():
 result={}
 orders=[order for order in itertools.permutations(('A0','A1','B0','B1'))
         if order.index('A0')<order.index('A1') and order.index('B0')<order.index('B1')]
 for mode in MODES:
  for verb in ('put','delete'):
   operations={'A':operation('A',None if verb=='delete' else 'metric'),
               'B':operation('B',None if verb=='delete' else 'foreign')}
   for order in orders:
    result[mode,'schedule_'+verb+'_'+'-'.join(order)]=dict(
     kind='schedule',operations=[operations[item[0]] for item in order],order=list(order),verb=verb)
  a=operation('A','metric');b=operation('B','foreign',1,'metric')
  witness_operations={
   'own_committed_reply_lost':[a,a],
   'newer_write_between_commit_and_retry':[a,b,a],
   'foreign_write_before_first_effect':[operation('B','foreign'),a],
   'value_ABA':[operation('B','foreign'),operation('C','imperial',1,'foreign'),a],
   'delete_recreate_ABA':[operation('B',None),operation('C','imperial',1,None),a]}
  for name,operations in witness_operations.items():
   result[mode,name]=dict(kind='witness',operations=operations)
  for verb,same in itertools.product(('put','delete'),(True,False)):
   name=f'race_{verb}_{"same" if same else "distinct"}_identity'
   operations=[operation('A',None if verb=='delete' else 'metric'),
               operation('A' if same else 'B',None if verb=='delete' else ('metric' if same else 'foreign'))]
   result[mode,name]=dict(kind='process_race',operations=operations,verb=verb,same_identity=same)
 return result


def model(mode,operations,order):
 """Declared per-operation contract; independent of participant implementation."""
 value='imperial';version=0;effects=[];receipts={};observed={}
 for index in order:
  op=operations[index];body=canonical({key:val for key,val in op.items() if key!='opid'})
  prior=receipts.get(op['opid']) if mode=='version_cas_dedup' else None
  if prior is not None:
   result=dict(status='replay' if prior['body']==body else 'identity_conflict',changed=False)
  elif mode=='value_cas' and value!=op['expected_value']:
   result=dict(status='value_conflict',changed=False)
  elif mode in ('version_cas','version_cas_dedup') and version!=op['expected_version']:
   result=dict(status='version_conflict',changed=False)
  else:
   effects.append(dict(serial=len(effects)+1,opid=op['opid'],body=body,
                       before_value=value,before_version=version,after_value=op['value'],after_version=version+1))
   value=op['value'];version+=1;result=dict(status='applied',changed=True)
   if mode=='version_cas_dedup':
    receipts[op['opid']]=dict(opid=op['opid'],body=body,result=canonical(result))
  observed[index]=result
 return dict(value=value,version=version,effects=effects,receipts=len(receipts)),observed,


def model_with_receipts(mode,operations,order):
 # Receipts contain exactly the successful applied result, keyed by effect identity.
 snapshot,observed=model(mode,operations,order)
 receipts=[]
 if mode=='version_cas_dedup':
  receipts=[dict(opid=effect['opid'],body=effect['body'],result=canonical(dict(status='applied',changed=True)))
            for effect in snapshot['effects']]
 return snapshot,observed,sorted(receipts,key=lambda row:row['opid'])


def read_database(path):
 require(path.is_file(),'missing database file')
 connection=sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)
 connection.row_factory=sqlite3.Row
 try:
  state=[dict(row) for row in connection.execute('SELECT id,value,version FROM state ORDER BY id')]
  effects=[dict(row) for row in connection.execute('SELECT * FROM effects ORDER BY serial')]
  receipts=[dict(row) for row in connection.execute('SELECT opid,body,result FROM receipts ORDER BY opid')]
 finally:connection.close()
 require(len(state)==1 and state[0]['id']=='unit','declared single-target state differs')
 return dict(value=state[0]['value'],version=state[0]['version'],effects=effects,receipts=len(receipts)),receipts


def check(out,report_path=None):
 rows=json.loads((out/'cases.json').read_text());expected=expected_cases()
 require(len(rows)==len(expected)==84,'incorrect finite denominator')
 keys=[(row['mode'],row['case']) for row in rows]
 require(len(set(keys))==len(keys) and set(keys)==set(expected),'missing, duplicate or unexpected structural case')
 spec=json.loads((out/'frozen_spec.json').read_text())
 source_hash=hashlib.sha256(pathlib.Path(__file__).with_name('experiment.py').read_bytes()).hexdigest()
 require(spec['source_sha256']==source_hash,'frozen engine source hash differs')
 require(spec['total']==84 and spec['modes']==list(MODES) and spec['witnesses']==list(WITNESSES),'manifest coverage differs')
 summary={};witness={};serializations={}
 for row in rows:
  key=(row['mode'],row['case']);declaration=expected[key];mode=row['mode']
  require(row['kind']==declaration['kind'],'case kind differs from declared coverage')
  observations=row['observations'];operations=[item['operation'] for item in observations]
  require(operations==declaration['operations'],'recorded operations differ from declared fixture')
  for item in observations:
   require(type(item['result']['changed']) is bool and isinstance(item['result']['status'],str),'invalid result representation')
  folder=out/'state'/('__'.join(key))
  require(json.loads((folder/'case.json').read_text())==row,'per-case record differs from archive row')
  actual,receipts=read_database(folder/'store.sqlite')
  require(row['snapshot']==actual,'serialized snapshot differs from complete physical database state/audit')
  if row['kind']=='schedule':
   require(row['metadata']['order']==declaration['order'] and row['metadata']['verb']==declaration['verb'],'declared linearization differs')
  if row['kind']=='process_race':
   require(row['metadata']['same_identity']==declaration['same_identity'] and row['metadata']['verb']==declaration['verb'],'race identity/profile differs')
   for index,item in enumerate(observations):
    require(type(item.get('returncode')) is int and item['returncode']==0,'child process did not complete')
    require(json.loads((folder/f'op{index}.json').read_text())==item['operation'],'child operation file differs')
    require((folder/f'ready{index}').is_file() and (folder/'go').is_file(),'race rendezvous evidence absent')
  candidate_orders=itertools.permutations(range(len(operations))) if row['kind']=='process_race' else [tuple(range(len(operations)))]
  accepted=[]
  for order in candidate_orders:
   predicted,predicted_results,predicted_receipts=model_with_receipts(mode,operations,order)
   if predicted==actual and predicted_receipts==receipts and all(predicted_results[index]==item['result'] for index,item in enumerate(observations)):
    accepted.append(list(order))
  require(accepted,f'{mode} / {row["case"]}: no legal contract order matches statuses, state, ledger and receipt bodies')
  if row['kind']=='process_race':serializations['__'.join(key)]=accepted
  s=summary.setdefault(mode,dict(cases=0,mutations=0,replays=0,conflicts=0))
  s['cases']+=1;s['mutations']+=len(actual['effects'])
  s['replays']+=sum(item['result']['status']=='replay' for item in observations)
  s['conflicts']+=sum('conflict' in item['result']['status'] for item in observations)
  if row['kind']=='witness':
   witness.setdefault(row['case'],{})[mode]=dict(value=actual['value'],version=actual['version'],
    statuses=[item['result']['status'] for item in observations],mutations=len(actual['effects']),
    original_intent_content_check=actual['value']=='metric',
    newer_write_preserved=actual['value']=='foreign' if row['case']=='newer_write_between_commit_and_retry' else None)
 # Explicitly check the claims interpreted in the manuscript; no new protocol theorem.
 newer=witness['newer_write_between_commit_and_retry']
 require(newer['upsert']['original_intent_content_check'] and not newer['upsert']['newer_write_preserved'],'upsert counterexample absent')
 require(newer['version_cas_dedup']['newer_write_preserved'] and not newer['version_cas_dedup']['original_intent_content_check'],'receipt+version counterexample differs')
 for name in ('value_ABA','delete_recreate_ABA'):
  require(witness[name]['value_cas']['statuses'][-1]=='applied','value ABA witness differs')
  require(witness[name]['version_cas']['statuses'][-1]=='version_conflict','version ABA witness differs')
 require(witness['own_committed_reply_lost']['version_cas']['statuses']==['applied','version_conflict'],'own replay conflict differs')
 require(witness['own_committed_reply_lost']['version_cas_dedup']['statuses']==['applied','replay'],'own replay recognition differs')
 result=dict(status='PASS',checked_cases=84,checked_process_races=16,contracts=summary,witnesses=witness,
  source_sha256=source_hash,observation_statuses_independently_modeled=True,exact_coverage_verified=True,
  full_snapshot_and_receipt_results_verified=True,consistent_race_serializations=serializations,
  scope='Finite specified operation contracts on actual SQLite. Sequential observations are replayed in declared order; each two-process result must match at least one legal transaction order. This is not exhaustive concurrent-program verification, a mid-commit crash test or a distributed guarantee.')
 if report_path is not None:
  report_path.parent.mkdir(parents=True,exist_ok=True);report_path.write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result,indent=2));return result


if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--out',type=pathlib.Path,required=True)
 parser.add_argument('--report',type=pathlib.Path,help='Separate derived verification path; omitted means stdout only')
 args=parser.parse_args();check(args.out.resolve(),args.report)
