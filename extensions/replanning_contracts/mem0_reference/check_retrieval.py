#!/usr/bin/env python3
"""Independent read-only evidence checker for the post hoc literal-exposure probe.

Imports neither the experiment, retrieval runner, nor their metric functions.
Native ranking, embedding inference, semantics and QA are not recomputed here.
"""
from __future__ import annotations

import argparse
import base64
import collections
import hashlib
import importlib.metadata
import io
import json
import math
import pickle
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SIZES = (8, 12, 24, 40)
BUDGETS = (5, 10, 20)
STATES = ('baseline', 'native_k10', 'widened_candidates', 'exact_admission')
CORE = ('hash', 'created_at', 'updated_at', 'user_id', 'attributed_to')


class VerificationError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise VerificationError(message)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


class RestrictedPointReader(pickle.Unpickler):
    def find_class(self, module, name):
        if module == 'qdrant_client.http.models.models' and name in ('PointStruct', 'SparseVector'):
            from qdrant_client.http.models import models
            return getattr(models, name)
        raise VerificationError(f'Unexpected stored pickle class: {module}.{name}')


def unpickle(data):
    return RestrictedPointReader(io.BytesIO(data)).load()


def read_sql(path, statement):
    path = Path(path).resolve()
    wal = Path(str(path) + '-wal')
    require(not wal.exists() or wal.stat().st_size == 0,
            'Uncheckpointed WAL is outside this immutable raw-reader contract')
    connection = sqlite3.connect(path.as_uri() + '?mode=ro&immutable=1', uri=True)
    connection.row_factory = sqlite3.Row
    try:
        require(connection.execute('PRAGMA integrity_check').fetchone()[0] == 'ok',
                f'SQLite integrity failure: {path.name}')
        return [dict(row) for row in connection.execute(statement)]
    finally:
        connection.close()


def read_store(folder):
    """Decode actual persisted points/history, not runner-produced metrics."""
    records = {}
    for row in read_sql(folder / 'qdrant/collection/study_memories/storage.sqlite',
                        'SELECT id,point FROM points ORDER BY rowid'):
        mid = unpickle(base64.b64decode(row['id'], validate=True))
        point = unpickle(row['point'])
        require(isinstance(mid, str) and mid == point.id, 'Stored point/key identity mismatch')
        require(mid not in records, 'Repeated physical point identity')
        payload = point.payload
        require(isinstance(payload.get('data'), str), 'Stored literal text is missing')
        require(payload.get('hash') == hashlib.md5(payload['data'].encode()).hexdigest(),
                'Stored exact-text hash mismatch')
        require(payload.get('user_id') == 'synthetic-study-user', 'Unexpected stored user scope')
        dense = point.vector.get('') if isinstance(point.vector, dict) else point.vector
        require(isinstance(dense, list) and len(dense) == 384, 'Expected 384-dimensional stored vectors')
        require(all(type(v) in (float, int) and math.isfinite(v) for v in dense),
                'Nonfinite stored vector')
        records[mid] = dict(memory=payload['data'], payload=payload, dense=dense,
            point_blob_sha256=hashlib.sha256(row['point']).hexdigest())
    history = read_sql(folder / 'history.sqlite', 'SELECT * FROM history ORDER BY rowid')
    require(len(history) == len(records), 'Physical point/history cardinality mismatch')
    require(len({row['memory_id'] for row in history}) == len(history)
            and {row['memory_id'] for row in history} == set(records),
            'Physical point/history identities mismatch')
    for row in history:
        point = records[row['memory_id']]
        require(row['event'] == 'ADD' and row['is_deleted'] == 0
                and row['old_memory'] is None, 'History is not the declared add-only state')
        require(row['new_memory'] == point['memory']
                and row['created_at'] == point['payload']['created_at'],
                'Point/history literal content mismatch')
    return records, history


def source_folder(here, n, state):
    if state == 'baseline':
        return here / 'live_results/baselines' / f'n{n}'
    return here / 'live_results/retries' / f'n{n}__fresh_recent_context__{state}__fresh_model'


