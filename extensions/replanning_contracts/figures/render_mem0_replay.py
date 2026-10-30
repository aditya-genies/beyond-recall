"""One measured scientific figure from verified frozen Mem0 cases only."""
from pathlib import Path
from hashlib import sha256
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.transforms import Bbox

HERE=Path(__file__).resolve().parent
STUDY=HERE.parent/'mem0_reference'
RESULTS=STUDY/'results'
STEM='fig_mem0_bulk_replay'
SIZES=[1,5,10,11,13,20,21,40]
ARMS=['native_k10','widened_candidates','exact_admission']
INK,GRAY,BLUE,CLAY='#303840','#67727c','#49667b','#96765f'

def sha(path):return sha256(path.read_bytes()).hexdigest()
def load(path):return json.loads(path.read_text())

verification=load(STUDY/'verification.json')
assert verification['status']=='PASS' and verification['case_count']==96
for rel,digest in verification['raw_sha256'].items():assert sha(RESULTS/rel)==digest,rel
inputs=[RESULTS/'cases.json',RESULTS/'frozen_spec.json',RESULTS/'summary.json',STUDY/'verification.json',STUDY/'checker_provenance.json']
input_hashes={str(p.relative_to(HERE.parent)):sha(p) for p in inputs}
rows=load(RESULTS/'cases.json')
index={(r['embedder'],r['extractor'],r['arm'],r['n']):r for r in rows}
values={a:[[index['bge_small','visible_delta',a,n]['attempts'][t]['physical_records'] for n in SIZES] for t in range(3)] for a in ARMS}
for e in ['hash_control','bge_small']:
    for x in ['literal_reemit','visible_delta']:
        for a in ARMS:
            for t in range(3):
                assert [index[e,x,a,n]['attempts'][t]['physical_records'] for n in SIZES]==values[a][t]
                assert all(index[e,x,a,n]['attempts'][t]['fact_set_matches'] for n in SIZES)
assert values['native_k10'][0]==SIZES
assert all(v==SIZES for a in ['widened_candidates','exact_admission'] for v in values[a])

plt.rcParams.update({'font.family':'serif','font.serif':['DejaVu Serif'],'font.size':7,
 'axes.labelsize':7,'axes.linewidth':.6,'xtick.labelsize':6.4,'ytick.labelsize':6.4,
 'legend.fontsize':6.5,'figure.dpi':300,'savefig.dpi':300,'pdf.fonttype':42,'ps.fonttype':42})
fig=plt.figure(figsize=(4.5,3.6))
ax=fig.add_axes([.15,.205,.765,.525])
ax.spines['top'].set_visible(False);ax.spines['right'].set_visible(False)
ax.tick_params(length=2.4,width=.6)
ax.grid(axis='y',color='#d7dcdf',linewidth=.5,alpha=.65);ax.set_axisbelow(True)
ax.set_xlim(0,44);ax.set_ylim(0,108)
ax.set_xticks([0,10,20,30,40]);ax.set_yticks([0,20,40,60,80,100])
ax.set_xlabel('Initial exact facts, N',labelpad=6)
ax.set_ylabel('Physical memory records',labelpad=6)
shared,=ax.plot(SIZES,SIZES,color=GRAY,linewidth=1.1,marker='o',markersize=3.0,markerfacecolor='white',markeredgewidth=.7,
 label='Initial add (all arms); widened-candidate +\nexact-admission controls (all calls)')
first,=ax.plot(SIZES,values['native_k10'][1],color=CLAY,linewidth=1.2,marker='^',markersize=3.2,
 label='Native k = 10: after first retry')
second,=ax.plot(SIZES,values['native_k10'][2],color=BLUE,linewidth=1.2,marker='s',markersize=3.0,
 label='Native k = 10: after second retry')
ax.axvline(10,color='#a4adb3',linestyle=(0,(2,3)),linewidth=.6,zorder=0)
limit_note=ax.text(11.2,98,'Native candidate limit\nk = 10',color=GRAY,fontsize=6.1,ha='left',va='top')
endpoint_labels=[]
for y,color in [(40,GRAY),(values['native_k10'][1][-1],CLAY),(values['native_k10'][2][-1],BLUE)]:
    endpoint_labels.append(ax.annotate(str(y),(40,y),xytext=(7,0),textcoords='offset points',ha='left',va='center',fontsize=6.4,color=color,fontweight='bold',bbox={'facecolor':'white','edgecolor':'none','pad':.5}))
title=fig.text(.035,.98,'Mem0 physical growth under controlled replay',ha='left',va='top',fontsize=8.1,fontweight='bold',color=INK)
subtitle=fig.text(.035,.93,'Displayed: BGE-small embeddings / visible-delta extractor',ha='left',va='top',fontsize=6.5,color=GRAY)
legend=fig.legend(handles=[shared,first,second],loc='upper left',bbox_to_anchor=(.15,.878),frameon=False,
 borderaxespad=0,borderpad=0,labelspacing=.32,handlelength=2)
footers=[fig.text(.035,.067,'Eight specified N values; no live-model incidence or semantic-quality estimate.',fontsize=5.8,color=GRAY),
 fig.text(.035,.025,'The other three controlled extractor/embedding configurations match these counts.',fontsize=5.7,color=GRAY)]

