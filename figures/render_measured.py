"""Independently verify raw finite results and render measured paper figures.

No participant code or participant metric function is imported. Each plotted
value is recomputed from archived records, SQLite ledgers, and process events.
"""
from __future__ import annotations

from collections import defaultdict
import hashlib
import json
from pathlib import Path
import sqlite3

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "figures"
RESULTS = ROOT / "results"
SPEC = json.loads((RESULTS / "frozen_spec.json").read_text())
POLICIES, HISTORIES, PROFILES = SPEC["policies"], SPEC["histories"], SPEC["profiles"]
INK, GRAY = "#303840", "#67727c"
BLUE, PALE_BLUE = "#49667b", "#abbcc7"
GREEN, CLAY = "#5d786b", "#96765f"

plt.rcParams.update({
    "font.family":"serif", "font.serif":["DejaVu Serif"],
    "font.size":7, "axes.titlesize":7.5, "axes.titleweight":"bold",
    "axes.labelsize":7, "axes.linewidth":.6, "xtick.labelsize":6.2,
    "ytick.labelsize":6.5, "legend.fontsize":6.4,
    "figure.dpi":300, "savefig.dpi":300,
    "pdf.fonttype":42, "ps.fonttype":42,
})


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def table(path, name, order):
    con = sqlite3.connect(path.resolve().as_uri()+"?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in con.execute(f"SELECT * FROM {name} ORDER BY {order}")]
    finally:
        con.close()


def verify(row, state):
    records = table(state/"effects.sqlite", "records", "address")
    actions = table(state/"effects.sqlite", "committed_actions", "serial")
    assert records == row["physical_records"], "Serialized records differ from SQLite"
    assert actions == row["committed_actions"], "Serialized audit differs from SQLite"
    assert all(a["kind"] in {"put","delete"} for a in actions)
    expected = [] if row.get("history", "").startswith("reset_") else SPEC["seed_data"]
    assert set(row["expected_facts"]) == set(expected)
    content = {r["fact"] for r in records} == set(expected)
    cardinality = len(records) == len(set(expected))
    by_intent = defaultdict(list)
    chosen = 0
    for attempt in row["attempts"]:
        ack = attempt["returncode"] == 0 and any(e["event"] == "ack" for e in attempt["events"])
        assert ack == attempt["acknowledged"]
        if attempt["returncode"] == 87:
            assert any(e["event"] == "abrupt_exit" for e in attempt["events"])
        for event in attempt["events"]:
            if event["event"] == "decision_chosen":
                chosen += 1
                digest = hashlib.sha256(json.dumps(event["operations"],sort_keys=True,separators=(",",":")).encode()).hexdigest()
                assert digest == event["digest"]
            if event["event"] in {"decision_chosen","decision_loaded"}:
                by_intent[event["intent"]].append(event["digest"])
    last = row["attempts"][-1]
    ack = last["returncode"] == 0 and any(e["event"] == "ack" for e in last["events"])
    derived = dict(content_correct=content, cardinality_correct=cardinality,
                   acknowledged=ack, selected_terminal=content and cardinality and ack,
                   decision_continuity=all(len(set(d))<=1 for d in by_intent.values()),
                   planning_invocations=chosen, committed_effect_calls=len(actions))
    for name,value in derived.items():
        assert row[name] == value, f"{name}: serialized metric differs from recomputation"
    derived["process_attempts"] = len(row["attempts"])
    derived["abrupt_exits"] = sum(a["returncode"] == 87 for a in row["attempts"])
    return derived


raw = [json.loads(line) for line in (RESULTS/"cases.jsonl").read_text().splitlines() if line]
keys = [(r["policy"],r["profile"],r["history"]) for r in raw]
wanted = {(p,o,h) for p in POLICIES for o in PROFILES for h in HISTORIES
          if h != "lost_delete_reply" or o in {"retire","mixed"}}
assert len(keys) == len(set(keys)) and set(keys) == wanted
assert len(raw) == SPEC["structural_cases"]
assert sha(ROOT/"study.py") == SPEC["source_sha256"], "Study source differs from frozen hash"
checked = []
for row in raw:
    name = f"{row['policy']}__{row['profile']}__{row['history']}"
    checked.append(dict(policy=row["policy"],history=row["history"],profile=row["profile"],
                        **verify(row,RESULTS/"state"/name)))

totals=[]
for policy in POLICIES:
    group=[r for r in checked if r["policy"]==policy]
    totals.append(dict(policy=policy,structural_cases=len(group),
      content_pass=sum(r["content_correct"] for r in group),
      cardinality_pass=sum(r["cardinality_correct"] for r in group),
      selected_terminal_pass=sum(r["selected_terminal"] for r in group),
      decision_continuity_pass=sum(r["decision_continuity"] for r in group),
      acknowledged=sum(r["acknowledged"] for r in group),
      planning_invocations=sum(r["planning_invocations"] for r in group),
      committed_effect_calls=sum(r["committed_effect_calls"] for r in group),
      process_attempts=sum(r["process_attempts"] for r in group),
      abrupt_exits=sum(r["abrupt_exits"] for r in group)))
assert totals == json.loads((RESULTS/"summary.json").read_text()), "Summary aggregate differs"

boundary = json.loads((RESULTS/"boundary_probes.json").read_text())
boundary_checked=[]
for row in boundary:
    observation=dict(probe=row["probe"],**verify(row,RESULTS/"boundary_state"/row["probe"]))
    if row["probe"]=="external_interleaving":
        preserved=any(r["fact"]=="unit=newer-external-value" for r in row["physical_records"])
        assert preserved == row["newer_external_write_preserved"]
        observation["newer_external_write_preserved"]=preserved
    boundary_checked.append(observation)


def save(fig, stem):
    for ext in ("png","pdf","svg"):
        fig.savefig(OUT/f"{stem}.{ext}",dpi=300,facecolor="white")
    plt.close(fig)


def clean(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(length=2.4,width=.6)
    ax.grid(axis="y",color="#d7dcdf",linewidth=.5,alpha=.6)
    ax.set_axisbelow(True)


def count_labels(ax, bars):
    for b in bars:
        ax.annotate(str(int(b.get_height())),(b.get_x()+b.get_width()/2,b.get_height()),
                    xytext=(0,2),textcoords="offset points",ha="center",va="bottom",fontsize=6.3,color=INK)


# One figure, two count panels with distinct and explicitly named axes.
fig,axes=plt.subplots(2,1,figsize=(5.6,4.2),sharex=True)
fig.subplots_adjust(left=.11,right=.985,bottom=.16,top=.83,hspace=.43)
x=np.arange(len(POLICIES)); width=.32
for ax in axes:
    clean(ax)
    ax.axvspan(5.5,7.5,color="#edf1ee",zorder=-2)
    ax.set_xlim(-.6,7.6)
ax=axes[0]
a=ax.bar(x-width/2,[r["content_pass"] for r in totals],width,color=PALE_BLUE,label="Content oracle")
b=ax.bar(x+width/2,[r["selected_terminal_pass"] for r in totals],width,color=BLUE,label="Selected terminal")
count_labels(ax,a);count_labels(ax,b)
ax.set_ylim(0,88);ax.set_yticks([0,22,44,66]);ax.set_ylabel("Passing runs (of 66)")
ax.set_title("(a) Content and selected terminal contract",loc="left",pad=5)
ax.legend(frameon=False,ncol=2,loc="upper left",bbox_to_anchor=(0,1.04))
ax=axes[1]
a=ax.bar(x-width/2,[r["planning_invocations"] for r in totals],width,color=GREEN,label="Scripted planning invocations")
b=ax.bar(x+width/2,[r["committed_effect_calls"] for r in totals],width,color=CLAY,label="Committed put/delete calls")
count_labels(ax,a);count_labels(ax,b)
ax.set_ylim(0,390);ax.set_yticks([0,100,200,300]);ax.set_ylabel("Invocation / commit count")
ax.set_title("(b) Planning and committed mutation work",loc="left",pad=5)
ax.legend(frameon=False,ncol=2,loc="upper left",bbox_to_anchor=(0,1.04),fontsize=5.8)
ax.set_xticks(x,POLICIES,fontsize=6.1);ax.set_xlabel("Policy: D = stable addresses; P = retained plan; R = receipt",fontsize=6.4,labelpad=6)
fig.text(.02,.976,"State correctness and execution history are separate observations",fontsize=8.3,fontweight="bold",color=INK,va="top")
fig.text(.02,.927,"Shaded pair: D1P1 has 66/66 terminal passes with either R; put/delete commits differ.",fontsize=6.1,color=GRAY,va="top")
fig.text(.02,.065,"528 specified structural runs; 66 per policy. Counts are not independent statistical samples.",fontsize=6.0,color=GRAY)
fig.text(.02,.025,"Committed calls include participant put/delete only; reset and cleanup mutations are excluded.",fontsize=5.9,color=GRAY)
save(fig,"fig_factorial_oracles")

labels={
 "normal":"No fault",
 "redelivery_fixed":"Redelivery: fixed tape",
 "redelivery_drift":"Redelivery: changed tape",
 "exit_after_prepare_fixed":"Exit after prepare: fixed",
 "exit_after_prepare_drift":"Exit after prepare: changed",
 "exit_after_first_put_fixed":"Exit after first put: fixed",
 "exit_after_first_put_drift":"Exit after first put: changed",
 "lost_put_reply_fixed":"Lost put reply: fixed",
 "lost_put_reply_drift":"Lost put reply: changed",
 "exit_after_effects_fixed":"Exit after all effects: fixed",
 "exit_after_effects_drift":"Exit after all effects: changed",
 "exit_after_finalize_drift":"Exit after finalize: changed",
 "bounded_input":"Bounded-input control",
 "superseded_input":"Disabled-source control",
 "reset_before_retry":"Reset before retry",
 "reset_during_effects":"Reset between effects",
 "lost_delete_reply":"Lost delete reply",
}
cell={}
for h in HISTORIES:
    for p in POLICIES:
        group=[r for r in checked if r["policy"]==p and r["history"]==h]
        cell[p,h]=(sum(r["selected_terminal"] for r in group),len(group))
values=np.array([[cell[p,h][0]/cell[p,h][1] for p in POLICIES] for h in HISTORIES])
fig,ax=plt.subplots(figsize=(5.6,4.2))
fig.subplots_adjust(left=.405,right=.98,bottom=.18,top=.86)
ax.imshow(values,vmin=0,vmax=1,aspect="auto",interpolation="nearest",
          cmap=LinearSegmentedColormap.from_list("terminal_fraction",["#f2f3f4",BLUE]))
ax.set_xticks(range(8),POLICIES,fontsize=6.0)
ax.set_yticks(range(17),[labels[h] for h in HISTORIES],fontsize=6.4)
ax.tick_params(which="both",length=0,pad=3)
ax.set_xlabel("D = stable addresses; P = retained plan; R = receipt",fontsize=6.0,labelpad=8)
ax.set_ylabel("Specified execution history",fontsize=6.8,labelpad=6)
ax.set_xticks(np.arange(-.5,8,1),minor=True);ax.set_yticks(np.arange(-.5,17,1),minor=True)
ax.grid(which="minor",color="white",linewidth=.55)
for i,h in enumerate(HISTORIES):
    for j,p in enumerate(POLICIES):
        passed,n=cell[p,h]
        ax.text(j,i,f"{passed}/{n}",ha="center",va="center",fontsize=6.5,
                color="white" if values[i,j]>=.6 else INK)
for spine in ax.spines.values():spine.set_visible(False)
fig.text(.02,.975,"Selected terminal contract by history and policy",fontsize=8.6,fontweight="bold",color=INK,va="top")
fig.text(.02,.93,"Cells: passing runs / applicable operation profiles; shading: fraction passing",fontsize=6.5,color=GRAY,va="top")
fig.text(.02,.075,"Terminal = exact expected fact set + expected physical cardinality + final acknowledgement.",fontsize=6.0,color=GRAY)
fig.text(.02,.032,"17 specified histories × 4 profiles, with two inapplicable delete cells omitted per policy.",fontsize=6.0,color=GRAY)
save(fig,"fig_history_matrix")

captions=json.loads((OUT/"captions.json").read_text())
captions.update({
 "fig_factorial_oracles": "Content, selected terminal conformance, and execution-work counts for the eight factorial policies. Each policy has 66 specified structural runs. The content oracle checks exact fact-set equality; selected terminal conformance also requires expected physical cardinality and final acknowledgement. The lower panel separately counts scripted planning invocations and committed participant put/delete calls, excluding reset and cleanup mutations. The shaded D1P1 pair passes all 66 terminal checks with either receipt setting while making 317 calls under R0 and 275 under R1. These are finite controlled counts, not population estimates, latency, monetary cost, retrieval recall, or live-model accuracy.",
 "fig_history_matrix": "Selected terminal conformance by specified history and D/P/R policy. Each cell reports passing structural runs over applicable operation profiles; shading represents that fraction. All histories have four profiles except lost-delete-reply, which has two. Stable addresses, retained decisions, and receipts change different history outcomes. The shared bounded-input, disabled-source, and generation-reset frontend is present in every policy. Changed-tape histories explicitly prescribe a different later decision; their counts do not estimate natural model drift. The matrix covers 528 unique structural runs and does not establish behavior under every process, concurrency, or storage failure."
})
(OUT/"captions.json").write_text(json.dumps(captions,indent=2)+"\n")
provenance=dict(
 status="PASS",case_count=len(checked),unique_structural_keys=len(set(keys)),
 source_sha256=SPEC["source_sha256"],
 raw_inputs={p.name:sha(p) for p in [RESULTS/"cases.jsonl",RESULTS/"summary.json",RESULTS/"frozen_spec.json",RESULTS/"boundary_probes.json"]},
 verification="Recomputed from read-only physical/audit SQLite tables and raw process events without importing participant metric code; exact summary agreement.",
 policy_totals=totals,boundary_observations=boundary_checked,
 process_attempts=sum(r["process_attempts"] for r in totals),
 abrupt_exits=sum(r["abrupt_exits"] for r in totals),
 figure_cells=[dict(policy=p,history=h,passing=cell[p,h][0],applicable=cell[p,h][1]) for h in HISTORIES for p in POLICIES],
 interpretation="Finite specified structural runs, no repeated renamings, no confidence intervals or significance tests. Commit metric excludes cleanup and reset.",
 figure_hashes={p.name:sha(p) for stem in ["fig_factorial_oracles","fig_history_matrix"] for ext in ["png","pdf","svg"] for p in [OUT/f"{stem}.{ext}"]},
)
(OUT/"measurement_provenance.json").write_text(json.dumps(provenance,indent=2)+"\n")
print(json.dumps({k:provenance[k] for k in ["status","case_count","process_attempts","abrupt_exits"]},indent=2))
