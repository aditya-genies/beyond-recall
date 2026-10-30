# Proposed benchmark-impact figures

This directory contains a **planned** experimental-design diagram and proposed
data interfaces. It contains no benchmark performance measurements. The diagram
must be reconciled with the actual frozen implementation before being described
as an executed pipeline or included as an experimental methods figure.

Inputs are `../RESEARCH_DESIGN.md` and `../feasibility.json`; their exact hashes
are recorded by the renderer. The current source-access feasibility assessment
does not establish reader performance, an installed second backend, novelty,
statistical power or a successful intervention.

Run the local Matplotlib renderer with Python to produce the PNG, PDF and SVG.
It deliberately consumes no result file. The 21:9 canvas is 2100 by 900 pixels
at 300 DPI. The spacing report checks text containment/non-overlap; final visual
inspection remains necessary for arrows, readability and methodological meaning.

## Data contracts awaiting a frozen implementation

`observations.schema.json` describes proposed source observations.
`paired_plot_data.schema.json` describes proposed derivations for later plots.
Neither is the frozen experiment specification. No example numeric row is
included. Metric ranges describe proposed domains rather than measured values.

- Historical ingestion receives permitted conversation text, dates and ordinary
  source identity. Questions enter at query time. Answers, gold evidence labels,
  question categories and evaluator IDs remain outside historical ingestion.
- Physical state invariance is a separate check from task correctness. A reader
  may vary across clean repeats. Literal answer equality is not the QA oracle.
- A task delta is candidate correctness minus reference correctness for the
  declared pairing. Retain clean-repeat contrasts to characterize the stochastic
  reader; do not imply that pairing forces identical random draws.
- Duplicate visible slots equal returned slots minus distinct exact visible
  strings. This is a literal-count metric, not semantic redundancy. Unused
  budget is not duplication. Track source-event coverage separately.
- Do not interpret the number of reader calls or question pairs as independent
  episodes. Freeze the true cluster definition and paired uncertainty analysis
  after the development pilot, before the confirmatory run.
- Report gains, losses and unchanged outcomes. A non-significant difference is
  not equivalence. Effect/equivalence bounds are not assigned in this figure
  plan; they must be justified and frozen with the analysis protocol.
- Genuine new identical observations, corroboration, corrections, expiry and
  renewed authorization require their own controls. A text-hash filter does not
  receive credit merely for rejecting all repeated words.

`plot_plan.json` lists unrendered empirical figure proposals. Generate no
performance plots until the actual frozen raw results, provenance and separate
checker report are supplied. The released paper and all earlier study data and
figures are untouched.