def validate_projection(rows, points, label):
    require(len(rows) == len(points) and len({r['id'] for r in rows}) == len(rows),
            f'{label} complete snapshot cardinality mismatch')
    require({r['id'] for r in rows} == set(points), f'{label} snapshot identity mismatch')
    for row in rows:
        require(row['memory'] == points[row['id']]['memory'], f'{label} snapshot literal mismatch')
        for key in CORE:
            require(row.get(key) == points[row['id']]['payload'].get(key),
                    f'{label} snapshot {key} mismatch')


def grouped_statistics(rows, sizes, budgets, states):
    output = []
    for n in sizes:
        for state in states:
            for k in budgets:
                subset = [r for r in rows if (r['n_source_preferences'], r['state'], r['budget']) == (n, state, k)]
                require(subset, 'Empty expected summary group')
                count = len(subset)
                distinct = [len({v['memory'] for v in r['results']}) for r in subset]
                total = sum(len(r['results']) for r in subset)
                output.append(dict(n_source_preferences=n, state=state, budget=k,
                    query_count=count, total_returned_records=total,
                    total_distinct_literal_facts=sum(distinct),
                    duplicate_context_slots=total-sum(distinct),
                    minimum_distinct_facts=min(distinct), mean_distinct_facts=sum(distinct)/count,
                    exact_target_present_count=sum(any(v['memory'] == r['query'] for v in r['results']) for r in subset)))
    return output


def check_summary(summary, groups, count):
    require(summary['native_search_calls'] == count, 'Summary search-call count mismatch')
    require(summary['additional_model_requests'] == 0, 'Summary declares additional model requests')
    observed = summary['groups']
    require(len(observed) == len(groups), 'Summary group coverage mismatch')
    key = lambda r: (r['n_source_preferences'], r['state'], r['budget'])
    require(len({key(r) for r in observed}) == len(observed), 'Repeated summary group')
    actual = {key(r): r for r in observed}
    require(set(actual) == {key(r) for r in groups}, 'Summary group identities mismatch')
    for group in groups:
        for field, expected in group.items():
            value = actual[key(group)].get(field)
            if type(expected) is float:
                require(type(value) in (int, float) and math.isclose(value, expected, abs_tol=1e-12),
                        f'Summary {field} mismatch')
            else:
                require(type(value) is type(expected) and value == expected,
                        f'Summary {field} mismatch')


