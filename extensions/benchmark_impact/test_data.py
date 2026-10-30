"""Small original fixtures and meaningful corruption checks; no model calls/data downloads."""
import copy
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from extensions.benchmark_impact import data
from extensions.benchmark_impact import audit_source_data as auditor


def lme(qid='q-A',repeated=False):
 turns=[{'role':'user','content':'The notebook is blue.','has_answer':True},
        {'role':'assistant','content':'I will remember the blue notebook.','has_answer':False}]
 return dict(question_id=qid,question_type='single-session-user',question='What color is the notebook?',
  question_date='2024/03/03 (Sun) 13:00',answer='blue',answer_session_ids=['public-s1'],
  haystack_session_ids=['public-s1','public-s1' if repeated else 'public-s2'],
  haystack_dates=['2024/01/01 (Mon) 12:00','2024/02/02 (Fri) 12:00'],
  haystack_sessions=[turns,copy.deepcopy(turns) if repeated else [{'role':'user','content':'An unrelated later observation.'}]])

def locomo():
 return dict(sample_id='conversation-A',conversation={
  'speaker_a':'Alice','speaker_b':'Bob',
  'session_10':[dict(dia_id='D10:1',speaker='Bob',text='A later independent observation.')],
  'session_10_date_time':'10 May 2024',
  'session_1':[dict(dia_id='D1:1',speaker='Alice',text='A blue notebook is here.')],
  'session_1_date_time':'1 May 2024'},qa=[
  dict(question='What is here?',answer='a blue notebook',evidence=['D1:1'],category=1),
  dict(question='Which unmentioned vehicle was bought?',adversarial_answer='A distracting invented van',evidence=['D1:1'],category=5)])

def adapted_lme(row):
 episodes,questions=data.lme_rows([row],{row['question_id']:'cluster-A'})
 return next(iter(episodes.values())).participant(),questions[0]

