"""One literal-slot figure from the independently verified 1,008 query cases."""
from pathlib import Path
from hashlib import sha256
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

HERE=Path(__file__).resolve().parent
STUDY=HERE.parent/'mem0_reference'
DATA=STUDY/'retrieval_results'
STEM='fig_mem0_retrieval_slots'
SIZES=[8,12,24,40]
STATES=['baseline','native_k10','widened_candidates','exact_admission']
BLUE,CLAY,PALE_CLAY,INK,GRAY='#49667b','#96765f','#c9b4a3','#303840','#67727c'

def sha(p):return sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
verification=load(DATA/'verification.json');protocol=load(DATA/'protocol.json')
assert verification['status']=='PASS' and verification['native_search_calls']==1008
assert verification['computational_reproduction']['status']=='PASS'
for filename,key in [('cases.json','cases_sha256'),('states.json','states_sha256'),('summary.json','summary_sha256'),('protocol.json','protocol_sha256')]:
    assert sha(DATA/filename)==verification[key]
assert (DATA/'protocol.sha256').read_text().strip()==sha(DATA/'protocol.json')
assert sha(STUDY/'retrieval.py')==protocol['source_sha256']
for rel,digest in protocol['protected_inputs'].items():assert sha(STUDY/rel)==digest,rel
input_files=[DATA/n for n in ['cases.json','states.json','summary.json','protocol.json','protocol.sha256','verification.json']]+[STUDY/'retrieval.py']
input_hashes={str(p.relative_to(HERE.parent)):sha(p) for p in input_files}
cases=load(DATA/'cases.json');states=load(DATA/'states.json')
assert len(cases)==1008
state_maps={(s['n_source_preferences'],s['state']):{r['id']:r for r in s['native_records']} for s in states}
queries={n:{r['memory'] for r in state_maps[n,'baseline'].values()} for n in SIZES}
assert all(len(queries[n])==n for n in SIZES)
expected={(n,s,k,q) for n in SIZES for s in STATES for k in [5,10,20] for q in queries[n]}
keys=[(r['n_source_preferences'],r['state'],r['budget'],r['query']) for r in cases]
assert len(keys)==len(set(keys)) and set(keys)==expected
derived=[]
for row in cases:
    records=row['results'];n=row['n_source_preferences'];state=row['state']
    texts=[r['memory'] for r in records]
    assert len({r['id'] for r in records})==len(records)
    for result in records:
        original=state_maps[n,state][result['id']]
        assert result['memory']==original['memory'] and result['hash']==original['hash']
    assert row['query_sha256']==sha256(row['query'].encode()).hexdigest()
    counts=dict(returned_records=len(records),distinct_literal_facts=len(set(texts)),duplicate_context_slots=len(texts)-len(set(texts)),exact_target_present=row['query'] in texts)
    assert all(row[k]==v for k,v in counts.items())
    derived.append(dict(n=n,state=state,budget=row['budget'],query=row['query'],query_sha256=row['query_sha256'],**counts))
selected=[r for r in derived if r['budget']==10]
assert len(selected)==336
target_count=sum(r['exact_target_present'] for r in selected)
assert target_count==336
groups=[]
for n in SIZES:
    for state in STATES:
        rows=[r for r in selected if r['n']==n and r['state']==state]
        assert len(rows)==n
        groups.append(dict(n=n,state=state,query_count=n,total_returned_slots=sum(r['returned_records'] for r in rows),total_distinct_strings=sum(r['distinct_literal_facts'] for r in rows),total_duplicate_slots=sum(r['duplicate_context_slots'] for r in rows),
          mean_returned_slots=sum(r['returned_records'] for r in rows)/n,mean_distinct_strings=sum(r['distinct_literal_facts'] for r in rows)/n,mean_duplicate_slots=sum(r['duplicate_context_slots'] for r in rows)/n,exact_target_present_count=sum(r['exact_target_present'] for r in rows)))
    base={r['query']:(r['returned_records'],r['distinct_literal_facts'],r['duplicate_context_slots']) for r in selected if r['n']==n and r['state']=='baseline'}
    for control in ['widened_candidates','exact_admission']:
        candidate={r['query']:(r['returned_records'],r['distinct_literal_facts'],r['duplicate_context_slots']) for r in selected if r['n']==n and r['state']==control}
        assert candidate==base
by_key={(r['n'],r['state']):r for r in groups}
for group in groups:
    verified=next(g for g in verification['groups'] if (g['n_source_preferences'],g['state'],g['budget'])==(group['n'],group['state'],10))
    assert group['total_returned_slots']==verified['total_returned_records']
    assert group['total_distinct_strings']==verified['total_distinct_literal_facts']
    assert group['total_duplicate_slots']==verified['duplicate_context_slots']

