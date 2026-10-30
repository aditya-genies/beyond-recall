"""Independent read-only arithmetic/store audit of retained ranking diagnostics.

This program never opens a native client, embeds text, searches, or calls a model.
Only SQLite read-only connections, restricted point decoding, and archived JSON
are used. Context selection and score arithmetic are independently implemented.
"""
from __future__ import annotations

import argparse
import base64
from collections import Counter
import copy
import hashlib
import importlib.metadata
import io
import json
import math
from pathlib import Path
import pickle
import sqlite3
import sys
import unittest

HERE = Path(__file__).resolve().parent
TOL = 1e-12
COMPONENTS = ('semantic_score', 'bm25_score', 'entity_boost', 'max_possible_score', 'final_score')


class AuditError(ValueError):
    pass


def need(test, message):
    if not test:
        raise AuditError(message)


def load(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def objsha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


class PointDecoder(pickle.Unpickler):
    def find_class(self, module, name):
        if module == 'qdrant_client.http.models.models' and name in ('PointStruct', 'SparseVector'):
            from qdrant_client.http.models import models
            return getattr(models, name)
        raise AuditError('Unapproved class in native point data')


def points(folder):
    path = folder / 'qdrant/collection/study_memories/storage.sqlite'
    connection = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)
    try:
        need(connection.execute('PRAGMA integrity_check').fetchone()[0] == 'ok', 'Physical SQLite corruption')
        result = {}
        for key, blob in connection.execute('SELECT id,point FROM points'):
            identity = PointDecoder(io.BytesIO(base64.b64decode(key))).load()
            point = PointDecoder(io.BytesIO(blob)).load()
            need(point.id == identity and identity not in result, 'Duplicate/mismatched physical key')
            need(point.payload['user_id'] == 'independent-benchmark-participant', 'Unexpected physical user scope')
            result[identity] = dict(payload=point.payload, vector=point.model_dump()['vector'], point_sha256=hashlib.sha256(blob).hexdigest())
        return result
    finally:
        connection.close()


def normalized(row):
    meta = row['metadata']
    return dict(physical_id=row['id'], text=row['memory'], event_id=meta['study_event_id'],
                source_id=meta['study_source_id'], occurred_at=meta['study_date'],
                body_sha256=meta['study_body_sha256'], score=row['score'])


def selected(rows):
    """Independent whole-record, 10-item, 12000-byte logical-event selection."""
    result, seen = [], set()
    for row in rows:
        meta = row['metadata']
        if meta['study_event_id'] in seen:
            continue
        if len(result) == 10:
            break
        item = dict(event_id=meta['study_event_id'], source_id=meta['study_source_id'],
                    date=meta['study_date'], text=row['memory'])
        candidate = [*result, item]
        if len(json.dumps(candidate, ensure_ascii=True, separators=(',', ':')).encode()) > 12000:
            continue
        result.append(item)
        seen.add(item['event_id'])
    return result


def validate_rows(rows, physical, full=False):
    ids = [row['id'] for row in rows]
    need(len(ids) == len(set(ids)), 'Repeated physical ID in query output')
    need(set(ids) <= set(physical), 'Query references nonexistent physical point')
    if full:
        need(set(ids) == set(physical), 'Full-pool query omitted physical points')
    previous = math.inf
    for row in rows:
        payload = physical[row['id']]['payload']
        expected_meta = {key: value for key, value in payload.items()
                         if key not in {'data', 'hash', 'created_at', 'updated_at', 'id', 'text_lemmatized',
                                        'user_id', 'agent_id', 'run_id', 'actor_id', 'role', 'attributed_to', 'expiration_date'}}
        need(row['metadata'] == expected_meta, 'Native result metadata differs from persisted payload')
        for output, source in [('memory', 'data'), ('hash', 'hash'), ('created_at', 'created_at'), ('updated_at', 'updated_at'), ('user_id', 'user_id'), ('role', 'role')]:
            need(row.get(output) == payload.get(source), 'Native result/persisted payload mismatch: ' + output)
        details = row['score_details']
        need(set(details) == {*COMPONENTS, 'raw_score', 'threshold'}, 'Unexpected score explanation schema')
        need(all(type(value) in (int, float) and math.isfinite(value) for value in details.values()), 'Nonfinite/nonnumeric score component')
        need(details['threshold'] == 0 and details['semantic_score'] >= 0, 'Unexpected semantic gate')
        need(0 <= details['bm25_score'] <= 1 and details['entity_boost'] >= 0, 'Invalid normalized signal')
        need(details['max_possible_score'] in (1, 1.5, 2, 2.5), 'Unexpected signal divisor')
        raw = details['semantic_score'] + details['bm25_score'] + details['entity_boost']
        final = min(raw / details['max_possible_score'], 1.0)
        need(abs(details['raw_score'] - raw) <= TOL, 'Incorrect additive raw-score arithmetic')
        need(abs(details['final_score'] - final) <= TOL and abs(row['score'] - final) <= TOL, 'Incorrect final-score arithmetic')
        need(row['score'] <= previous + TOL, 'Query output is not descending by score')
        previous = row['score']
    return len(rows)


