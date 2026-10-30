"""Run and independently check one specified case in a new output directory."""
import argparse,json
from pathlib import Path
import study
from checks.check_results import recompute_case
p=argparse.ArgumentParser();p.add_argument('--policy',choices=study.POLICIES,required=True);p.add_argument('--profile',choices=study.PROFILES,required=True);p.add_argument('--history',choices=study.HISTORIES,required=True);p.add_argument('--out',required=True);a=p.parse_args()
if a.history=='lost_delete_reply' and a.profile not in ('retire','mixed'):p.error('Lost-delete history requires retire or mixed profile')
r=Path(a.out);r.mkdir(parents=True,exist_ok=False)
x=study.run_case(r,a.policy,a.profile,a.history);recompute_case(x,r/'state'/f'{a.policy}__{a.profile}__{a.history}')
(r/'case.json').write_text(json.dumps(x,indent=2)+'\n');print(json.dumps({k:x[k] for k in ('policy','profile','history','selected_terminal','decision_continuity','planning_invocations','committed_effect_calls')},indent=2))