def audit(here, out, expected_design=(SIZES, BUDGETS, STATES)):
    """Check one frozen execution. Tests supply a smaller, explicitly authored design."""
    here, out = Path(here).resolve(), Path(out).resolve()
    protocol = load(out / 'protocol.json')
    require(digest(out / 'protocol.json') == (out / 'protocol.sha256').read_text().strip(),
            'Frozen protocol hash mismatch')
    require(digest(here / 'retrieval.py') == protocol['source_sha256'], 'Frozen retrieval source changed')
    sizes, budgets, states = tuple(protocol['sizes']), tuple(protocol['budgets']), tuple(protocol['states'])
    require((sizes, budgets, states) == tuple(tuple(x) for x in expected_design),
            'Declared dimensions differ from the reviewed design')
    require(protocol['model_requests'] == 0, 'Protocol declares additional model requests')
    expected_files = set()
    for n in sizes:
        for state in states:
            expected_files.update(str(p.relative_to(here)) for p in source_folder(here, n, state).rglob('*') if p.is_file())
    require(expected_files == set(protocol['protected_inputs']), 'Frozen input coverage mismatch')
    for rel, expected in protocol['protected_inputs'].items():
        require((here / rel).resolve().is_relative_to(here), 'Frozen path escapes the source root')
        require(digest(here / rel) == expected, f'Frozen input changed: {rel}')

    state_rows = load(out / 'states.json')
    expected_states = {(n, state) for n in sizes for state in states}
    require(len(state_rows) == len(expected_states)
            and {(r['n_source_preferences'], r['state']) for r in state_rows} == expected_states,
            'State snapshot coverage mismatch')
    state_map = {(r['n_source_preferences'], r['state']): r for r in state_rows}
    stores, histories, queries, comparisons = {}, {}, {}, []
    for n in sizes:
        for state in states:
            folder = source_folder(here, n, state)
            points, history = read_store(folder)
            stores[n, state], histories[n, state] = points, history
            validate_projection(load(folder / 'execution.json')['after'], points, 'Live execution')
            row = state_map[n, state]
            validate_projection(row['native_records'], points, 'Retrieval')
            require(row['query_source'] == 'all distinct baseline fact strings', 'Query-source declaration mismatch')
            require(row['record_state_unchanged_by_search'] is True, 'Runner reports a mutated search copy')
        baseline = stores[n, 'baseline']
        queries[n] = {v['memory'] for v in baseline.values()}
        require(len(queries[n]) == len(baseline) == n, 'Baseline has unexpected or repeated literal queries')
        for state in states:
            points = stores[n, state]
            new_ids = set(points) - set(baseline)
            unchanged = set(baseline) <= set(points) and all(points[mid]['point_blob_sha256'] == value['point_blob_sha256'] for mid, value in baseline.items())
            literal_copies = all(points[mid]['memory'] in queries[n] for mid in new_ids)
            vectors_match = all(any(value['memory'] == points[mid]['memory'] and
                all(abs(a-b) <= 1e-6 for a,b in zip(value['dense'], points[mid]['dense']))
                for value in baseline.values()) for mid in new_ids)
            comparisons.append(dict(n_source_preferences=n, state=state,
                raw_physical_records=len(points), baseline_raw_records=len(baseline),
                extra_point_ids=len(new_ids), baseline_point_blobs_preserved=unchanged,
                literal_set_matches_baseline={v['memory'] for v in points.values()} == queries[n],
                all_new_points_are_literal_baseline_copies=literal_copies,
                new_literal_vectors_match_baseline_tolerance_1e_6=vectors_match,
                all_point_blobs_equal_baseline=unchanged and not new_ids))

    rows = load(out / 'cases.json')
    expected_calls = {(n, state, query, k) for n in sizes for state in states for query in queries[n] for k in budgets}
    actual_calls = [(r['n_source_preferences'], r['state'], r['query'], r['budget']) for r in rows]
    require(len(actual_calls) == len(expected_calls) and set(actual_calls) == expected_calls,
            'Search coverage mismatch: missing, selected, repeated or unexpected query cell')
    for row in rows:
        n, state, query, k = row['n_source_preferences'], row['state'], row['query'], row['budget']
        require(row['query_sha256'] == hashlib.sha256(query.encode()).hexdigest(), 'Literal query hash mismatch')
        results, points = row['results'], stores[n, state]
        require(len(results) <= k and len({r['id'] for r in results}) == len(results),
                'Search budget or physical-identity uniqueness violated')
        for result in results:
            require(result['id'] in points, 'Returned identity absent from declared raw state')
            source = points[result['id']]
            require(result['memory'] == source['memory'], 'Returned literal differs from declared raw state')
            for key in CORE:
                require(result.get(key) == source['payload'].get(key), f'Returned {key} differs from raw state')
            require(type(result.get('score')) in (float, int) and math.isfinite(result['score'])
                    and result['score'] >= 0, 'Returned score violates declared threshold or finiteness')
        texts = [r['memory'] for r in results]
        metrics = dict(returned_records=len(texts), distinct_literal_facts=len(set(texts)),
            duplicate_context_slots=len(texts)-len(set(texts)), exact_target_present=query in texts)
        for field, value in metrics.items():
            require(type(row.get(field)) is type(value) and row[field] == value, f'Row {field} metric mismatch')
    groups = grouped_statistics(rows, sizes, budgets, states)
    check_summary(load(out / 'summary.json'), groups, len(rows))
    by_cell={(r['n_source_preferences'],r['state'],r['query'],r['budget']):r for r in rows}
    paired=[]
    for n in sizes:
        for state in states:
            if state == 'baseline':
                continue
            for k in budgets:
                differences=[];returned_differences=[];target_losses=0;target_gains=0
                for query in queries[n]:
                    baseline=by_cell[n,'baseline',query,k]['results']
                    current=by_cell[n,state,query,k]['results']
                    differences.append(len({r['memory'] for r in current})-len({r['memory'] for r in baseline}))
                    returned_differences.append(len(current)-len(baseline))
                    before_target=any(r['memory']==query for r in baseline)
                    after_target=any(r['memory']==query for r in current)
                    target_losses+=before_target and not after_target
                    target_gains+=after_target and not before_target
                paired.append(dict(n_source_preferences=n,state=state,budget=k,query_count=len(differences),
                    cells_with_fewer_distinct_literals=sum(d<0 for d in differences),
                    cells_with_same_distinct_literals=sum(d==0 for d in differences),
                    cells_with_more_distinct_literals=sum(d>0 for d in differences),
                    sum_distinct_literal_difference=sum(differences),
                    sum_returned_record_difference=sum(returned_differences),
                    exact_target_losses=target_losses,exact_target_gains=target_gains))
    for rel, expected in protocol['protected_inputs'].items():
        require(digest(here / rel) == expected, f'Frozen input changed during audit: {rel}')
    return dict(status='PASS', native_search_calls=len(rows), unique_baseline_queries=sum(map(len, queries.values())),
        baseline_queries_by_n={str(n):len(queries[n]) for n in sizes}, protected_input_files=len(expected_files),
        all_declared_query_cells_present_exactly_once=True, all_returned_identities_and_literals_from_declared_raw_state=True,
        exact_target_present_count=sum(r['exact_target_present'] for r in rows),
        query_cells_with_duplicate_context_slots=sum(r['duplicate_context_slots'] > 0 for r in rows),
        groups=groups, paired_literal_exposure=paired, raw_state_comparisons=comparisons,
        source_sha256=protocol['source_sha256'], protocol_sha256=digest(out/'protocol.json'),
        cases_sha256=digest(out/'cases.json'), states_sha256=digest(out/'states.json'),
        summary_sha256=digest(out/'summary.json'), protected_inputs_unchanged=True,
        scope='Post hoc finite literal-exposure probe; no independent workload generalization, semantic-diversity, QA, harm or token-cost inference.',
        limits=['Native rankings, BGE inference and BM25 scores are not independently recomputed.',
                'The original temporary copies were deleted. The original run unchanged-state flag is a runner assertion; retained computational reproduction can close that raw-after-state evidence gap.',
                'No-model execution is guarded by the frozen runner and declared protocol, not inferred from answer-quality metrics.'])


