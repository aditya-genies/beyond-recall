"""Original API-only adapter for public pinned MemTX; implementation stays external."""
from pathlib import Path
from datetime import datetime,timezone
from dataclasses import asdict
import argparse,hashlib,importlib.metadata,json,platform,subprocess,sys,time
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
COMMIT='4e1124ccd5fd384857463020e3497aa73ec93be6'
REQUESTER=dict(agent_id='synthetic-reader',role='worker',permissions=[])

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2,default=str)+'\n')
def utc():return datetime.now(timezone.utc).isoformat()

def verify(source):
    f=json.loads((HERE/'freeze.json').read_text())
    for rel,digest in f['adapter_sha256'].items():assert sha(HERE/rel)==digest,rel
    for rel,digest in f['upstream_sha256'].items():assert sha(source/rel)==digest,rel
    return f

def freeze(source,paper,download):
    assert not (HERE/'freeze.json').exists()
    files=[p for p in source.rglob('*') if p.is_file()]
    versions={d.metadata['Name']:d.version for d in importlib.metadata.distributions()}
    report=dict(commit=COMMIT,repository='https://github.com/lxy1134/MEMTX_',paper_url='https://arxiv.org/abs/2607.23929v2',paper_sha256=sha(paper),created_at_utc=utc(),
      adapter_sha256={n:sha(HERE/n) for n in ['PROTOCOL.md','probe.py','check.py']},
      upstream_sha256={str(p.relative_to(source)):sha(p) for p in sorted(files)},
      archive=json.loads(download.read_text()),python=sys.version,platform=platform.platform(),package_versions=dict(sorted(versions.items())),source_in_external_cache=True)
    assert report['archive']['commit']==COMMIT
    write(HERE/'freeze.json',report);print('FROZEN',sha(HERE/'freeze.json'))

def unit_tests(source):
    verify(source)
    target=HERE/'unit_tests';target.mkdir()
    external=source.parent/'memtx_unit_test_raw';external.mkdir(exist_ok=False)
    runs=[]
    for label,extra in [('full',[]),('without_optional_tau2',['--ignore=tests/test_tau2_adapter.py'])]:
        command=[sys.executable,'-m','pytest','tests','-q',*extra,'-rA',f'--junitxml={external/(label+".xml")}']
        started=utc();proc=subprocess.run(command,cwd=source,capture_output=True,text=True)
        log=external/(label+'.txt');log.write_text(proc.stdout+proc.stderr)
        suites=ET.parse(external/(label+'.xml')).getroot();cases=[]
        for case in suites.iter('testcase'):
            item=dict(name=case.get('name'),class_name=case.get('classname'),status='passed')
            for kind in ('failure','error','skipped'):
                node=case.find(kind)
                if node is not None:
                    item.update(status=kind,message=node.get('message',''))
            cases.append(item)
        counts={status:sum(x['status']==status for x in cases) for status in ['passed','failure','error','skipped']}
        runs.append(dict(label=label,command=['python','-m','pytest','tests','-q',*extra,'-rA','--junitxml=<external-log>'],started_at_utc=started,finished_at_utc=utc(),returncode=proc.returncode,counts=counts,test_cases=cases,external_raw_log_sha256=sha(log),external_junit_sha256=sha(external/(label+'.xml'))))
        if label=='full' and proc.returncode==0:break
    write(target/'report.json',dict(runs=runs,upstream_unchanged=bool(verify(source)),freeze_sha256=sha(HERE/'freeze.json')))
    print(json.dumps([{k:r[k] for k in ['label','returncode','counts']} for r in runs],indent=2))

