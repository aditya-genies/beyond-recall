"""Original trace-only checker: imports neither MemTX nor the calling adapter."""
from pathlib import Path
import hashlib,json

HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def check():
    f=json.loads((HERE/'freeze.json').read_text())
    for path,digest in f['adapter_sha256'].items():assert sha(HERE/path)==digest,path
    out=HERE/'results';p=json.loads((out/'provenance.json').read_text())
    assert p['freeze_sha256']==sha(HERE/'freeze.json') and p['trace_sha256']==sha(out/'traces.json')
    rows=json.loads((out/'traces.json').read_text());assert len(rows)==24 and len({r['case_id'] for r in rows})==24
    reads=[];writes=[]
    for r in rows:
        assert [e['sequence'] for e in r['events']]==list(range(len(r['events'])))
        assert r['b_commit']['status']=='committed' and r['b_commit']['committed_ids']==['newer-B']
        captured=set(r['a_snapshot']['snapshot_ids'])
        assert ('unrelated-anchor' in captured)==r['anchor']
        if r['family']=='reads':
            before={x['memory_id'] for x in r['before']};after={x['memory_id'] for x in r['after']};fresh={x['memory_id'] for x in r['fresh']}
            assert before==captured and set(r['c_snapshot']['snapshot_ids'])==captured|{'newer-B'}
            assert 'newer-B' in fresh
            reads.append(dict(case_id=r['case_id'],snapshot_ids=sorted(captured),retrieved_after=sorted(after),post_begin_ids_returned=sorted(after-captured),fresh_control_pass=True))
        else:
            assert ('newer-B' in captured)==(r['order']=='fresh_A')
            stages=[e for e in r['events'] if e['method']=='stage_write']
            facts={e['arguments'][2][0]['memory_id']:e['arguments'][2][0] for e in stages}
            a,b=facts['older-A'],facts['newer-B']
            assert a['entity']==b['entity'] and a['attribute']==b['attribute'] and a['scope']==b['scope'] and a['validity']==b['validity']
            assert a['value']=='closed' and b['value']=='open' and a['confidence']==b['confidence']==1.0
            if r['order']=='old_A':
                assert stages[0]['arguments'][2][0]['memory_id']=='older-A'
                b_commit_event=next(e for e in r['events'] if e['method']=='validate_and_commit' and e['result']['committed_ids']==['newer-B'])
                records={x['memory_id']:x for x in b_commit_event['store_after']}
                assert records['older-A']['created_at']<=records['newer-B']['created_at']
                assert r['a_snapshot']['started_at']<=r['b_snapshot']['started_at']
            states={x['memory_id']:x['state'] for x in r['final_store']}
            a_committed='older-A' in r['a_commit']['committed_ids']
            assert a_committed==(states['older-A']=='committed')
            b_superseded=states['newer-B']=='superseded'
            assert b_superseded==a_committed
            temporal=any(x.startswith('temporal_override:') for x in r['a_commit']['violations'])
            writes.append(dict(case_id=r['case_id'],order=r['order'],anchor=r['anchor'],authority_case=r['authority_case'],snapshot_ids=sorted(captured),a_commit=r['a_commit'],final_states=states,post_snapshot_rival_superseded=(r['order']=='old_A' and b_superseded),temporal_rejection=temporal))
    assert len(reads)==8 and len(writes)==16
    report=dict(status='PASS',meaning='Trace consistency, not baseline contract conformance or external replication.',case_count=len(rows),read_observations=reads,write_observations=writes,summary=dict(read_cases=8,read_cases_returning_post_begin_ids=sum(bool(x['post_begin_ids_returned']) for x in reads),fresh_read_controls=8,old_A_cases=sum(x['order']=='old_A' for x in writes),old_A_rival_superseded=sum(x['post_snapshot_rival_superseded'] for x in writes),old_A_temporal_rejections=sum(x['order']=='old_A' and x['temporal_rejection'] for x in writes),fresh_A_cases=sum(x['order']=='fresh_A' for x in writes)),freeze_sha256=sha(HERE/'freeze.json'))
    (out/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['summary'],indent=2))

if __name__=='__main__':check()
