"""Render the independent factorial experiment's public algorithmic design.

This figure consumes no result data. It depicts only the declared independent
experiment: three policy switches, two SQLite files, and subprocess fault phases.
"""
from pathlib import Path
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = Path(__file__).resolve().parent
INK, MUTED = "#303840", "#67727c"
BLUE, BLUE_PALE = "#49667b", "#e8eef2"
GREEN, GREEN_PALE = "#5d786b", "#edf1ee"
GRAY_PALE = "#f3f4f5"
plt.rcParams.update({
    "font.family": "serif", "font.serif": ["DejaVu Serif"],
    "font.size": 7, "figure.dpi": 300, "savefig.dpi": 300,
    "pdf.fonttype": 42, "ps.fonttype": 42,
})
fig, ax = plt.subplots(figsize=(5.6, 3.15))
fig.subplots_adjust(left=.012, right=.988, top=.985, bottom=.02)
ax.set(xlim=(0, 16), ylim=(0, 9))
ax.axis("off")


def box(x, y, width, height, title, detail, *, controlled=False, color=BLUE, fill=BLUE_PALE):
    ax.add_patch(FancyBboxPatch(
        (x, y), width, height, boxstyle="round,pad=.035,rounding_size=.07",
        linewidth=.8, edgecolor=MUTED if controlled else color,
        facecolor=GRAY_PALE if controlled else fill,
        linestyle=(0, (3, 2)) if controlled else "solid",
    ))
    ax.text(x+width/2, y+height*.74, title, ha="center", va="center",
            fontsize=6.2, fontweight="bold", color=INK)
    ax.text(x+width/2, y+height*.32, detail, ha="center", va="center",
            fontsize=5.9, color=MUTED, linespacing=1.2)


def arrow(start, end, *, controlled=False, color=BLUE, both=False, rad=0):
    ax.add_patch(FancyArrowPatch(
        start, end, arrowstyle="<->" if both else "-|>", mutation_scale=6.5,
        linewidth=.75, color=MUTED if controlled else color,
        linestyle=(0, (2, 2)) if controlled else "solid",
        connectionstyle=f"arc3,rad={rad}",
    ))


ax.text(.15, 8.67, "Factorial memory recovery with real process failures",
        fontsize=8.7, fontweight="bold", color=INK, va="top")
box(.15, 6.99, 2.75, 1.03, "Synthetic histories", "conversation +\ndelivery / faults", controlled=True)
box(6.65, 6.99, 3.12, 1.03, "Scripted decisions", "operation choices", controlled=True)

# The frame identifies a process boundary, not an atomic transaction.
ax.add_patch(FancyBboxPatch(
    (3.23, 3.88), 12.50, 2.85,
    boxstyle="round,pad=.04,rounding_size=.10", linewidth=.8,
    edgecolor=BLUE, facecolor="white",
))
ax.text(3.47, 6.48, "Fresh subprocess", fontsize=6.5,
        color=BLUE, fontweight="bold", va="center")
ax.text(15.48, 6.48, "same frontend in all 8 D/P/R variants", fontsize=5.8,
        color=BLUE, ha="right", va="center")

box(3.46, 4.75, 2.55, 1.20, "Entry checks", "generation check\nR1: receipt lookup")
box(6.65, 4.75, 3.12, 1.20, "Load / choose plan", "P1: plan + targets\nelse query + choose")
box(10.36, 4.75, 2.22, 1.20, "Apply effects", "D1: stable\neffect addresses")
box(13.16, 4.75, 2.32, 1.20, "Finalize", "R1: store receipt\nretain P1 plan")
for left, right in [(6.01, 6.65), (9.77, 10.36), (12.58, 13.16)]:
    arrow((left+.04, 5.35), (right-.04, 5.35))
arrow((8.21, 6.94), (8.21, 6.01), controlled=True)
box(.15, 4.18, 2.75, 2.17, "Parent harness",
    "start / retry\nphase exits + reset\nhandshake", fill=BLUE_PALE)
arrow((1.52, 6.73), (1.52, 6.41), controlled=True)
arrow((2.96, 5.35), (3.40, 5.35))

box(3.46, 1.95, 6.31, 1.30, "Coordinator SQLite file",
    "conversation fixture + generation\nP1 plans stay after success; R1 receipts")
box(10.36, 1.95, 5.12, 1.30, "Effect-store SQLite file",
    "memory records + commit audit\nparticipant never reads the audit")
arrow((4.73, 4.68), (4.73, 3.31), both=True)
arrow((8.21, 4.68), (8.21, 3.31), both=True)
arrow((11.47, 4.68), (11.47, 3.31), both=True)
ax.text(6.36, 3.53, "same generation frontend", fontsize=5.6,
        color=MUTED, ha="center", va="center")

# Generation changes are committed to the actual coordinator file by the parent.
arrow((2.94, 4.30), (3.40, 2.71), color=GREEN)
ax.text(.15, 3.58, "Reset generation\nbetween effects", fontsize=5.4,
        color=GREEN, ha="left", va="center", linespacing=1.25)

box(.15, 1.95, 2.75, 1.30, "External evaluator", "terminal state\n+ commit audit", color=GREEN, fill=GREEN_PALE)
arrow((3.40, 2.60), (2.96, 2.60), color=GREEN)
arrow((12.92, 1.89), (1.52, 1.89), color=GREEN, rad=-.06)

ax.text(.15, 1.09,
        "Exit phases: after prepare / first put / all effects / finalize",
        fontsize=6.4, color=INK, va="center")
ax.text(.15, .65,
        "Abrupt os._exit and committed-effect exceptions; separate storage commit boundaries",
        fontsize=5.9, color=MUTED, va="center")
legend = [
    Line2D([0], [0], color=BLUE, linewidth=1,
           label="executed algorithm, storage or process control"),
    Line2D([0], [0], color=MUTED, linestyle=(0, (3, 2)), linewidth=1,
           label="controlled synthetic input or decision source"),
]
ax.legend(handles=legend, loc="lower left", bbox_to_anchor=(-.006, -.025),
          ncol=2, frameon=False, handlelength=1.6, columnspacing=1.0,
          fontsize=5.4)

for ext in ("png", "pdf", "svg"):
    fig.savefig(OUT/f"fig_experiment_architecture.{ext}", dpi=300, facecolor="white")
plt.close(fig)

caption = (
    "Independent experiment architecture. A controlled conversation/failure history "
    "and decision tape feed a common frontend across all eight combinations of "
    "stable effect addresses (D), retained chosen plans with target bindings (P), "
    "and completion receipts (R). Every attempt runs in a fresh Python subprocess. "
    "Generation checks precede the receipt fast path; receipt and retained-plan "
    "hits bypass the shared source query. The coordinator and effect store use "
    "separate SQLite files; the participant "
    "does not read the effect-store commit audit. The parent harness schedules "
    "abrupt process exits, committed-effect exceptions, and a real generation "
    "reset between effects through a handshake. P1 retains its chosen plan after "
    "success with either R setting. Dashed boxes identify controlled inputs, while "
    "solid boxes identify executed algorithms, storage, and process control. "
    "The process frame does not imply an atomic cross-store transaction."
)
caption_file = OUT/"captions.json"
captions = json.loads(caption_file.read_text()) if caption_file.exists() else {}
captions["fig_experiment_architecture"] = caption
caption_file.write_text(json.dumps(captions,indent=2)+"\n")
