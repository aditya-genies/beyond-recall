"""Read-only reconciliation for scientific review; no participant execution."""
from pathlib import Path
from collections import Counter, defaultdict
from contextlib import closing
import hashlib,json,re,sqlite3
ROOT=Path(__file__).resolve().parents[2]
def load(p):return json.loads((ROOT/p).read_text())
def sha(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def dbrows(p,query):
 with closing(sqlite3.connect((ROOT/p).resolve().as_uri()+'?mode=ro',uri=True)) as c:
  c.row_factory=sqlite3.Row;return [dict(r) for r in c.execute(query)]
def campaign(base,native=False):
 rows=[json.loads(s) for s in (ROOT/base/'cases.jsonl').read_text().splitlines()];groups=defaultdict(Counter);sources=0;codes=Counter();barriers=Counter();checkpoints=0
 for r in rows:
  folder=Path(base)/'state'/f"{r['policy']}__{r['profile']}__{r['history']}"
  physical=dbrows(folder/'effects.sqlite','SELECT * FROM records ORDER BY address')
  actions=dbrows(folder/'effects.sqlite','SELECT * FROM committed_actions ORDER BY serial')
  events=[e for a in r['attempts'] for e in a['events']];digests=defaultdict(set)
  for e in events:
   if e['event'] in ('decision_chosen','decision_loaded'):digests[e['intent']].add(e['digest'])
   if e['event']=='source_selected':sources+=1
   if e['event']=='abrupt_exit':barriers[e['point']]+=1
  last=r['attempts'][-1];ack=last['returncode']==0 and any(e['event']=='ack' for e in last['events'])
  vals=dict(content_correct={x['fact'] for x in physical}==set(r['expected_facts']),cardinality_correct=len(physical)==len(r['expected_facts']),acknowledged=ack,decision_continuity=all(len(d)<=1 for d in digests.values()),planning_invocations=sum(e['event']=='decision_chosen' for e in events),committed_effect_calls=len(actions))
  vals['selected_terminal']=vals['content_correct'] and vals['cardinality_correct'] and ack
  assert physical==r['physical_records'] and actions==r['committed_actions']
  assert all(r[k]==v for k,v in vals.items()),(folder,vals)
  g=groups[r['policy']];g.update(vals);g['cases']+=1;g['attempts']+=len(r['attempts'])
  for a in r['attempts']:codes[str(a['returncode'])]+=1
  if native:
   cps=dbrows(folder/'native_checkpoints.sqlite','SELECT COUNT(*) AS n FROM checkpoints')[0]['n'];checkpoints+=cps
   assert cps==r['checkpoint_snapshot']['native_checkpoint_rows']
 return dict(cases=len(rows),groups={k:dict(v) for k,v in groups.items()},source_selection_events=sources,returncodes=dict(codes),barriers=dict(barriers),native_checkpoint_rows=checkpoints)
primary=campaign(Path('results'));native=campaign(Path('extensions/langgraph_reference/results'),True)
assert primary['cases']==528 and native['cases']==66
reference=primary['groups']['D1P1R1'];measured=native['groups']['langgraph_native'];assert reference==measured
text=(ROOT/'manuscript/main.tex').read_text()+(ROOT/'manuscript/plan_binding.tex').read_text();bib=(ROOT/'manuscript/refs.bib').read_text();keys=re.findall(r'@\w+\{([^,]+),',bib);cites={k.strip() for body in re.findall(r'\\cite\w*\{([^}]+)\}',text) for k in body.split(',')}
assert len(keys)==len(set(keys))==len(cites)==36 and cites==set(keys)
for policy, c,k,t,l,q,w in re.findall(r'(D[01]P[01]R[01])\s*&\s*(\d+)&(\d+)&(\d+)&(\d+)&(\d+)&(\d+)\\\\',text):
 g=primary['groups'][policy]
 assert list(map(int,(c,k,t,l,q,w)))==[g[v] for v in ('content_correct','cardinality_correct','selected_terminal','decision_continuity','planning_invocations','committed_effect_calls')]
trials=load('extensions/sol_pilot/registered/results.json');index={r['trial']:r for r in trials};assert len(index)==24
same=changed=0;targetless=[]
for spec in load('extensions/sol_pilot/registered/protocol.json')['scenarios']:
 name=spec['id'];a=index[name+'-original-0'];first=a['operations'][0]
 if first['target'] is None:targetless.append(name)
 expected=[dict(r) for r in spec['records'] if r['id']!=first['target']]
 if first['kind']=='put':expected.append(dict(id=first['target'] or name+'-first-effect',key=first['key'],value=first['value']))
 for condition in ('original','partial'):
  pair=[index[f'{name}-{condition}-{i}'] for i in (0,1)]
  assert pair[0]['prompt_sha256']==pair[1]['prompt_sha256']
  same+=sorted(map(lambda x:json.dumps(x,sort_keys=True),pair[0]['operations']))!=sorted(map(lambda x:json.dumps(x,sort_keys=True),pair[1]['operations']))
 for i in (0,1):
  p=index[f'{name}-partial-{i}'];assert sorted(p['records'],key=lambda x:x['id'])==sorted(expected,key=lambda x:x['id'])
  changed+=a['operations']!=p['operations']
for r in trials:
 folder=Path('extensions/sol_pilot/registered/trials')/r['trial'];raw=load(folder/'response.txt');assert raw['operations']==r['operations'] and r['schema_valid'] and r['returncode']==0 and not r['tool_events']
 assert sha(folder/'response.txt')==r['response_sha256'] and sha(folder/'prompt.txt')==r['prompt_sha256']
assert same==7 and changed==12 and targetless==['preferences']
pairs=load('extensions/plan_binding/results/cases.json');arms=defaultdict(Counter)
for r in pairs:
 p=Path('extensions/plan_binding/results')/r['database'];records=dbrows(p,'SELECT public_id AS id,fact_key AS key,fact_value AS value FROM records ORDER BY public_id')
 assert records==r['final_records'];g=arms[r['arm']];g['cases']+=1;g['aliases']+=r['structural_alias'];g['prefix_preserved']+=r['prefix_binding_preserved']
assert len(pairs)==36 and {r['scenario'] for r in pairs if r['structural_alias']}=={'preferences'}
conflicts=load('extensions/conflict_contracts/results/cases.json');assert len(conflicts)==84
for r in conflicts:
 p=Path('extensions/conflict_contracts/results/state')/f"{r['mode']}__{r['case']}"/'store.sqlite';s=r['snapshot'];state=dbrows(p,'SELECT value,version FROM state')[0]
 assert state=={k:s[k] for k in ('value','version')}
 assert dbrows(p,'SELECT * FROM effects ORDER BY serial')==s['effects']
 receipts=dbrows(p,'SELECT * FROM receipts');assert len(receipts)==s['receipts']
 for receipt in receipts:assert any(e['opid']==receipt['opid'] and e['body']==receipt['body'] for e in s['effects'])
files=['manuscript/main.tex','manuscript/plan_binding.tex','manuscript/refs.bib','refs.bib','study.py','results/cases.jsonl','results/summary.json','results/boundary_probes.json','results/frozen_spec.json','extensions/langgraph_reference/runner.py','extensions/langgraph_reference/results/cases.jsonl','extensions/langgraph_reference/results/summary.json','extensions/langgraph_reference/results/frozen_spec.json','extensions/sol_pilot/pilot.py','extensions/sol_pilot/registered/protocol.json','extensions/sol_pilot/registered/results.json','extensions/sol_pilot/registered/summary.json','extensions/plan_binding/replay.py','extensions/plan_binding/design_freeze.json','extensions/plan_binding/results/cases.json','extensions/plan_binding/results/summary.json','extensions/conflict_contracts/experiment.py','extensions/conflict_contracts/check.py','extensions/conflict_contracts/results/cases.json','extensions/conflict_contracts/audit_verification.json']
assert sha('study.py')=='98378f217f0dae050dbc07aa04e1121ed9bc73862c2ee35a2e31a7a464f4e9b9'
assert sha('results/cases.jsonl')=='6714681fbefcbdf63334f76b95410aa1c2bc620ce8b7511fadb0c91354b72d01'
report=dict(status='PASS',review_action='Read-only evidence reconciliation; no new model requests, experiments or test campaigns',primary=primary,native=native,pilot=dict(raw_responses=24,same_prompt_unordered_changed_pairs=same,changed_snapshot_differences=changed,targetless_first_operation_scenarios=targetless),plan_binding=dict(cases=len(pairs),arms={k:dict(v) for k,v in arms.items()}),conflicts=dict(cases=len(conflicts),process_races=sum(r['kind']=='process_race' for r in conflicts)),citations=dict(bibliography_entries=len(keys),cited_keys=len(cites),missing=[],uncited=[],duplicates=[]),source_sha256={str(p):sha(p) for p in files})
(ROOT/'revisions/review1/final_evidence_reconciliation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ('primary','native','source_sha256')},indent=2))
