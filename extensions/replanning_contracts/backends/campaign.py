"""Frozen finite cross-backend campaign. Runs only newly owned local resources."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import platform
import sqlite3
import subprocess
import sys
import tempfile
import time

from .contract import PROFILES, canonical, operation, prepare
from .services import IsolatedRedis
from .sqlite_store import SQLiteStore

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
HISTORIES=('normal','before_effect_error','receipt_storage_error','lost_reply',
 'changed_body','stale_version','foreign_before_retry','revoke_before_submit',
 'exit_after_effect','revoke_before_retry','receipt_gc','race_same_id','race_distinct_ids')
ENGINE_FILES=('contract.py','sqlite_store.py','redis_store.py','actor.py','campaign.py','services.py')

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def dump(path,value):Path(path).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
def relative(path):return str(Path(path).resolve().relative_to(ROOT))
def applicability(profile,history):
    if history=='receipt_storage_error' and profile=='envelope':return False,'No separate receipt storage in the envelope profile.'
    if history=='exit_after_effect' and profile!='split':return False,'No committed effect-before-receipt boundary in this grouped/envelope primitive.'
    return True,None

def freeze(output):
    spec=dict(protocol='bounded-cross-backend-v1',source={name:digest(HERE/name) for name in ENGINE_FILES},
        design_sha256=digest(HERE/'DESIGN.md'),profiles=list(PROFILES),histories=list(HISTORIES),
        backends=['sqlite','redis'],declared_cells=104,applicable_cells=96,not_applicable_cells=8,
        application_binding='Identical durable caller journal before every backend request; not a backend guarantee.',
        revoke='epoch increments; version holds; value/visibility/origin removed; successful receipts retained.',
        group='Authored prepared-new-write baseline, not strongest vendor implementation; all profiles guard effect-time version and epoch.',
        envelope='One application key/row replacement; no physical disk write-count claim.',
        runtime=dict(python=platform.python_version(),sqlite=sqlite3.sqlite_version,platform=platform.platform()),
        boundaries='Child os._exit(87) at semantic barriers; no mid-commit, power-loss, cluster or performance claim.')
    dump(output,spec);return spec

class Request:
    def __init__(self,case_dir,index,config,op,journal,**flags):
        self.request=case_dir/f'attempt_{index}.request.json'
        self.ready=case_dir/f'attempt_{index}.ready';self.go=case_dir/f'attempt_{index}.go'
        dump(self.request,dict(operation=op,journal=relative(journal),**flags))
        self.process=subprocess.Popen([sys.executable,'-m','extensions.replanning_contracts.backends.actor',str(config),
            relative(self.request),relative(self.ready),relative(self.go)],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    def wait_entry(self):
        deadline=time.monotonic()+25
        while not self.ready.exists() and self.process.poll() is None:
            if time.monotonic()>deadline:
                self.process.kill();raise TimeoutError('actor entry barrier timeout')
            time.sleep(.005)
    def release(self):self.go.write_text('go')
    def collect(self):
        out,err=self.process.communicate(timeout=25)
        stdout=self.request.with_suffix('.stdout.jsonl');stderr=self.request.with_suffix('.stderr.txt')
        stdout.write_text(out);stderr.write_text(err)
        events=[json.loads(line) for line in out.splitlines() if line.strip()]
        row=dict(request_path=relative(self.request),stdout_path=relative(stdout),stderr_path=relative(stderr),
            returncode=self.process.returncode,events=events)
        return row

def run_case(output,backend,profile,history,service,config_dir):
    identity=f'{backend}__{profile}__{history}'
    applicable,reason=applicability(profile,history)
    if not applicable:return dict(case_id=identity,backend=backend,profile=profile,history=history,applicable=False,reason=reason)
    folder=output/'cells'/identity;folder.mkdir(parents=True)
    a=operation();b=operation('B','contender')
    journal=folder/'prepared.json';prepared_hash=prepare(journal,[a,b] if history=='race_distinct_ids' else [a])
    if backend=='sqlite':
        database=folder/'store.sqlite';store=SQLiteStore(database,profile)
        config=dict(backend=backend,profile=profile,database=str(database.resolve()))
    else:
        from .redis_store import RedisStore
        store=RedisStore(service.client(),identity,profile)
        config=dict(backend=backend,profile=profile,namespace=identity,port=service.port,password=service.password)
    store.initialize();config_path=Path(config_dir)/(identity+'.json');dump(config_path,config)
    timeline=[dict(phase='initial',snapshot=store.snapshot())];attempts=[]
    def snapshot(phase):timeline.append(dict(phase=phase,snapshot=store.snapshot()))
    def control(kind,**kw):
        store.control(kind,**kw);timeline.append(dict(phase='control',control=kind,arguments=kw,snapshot=store.snapshot()))
    def request(op=a,entry_control=None,**flags):
        child=Request(folder,len(attempts),config_path,op,journal,**flags)
        child.wait_entry()
        if entry_control:entry_control()
        child.release();attempts.append(child.collect());snapshot('after_attempt_'+str(len(attempts)))
    try:
        if history=='normal':request()
        elif history=='before_effect_error':request(before_error=True)
        elif history=='receipt_storage_error':request(entry_control=lambda:control('poison_receipts'))
        elif history=='lost_reply':request(exit_after_finalize=True);request()
        elif history=='changed_body':request();request(op=operation(value='changed'))
        elif history=='stale_version':control('foreign',value='newer');request()
        elif history=='foreign_before_retry':request();control('foreign',value='newer');request()
        elif history=='revoke_before_submit':request(entry_control=lambda:control('revoke'))
        elif history=='exit_after_effect':request(exit_after_effect=True);request()
        elif history=='revoke_before_retry':request();control('revoke');request()
        elif history=='receipt_gc':request();control('gc_receipt');request()
        elif history in ('race_same_id','race_distinct_ids'):
            first=Request(folder,0,config_path,a,journal)
            second=Request(folder,1,config_path,a if history=='race_same_id' else b,journal)
            first.wait_entry();second.wait_entry()
            snapshot('both_entries_before_release');first.release();second.release()
            attempts.extend([first.collect(),second.collect()]);snapshot('after_concurrent_attempts')
        else:raise ValueError(history)
        final=store.snapshot();dump(folder/'final_snapshot.json',final)
        return dict(case_id=identity,backend=backend,profile=profile,history=history,applicable=True,
            journal_path=relative(journal),journal_sha256=prepared_hash,attempts=attempts,timeline=timeline,
            final_snapshot=final,final_snapshot_path=relative(folder/'final_snapshot.json'),
            database_path=relative(database) if backend=='sqlite' else None)
    finally:
        if backend=='redis':store.client.close()

def run(output,spec_path,selected=None):
    output=Path(output).resolve()
    if output.exists():raise ValueError('Refusing to overwrite existing campaign directory')
    spec=json.loads(Path(spec_path).read_text())
    for name,expected in spec['source'].items():
        if digest(HERE/name)!=expected:raise ValueError('Frozen engine mismatch: '+name)
    if digest(HERE/'DESIGN.md')!=spec['design_sha256']:raise ValueError('Frozen protocol mismatch')
    output.mkdir(parents=True);dump(output/'frozen_spec.json',spec)
    rows=[]
    with tempfile.TemporaryDirectory(prefix='backend-study-connections-') as private:
        service=IsolatedRedis()
        try:
            service.start();dump(output/'redis_provenance.json',service.metadata())
            for backend in spec['backends']:
                for profile in spec['profiles']:
                    for history in spec['histories']:
                        if selected and history not in selected:continue
                        row=run_case(output,backend,profile,history,service,private);rows.append(row)
                        with (output/'cases.jsonl').open('a') as handle:handle.write(canonical(row)+'\n')
            # Separate persistence control (not a new case/denominator): graceful
            # restart of the owned server/volume, with all completed Redis keys.
            before_client=service.client()
            try:
                run_id_before=before_client.info('server')['run_id']
                before={key:(before_client.type(key),before_client.hgetall(key) if before_client.type(key)=='hash' else before_client.get(key)) for key in before_client.scan_iter()}
            finally:before_client.close()
            service.restart()
            after_client=service.client()
            try:
                run_id_after=after_client.info('server')['run_id']
                after={key:(after_client.type(key),after_client.hgetall(key) if after_client.type(key)=='hash' else after_client.get(key)) for key in after_client.scan_iter()}
            finally:after_client.close()
            if before!=after or run_id_before==run_id_after:raise AssertionError('owned Redis restart control failed')
            dump(output/'restart_control.json',dict(graceful_server_restart=True,new_server_run_id=run_id_before!=run_id_after,
                exact_key_state_equal=before==after,key_count=len(after),before_sha256=hashlib.sha256(canonical(before).encode()).hexdigest(),
                after_sha256=hashlib.sha256(canonical(after).encode()).hexdigest(),
                scope='Separate persistence control, no power-loss/mid-commit claim or extra case denominator.'))
            # Quiescent native AOF export from this experiment's own container.
            aof=output/'redis_native_data';aof.mkdir()
            service.command(['cp',service.container+':/data/.',str(aof)],timeout=30)
            exported=[]
            for path in sorted(aof.rglob('*')):
                if path.is_file():exported.append(dict(path=str(path.relative_to(output)),sha256=digest(path),bytes=path.stat().st_size))
            dump(output/'native_aof_manifest.json',exported)
        finally:
            service.stop();dump(output/'cleanup.json',service.cleanup_status)
    dump(output/'execution_summary.json',dict(declared_rows=len(rows),applicable_rows=sum(row['applicable'] for row in rows),
        attempts=sum(len(row.get('attempts',[])) for row in rows),abrupt_exit_87=sum(a['returncode']==87 for r in rows for a in r.get('attempts',[])),
        actual_runtime=dict(python=platform.python_version(),sqlite=sqlite3.sqlite_version,platform=platform.platform()),
        engine_sha256=spec['source'],cases_sha256=digest(output/'cases.jsonl'),development_subset=selected))
    return rows

if __name__=='__main__':
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='action',required=True)
    freeze_parser=sub.add_parser('freeze');freeze_parser.add_argument('output')
    run_parser=sub.add_parser('run');run_parser.add_argument('output');run_parser.add_argument('--spec',required=True);run_parser.add_argument('--histories',nargs='+')
    args=parser.parse_args()
    if args.action=='freeze':freeze(args.output)
    else:run(args.output,args.spec,args.histories)
