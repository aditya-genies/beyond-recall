# Sol 6.1 through Codex: descriptive planning pilot

The protocol was frozen before 24 model requests: six synthetic scenarios,
two store snapshots and two fresh contexts per condition. The partial snapshot
applies the first operation from original repeat 0 and is constant across both
partial repeats. No failed call is discarded; all 24 succeeded.

The user explicitly requested personal Codex and Sol6.1. Calls used CLI
0.165.0-alpha.1.2, requested model gpt-6.1-sol and medium reasoning. Each used
an empty temporary directory, ephemeral session, ignored user configuration,
project documents disabled, a read-only environment and fixed output schema.
Existing Codex authentication was used; no API key or company source.

Prompts and raw final JSON responses are in registered/trials. Public usage
events are in result files. Hidden reasoning, session IDs, local paths and
diagnostics are excluded. The exact backend snapshot, temperature, seed and
harness system prompt were not exposed or controlled.

Seven of twelve identical-prompt pairs differ literally, even ignoring
operation-list order. Differences include synonymous fact keys/wording.
Twelve original/partial comparisons differ, but those are different inputs.
Neither count is a semantic error rate, harmfulness assessment or population
estimate. No significance test or confidence interval is justified.

Verify archived data without model access:

    python3 extensions/sol_pilot/check.py --out extensions/sol_pilot/registered

For new requests, freeze a protocol in a fresh directory:

    python3 extensions/sol_pilot/pilot.py prepare --out extensions/sol_pilot/my-pilot
    python3 extensions/sol_pilot/pilot.py run --out extensions/sol_pilot/my-pilot --cli /path/to/codex

New outputs may differ. Do not overwrite the archive. The protocol was not
externally preregistered. A downstream exploratory integration uses fixed
outputs and makes no additional model requests.
