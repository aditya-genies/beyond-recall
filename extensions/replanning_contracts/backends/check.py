"""Independent finite protocol oracle, physical DB/AOF reader and status checker.

No adapter/worker/transition implementation is imported. Expected histories below
are authored separately from the engine; agreement is bounded testing, not proof.
"""
import argparse
from collections import Counter
import copy
import csv
import hashlib
import itertools
import json
from pathlib import Path
import sqlite3

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
PROFILES=('split','grouped','preflight','envelope')
HISTORIES=('normal','before_effect_error','receipt_storage_error','lost_reply','changed_body',
 'stale_version','foreign_before_retry','revoke_before_submit','exit_after_effect',
 'revoke_before_retry','receipt_gc','race_same_id','race_distinct_ids')

def require(condition,message):
    if not condition:raise AssertionError(message)
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def op(identity='A',value='preferred'):
    return dict(opid=identity,target='record',value=value,expected_version=0,expected_epoch=0)
def binding(operation):return canonical({k:v for k,v in operation.items() if k!='opid'})
def start():return dict(value=None,visible=False,origin=None,record_epoch=None,version=0,epoch=0,history=[])
def logical_snapshot(state,receipts,poison=False):return dict(state=copy.deepcopy(state),receipts=copy.deepcopy(receipts),poison=poison)
def effect(state,receipts,operation,with_receipt=True):
    require(state['version']==operation['expected_version'] and state['epoch']==operation['expected_epoch'],'oracle invalid effect')
    state['version']+=1
    state.update(value=operation['value'],visible=True,origin=operation['opid'],record_epoch=state['epoch'])
    state['history'].append(dict(kind='participant',opid=operation['opid'],body=binding(operation),value=operation['value'],version=state['version'],epoch=state['epoch']))
    if with_receipt:receipts[operation['opid']]=dict(body=binding(operation),outcome=dict(value=operation['value'],version=state['version'],epoch=state['epoch']))

