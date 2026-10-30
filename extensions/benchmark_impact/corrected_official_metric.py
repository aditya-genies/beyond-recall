"""Explicit development-analysis correction of the frozen LoCoMo token proxy.

The frozen grade.py uses Python re for article boundaries; the public scorer
uses the third-party regex module, which treats combining marks differently.
This module changes no generated answer, reference, frozen driver or protocol.
It is an independently written transcription for the string answers in this
study, not a semantic-accuracy measure or a new evaluation algorithm.
"""
from __future__ import annotations
from collections import Counter
from functools import lru_cache
import hashlib
import importlib.metadata
from pathlib import Path
import string

import numpy as np
import regex
from nltk.stem import PorterStemmer

SOURCE_REPOSITORY='https://github.com/snap-research/locomo'
SOURCE_COMMIT='3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376'
SOURCE_PATH='task_eval/evaluation.py'
SOURCE_SHA256='8e3be5d57ff2ff9ec5cd05939592f468c5f3f1fd95d13e431932bdf6bf0fd6fd'
SOURCE_URL=SOURCE_REPOSITORY+'/blob/'+SOURCE_COMMIT+'/'+SOURCE_PATH
ANALYSIS_VERSION='locomo-official-regex-v1'

@lru_cache(maxsize=1)
def _stemmer():return PorterStemmer()

def normalize_answer(text):
 if not isinstance(text,str):raise TypeError('Expected a string answer')
 text=text.replace(',','').lower()
 text=''.join(character for character in text if character not in string.punctuation)
 text=regex.sub(r'\b(a|an|the|and)\b',' ',text)
 return ' '.join(text.split())

def _f1(prediction,reference):
 predicted=[_stemmer().stem(token) for token in normalize_answer(prediction).split()]
 expected=[_stemmer().stem(token) for token in normalize_answer(reference).split()]
 overlap=sum((Counter(predicted)&Counter(expected)).values())
 if not overlap:return 0.
 precision=overlap/len(predicted);recall=overlap/len(expected)
 return (2*precision*recall)/(precision+recall)

def locomo_proxy(prediction,reference,category):
 """Published category-specific token proxy; strings only, categories 1–5."""
 if not isinstance(prediction,str) or not isinstance(reference,str):raise TypeError('Expected string prediction and reference')
 category=str(category)
 if category=='5':return float('no information available' in prediction.lower() or 'not mentioned' in prediction.lower())
 if category=='3':reference=reference.split(';')[0].strip()
 if category=='1':
  proposed=[part.strip() for part in prediction.split(',')]
  required=[part.strip() for part in reference.split(',')]
  return float(np.mean([max(_f1(part,target) for part in proposed) for target in required]))
 if category in ('2','3','4'):return float(_f1(prediction,reference))
 raise ValueError('Unknown LoCoMo category')

def verify_source(path):
 observed=hashlib.sha256(Path(path).read_bytes()).hexdigest()
 if observed!=SOURCE_SHA256:raise ValueError('Pinned official LoCoMo scorer source differs')
 return observed

def provenance():
 return dict(analysis_version=ANALYSIS_VERSION,official_repository=SOURCE_REPOSITORY,
  official_commit=SOURCE_COMMIT,official_source_path=SOURCE_PATH,official_source_sha256=SOURCE_SHA256,
  source_url=SOURCE_URL,runtime_versions={package:importlib.metadata.version(package) for package in ('regex','nltk','numpy')},
  correction='Use official regex article word boundaries; retain frozen-proxy scores and all model outputs separately.',
  interpretation='Category-specific published token overlap/abstention proxy, not semantic task accuracy.')
