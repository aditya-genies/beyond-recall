# Recorded-plan integration: operation identity after compaction

This posthoc exploratory experiment uses the already archived Sol6.1 outputs.
It makes no new model requests. Source, controls and input hashes were frozen
after observing those outputs and before running the SQLite integrations.

Twelve original-repeat-0/partial-repeat pairs run through three arms:

- Replan with stable intent/slot addresses.
- The identical replan with fresh insertion addresses.
- Retain the original ordered plan with its original stable addresses.

All arms begin from exactly the archived partial snapshot. A shared bijection
maps the model-visible first-effect ID to its physical stable address. Existing
named targets use the same binding. The fresh-address arm changes only insertion
address behavior relative to the positional-replan arm.

All 36 integrations are retained. Positional replanning causes two cross-key
prefix overwrites; both are responses from the same preferences scenario, the
only scenario whose first operation inserts a new record. The other ten pairs
preserve the prefix. Both controls preserve it in all twelve pairs. This is a
structural address alias, not a semantic error label or population failure rate.
Three focused controls and a separate state/audit checker pass.

Check the archived evidence:

    python3 -W error::ResourceWarning -m unittest discover -v -s extensions/plan_binding -p 'test_*.py'
    python3 extensions/plan_binding/check.py --out extensions/plan_binding/results

Reproduce from the fixed model outputs into a fresh directory:

    python3 extensions/plan_binding/replay.py run --out extensions/plan_binding/my-results
    python3 extensions/plan_binding/check.py --out extensions/plan_binding/my-results

Do not rerun the freeze command over the archived design or replace model
responses. Read DESIGN.md, robustness_review.md and results/counterexamples.json
for the contract, raw before/after records and known identity/order antecedents.
The test is an application-adapter witness, not a LangGraph defect or a new
general idempotency principle. Logical-operation IDs and mismatch rejection are
additional unevaluated controls.
