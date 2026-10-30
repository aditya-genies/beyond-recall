# Robustness review of the positional-address hypothesis

## Finding

The conditional claim is supported by the archived responses and the declared integration. In 36 SQLite integrations covering every one of the 12 original-0/partial-response pairs, the positional-replanning arm overwrites the completed prefix under two recorded responses. The same fresh plans produce no prefix overwrite under the disjoint-address control, and the retained original plan produces none under its original positional addresses. Prefix binding is preserved in 10/12, 12/12, and 12/12 integrations, respectively.

Both witnesses come from **one scenario**, `preferences`, whose original first operation is a targetless put of `reply_style = Prefers concise replies.` Each archived partial response omits that already represented fact and begins with a targetless put of `preferred_units = Prefers metric units.` Zero-based slot 0 is reused at physical address `pos:5e63457a9c29cdfc7a930e5cf22169afd208af9f30ffafe46611b139203aa662`. The committed SQL audit shows the row named `preferences-first-effect` changing from the style key to the units key. The final store contains the units and hobby records and no style-key record. See `results/counterexamples.json` for complete before/after records and `results/*sqlite` for the committed audit.

This is a repeat of the same address-coordinate input, not an accidental SHA-256 collision. A stable function of a new list's positions does not preserve the association between an address and the originally selected operation when replanning compacts that list.

## Attempts to falsify the interpretation

- **Unrelated-prefix-address confound:** using the pilot's visible ID as an unrelated physical record would make a new positional hash miss it and could falsely suggest safety. Here the common public-ID binding maps that visible ID to the actual completed slot-0 address. Before any recovery operation, each arm must reproduce the complete archived partial snapshot exactly. The separate checker independently reconstructs that mapping and all stored rows.
- **Plan-content confound:** the fresh-address control executes exactly the same archived remaining operations as positional replanning. Only the targetless address rule changes. Both preferences responses preserve the style prefix in this control, isolating positional reuse as the cause of the observed overwrite.
- **Literal-synonym confound:** no operation-list variation or changed literal value is scored as a semantic error. The outcome is a physical cross-key overwrite of the same completed record. The same-key changed-value negative test intentionally produces a different literal prefix value while recording no structural alias. The result does not establish semantic accuracy of either the fresh or retained plans.
- **Selective-response confound:** all six scenarios and both archived partial responses are included. Original repeat 0 is the fixed baseline specified before replay; it is not replaced. Only the preferences scenario has a targetless first operation, so its two partial responses supply the two at-risk prefix cases. The other ten integrations in each arm are controls with named first updates or a named first delete. Two positives among these 12 constructed plan pairs must not be presented as a model failure probability or as evidence from 12 independent trials.
- **Named-target unfairness:** original named records and the newly exposed prefix record resolve through the same bindings in all arms. Named targets are never reassigned by a policy-specific rule. SQLite records, bindings, and every before/after audit row match a separately implemented reconstruction.
- **Execution/evidence circularity:** `check.py` imports no participant execution or observation function and recomputes outcomes from raw recorded response files and read-only database rows. It is a separate implementation by the same author on the same host, not independent external replication. Three focused negative tests also pass.

## Scope of the supported claim

A suitable statement is: “In a posthoc SQLite integration follow-up using recorded partial-snapshot plans, two responses from the preferences scenario omitted a completed style operation and reused slot 0 for a units operation. Replanning with positional addresses overwrote the completed style record; the same replans with fresh addresses and replay of the retained original plan preserved it.”

Do not state that the model chose an unreasonable plan, that omission is itself a failure, that stable effect addresses generally fail, that the model has a measured drift/failure rate, or that a specific memory framework uses this integration. This example supports persistence of the association between effect identity and the chosen operation; it does not choose a universally correct semantic identity scheme.

The related mechanism is already documented publicly. LangGraph's [Graph API overview, “Re-execution and idempotency”](https://docs.langchain.com/oss/python/langgraph/graph-api#re-execution-and-idempotency) warns that changing task or interrupt order before resumption can mismatch restored task results. Malcolm Featonby's [“Making Retries Safe with Idempotent APIs,” “Same client request ID, different intent”](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) describes storing initial parameters alongside a client token and rejecting changed parameters under the same token. Both current primary pages were checked directly. These are explanatory analogies; this follow-up neither tests those implementations nor discovers a previously unknown general identity/order hazard.

## Provenance and reproduction

The design was frozen after observing pilot outputs and before the first SQLite replay. This is explicitly posthoc exploratory work, not a preregistration. No model request was made in this extension. The freeze includes the design, execution source, checker, tests, all registered pilot files, and primary source/result hashes; all protected files remain byte-identical. Its SHA-256 is `e4ed851befcd1ddf183bf0a8315588df91b8faed706648fbdacb53eb0a26df22`.

From the artifact root, use:

```sh
python3 -W error::ResourceWarning -m unittest discover -s extensions/plan_binding -p test_replay.py -v
python3 extensions/plan_binding/replay.py run --out extensions/plan_binding/results_new
python3 extensions/plan_binding/check.py --out extensions/plan_binding/results_new
```

The checked-in `design_freeze.json` is reused; do not rerun `freeze` over it. The runner refuses changed frozen inputs and existing output directories. The three negative checks cover mismatched partial snapshots, same-key literal variation, and fresh-address prefix preservation. The complete observations, summaries, counterexamples, per-integration databases, execution provenance, and separate checker report are retained. No primary campaign, pilot raw file, manuscript, repository visibility, or remote state was changed.
