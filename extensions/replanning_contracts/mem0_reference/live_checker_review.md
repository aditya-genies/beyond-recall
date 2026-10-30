# Separate live Mem0 replay audit

The separate checker passes all four exited baseline processes and all 48 fresh-process retries. It checks 553 artifact hashes and reads each actual Qdrant point/history store. No raw artifact was modified. The evidence supports a bounded native-pipeline replay observation, not a natural failure-rate or semantic-quality estimate.

## Confirmed observations

Each baseline requested 8, 12, 24 or 40 authored preferences, produced that many model response items, and stored that many native records. The child then exited with code 87 after the native API returned and before the application-level logical acknowledgement. This is actual process termination after committed effects; it is not a dropped network packet, an interruption inside a SQLite commit or a power-loss experiment.

There are 28 successful fresh-model request-status files: four baseline requests and 24 retry requests. The other 24 retries reuse the parsed baseline model response, including its literal strings, and have no fresh-request prompt/schema artifact. The retained-result control is not another model observation and does not provide stable operation addresses by itself.

For fresh-model native-k10 retries, both recent-context conditions add 0, 2, 14 and 30 records at the four respective source sizes. The fresh-recent cases add 46 verbatim copies in total. The aged-recent cases add 46 records, of which 45 are verbatim baseline copies and one is a different literal formulation, `User prefers the metric measurement system.` That formulation is not graded as semantically wrong. Thus the eight fresh-model native retries add 91 exact copies plus one ungraded new string. Recorded-result native retries add 92 exact copies. The widened-candidate and sequential exact-admission controls add no records in their observed retries. All baseline record identities, literal values and stored point bytes are preserved.

The fresh and aged context conditions are verified from the actual native messages sent to the model. The native formatter truncates each historical message to 300 characters. Fresh-recent context therefore retains the original source message or its prefix, not necessarily the entire previous preference batch. Aged retries append twelve neutral synthetic messages through the native history API, evict the source from its ten-message cache, and send ten neutral historical messages. Every repeated New Messages section still contains the complete original input. The checker also verifies the empty Recently Extracted Memories section and exact prior-candidate projection.

## What was checked

The checker imports neither `live.py`, `experiment.py` nor Mem0 metric functions. It reuses only our separately authored read-only raw decoder. It verifies the driver/protocol/protected-source hashes; exact four-baseline/48-retry coverage; absence of unreported execution or model-status artifacts; real child exit results and the explicit pre-logical-ack witness; all model-artifact hashes; raw response versus used response and admission removals; model output schema; wrapper prompt versus native role-designated messages; tool-event absence; and completed request usage events.

It reconciles candidate IDs/text/hash with the prior store, returned ADD items with admitted literal hashes, every new native point with its ADD history row, all recorded metrics, and the final summary. Every retry's starting API snapshot matches the exited baseline. The original history prefix and the complete serialized baseline point bytes match the baseline archive. This is stronger evidence than comparing only counts, while the driver did not capture a separate full database-byte manifest immediately before every retry. Ranking and BGE ONNX inference are not independently rerun.

Three focused forgery tests reject a false successful exit in place of code 87, a used response that bypasses the exact filter, and a changed value in the supposed copied baseline. These tests use newly authored toy values and never mutate recorded data. The earlier raw-decoder forgery checks separately cover candidate hashes, duplicate metrics and hidden physical points.

## Claim boundaries

Fresh model outputs need not satisfy the literal N-|U| equality from the controlled campaign: a new formulation can have a different hash, as one observed case does. This audit never imposes that equality on fresh replies or labels paraphrases as semantic errors. It verifies the concrete exact-copy observation instead.

Fresh requests in different arms are different nondeterministic draws. The copied baseline stores are matched, but those outputs are not interchangeable counterfactuals. The recorded-result strategy holds the chosen literal response fixed and demonstrates that this replay mechanism does not require a changed model decision. Widened candidates and global exact filtering remain authored interventions; the exact filter is a sequential postprocessor rather than an atomic multi-writer native API. No default Mem0/OpenAI configuration, model-population incidence, complete recovery theorem or vendor exactly-once promise is established.

The checker was written after the experiment and after its aggregate outcomes were shared. It is a separate implementation within the same study, not external replication. `live_verification.json` records the complete per-case reconstruction and evidence hashes; `live_checker_provenance.json` records source/test hashes. No manuscript or remote state was changed.

```sh
python extensions/replanning_contracts/mem0_reference/check_live.py
python -W error::ResourceWarning -m unittest discover \
  -s extensions/replanning_contracts/mem0_reference -p test_check_live.py -v
```
