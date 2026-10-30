#!/usr/bin/env python3
"""Recompute pilot observations from literal prompts/responses; no runner import."""
import argparse, hashlib, json, pathlib

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'))
def check(out):
 protocol=json.loads((out/'protocol.json').read_text())
 assert sha(out/'protocol.json')==(out/'protocol.sha256').read_text().strip()
 results=json.loads((out/'results.json').read_text());assert len(results)==24
 index={r['trial']:r for r in results};assert len(index)==24
 same=[];changed=[];observations=[]
 for s in protocol['scenarios']:
  name=s['id'];base=index[name+'-original-0']
  for condition in ('original','partial'):
   pair=[]
   for repeat in (0,1):
    trial=f'{name}-{condition}-{repeat}';r=index[trial];folder=out/'trials'/trial
    assert r['returncode']==0 and r['schema_valid'] and not r['tool_events']
    assert sha(folder/'response.txt')==r['response_sha256']
    obj=json.loads((folder/'response.txt').read_text());ops=obj['operations']
    assert set(obj)=={'operations'} and isinstance(ops,list)
    known={v['id'] for v in r['records']}
    for op in ops:
     assert set(op)=={'kind','target','key','value'} and op['kind'] in ('put','delete')
     assert op['target'] is None or op['target'] in known
     if op['kind']=='delete':assert op['target'] is not None and op['key'] is None and op['value'] is None
     else:assert isinstance(op['key'],str) and isinstance(op['value'],str)
    assert ops==r['operations'];assert hashlib.sha256(canonical(ops).encode()).hexdigest()==r['normalized_operations_sha256']
    expected=protocol['instruction']+'\nCurrent records:\n'+json.dumps(r['records'],sort_keys=True)+'\nConversation:\n'+s['conversation']+'\n'
    assert (folder/'prompt.txt').read_text()==expected and sha(folder/'prompt.txt')==r['prompt_sha256']
    if condition=='original':assert r['records']==s['records'] and r['prompt_sha256']==s['original_prompt_sha256']
    else:
     records=[dict(x) for x in s['records']]
     if base['operations']:
      op=base['operations'][0];target=op['target'] or name+'-first-effect'
      records=[x for x in records if x['id']!=target]
      if op['kind']=='put':records.append(dict(id=target,key=op['key'],value=op['value']))
     assert r['records']==sorted(records,key=lambda x:x['id'])
     changed.append(base['operations']!=ops)
    pair.append(r);observations.append({'trial':trial,'operations':ops})
   assert pair[0]['prompt_sha256']==pair[1]['prompt_sha256']
   same.append(pair[0]['operations']!=pair[1]['operations'])
 summary=json.loads((out/'summary.json').read_text())
 assert summary['same_prompt_pairs']==len(same)==12
 assert summary['same_prompt_literal_variation_pairs']==sum(same)
 assert summary['changed_snapshot_comparisons']==len(changed)==12
 assert summary['changed_snapshot_literal_changes']==sum(changed)
 result={'status':'PASS','raw_responses_checked':len(observations),'prompt_pairs_checked':12,
  'same_prompt_literal_variation_pairs':sum(same),'changed_snapshot_literal_changes':sum(changed),
  'semantic_review':'Observed same-input differences include synonymous fact names/wording (e.g., reply_style versus reply_length); no harmful semantic drift is established.',
  'limits':'Protocol frozen before model requests, not externally preregistered. One requested Sol6.1 alias through one Codex harness, medium reasoning requested; exact backend snapshot/system prompt/temperature/seed not controlled. No recorded command_execution/mcp_tool_call/web_search/file_change event. No model-quality, harmfulness, incidence, or broad generalization claim.'}
 (out/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=pathlib.Path);check(p.parse_args().out.resolve())
