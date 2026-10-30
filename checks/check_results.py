#!/usr/bin/env python3
"""Recompute recorded metrics from read-only SQLite files and event traces.

This checker does not import the participant implementation or its metric code.
It checks finite evidence consistency, not arbitrary process/storage failures.
"""
import argparse
import hashlib
import itertools
import json
import sqlite3
from collections import defaultdict
from pathlib import Path

POLICIES = [f'D{d}P{p}R{r}' for d,p,r in itertools.product((0,1), repeat=3)]
PROFILES = ['insert','revise','retire','mixed']
HISTORIES = [
 'normal','redelivery_fixed','redelivery_drift',
 'exit_after_prepare_fixed','exit_after_prepare_drift',
 'exit_after_first_put_fixed','exit_after_first_put_drift',
 'lost_put_reply_fixed','lost_put_reply_drift',
 'exit_after_effects_fixed','exit_after_effects_drift',
 'exit_after_finalize_drift','bounded_input','superseded_input',
 'reset_before_retry','reset_during_effects','lost_delete_reply',
]
FIXTURE_FACTS = ['tone=concise','unit=metric','topic=cycling']
METRICS = [
 'content_correct','cardinality_correct','acknowledged','selected_terminal',
 'decision_continuity','planning_invocations','committed_effect_calls',
]


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def digest(value):
    encoded = json.dumps(value,sort_keys=True,separators=(',',':')).encode()
    return hashlib.sha256(encoded).hexdigest()


def read_table(path, table, order):
    connection = sqlite3.connect(path.resolve().as_uri()+'?mode=ro', uri=True)
    connection.row_factory = sqlite3.Row
    try:
        return [dict(row) for row in connection.execute(f'SELECT * FROM {table} ORDER BY {order}')]
    finally:
        connection.close()


def terminal_oracles(records, expected, acknowledged):
    """Exact content, physical cardinality and last delivery outcome are distinct."""
    actual = {row['fact'] for row in records}
    wanted = set(expected)
    content = actual == wanted
    cardinality = len(records) == len(wanted)
    return dict(content_correct=content, cardinality_correct=cardinality,
                acknowledged=bool(acknowledged),
                selected_terminal=content and cardinality and bool(acknowledged))


def recompute_case(case, folder):
    physical = read_table(folder/'effects.sqlite','records','address')
    actions = read_table(folder/'effects.sqlite','committed_actions','serial')
    source_rows = read_table(folder/'recovery.sqlite','conversation','turn')
    epochs = read_table(folder/'recovery.sqlite','epoch_state','epoch')
    history=case.get('history','')
    if history in HISTORIES:
        require(epochs==[{'epoch':1 if history.startswith('reset_') else 0}],
                'final generation differs from declared schedule')
    require(all(action['origin']=='intent-alpha' and action['epoch']==0 for action in actions),
            'committed action has incorrect origin/generation')
    selected = [fact for row in source_rows
                if row['enabled']==1 and row['epoch']==0 and row['turn']<=1
                for fact in json.loads(row['facts'])]
    expected = [] if case.get('history','').startswith('reset_') else FIXTURE_FACTS
    require(sorted(case['expected_facts'])==sorted(expected),'expected facts differ from declared fixture contract')
    require(case['physical_records']==physical,'serialized physical records differ from database')
    require(case['committed_actions']==actions,'serialized action ledger differs from database')
    require(all(action['kind'] in ('put','delete') for action in actions),
            'action-call metric includes an undeclared action kind')
    plan_digests = defaultdict(list)
    planning_calls = 0
    source_observations = 0
    chosen_plans={event['digest']:event['operations']
                  for attempt in case['attempts'] for event in attempt['events']
                  if event['event']=='decision_chosen'}
    by_attempt=defaultdict(list)
    for action in actions:
        by_attempt[action['attempt']].append(action)
    for attempt in case['attempts']:
        events = attempt['events']
        observed=[event for event in events if event['event']=='effect_committed']
        committed=by_attempt[attempt['attempt']]
        require(len(observed)==len(committed),'effect witness/ledger operation count differs')
        decision_event=next((event for event in events if event['event'] in ('decision_chosen','decision_loaded')),None)
        if committed:
            require(decision_event is not None,'committed effects lack an observed decision')
            plan=chosen_plans[decision_event['digest']]
            for witness,action in zip(observed,committed):
                require(witness['kind']==action['kind'] and witness['address']==action['address'],
                        'effect witness differs from committed ledger')
                slot=witness['slot']
                require(0<=slot<len(plan),'effect slot is outside its observed decision')
                operation=plan[slot]
                require(operation['kind']==action['kind'],'effect order/kind differs from its decision')
                if action['kind']=='put':
                    require(witness['fact']==action['fact']==operation['fact'],'committed fact differs from chosen operation')
                if operation.get('target'):
                    require(action['address']==operation['target'],'effect did not preserve its literal target binding')
                elif case.get('policy','').startswith('D1'):
                    expected_address=hashlib.sha256(f"intent-alpha|slot={slot}".encode()).hexdigest()[:24]
                    require(action['address']==expected_address,'deterministic effect address differs')
        ack = attempt['returncode']==0 and any(event['event']=='ack' for event in events)
        require(attempt['acknowledged']==ack,'attempt acknowledgement differs from process/event evidence')
        if attempt['returncode']==87:
            require(any(event['event']=='abrupt_exit' for event in events),'abrupt exit lacks barrier witness')
            require(not ack,'abrupt exit was acknowledged')
        for event in events:
            name = event['event']
            if name=='source_selected':
                source_observations += 1
                require(event['facts']==selected,'source selection differs from independent bounded/enabled query')
            if name=='decision_chosen':
                require(digest(event['operations'])==event['digest'],'chosen decision digest is incorrect')
                planning_calls += 1
            if name in ('decision_chosen','decision_loaded'):
                plan_digests[event['intent']].append(event['digest'])
    final = case['attempts'][-1]
    ack = final['returncode']==0 and any(event['event']=='ack' for event in final['events'])
    derived = terminal_oracles(physical,expected,ack)
    derived.update(decision_continuity=all(len(set(values))<=1 for values in plan_digests.values()),
                   planning_invocations=planning_calls,committed_effect_calls=len(actions))
    for metric in METRICS:
        require(case[metric]==derived[metric],f'metric {metric} differs from independent recomputation')
    return dict(derived,source_observations_checked=source_observations,
                source_selection_correct=True,
                put_commits=sum(action['kind']=='put' for action in actions),
                delete_commits=sum(action['kind']=='delete' for action in actions))