def comparison(clean, replay):
    a, b = {r['id']: r for r in clean}, {r['id']: r for r in replay}
    common = set(a) & set(b)
    ca, cb = selected(clean), selected(replay)
    ia, ib = [r['event_id'] for r in ca], [r['event_id'] for r in cb]
    return dict(common_original_point_scores=len(common),
                component_changes_at_1e12={key: sum(abs(a[i]['score_details'][key] - b[i]['score_details'][key]) > TOL for i in common) for key in COMPONENTS},
                same_selected_event_order=ia == ib, same_selected_event_set=set(ia) == set(ib),
                clean_context=ca, retry_context=cb)


def strict_reversals(clean, replay):
    a = {r['id']: r for r in clean}; b = {r['id']: r for r in replay}
    ordered = [r for r in clean if r['id'] in b]
    witness = None
    for i, first in enumerate(ordered):
        for second in ordered[i + 1:]:
            x, y = first['id'], second['id']
            if a[x]['score'] > a[y]['score'] + TOL and b[x]['score'] + TOL < b[y]['score']:
                witness = dict(first=x, second=y, clean_margin=a[x]['score'] - a[y]['score'], replay_margin=b[y]['score'] - b[x]['score'])
                break
        if witness:
            break
    ca, cb = selected(clean), selected(replay)
    lost = {r['event_id'] for r in ca} - {r['event_id'] for r in cb}
    gained = {r['event_id'] for r in cb} - {r['event_id'] for r in ca}
    event_to_id = {r['metadata']['study_event_id']: r['id'] for r in clean}
    switch = None
    for old in sorted(lost):
        for new in sorted(gained):
            x, y = event_to_id[old], event_to_id[new]
            if a[x]['score'] > a[y]['score'] + TOL and b[x]['score'] + TOL < b[y]['score']:
                switch = dict(lost_event=old, gained_event=new, clean_margin=a[x]['score'] - a[y]['score'], replay_margin=b[y]['score'] - b[x]['score'])
                break
        if switch:
            break
    return witness, switch


def df_stats(records):
    frequencies = Counter()
    n = 0
    for point in records.values():
        sparse = point['vector'].get('bm25')
        if sparse is not None:
            n += 1
            frequencies.update(set(sparse['indices']))
    return n, frequencies


