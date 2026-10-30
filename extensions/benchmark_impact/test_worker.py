"""Offline unit/negative checks plus tiny native runtime feasibility fixtures.

Native fixtures use the two existing public research runtimes and cached BGE
weights. They make no LLM/API request and are not primary study observations.
"""
from __future__ import annotations
import ast
import base64
import copy
from dataclasses import asdict
import hashlib
import importlib
import importlib.util
import io
import json
import os
from pathlib import Path
import pickle
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

from extensions.benchmark_impact import data,memory_worker as worker

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
# pipeline.py is also a direct CLI and imports sibling data by its plain name.
with mock.patch.dict(sys.modules,{'data':data}):
 spec=importlib.util.spec_from_file_location('benchmark_impact_pipeline_under_test',HERE/'pipeline.py')
 pipeline=importlib.util.module_from_spec(spec);spec.loader.exec_module(pipeline)


def dump(path,value):path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2)+'\n')
def event(index,text,date='2024/01/01',speaker='user'):
 return dict(event_id=f'{index:024x}',source_id=f'{index+100:024x}',occurred_at=date,speaker=speaker,text=text)
def episode(events=None):
 return dict(scope='a'*24,events=events if events is not None else [event(1,'The lighthouse notebook is cobalt blue.'),event(2,'The lighthouse notebook is cobalt blue.','2024/02/02'),event(3,'Correction: the lighthouse notebook is now amber.','2024/03/03'),event(4,'The current notebook is amber.','2024/03/03','assistant')])
def native_row(e,physical='point'):
 return dict(physical_id=physical,event_id=e['event_id'],source_id=e['source_id'],occurred_at=e['occurred_at'],text=worker.content(e),body_sha256=worker.sha_obj(e),score=1.)
def load_pipeline_fixture(folder,unanswerable=False):
 ep=episode();scope=ep['scope'];q=dict(key='q-test',dataset='synthetic',group='g',source_question_id='raw-q',question='What is the notebook color?',reference='amber',category='toy',expected_events=[ep['events'][2]['event_id']],missing_gold_locations=[],unanswerable=unanswerable,episode_scope=scope,question_date='2024/04/04')
 dump(folder/'participants'/f'{scope}.json',ep);dump(folder/'queries'/f'{scope}.json',[dict(invocation=q['key'],question=q['question'])]);dump(folder/'retry_sources'/f'{scope}.json',[ep['events'][0]['source_id']])
 dump(folder/'embedding_manifest.json',{'fixture':'No model calls; version-bound test manifest.'});dump(folder/'evaluator_questions.json',[q]);dump(folder/'split.json',{'fixture':'original split'})
 inputs={str(p.relative_to(folder)):pipeline.sha(p) for group in ('participants','queries','retry_sources') for p in (folder/group).glob('*.json')}
 spec=dict(source_hashes={str(p.relative_to(ROOT)):pipeline.sha(p) for p in pipeline.source_files()},protected_release={},input_files=inputs,embedding_manifest_sha256=pipeline.sha(folder/'embedding_manifest.json'),evaluator_sha256=pipeline.sha(folder/'evaluator_questions.json'),split_sha256=pipeline.sha(folder/'split.json'))
 dump(folder/'protocol.json',spec);(folder/'protocol.sha256').write_text(pipeline.sha(folder/'protocol.json')+'\n')
 for backend in pipeline.BACKENDS:
  for mode in ('clean',*pipeline.STORAGE_MODES):dump(folder/'stores'/backend/scope/mode/'candidates.json',[dict(invocation=q['key'],candidates=[native_row(ep['events'][2])])])
 return ep,q

def completed_fixture(folder):
 scope=next((folder/'participants').glob('*.json')).stem
 for backend in pipeline.BACKENDS:
  jobs=[('initial','initial','native_once',0),('query-clean','query','native_once',0)]
  for mode in pipeline.STORAGE_MODES:jobs.extend([('cut-'+mode,'retry',mode,87),('resume-'+mode,'retry',mode,0),('query-'+mode,'query',mode,0)])
  for tag,action,mode,code in jobs:dump(folder/'executions'/f'{backend}-{scope}-{tag}.json',dict(backend=backend,scope=scope,action=action,mode=mode,tag=tag,returncode=code,expected_returncode=code,stdout=''))
 dump(folder/'native_completion.json',dict(status='COMPLETE',participants=2,actual_expected_exit87=6,source_protocol_sha256=pipeline.sha(folder/'protocol.json')))

