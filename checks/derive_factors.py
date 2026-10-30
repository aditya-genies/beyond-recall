#!/usr/bin/env python3
"""Paired finite-cell factorial contrasts from verified archived cases only."""
import argparse
import csv
import hashlib
import itertools
import json
from collections import Counter,defaultdict
from pathlib import Path


def derive(root):
    raw=(root/'cases.jsonl').read_bytes()
    cases=[json.loads(line) for line in raw.splitlines() if line.strip()]
    index={(row['policy'],row['profile'],row['history']):row for row in cases}
    assert len(index)==528
    cells=sorted({(row['profile'],row['history']) for row in cases})
    assert len(cells)==66
    summaries=[];pairs=[]
    for factor,position in [('D',1),('P',3),('R',5)]:
        other=[candidate for candidate in (1,3,5) if candidate!=position]
        for combination in itertools.product('01',repeat=2):
            text=list('D0P0R0')
            for at,value in zip(other,combination):text[at]=value
            text[position]='0';low=''.join(text)
            text[position]='1';high=''.join(text)
            compared=[]
            for profile,history in cells:
                before=index[(low,profile,history)];after=index[(high,profile,history)]
                signatures=lambda row:[(attempt['attempt'],attempt['fault'],attempt['alternative']) for attempt in row['attempts']]
                assert signatures(before)==signatures(after),(low,high,profile,history,'unmatched schedule/tape')
                first=lambda row:next(event['digest'] for event in row['attempts'][0]['events'] if event['event']=='decision_chosen')
                assert first(before)==first(after),(low,high,profile,history,'initial decisions differ')
                pair=dict(factor=factor,low_policy=low,high_policy=high,profile=profile,history=history,
                    content_gain=int(after['content_correct'])-int(before['content_correct']),
                    terminal_gain=int(after['selected_terminal'])-int(before['selected_terminal']),
                    continuity_gain=int(after['decision_continuity'])-int(before['decision_continuity']),
                    planning_calls_saved=before['planning_invocations']-after['planning_invocations'],
                    committed_operations_saved=before['committed_effect_calls']-after['committed_effect_calls'])
                compared.append(pair);pairs.append(pair)
            summaries.append(dict(factor=factor,low_policy=low,high_policy=high,paired_cells=len(compared),
                **{metric:sum(pair[metric] for pair in compared) for metric in
                   ['content_gain','terminal_gain','continuity_gain','planning_calls_saved','committed_operations_saved']},
                terminal_improved_cells=sum(pair['terminal_gain']>0 for pair in compared),
                terminal_regressed_cells=sum(pair['terminal_gain']<0 for pair in compared)))
    barrier=Counter();returncodes=Counter();per_policy=defaultdict(Counter)
    for row in cases:
        for attempt in row['attempts']:
            returncodes[str(attempt['returncode'])]+=1
            per_policy[row['policy']]['process_attempts']+=1
            for event in attempt['events']:
                if event['event']=='abrupt_exit':
                    barrier[event['point']]+=1
                    per_policy[row['policy']][event['point']]+=1
    return dict(input='results/cases.jsonl',input_sha256=hashlib.sha256(raw).hexdigest(),
        analysis='Paired finite structural-cell comparisons; no additional experiment or inferential statistics',
        structural_cells_per_policy=66,policies=8,case_count=len(cases),
        matched_pair_comparisons=len(pairs),paired_factor_strata=summaries,
        observed_exit_barriers=dict(barrier),observed_process_returncodes=dict(returncodes),
        per_policy_attempts_and_barriers={key:dict(value) for key,value in per_policy.items()},
        pair_details=pairs)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True,help='Output basename without extension')
    args=parser.parse_args();result=derive(args.campaign)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.with_suffix('.json').write_text(json.dumps(result,indent=2)+'\n')
    with args.out.with_suffix('.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(result['paired_factor_strata'][0]))
        writer.writeheader();writer.writerows(result['paired_factor_strata'])
    print(json.dumps({key:value for key,value in result.items() if key not in ('pair_details','per_policy_attempts_and_barriers')},indent=2))


if __name__=='__main__':main()