def run(source):
    verify(source);out=HERE/'results';out.mkdir()
    sys.path.insert(0,str(source/'src'))
    from memtx.memtx_manager import MemTXManager
    from schema import MemoryRecord,MemoryState
    all_rows=[]
    def fixture(mid,value,auth=.7,src='same-sensor'):
        return dict(memory_id=mid,entity='synthetic-room-1',attribute='door_state',value=value,scope='same-room-now',confidence=1.0,source=dict(type='agent',id=src,authority=auth),validity=dict(valid_from='2026-01-01',valid_until='2030-01-01'))
    def setup(anchor):
        manager=MemTXManager();manager.set_sim_now('2026-10-29')
        if anchor:manager.pre_load_memory([MemoryRecord(memory_id='unrelated-anchor',entity='unrelated-control',attribute='mode',value='anchor',state=MemoryState.ACTION_SAFE)])
        return manager
    def state(manager):
        return [dict(**record.to_dict(),created_at=record.created_at) for _,record in sorted(manager._store.items())]
    def trace(manager,events,method,*args,**kwargs):
        result=getattr(manager,method)(*args,**kwargs)
        events.append(dict(sequence=len(events),at_utc=utc(),method=method,arguments=args,keywords=kwargs,result=result,store_after=state(manager)))
        return result
    def txstate(manager,tx):return json.loads(json.dumps(asdict(manager._txns[tx]),default=str))
    for risk in ('low','medium','high','external_action'):
        for anchor in (False,True):
            manager=setup(anchor);events=[]
            a=trace(manager,events,'begin_tx','read-A','A',risk);a_snapshot=txstate(manager,a)
            before=trace(manager,events,'retrieve',a,'door_state',REQUESTER,'plan',100)
            b=trace(manager,events,'begin_tx','write-B','B',risk)
            trace(manager,events,'stage_write',b,dict(observed_at='2026-10-29T12:00:00Z'),[fixture('newer-B','open')])
            b_commit=trace(manager,events,'validate_and_commit',b)
            after=trace(manager,events,'retrieve',a,'door_state',REQUESTER,'plan',100)
            c=trace(manager,events,'begin_tx','fresh-C','C',risk);c_snapshot=txstate(manager,c)
            fresh=trace(manager,events,'retrieve',c,'door_state',REQUESTER,'plan',100)
            all_rows.append(dict(family='reads',case_id=f'read-{risk}-anchor{int(anchor)}',risk=risk,anchor=anchor,a_snapshot=a_snapshot,c_snapshot=c_snapshot,b_commit=b_commit,before=before,after=after,fresh=fresh,events=events))
    authorities=[('equal_same_source',.7,'same-sensor'),('higher_A',.95,'other-sensor'),('lower_A',.5,'same-sensor'),('equal_different_sources',.7,'other-sensor')]
    for anchor in (False,True):
        for order in ('old_A','fresh_A'):
            for label,auth,src in authorities:
                manager=setup(anchor);events=[];a=None;a_snapshot=None
                if order=='old_A':
                    a=trace(manager,events,'begin_tx','older-A','A','low');a_snapshot=txstate(manager,a)
                    trace(manager,events,'stage_write',a,dict(observed_at='2026-10-28T12:00:00Z'),[fixture('older-A','closed',auth,src)])
                b=trace(manager,events,'begin_tx','newer-B','B','low');b_snapshot=txstate(manager,b)
                trace(manager,events,'stage_write',b,dict(observed_at='2026-10-29T12:00:00Z'),[fixture('newer-B','open')])
                b_commit=trace(manager,events,'validate_and_commit',b)
                if order=='fresh_A':
                    a=trace(manager,events,'begin_tx','correction-A','A','low');a_snapshot=txstate(manager,a)
                    trace(manager,events,'stage_write',a,dict(observed_at='2026-10-28T12:00:00Z'),[fixture('older-A','closed',auth,src)])
                a_read=trace(manager,events,'retrieve',a,'door_state',REQUESTER,'plan',100)
                a_commit=trace(manager,events,'validate_and_commit',a)
                view=trace(manager,events,'current_belief_view',REQUESTER,'plan')
                all_rows.append(dict(family='writes',case_id=f'write-{order}-anchor{int(anchor)}-{label}',anchor=anchor,order=order,authority_case=label,a_snapshot=a_snapshot,b_snapshot=b_snapshot,b_commit=b_commit,a_read=a_read,a_commit=a_commit,final_belief_view=view,final_store=state(manager),events=events))
    write(out/'traces.json',all_rows)
    write(out/'provenance.json',dict(freeze_sha256=sha(HERE/'freeze.json'),trace_sha256=sha(out/'traces.json'),finished_at_utc=utc(),python=sys.version,baseline_code_modified=False,upstream_unchanged=bool(verify(source)),api_calls=sum(len(r['events']) for r in all_rows),case_count=len(all_rows)))
    print('Recorded',len(all_rows),'cases')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['freeze','unit-tests','run']);p.add_argument('--source',type=Path,required=True);p.add_argument('--paper',type=Path);p.add_argument('--download',type=Path);a=p.parse_args()
    if a.command=='freeze':freeze(a.source,a.paper,a.download)
    elif a.command=='unit-tests':unit_tests(a.source)
    else:run(a.source)