class WorkerBoundaryTests(unittest.TestCase):
 def test_ingestion_rejects_top_level_and_event_evaluator_fields(self):
  for field in ('reference','expected_ids','has_answer','category','question'):
   for level in ('episode','event'):
    bad=episode();(bad if level=='episode' else bad['events'][0])[field]='EVALUATOR_ONLY'
    with self.subTest(field=field,level=level):
     with self.assertRaises(ValueError):worker.validate_episode(bad)
 def test_ingestion_rejects_nonobjects_and_duplicate_occurrences(self):
  for bad in [None,[],{'scope':'x','events':[[]]},dict(scope='x',events=[event(1,'x'),event(1,'x')])]:
   with self.subTest(payload=type(bad).__name__):
    with self.assertRaises(ValueError):worker.validate_episode(bad)
 def test_bad_ingestion_and_wrong_initial_mode_fail_before_provider_creation(self):
  from types import SimpleNamespace
  with tempfile.TemporaryDirectory(prefix='worker-boundary-') as directory:
   folder=Path(directory);path=folder/'episode.json';bad=episode();bad['reference']='LEAK';dump(path,bad)
   args=SimpleNamespace(folder=folder/'store',backend='mem0_raw',action='initial',mode='native_once',episode=path)
   with mock.patch.dict(os.environ,{},clear=True),mock.patch.object(worker,'Mem0Participant',side_effect=AssertionError('Provider initialized')):
    with self.assertRaises(ValueError):worker.run(args)
    dump(path,episode());args.mode='content_admission'
    with self.assertRaisesRegex(ValueError,'common native baseline'):worker.run(args)
 def test_clean_baseline_cannot_receive_retry_writes(self):
  from types import SimpleNamespace
  with tempfile.TemporaryDirectory() as directory:
   folder=Path(directory);path=folder/'ep.json';dump(path,episode());args=SimpleNamespace(folder=folder/'store',backend='mem0_raw',action='retry',mode='native_once',episode=path)
   with mock.patch.dict(os.environ,{},clear=True),mock.patch.object(worker,'Mem0Participant',side_effect=AssertionError('Provider initialized')):
    with self.assertRaisesRegex(ValueError,'Clean baseline'):worker.run(args)
 def test_cache_is_manifest_bound_and_rejection_does_not_leave_write_lock(self):
  with tempfile.TemporaryDirectory(prefix='worker-cache-') as directory:
   folder=Path(directory);manifest=folder/'manifest.json';other=folder/'other.json';dump(manifest,{'version':1});dump(other,{'version':2});cache=folder/'cache.sqlite';calls=[]
   def embed(text):calls.append(text);return [1.,2.]
   c=worker.EmbeddingCache(cache,'unit',embed,embed,manifest)
   self.assertEqual(c.get('text','document'),[1.,2.]);self.assertEqual(c.get('text','document'),[1.,2.]);self.assertEqual(len(calls),1)
   c.get('text','query');self.assertEqual(len(calls),2);c.close()
   with self.assertRaisesRegex(ValueError,'manifest differs'):worker.EmbeddingCache(cache,'unit',embed,embed,other)
   connection=sqlite3.connect(cache,timeout=.05)
   try:connection.execute('BEGIN IMMEDIATE');connection.rollback()
   finally:connection.close()
   c=worker.EmbeddingCache(cache,'unit',embed,embed,manifest)
   try:self.assertEqual(c.get('text','document'),[1.,2.]);self.assertEqual(len(calls),2)
   finally:c.close()
 def test_unbound_existing_vectors_cannot_be_relabelled_as_current_manifest(self):
  with tempfile.TemporaryDirectory() as directory:
   folder=Path(directory);cache=folder/'cache.sqlite';manifest=folder/'manifest.json';dump(manifest,{'version':1})
   connection=sqlite3.connect(cache)
   try:connection.execute('CREATE TABLE embeddings(k TEXT PRIMARY KEY,v TEXT NOT NULL)');connection.execute("INSERT INTO embeddings VALUES('old','[1]')");connection.commit()
   finally:connection.close()
   with self.assertRaisesRegex(ValueError,'Unbound preexisting'):worker.EmbeddingCache(cache,'unit',lambda _:[],lambda _:[],manifest)
 def test_changed_body_under_retained_event_id_fails_before_add(self):
  e=event(1,'original');bad=dict(e,text='changed');participant=mock.Mock()
  with self.assertRaisesRegex(ValueError,'different body'):worker.admit(participant,bad,'event_admission',{e['event_id']:worker.sha_obj(e)},{worker.content(e)})
  participant.add.assert_not_called()
 def test_context_budget_counts_array_envelope_and_preserves_whole_records(self):
  base=native_row(event(1,''));item=dict(event_id=base['event_id'],source_id=base['source_id'],date=base['occurred_at'],text='')
  overhead=len(json.dumps([item],ensure_ascii=True,separators=(',',':')).encode())
  exact=dict(base,text='x'*(pipeline.BYTE_BUDGET-overhead))
  chosen=pipeline.select_context([exact]);self.assertEqual(len(chosen),1)
  self.assertEqual(len(json.dumps(chosen,ensure_ascii=True,separators=(',',':')).encode()),pipeline.BYTE_BUDGET)
  oversized=dict(exact,text=exact['text']+'x');small=native_row(event(2,'small'))
  selected=pipeline.select_context([oversized,small]);self.assertEqual([r['event_id'] for r in selected],[small['event_id']]);self.assertEqual(selected[0]['text'],small['text'])
 def test_context_dedup_uses_event_identity_not_literal_text(self):
  a=native_row(event(1,'same'));b=native_row(event(2,'same'),'second');duplicate=dict(a,physical_id='duplicate')
  selected=pipeline.select_context([a,duplicate,b],True);self.assertEqual([r['event_id'] for r in selected],[a['event_id'],b['event_id']])
 def test_split_tamper_is_rejected(self):
  with tempfile.TemporaryDirectory() as directory:
   folder=Path(directory);load_pipeline_fixture(folder);pipeline.verify(folder);dump(folder/'split.json',{'fixture':'post-outcome split'})
   with self.assertRaises(AssertionError):pipeline.verify(folder)
 def test_contexts_reject_partial_or_bad_native_execution_coverage(self):
  with tempfile.TemporaryDirectory() as directory:
   folder=Path(directory);load_pipeline_fixture(folder)
   with self.assertRaises((FileNotFoundError,AssertionError)):pipeline.contexts(folder)
   completed_fixture(folder);pipeline.verify_native(folder)
   record=next((folder/'executions').glob('*-initial.json'));row=json.loads(record.read_text());row['returncode']=87;dump(record,row)
   with self.assertRaises(AssertionError):pipeline.contexts(folder)
 def test_native_completion_summary_counts_match_actual_expected_manifests(self):
  with tempfile.TemporaryDirectory() as directory:
   folder=Path(directory);load_pipeline_fixture(folder);completed_fixture(folder)
   path=folder/'native_completion.json';row=json.loads(path.read_text());row['participants']=999;row['actual_expected_exit87']=0;dump(path,row)
   with self.assertRaises(AssertionError):pipeline.verify_native(folder)
 def test_native_execution_labels_match_filename_backend_scope_and_phase(self):
  with tempfile.TemporaryDirectory() as directory:
   folder=Path(directory);load_pipeline_fixture(folder);completed_fixture(folder)
   path=next((folder/'executions').glob('mem0_raw-*-initial.json'));row=json.loads(path.read_text());row['backend']='llama_index';dump(path,row)
   with self.assertRaises(AssertionError):pipeline.verify_native(folder)
 def test_unanswerable_support_stays_null_and_query_date_is_reader_only(self):
  with tempfile.TemporaryDirectory() as directory:
   folder=Path(directory);_,q=load_pipeline_fixture(folder,unanswerable=True);completed_fixture(folder);pipeline.contexts(folder)
   rows=json.loads((folder/'contexts.json').read_text());self.assertTrue(rows)
   self.assertTrue(all(row['metrics']['positive_support_coverage'] is None for row in rows))
   self.assertTrue(all(row['question_date']==q['question_date'] for row in rows))
   query=json.loads(next((folder/'queries').glob('*.json')).read_text())[0];self.assertEqual(set(query),{'invocation','question'})
 def test_reader_source_parses_and_prompt_excludes_evaluator_metadata(self):
  path=HERE/'reader.py';ast.parse(path.read_text());spec=importlib.util.spec_from_file_location('impact_reader_under_test',path);reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
  row=dict(question='What is the current color?',question_date='2024/04/04',context=[],reference='GOLD-ONLY',expected_ids=['GOLD-ID'],backend='HIDDEN-BACKEND',arm='HIDDEN-ARM',category='HIDDEN-CATEGORY')
  text=reader.prompt(row);body=json.loads(text[len(reader.INSTRUCTION):]);self.assertEqual(set(body),{'question','question_date','evidence'})
  self.assertNotIn('GOLD-ONLY',text);self.assertNotIn('HIDDEN-',text)
  prediction=dict(answer='A prediction',cited_event_ids=['out-of-context-id'],abstain=False)
  self.assertEqual(reader.validate(prediction,set()),prediction) # Invalid citation is retained for outcome grading.