def expected_case_keys():
    return {(policy,profile,history) for policy in POLICIES for profile in PROFILES
            for history in HISTORIES
            if history!='lost_delete_reply' or profile in ('retire','mixed')}


def check_campaign(root):
    data = (root/'cases.jsonl').read_bytes()
    cases = [json.loads(line) for line in data.splitlines() if line.strip()]
    keys = [(case['policy'],case['profile'],case['history']) for case in cases]
    require(len(keys)==len(set(keys)),'duplicate structural case key')
    require(set(keys)==expected_case_keys(),'missing or unexpected structural cases')
    totals=[]
    observations=0
    for case in cases:
        key=f"{case['policy']}__{case['profile']}__{case['history']}"
        try:
            checked = recompute_case(case,root/'state'/key)
        except AssertionError as exc:
            raise AssertionError(f'{key}: {exc}') from None
        observations += checked['source_observations_checked']
    for policy in POLICIES:
        group=[case for case in cases if case['policy']==policy]
        totals.append(dict(policy=policy,structural_cases=len(group),
          content_pass=sum(case['content_correct'] for case in group),
          cardinality_pass=sum(case['cardinality_correct'] for case in group),
          selected_terminal_pass=sum(case['selected_terminal'] for case in group),
          decision_continuity_pass=sum(case['decision_continuity'] for case in group),
          acknowledged=sum(case['acknowledged'] for case in group),
          planning_invocations=sum(case['planning_invocations'] for case in group),
          committed_effect_calls=sum(case['committed_effect_calls'] for case in group),
          process_attempts=sum(len(case['attempts']) for case in group),
          abrupt_exits=sum(attempt['returncode']==87 for case in group for attempt in case['attempts'])))
    require(json.loads((root/'summary.json').read_text())==totals,'summary differs from independently checked raw totals')
    spec=json.loads((root/'frozen_spec.json').read_text())
    require(spec['structural_cases']==len(cases)==528,'manifest denominator is incorrect')
    require(spec['policies']==POLICIES,'manifest policies differ from checked factorial')
    require(spec['profiles']==PROFILES,'manifest profiles differ from checked operations')
    require(spec['histories']==HISTORIES,'manifest histories differ from checked finite coverage')
    source_file=Path(__file__).resolve().parents[1]/'study.py'
    require(hashlib.sha256(source_file.read_bytes()).hexdigest()==spec['source_sha256'],
            'current participant source differs from frozen source hash')
    require('excludes reset and cleanup' in spec['effect_call_definition'],'effect-call exclusion is not disclosed')
    boundary_rows=json.loads((root/'boundary_probes.json').read_text())
    expected_probes={'receipt_only','decision_only','both','before_decision_store','external_interleaving'}
    require({row['probe'] for row in boundary_rows}==expected_probes,'boundary probe set differs')
    require(len(boundary_rows)==len(expected_probes),'duplicate boundary probe')
    boundary_summary=[]
    for row in boundary_rows:
        checked=recompute_case(row,root/'boundary_state'/row['probe'])
        if row['probe']=='before_decision_store':
            require(row.get('outside_prepared_decision_guarantee') is True,'unpersisted decision boundary lost its scope marker')
        if row['probe']=='external_interleaving':
            preserved=any(record['fact']=='unit=newer-external-value' for record in row['physical_records'])
            require(row['newer_external_write_preserved']==preserved,'external intervening-write observation differs')
        boundary_summary.append(dict(probe=row['probe'],**checked))
    return dict(status='PASS',case_count=len(cases),cases_sha256=hashlib.sha256(data).hexdigest(),
                boundary_probes_checked=len(boundary_rows),boundary_observations=boundary_summary,
                structural_cases_per_policy=66,policy_count=8,
                independently_checked_metrics=METRICS,
                source_observations_checked=observations,policy_totals=totals,
                effect_call_scope='Committed participant put/delete operations; reset and cleanup excluded',
                scope='Archived finite cases and local abrupt subprocess exits; no power-loss or remote-provider guarantee')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args()
    result=check_campaign(args.campaign)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({key:value for key,value in result.items() if key!='policy_totals'},indent=2))


if __name__=='__main__':
    main()