plt.rcParams.update({'font.family':'serif','font.serif':['DejaVu Serif'],'font.size':7,'axes.labelsize':7,'axes.linewidth':.6,'xtick.labelsize':6.6,'ytick.labelsize':6.4,
 'legend.fontsize':6.4,'figure.dpi':300,'savefig.dpi':300,'pdf.fonttype':42,'ps.fonttype':42,'hatch.linewidth':.45})
fig=plt.figure(figsize=(4.5,3.6));ax=fig.add_axes([.15,.205,.82,.545])
ax.spines['top'].set_visible(False);ax.spines['right'].set_visible(False)
ax.tick_params(length=2.4,width=.6);ax.grid(axis='y',color='#d7dcdf',linewidth=.5,alpha=.65);ax.set_axisbelow(True)
ax.set_ylim(0,10.6);ax.set_xlim(-.6,3.6);ax.set_yticks([0,2,4,6,8,10]);ax.set_xticks(range(4),[str(n) for n in SIZES])
ax.set_xlabel('Initial source preferences, N',labelpad=6);ax.set_ylabel('Mean returned slots per query',labelpad=6)
x=np.arange(4);width=.32;segments=[];labels=[]
for offset,state in [(-.19,'baseline'),(.19,'native_k10')]:
    distinct=[by_key[n,state]['mean_distinct_strings'] for n in SIZES]
    duplicate=[by_key[n,state]['mean_duplicate_slots'] for n in SIZES]
    bottom=ax.bar(x+offset,distinct,width,color=BLUE,label='Distinct exact strings' if state=='baseline' else None,zorder=3)
    top=ax.bar(x+offset,duplicate,width,bottom=distinct,color=PALE_CLAY,edgecolor=CLAY,hatch='///',linewidth=.5,label='Duplicate slots' if state=='baseline' else None,zorder=3)
    for bars,values,color in [(bottom,distinct,'white'),(top,duplicate,INK)]:
        for i,(bar,value) in enumerate(zip(bars,values)):
            if value<=0:continue
            number=f'{value:.3f}'.rstrip('0').rstrip('.')
            text=ax.text(bar.get_x()+bar.get_width()/2,bar.get_y()+bar.get_height()/2,number,ha='center',va='center',fontsize=6.0,color=color,zorder=4)
            labels.append((f'{state}_{"distinct" if bars is bottom else "duplicate"}_{i}',text,bar))
annotation=ax.text(0,8.28,'8 returned; 2 unused',ha='center',va='bottom',fontsize=6.0,color=GRAY)
title=fig.text(.035,.98,'Mem0 exact-target presence and slot diversity',fontsize=8.0,fontweight='bold',va='top',color=INK)
subtitle=fig.text(.035,.927,'Left: baseline + both controls (identical counts); right: native retry',fontsize=6.2,va='top',color=GRAY)
presence=fig.text(.035,.875,f'Exact target present: {target_count}/{len(selected)} (100%) at K = 10, across all four states',fontsize=6.1,va='top',color=INK)
legend=fig.legend(loc='upper left',bbox_to_anchor=(.15,.82),ncol=2,frameon=False,borderpad=0,borderaxespad=0,handlelength=1.8,columnspacing=1.7)
footers=[fig.text(.035,.067,'Means over N exact-literal queries per state; finite paired cases, no error bars.',fontsize=5.7,color=GRAY),
 fig.text(.035,.025,'Returned-slot counts only; no answer-quality, semantic-accuracy, or harm inference.',fontsize=5.6,color=GRAY)]

fig.canvas.draw();renderer=fig.canvas.get_renderer()
artists={'axes':ax,'legend':legend,'title':title,'subtitle':subtitle,'presence':presence,'xlabel':ax.xaxis.label,'ylabel':ax.yaxis.label,'unused_note':annotation}
artists.update({f'footer_{i}':a for i,a in enumerate(footers)})
artists.update({f'xtick_{i}':a for i,a in enumerate(ax.get_xticklabels())})
boxes={name:a.get_window_extent(renderer) for name,a in artists.items()}
checks=[]
def apart(a,b,gap_required=6):
    p,q=boxes[a],boxes[b];overlap=p.x0<q.x1 and q.x0<p.x1 and p.y0<q.y1 and q.y0<p.y1
    gap=max(p.x0-q.x1,q.x0-p.x1,p.y0-q.y1,q.y0-p.y1,0)
    checks.append(dict(first=a,second=b,gap_px=round(float(gap),3),required_gap_px=gap_required,overlap=bool(overlap),passed=bool(not overlap and gap>=gap_required)))
for a,b in [('title','subtitle'),('subtitle','presence'),('presence','legend'),('legend','axes'),('legend','unused_note'),('footer_0','footer_1')]:apart(a,b)
for i in range(2):
    for name in artists:
        if not name.startswith('footer_'):apart(f'footer_{i}',name)
