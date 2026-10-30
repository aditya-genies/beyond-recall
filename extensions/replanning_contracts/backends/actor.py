"""One fresh process per request. Private service config is temporary, never logged."""
import argparse
import json
import os
from pathlib import Path
import time

from .contract import canonical, result, validate_prepared
from .sqlite_store import SQLiteStore


def emit(event,**fields):
    print(canonical(dict(event=event,**fields)),flush=True)


def run(config_path,request_path,ready_path,go_path):
    config=json.loads(Path(config_path).read_text())
    request=json.loads(Path(request_path).read_text());op=request['operation']
    valid,journal_sha=validate_prepared(request['journal'],op)
    emit('prepared_validation',valid=valid,journal_sha256=journal_sha,operation=op)
    if not valid:
        emit('result',result=result('caller_binding_conflict'));return
    client=None
    try:
        if config['backend']=='sqlite':store=SQLiteStore(config['database'],config['profile'])
        else:
            import redis
            from redis.backoff import NoBackoff
            from redis.retry import Retry
            from .redis_store import RedisStore
            client=redis.Redis(host='127.0.0.1',port=config['port'],password=config['password'],
                decode_responses=True,protocol=2,socket_connect_timeout=2,socket_timeout=5,
                retry=Retry(NoBackoff(),0))
            store=RedisStore(client,config['namespace'],config['profile'])
        snap,prior=store.entry(op)
        emit('entry',snapshot=snap,receipt_hit=prior is not None)
        if prior:
            emit('result',result=prior);return
        Path(ready_path).write_text('ready')
        deadline=time.monotonic()+20
        while not Path(go_path).exists():
            if time.monotonic()>deadline:raise TimeoutError('controller release missing')
            time.sleep(.005)
        emit('submitted')
        def after_effect():
            emit('effect_committed_before_receipt')
            if request.get('exit_after_effect'):os._exit(87)
        outcome=store.apply_new(op,before_error=request.get('before_error',False),after_effect=after_effect)
        emit('backend_return',result=outcome)
        if request.get('exit_after_finalize') and outcome['acknowledged']:
            emit('finalized_before_client_ack');os._exit(87)
        emit('result',result=outcome)
    except Exception as error:
        emit('result',result=result('error',changed=None,error_type=type(error).__name__,error=str(error)))
    finally:
        if client is not None:client.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('config');parser.add_argument('request');parser.add_argument('ready');parser.add_argument('go')
    args=parser.parse_args();run(args.config,args.request,args.ready,args.go)
