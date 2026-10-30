#!/usr/bin/env python3
"""Audit event/SQLite correspondence, declared barriers and retained state.

Reads archived evidence only and never imports the participant implementation.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

from check_results import digest,read_table,require


def audit(root):
    cases=[json.loads(line) for line in (root/'cases.jsonl').read_text().splitlines()]
    barriers=Counter();outcomes=Counter();attempts_total=0
    for case in cases:
        history=case['history'];profile=case['profile'];policy=case['policy']
        folder=root/'state'/f'{policy}__{profile}__{history}'
        decisions=read_table(folder/'recovery.sqlite','decisions','intent')
        receipts=read_table(folder/'recovery.sqlite','receipts','intent')
        chosen=[event for attempt in case['attempts'] for event in attempt['events'] if event['event']=='decision_chosen']
        require(len(decisions)==int(policy[3]=='1'),'decision retention differs from factorial setting')
        if decisions:
            require(decisions[0]['epoch']==0 and decisions[0]['intent']=='intent-alpha','retained decision identity differs')
            require(digest(json.loads(decisions[0]['body']))==chosen[0]['digest'],'retained decision differs from initial literal plan')
        require(len(receipts)==int(policy[5]=='1' and history!='reset_before_retry'),'receipt presence differs from schedule/policy')
        if receipts:
            require(receipts[0]['epoch']==0 and receipts[0]['intent']=='intent-alpha','receipt identity differs')
            require(receipts[0]['decision']==chosen[-1]['digest'],'receipt does not record its executed decision')
            require(receipts[0]['outcome']==('cancelled' if history=='reset_during_effects' else 'applied'),'receipt outcome differs')
        fault=''
        if history.startswith('exit_after_prepare'):fault='after_prepare'
        elif history.startswith('exit_after_first_put') or history=='reset_before_retry':fault='after_first_put'
        elif history.startswith('exit_after_effects'):fault='after_effects'
        elif history.startswith('exit_after_finalize'):fault='after_finalize'
        elif history.startswith('lost_put_reply'):fault='lost_put_reply'
        elif history=='lost_delete_reply':fault='lost_delete_reply'
        elif history=='reset_during_effects':fault='reset_handshake'
        require(case['attempts'][0]['fault']==fault,'first attempt fault differs from declared history')
        first_code=87 if fault.startswith('after_') else 74 if fault in ('lost_put_reply','lost_delete_reply') else 0
        require(case['attempts'][0]['returncode']==first_code,'first outcome differs from declared injection')
        should_repeat=first_code!=0 or history.startswith('redelivery')
        require(len(case['attempts'])==(2 if should_repeat else 1),'unexpected number of attempts')
        state={}
        if profile in ('revise','mixed'):state['existing-unit']=dict(address='existing-unit',fact='unit=imperial',origin='fixture',epoch=0)
        if profile in ('retire','mixed'):state['retired-entry']=dict(address='retired-entry',fact='obsolete=yes',origin='fixture',epoch=0)
        reset_seen=False
        for position,attempt in enumerate(case['attempts']):
            attempts_total+=1;outcomes[str(attempt['returncode'])]+=1
            require(attempt['attempt']==position,'attempt ordinal differs')
            require(not attempt['stderr'],'worker stderr is nonempty')
            require(attempt['alternative']==(position==1 and 'drift' in history),'decision tape differs from declared history')
            if position:
                require(attempt['returncode']==0 and not attempt['fault'],'resumed attempt did not complete without another injected fault')
            committed=[event for event in attempt['events'] if event['event']=='effect_committed']
            require([event['slot'] for event in committed]==list(range(len(committed))),
                    'effects are not the sequential prefix of the chosen instruction list')
            for event in attempt['events']:
                if event['event']=='abrupt_exit':
                    barriers[event['point']]+=1
                    require(position==0 and event['point']==fault,'abrupt exit at undeclared barrier')
                if event['event']=='effect_committed':
                    if event['kind']=='put':
                        state[event['address']]=dict(address=event['address'],fact=event['fact'],origin='intent-alpha',epoch=0)
                        if history=='reset_during_effects' and not reset_seen:
                            require((folder/'reset-ready').exists() and (folder/'reset-continue').exists(),
                                    'generation schedule lacks its actual process handshake')
                            state={};reset_seen=True
                    else:state.pop(event['address'],None)
                if event['event']=='cleanup':
                    state={key:value for key,value in state.items()
                           if not (value['origin']==event['intent'] and value['epoch']==event['epoch'])}
            if position==0 and history=='reset_before_retry':
                state={key:value for key,value in state.items() if value['origin']!='fixture'}
            if position==0:
                if fault=='after_prepare':require(not committed,'prepare exit unexpectedly committed effects')
                elif fault in ('after_first_put','lost_put_reply'):
                    require(sum(event['kind']=='put' for event in committed)==1,'first-put boundary has wrong prefix')
                elif fault in ('after_effects','after_finalize'):
                    require(len(committed)==len(chosen[0]['operations']),'final-effect boundary lacks all operations')
                elif fault=='lost_delete_reply':
                    require(sum(event['kind']=='delete' for event in committed)==1,'delete-response boundary lacks its committed delete')
        require(sorted(state.values(),key=lambda row:row['address'])==case['physical_records'],
                'final physical state differs from replayed observed effects and declared resets')
    return dict(status='PASS',campaign=root.as_posix(),cases_audited=len(cases),
                process_attempts=attempts_total,observed_returncodes=dict(outcomes),observed_abrupt_barriers=dict(barriers),
                decision_retention_matches_factor=True,receipt_state_matches_factor=True,
                literal_retained_plans_verified=True,final_state_reconstructed_from_events=True,
                actual_generation_handshakes_verified=True,
                boundary_scope='Named post-commit semantic barriers; not interruption inside SQLite commit or machine power loss')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args();report=audit(args.campaign)
    args.out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