def audit(pilot, ranking, fixed):
    files = []
    def tracked(path):
        files.append(path)
        return load(path)
    rp, fp = tracked(ranking / 'protocol.json'), tracked(fixed / 'protocol.json')
    for folder in (ranking, fixed):
        need((folder / 'protocol.sha256').read_text().strip() == sha(folder / 'protocol.json'), 'Protocol SHA sidecar mismatch')
        files.append(folder / 'protocol.sha256')
    need(rp['pilot_protocol_sha256'] == fp['pilot_protocol_sha256'] == sha(pilot / 'protocol.json'), 'Pilot protocol linkage mismatch')
    need(rp['pilot_contexts_sha256'] == sha(pilot / 'contexts.json'), 'Pilot context linkage mismatch')
    need(fp['parent_probe_protocol_sha256'] == sha(ranking / 'protocol.json') and fp['parent_report_sha256'] == sha(ranking / 'report.json'), 'Fixed-IDF parent linkage mismatch')
    source_root = Path('/tmp/beyond-recall-mem0-public-20261029')
    local = Path(importlib.metadata.distribution('qdrant-client').locate_file('qdrant_client/local/local_collection.py'))
    sources = dict(zip(('probe_ranking.py', 'memory_worker.py', 'main.py', 'scoring.py', 'qdrant.py', 'local_collection.py'),
                       (HERE / 'probe_ranking.py', HERE / 'memory_worker.py', source_root / 'mem0/memory/main.py', source_root / 'mem0/utils/scoring.py', source_root / 'mem0/vector_stores/qdrant.py', local)))
    for name, path in sources.items():
        need(sha(path) == rp['source_hashes'][name], 'Source pin differs: ' + name)
    need(sha(HERE / 'probe_fixed_idf.py') == fp['runner_sha256'], 'Fixed-IDF runner pin mismatch')
    need(fp['worker_sha256'] == sha(sources['memory_worker.py']) and fp['native_qdrant_adapter_sha256'] == sha(sources['qdrant.py']) and fp['native_idf_implementation_sha256'] == sha(local), 'Fixed-IDF source pin mismatch')
    files.extend(sources.values()); files.append(HERE / 'probe_fixed_idf.py')
    report, fixed_report, summary = tracked(ranking / 'report.json'), tracked(fixed / 'report.json'), tracked(ranking / 'summary.json')
    need(report['protocol_sha256'] == sha(ranking / 'protocol.json') and fixed_report['protocol_sha256'] == sha(fixed / 'protocol.json'), 'Report/protocol mismatch')
    contexts = tracked(pilot / 'contexts.json')
    context_by_key = {(r['backend'], r['question_key'], r['arm']): r['context'] for r in contexts}
    prior = tracked(HERE / 'worker_review_pilot_v2.json')
    prior_by_scope = {r['scope']: r for r in prior['cases'] if r['backend'] == 'mem0_raw'}
    cases = {(r['scope'], r['question_key']): r for r in report['cases']}
    fixed_cases = {(r['scope'], r['question_key']): r for r in fixed_report['cases']}
    need(len(cases) == len(report['cases']) and len(fixed_cases) == len(fixed_report['cases']), 'Repeated report question')
    scopes = sorted(path.stem for path in (pilot / 'participants').glob('*.json'))
    need(len(scopes) == 14, 'Expected 14 pilot source scopes')
    need({p.name for p in (ranking / 'queries').glob('*.json')} == {f'{s}-{state}.json' for s in scopes for state in ('clean', 'native_retry')}, 'Ranking file coverage differs')
    need({p.name for p in (fixed / 'queries').glob('*.json')} == {f'{s}.json' for s in scopes}, 'Fixed-IDF file coverage differs')
    totals = Counter(); by_pool = {}; scope_stats = []; reversal_rows = []; wanted_cases = set()
    divisors, entities = Counter(), Counter()
    for scope in scopes:
        episode = tracked(pilot / 'participants' / f'{scope}.json')
        events = {r['event_id']: r for r in episode['events']}
        queries = tracked(pilot / 'queries' / f'{scope}.json')
        wanted = {q['invocation'] for q in queries}
        need(len(wanted) == len(queries), 'Duplicate input invocation')
        wanted_cases.update((scope, q) for q in wanted)
        parent = pilot / 'stores/mem0_raw' / scope
        physical = {state: points(parent / state) for state in ('clean', 'native_retry')}
        for state in physical:
            files.append(parent / state / 'qdrant/collection/study_memories/storage.sqlite')
        clean, replay = physical['clean'], physical['native_retry']
        need(len(clean) == len(events) and set(clean) < set(replay), 'Replay does not preserve clean IDs/add duplicates')
        need(all(clean[i]['point_sha256'] == replay[i]['point_sha256'] for i in clean), 'An original physical point changed')
        need(objsha({i: p['point_sha256'] for i, p in clean.items()}) == prior_by_scope[scope]['baseline_record_fingerprint'], 'Original point bytes differ from earlier independent audit')
        snapshot = tracked(parent / 'clean/initial_snapshot.json')
        need({r['physical_id'] for r in snapshot} == set(clean) and len(snapshot) == len(clean), 'IDF clean-ID selection differs from actual clean store')
        retry_sources = set(tracked(pilot / 'retry_sources' / f'{scope}.json'))
        expected_counts = Counter({key: 1 + 2 * (event['source_id'] in retry_sources) for key, event in events.items()})
        need(Counter(p['payload']['study_event_id'] for p in replay.values()) == expected_counts, 'Replay event multiplicities differ')
        clean_by_event = {p['payload']['study_event_id']: p for p in clean.values()}
        need(set(clean_by_event) == set(events), 'Physical clean event coverage differs')
        for point in replay.values():
            payload = point['payload']; event = events[payload['study_event_id']]
            need(payload['data'] == event['speaker'] + ': ' + event['text'] and payload['study_source_id'] == event['source_id'] and payload['study_date'] == event['occurred_at'] and payload['study_body_sha256'] == objsha(event), 'Physical literal event mismatch')
            need(point['vector'] == clean_by_event[event['event_id']]['vector'], 'Duplicate dense/sparse vector differs from original occurrence')
        n0, df0 = df_stats(clean); n1, df1 = df_stats(replay)
        need(n0 == len(clean) and n1 == len(replay), 'Sparse corpus does not cover every stored point')
        restored_n, restored_df = df_stats({i: replay[i] for i in clean})
        need((restored_n, restored_df) == (n0, df0), 'Known-clean IDF corpus statistics differ from clean')
        changed_terms = sum(abs(math.log((n0 + 1)/(df0[i] + .5)) - math.log((n1 + 1)/(df1[i] + .5))) > TOL for i in df0)
        scope_stats.append(dict(scope=scope, clean_physical_points=n0, replay_physical_points=n1,
                                distinct_sparse_terms=len(df0), terms_with_changed_physical_corpus_idf=changed_terms,
                                original_point_bytes_preserved=True, replay_vectors_preserved=True,
                                fixed_corpus_N_and_df_equal_clean=True))
        raw = {}
        for state in ('clean', 'native_retry'):
            entries = tracked(ranking / 'queries' / f'{scope}-{state}.json')
            raw[state] = {(r['invocation'], r['requested_top_k']): r['rows'] for r in entries}
            need(len(raw[state]) == len(entries) and set(raw[state]) == {(q, k) for q in wanted for k in (60, 10000)}, 'Ranking invocation/pool coverage differs')
            original_candidates = {r['invocation']: r['candidates'] for r in tracked(parent / state / 'candidates.json')}
            need(set(original_candidates) == wanted, 'Pilot candidate coverage differs')
            for (question, k), rows in raw[state].items():
                totals['ranking_rows'] += validate_rows(rows, physical[state], full=k == 10000)
                totals['ranking_queries'] += 1
                divisors.update(r['score_details']['max_possible_score'] for r in rows)
                entities.update(r['score_details']['entity_boost'] for r in rows)
                if k == 60:
                    candidates = original_candidates[question]
                    need(len(candidates) == len(rows), 'K60 pilot/probe size differs')
                    for row, candidate in zip(rows, candidates):
                        transformed = normalized(row)
                        need({k: v for k, v in transformed.items() if k != 'score'} == {k: v for k, v in candidate.items() if k != 'score'}, 'K60 pilot physical order/payload differs')
                        need(abs(transformed['score'] - candidate['score']) <= TOL, 'K60 pilot score differs')
                    totals['k60_exact_physical_order_reproductions'] += 1
        fixed_entries = tracked(fixed / 'queries' / f'{scope}.json')
        fixed_raw = {r['invocation']: r['rows'] for r in fixed_entries}
        need(len(fixed_raw) == len(fixed_entries) and set(fixed_raw) == wanted, 'Fixed-IDF invocation coverage differs')
        for question in wanted:
            for k in (60, 10000):
                details = comparison(raw['clean'][question, k], raw['native_retry'][question, k])
                need(details == cases[scope, question]['diagnostic'][str(k)], 'Ranking report arithmetic/context differs')
                stats = by_pool.setdefault(str(k), dict(different_selected_event_sets=0, different_selected_event_orders=0, questions_with_component_changes={f: 0 for f in COMPONENTS}, common_original_points_compared=0))
                stats['different_selected_event_sets'] += not details['same_selected_event_set']
                stats['different_selected_event_orders'] += not details['same_selected_event_order']
                stats['common_original_points_compared'] += details['common_original_point_scores']
                for f in COMPONENTS:
                    stats['questions_with_component_changes'][f] += details['component_changes_at_1e12'][f] > 0
                if k == 60:
                    need(details['clean_context'] == context_by_key['mem0_raw', question, 'clean'], 'K60 clean pilot context differs')
                    need(details['retry_context'] == context_by_key['mem0_raw', question, 'read_event_dedup'], 'K60 dedup pilot context differs')
            rows = fixed_raw[question]
            totals['fixed_idf_rows'] += validate_rows(rows, replay, full=True)
            totals['fixed_idf_queries'] += 1
            details = comparison(raw['clean'][question, 10000], rows)
            expected = dict(question_key=question, scope=scope, original_points_compared=details['common_original_point_scores'],
                            component_changes_at_1e12=details['component_changes_at_1e12'],
                            same_selected_event_order=details['same_selected_event_order'], same_selected_event_set=details['same_selected_event_set'],
                            clean_context=details['clean_context'], fixed_idf_context=details['retry_context'])
            need(expected == fixed_cases[scope, question], 'Fixed-IDF report arithmetic/context differs')
            need(details['same_selected_event_order'] and details['same_selected_event_set'] and all(v == 0 for v in details['component_changes_at_1e12'].values()), 'Fixed-IDF restoration failed')
            totals['fixed_idf_original_points_compared'] += details['common_original_point_scores']
            need(set(r['id'] for r in rows) - set(clean) == set(replay) - set(clean), 'Fixed-IDF intervention removed duplicate candidates')
            witness, switch = strict_reversals(raw['clean'][question, 10000], raw['native_retry'][question, 10000])
            reversal_rows.append(dict(scope=scope, question_key=question, strict_original_point_reversal=witness,
                                      strict_lost_gained_event_reversal=switch))
    need(set(cases) == set(fixed_cases) == wanted_cases and len(wanted_cases) == 24, 'Whole-pilot question coverage differs')
    need(report['questions'] == fixed_report['questions'] == summary['questions'] == 24, 'Declared question count differs')
    need(report['native_search_calls'] == summary['native_search_calls'] == totals['ranking_queries'] == 96 and fixed_report['native_search_calls'] == totals['fixed_idf_queries'] == 24, 'Declared native-query count differs')
    need(by_pool == summary['by_pool'], 'Ranking summary differs from raw arithmetic')
    need(fixed_report['different_event_sets'] == fixed_report['different_event_orders'] == 0 and fixed_report['questions_with_component_changes'] == {f: 0 for f in COMPONENTS}, 'Fixed-IDF summary differs')
    llama_changes = sum(context_by_key['llama_index', q, 'clean'] != context_by_key['llama_index', q, 'read_event_dedup'] for _, q in wanted_cases)
    inputs = {}
    for path in set(files):
        label = str(path.relative_to(HERE)) if path.is_relative_to(HERE) else ('public_source/' + path.name)
        need(label not in inputs, 'Input manifest label collision')
        inputs[label] = sha(path)
    return dict(status='PASS', phase='Independent same-study read-only audit; no native search, embedding, or model call',
                auditor_sha256=sha(Path(__file__)), tolerance=TOL, audited_questions=24, audited_source_scopes=14,
                pilot_protocol_sha256=sha(pilot/'protocol.json'), ranking_protocol_sha256=sha(ranking/'protocol.json'),
                fixed_idf_protocol_sha256=sha(fixed/'protocol.json'), totals=dict(totals), by_pool=by_pool,
                fixed_idf=dict(questions=24, original_points_compared=totals['fixed_idf_original_points_compared'],
                               all_original_components_restored=True, all_selected_event_orders_restored=True,
                               all_replay_duplicate_points_still_present_in_outputs=True),
                additional_posthoc_arithmetic=dict(questions_with_strict_original_point_reversal=sum(r['strict_original_point_reversal'] is not None for r in reversal_rows),
                                                  changed_selected_sets_with_strict_lost_gained_reversal=sum(r['strict_lost_gained_event_reversal'] is not None for r in reversal_rows),
                                                  witnesses=reversal_rows),
                retained_llama_index_questions_with_changed_dedup_context=llama_changes,
                observed_score_divisors=dict(divisors), observed_entity_boosts=dict(entities), scopes=scope_stats,
                public_runtime_versions={name: importlib.metadata.version(name) for name in ('qdrant-client','mem0ai','fastembed')},
                input_sha256=inputs,
                audit_limits=['Raw sparse query vectors/unnormalized keyword scores were not retained, so this audit does not independently reconstruct each per-term query dot product.',
                              'No task answer quality is inferred from context changes or score restoration.',
                              'All diagnostic questions are the same 24 development questions, not new independent samples or held-out confirmation.',
                              'Known-clean physical IDs are an oracle mechanism intervention, not a proposed deployable policy.',
                              'Pinned Qdrant local behavior does not establish cloud/server/cluster behavior.',
                              'The producer field component_changes_at_1e12 uses the numeric tolerance 1e-12 despite its abbreviated name.'])