class RestrictedPointDecoder(pickle.Unpickler):
 def find_class(self,module,name):
  if module=='qdrant_client.http.models.models' and name in ('PointStruct','SparseVector'):
   from qdrant_client.http.models import models
   return getattr(models,name)
  raise ValueError('Unexpected point pickle class')

def physical_records(folder,backend):
 if backend=='mem0_raw':
  connection=sqlite3.connect((folder/'qdrant/collection/study_memories/storage.sqlite').resolve().as_uri()+'?mode=ro',uri=True)
  try:
   records={}
   for key,blob in connection.execute('SELECT id,point FROM points'):
    identity=RestrictedPointDecoder(io.BytesIO(base64.b64decode(key))).load();point=RestrictedPointDecoder(io.BytesIO(blob)).load();assert point.id==identity
    payload=point.payload;meta=payload
    records[identity]=dict(physical_id=identity,text=payload['data'],event_id=meta['study_event_id'],source_id=meta['study_source_id'],occurred_at=meta['study_date'],body_sha256=meta['study_body_sha256'])
   return records
  finally:connection.close()
 doc=json.loads((folder/'storage/docstore.json').read_text())['docstore/data'];vector=json.loads((folder/'storage/default__vector_store.json').read_text())
 records={}
 for identity,wrapped in doc.items():
  value=wrapped['__data__'];meta=value['metadata'];assert value['id_']==identity
  records[identity]=dict(physical_id=identity,text=value['text'],event_id=meta['study_event_id'],source_id=meta['study_source_id'],occurred_at=meta['study_date'],body_sha256=meta['study_body_sha256'])
 assert set(vector['embedding_dict'])==set(records)
 return records