class DataBoundaryTests(unittest.TestCase):
 def test_lme_strips_labels_and_preserves_dates_roles_text_order(self):
  row=lme();row['haystack_sessions'][0][0].update(expected_ids=['secret'],reference='secret',category='secret')
  payload,_=adapted_lme(row);self.assertTrue(auditor.validate_alignment(payload,auditor.lme_flat(row)))
  self.assertEqual(set(payload),{'scope','events'})
  self.assertTrue(all(set(event)==auditor.EVENT_FIELDS for event in payload['events']))
 def test_evaluator_label_poisoning_cannot_change_lme_ingestion(self):
  original=lme();expected,_=adapted_lme(original);poisoned=copy.deepcopy(original)
  poisoned.update(question='EVALUATOR-ONLY-QUESTION',answer='EVALUATOR-ONLY-REFERENCE',question_type='EVALUATOR-ONLY-CATEGORY',answer_session_ids=[],question_date='EVALUATOR-ONLY-QUERY-DATE')
  for turns in poisoned['haystack_sessions']:
   for turn in turns:turn['has_answer']=not turn.get('has_answer',False)
  actual,_=adapted_lme(poisoned);self.assertEqual(actual,expected)
 def test_lme_question_date_comes_from_selected_row_and_is_query_only(self):
  row=lme();payload,q=adapted_lme(row)
  self.assertEqual(q.question_date,row['question_date'])
  self.assertNotIn(row['question_date'],json.dumps(payload))
 def test_repeated_upstream_session_occurrences_keep_distinct_identity(self):
  row=lme(repeated=True);payload,_=adapted_lme(row)
  self.assertTrue(auditor.validate_alignment(payload,auditor.lme_flat(row)))
  self.assertEqual(len({e['event_id'] for e in payload['events']}),4)
  self.assertNotEqual(payload['events'][0]['source_id'],payload['events'][2]['source_id'])
 def test_replay_of_same_row_retains_identical_occurrence_ids_and_times(self):
  row=lme(repeated=True);a,_=adapted_lme(row);b,_=adapted_lme(copy.deepcopy(row));self.assertEqual(a,b)
 def test_recontextualized_questions_do_not_reuse_global_source_ids(self):
  first=lme('q-A');second=lme('q-B');second['haystack_dates']=['2025/01/01','2025/02/02']
  a,_=adapted_lme(first);b,_=adapted_lme(second)
  self.assertTrue({e['event_id'] for e in a['events']}.isdisjoint({e['event_id'] for e in b['events']}))
  self.assertTrue({e['source_id'] for e in a['events']}.isdisjoint({e['source_id'] for e in b['events']}))
 def test_full_and_oracle_variants_preserve_their_own_query_dates_and_histories(self):
  full=lme();oracle=copy.deepcopy(full);oracle['question_date']='2023/01/01 (Sun) 13:00'
  for key in ['haystack_session_ids','haystack_dates','haystack_sessions']:oracle[key]=oracle[key][:1]
  files={'locomo10.json':[locomo()],'longmemeval_oracle.json':[oracle],'longmemeval_s_cleaned.json':[full]}
  observed={}
  for variant,row in [('full',full),('oracle',oracle)]:
   with mock.patch.object(data,'load_pinned',side_effect=lambda cache,name:copy.deepcopy(files[name])):
    episodes,questions,_,_=data.corpus('/unused',variant)
   q=next(q for q in questions if q.dataset=='longmemeval');self.assertEqual(q.question_date,row['question_date'])
   payload=episodes[q.episode_scope].participant();self.assertTrue(auditor.validate_alignment(payload,auditor.lme_flat(row)))
   observed[variant]=len(payload['events'])
  self.assertGreater(observed['full'],observed['oracle'])
 def test_independent_same_text_turns_are_not_content_hash_identity(self):
  a=data.make_event('synthetic','source',0,'date','user','identical text')
  b=data.make_event('synthetic','source',1,'date','user','identical text')
  self.assertNotEqual(a.event_id,b.event_id);self.assertEqual(a.source_id,b.source_id)
 def test_changed_literal_does_not_reassign_source_occurrence(self):
  a=data.make_event('synthetic','source',0,'date','user','before')
  b=data.make_event('synthetic','source',0,'date','user','after')
  self.assertEqual(a.event_id,b.event_id)
 def test_locomo_numeric_session_order_and_speakers(self):
  row=locomo();episodes,questions=data.locomo_rows([row]);payload=episodes[questions[0].episode_scope].participant()
  self.assertTrue(auditor.validate_alignment(payload,auditor.locomo_flat(row)[0]))
  self.assertEqual([e['speaker'] for e in payload['events']],['Alice','Bob'])
 def test_released_caption_is_marked_and_other_annotations_are_ignored(self):
  row=locomo();row['conversation']['session_1'][0].update(blip_caption='A released depiction of a notebook.',reference='EVALUATOR-ONLY')
  episodes,questions=data.locomo_rows([row]);payload=episodes[questions[0].episode_scope].participant()
  self.assertTrue(auditor.validate_alignment(payload,auditor.locomo_flat(row)[0]))
  self.assertIn('Released image caption: A released depiction of a notebook.',payload['events'][0]['text'])
  self.assertNotIn('EVALUATOR-ONLY',json.dumps(payload))
 def test_locomo_category5_distractor_is_not_gold_answer(self):
  row=locomo();_,questions=data.locomo_rows([row]);q=questions[1]
  self.assertTrue(q.unanswerable);self.assertEqual(q.reference,'Not mentioned in the conversation.')
  self.assertNotEqual(q.reference,row['qa'][1]['adversarial_answer'])
 def test_unanswerable_antecedents_cannot_be_positive_answer_support(self):
  _,questions=data.locomo_rows([locomo()]);q=questions[1]
  self.assertTrue(q.expected_events)  # Upstream antecedent/distractor references remain recorded.
  self.assertTrue(auditor.validate_support_metric(q,None))
  for value in [0,1,.5]:
   with self.subTest(value=value):
    with self.assertRaisesRegex(auditor.AuditError,'cannot receive positive-support'):auditor.validate_support_metric(q,value)
  _,abstention=adapted_lme(lme('q-A_abs'));self.assertTrue(auditor.validate_support_metric(abstention,None))
  with self.assertRaises(auditor.AuditError):auditor.validate_support_metric(abstention,1)
 def test_missing_gold_locations_cannot_be_counted_as_retrieval_failures(self):
  row=locomo();row['qa'][0]['evidence']=['D99:1'];_,questions=data.locomo_rows([row]);q=questions[0]
  self.assertTrue(q.missing_gold_locations);self.assertTrue(auditor.validate_support_metric(q,None))
  with self.assertRaises(auditor.AuditError):auditor.validate_support_metric(q,0)
 def test_locomo_question_reference_category_poison_does_not_change_ingestion(self):
  row=locomo();episodes,_=data.locomo_rows([row]);poisoned=copy.deepcopy(row)
  for q in poisoned['qa']:q.update(question='PRIVATE-Q',answer='PRIVATE-A',category=2,evidence=[],adversarial_answer='PRIVATE-DISTRACTOR')
  actual,_=data.locomo_rows([poisoned]);self.assertEqual(episodes,actual)
 def test_transitive_evidence_components_and_order_invariance(self):
  rows=[dict(question_id='a',answer_session_ids=['x']),dict(question_id='b',answer_session_ids=['x','y']),dict(question_id='c',answer_session_ids=['y']),dict(question_id='d',answer_session_ids=['z'])]
  groups=data.evidence_components(rows);reverse=data.evidence_components(list(reversed(rows)))
  self.assertEqual(groups,reverse);self.assertEqual(groups['a'],groups['c']);self.assertNotEqual(groups['a'],groups['d'])
 def test_unaligned_session_lists_are_rejected(self):
  row=lme();row['haystack_dates'].pop()
  with self.assertRaises(ValueError):adapted_lme(row)
 def test_duplicate_locomo_dialog_ids_are_rejected(self):
  row=locomo();row['conversation']['session_10'][0]['dia_id']='D1:1'
  with self.assertRaises(ValueError):data.locomo_rows([row])
 def test_unknown_corpus_variant_rejected_before_reading_cache(self):
  with mock.patch.object(data,'load_pinned',side_effect=AssertionError('Unknown variant read a source file')):
   with self.assertRaises(ValueError):data.corpus('/unused','typo-full')
 def test_modified_source_bytes_are_rejected(self):
  with tempfile.TemporaryDirectory() as folder:
   Path(folder,'locomo10.json').write_text('[]')
   with self.assertRaisesRegex(ValueError,'digest differs'):data.load_pinned(folder,'locomo10.json')