def oracle(row):
    backend,profile,history=row['backend'],row['profile'],row['history']
    state=start();receipts={};poison=False
    timeline=[('initial',None,{},logical_snapshot(state,receipts))];entries=[];statuses=[];exits=[];flags=[];operations=[]
    def snapshot(phase,control=None,arguments=None):timeline.append((phase,control,arguments or {},logical_snapshot(state,receipts,poison)))
    def control(kind):
        nonlocal poison,receipts
        arguments={}
        if kind=='foreign':
            state['version']+=1;state.update(value='newer',visible=True,origin='external',record_epoch=state['epoch'])
            state['history'].append(dict(kind='foreign',value='newer',version=state['version'],epoch=state['epoch']));arguments={'value':'newer'}
        elif kind=='revoke':
            state['epoch']+=1;state.update(value=None,visible=False,origin=None,record_epoch=None)
            state['history'].append(dict(kind='revoke',version=state['version'],epoch=state['epoch']))
        elif kind=='poison_receipts':poison=True;receipts=None
        elif kind=='gc_receipt':receipts.pop('A',None)
        else:raise AssertionError(kind)
        snapshot('control',kind,arguments)
    def request(status,apply=False,receipt=True,exitcode=0,request_flags=None,entry_control=None,operation=None):
        operations.append(operation or op());flags.append(request_flags or {})
        entries.append(logical_snapshot(state,receipts,poison) if status!='caller_binding_conflict' else None)
        if entry_control:control(entry_control)
        if apply:
            # With poisoned storage, a committed effect has no usable receipt.
            effect(state,receipts,operations[-1],with_receipt=receipt)
        statuses.append(status);exits.append(exitcode)
        snapshot('after_attempt_'+str(len(statuses)))
    if history=='normal':request('applied',apply=True)
    elif history=='before_effect_error':request('error',request_flags={'before_error':True})
    elif history=='receipt_storage_error':
        applies=profile=='split' or (profile=='grouped' and backend=='redis')
        request('receipt_storage_invalid' if profile=='preflight' else 'error',apply=applies,receipt=False,entry_control='poison_receipts')
    elif history=='lost_reply':request(None,apply=True,exitcode=87,request_flags={'exit_after_finalize':True});request('historical_ack')
    elif history=='changed_body':request('applied',apply=True);request('caller_binding_conflict',operation=op(value='changed'))
    elif history=='stale_version':control('foreign');request('stale_version')
    elif history=='foreign_before_retry':request('applied',apply=True);control('foreign');request('historical_ack')
    elif history=='revoke_before_submit':request('stale_epoch',entry_control='revoke')
    elif history=='exit_after_effect':request(None,apply=True,receipt=False,exitcode=87,request_flags={'exit_after_effect':True});request('stale_version')
    elif history=='revoke_before_retry':request('applied',apply=True);control('revoke');request('historical_ack')
    elif history=='receipt_gc':request('applied',apply=True);control('gc_receipt');request('stale_version')
    elif history in ('race_same_id','race_distinct_ids'):
        observed=[next((e['result']['status'] for e in a['events'] if e['event']=='result'),None) for a in row['attempts']]
        require(observed.count('applied')==1,'race must have exactly one accepted request')
        winner=observed.index('applied')
        operations=[op(),op() if history=='race_same_id' else op('B','contender')];flags=[{},{}]
        entries=[logical_snapshot(state,receipts),logical_snapshot(state,receipts)]
        loser_status='historical_ack' if history=='race_same_id' and profile in ('preflight','envelope') else 'stale_version'
        statuses=['applied' if i==winner else loser_status for i in range(2)];exits=[0,0]
        snapshot('both_entries_before_release')
        effect(state,receipts,operations[winner]);snapshot('after_concurrent_attempts')
    else:raise AssertionError('unrecognized history')
    return dict(timeline=timeline,entries=entries,statuses=statuses,exits=exits,operations=operations,flags=flags,
                final=logical_snapshot(state,receipts,poison))

def decode_raw(snapshot,backend,profile):
    raw=snapshot['raw']
    if backend=='redis':
        state=json.loads(raw['state_json'])
        if state['history']=={}:state['history']=[]
        if profile=='envelope':
            receipts=state.pop('receipts');kind='envelope';poison=False
        else:
            kind=raw['receipts_type'];poison=kind not in ('none','hash')
            require(kind in ('none','hash','string'),'unexpected Redis receipt type')
            if kind=='none':require(raw['receipts_data'] is None,'absent hash must have no data');receipts={}
            elif kind=='hash':receipts={k:json.loads(v) for k,v in raw['receipts_data'].items()}
            else:require(raw['receipts_data']=='controlled-wrong-type','wrong poison payload');receipts=None
    else:
        if profile=='envelope':state=copy.deepcopy(raw['envelope']);receipts=state.pop('receipts');kind='envelope';poison=False
        else:
            state=copy.deepcopy(raw['record']);poison=raw['receipts_table_columns']==[]
            require(poison or raw['receipts_table_columns']==['opid','body','outcome'],'unexpected SQLite receipt schema')
            kind='missing_or_invalid_table' if poison else 'table';receipts=snapshot['receipts']
    require(snapshot['state']==state,'normalized state differs from native raw record')
    require(snapshot['receipts']==receipts,'normalized receipts differ from native raw receipt data')
    require(snapshot['receipt_storage']==kind,'receipt storage label differs from raw type/schema')
    return logical_snapshot(state,receipts,poison)

def check_snapshot(observed,expected,backend,profile):
    decoded=decode_raw(observed,backend,profile)
    require(decoded==expected,'stored snapshot differs from independent history oracle')

