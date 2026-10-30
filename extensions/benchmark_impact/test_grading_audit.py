"""Stdlib-only negative fixtures for the independent grading auditor.

Run with either:
  python -m unittest -v extensions.benchmark_impact.test_grading_audit
  python -I -S extensions/benchmark_impact/test_grading_audit.py

Load the actual checker definitions from its AST rather than importing the full
audit program, whose unrelated token-metric import requires scientific packages.
No validation logic is transcribed, no metric dependency is mocked, and no data,
model/runtime, network, or full-pilot artifact is needed.
"""
from __future__ import annotations

import ast
from pathlib import Path
import unittest


def _load_checker():
    path = Path(__file__).with_name('worker_review_grading_audit.py')
    source = ast.parse(path.read_text(), filename=str(path))
    wanted = {'AuditError', 'need', 'decision_rows'}
    definitions = [node for node in source.body
                   if isinstance(node, (ast.ClassDef, ast.FunctionDef))
                   and node.name in wanted]
    if len(definitions) != len(wanted) or {node.name for node in definitions} != wanted:
        raise AssertionError('Expected unique live grading-checker definitions')
    namespace = {}
    module = ast.Module(body=definitions, type_ignores=[])
    exec(compile(module, str(path), 'exec'), namespace)
    return namespace['decision_rows'], namespace['AuditError']


decision_rows, AuditError = _load_checker()


class GradingAuditorNegativeTests(unittest.TestCase):
    def setUp(self):
        self.items = [{'id': 'a'}, {'id': 'b'}]
        self.value = {'decisions': [
            {'id': identity, 'task_correct': True, 'current_conflict': 'no',
             'evidence_supported': 'yes', 'reason': 'Synthetic checker fixture.'}
            for identity in ('a', 'b')
        ]}

    def test_valid_coverage(self):
        self.assertEqual(len(decision_rows(self.value, self.items)), 2)

    def test_duplicate_identity_rejected(self):
        self.value['decisions'][1]['id'] = 'a'
        with self.assertRaises(AuditError):
            decision_rows(self.value, self.items)

    def test_missing_decision_rejected(self):
        self.value['decisions'].pop()
        with self.assertRaises(AuditError):
            decision_rows(self.value, self.items)

    def test_unrequested_identity_rejected(self):
        self.value['decisions'][1]['id'] = 'unrequested'
        with self.assertRaises(AuditError):
            decision_rows(self.value, self.items)

    def test_integer_is_not_boolean(self):
        self.value['decisions'][0]['task_correct'] = 1
        with self.assertRaises(AuditError):
            decision_rows(self.value, self.items)

    def test_invalid_auxiliary_enum_rejected(self):
        self.value['decisions'][0]['current_conflict'] = 'correct'
        with self.assertRaises(AuditError):
            decision_rows(self.value, self.items)

    def test_unrequested_label_rejected(self):
        self.value['decisions'][0]['arm'] = 'leaked-arm'
        with self.assertRaises(AuditError):
            decision_rows(self.value, self.items)


if __name__ == '__main__':
    unittest.main(verbosity=2)