fig.canvas.draw();renderer=fig.canvas.get_renderer()
artists={'axes':ax,'legend':legend,'title':title,'subtitle':subtitle,'xlabel':ax.xaxis.label,'ylabel':ax.yaxis.label,'limit_note':limit_note}
artists.update({f'endpoint_label_{i}':x for i,x in enumerate(endpoint_labels)})
artists.update({f'footer_{i}':x for i,x in enumerate(footers)})
artists.update({f'xtick_{i}':x for i,x in enumerate(ax.get_xticklabels())})
artists.update({f'ytick_{i}':x for i,x in enumerate(ax.get_yticklabels())})
boxes={k:v.get_window_extent(renderer) for k,v in artists.items()}
for i,label in enumerate(endpoint_labels):boxes[f'endpoint_label_{i}']=label.get_bbox_patch().get_window_extent(renderer)
for i,y in enumerate([40,values['native_k10'][1][-1],values['native_k10'][2][-1]]):
    xpixel,ypixel=ax.transData.transform((40,y));radius=3.2*300/144
    boxes[f'endpoint_marker_{i}']=Bbox.from_extents(xpixel-radius,ypixel-radius,xpixel+radius,ypixel+radius)
checks=[]
def apart(a,b,minimum=6):
    x,y=boxes[a],boxes[b]
    overlap=x.x0<y.x1 and y.x0<x.x1 and x.y0<y.y1 and y.y0<x.y1
    gap=max(x.x0-y.x1,y.x0-x.x1,x.y0-y.y1,y.y0-x.y1,0)
    checks.append(dict(first=a,second=b,gap_px=round(float(gap),3),required_gap_px=minimum,overlap=bool(overlap),passed=bool(not overlap and gap>=minimum)))
apart('legend','axes',12);apart('legend','subtitle');apart('subtitle','title')
apart('legend','limit_note')
for i in range(3):
    apart('legend',f'endpoint_label_{i}')
    apart(f'endpoint_label_{i}',f'endpoint_marker_{i}')
    for j in range(i+1,3):apart(f'endpoint_label_{i}',f'endpoint_label_{j}')
for i in range(2):
    for name in boxes:
        if name!=f'footer_{i}' and not name.startswith('footer_'):apart(f'footer_{i}',name)
apart('footer_0','footer_1')
for i in range(len(ax.get_xticklabels())):apart('xlabel',f'xtick_{i}')
outside=[name for name,b in boxes.items() if b.x0<0 or b.y0<0 or b.x1>fig.bbox.width or b.y1>fig.bbox.height]
spacing=dict(status='PASS' if all(c['passed'] for c in checks) and not outside else 'FAIL',coordinate_system='300-DPI pixels, bottom-left origin',canvas_px=[int(fig.bbox.width),int(fig.bbox.height)],
 bboxes={k:[round(float(v),3) for v in b.extents] for k,b in boxes.items()},checks=checks,outside_canvas=outside,
 scope='Critical legend/axes/labels and footer/xlabel/labels separations; explicit endpoint marker clearance. Pixel inspection is additionally required.')
(HERE/(STEM+'_spacing.json')).write_text(json.dumps(spacing,indent=2)+'\n')
assert spacing['status']=='PASS','Figure spacing check failed'
for extension in ['png','pdf','svg']:fig.savefig(HERE/(STEM+'.'+extension),dpi=300,facecolor='white')
plt.close(fig)
assert all(sha(p)==input_hashes[str(p.relative_to(HERE.parent))] for p in inputs)
caption='Physical record counts under controlled exact-source replay in native Mem0 and two authored controls. Points display local BGE-small embeddings with the controlled visible-delta extractor; the other three controlled extractor/embedding configurations give identical counts. The shared curve explicitly combines initial calls in all arms and both widened-candidate and sequential exact-admission controls at every call. Native k = 10 grows from 40 to 70 to 100 records for N = 40 while preserving the 40-string exact fact set. These are finite parameterized executions with repeated calls, not independent live-model trials or semantic-quality estimates. The controls do not establish atomic multi-writer admission.'
(HERE/'captions.json').write_text(json.dumps({STEM:caption},indent=2)+'\n')
provenance=dict(status='PASS',renderer_sha256=sha(Path(__file__)),input_sha256=input_hashes,frozen_spec_sha256=verification['frozen_spec_sha256'],runner_sha256=verification['runner_sha256'],native_main_sha256=verification['native_main_sha256'],
 verified_evidence_manifest='mem0_reference/verification.json:raw_sha256',raw_evidence_sha256=verification['raw_sha256'],displayed_configuration=dict(embedder='bge_small',extractor='visible_delta'),
 other_three_configurations_exactly_agree=True,sizes=SIZES,physical_record_values=values,combined_curve=['initial add, all three arms','widened candidates, both retries','sequential exact admission, both retries'],
 figure=dict(aspect_ratio='5:4',inches=[4.5,3.6],dpi=300,pixels=[1350,1080],files={extension:sha(HERE/(STEM+'.'+extension)) for extension in ['png','pdf','svg']}),
 interpretation='Finite specified parameter cases and controlled extraction, not independent live-model trials, incidence, semantic quality, monetary cost or concurrency guarantees.',
 input_files_unchanged=True,spacing_report=STEM+'_spacing.json')
(HERE/(STEM+'_provenance.json')).write_text(json.dumps(provenance,indent=2)+'\n')
print(json.dumps(dict(status='PASS',sizes=SIZES,native_values=values['native_k10'],minimum_spacing_px=min(c['gap_px'] for c in checks)),indent=2))