for i in range(4):apart('xlabel',f'xtick_{i}')
containment=[]
for name,text,bar in labels:
    box=text.get_window_extent(renderer);container=bar.get_window_extent(renderer);boxes[name]=box
    margins=[box.x0-container.x0,container.x1-box.x1,box.y0-container.y0,container.y1-box.y1]
    containment.append(dict(label=name,label_bbox_px=[round(float(v),3) for v in box.extents],bar_bbox_px=[round(float(v),3) for v in container.extents],minimum_margin_px=round(float(min(margins)),3),required_margin_px=5,passed=bool(min(margins)>=5)))
    apart('legend',name);apart('footer_0',name);apart('footer_1',name)
for state in ['baseline','native_k10']:
    bar=next(bar for name,text,bar in labels if name==state+'_distinct_0')
    boxes['n8_'+state+'_bar']=bar.get_window_extent(renderer)
    apart('unused_note','n8_'+state+'_bar')
outside=[name for name,b in boxes.items() if b.x0<0 or b.y0<0 or b.x1>fig.bbox.width or b.y1>fig.bbox.height]
spacing=dict(status='PASS' if all(c['passed'] for c in checks+containment) and not outside else 'FAIL',coordinate_system='300-DPI pixels, bottom-left origin',canvas_px=[1350,1080],bboxes={k:[round(float(v),3) for v in b.extents] for k,b in boxes.items()},checks=checks,label_containment=containment,outside_canvas=outside)
(HERE/(STEM+'_spacing.json')).write_text(json.dumps(spacing,indent=2)+'\n')
assert spacing['status']=='PASS','Label/legend spacing gate failed'
for ext in ['png','pdf','svg']:fig.savefig(HERE/(STEM+'.'+ext),dpi=300,facecolor='white')
plt.close(fig)
source_data=dict(budget=10,distinct_N_query_pairs=sum(SIZES),query_cells=336,exact_target_present_count=target_count,displayed_groups=groups,per_query_partitions=selected,combined_left_bar_states=['baseline','widened_candidates','exact_admission'],controls_match_baseline_per_query_partitions=True,means_are_arithmetic_not_population_estimates=True)
(HERE/(STEM+'_source_data.json')).write_text(json.dumps(source_data,indent=2)+'\n')
caption='Partition of returned slots under native BGE/BM25 search at retrieval budget K = 10 for all baseline exact-fact queries at N = 8, 12, 24 and 40. Each pair shows baseline on the left and the native recent-context, fresh-model retry state on the right; both authored control states have the same per-query count partition as baseline and share its bar. Stacks show means of distinct exact strings and duplicate slots over N queries per state, with labels rounded to three decimals. N = 8 returns eight records; its two unused budget slots are not duplicates. The exact queried string is present in all 336 selected query-state cells. These literal-exposure observations do not establish semantic diversity, answer quality, harm or population reliability.'
captions=load(HERE/'captions.json');captions[STEM]=caption;(HERE/'captions.json').write_text(json.dumps(captions,indent=2)+'\n')
assert all(sha(p)==input_hashes[str(p.relative_to(HERE.parent))] for p in input_files)
assert all(sha(STUDY/rel)==h for rel,h in protocol['protected_inputs'].items())
provenance=dict(status='PASS',renderer_sha256=sha(Path(__file__)),input_sha256=input_hashes,source_sha256=verification['source_sha256'],protocol_sha256=verification['protocol_sha256'],verification_status='PASS',protected_source_input_sha256=protocol['protected_inputs'],full_case_count=1008,displayed_budget=10,displayed_query_state_cells=336,distinct_N_query_pairs=84,
 exact_target_presence=dict(numerator=target_count,denominator=len(selected),fraction=target_count/len(selected)),all_four_N_values=SIZES,groups=groups,source_data_sha256=sha(HERE/(STEM+'_source_data.json')),same_computation_reproduction=verification['computational_reproduction'],
 figure=dict(aspect_ratio='5:4',inches=[4.5,3.6],dpi=300,pixels=[1350,1080],files={ext:sha(HERE/(STEM+'.'+ext)) for ext in ['png','pdf','svg']}),input_files_unchanged=True,
 interpretation='Post hoc finite exact-literal retrieval exposure; no QA, semantic-quality, harm, population rate, independent-replication or token-cost inference. Paired states/queries are not independent samples.',spacing_report=STEM+'_spacing.json')
(HERE/(STEM+'_provenance.json')).write_text(json.dumps(provenance,indent=2)+'\n')
print(json.dumps(dict(status='PASS',target_presence=f'{target_count}/{len(selected)}',native_means=[by_key[n,'native_k10']['mean_distinct_strings'] for n in SIZES],native_duplicate_means=[by_key[n,'native_k10']['mean_duplicate_slots'] for n in SIZES]),indent=2))