class NativeFeasibilityTests(unittest.TestCase):
 records=[]
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory(prefix='benchmark-impact-native-fixture-');cls.root=Path(cls.temp.name);cls.ep=episode();cls.manifest=cls.root/'embedding-manifest.json';dump(cls.manifest,dict(fixture='Tiny SHA-bound runtime check; not a loaded-weight provenance claim.'))
  cls.epfile=cls.root/'episode.json';dump(cls.epfile,cls.ep);cls.sources=cls.root/'retry-sources.json';dump(cls.sources,[cls.ep['events'][0]['source_id']]);cls.queries=cls.root/'queries.json';dump(cls.queries,[dict(invocation='synthetic-query',question=cls.ep['events'][2]['text'])])
  cls.clean={};cls.records=[]
  for backend in pipeline.BACKENDS:
   executable=pipeline.interpreter(backend)
   if not executable.exists():raise RuntimeError('Required public native runtime missing: '+backend)
   cls.clean[backend]=cls.root/backend/'clean'
   cls.invoke(backend,'initial',cls.clean[backend],'native_once')
 @classmethod
 def tearDownClass(cls):
  dump(HERE/'worker_review_native.json',dict(phase='Tiny synthetic native runtime feasibility only; no primary study cells',llm_calls=0,offline_local_embedding_inference=True,attempts=cls.records))
  cls.temp.cleanup()
 @classmethod
 def invoke(cls,backend,action,folder,mode,cut=False,epfile=None,sources=None,manifest=None,expected=0):
  cmd=[str(pipeline.interpreter(backend)),str(HERE/'memory_worker.py'),action,'--backend',backend,'--mode',mode,'--folder',str(folder),'--cache',str(folder.parent/(folder.name+'-embedding-cache.sqlite')),'--embedding-manifest',str(manifest or cls.manifest),'--episode',str(epfile or cls.epfile),'--retry-sources',str(sources or cls.sources),'--queries',str(cls.queries),'--output',str(folder/'candidates.json'),'--redeliveries','1','--limit','10']
  if cut:cmd.append('--cut')
  env=dict(os.environ);env.update(HF_HUB_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',MEM0_TELEMETRY='false',OMP_NUM_THREADS='2')
  for key in list(env):
   if key.endswith('_API_KEY') or key in ('HF_TOKEN','HUGGING_FACE_HUB_TOKEN'):env.pop(key)
  start=time.monotonic();r=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True,timeout=120)
  native_file=folder/('qdrant/collection/study_memories/storage.sqlite' if backend=='mem0_raw' else 'storage/docstore.json')
  observed=physical_records(folder,backend) if native_file.exists() else {}
  cls.records.append(dict(backend=backend,action=action,mode=mode,cut=cut,returncode=r.returncode,expected_returncode=87 if cut else expected,seconds=round(time.monotonic()-start,3),fresh_fixture_cache_file=folder.name+'-embedding-cache.sqlite',worker_sha256=worker.file_sha(HERE/'memory_worker.py'),embedding_manifest_sha256=worker.file_sha(manifest or cls.manifest),physical_records=list(observed.values()),stdout=r.stdout.replace(str(cls.root),'[temporary fixture]').replace(str(ROOT),'[repository]'),stderr=r.stderr.replace(str(cls.root),'[temporary fixture]').replace(str(ROOT),'[repository]')))
  wanted=87 if cut else expected
  if (wanted==0 or wanted==87) and r.returncode!=wanted:raise AssertionError('Native fixture failed '+backend+'/'+action+': '+r.stderr[-4000:])
  if wanted==1 and r.returncode==0:raise AssertionError('Expected native rejection did not occur')
  return r
 def cloned(self,backend,name):
  folder=self.root/backend/name;shutil.copytree(self.clean[backend],folder)
  self.assertEqual(physical_records(folder,backend),physical_records(self.clean[backend],backend));return folder
 def test_initial_persistence_and_query_reopen_use_actual_native_records(self):
  for backend in pipeline.BACKENDS:
   with self.subTest(backend=backend):
    before=physical_records(self.clean[backend],backend);self.assertEqual(len(before),4)
    self.assertEqual({r['event_id'] for r in before.values()},{e['event_id'] for e in self.ep['events']})
    self.assertEqual(sum(r['text']==worker.content(self.ep['events'][0]) for r in before.values()),2)
    self.invoke(backend,'query',self.clean[backend],'native_once');self.assertEqual(physical_records(self.clean[backend],backend),before)
    candidates=json.loads((self.clean[backend]/'candidates.json').read_text())[0]['candidates'];self.assertTrue(candidates)
    self.assertTrue({r['physical_id'] for r in candidates}<=set(before));self.assertIn(self.ep['events'][2]['event_id'],{r['event_id'] for r in candidates})
 def test_cloned_baseline_preserves_physical_ids_after_native_reopen(self):
  for backend in pipeline.BACKENDS:
   with self.subTest(backend=backend):
    folder=self.cloned(backend,'clone-reopen');before=physical_records(folder,backend);self.invoke(backend,'query',folder,'native_once');self.assertEqual(physical_records(folder,backend),before)
 def test_actual_exit87_then_fresh_process_native_retry_adds_two_physical_copies(self):
  for backend in pipeline.BACKENDS:
   with self.subTest(backend=backend):
    folder=self.cloned(backend,'native-cut');before=physical_records(folder,backend);self.invoke(backend,'retry',folder,'native_retry',cut=True)
    after_cut=physical_records(folder,backend);self.assertEqual(len(after_cut),5);self.assertTrue(set(before)<=set(after_cut))
    self.invoke(backend,'retry',folder,'native_retry');after=physical_records(folder,backend);self.assertEqual(len(after),6)
    self.assertEqual(sum(r['event_id']==self.ep['events'][0]['event_id'] for r in after.values()),3)
 def test_actual_event_guard_exit_and_resume_suppress_only_same_occurrence(self):
  for backend in pipeline.BACKENDS:
   with self.subTest(backend=backend):
    folder=self.cloned(backend,'event-cut');before=physical_records(folder,backend)
    self.invoke(backend,'retry',folder,'event_admission',cut=True);self.assertEqual(physical_records(folder,backend),before)
    self.invoke(backend,'retry',folder,'event_admission');self.assertEqual(physical_records(folder,backend),before)
 def test_event_vs_content_policy_retains_different_legitimate_new_occurrences(self):
  extra=[event(5,self.ep['events'][0]['text'],'2024/04/04'),event(6,'A later correction: the notebook is now turquoise.','2024/05/05')]
  path=self.root/'legitimate-events.json';dump(path,episode([self.ep['events'][0],*extra]));sources=self.root/'legitimate-sources.json';dump(sources,[e['source_id'] for e in json.loads(path.read_text())['events']])
  for backend in pipeline.BACKENDS:
   for mode,expected_new in [('event_admission',2),('content_admission',1)]:
    with self.subTest(backend=backend,mode=mode):
     folder=self.cloned(backend,'legitimate-'+mode);before=physical_records(folder,backend);self.invoke(backend,'retry',folder,mode,epfile=path,sources=sources)
     after=physical_records(folder,backend);self.assertEqual(len(after)-len(before),expected_new)
     self.assertIn(extra[1]['event_id'],{r['event_id'] for r in after.values()})
     self.assertEqual(extra[0]['event_id'] in {r['event_id'] for r in after.values()},mode=='event_admission')
 def test_native_cache_mismatch_rejects_without_writes_and_valid_manifest_reopens(self):
  bad=self.root/'other-manifest.json';dump(bad,{'fixture':'changed'})
  for backend in pipeline.BACKENDS:
   with self.subTest(backend=backend):
    folder=self.cloned(backend,'cache-mismatch');before=physical_records(folder,backend);self.invoke(backend,'query',folder,'native_once');r=self.invoke(backend,'query',folder,'native_once',manifest=bad,expected=1)
    self.assertIn('Embedding cache manifest differs',r.stderr);self.assertEqual(physical_records(folder,backend),before)
    self.invoke(backend,'query',folder,'native_once');self.assertEqual(physical_records(folder,backend),before)


