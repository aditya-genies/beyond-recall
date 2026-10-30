"""Independently derive and plot structural context pairs, never reader grades."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch, Rectangle

HERE=Path(__file__).resolve().parent
IMPACT=HERE.parents[1]
ROOT=IMPACT.parents[1]
PILOT=IMPACT/'development_pilot_v2'
NAME='fig_pilot_context_structure'
EXPECTED_PROTOCOL='dd5280476348b1b60ec9bd91626b6b909b8ae4697233f1a6f8a0a8631035d9ea'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')


def derive():
    protocol=json.loads((PILOT/'protocol.json').read_text())
    reader=json.loads((PILOT/'reader_protocol.json').read_text())
    audit=json.loads((IMPACT/'worker_review_pilot_v2.json').read_text())
    assert sha(PILOT/'protocol.json')==EXPECTED_PROTOCOL==(PILOT/'protocol.sha256').read_text().strip()
    assert sha(PILOT/'reader_protocol.json')==(PILOT/'reader_protocol.sha256').read_text().strip()
    assert sha(PILOT/'contexts.json')==reader['contexts_sha256']
    assert sha(PILOT/'evaluator_questions.json')==protocol['evaluator_sha256']
    assert audit['status']=='PASS' and audit['protocol_sha256']==EXPECTED_PROTOCOL
    assert audit['execution_manifests']==308 and audit['actual_expected_exit87']==84
    assert sha(IMPACT/'worker_review_pilot_audit.py')==audit['auditor_sha256']
    questions=json.loads((PILOT/'evaluator_questions.json').read_text())
    qmap={q['key']:q for q in questions}
    contexts=json.loads((PILOT/'contexts.json').read_text())
    assert len(qmap)==len(questions)==24 and len(contexts)==336==reader['condition_cells']
    expected={(q,b,a) for q in qmap for b in protocol['backends'] for a in protocol['reader_arms']}
    indexed={};all_recomputed=[]
    for row in contexts:
        key=(row['question_key'],row['backend'],row['arm'])
        assert key not in indexed and key in expected
        q=qmap[row['question_key']]
        assert row['question']==q['question'] and row['question_date']==q['question_date']
        context=row['context']
        assert len(context)<=protocol['retrieval']['context_record_limit']
        assert all(set(r)=={'event_id','source_id','date','text'} for r in context)
        serialized_bytes=len(json.dumps(context,ensure_ascii=True,separators=(',',':')).encode('utf-8'))
        assert serialized_bytes<=protocol['retrieval']['context_utf8_byte_budget']
        visible={r['event_id'] for r in context};gold=set(q['expected_events'])
        unavailable=q['unanswerable'] or q['missing_gold_locations'] or not gold
        support=None if unavailable else len(visible & gold)/len(gold)
        metrics={'context_records':len(context),'distinct_event_ids':len(visible),
            'distinct_exact_strings':len({r['text'] for r in context}),
            'duplicate_event_slots':len(context)-len(visible),'positive_support_coverage':support}
        assert set(metrics)==set(row['metrics'])
        for n,v in metrics.items():
            actual=row['metrics'][n]
            if v is None:assert actual is None
            else:assert actual is not None and math.isclose(actual,v,rel_tol=0,abs_tol=1e-12)
        record={'case':row['case'],'question_key':row['question_key'],'backend':row['backend'],
            'arm':row['arm'],'source_scope':q['episode_scope'],'dataset':q['dataset'],
            'metrics':metrics,'serialized_context_bytes':serialized_bytes,
            'annotated_support_available':not unavailable,
            'visible_annotated_support_events':None if unavailable else len(visible & gold),
            'annotated_gold_event_count':None if unavailable else len(gold),
            'support_null_reason':('unanswerable' if q['unanswerable'] else ('missing_gold_locations' if q['missing_gold_locations'] else 'no_gold')) if unavailable else None}
        indexed[key]=record;all_recomputed.append(record)
    assert set(indexed)==expected
    # Source-based ordering is fixed without sorting by an observed effect.
    ordered=sorted(questions,key=lambda q:({'locomo':0,'longmemeval':1}[q['dataset']],q['episode_scope'],q['key']))
    groups=[]
    for q in ordered:
        group=q['episode_scope'] if q['dataset']=='locomo' else 'LME'
        if not groups or groups[-1]['source_group']!=group:
            groups.append({'source_group':group,'dataset':q['dataset'],'start':len([k for g in groups for k in g['keys']]),'keys':[]})
        groups[-1]['keys'].append(q['key'])
    assert [len(g['keys']) for g in groups]==[6,6,12]
    group_labels=['LoCoMo A (6)','LoCoMo B (6)','LongMemEval (12)']
    for g,label in zip(groups,group_labels):g['label']=label;g['end']=g['start']+len(g['keys'])
    pairs=[];summary={}
    for backend in protocol['backends']:
        for number,q in enumerate(ordered,1):
            clean=indexed[(q['key'],backend,'clean')];retry=indexed[(q['key'],backend,'retry')]
            pairs.append({'question_label':f'Q{number:02}','question_key':q['key'],'dataset':q['dataset'],
                'group':q['group'],'source_scope':q['episode_scope'],'backend':backend,
                'clean':clean,'retry':retry,
                'distinct_event_delta':retry['metrics']['distinct_event_ids']-clean['metrics']['distinct_event_ids'],
                'annotated_support_delta':None if clean['metrics']['positive_support_coverage'] is None else retry['metrics']['positive_support_coverage']-clean['metrics']['positive_support_coverage']})
        rows=[p for p in pairs if p['backend']==backend]
        def counts(field):
            vals=[r[field] for r in rows]
            return {'lower':sum(v is not None and v<0 for v in vals),
                'unchanged':sum(v is not None and v==0 for v in vals),
                'higher':sum(v is not None and v>0 for v in vals),
                'unavailable':sum(v is None for v in vals),'total_questions':len(vals)}
        summary[backend]={'distinct_events':counts('distinct_event_delta'),'annotated_support':counts('annotated_support_delta')}
    data={'status':'MEASURED_STRUCTURAL_DEVELOPMENT_PILOT_ONLY','protocol_sha256':EXPECTED_PROTOCOL,
        'question_order_rule':'dataset, source scope, question key; no effect-based ordering',
        'coverage':{'all_context_cells_recomputed':336,'selected_pair_rows':48,'selected_question_state_cells':96,'unique_questions':24,'source_history_scopes':14},
        'groups':groups,'question_map':[{'label':f'Q{n:02}','key':q['key'],'dataset':q['dataset'],'source_scope':q['episode_scope'],'group':q['group']} for n,q in enumerate(ordered,1)],
        'pairs':pairs,'summary':summary,
        'interpretation':'Exact finite context observations, not reader quality, semantic support completeness, significance or an IID population estimate.'}
    write(HERE/(NAME+'_source_data.json'),data)
    write(HERE/(NAME+'_all_context_recomputation.json'),{'rows':all_recomputed,'task_answers_or_grades_consumed':False})
    paths=[PILOT/n for n in ['protocol.json','protocol.sha256','reader_protocol.json','reader_protocol.sha256','contexts.json','evaluator_questions.json']]
    paths+=[IMPACT/'worker_review_pilot_v2.json',IMPACT/'worker_review_pilot_audit.py']
    return data,{str(f.relative_to(ROOT)):sha(f) for f in paths}


def main():
    data,inputs=derive()
    plt.rcParams.update({'font.family':'serif','font.serif':['DejaVu Serif'],
       'font.size':7,'figure.dpi':300,'savefig.dpi':300,'svg.fonttype':'none','pdf.fonttype':42})
    fig=plt.figure(figsize=(7,3),dpi=300,facecolor='white')
    ax=fig.add_axes([.205,.265,.777,.44]);ax.set_xlim(0,24);ax.set_ylim(4,0)
    ax.set_yticks([]);ax.set_xticks([i+.5 for i in range(24)]);ax.set_xticklabels([f'Q{i:02}' for i in range(1,25)],fontsize=5.9)
    ax.tick_params(axis='x',length=0,pad=4)
    for spine in ax.spines.values():spine.set_visible(False)
    ink='#303942';colors={'lower':'#dfc6b2','unchanged':'#e6edf1','higher':'#d7e5d9','unavailable':'#efefef'}
    artists={};segments=[]
    def ftext(name,x,y,value,**kw):
        kw.setdefault('color',ink);a=fig.text(x,y,value,**kw);artists[name]=a;return a
    ftext('title',.018,.965,'Development pilot: clean and retry retrieval contexts',fontsize=11.2,fontweight='bold',ha='left',va='top')
    ftext('subtitle',.018,.897,'Every cell shows clean above retry. Distinct events are counts; annotated support is percent (rounded).',fontsize=6.9,ha='left',va='top')
    legend=fig.legend([Patch(facecolor=colors[k],edgecolor='#9ba7ae',lw=.5,hatch='///' if k=='unavailable' else None) for k in colors],
      ['Lower after retry','Unchanged','Higher after retry','Unavailable support'],
      loc='center left',bbox_to_anchor=(.205,.825),ncol=4,fontsize=6.3,frameon=False,handlelength=1,handletextpad=.4,columnspacing=1.1,borderaxespad=0)
    for group in data['groups']:
        start,end=group['start'],group['end'];x=.205+.777*((start+end)/2/24)
        ftext('group_'+str(start),x,.760,group['label'],fontsize=6.8,ha='center',va='center')
        ax.plot([start+.05,end-.05],[-.16,-.16],color='#8796a0',lw=.6,clip_on=False)
    row_defs=[('mem0_raw','distinct_events'),('mem0_raw','annotated_support'),('llama_index','distinct_events'),('llama_index','annotated_support')]
    for y,(backend,metric) in enumerate(row_defs):
        pairs=[p for p in data['pairs'] if p['backend']==backend]
        summary=data['summary'][backend][metric]
        available=summary['total_questions']-summary['unavailable']
        count_label=f"{summary['lower']}/{available} lower"+(f"; {summary['unavailable']} NA" if summary['unavailable'] else '')
        backend_label='Mem0 raw' if backend=='mem0_raw' else 'LlamaIndex'
        metric_label='Distinct events' if metric=='distinct_events' else 'Annotated support %'
        ftext('row_'+str(y),.190,.265+.44*(1-(y+.5)/4),backend_label+'\n'+metric_label+'\n'+count_label,
          fontsize=6.5,ha='right',va='center',linespacing=1.12)
        for x,pair in enumerate(pairs):
            field='distinct_event_ids' if metric=='distinct_events' else 'positive_support_coverage'
            clean=pair['clean']['metrics'][field];retry=pair['retry']['metrics'][field]
            category='unavailable' if clean is None else ('lower' if retry<clean else ('higher' if retry>clean else 'unchanged'))
            rect=Rectangle((x,y),1,1,facecolor=colors[category],edgecolor='white',lw=.6,hatch='///' if category=='unavailable' else None)
            ax.add_patch(rect)
            for state,value,dy in [('clean',clean,.30),('retry',retry,.72)]:
                label='NA' if value is None else (str(value) if metric=='distinct_events' else str(round(100*value)))
                a=ax.text(x+.5,y+dy,label,ha='center',va='center',fontsize=6.9,color=ink)
                artists[f'cell_{y}_{x}_{state}']=a
                segments.append((a,rect))
    for x in [6,12]:ax.axvline(x,color='#8796a0',lw=1)
    ax.axhline(2,color='#8796a0',lw=1)
    ftext('dependence',.018,.157,'Questions share two LoCoMo conversations or LME evidence components; LME background sessions can overlap.',fontsize=6.6,ha='left',va='top')
    ftext('limits',.018,.105,'Common limits: 60 candidates; 10 records; 12,000 serialized evidence bytes. No reader-accuracy or harm claim.',fontsize=6.6,ha='left',va='top')
    ftext('nulls',.018,.053,'Unavailable support stays NA. Gold annotations may be incomplete. Descriptive paired pilot; no p-values or CI.',fontsize=6.6,ha='left',va='top')
    fig.canvas.draw();renderer=fig.canvas.get_renderer()
    for i,a in enumerate(ax.get_xticklabels()):artists['question_tick_'+str(i)]=a
    for i,a in enumerate(legend.get_texts()):artists['legend_text_'+str(i)]=a
    boxes={n:a.get_window_extent(renderer) for n,a in artists.items()}
    names=list(boxes);overlaps=[]
    for i,n in enumerate(names):
        for m in names[i+1:]:
            if boxes[n].overlaps(boxes[m]):overlaps.append([n,m])
    containment=[]
    for artist,rect in segments:
        a=artist.get_window_extent(renderer);b=rect.get_window_extent(renderer)
        margin=min(a.x0-b.x0,a.y0-b.y0,b.x1-a.x1,b.y1-a.y1)
        containment.append(float(margin))
    legend_box=legend.get_window_extent(renderer)
    group_boxes=[b for n,b in boxes.items() if n.startswith('group_')]
    tick_boxes=[b for n,b in boxes.items() if n.startswith('question_tick_')]
    critical_gaps={
      'subtitle_to_legend_px':float(boxes['subtitle'].y0-legend_box.y1),
      'legend_to_group_labels_px':float(legend_box.y0-max(b.y1 for b in group_boxes)),
      'question_ticks_to_first_footer_px':float(min(b.y0 for b in tick_boxes)-boxes['dependence'].y1)}
    outside=[n for n,b in boxes.items() if b.x0<0 or b.y0<0 or b.x1>2100 or b.y1>900]
    spacing={'status':'PASS' if not overlaps and not outside and min(containment)>=6 and min(critical_gaps.values())>=6 else 'FAIL',
      'canvas_px':[2100,900],'text_pair_checks':len(names)*(len(names)-1)//2,'text_overlaps':overlaps,
      'cell_text_containment_checks':len(containment),'minimum_cell_text_margin_px':round(min(containment),3),
      'required_cell_text_margin_px':6,'outside_canvas':outside,
      'critical_gaps_px':{n:round(v,3) for n,v in critical_gaps.items()},
      'legend_bbox':[round(float(v),3) for v in legend_box.extents],
      'text_bboxes':{n:[round(float(v),3) for v in b.extents] for n,b in boxes.items()},
      'visual_review_required':True}
    write(HERE/(NAME+'_spacing.json'),spacing)
    for ext in ['png','pdf','svg']:
        meta={'CreationDate':None,'ModDate':None} if ext=='pdf' else ({'Date':None} if ext=='svg' else None)
        fig.savefig(HERE/(NAME+'.'+ext),dpi=300,bbox_inches=None,pad_inches=0,metadata=meta)
    plt.close(fig)
    provenance={'status':'MEASURED_STRUCTURAL_DEVELOPMENT_PILOT_ONLY','inputs':inputs,
      'renderer_sha256':sha(Path(__file__)),'source_data_sha256':sha(HERE/(NAME+'_source_data.json')),
      'all_context_recomputation_sha256':sha(HERE/(NAME+'_all_context_recomputation.json')),
      'outputs':{ext:sha(HERE/(NAME+'.'+ext)) for ext in ['png','pdf','svg']},
      'coverage':data['coverage'],'summary':data['summary'],
      'native_store_audit_scope':json.loads((IMPACT/'worker_review_pilot_v2.json').read_text())['interpretation'],
      'additional_verification':'All336 frozen context metric rows reconstructed independently from visible event IDs/text and separately pinned evaluator gold IDs; all48clean/retry pairs and both null support cases preserved.',
      'answer_outcomes_or_grades_read':False,'benchmark_or_source_files_modified':False,
      'inference':'Finite paired structural observations; no answer quality, harm, semantic completeness, independent-sample or population claim.'}
    write(HERE/(NAME+'_provenance.json'),provenance)
    print(json.dumps({'spacing':spacing['status'],'overlaps':overlaps,'outside':outside,'min_cell_margin_px':spacing['minimum_cell_text_margin_px'],'summary':data['summary']}))


if __name__=='__main__':main()
