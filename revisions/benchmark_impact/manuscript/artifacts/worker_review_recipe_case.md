# Emma recipe-count displacement: auditable development witness

**Question:** “How many of Emma's recipes have I tried out?”
**Public LongMemEval ID:** `45dc21b6`
**Study question key:** `f65dcff812445376dbc709ef`
**Question date:** June 16, 2023; **official reference:** `3`.

This case was selected after the pilot outcomes. It is a same-study source/trace inspection, not outside human peer review, a held-out example, or a new reader experiment. Full paths, hashes, native ranks, context event IDs, and all 21 condition/repeat answer observations are in `worker_review_recipe_case.json`. Those observations correspond to 12 physical archived reader answers because identical prompt aliases intentionally reuse responses.

The independently hash-verified public full-history source contains two annotated user statements:

- **May 29, 04:51**, session position 15, turn 0 (`answer_07664d43_1`): “I've already tried out two of them”. Study event `f36100b59a26e63666fe32cd`.
- **May 30, 06:32**, session position 44, turn 2 (`answer_07664d43_2`): “I've tried out 3 of Emma's recipes so far”. Study event `c013be29cdabd2738e96a10d`.

In the LlamaIndex clean store there are 485 physical records, with one copy of each statement. The older statement ranks first and the newer one fifth in the native candidates. The final ten-record context contains both statements.

After the declared cut/retry history, the store has 737 records. The older statement now has three physical copies, ranked first, second and third. The newer statement still has one unchanged physical record and remains in the native top60 result at **rank 11**. Copies of each of the first three original occurrences fill nine of the final ten slots; only four distinct events remain. Six slots are duplicates, and the newer count is absent from the final context. Annotated support coverage falls from 2/2 to 1/2; this metric measures retained annotation IDs, not a complete semantic-support oracle.

The retained clean answers say three: Sol repeat 0 says “You’d tried 3 of Emma’s recipes as of May 30, 2023, the latest count supplied”; its second repeat also reports three. Qwen says “You have tried out 3 of Emma's recipes so far.”

With the retry context, both Sol repeats say “You had tried two of Emma’s recipes as of May 29, 2023; no later count is supplied.” Qwen answers `2`. The cited older-count events exist in the supplied context. This is compatible with readers following their restricted evidence; the trace does not require hallucination to explain the wrong count relative to the official reference.

Selecting distinct event occurrences from the same native candidate list restores the clean ten-event context, including the newer statement. The complete prompt bytes then equal the clean prompt, so clean and dedup deliberately use the **same archived response**. Both admission controls also preserve the clean input. This is a concrete demonstration of context restoration, not an additional independent generation showing recovery.

The primary judge's task labels agree with the visible numeric difference, but the pilot's separate current-conflict calibration still failed and is retained. Do not present this single selected witness, or the broader automated transition counts, as a validated population-level stale-memory failure rate.
