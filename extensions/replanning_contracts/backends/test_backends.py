"""Focused development/negative checks; these are not added to campaign counts."""
import copy
import hashlib
import itertools
import json
from pathlib import Path
import sqlite3
import shutil
import tempfile
import unittest

from .campaign import HERE, ROOT, applicability, run_case
from .check import check_case,check_aof_against_rows
from .contract import body, operation, prepare, validate_prepared
from .redis_store import RedisStore
from .services import IsolatedRedis
from .sqlite_store import SQLiteStore


class ContractChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='development-checks-',dir=HERE)
        cls.folder=Path(cls.temp.name);cls.private=tempfile.TemporaryDirectory(prefix='development-connections-')
        cls.service=IsolatedRedis().start()
        cls.normal=run_case(cls.folder,'sqlite','grouped','normal',cls.service,cls.private.name)
        cls.crash={backend:run_case(cls.folder,backend,'split','exit_after_effect',cls.service,cls.private.name) for backend in ('sqlite','redis')}
        cls.races={backend:run_case(cls.folder,backend,'preflight','race_same_id',cls.service,cls.private.name) for backend in ('sqlite','redis')}
    @classmethod
    def tearDownClass(cls):
        cls.service.stop();cls.private.cleanup();cls.temp.cleanup()
    def sqlite(self,profile):
        path=self.folder/(self._testMethodName+'_'+profile+'.sqlite')
        store=SQLiteStore(path,profile);store.initialize();return store
    def redis(self,profile):
        store=RedisStore(self.service.client(),self._testMethodName+'_'+profile,profile);store.initialize();self.addCleanup(store.client.close);return store
    def rejects(self,row):
        with self.assertRaises(AssertionError):check_case(row,artifacts=False)
    def test_prepared_journal_is_immutable_before_success(self):
        path=self.folder/'identity.json';prepare(path,[operation()])
        self.assertTrue(validate_prepared(path,operation())[0]);self.assertFalse(validate_prepared(path,operation(value='different'))[0])
        with self.assertRaises(ValueError):prepare(path,[operation(value='different')])
        with self.assertRaises(ValueError):prepare(self.folder/'conflict.json',[operation(),operation(value='different')])
    def test_same_matrix_has_104_declared_96_applicable_8_na(self):
        from .check import HISTORIES,PROFILES
        cells=list(itertools.product(('sqlite','redis'),PROFILES,HISTORIES))
        self.assertEqual(len(cells),104);self.assertEqual(sum(applicability(profile,history)[0] for _,profile,history in cells),96)
    def test_sqlite_grouped_error_rolls_back_but_split_keeps_effect(self):
        for profile,count in [('split',1),('grouped',0)]:
            store=self.sqlite(profile);store.entry(operation());store.control('poison_receipts')
            with self.assertRaises(sqlite3.OperationalError):store.apply_new(operation())
            snap=store.snapshot();self.assertEqual(len(snap['state']['history']),count);self.assertIsNone(snap['receipts'])
    def test_redis_grouped_real_wrongtype_keeps_effect_preflight_prevents(self):
        import redis
        for profile,count in [('grouped',1),('preflight',0)]:
            store=self.redis(profile);store.entry(operation());store.control('poison_receipts')
            if profile=='grouped':
                with self.assertRaisesRegex(redis.ResponseError,'WRONGTYPE'):store.apply_new(operation())
            else:self.assertEqual(store.apply_new(operation())['status'],'receipt_storage_invalid')
            self.assertEqual(len(store.snapshot()['state']['history']),count)
    def test_preflight_cannot_predict_valid_schema_trigger_error(self):
        store=self.sqlite('preflight');c=store.connect()
        try:
            c.execute("CREATE TRIGGER controlled_receipt_error BEFORE INSERT ON receipts BEGIN SELECT RAISE(ABORT,'controlled late trigger'); END");c.commit()
        finally:c.close()
        with self.assertRaisesRegex(sqlite3.IntegrityError,'controlled late trigger'):store.apply_new(operation())
        self.assertEqual(store.snapshot()['state']['history'],[])
    def test_receipt_retry_historic_ack_does_not_restore_revoked_value(self):
        for backend in ('sqlite','redis'):
            store=self.sqlite('envelope') if backend=='sqlite' else self.redis('envelope')
            store.apply_new(operation());store.control('revoke')
            snapshot,prior=store.entry(operation());self.assertEqual(prior['status'],'historical_ack')
            self.assertEqual(snapshot['state']['epoch'],1);self.assertEqual(snapshot['state']['version'],1);self.assertFalse(snapshot['state']['visible'])
            self.assertEqual(len(snapshot['state']['history']),2)
    def test_effect_time_epoch_guard_uses_unchanged_version(self):
        for backend,profile in itertools.product(('sqlite','redis'),('split','grouped','preflight','envelope')):
            store=self.sqlite(profile) if backend=='sqlite' else self.redis(profile)
            store.entry(operation());store.control('revoke')
            self.assertEqual(store.apply_new(operation())['status'],'stale_epoch')
            self.assertEqual(store.snapshot()['state']['version'],0)
    def test_actual_abrupt_child_exit_and_new_process_retry(self):
        for row in self.crash.values():
            metric=check_case(row);self.assertEqual(metric['abrupt_exit_87'],1)
            self.assertEqual(metric['participant_effects'],1);self.assertEqual(metric['usable_receipts'],0)
            self.assertEqual(metric['request_statuses'],['stale_version'])
    def test_two_fresh_processes_native_receipt_recheck(self):
        for row in self.races.values():
            metric=check_case(row);self.assertEqual(metric['participant_effects'],1)
            self.assertCountEqual(metric['request_statuses'],['applied','historical_ack'])
    def test_checker_reads_sqlite_without_mutation(self):
        path=ROOT/self.normal['database_path'];before=hashlib.sha256(path.read_bytes()).hexdigest()
        check_case(self.normal);self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),before)
    def test_checker_rejects_altered_physical_sqlite(self):
        row=copy.deepcopy(self.normal);altered=self.folder/'altered.sqlite'
        shutil.copy2(ROOT/row['database_path'],altered)
        connection=sqlite3.connect(altered)
        try:connection.execute("UPDATE record SET value='hidden'");connection.commit()
        finally:connection.close()
        row['database_path']=str(altered.relative_to(ROOT))
        with self.assertRaisesRegex(AssertionError,'physical SQLite'):check_case(row)
    def test_checker_rejects_hidden_native_aof_write_even_if_final_state_same(self):
        source=HERE/'results';rows=[json.loads(line) for line in (source/'cases.jsonl').read_text().splitlines()]
        copied=self.folder/'aof-forgery';copied.mkdir()
        shutil.copytree(source/'redis_native_data',copied/'redis_native_data')
        row=next(r for r in rows if r['case_id']=='redis__grouped__normal')
        command=['SET',row['case_id']+':state',row['final_snapshot']['raw']['state_json']]
        encoded=b'*3\r\n'+b''.join(b'$'+str(len(part.encode())).encode()+b'\r\n'+part.encode()+b'\r\n' for part in command)
        stream=copied/'redis_native_data/appendonlydir/appendonly.aof.1.incr.aof'
        with stream.open('ab') as handle:handle.write(encoded)
        manifest=json.loads((source/'native_aof_manifest.json').read_text())
        for item in manifest:
            path=copied/item['path'];item['sha256']=hashlib.sha256(path.read_bytes()).hexdigest();item['bytes']=path.stat().st_size
        (copied/'native_aof_manifest.json').write_text(json.dumps(manifest))
        with self.assertRaisesRegex(AssertionError,'mutation sequence'):check_aof_against_rows(copied,rows)
    def test_checker_rejects_forged_aof_grouping_with_identical_key_writes(self):
        source=HERE/'results';rows=[json.loads(line) for line in (source/'cases.jsonl').read_text().splitlines()]
        copied=self.folder/'aof-grouping-forgery';copied.mkdir()
        shutil.copytree(source/'redis_native_data',copied/'redis_native_data')
        stream=copied/'redis_native_data/appendonlydir/appendonly.aof.1.incr.aof'
        data=stream.read_bytes();start=data.index(b'*1\r\n$5\r\nMULTI\r\n');end=data.index(b'*1\r\n$4\r\nEXEC\r\n',start)
        data=data[:end]+data[end+len(b'*1\r\n$4\r\nEXEC\r\n'):]
        data=data[:start]+data[start+len(b'*1\r\n$5\r\nMULTI\r\n'):];stream.write_bytes(data)
        manifest=json.loads((source/'native_aof_manifest.json').read_text())
        for item in manifest:
            path=copied/item['path'];item['sha256']=hashlib.sha256(path.read_bytes()).hexdigest();item['bytes']=path.stat().st_size
        (copied/'native_aof_manifest.json').write_text(json.dumps(manifest))
        with self.assertRaisesRegex(AssertionError,'transaction cases'):check_aof_against_rows(copied,rows)
    def test_checker_rejects_forged_acknowledgement(self):
        row=copy.deepcopy(self.normal);row['attempts'][0]['events'][-1]['result']['status']='historical_ack';self.rejects(row)
    def test_checker_rejects_forged_native_return(self):
        row=copy.deepcopy(self.normal);row['attempts'][0]['events'][-2]['result']['status']='historical_ack';self.rejects(row)
    def test_checker_rejects_hidden_state_change(self):
        row=copy.deepcopy(self.normal);row['final_snapshot']['state']['value']='forged';row['final_snapshot']['raw']['record']['value']='forged';self.rejects(row)
    def test_checker_rejects_missing_success_receipt(self):
        row=copy.deepcopy(self.normal);row['final_snapshot']['receipts']={};self.rejects(row)
    def test_checker_rejects_changed_prepared_body(self):
        row=copy.deepcopy(self.normal);row['attempts'][0]['events'][0]['operation']['value']='forged';self.rejects(row)
    def test_checker_rejects_misclassified_na(self):
        row=copy.deepcopy(self.normal);row['applicable']=False;row['reason']='unsupported';self.rejects(row)
    def test_checker_rejects_fake_crash_barrier(self):
        row=copy.deepcopy(self.crash['sqlite']);row['attempts'][0]['events']=[e for e in row['attempts'][0]['events'] if e['event']!='effect_committed_before_receipt'];self.rejects(row)
    def test_checker_rejects_impossible_two_process_outcome(self):
        row=copy.deepcopy(self.races['sqlite'])
        for attempt in row['attempts']:attempt['events'][-1]['result']['status']='historical_ack'
        self.rejects(row)

if __name__=='__main__':unittest.main(verbosity=2)