def verify_reproduction(here, original, reproduction, report):
    """Inspect after-close copies retained by an independently frozen wrapper."""
    spec = load(reproduction / 'retention_protocol.json')
    require(digest(reproduction/'retention_protocol.json') == (reproduction/'retention_protocol.sha256').read_text().strip(),
            'Frozen retention protocol hash mismatch')
    require(digest(here / 'retain_retrieval.py') == spec['wrapper_source_sha256'], 'Frozen retention wrapper changed')
    require(digest(here/'retrieval.py') == spec['retrieval_source_sha256'], 'Retained-run reader source changed')
    require(spec['expected_captures'] == len(SIZES)*len(STATES)
            and spec['capture_prefix'] == 'memory-retrieval-copy-'
            and spec['additional_model_requests'] == 0, 'Retention protocol scope mismatch')
    require(digest(original/'protocol.json') == spec['original_protocol_sha256'] == digest(reproduction/'protocol.json'),
            'Reproduction uses a different frozen protocol')
    require(digest(original/'cases.json') == spec['original_cases_sha256']
            and digest(original/'summary.json') == spec['original_summary_sha256'], 'Original measured outputs changed')
    captures = load(reproduction/'retained_manifest.json')['captures']
    expected = [(n,s) for n in SIZES for s in STATES]
    require([(c['n_source_preferences'], c['state']) for c in captures] == expected, 'Retention capture coverage/order mismatch')
    after_checks = []
    for cap in captures:
        folder = reproduction / cap['path']
        require(folder.resolve().is_relative_to(reproduction), 'Retained path escapes reproduction root')
        require(cap['runner_body_exception'] is None, 'Retained run body raised an exception')
        files = {str(p.relative_to(folder)):digest(p) for p in folder.rglob('*') if p.is_file()}
        require(files == cap['files'], 'Retained after-close files changed')
        n,state = cap['n_source_preferences'],cap['state']
        before,before_history = read_store(source_folder(here,n,state))
        after,after_history = read_store(folder)
        require(set(before) == set(after) and all(before[mid]['point_blob_sha256'] == after[mid]['point_blob_sha256'] for mid in before),
                'Retained after-search point state differs from frozen input')
        require(before_history == after_history, 'Retained after-search history differs from frozen input')
        after_checks.append(dict(n_source_preferences=n,state=state,point_blobs_unchanged=True,history_unchanged=True))
    repeated = audit(here,reproduction)
    require(repeated['groups'] == report['groups'], 'Computational reproduction metric summaries differ')
    old_rows = load(original/'cases.json');new_rows = load(reproduction/'cases.json')
    key = lambda r:(r['n_source_preferences'],r['state'],r['query'],r['budget'])
    new_map={key(r):r for r in new_rows}
    same_ordered_ids = sum([v['id'] for v in r['results']] == [v['id'] for v in new_map[key(r)]['results']] for r in old_rows)
    same_metrics = sum(all(r[k] == new_map[key(r)][k] for k in ('returned_records','distinct_literal_facts','duplicate_context_slots','exact_target_present')) for r in old_rows)
    require(same_metrics == len(old_rows), 'Computational reproduction per-query metrics differ')
    return dict(status='PASS', retained_states_checked=len(after_checks), states=after_checks,
        native_search_calls_reproduced=repeated['native_search_calls'], identical_per_query_metric_cells=same_metrics,
        identical_ordered_returned_identity_cells=same_ordered_ids,
        retention_protocol_sha256=digest(reproduction/'retention_protocol.json'),
        retention_manifest_sha256=digest(reproduction/'retained_manifest.json'),
        reproduction_cases_sha256=digest(reproduction/'cases.json'),
        interpretation='Same frozen computation and stores, retained after-close; computational reproduction, not independent experimental samples.')


