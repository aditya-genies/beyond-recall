#!/usr/bin/env python3
"""Independent native checkpoint and result checker for the extension.

Does not import the native worker, its graph factory, or participant metrics.
"""
import argparse
import contextlib
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
from typing import TypedDict

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from checks.check_results import METRICS, digest, recompute_case, require


class ReadState(TypedDict, total=False):
    intent: str
    epoch: int
    plan: list[dict]
    outcome: str


def read_native(folder):
    from langgraph.checkpoint.sqlite import SqliteSaver
    from langgraph.graph import END, START, StateGraph
    def never_execute(state):
        raise AssertionError('verifier must not execute participant nodes')
    builder = StateGraph(ReadState)
    builder.add_node('choose_decision', never_execute)
    builder.add_node('apply_effects', never_execute)
    builder.add_edge(START, 'choose_decision')
    builder.add_edge('choose_decision', 'apply_effects')
    builder.add_edge('apply_effects', END)
    with contextlib.closing(sqlite3.connect(folder / 'native_checkpoints.sqlite', check_same_thread=False)) as connection:
        saver = SqliteSaver(connection)
        graph = builder.compile(checkpointer=saver)
        snapshot = graph.get_state({'configurable': {'thread_id': 'intent-alpha'}})
        return dict(values=dict(snapshot.values), next=list(snapshot.next),
                    checkpoint_rows=connection.execute('SELECT COUNT(*) FROM checkpoints').fetchone()[0],
                    task_write_rows=connection.execute('SELECT COUNT(*) FROM writes').fetchone()[0])


def verify_case(case, folder):
    # Apply the existing independent fixture oracle with the explicit matched address rule.
    normalized = dict(case, policy='D1P1R1')
    recompute_case(normalized, folder)
    chosen = [event for attempt in case['attempts'] for event in attempt['events']
              if event['event'] == 'decision_chosen']
    require(len(chosen) == 1, 'native reference replanned after a retained decision')
    require(case['planning_invocations'] == 1, 'planning count differs from one per logical intent')
    require(case['decision_continuity'], 'observed native decision continuity failed')
    with contextlib.closing(sqlite3.connect(folder / 'recovery.sqlite')) as connection:
        require(connection.execute('SELECT COUNT(*) FROM decisions').fetchone()[0] == 0,
                'reference used the application decision table instead of native checkpoints')
        require(connection.execute('SELECT COUNT(*) FROM receipts').fetchone()[0] == 0,
                'reference used the application receipt table instead of native completion')
    native = read_native(folder)
    require(native['checkpoint_rows'] >= 3, 'native checkpoint history is absent')
    require(digest(native['values']['plan']) == chosen[0]['digest'], 'native stored plan differs from chosen literal arguments')
    if case['history'] == 'reset_before_retry':
        require(native['next'] == ['apply_effects'], 'entry generation cancellation changed unfinished checkpoint unexpectedly')
        require(case['attempts'][-1]['events'][-1]['outcome'] == 'cancelled', 'stale generation was not cancelled')
    else:
        require(native['next'] == [], 'native execution did not have a completed terminal checkpoint')
        require(native['values']['outcome'] == ('cancelled' if case['history'] == 'reset_during_effects' else 'applied'),
                'native checkpoint outcome differs from declared history')
    for attempt in case['attempts']:
        require(not attempt['stderr'], 'worker emitted unexpected stderr')
        require(any(event['event'] == 'worker_started' and event['pid'] == attempt['pid'] for event in attempt['events']),
                'attempt lacks its actual child-process witness')
        if attempt['returncode'] == 87:
            require(attempt['native_snapshot']['values'].get('plan') is not None,
                    'abrupt process exit lacks a recoverable native stored plan')
        if attempt['returncode'] in (74, 87) and attempt['fault'] != 'after_finalize':
            require(attempt['native_snapshot']['next'] == ['apply_effects'],
                    'unfinished native effect node does not match the declared replay barrier')
        if attempt['fault'] == 'after_prepare':
            require(attempt['native_snapshot']['next'] == ['apply_effects'], 'preparation exit was not after native planner checkpoint')
        if attempt['fault'] == 'after_finalize':
            require(attempt['native_snapshot']['next'] == [], 'finalization exit occurred before native completion')
    require(any(event['event'] == 'native_checkpoint_committed' for attempt in case['attempts'] for event in attempt['events']),
            'actual native checkpoint-write instrumentation is absent')
    return native


def verify_campaign(root):
    cases = [json.loads(line) for line in (root / 'cases.jsonl').read_text().splitlines()]
    primary = [json.loads(line) for line in (ROOT / 'results/cases.jsonl').read_text().splitlines()]
    primary = {(row['profile'], row['history']): row for row in primary if row['policy'] == 'D1P1R1'}
    keys = [(row['profile'], row['history']) for row in cases]
    require(len(keys) == len(set(keys)) == 66 and set(keys) == set(primary), 'matched 66-cell coverage differs')
    differences = []
    checkpoints = 0
    for case in cases:
        folder = root / 'state' / f"langgraph_native__{case['profile']}__{case['history']}"
        native = verify_case(case, folder)
        checkpoints += native['checkpoint_rows']
        before = primary[(case['profile'], case['history'])]
        signature = lambda row: [(attempt['attempt'], attempt['fault'], attempt['alternative'],
                                  attempt['returncode'], attempt['acknowledged']) for attempt in row['attempts']]
        if signature(case) != signature(before):
            differences.append(dict(profile=case['profile'], history=case['history'],
                                    metric='attempt_schedule_and_outcomes', native=signature(case), original=signature(before)))
        for metric in METRICS:
            if case[metric] != before[metric]:
                differences.append(dict(profile=case['profile'], history=case['history'], metric=metric,
                                        native=case[metric], original=before[metric]))
    spec = json.loads((root / 'frozen_spec.json').read_text())
    require(spec['original_study_sha256'] == hashlib.sha256((ROOT / 'study.py').read_bytes()).hexdigest(),
            'original participant source differs from extension manifest')
    require(spec['source_sha256'] == hashlib.sha256((Path(__file__).parent / 'runner.py').read_bytes()).hexdigest(),
            'native source differs from its frozen manifest')
    expected_summary = dict(reference='langgraph_native', structural_cases=len(cases),
        **{name:sum(row[field] for row in cases) for name,field in
           [('content_pass','content_correct'),('cardinality_pass','cardinality_correct'),
            ('selected_terminal_pass','selected_terminal'),('decision_continuity_pass','decision_continuity'),
            ('acknowledged','acknowledged'),('planning_invocations','planning_invocations'),
            ('committed_effect_calls','committed_effect_calls')]},
        process_attempts=sum(len(row['attempts']) for row in cases),
        abrupt_exits=sum(attempt['returncode']==87 for row in cases for attempt in row['attempts']))
    require(json.loads((root/'summary.json').read_text()) == expected_summary,
            'native summary differs from independently checked raw rows')
    report = dict(status='PASS',reference='Native LangGraph execution-framework integration, not a live memory-agent baseline',
                  matched_structural_cases=66, original_main_denominator_unchanged=528,
                  checkpoint_rows_observed=checkpoints,
                  application_decision_receipt_rows_used=False,
                  comparison_differences=differences,
                  all_seven_metric_values_match=len(differences) == 0,
                  native_versions=spec['versions'],
                  scope='Declared sequential semantic barriers, scripted planner and SQLite effect store; no latency, throughput, production or arbitrary-crash claim')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    arguments = parser.parse_args()
    report = verify_campaign(arguments.results)
    arguments.out.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
