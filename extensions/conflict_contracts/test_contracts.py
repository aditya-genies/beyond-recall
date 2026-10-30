import importlib.util, pathlib, tempfile, unittest

P=pathlib.Path(__file__).with_name('experiment.py');spec=importlib.util.spec_from_file_location('contract_experiment',P);e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)

class ContractTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.p=pathlib.Path(self.temp.name)/'store.sqlite';e.init(self.p)
 def test_receipt_is_atomic_with_effect(self):
  op=e.operation('A','metric');self.assertEqual(e.apply(self.p,'version_cas_dedup',op)['status'],'applied')
  state=e.snapshot(self.p);self.assertEqual((state['version'],state['receipts'],len(state['effects'])),(1,1,1))
 def test_own_commit_is_acknowledged_without_overwriting_newer_write(self):
  op=e.operation('A','metric');e.apply(self.p,'version_cas_dedup',op)
  e.apply(self.p,'version_cas_dedup',e.operation('B','foreign',1,'metric'))
  self.assertEqual(e.apply(self.p,'version_cas_dedup',op)['status'],'replay');self.assertEqual(e.snapshot(self.p)['value'],'foreign')
 def test_version_check_without_receipt_cannot_acknowledge_own_replay(self):
  op=e.operation('A','metric');e.apply(self.p,'version_cas',op)
  self.assertEqual(e.apply(self.p,'version_cas',op)['status'],'version_conflict')
 def test_same_identity_with_changed_arguments_is_rejected(self):
  e.apply(self.p,'version_cas_dedup',e.operation('A','metric'))
  self.assertEqual(e.apply(self.p,'version_cas_dedup',e.operation('A','foreign',1,'metric'))['status'],'identity_conflict')
  self.assertEqual(e.snapshot(self.p)['value'],'metric')
 def test_value_aba_is_visible_to_version_check(self):
  e.apply(self.p,'version_cas',e.operation('B','foreign'))
  e.apply(self.p,'version_cas',e.operation('C','imperial',1,'foreign'))
  self.assertEqual(e.apply(self.p,'version_cas',e.operation('A','metric'))['status'],'version_conflict')
 def test_tombstone_retains_version(self):
  e.apply(self.p,'version_cas_dedup',e.operation('B',None))
  e.apply(self.p,'version_cas_dedup',e.operation('C','imperial',1,None))
  self.assertEqual(e.snapshot(self.p)['version'],2)
  self.assertEqual(e.apply(self.p,'version_cas_dedup',e.operation('A','metric'))['status'],'version_conflict')
 def test_old_content_oracle_rewards_stale_overwrite(self):
  e.apply(self.p,'upsert',e.operation('A','metric'));e.apply(self.p,'upsert',e.operation('B','foreign',1,'metric'))
  e.apply(self.p,'upsert',e.operation('A','metric'));self.assertEqual(e.snapshot(self.p)['value'],'metric')
  self.assertEqual(len(e.snapshot(self.p)['effects']),3)
 def test_schedule_space_is_exactly_six_linearizations(self):
  s=e.schedules();self.assertEqual(len(s),6);self.assertEqual(len(set(s)),6)
  self.assertTrue(all(x.index('A0')<x.index('A1') and x.index('B0')<x.index('B1') for x in s))

if __name__=='__main__':unittest.main()
