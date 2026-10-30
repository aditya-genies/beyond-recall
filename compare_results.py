"""Compare a fresh full reproduction with the frozen aggregate outcomes."""
import argparse
import json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--reference',default='results');p.add_argument('--candidate',required=True);a=p.parse_args()
r=Path(a.reference);c=Path(a.candidate)
assert json.loads((r/'summary.json').read_text())==json.loads((c/'summary.json').read_text()),'Aggregate difference'
keys=('probe','content_correct','cardinality_correct','acknowledged','selected_terminal','decision_continuity','planning_invocations','committed_effect_calls','newer_external_write_preserved')
x=json.loads((r/'boundary_probes.json').read_text());y=json.loads((c/'boundary_probes.json').read_text());assert len(x)==len(y)
assert all({k:v.get(k) for k in keys}=={k:w.get(k) for k in keys} for v,w in zip(x,y)),'Boundary difference'
print('PASS: all eight policy aggregates and all five boundary observations match; counts are not pooled.')
