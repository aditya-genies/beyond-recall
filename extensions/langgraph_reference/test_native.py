import contextlib
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from . import runner
from .verify_results import verify_case, read_native


class NativeCheckpointTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='native-reference-')
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def run_case(self, profile, history):
        case = runner.run_case(self.root, profile, history)
        folder = self.root / 'state' / f'langgraph_native__{profile}__{history}'
        verify_case(case, folder)
        return case, folder

    def test_native_planner_checkpoint_survives_process_exit_before_effects(self):
        case, folder = self.run_case('mixed', 'exit_after_prepare_drift')
        self.assertEqual([row['returncode'] for row in case['attempts']], [87, 0])
        self.assertNotEqual(case['attempts'][0]['pid'], case['attempts'][1]['pid'])
        self.assertEqual(case['attempts'][0]['native_snapshot']['next'], ['apply_effects'])
        self.assertEqual(case['planning_invocations'], 1)
        self.assertTrue(case['selected_terminal'])
        self.assertEqual(read_native(folder)['next'], [])

    def test_native_partial_effect_resume_preserves_targets_and_decision(self):
        case, _ = self.run_case('mixed', 'exit_after_first_put_drift')
        self.assertTrue(case['selected_terminal'])
        self.assertTrue(case['decision_continuity'])
        self.assertEqual(case['committed_effect_calls'], 5)
        self.assertEqual({row['fact'] for row in case['physical_records']}, set(runner.study.FACTS))

    def test_completed_checkpoint_skips_changed_redelivery(self):
        case, _ = self.run_case('mixed', 'redelivery_drift')
        self.assertEqual(case['committed_effect_calls'], 4)
        self.assertEqual(case['planning_invocations'], 1)
        self.assertTrue(any(event['event'] == 'native_completed_checkpoint_hit' for event in case['attempts'][1]['events']))

    def test_effects_before_native_completion_are_replayed_after_exit(self):
        case, _ = self.run_case('insert', 'exit_after_effects_drift')
        self.assertEqual(case['committed_effect_calls'], 6)
        self.assertEqual(case['attempts'][0]['native_snapshot']['next'], ['apply_effects'])
        self.assertTrue(case['selected_terminal'])

    def test_exit_after_native_completion_does_not_repeat_effects(self):
        case, _ = self.run_case('mixed', 'exit_after_finalize_drift')
        self.assertEqual(case['attempts'][0]['native_snapshot']['next'], [])
        self.assertEqual(case['committed_effect_calls'], 4)
        self.assertTrue(case['selected_terminal'])

    def test_generation_change_cancels_native_pending_effects(self):
        before, _ = self.run_case('mixed', 'reset_before_retry')
        during, _ = self.run_case('mixed', 'reset_during_effects')
        self.assertEqual(before['physical_records'], [])
        self.assertEqual(during['physical_records'], [])
        self.assertTrue(before['selected_terminal'])
        self.assertTrue(during['selected_terminal'])

    def test_shared_source_controls_and_lost_delete_reply(self):
        for history in ('bounded_input', 'superseded_input', 'lost_delete_reply'):
            case, _ = self.run_case('mixed', history)
            self.assertTrue(case['selected_terminal'])
        self.assertEqual(case['attempts'][0]['returncode'], 74)

    def test_independent_checker_rejects_tampered_native_plan(self):
        from types import SimpleNamespace
        case, folder = self.run_case('insert', 'normal')
        args = SimpleNamespace(profile='insert', alternative=False, fault='', attempt=-1)
        with runner.native_graph(folder, args, log_writes=False) as (graph, _):
            current = graph.get_state({'configurable': {'thread_id': 'intent-alpha'}})
            changed = json.loads(json.dumps(current.values['plan']))
            changed[0]['fact'] = 'tone=tampered'
            graph.update_state({'configurable': {'thread_id': 'intent-alpha'}}, {'plan': changed})
        with self.assertRaisesRegex(AssertionError, 'native stored plan'):
            verify_case(case, folder)

    def test_repeated_fresh_runs_have_same_deterministic_effect_state(self):
        case, _ = self.run_case('mixed', 'exit_after_first_put_drift')
        with tempfile.TemporaryDirectory(prefix='native-repeat-') as directory:
            repeat = runner.run_case(Path(directory), 'mixed', 'exit_after_first_put_drift')
        self.assertEqual(case['physical_records'], repeat['physical_records'])
        for metric in ('selected_terminal', 'decision_continuity', 'planning_invocations', 'committed_effect_calls'):
            self.assertEqual(case[metric], repeat[metric])


if __name__ == '__main__':
    unittest.main()
