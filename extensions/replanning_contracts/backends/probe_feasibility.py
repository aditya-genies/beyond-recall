#!/usr/bin/env python3
"""Tiny development probes, not a research campaign or comparative score."""
import contextlib
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sqlite3
import sys
import tempfile

HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path:sys.path.insert(0,str(HERE))
from services import IsolatedRedis


def probe():
 import redis
 report={'phase':'DEVELOPMENT_FEASIBILITY_ONLY','not_part_of_any_frozen_campaign':True,
  'python':sys.version.split()[0],'sqlite':sqlite3.sqlite_version,'redis_py':importlib.metadata.version('redis'),
  'existing_services_or_credentials_used':False,'probes':{}}
 service=IsolatedRedis()
 try:
  with service:
   report['redis_runtime']=service.metadata()
   client=service.client();other=service.client()
   try:
    unauthenticated=service.client(False)
    try:
     try:unauthenticated.ping();rejected=False
     except redis.AuthenticationError:rejected=True
    finally:unauthenticated.close()
    assert rejected;report['probes']['fresh_random_authentication_enforced']=True
    prefix='{development-probe}:'
    effect,receipt=prefix+'effect',prefix+'receipt'
    script="redis.call('SET',KEYS[1],'applied'); redis.call('SET',KEYS[2],'ack'); return 1"
    assert client.eval(script,2,effect,receipt)==1
    assert client.get(effect)=='applied' and client.get(receipt)=='ack'
    report['probes']['native_lua_effect_and_receipt_success']=True
    client.delete(effect,receipt)
    failing="redis.call('SET',KEYS[1],'applied-before-error'); redis.call('HSET',KEYS[2],'operation','receipt'); return 1"
    client.set(receipt,'wrong-kind-for-hash')
    try:client.eval(failing,2,effect,receipt);raise AssertionError('Expected Redis WRONGTYPE')
    except redis.ResponseError as error:
     assert 'WRONGTYPE' in str(error)
    assert client.get(effect)=='applied-before-error'
    report['probes']['redis_runtime_wrongtype_after_write_retains_prior_effect']=True
    report['error_probe_script_sha256']=hashlib.sha256(failing.encode()).hexdigest()
    client.set(prefix+'watched','initial')
    with client.pipeline() as pipeline:
     pipeline.watch(prefix+'watched');assert pipeline.get(prefix+'watched')=='initial'
     other.set(prefix+'watched','other-writer')
     pipeline.multi();pipeline.set(prefix+'watched','stale-write')
     try:pipeline.execute();raise AssertionError('Expected watched transaction abort')
     except redis.WatchError:pass
    assert client.get(prefix+'watched')=='other-writer'
    report['probes']['watch_multi_exec_rejects_intervening_write']=True
    marker=prefix+'aof-marker';client.set(marker,'persisted-in-probe')
    before=client.info('server')['run_id'];client.close();other.close()
    service.restart();client=service.client();other=service.client()
    assert client.info('server')['run_id']!=before and client.get(marker)=='persisted-in-probe'
    report['probes']['aof_survives_controlled_server_restart']=True
    report['restart_scope']='Docker graceful restart with same fresh volume; no power-loss or failover claim'
   finally:client.close();other.close()
  report['owned_service_cleanup']=service.cleanup_status
  assert all(service.cleanup_status.values()) and len(service.cleanup_status)==3
 except BaseException as error:
  report['status']='FAILED_DEVELOPMENT_PROBE';report['error_type']=type(error).__name__;report['error']=str(error);report['owned_service_cleanup']=service.cleanup_status
  (HERE/'development_feasibility.json').write_text(json.dumps(report,indent=2)+'\n');raise
 with tempfile.TemporaryDirectory(prefix='sqlite-development-probe-') as directory:
  with contextlib.closing(sqlite3.connect(Path(directory)/'store.sqlite')) as connection:
   connection.executescript('CREATE TABLE state(value TEXT); CREATE TABLE receipts(value TEXT CHECK(value="ack"));')
   try:
    connection.execute('BEGIN IMMEDIATE');connection.execute('INSERT INTO state VALUES("applied")')
    connection.execute('INSERT INTO receipts VALUES("rejected-by-constraint")');connection.commit()
   except sqlite3.DatabaseError:connection.rollback()
   assert connection.execute('SELECT COUNT(*) FROM state').fetchone()[0]==0
   assert connection.execute('SELECT COUNT(*) FROM receipts').fetchone()[0]==0
   report['probes']['sqlite_explicit_rollback_removes_effect_after_receipt_error']=True
 report['status']='PASS_DEVELOPMENT_FEASIBILITY'
 report['interpretation']='Native transaction/script capabilities and one known runtime-error difference; not a frozen contract campaign, performance result or new backend discovery.'
 (HERE/'development_feasibility.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report,indent=2))

if __name__=='__main__':probe()