class IndependentAuditorForgeryTests(unittest.TestCase):
 def setUp(self):self.row=lme();self.payload,_=adapted_lme(self.row)
 def test_rejects_nested_evaluator_fields(self):
  for field in ['has_answer','expected_ids','expected_events','reference','answer','category','question_type']:
   with self.subTest(field=field):
    forged=copy.deepcopy(self.payload);forged['events'][0][field]='LEAK'
    with self.assertRaisesRegex(auditor.AuditError,'evaluator/unknown'):auditor.validate_payload(forged)
 def test_rejects_episode_level_evaluator_label(self):
  forged=copy.deepcopy(self.payload);forged['reference']='LEAK'
  with self.assertRaisesRegex(auditor.AuditError,'evaluator/unknown'):auditor.validate_payload(forged)
 def test_rejects_label_smuggled_into_allowed_text(self):
  forged=copy.deepcopy(self.payload);forged['events'][0]['text']+=' GOLD-ANSWER'
  with self.assertRaisesRegex(auditor.AuditError,'differs from selected raw'):auditor.validate_alignment(forged,auditor.lme_flat(self.row))
 def test_rejects_incorrect_date_role_and_turn_order(self):
  for field,value in [('occurred_at','wrong date'),('speaker','assistant')]:
   with self.subTest(field=field):
    forged=copy.deepcopy(self.payload);forged['events'][0][field]=value
    with self.assertRaisesRegex(auditor.AuditError,'differs from selected raw'):auditor.validate_alignment(forged,auditor.lme_flat(self.row))
  forged=copy.deepcopy(self.payload);forged['events'].reverse()
  with self.assertRaisesRegex(auditor.AuditError,'differs from selected raw'):auditor.validate_alignment(forged,auditor.lme_flat(self.row))
 def test_rejects_exact_and_nonmatching_duplicate_event_ids(self):
  for changed in [False,True]:
   forged=copy.deepcopy(self.payload);forged['events'].append(copy.deepcopy(forged['events'][0]))
   if changed:forged['events'][-1]['text']='different event under same ID'
   with self.assertRaisesRegex(auditor.AuditError,'Repeated participant event identity'):auditor.validate_payload(forged)
 def test_rejects_colliding_source_ids_across_distinct_occurrences(self):
  forged=copy.deepcopy(self.payload);forged['events'][-1]['source_id']=forged['events'][0]['source_id']
  with self.assertRaisesRegex(auditor.AuditError,'Different source occurrences'):auditor.validate_alignment(forged,auditor.lme_flat(self.row))
 def test_rejects_source_id_changes_within_one_occurrence(self):
  forged=copy.deepcopy(self.payload);forged['events'][1]['source_id']='0'*24
  with self.assertRaisesRegex(auditor.AuditError,'One source occurrence'):auditor.validate_alignment(forged,auditor.lme_flat(self.row))
 def test_rejects_plain_evaluator_identity_in_participant_metadata(self):
  forged=copy.deepcopy(self.payload);forged['events'][0]['event_id']='question-A/answer-session'
  with self.assertRaisesRegex(auditor.AuditError,'opaque encoding'):auditor.validate_payload(forged)
 def test_rejects_dropped_source_turn(self):
  forged=copy.deepcopy(self.payload);forged['events'].pop()
  with self.assertRaisesRegex(auditor.AuditError,'turn count'):auditor.validate_alignment(forged,auditor.lme_flat(self.row))
 def test_split_audit_distinguishes_gold_and_background_overlap(self):
  dev=lme('dev');overlap=lme('held-overlap');safe=lme('held-safe')
  overlap.update(answer_session_ids=['other-answer'],haystack_session_ids=['other-answer','public-s2'])
  safe.update(answer_session_ids=['safe-answer'],haystack_session_ids=['safe-answer','safe-background'])
  rows=[dev,overlap,safe];_,questions=data.lme_rows(rows,{'dev':'dev-group','held-overlap':'held1','held-safe':'held2'})
  held=[q.key for q in questions if q.source_question_id!='dev']
  split=dict(lme_development_evidence_components=['dev-group'],held_out_question_keys=held)
  report=auditor.split_observations(rows,questions,split)
  self.assertEqual(report['shared_gold_session_ids'],0);self.assertEqual(report['shared_full_history_session_ids'],1)
  self.assertEqual(report['strict_candidate_question_ids'],['held-safe'])
  forged=copy.deepcopy(split);forged['held_out_question_keys'].append(next(q.key for q in questions if q.source_question_id=='dev'))
  with self.assertRaisesRegex(auditor.AuditError,'outside the gold-component'):auditor.split_observations(rows,questions,forged)
 def test_rejects_duplicate_raw_question_identity(self):
  row=lme()
  with self.assertRaisesRegex(auditor.AuditError,'Repeated raw question ID'):auditor.component_partition([row,row],'answer_session_ids')

if __name__=='__main__':unittest.main(verbosity=2)
