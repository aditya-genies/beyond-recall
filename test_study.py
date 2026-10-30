"""Meaningful standard-library checks; local subprocesses and synthetic data only."""
import copy
from contextlib import closing
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

import study
from checks.check_results import expected_case_keys, recompute_case, terminal_oracles


class StandaloneStudyTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory(prefix='standalone-check-')
        self.root=Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def case(self,policy,profile,history):
        value=study.run_case(self.root,policy,profile,history)
        folder=self.root/'state'/f'{policy}__{profile}__{history}'
        recompute_case(value,folder)
        return value,folder

    def test_receipt_preserves_same_plan_retention_but_suppresses_calls(self):
        values=[]
        plans=[]
        for receipt in (0,1):
            value,folder=self.case(f'D1P1R{receipt}','mixed','redelivery_drift')
            values.append(value)
            with closing(sqlite3.connect(folder/'recovery.sqlite')) as connection:
                plans.append(connection.execute('SELECT body FROM decisions').fetchall())
            self.assertTrue(value['selected_terminal'])
            self.assertTrue(value['decision_continuity'])
            self.assertEqual(value['planning_invocations'],1)
        self.assertEqual(plans[0],plans[1])
        self.assertEqual(len(plans[0]),1)
        self.assertEqual(values[0]['committed_effect_calls'],8)
        self.assertEqual(values[1]['committed_effect_calls'],4)

    def test_duplicate_and_wrong_content_oracles_are_distinct(self):
        records=[dict(fact='x=one'),dict(fact='x=one'),dict(fact='y=two')]
        duplicate=terminal_oracles(records,['x=one','y=two'],True)
        self.assertTrue(duplicate['content_correct'])
        self.assertFalse(duplicate['cardinality_correct'])
        self.assertFalse(duplicate['selected_terminal'])
        changed=terminal_oracles([dict(fact='x=one'),dict(fact='y=wrong')],['x=one','y=two'],True)
        self.assertFalse(changed['content_correct'])
        self.assertTrue(changed['cardinality_correct'])
        self.assertFalse(changed['selected_terminal'])

    def test_abrupt_exit_and_new_process_resume_reuses_decision(self):
        value,_=self.case('D1P1R0','mixed','exit_after_first_put_drift')
        self.assertEqual([attempt['returncode'] for attempt in value['attempts']],[87,0])
        self.assertTrue(value['selected_terminal'])
        self.assertEqual(value['planning_invocations'],1)
        self.assertTrue(any(event['event']=='decision_loaded' for event in value['attempts'][1]['events']))
        self.assertTrue(any(event['event']=='abrupt_exit' for event in value['attempts'][0]['events']))

    def test_full_finite_coverage_is_66_cells_for_each_of_eight_policies(self):
        independent=expected_case_keys()
        implementation={(p,q,h) for p in study.POLICIES for q in study.PROFILES for h in study.HISTORIES
                        if h!='lost_delete_reply' or q in ('retire','mixed')}
        self.assertEqual(implementation,independent)
        self.assertEqual(len(independent),528)
        self.assertEqual({sum(key[0]==policy for key in independent) for policy in study.POLICIES},{66})

    def test_unpersisted_decision_remains_a_real_boundary(self):
        folder=self.root/'unpersisted'
        study.setup(folder,'mixed','normal')
        first=study.invoke(folder,'D1P1R1','mixed',0,'before_decision_store')
        self.assertEqual(first['returncode'],87)
        with closing(sqlite3.connect(folder/'recovery.sqlite')) as connection:
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM decisions').fetchone()[0],0)
        with closing(sqlite3.connect(folder/'effects.sqlite')) as connection:
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM committed_actions').fetchone()[0],0)
        second=study.invoke(folder,'D1P1R1','mixed',1,alternative=True)
        value=study.metrics(folder,[first,second],study.FACTS)
        value['history']='before_decision_store_boundary'
        recompute_case(value,folder)
        self.assertEqual(second['returncode'],0)
        self.assertFalse(value['content_correct'])
        self.assertFalse(value['decision_continuity'])
        self.assertEqual(value['planning_invocations'],2)

    def test_independent_checker_rejects_forged_metric(self):
        value,folder=self.case('D1P1R1','insert','normal')
        value['selected_terminal']=False
        with self.assertRaisesRegex(AssertionError,'selected_terminal'):
            recompute_case(value,folder)

    def test_bounded_and_disabled_source_controls_are_discriminating(self):
        for history,omitted_predicate in [('bounded_input','enabled=1'),('superseded_input','turn<=1')]:
            value,folder=self.case('D1P1R1','insert',history)
            self.assertTrue(value['selected_terminal'])
            with closing(sqlite3.connect(folder/'recovery.sqlite')) as connection:
                unfiltered=connection.execute(f'SELECT facts FROM conversation WHERE epoch=0 AND {omitted_predicate} ORDER BY turn').fetchall()
            facts=[fact for row in unfiltered for fact in json.loads(row[0])]
            wrong_plan=study.make_plan(facts,'insert',False)
            self.assertNotEqual({op['fact'] for op in wrong_plan if op['kind']=='put'},set(study.FACTS))
            forged=copy.deepcopy(value)
            event=next(event for attempt in forged['attempts'] for event in attempt['events'] if event['event']=='source_selected')
            event['facts']=facts
            with self.assertRaisesRegex(AssertionError,'source selection'):
                recompute_case(forged,folder)

    def test_generation_handshake_removes_stale_rows_and_excludes_cleanup_from_calls(self):
        value,_=self.case('D1P1R1','mixed','reset_during_effects')
        self.assertTrue(value['selected_terminal'])
        self.assertEqual(value['physical_records'],[])
        self.assertEqual(value['committed_effect_calls'],4)
        self.assertTrue(any(event['event']=='cleanup' for attempt in value['attempts'] for event in attempt['events']))
        self.assertTrue(all(action['kind'] in ('put','delete') for action in value['committed_actions']))

    def test_lost_delete_reply_repeats_a_call_without_duplicate_rows(self):
        value,_=self.case('D1P1R0','retire','lost_delete_reply')
        self.assertEqual([attempt['returncode'] for attempt in value['attempts']],[74,0])
        self.assertTrue(value['selected_terminal'])
        self.assertEqual(sum(action['kind']=='delete' for action in value['committed_actions']),2)
        self.assertEqual(len(value['physical_records']),3)

    def test_stable_addresses_do_not_preserve_unsaved_changed_decision(self):
        value,_=self.case('D1P0R0','insert','exit_after_first_put_drift')
        self.assertFalse(value['content_correct'])
        self.assertTrue(value['cardinality_correct'])
        self.assertFalse(value['decision_continuity'])


if __name__=='__main__':
    unittest.main()