class AuditorNegativeTests(unittest.TestCase):
    def fixture(self):
        payload = dict(data='fixture', hash='h', created_at='t', updated_at='t', user_id='independent-benchmark-participant', role='user', study_event_id='e', study_source_id='s', study_date='d', study_body_sha256='b')
        row = dict(id='p', memory='fixture', hash='h', created_at='t', updated_at='t', user_id=payload['user_id'], role='user', metadata={k:v for k,v in payload.items() if k.startswith('study_')}, score=.6,
                   score_details=dict(semantic_score=.8,bm25_score=.4,entity_boost=0.,raw_score=1.2,max_possible_score=2.,final_score=.6,threshold=0))
        return row, {'p': {'payload':payload}}
    def test_accepts_correct_score(self):
        row, physical = self.fixture(); self.assertEqual(validate_rows([row],physical,True),1)
    def test_rejects_forged_score(self):
        row, physical = self.fixture(); row['score_details']['final_score']=.7
        with self.assertRaises(AuditError): validate_rows([row],physical)
    def test_rejects_forged_payload(self):
        row, physical = self.fixture(); row['metadata']['study_source_id']='forged'
        with self.assertRaises(AuditError): validate_rows([row],physical)
    def test_rejects_missing_full_pool_point(self):
        row, physical = self.fixture(); physical['missing']=copy.deepcopy(physical['p'])
        with self.assertRaises(AuditError): validate_rows([row],physical,True)
    def test_rejects_repeated_physical_identity(self):
        row, physical = self.fixture()
        with self.assertRaises(AuditError): validate_rows([row,row],physical)
    def test_logical_dedup_preserves_legitimate_same_text_occurrence(self):
        row, _ = self.fixture(); duplicate=copy.deepcopy(row);duplicate['id']='duplicate'
        occurrence=copy.deepcopy(row);occurrence['id']='new';occurrence['metadata']['study_event_id']='e2'
        self.assertEqual([r['event_id'] for r in selected([row,duplicate,occurrence])],['e','e2'])


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--self-test',action='store_true');parser.add_argument('--out',type=Path,default=HERE/'worker_review_ranking_audit.json');args=parser.parse_args()
    if args.self_test:
        suite=unittest.defaultTestLoader.loadTestsFromTestCase(AuditorNegativeTests)
        sys.exit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())
    result=audit(HERE/'development_pilot_v2',HERE/'posthoc_ranking_probe_v1',HERE/'posthoc_fixed_idf_v1')
    args.out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({key:value for key,value in result.items() if key in ('status','totals','by_pool','fixed_idf','retained_llama_index_questions_with_changed_dedup_context')},indent=2))
