"""Render a frozen design, not a performance plot or a completion report."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

HERE = Path(__file__).resolve().parent
IMPACT = HERE.parents[1]
ROOT = IMPACT.parents[1]
PILOT = IMPACT / "development_pilot_v2"
NAME = "fig_frozen_development_pilot_design"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def derive():
    protocol = json.loads((PILOT / "protocol.json").read_text())
    spec = json.loads((HERE / "figure_spec.json").read_text())
    digest = sha(PILOT / "protocol.json")
    assert digest == (PILOT / "protocol.sha256").read_text().strip() == spec["protocol_sha256"]
    for rel, h in protocol["source_hashes"].items():
        assert sha(ROOT / rel) == h, rel
    analysis = json.loads((IMPACT / "analysis_plan.json").read_text())
    grade_protocol = json.loads((PILOT / "grading_protocol.json").read_text())
    assert sha(PILOT / "grading_protocol.json") == (PILOT / "grading_protocol.sha256").read_text().strip()
    fixtures = json.loads((PILOT / "grading_calibration.json").read_text())
    assert sha(PILOT / "grading_calibration.json") == grade_protocol["calibration_sha256"]
    decisions = json.loads((PILOT / "grading_results/calibration/parsed.json").read_text())["decisions"]
    by_id = {r["id"]: r for r in decisions}
    assert len(by_id) == len(decisions) == len(fixtures) == 12
    assert set(by_id) == {f["id"] for f in fixtures}
    task_matches = sum(by_id[f["id"]]["task_correct"] == f["expected_task_correct"] for f in fixtures)
    conflict_mismatches = [f["id"] for f in fixtures if by_id[f["id"]]["current_conflict"] != f["expected_current_conflict"]]
    report = json.loads((PILOT / "grading_calibration_report.json").read_text())
    assert task_matches == 12 and len(conflict_mismatches) == 2
    assert report["status"] == "CALIBRATION_MISMATCH"
    assert {(r["id"], r["label"]) for r in report["mismatches"]} == {(i,"current_conflict") for i in conflict_mismatches}
    scopes = protocol["participants"]
    backends = len(protocol["backends"])
    modes = len(protocol["storage_modes"])
    assert scopes == 14 and protocol["questions"] == 24 and backends == 2 and modes == 3
    assert len(protocol["reader_arms"]) == 7
    assert protocol["retrieval"] == {"common_candidate_limit":60,"context_record_limit":10,"context_utf8_byte_budget":12000,"token_budget_claim":False,"read_dedup":"Collapse native retry candidate pool by logical event ID, not literal text; all arms use the same candidate limit."}
    split = json.loads((PILOT / "split.json").read_text())
    assert len(split["locomo_development_conversations"]) == 2
    assert len(split["lme_development_evidence_components"]) == 12
    assert len(split["development_question_keys"]) == protocol["questions"]
    values = {"questions":protocol["questions"],"source_history_scopes":scopes,
      "locomo_conversations":2,"lme_evidence_components":12,"native_backends":backends,
      "storage_modes":modes,"reader_arms":len(protocol["reader_arms"]),
      "expected_native_process_phases":scopes*backends*(2+3*modes),
      "scheduled_exit87_phases":scopes*backends*modes,
      "candidate_limit":60,"context_record_limit":10,"serialized_context_byte_limit":12000,
      "calibration_fixtures":len(fixtures),"calibration_task_label_matches":task_matches,
      "calibration_current_conflict_mismatches":len(conflict_mismatches),
      "benchmark_task_performance_rows_consumed":0,
      "interpretation":"Design inventory and authored grading calibration only; no run-completion or benchmark-performance observation."}
    assert values["expected_native_process_phases"] == 308 and values["scheduled_exit87_phases"] == 84
    (HERE / "design_values.json").write_text(json.dumps(values,indent=2)+"\n")
    inputs = [PILOT / f for f in ["protocol.json","protocol.sha256","grading_protocol.json","grading_protocol.sha256","grading_calibration.json","grading_results/calibration/parsed.json","grading_calibration_report.json","split.json"]]
    inputs += [IMPACT / f for f in ["analysis_plan.json","pipeline.py","memory_worker.py","reader.py"]]
    return values, {str(p.relative_to(ROOT)):sha(p) for p in inputs}


def main():
    values, inputs = derive()
    plt.rcParams.update({"font.family":"serif","font.serif":["DejaVu Serif"],
        "font.size":7.0,"figure.dpi":300,"savefig.dpi":300,
        "svg.fonttype":"none","pdf.fonttype":42})
    fig=plt.figure(figsize=(7,3),dpi=300,facecolor="white")
    ax=fig.add_axes([0,0,1,1]);ax.set_xlim(0,1);ax.set_ylim(0,1);ax.axis("off")
    ink="#303942";border="#627481";blue="#e9eff3";gray="#f3f4f5";green="#edf2ee";gold="#947b61"
    texts={};bounds={}
    def text(name,x,y,value,**kw):
        kw.setdefault("color",ink)
        a=ax.text(x,y,value,transform=ax.transAxes,**kw);texts[name]=a;return a
    def box(name,x,y,w,h,title,body,fill=blue):
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.003,rounding_size=0.008",
          facecolor=fill,edgecolor=border,lw=.85,transform=ax.transAxes))
        bounds[name]=(x,y,w,h)
        text(name+"_title",x+w/2,y+h-.026,title,fontsize=7.4,fontweight="bold",ha="center",va="top",linespacing=1.1)
        text(name+"_body",x+w/2,y+.026,body,fontsize=6.9,ha="center",va="bottom",linespacing=1.17)
    def arrow(x1,y1,x2,y2,*,dashed=False,color=border):
        ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle="-|>",mutation_scale=8,lw=.9,
          color=color,linestyle=(0,(3,2)) if dashed else "solid",transform=ax.transAxes,shrinkA=0,shrinkB=0))
    text("title",.018,.965,"Frozen development pilot: public-history recovery and readers",fontsize=11.2,fontweight="bold",ha="left",va="top")
    text("status",.018,.897,"24 questions / 14 scopes / 2 local backends / 7 reader arms; not held-out confirmation",fontsize=7.1,ha="left",va="top")
    # Public source identities are ordinary participant metadata, not evaluation labels.
    nodes=[
      ("input",.018,.405,.150,.340,"History-only\ninput","14 source scopes\n2 LoCoMo conv.\n12 LME components\nno gold or query",gray),
      ("native",.195,.405,.196,.340,"Native provision\nand cloning","Mem0 infer=False\nLlamaIndex persisted\nreal local BGE\nclosed baseline cloned",blue),
      ("delivery",.418,.405,.206,.340,"Retry + admission\nvariants","native / event / text\npost-effect exit87\nbefore ack, then retry\nsame event IDs + times",blue),
      ("context",.651,.405,.174,.340,"Fixed context\n+ readers","60 candidates\nat most 10 records\nat most 12,000 bytes\nSol x2; Qwen x1",blue),
      ("judge",.852,.405,.130,.340,"Blinded\njudge","automated\narm IDs hidden\nprovisional\nnot human-rated",green),
    ]
    for n,x,y,w,h,t,b,f in nodes:box(n,x,y,w,h,t,b,f)
    for a,b in zip(nodes,nodes[1:]):arrow(a[1]+a[3]+.004,.563,b[1]-.004,.563)
    text("question",.705,.837,"Question / date\nquery time only",fontsize=6.7,ha="center",va="top",linespacing=1.1)
    arrow(.705,.775,.705,.749)
    text("labels",.908,.837,"Gold labels; support\nfor oracle diagnostic only",fontsize=6.7,ha="center",va="top",linespacing=1.1)
    arrow(.917,.775,.917,.749,dashed=True,color=gold)
    # The oracle-support diagnostic deliberately bypasses normal retrieval.
    arrow(.864,.766,.815,.749,dashed=True,color=gold)
    box("state",.018,.155,.430,.210,"Separate state / context checks",
        "records; source-event coverage;\nduplicate event slots; serialized bytes",gray)
    box("comparison",.478,.155,.504,.210,"Paired task comparisons: seven arms",
        "clean; retry; event guard; text guard; read-event dedup;\nno-context; oracle-support (diagnostic only).\nClean Sol repeat disagreement is a separate control.",green)
    # Native-state and retrieved-context observations join outside the text boxes.
    ax.plot([.521,.521],[.401,.385],color=border,lw=.9,transform=ax.transAxes)
    ax.plot([.738,.738],[.401,.385],color=border,lw=.9,transform=ax.transAxes)
    ax.plot([.738,.233],[.385,.385],color=border,lw=.9,transform=ax.transAxes)
    arrow(.233,.385,.233,.369)
    arrow(.917,.401,.917,.369)
    text("inventory",.018,.100,
        "Design inventory: 308 native process phases, including 84 scheduled post-effect / pre-ack exits; no completion claim.",
        fontsize=6.7,ha="left",va="top")
    text("calibration",.018,.054,
        "Authored grader calibration: 12/12 task labels agree; 2 current-conflict mismatches retained. Task outcomes remain provisional.",
        fontsize=6.7,ha="left",va="top")
    fig.canvas.draw();renderer=fig.canvas.get_renderer()
    boxes={n:t.get_window_extent(renderer) for n,t in texts.items()}
    overlap=[];names=list(boxes)
    for i,n in enumerate(names):
        for other in names[i+1:]:
            if boxes[n].overlaps(boxes[other]):overlap.append([n,other])
    checks=[]
    for n,(x,y,w,h) in bounds.items():
        p=ax.transAxes.transform([[x,y],[x+w,y+h]])
        for part in ['title','body']:
            b=boxes[n+'_'+part];m=min(b.x0-p[0,0],b.y0-p[0,1],p[1,0]-b.x1,p[1,1]-b.y1)
            checks.append({'text':n+'_'+part,'minimum_margin_px':round(float(m),3),'passed':bool(m>=6-1e-6)})
    outside=[n for n,b in boxes.items() if b.x0<0 or b.y0<0 or b.x1>2100 or b.y1>900]
    spacing={'status':'PASS' if not overlap and not outside and all(r['passed'] for r in checks) else 'FAIL',
      'canvas_px':[2100,900],'text_pair_checks':len(names)*(len(names)-1)//2,'text_overlaps':overlap,
      'inside_box_checks':checks,'required_box_margin_px':6,'outside_canvas':outside,
      'text_bboxes':{n:[round(float(v),3) for v in b.extents] for n,b in boxes.items()},
      'scope':'Mechanical text clearance and canvas bounds; inspect actual pixels for arrow routing and semantics.'}
    (HERE/(NAME+'_spacing.json')).write_text(json.dumps(spacing,indent=2)+'\n')
    for ext in ['png','pdf','svg']:
        meta={'CreationDate':None,'ModDate':None} if ext=='pdf' else ({'Date':None} if ext=='svg' else None)
        fig.savefig(HERE/(NAME+'.'+ext),dpi=300,bbox_inches=None,pad_inches=0,metadata=meta)
    plt.close(fig)
    # All prior planned artifacts are immutable during this separate rendering.
    protected=json.loads((HERE/'planned_preservation.json').read_text())['files']
    assert all(sha(HERE.parent/rel)==h for rel,h in protected.items())
    provenance={'status':'FROZEN_DEVELOPMENT_DESIGN_NOT_CONFIRMATION','protocol_sha256':sha(PILOT/'protocol.json'),
      'inputs':inputs,'renderer_sha256':sha(Path(__file__)),'spec_sha256':sha(HERE/'figure_spec.json'),
      'outputs':{ext:sha(HERE/(NAME+'.'+ext)) for ext in ['png','pdf','svg']},
      'design_values_sha256':sha(HERE/'design_values.json'),'previous_planned_files_preserved':True,
      'benchmark_task_performance_rows_consumed':0,'structural_results_not_yet_plotted':True,
      'grading_calibration_observation':'Authored fixtures only; 12 task-label matches, two auxiliary current-conflict mismatches. No semantic outcome validation or human review asserted.',
      'scope':'Actual frozen design only. Expected phase/cut inventory does not assert completed runs.'}
    (HERE/(NAME+'_provenance.json')).write_text(json.dumps(provenance,indent=2)+'\n')
    print(json.dumps({'status':spacing['status'],'overlaps':overlap,'box_failures':[r for r in checks if not r['passed']],'outside':outside}))


if __name__=='__main__':main()