def verify_runtime(here):
    """Use earlier frozen source evidence without importing native experiment code."""
    frozen=load(here/'results/frozen_spec.json')
    previous_check=load(here/'verification.json')
    require(digest(here/'results/frozen_spec.json') == (here/'results/spec.sha256').read_text().strip(),
            'Inherited controlled protocol hash mismatch')
    require(digest(here/'experiment.py') == frozen['runner_sha256'],
            'Reader construction helper differs from earlier frozen source')
    mem0=Path(importlib.metadata.distribution('mem0ai').locate_file('mem0/memory/main.py'))
    persistence=Path(importlib.metadata.distribution('qdrant-client').locate_file('qdrant_client/local/persistence.py'))
    require(digest(mem0) == frozen['installed_main_sha256'], 'Installed native Mem0 source changed')
    require(digest(persistence) == previous_check['qdrant_persistence_sha256'], 'Installed Qdrant persistence source changed')
    versions={name:importlib.metadata.version(name) for name in frozen['environment']['packages']}
    require(versions == frozen['environment']['packages'], 'Frozen runtime package versions differ')
    require(sys.version == frozen['environment']['python'] and sqlite3.sqlite_version == frozen['environment']['sqlite'],
            'Frozen Python/SQLite runtime differs')
    return dict(status='PASS',reader_helper_sha256=digest(here/'experiment.py'),
        installed_mem0_source_sha256=digest(mem0),qdrant_persistence_source_sha256=digest(persistence),
        python=sys.version,sqlite=sqlite3.sqlite_version,packages=versions,
        provenance='Current source/runtime matches earlier frozen controlled-study evidence. The retrieval protocol itself did not separately freeze transitive dependencies or record loaded model-file digests.')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',type=Path,default=HERE/'retrieval_results')
    parser.add_argument('--reproduction',type=Path)
    parser.add_argument('--report',type=Path)
    args=parser.parse_args();out=args.out.resolve()
    report=audit(HERE,out)
    report['checker_sha256']=digest(__file__)
    report['runtime_integrity']=verify_runtime(HERE)
    if args.reproduction:
        report['computational_reproduction']=verify_reproduction(HERE,out,args.reproduction.resolve(),report)
    target=args.report or out/'verification.json'
    target.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('status','native_search_calls','unique_baseline_queries','exact_target_present_count','query_cells_with_duplicate_context_slots')},indent=2))


if __name__=='__main__':
    main()