def sqlite_native(path,profile):
    connection=sqlite3.connect('file:'+str(path)+'?mode=ro',uri=True)
    try:
        tables=[r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        if profile=='envelope':
            require(tables==['envelope'],'unexpected native SQLite tables')
            rows=connection.execute('SELECT id,payload FROM envelope').fetchall();require(len(rows)==1 and rows[0][0]=='record','unexpected envelope cardinality')
            state=json.loads(rows[0][1]);receipts=state.pop('receipts');poison=False
        else:
            require(tables in (['record'],['receipts','record']),'unexpected native SQLite schema')
            rows=connection.execute('SELECT id,value,visible,origin,record_epoch,version,epoch,history FROM record').fetchall()
            require(len(rows)==1 and rows[0][0]=='record','unexpected native target cardinality');r=rows[0]
            state=dict(value=r[1],visible=bool(r[2]),origin=r[3],record_epoch=r[4],version=r[5],epoch=r[6],history=json.loads(r[7]))
            poison='receipts' not in tables
            receipts=None if poison else {r[0]:dict(body=r[1],outcome=json.loads(r[2])) for r in connection.execute('SELECT opid,body,outcome FROM receipts')}
        require(connection.execute('PRAGMA integrity_check').fetchone()[0]=='ok','native SQLite integrity error')
        return logical_snapshot(state,receipts,poison)
    finally:connection.close()

def check_case(row,artifacts=True):
    backend,profile,history=row['backend'],row['profile'],row['history']
    require(backend in ('sqlite','redis') and profile in PROFILES and history in HISTORIES,'unknown matrix cell')
    require(row['case_id']=='__'.join((backend,profile,history)),'case identity mismatch')
    excluded=(history=='receipt_storage_error' and profile=='envelope') or (history=='exit_after_effect' and profile!='split')
    require(row['applicable']==(not excluded),'capability applicability mismatch')
    if excluded:
        expected=('No separate receipt storage in the envelope profile.' if history=='receipt_storage_error' else 'No committed effect-before-receipt boundary in this grouped/envelope primitive.')
        require(row.get('reason')==expected,'N/A reason mismatch');require('attempts' not in row,'N/A must not execute');return None
    model=oracle(row);require(len(row['timeline'])==len(model['timeline']),'timeline length mismatch')
    for observed,(phase,control,args,expected) in zip(row['timeline'],model['timeline']):
        require(observed['phase']==phase,'timeline phase mismatch')
        if control:require(observed.get('control')==control and observed.get('arguments')==args,'control mismatch')
        else:require('control' not in observed,'unexpected control')
        check_snapshot(observed['snapshot'],expected,backend,profile)
    expected_journal={operation['opid']:binding(operation) for operation in ([op(),op('B','contender')] if history=='race_distinct_ids' else [op()])}
    expected_journal_hash=hashlib.sha256(canonical(expected_journal).encode()).hexdigest()
    require(row['journal_sha256']==expected_journal_hash,'prepared body journal hash mismatch')
    require(len(row['attempts'])==len(model['statuses']),'attempt count mismatch')
    for i,(attempt,status,exitcode,operation,flags,entry) in enumerate(zip(row['attempts'],model['statuses'],model['exits'],model['operations'],model['flags'],model['entries'])):
        require(attempt['returncode']==exitcode,'child exit mismatch')
        events=attempt['events'];valid=status!='caller_binding_conflict'
        require(events[0]==dict(event='prepared_validation',valid=valid,journal_sha256=expected_journal_hash,operation=operation),'caller journal observation mismatch')
        event_names=[e['event'] for e in events]
        if not valid:require(event_names==['prepared_validation','result'],'invalid body accessed backend')
        else:
            check_snapshot(events[1]['snapshot'],entry,backend,profile)
            receipt_hit=status=='historical_ack' and history not in ('race_same_id','race_distinct_ids')
            require(events[1]['event']=='entry' and events[1]['receipt_hit']==receipt_hit,'entry receipt-hit mismatch')
            expected_names=['prepared_validation','entry']
            if receipt_hit:expected_names+=['result']
            else:
                expected_names+=['submitted']
                if history=='exit_after_effect':
                    if i==0:expected_names+=['effect_committed_before_receipt']
                    else:expected_names+=['backend_return','result']
                elif status=='error':
                    if profile=='split' and history=='receipt_storage_error':expected_names+=['effect_committed_before_receipt']
                    expected_names+=['result']
                else:
                    if status=='applied' and profile=='split':expected_names+=['effect_committed_before_receipt']
                    # Fully committed lost response has no result event; caller died.
                    if history=='lost_reply' and i==0:
                        if profile=='split':expected_names+=['effect_committed_before_receipt']
                        expected_names+=['backend_return','finalized_before_client_ack']
                    else:expected_names+=['backend_return','result']
            require(event_names==expected_names,'actor barrier/event sequence mismatch: '+repr(event_names)+' vs '+repr(expected_names))
        backend_returns=[e['result'] for e in events if e['event']=='backend_return']
        if backend_returns:
            internal='applied' if status is None and history=='lost_reply' else status
            require(backend_returns==[dict(status=internal,changed=internal=='applied',historical_ack=internal=='historical_ack',acknowledged=internal in ('applied','historical_ack'))],'native returned status mismatch')
        returned=[e['result'] for e in events if e['event']=='result']
        if status is None:require(returned==[],'terminated actor returned a client acknowledgement')
        else:
            require(len(returned)==1 and returned[0]['status']==status,'request status mismatch')
            expected_changed=None if status=='error' else status=='applied'
            require(returned[0]['changed']==expected_changed,'returned changed field mismatch')
            require(returned[0]['historical_ack']==(status=='historical_ack'),'historical acknowledgement flag mismatch')
            require(returned[0]['acknowledged']==(status in ('applied','historical_ack')),'acknowledgement flag mismatch')
            if status=='error':
                expected_type='OperationalError' if backend=='sqlite' else 'ResponseError'
                require(returned[0]['error_type']==expected_type,'unexpected native error type')
                message=returned[0]['error']
                needle=('controlled_absent_table' if history=='before_effect_error' else 'no such table: receipts') if backend=='sqlite' else ('CONTROLLED_BEFORE_EFFECT' if history=='before_effect_error' else 'WRONGTYPE')
                require(needle in message,'unexpected backend error text')
            else:require(set(returned[0])=={'status','changed','historical_ack','acknowledged'},'unexpected result fields')
        if artifacts:
            request=json.loads((ROOT/attempt['request_path']).read_text())
            require(request==dict(operation=operation,journal=row['journal_path'],**flags),'actual request file mismatch')
            raw_events=[json.loads(line) for line in (ROOT/attempt['stdout_path']).read_text().splitlines() if line]
            require(raw_events==events,'stdout differs from row observations')
            require((ROOT/attempt['stderr_path']).read_text()=='','unexpected child stderr')
    check_snapshot(row['final_snapshot'],model['final'],backend,profile)
    if artifacts:
        require(json.loads((ROOT/row['journal_path']).read_text())==expected_journal,'physical caller journal mismatch')
        require(sha(ROOT/row['journal_path'])==expected_journal_hash,'physical caller journal digest mismatch')
        require(json.loads((ROOT/row['final_snapshot_path']).read_text())==row['final_snapshot'],'final snapshot file mismatch')
        if backend=='sqlite':require(sqlite_native(ROOT/row['database_path'],profile)==model['final'],'physical SQLite differs from oracle')
    state=model['final']['state'];receipts=model['final']['receipts'] or {}
    effects=[item for item in state['history'] if item['kind']=='participant']
    counts=Counter(item['opid'] for item in effects)
    missing=sum(1 for item in effects if item['opid'] not in receipts or receipts[item['opid']]['body']!=item['body'])
    epoch=0;stale=0
    for item in state['history']:
        if item['kind']=='revoke':epoch=item['epoch']
        elif item['kind']=='participant':stale+=item['epoch']!=epoch
    statuses=[e['result']['status'] for a in row['attempts'] for e in a['events'] if e['event']=='result']
    return dict(case_id=row['case_id'],backend=backend,profile=profile,history=history,participant_effects=len(effects),
        usable_receipts=len(receipts),effects_without_usable_receipt=missing,duplicate_effects=sum(max(n-1,0) for n in counts.values()),
        stale_epoch_effects=stale,historical_ack_results=statuses.count('historical_ack'),acknowledged_results=sum(s in ('applied','historical_ack') for s in statuses),
        current_visible=state['visible'],current_value=state['value'],current_origin=state['origin'],current_epoch=state['epoch'],current_version=state['version'],
        request_statuses=statuses,abrupt_exit_87=sum(a['returncode']==87 for a in row['attempts']))

# Read the native Redis incremental append-only command stream. Redis logs script
# effects, not EVAL source. This independent reducer has no adapter dependency.
def resp_commands(data):
    position=0
    def line():
        nonlocal position
        end=data.index(b'\r\n',position);value=data[position:end];position=end+2;return value
    while position<len(data):
        marker=line();require(marker.startswith(b'*'),'AOF expected RESP array');values=[]
        for _ in range(int(marker[1:])):
            marker=line();require(marker.startswith(b'$'),'AOF expected bulk string');length=int(marker[1:])
            values.append(data[position:position+length].decode());position+=length
            require(data[position:position+2]==b'\r\n','AOF malformed bulk terminator');position+=2
        yield values

def empty_rdb(data):
    require(data[:9]==b'REDIS0011','unexpected native base RDB format');position=9
    def read_string():
        nonlocal position
        lead=data[position];position+=1
        if lead>>6==3:
            require(lead in (192,193,194),'unsupported RDB aux encoding');position+={192:1,193:2,194:4}[lead];return
        if lead>>6==0:length=lead
        elif lead>>6==1:length=((lead&63)<<8)|data[position];position+=1
        else:raise AssertionError('unexpected RDB aux length')
        position+=length
    while data[position]==250:position+=1;read_string();read_string()
    require(data[position]==255 and position+9==len(data),'base RDB must contain only AUX metadata, no preexisting keys')

def aof_state(output,with_traces=False):
    manifest=json.loads((output/'native_aof_manifest.json').read_text())
    for item in manifest:require(sha(output/item['path'])==item['sha256'],'native AOF file digest mismatch')
    base=output/'redis_native_data/appendonlydir';empty_rdb((base/'appendonly.aof.1.base.rdb').read_bytes())
    keys={};traces={};transactions=[];transaction=None;commands=list(resp_commands((base/'appendonly.aof.1.incr.aof').read_bytes()))
    counts=Counter()
    def apply(command):
        name=command[0].upper();counts[name]+=1
        if name=='SELECT':require(command==['SELECT','0'],'unexpected AOF database')
        elif name=='SET':require(len(command)==3,'unexpected SET options');keys[command[1]]=command[2]
        elif name=='HSET':
            require(len(command)==4,'unexpected HSET arity');require(isinstance(keys.get(command[1],{}),dict),'AOF HSET wrongtype');keys.setdefault(command[1],{})[command[2]]=command[3]
        elif name=='HDEL':
            require(len(command)==3,'unexpected HDEL arity')
            if command[1] in keys:
                keys[command[1]].pop(command[2],None)
                if not keys[command[1]]:del keys[command[1]]
        else:raise AssertionError('unexpected native AOF command: '+name)
        if name!='SELECT':traces.setdefault(command[1],[]).append(copy.deepcopy(keys.get(command[1])))
    for command in commands:
        if command[0].upper()=='MULTI':require(transaction is None,'nested AOF transaction');transaction=[];counts['MULTI']+=1
        elif command[0].upper()=='EXEC':
            require(transaction is not None,'AOF EXEC without MULTI')
            transactions.append(copy.deepcopy(transaction))
            for pending in transaction:apply(pending)
            transaction=None;counts['EXEC']+=1
        elif transaction is not None:transaction.append(command)
        else:apply(command)
    require(transaction is None,'incomplete native AOF transaction')
    return (keys,dict(counts),traces,transactions) if with_traces else (keys,dict(counts))

def check_aof_against_rows(output,rows):
    keys,counts,traces,transactions=aof_state(output,with_traces=True)
    def normalized(key,value):
        if value is None:return None
        if key.endswith(':state'):return json.loads(value)
        if isinstance(value,dict):return {k:json.loads(v) for k,v in value.items()}
        return value
    expected_traces={};expected_keys={};expected_transactions=[]
    for row in rows:
        if row['backend']!='redis' or not row['applicable']:continue
        namespace=row['case_id'];previous={}
        for phase in row['timeline']:
            raw=phase['snapshot']['raw']
            current={namespace+':state':json.loads(raw['state_json'])}
            if row['profile']!='envelope':
                value=raw['receipts_data']
                current[namespace+':receipts']=({k:json.loads(v) for k,v in value.items()} if isinstance(value,dict) else value)
            for key,value in current.items():
                if (key not in previous and value is not None) or (key in previous and value!=previous[key]):expected_traces.setdefault(key,[]).append(copy.deepcopy(value))
            previous=current
        raw=row['final_snapshot']['raw'];expected_keys[namespace+':state']=raw['state_json']
        if row['profile']!='envelope' and raw['receipts_type']!='none':expected_keys[namespace+':receipts']=raw['receipts_data']
        if row['profile'] in ('grouped','preflight') and row['final_snapshot']['receipts'] is not None:
            # Include explicit GC: the successful receipt existed before removal.
            if any(s['snapshot']['receipts'] for s in row['timeline']):expected_transactions.append(namespace)
    observed_traces={key:[normalized(key,value) for value in values] for key,values in traces.items()}
    require(observed_traces==expected_traces,'native AOF mutation sequence differs from declared physical-state transitions')
    require(keys==expected_keys,'replayed native Redis AOF differs from all final physical key snapshots')
    observed_transactions=[]
    for transaction in transactions:
        require(len(transaction)==2 and transaction[0][0].upper()=='SET' and transaction[1][0].upper()=='HSET','unexpected native multi-write grouping')
        state_key,receipt_key=transaction[0][1],transaction[1][1]
        require(state_key.endswith(':state') and receipt_key==state_key[:-6]+':receipts','native grouped writes cross logical cases')
        observed_transactions.append(state_key[:-6])
    require(Counter(observed_transactions)==Counter(expected_transactions),'native grouped-write transaction cases differ from declared profiles')
    return keys,counts

def verify(output,artifacts=True):
    output=Path(output);spec=json.loads((output/'frozen_spec.json').read_text())
    for name,expected in spec['source'].items():require(sha(HERE/name)==expected,'engine source differs from frozen specification')
    require(sha(HERE/'DESIGN.md')==spec['design_sha256'],'design differs from frozen specification')
    require(spec['profiles']==list(PROFILES) and spec['histories']==list(HISTORIES) and spec['backends']==['sqlite','redis'],'frozen declared axes differ')
    require(spec['declared_cells']==104 and spec['applicable_cells']==96 and spec['not_applicable_cells']==8,'frozen matrix counts differ')
    rows=[json.loads(line) for line in (output/'cases.jsonl').read_text().splitlines() if line]
    expected_ids={'__'.join(cell) for cell in itertools.product(('sqlite','redis'),PROFILES,HISTORIES)}
    require(len(rows)==104 and {r['case_id'] for r in rows}==expected_ids,'declared matrix must contain each of the 104 cells exactly once')
    metrics=[]
    for row in rows:
        try:metric=check_case(row,artifacts)
        except (AssertionError,KeyError,ValueError) as error:raise AssertionError(row['case_id']+': '+str(error)) from error
        if metric:metrics.append(metric)
    require(len(metrics)==96,'applicable matrix count differs')
    aof_counts=None
    if artifacts:
        keys,aof_counts=check_aof_against_rows(output,rows)
        restart=json.loads((output/'restart_control.json').read_text())
        typed={key:('hash' if isinstance(value,dict) else 'string',value) for key,value in keys.items()}
        expected_digest=hashlib.sha256(canonical(typed).encode()).hexdigest()
        require(restart['graceful_server_restart'] is True and restart['new_server_run_id'] is True and restart['exact_key_state_equal'] is True,'restart control failed')
        require(restart['before_sha256']==restart['after_sha256']==expected_digest and restart['key_count']==len(keys),'restart control differs from native final keys')
        provenance=json.loads((output/'redis_provenance.json').read_text())
        require(provenance['redis_version']=='7.2.17' and provenance['redis_py_version']=='8.1.0','public Redis runtime pins differ')
        require(provenance['resolved_image']=='redis@sha256:2c933526722b4126a61d5c170f766dc159adf97682f0b1cbbc27b1666ba96d84','public image digest differs')
        require(provenance['persistence']=={'appendonly':'yes','appendfsync':'always'},'AOF policy differs')
        require(json.loads((output/'cleanup.json').read_text())==dict(container=True,volume=True,network=True),'owned service resources not fully cleaned')
    summary={}
    for backend,profile in itertools.product(('sqlite','redis'),PROFILES):
        selected=[m for m in metrics if m['backend']==backend and m['profile']==profile]
        summary[backend+'/'+profile]=dict(applicable_cells=len(selected),
            **{key:sum(m[key] for m in selected) for key in ('participant_effects','usable_receipts','effects_without_usable_receipt','duplicate_effects','stale_epoch_effects','historical_ack_results','acknowledged_results','abrupt_exit_87')},
            request_status_counts=dict(Counter(s for m in selected for s in m['request_statuses'])))
    execution=json.loads((output/'execution_summary.json').read_text())
    require(execution['engine_sha256']==spec['source'],'execution source manifest mismatch')
    require(execution['development_subset'] is None,'partial development run is not the evidence campaign')
    require(execution['cases_sha256']==sha(output/'cases.jsonl'),'raw cases digest mismatch')
    require(execution['declared_rows']==104 and execution['applicable_rows']==96,'execution matrix count mismatch')
    require(execution['attempts']==sum(len(r.get('attempts',[])) for r in rows),'attempts summary mismatch')
    require(execution['abrupt_exit_87']==sum(m['abrupt_exit_87'] for m in metrics),'exit summary mismatch')
    return dict(status='pass',declared_cells=104,applicable_cells=96,not_applicable_cells=8,
        attempts=execution['attempts'],abrupt_exit_87=execution['abrupt_exit_87'],by_backend_profile=summary,
        native_aof_commands=aof_counts,native_aof_key_mutation_sequences_checked=bool(artifacts),
        native_aof_grouped_transactions_checked=aof_counts.get('EXEC',0) if artifacts else None,case_metrics=metrics,
        verification='Independent literal-history/status oracle + caller journal/stdout files + read-only native SQLite + native Redis AOF reduction.',
        scope='Agreement for finite histories; not a formal proof, production benchmark, arbitrary error, cluster or power-loss guarantee.')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('output');parser.add_argument('--report');parser.add_argument('--csv');args=parser.parse_args()
    report=verify(Path(args.output))
    if args.report:Path(args.report).write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    if args.csv:
        records=[m|{'request_statuses':canonical(m['request_statuses'])} for m in report['case_metrics']]
        with Path(args.csv).open('w',newline='') as handle:
            writer=csv.DictWriter(handle,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
    print(json.dumps({k:v for k,v in report.items() if k!='case_metrics'},indent=2,sort_keys=True))