def load_local(name):
 spec=importlib.util.spec_from_file_location('impact_'+name+'_under_test',HERE/(name+'.py'));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

class GradeBoundaryTests(unittest.TestCase):
 def setUp(self):self.grade=load_local('grade');self.reader=load_local('reader')
 def decisions(self,items):return {'decisions':[dict(id=i['id'],task_correct=True,current_conflict='no',evidence_supported='yes',reason='Synthetic test decision.') for i in items]}
 def test_decision_coverage_fields_types_and_labels_are_strict(self):
  items=[{'id':'a'},{'id':'b'}];valid=self.decisions(items);self.assertEqual(len(self.grade.validate_decisions(valid,items)),2)
  bad=[]
  d=copy.deepcopy(valid);d['unexpected']=1;bad.append(d)
  d=copy.deepcopy(valid);d['decisions'].pop();bad.append(d)
  d=copy.deepcopy(valid);d['decisions'][1]['id']='a';bad.append(d)
  d=copy.deepcopy(valid);d['decisions'][1]['id']='unknown';bad.append(d)
  d=copy.deepcopy(valid);d['decisions'][0]['task_correct']='true';bad.append(d)
  d=copy.deepcopy(valid);d['decisions'][0]['current_conflict']='maybe';bad.append(d)
  d=copy.deepcopy(valid);d['decisions'][0]['evidence_supported']=True;bad.append(d)
  d=copy.deepcopy(valid);d['decisions'][0]['reason']=[];bad.append(d)
  d=copy.deepcopy(valid);d['decisions'][0]['reference']='hidden';bad.append(d)
  for index,d in enumerate(bad):
   with self.subTest(index=index):
    with self.assertRaises(ValueError):self.grade.validate_decisions(d,items)
 def transport(self,response):
  captured={}
  def fake_run(cmd,**kwargs):
   captured['prompt']=kwargs['input'];Path(cmd[cmd.index('-o')+1]).write_text(json.dumps(response))
   return subprocess.CompletedProcess(cmd,0,stdout=json.dumps({'type':'turn.completed','usage':{'input_tokens':0,'output_tokens':0}}),stderr='')
  return captured,fake_run
 def test_grader_transport_accepts_decision_schema_and_remains_blinded(self):
  fixtures=self.grade.calibration()
  self.assertTrue(all(len(item['id'])>=24 and set(item['id'])<=set('0123456789abcdef') for item in fixtures))
  items=fixtures[:2]
  for item in items:item.update(backend='HIDDEN_BACKEND',arm='HIDDEN_ARM',reader='HIDDEN_READER',fixture_name='HIDDEN_FIXTURE_NAME',expected_task_correct='HIDDEN_EXPECTATION')
  captured,fake=self.transport(self.decisions(items))
  with tempfile.TemporaryDirectory() as directory,mock.patch.dict(sys.modules,{'reader':self.reader}),mock.patch.dict(os.environ,{},clear=True),mock.patch.object(self.reader.subprocess,'run',side_effect=fake):
   folder=Path(directory)/'request';status=self.grade.judge_batch(folder,items)
   self.assertEqual(status['status'],'PASS');self.assertEqual(json.loads((folder/'parsed.json').read_text()),self.decisions(items))
   self.assertNotIn('invalid_citations',status)
  self.assertNotIn('HIDDEN_',captured['prompt']);self.assertNotIn('expected_task_correct',captured['prompt'])
 def test_invalid_grader_result_is_retained_but_marked_error(self):
  items=self.grade.calibration()[:2];response=self.decisions(items);response['decisions'][0]['task_correct']='false';_,fake=self.transport(response)
  with tempfile.TemporaryDirectory() as directory,mock.patch.dict(sys.modules,{'reader':self.reader}),mock.patch.dict(os.environ,{},clear=True),mock.patch.object(self.reader.subprocess,'run',side_effect=fake):
   folder=Path(directory)/'request';status=self.grade.judge_batch(folder,items)
   self.assertEqual(status['status'],'ERROR');self.assertTrue((folder/'parsed.json').exists());self.assertEqual(json.loads((folder/'status.json').read_text())['status'],'ERROR')
 def prepare_shared_fixture(self,folder):
  load_pipeline_fixture(folder);self.grade.prepare(folder)
  questions=[];contexts=[];aliases=[]
  for key,reference in [('q1','first gold'),('q2','different gold')]:
   questions.append(dict(key=key,question='Same visible question',question_date='2024/01/01',reference=reference,dataset='longmemeval',category='single-session-user',unanswerable=False))
   contexts.append(dict(case=key,context=[]));aliases.append(dict(case=key,question_key=key,prompt_sha256='same-prompt',backend='hidden',arm='no_context'))
  dump(folder/'evaluator_questions.json',questions);dump(folder/'contexts.json',contexts);dump(folder/'reader_aliases.json',aliases)
  source=json.loads((folder/'protocol.json').read_text());source['evaluator_sha256']=pipeline.sha(folder/'evaluator_questions.json');dump(folder/'protocol.json',source);(folder/'protocol.sha256').write_text(pipeline.sha(folder/'protocol.json')+'\n')
  protocol=dict(reader_source_sha256=self.reader.sha(HERE/'reader.py'),contexts_sha256=self.reader.sha(folder/'contexts.json'),aliases_sha256=self.reader.sha(folder/'reader_aliases.json'),input_hashes={},grading_protocol_sha256=self.grade.sha(folder/'grading_protocol.json'))
  dump(folder/'reader_protocol.json',protocol);(folder/'reader_protocol.sha256').write_text(self.reader.sha(folder/'reader_protocol.json')+'\n')
  for repeat,status in [('r0','PASS'),('r1','ERROR')]:
   root=folder/'reader_results/sol/same-prompt'/repeat;dump(root/'parsed.json',dict(answer='One physical response',cited_event_ids=[],abstain=False));dump(root/'status.json',dict(status=status))
  return folder
 def test_shared_prompt_answers_are_graded_against_each_question_reference(self):
  with tempfile.TemporaryDirectory() as directory,mock.patch.dict(sys.modules,{'pipeline':pipeline,'reader':self.reader}):
   folder=self.prepare_shared_fixture(Path(directory));self.grade.prepare_answers(folder);items=json.loads((folder/'grading_items.json').read_text())
   self.assertEqual(len(items),2);self.assertEqual({i['reference'] for i in items},{'first gold','different gold'});self.assertEqual(len({i['id'] for i in items}),2)
   self.grade.verify_packet(folder)
 def test_grading_packet_detects_items_reference_context_alias_split_and_response_tampering(self):
  with tempfile.TemporaryDirectory() as directory,mock.patch.dict(sys.modules,{'pipeline':pipeline,'reader':self.reader}):
   folder=self.prepare_shared_fixture(Path(directory));self.grade.prepare_answers(folder)
   files=['grading_items.json','evaluator_questions.json','contexts.json','reader_aliases.json','split.json','reader_results/sol/same-prompt/r0/parsed.json','grading_packet.json']
   for name in files:
    with self.subTest(file=name):
     path=folder/name;before=path.read_bytes();path.write_bytes(before+b' ')
     try:
      with self.assertRaises(AssertionError):self.grade.verify_packet(folder)
     finally:path.write_bytes(before)
   self.grade.verify_packet(folder)
 def test_reference_tamper_rejected_before_packet_creation(self):
  with tempfile.TemporaryDirectory() as directory,mock.patch.dict(sys.modules,{'pipeline':pipeline,'reader':self.reader}):
   folder=self.prepare_shared_fixture(Path(directory));path=folder/'evaluator_questions.json';rows=json.loads(path.read_text());rows[0]['reference']='changed after source freeze';dump(path,rows)
   with self.assertRaises(AssertionError):self.grade.prepare_answers(folder)
   self.assertFalse((folder/'grading_packet.json').exists())
 def test_tampered_packet_blocks_judge_invocation(self):
  with tempfile.TemporaryDirectory() as directory,mock.patch.dict(sys.modules,{'pipeline':pipeline,'reader':self.reader}):
   folder=self.prepare_shared_fixture(Path(directory));self.grade.prepare_answers(folder);path=folder/'grading_items.json';path.write_text(path.read_text()+' ')
   with mock.patch.object(self.grade,'judge_batch',side_effect=AssertionError('Judge must not be called')) as request:
    with self.assertRaises(AssertionError):self.grade.run_answers(folder)
    request.assert_not_called()
 def test_locomo_proxy_matches_ast_extracted_pinned_official_functions(self):
  code=r"""
import ast,collections,contextlib,hashlib,io,json,string,sys,types
from pathlib import Path
import regex
from nltk.stem import PorterStemmer
sys.path.insert(0,sys.argv[1]);import grade
source=Path(sys.argv[2]);tree=ast.parse(source.read_text());wanted={'normalize_answer','f1_score','f1','eval_question_answering'}
functions=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in wanted]
assert {node.name for node in functions}==wanted
scope={'regex':regex,'string':string,'Counter':collections.Counter,'ps':PorterStemmer(),'np':types.SimpleNamespace(mean=lambda values:sum(values)/len(values))}
exec(compile(ast.Module(body=functions,type_ignores=[]),str(source),'exec'),scope)
pairs=[('A red notebook.','red notebook'),('red, blue','red, blue'),('red','red, blue'),('coffee and tea','coffee'),('New York and London','New York, London'),('jogging runners','running'),('green notebook','green notebook; irrelevant alternate'),('not mentioned in the conversation','distractor'),('No information available.','distractor'),('','alpha'),('alpha',''),('blue, blue','blue'),('Café and tea','café tea')]
count=0
for category in range(1,6):
 for prediction,reference in pairs:
  with contextlib.redirect_stdout(io.StringIO()):expected=scope['eval_question_answering']([dict(category=category,answer=reference,prediction=prediction,evidence=[])])[0][0]
  actual=grade.locomo_proxy(prediction,reference,category)
  assert abs(actual-expected)<1e-12,(category,prediction,reference,expected,actual)
  count+=1
print(json.dumps({'status':'PASS','proxy_comparisons':count,'pinned_official_source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'bert_imported':False}))
"""
  source=Path('/tmp/beyond-recall-benchmark-feasibility-20261029/locomo_scorer.py');self.assertTrue(source.exists())
  result=subprocess.run([str(pipeline.interpreter('llama_index')),'-c',code,str(HERE),str(source)],capture_output=True,text=True,timeout=60)
  self.assertEqual(result.returncode,0,result.stderr);record=json.loads(result.stdout.strip());self.assertEqual(record['proxy_comparisons'],65)
  dump(HERE/'worker_review_proxy.json',record)

