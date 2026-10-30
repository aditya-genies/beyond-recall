# Frozen development-pilot design figure

This is a separate figure for protocol
`dd5280476348b1b60ec9bd91626b6b909b8ae4697233f1a6f8a0a8631035d9ea`.
It preserves every earlier planned figure file under the parent directory.
The preservation manifest records their pre-existing hashes.

The renderer verifies the native protocol, source hashes, grading-protocol
hash, calibration fixture/decision correspondence and split inventory. It
derives the design values without importing participant or metric functions.
It does not inspect or plot benchmark reader correctness, task deltas, native
structural results, or a winning intervention.

`render_context_structure.py` is a separately scoped empirical structural
figure. It verifies the completed native audit, frozen reader/context hashes,
and all 336 context rows, independently reconstructing metrics without importing
participant metric functions. It selects all 48 clean/retry question/backend
pairs, preserving unchanged pairs and the one null-support question per backend.
No reader answer or grade file is consumed. The complete numerical data and
question/source-group map are saved beside the figure.

The structural figure prints clean values above retry values. Count cells show
distinct logical event IDs; support cells show the fraction of annotated gold
event IDs visible, rounded to whole percent only for display. Coloring uses
the unrounded values. Missing positive-support eligibility remains null/NA,
not zero. These annotations need not exhaust alternative evidence. Full exact
values and support numerators/denominators remain in the source-data JSON.
All questions are ordered by dataset, source scope and key, without using the
observed effect to sort them. No inference treats them as IID samples.

The 308 native phases and 84 scheduled exits are the source-defined inventory:
14 scopes × 2 backends × (2 initial/query phases + 3 modes × 3 phases), and
14 × 2 × 3 respectively. They are not a completion claim or independent
sample count. Structural and task results require a later audited handoff.

The first Sol grader calibration is retained explicitly: all twelve authored
task labels match, while two current-conflict labels mismatch. Calibration
fixtures are not benchmark questions; same-family automated grading is not
independent human validation. No definitive semantic-outcome claim is made.

Run `render_frozen_pilot_design.py` using the research Matplotlib environment.
PNG is 2100×900 at 300 DPI; PDF and SVG are vector companions. The diagram must
still be interpreted with its frozen development scope: raw-document local
participants, sequential authored guards, bounded evidence serialization,
diagnostic oracle support, and provisional automated judgement.
