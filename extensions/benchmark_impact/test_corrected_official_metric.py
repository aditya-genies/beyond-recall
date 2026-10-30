"""Pure scoring tests; no model calls, BERT imports, generated-output changes."""
import ast
from collections import Counter
import contextlib
import copy
import importlib.util
import io
import os
from pathlib import Path
import string
import unittest

import numpy as np
import regex
from nltk.stem import PorterStemmer

try:from . import corrected_official_metric as metric
except ImportError:import corrected_official_metric as metric


def official_functions(path):
 metric.verify_source(path);tree=ast.parse(Path(path).read_text())
 required={'normalize_answer','f1_score','f1','eval_question_answering'}
 nodes=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in required]
 if {node.name for node in nodes}!=required:raise ValueError('Official scorer function coverage differs')
 scope={'regex':regex,'string':string,'Counter':Counter,'ps':PorterStemmer(),'np':np}
 exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),scope)
 return scope

ASCII_PAIRS=[('A red notebook.','red notebook'),('red, blue','red, blue'),('red','red, blue'),('coffee and tea','coffee'),('New York and London','New York, London'),('jogging runners','running'),('green notebook','green notebook; irrelevant alternate'),('not mentioned in the conversation','distractor'),('No information available.','distractor'),('','alpha'),('alpha',''),('blue, blue','blue'),('Café and tea','café tea')]
UNICODE_PAIRS=[(article+mark+'cat',mark+'cat') for article in ('a','an','and','the') for mark in ('\u0301','\u0300','\u034f','\u05b0','\u0903','\u200d')]+[('the\u0301 cat','\u0301 cat'),('a\u0301','\u0301'),('Café','Cafe\u0301'),('the café','café')]

class CorrectedMetricTests(unittest.TestCase):
 def test_combining_mark_article_boundary_uses_official_regex_semantics(self):
  self.assertEqual(metric.normalize_answer('the\u0301cat'),'the\u0301cat')
  self.assertEqual(metric.locomo_proxy('a\u0301','\u0301',4),0.)
  self.assertEqual(metric.locomo_proxy('the\u0301 cat','\u0301 cat',4),.5)
 def test_category_controls_and_unknown_category(self):
  self.assertEqual(metric.locomo_proxy('red','red, blue',1),.5)
  self.assertEqual(metric.locomo_proxy('green notebook','green notebook; unused',3),1.)
  self.assertEqual(metric.locomo_proxy('Not mentioned.','a distractor',5),1.)
  with self.assertRaises(ValueError):metric.locomo_proxy('x','x',6)
 def test_metric_is_string_only_and_has_no_unreported_unicode_normalization(self):
  with self.assertRaises(TypeError):metric.locomo_proxy(['x'],'x',4)
  self.assertEqual(metric.locomo_proxy('Café','Cafe\u0301',4),0.)
 def test_unknown_official_source_bytes_are_rejected(self):
  import tempfile
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'scorer.py';path.write_text('def f1_score(): pass')
   with self.assertRaises(ValueError):metric.verify_source(path)

class OfficialAstComparisons(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.path=Path(os.environ.get('LOCOMO_OFFICIAL_SCORER','/tmp/beyond-recall-benchmark-feasibility-20261029/locomo_scorer.py'))
  if not cls.path.exists():raise unittest.SkipTest('Provide pinned official scorer at LOCOMO_OFFICIAL_SCORER')
  cls.functions=official_functions(cls.path)
 def compare(self,pairs):
  for category in range(1,6):
   for prediction,reference in pairs:
    with self.subTest(category=category,prediction=prediction,reference=reference),contextlib.redirect_stdout(io.StringIO()):
     expected=self.functions['eval_question_answering']([dict(category=category,answer=reference,prediction=prediction,evidence=[])])[0][0]
     self.assertAlmostEqual(metric.locomo_proxy(prediction,reference,category),expected,places=14)
 def test_original_sixty_five_ascii_style_comparisons(self):self.compare(ASCII_PAIRS)
 def test_one_hundred_forty_unicode_comparisons(self):self.compare(UNICODE_PAIRS)

if __name__=='__main__':unittest.main(verbosity=2)