class PilotEvidenceAuditorTests(unittest.TestCase):
 def setUp(self):self.audit=load_local('worker_review_pilot_audit');self.event=event(1,'Synthetic public-fixture fact.');self.records={'point':native_row(self.event)}
 def test_raw_auditor_rejects_changed_event_date_body_source_and_multiplicity(self):
  events={self.event['event_id']:self.event};self.audit.verify_records(self.records,events,{self.event['event_id']:1})
  for key,value in [('occurred_at','changed-date'),('body_sha256','changed-digest'),('source_id','changed-source'),('text','changed-fact')]:
   with self.subTest(field=key):
    forged=copy.deepcopy(self.records);forged['point'][key]=value
    with self.assertRaises(self.audit.AuditError):self.audit.verify_records(forged,events,{self.event['event_id']:1})
  forged=copy.deepcopy(self.records);forged['extra']=dict(forged['point'],physical_id='extra')
  with self.assertRaises(self.audit.AuditError):self.audit.verify_records(forged,events,{self.event['event_id']:1})
 def test_raw_auditor_rejects_candidate_identity_payload_and_score_forgeries(self):
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'candidates.json';queries=[dict(invocation='q',question='A synthetic query')]
   honest=[dict(invocation='q',candidates=[copy.deepcopy(self.records['point'])])];dump(path,honest);self.audit.verify_candidates(path,queries,self.records)
   for key,value in [('physical_id','unknown'),('text','forged'),('occurred_at','wrong-date'),('body_sha256','wrong-digest'),('score',float('nan'))]:
    with self.subTest(field=key):
     forged=copy.deepcopy(honest);forged[0]['candidates'][0][key]=value;dump(path,forged)
     with self.assertRaises(self.audit.AuditError):self.audit.verify_candidates(path,queries,self.records)
   forged=copy.deepcopy(honest);forged[0]['candidates'].append(copy.deepcopy(forged[0]['candidates'][0]));dump(path,forged)
   with self.assertRaises(self.audit.AuditError):self.audit.verify_candidates(path,queries,self.records)
 def test_missing_completion_is_not_ready_and_does_not_inspect_partial_stores(self):
  with tempfile.TemporaryDirectory() as directory,mock.patch.object(self.audit,'physical_records',side_effect=AssertionError('Do not inspect in-progress stores')) as read:
   result=self.audit.audit(Path(directory));self.assertEqual(result['status'],'NOT_READY');read.assert_not_called()

if __name__=='__main__':unittest.main(verbosity=2)
