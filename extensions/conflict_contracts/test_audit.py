"""Adversarial checker fixtures and a bounded SQLite rollback check.

Copies recorded evidence into temporary directories; never changes frozen runs.
"""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest

BASE=Path(__file__).resolve().parent

def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path)
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

checker=load('conflict_audit_checker',BASE/'check.py')
engine=load('conflict_frozen_engine',BASE/'experiment.py')

class ConflictCheckerAuditTests(unittest.TestCase):
 def setUp(self):
  self.temporary=tempfile.TemporaryDirectory(prefix='conflict-audit-')
  self.addCleanup(self.temporary.cleanup)
  self.out=Path(self.temporary.name)/'results'
  shutil.copytree(BASE/'results',self.out)
  self.rows=json.loads((self.out/'cases.json').read_text())

 def row(self,mode,name):
  return next(row for row in self.rows if row['mode']==mode and row['case']==name)

 def persist(self,row):
  (self.out/'cases.json').write_text(json.dumps(self.rows))
  folder=self.out/'state'/f'{row["mode"]}__{row["case"]}'
  (folder/'case.json').write_text(json.dumps(row))

 def check(self):
  with contextlib.redirect_stdout(io.StringIO()):return checker.check(self.out)

 def test_forged_replay_status_is_rejected_even_with_correct_ledger(self):
  row=self.row('version_cas','foreign_write_before_first_effect')
  row['observations'][-1]['result']['status']='replay';self.persist(row)
  with self.assertRaisesRegex(AssertionError,'no legal contract order'):self.check()

 def test_forged_snapshot_effect_body_is_rejected(self):
  row=self.row('upsert','own_committed_reply_lost')
  row['snapshot']['effects'][0]['after_value']='fabricated';self.persist(row)
  with self.assertRaisesRegex(AssertionError,'snapshot'):self.check()

 def test_forged_receipt_result_is_rejected(self):
  folder=self.out/'state'/'version_cas_dedup__own_committed_reply_lost'
  with contextlib.closing(sqlite3.connect(folder/'store.sqlite')) as connection:
   connection.execute('UPDATE receipts SET result=?',(json.dumps({'status':'applied','changed':False}),));connection.commit()
  with self.assertRaisesRegex(AssertionError,'no legal contract order'):self.check()

 def test_forged_receipt_body_is_rejected(self):
  folder=self.out/'state'/'version_cas_dedup__own_committed_reply_lost'
  with contextlib.closing(sqlite3.connect(folder/'store.sqlite')) as connection:
   connection.execute('UPDATE receipts SET body=?',(json.dumps({'id':'unit','value':'different','expected_version':0,'expected_value':'imperial'}),));connection.commit()
  with self.assertRaisesRegex(AssertionError,'no legal contract order'):self.check()

 def test_source_hash_mismatch_is_rejected(self):
  path=self.out/'frozen_spec.json';spec=json.loads(path.read_text());spec['source_sha256']='0'*64;path.write_text(json.dumps(spec))
  with self.assertRaisesRegex(AssertionError,'source hash'):self.check()

 def test_substituted_case_is_rejected_despite_same_denominator(self):
  row=self.row('upsert','schedule_put_A0-A1-B0-B1');old=row['case'];row['case']='schedule_put_substituted'
  (self.out/'state'/f'upsert__{old}').rename(self.out/'state'/f'upsert__{row["case"]}')
  self.persist(row)
  with self.assertRaisesRegex(AssertionError,'structural case'):self.check()

 def test_wrong_operation_identity_cannot_be_hidden_by_mutation_count(self):
  row=self.row('upsert','own_committed_reply_lost');row['observations'][-1]['operation']['opid']='other';self.persist(row)
  with self.assertRaisesRegex(AssertionError,'declared fixture'):self.check()

 def test_race_status_must_match_a_legal_transaction_order(self):
  row=self.row('version_cas','race_put_distinct_identity')
  conflict=next(item for item in row['observations'] if not item['result']['changed'])
  conflict['result']['status']='replay';self.persist(row)
  with self.assertRaisesRegex(AssertionError,'no legal contract order'):self.check()

 def test_successful_verification_does_not_write_into_frozen_evidence(self):
  before={path.relative_to(self.out).as_posix():hashlib.sha256(path.read_bytes()).hexdigest() for path in self.out.rglob('*') if path.is_file()}
  result=self.check();self.assertEqual(result['checked_cases'],84)
  after={path.relative_to(self.out).as_posix():hashlib.sha256(path.read_bytes()).hexdigest() for path in self.out.rglob('*') if path.is_file()}
  self.assertEqual(before,after)

 def test_identity_binding_starts_with_success_not_rejected_attempt(self):
  path=Path(self.temporary.name)/'identity-boundary.sqlite';engine.init(path)
  engine.apply(path,'version_cas_dedup',engine.operation('B','foreign'))
  rejected=engine.operation('A','metric')
  self.assertEqual(engine.apply(path,'version_cas_dedup',rejected)['status'],'version_conflict')
  revised=engine.operation('A','metric',1,'foreign')
  self.assertEqual(engine.apply(path,'version_cas_dedup',revised)['status'],'applied')
  self.assertEqual(engine.apply(path,'version_cas_dedup',rejected)['status'],'identity_conflict')
  self.assertEqual((engine.snapshot(path)['value'],engine.snapshot(path)['version']),('metric',2))

 def test_receipt_insert_failure_rolls_back_mutation_and_audit(self):
  path=Path(self.temporary.name)/'rollback.sqlite';engine.init(path)
  with contextlib.closing(sqlite3.connect(path)) as connection:
   connection.execute("CREATE TRIGGER reject_receipt BEFORE INSERT ON receipts BEGIN SELECT RAISE(ABORT,'controlled receipt failure'); END;");connection.commit()
  with self.assertRaises(sqlite3.DatabaseError):engine.apply(path,'version_cas_dedup',engine.operation('A','metric'))
  actual=engine.snapshot(path)
  self.assertEqual((actual['value'],actual['version'],actual['receipts'],actual['effects']),('imperial',0,0,[]))

if __name__=='__main__':unittest.main()
