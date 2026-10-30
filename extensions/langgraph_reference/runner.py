#!/usr/bin/env python3
"""Native LangGraph reference; preserves the original participant and archives.

Uses the project's independent synthetic fixtures/planner, a real StateGraph,
a real SqliteSaver, and a separate application effect database. No live model.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import contextlib
import hashlib
import importlib.metadata
import inspect
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
from types import SimpleNamespace
from typing import TypedDict

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import study

# The reference does not use any network tracing or provider integration.
os.environ['LANGSMITH_TRACING'] = 'false'
os.environ['LANGCHAIN_TRACING_V2'] = 'false'
INTENT = 'intent-alpha'
EPOCH = 0
REFERENCE = 'langgraph_native'
ORIGINAL_SOURCE = '98378f217f0dae050dbc07aa04e1121ed9bc73862c2ee35a2e31a7a464f4e9b9'


class State(TypedDict, total=False):
    intent: str
    epoch: int
    plan: list[dict]
    outcome: str


def emit(event, **values):
    study.emit(event, **values)


def current_generation(folder):
    with study.managed_db(folder / 'recovery.sqlite') as connection:
        return connection.execute('SELECT epoch FROM epoch_state').fetchone()[0]


def cleanup(folder):
    with study.managed_db(folder / 'effects.sqlite') as connection:
        connection.execute('DELETE FROM records WHERE origin=? AND epoch=?', (INTENT, EPOCH))
    emit('cleanup', intent=INTENT, epoch=EPOCH)


def abrupt(args, point):
    if args.fault == point:
        emit('abrupt_exit', point=point)
        os._exit(87)


@contextlib.contextmanager
def native_graph(folder, args, log_writes=True):
    from langgraph.checkpoint.sqlite import SqliteSaver
    from langgraph.graph import END, START, StateGraph

    class ObservedSqliteSaver(SqliteSaver):
        """Instrumentation only: storage and serialization remain native."""
        def put(self, config, checkpoint, metadata, new_versions):
            result = super().put(config, checkpoint, metadata, new_versions)
            if log_writes:
                values = checkpoint.get('channel_values', {})
                plan = values.get('plan')
                emit('native_checkpoint_committed',
                     checkpoint_id=result['configurable'].get('checkpoint_id'),
                     step=metadata.get('step'),
                     plan_digest=study.fingerprint(plan) if isinstance(plan, list) else None,
                     outcome=values.get('outcome'),
                     channels=sorted(str(key) for key in values))
            return result

        def put_writes(self, config, writes, task_id, task_path=''):
            writes = tuple(writes)
            result = super().put_writes(config, writes, task_id, task_path)
            if log_writes:
                emit('native_task_writes_committed', task_id=str(task_id),
                     channels=[str(channel) for channel, _ in writes])
            return result

    def choose_decision(state):
        with study.managed_db(folder / 'recovery.sqlite') as connection:
            source = connection.execute(
                'SELECT facts FROM conversation WHERE enabled=1 AND epoch=? AND turn<=? ORDER BY turn',
                (EPOCH, 1)).fetchall()
        facts = [fact for row in source for fact in json.loads(row[0])]
        emit('source_selected', intent=INTENT, facts=facts)
        plan = study.make_plan(facts, args.profile, args.alternative)
        emit('decision_chosen', intent=INTENT, digest=study.fingerprint(plan), operations=plan)
        # No exit here: returning is what hands the plan to the real checkpointer.
        return {'plan': plan}

    def apply_effects(state):
        plan = state['plan']
        emit('native_plan_available', intent=INTENT, digest=study.fingerprint(plan))
        # sync durability persists choose_decision's result before this node starts.
        abrupt(args, 'after_prepare')
        put_count = 0
        for slot, operation in enumerate(plan):
            if operation['kind'] == 'put':
                address = operation['target'] or hashlib.sha256(
                    f'{INTENT}|slot={slot}'.encode()).hexdigest()[:24]
                with study.managed_db(folder / 'effects.sqlite') as connection:
                    connection.execute('INSERT OR REPLACE INTO records VALUES(?,?,?,?)',
                                       (address, operation['fact'], INTENT, EPOCH))
                    connection.execute(
                        'INSERT INTO committed_actions(attempt,kind,address,fact,origin,epoch) VALUES(?,?,?,?,?,?)',
                        (args.attempt, 'put', address, operation['fact'], INTENT, EPOCH))
                put_count += 1
                emit('effect_committed', intent=INTENT, slot=slot, kind='put',
                     address=address, fact=operation['fact'])
                if put_count == 1:
                    abrupt(args, 'after_first_put')
                    if args.fault == 'lost_put_reply':
                        raise RuntimeError('controlled committed put with unavailable reply')
                    if args.fault == 'reset_handshake':
                        (folder / 'reset-ready').write_text('ready')
                        deadline = time.monotonic() + 15
                        while not (folder / 'reset-continue').exists():
                            if time.monotonic() > deadline:
                                raise RuntimeError('reset handshake timeout')
                            time.sleep(.005)
            else:
                address = operation['target']
                with study.managed_db(folder / 'effects.sqlite') as connection:
                    connection.execute('DELETE FROM records WHERE address=?', (address,))
                    connection.execute(
                        'INSERT INTO committed_actions(attempt,kind,address,fact,origin,epoch) VALUES(?,?,?,?,?,?)',
                        (args.attempt, 'delete', address, None, INTENT, EPOCH))
                emit('effect_committed', intent=INTENT, slot=slot, kind='delete', address=address)
                if args.fault == 'lost_delete_reply':
                    raise RuntimeError('controlled committed delete with unavailable reply')
        outcome = 'applied'
        if current_generation(folder) != EPOCH:
            cleanup(folder)
            outcome = 'cancelled'
        # Exit before this node returns: its completion is not checkpointed yet.
        abrupt(args, 'after_effects')
        return {'outcome': outcome}

    builder = StateGraph(State)
    builder.add_node('choose_decision', choose_decision)
    builder.add_node('apply_effects', apply_effects)
    builder.add_edge(START, 'choose_decision')
    builder.add_edge('choose_decision', 'apply_effects')
    builder.add_edge('apply_effects', END)
    connection = sqlite3.connect(folder / 'native_checkpoints.sqlite', check_same_thread=False)
    connection.execute('PRAGMA synchronous=FULL')
    # SqliteSaver owns its schema and configures its documented SQLite backend.
    saver = ObservedSqliteSaver(connection)
    try:
        yield builder.compile(checkpointer=saver), saver
    finally:
        connection.close()


def snapshot(folder, profile):
    args = SimpleNamespace(profile=profile, alternative=False, fault='', attempt=-1)
    with native_graph(folder, args, log_writes=False) as (graph, saver):
        state = graph.get_state({'configurable': {'thread_id': INTENT}})
        result = dict(values=dict(state.values), next=list(state.next),
                      checkpoint_id=state.config.get('configurable', {}).get('checkpoint_id'),
                      step=(state.metadata or {}).get('step'))
        # The rows are produced by SqliteSaver, never by an application emulator.
        result['native_checkpoint_rows'] = saver.conn.execute('SELECT COUNT(*) FROM checkpoints').fetchone()[0]
        result['native_task_write_rows'] = saver.conn.execute('SELECT COUNT(*) FROM writes').fetchone()[0]
        result['checkpoint_journal_mode'] = saver.conn.execute('PRAGMA journal_mode').fetchone()[0]
        return result


def worker(args):
    folder = Path(args.directory)
    try:
        emit('worker_started', pid=os.getpid(), attempt=args.attempt)
        # This application guard is also applied before the original receipt path.
        if current_generation(folder) != EPOCH:
            cleanup(folder)
            emit('ack', intent=INTENT, outcome='cancelled')
            return 0
        with native_graph(folder, args) as (graph, _):
            config = {'configurable': {'thread_id': INTENT}}
            retained = graph.get_state(config)
            if retained.values and not retained.next and retained.values.get('outcome') in ('applied', 'cancelled'):
                emit('native_completed_checkpoint_hit', intent=INTENT,
                     checkpoint_id=retained.config['configurable'].get('checkpoint_id'))
                emit('ack', intent=INTENT, outcome=retained.values['outcome'])
                return 0
            if retained.values.get('plan'):
                emit('decision_loaded', intent=INTENT, digest=study.fingerprint(retained.values['plan']))
            result = graph.invoke(None if retained.values else {'intent': INTENT, 'epoch': EPOCH},
                                  config, durability='sync')
            completed = graph.get_state(config)
            if completed.next or completed.values.get('outcome') not in ('applied', 'cancelled'):
                raise RuntimeError('native graph returned without completed checkpoint')
            emit('native_completed_checkpoint_observed', checkpoint_id=completed.config['configurable'].get('checkpoint_id'),
                 outcome=completed.values['outcome'])
            abrupt(args, 'after_finalize')
            emit('ack', intent=INTENT, outcome=result['outcome'])
            return 0
    except Exception as exception:
        emit('attempt_failed', error_type=type(exception).__name__, error=str(exception))
        return 74


def invoke(folder, profile, attempt, fault='', alternative=False):
    command = [sys.executable, str(Path(__file__).resolve()), 'worker', '--directory', str(folder),
               '--profile', profile, '--attempt', str(attempt), '--fault', fault]
    if alternative:
        command.append('--alternative')
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if fault == 'reset_handshake':
        deadline = time.monotonic() + 18
        while not (folder / 'reset-ready').exists() and process.poll() is None:
            if time.monotonic() > deadline:
                process.kill()
                process.communicate()
                raise RuntimeError('parent reset handshake timed out')
            time.sleep(.005)
        if (folder / 'reset-ready').exists():
            study.reset(folder, False)
            (folder / 'reset-continue').write_text('continue')
    output, error = process.communicate(timeout=30)
    events = [json.loads(line) for line in output.splitlines() if line.strip()]
    return dict(attempt=attempt, pid=process.pid, returncode=process.returncode, fault=fault,
                alternative=alternative, events=events, stderr=error,
                acknowledged=process.returncode == 0 and any(event['event'] == 'ack' for event in events),
                native_snapshot=snapshot(folder, profile))


def fault_for(history):
    if history.startswith('exit_after_prepare'):
        return 'after_prepare'
    if history.startswith('exit_after_first_put') or history == 'reset_before_retry':
        return 'after_first_put'
    if history.startswith('lost_put_reply'):
        return 'lost_put_reply'
    if history.startswith('exit_after_effects'):
        return 'after_effects'
    if history.startswith('exit_after_finalize'):
        return 'after_finalize'
    return {'reset_during_effects': 'reset_handshake', 'lost_delete_reply': 'lost_delete_reply'}.get(history, '')


def run_case(root, profile, history):
    folder = root / 'state' / f'{REFERENCE}__{profile}__{history}'
    study.setup(folder, profile, history)
    attempts = [invoke(folder, profile, 0, fault_for(history))]
    if history == 'reset_before_retry':
        study.reset(folder, True)
    if history.startswith('redelivery') or not attempts[0]['acknowledged']:
        attempts.append(invoke(folder, profile, 1, alternative='drift' in history))
    expected = [] if history.startswith('reset_') else study.FACTS
    return dict(policy=REFERENCE, profile=profile, history=history,
                **study.metrics(folder, attempts, expected),
                checkpoint_snapshot=snapshot(folder, profile))


def package_provenance():
    from langgraph.graph import StateGraph
    from langgraph.checkpoint.sqlite import SqliteSaver
    versions = {name: importlib.metadata.version(name) for name in
                ('langgraph', 'langgraph-checkpoint', 'langgraph-checkpoint-sqlite', 'langchain-core')}
    sources = {}
    for label, obj in [('StateGraph', StateGraph), ('SqliteSaver', SqliteSaver)]:
        path = Path(inspect.getsourcefile(obj))
        try:
            relative = path.relative_to(sys.prefix).as_posix()
        except ValueError:
            relative = path.name
        sources[label] = dict(installed_source=relative, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    return dict(versions=versions, installed_public_sources=sources, python=sys.version.split()[0],
                sqlite=sqlite3.sqlite_version)


def campaign(args):
    root = Path(args.out)
    root.mkdir(parents=True, exist_ok=True)
    if (root / 'cases.jsonl').exists():
        raise RuntimeError('refusing to replace an existing reference campaign')
    if hashlib.sha256((ROOT / 'study.py').read_bytes()).hexdigest() != ORIGINAL_SOURCE:
        raise RuntimeError('frozen original participant differs')
    tasks = [(profile, history) for profile in study.PROFILES for history in study.HISTORIES
             if history != 'lost_delete_reply' or profile in ('retire', 'mixed')]
    spec = dict(reference=REFERENCE, comparator='D1P1R1', structural_cases=len(tasks),
                profiles=list(study.PROFILES), histories=list(study.HISTORIES),
                matched_cases='All declared cells use the same semantic barriers; actual checkpoint-write/mid-commit faults are not tested.',
                source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                original_study_sha256=ORIGINAL_SOURCE,
                graph='START -> choose_decision -> apply_effects -> END', durability='sync',
                persistence='Native SqliteSaver; no application decision or receipt row is used',
                explicit_application_logic=['generation guard', 'source query', 'literal target bindings', 'stable effect addresses', 'cleanup', 'completed-checkpoint fast path'],
                **package_provenance())
    (root / 'frozen_spec.json').write_text(json.dumps(spec, indent=2) + '\n')
    cases = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(run_case, root, profile, history) for profile, history in tasks]
        for future in concurrent.futures.as_completed(futures):
            cases.append(future.result())
    cases.sort(key=lambda row: (row['profile'], row['history']))
    (root / 'cases.jsonl').write_text(''.join(study.js(row) + '\n' for row in cases))
    summary = dict(reference=REFERENCE, structural_cases=len(cases),
                   **{name: sum(row[field] for row in cases) for name, field in
                      [('content_pass', 'content_correct'), ('cardinality_pass', 'cardinality_correct'),
                       ('selected_terminal_pass', 'selected_terminal'), ('decision_continuity_pass', 'decision_continuity'),
                       ('acknowledged', 'acknowledged'), ('planning_invocations', 'planning_invocations'),
                       ('committed_effect_calls', 'committed_effect_calls')]},
                   process_attempts=sum(len(row['attempts']) for row in cases),
                   abrupt_exits=sum(attempt['returncode'] == 87 for row in cases for attempt in row['attempts']))
    (root / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    child = sub.add_parser('worker')
    child.add_argument('--directory', required=True)
    child.add_argument('--profile', choices=study.PROFILES, required=True)
    child.add_argument('--attempt', type=int, required=True)
    child.add_argument('--fault', default='')
    child.add_argument('--alternative', action='store_true')
    run = sub.add_parser('campaign')
    run.add_argument('--out', required=True)
    run.add_argument('--workers', type=int, default=4)
    args = parser.parse_args()
    if args.command == 'worker':
        sys.exit(worker(args))
    campaign(args)
