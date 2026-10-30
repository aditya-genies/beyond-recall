# Public data and model attribution

This independent, noncommercial research phase uses released public benchmark
conversations. It uses no employer application code, credentials, private user
conversations or internal incidents. Upstream raw downloads remain outside the
repository. Derived participant records, prompts and answer/grading artifacts
can contain excerpts from those public datasets and retain their source terms.

LoCoMo is from Adyasha Maharana, Dong-Ho Lee, Sergey Tulyakov, Mohit Bansal,
Francesco Barbieri and Yuwei Fang, *Evaluating Very Long-Term Conversational
Memory of LLM Agents* (ACL 2024),
<https://aclanthology.org/2024.acl-long.747/>. The source is
<https://github.com/snap-research/locomo/tree/3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376>.
Its pinned [LICENSE.txt](https://github.com/snap-research/locomo/blob/3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376/LICENSE.txt)
states [Creative Commons Attribution–NonCommercial 4.0 International](https://creativecommons.org/licenses/by-nc/4.0/).
That license and its warranty disclaimer apply to redistributed source excerpts
and derived LoCoMo material. Changes here include opaque occurrence IDs,
participant/evaluator separation, appending explicitly labelled released image
captions, selecting fixed development questions, and synthetic delivery retries.
The authors do not endorse this study. No new license for this study removes
the upstream noncommercial restriction.

LongMemEval is from Di Wu, Hongwei Wang, Wenhao Yu, Yuwei Zhang, Kai-Wei Chang
and Dong Yu, *LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive
Memory*, <https://arxiv.org/abs/2410.10813>. The source code revision is
<https://github.com/xiaowu0162/LongMemEval/tree/9e0b455f4ef0e2ab8f2e582289761153549043fc>;
the cleaned dataset is
<https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/tree/98d7416c24c778c2fee6e6f3006e7a073259d48f>.
The pinned hosted dataset card declares MIT; code and hosted data identities
are recorded separately. Changes here remove evaluator flags from participant
inputs, distinguish repeated source occurrences, preserve full-history dates,
select development questions, and apply synthetic delivery retries.

Native Mem0 and LlamaIndex software and their exact installed versions are
recorded in the protocol and runtime manifests. Embeddings use the public
BGE-small-en-v1.5 model through native FastEmbed APIs. The local reader is
mlx-community/Qwen3-4B-4bit at a pinned revision, under Apache 2.0 as recorded
in local_reader_feasibility.json. Model weights are not redistributed here.
Sol 6.1 requests use the researcher's authorized personal Codex access; this
is not an API-key experiment or a claim of a pinned backend weight snapshot.

The separate scorer reports an independently transcribed LoCoMo token metric
validated against its pinned public source. Adapted Sol semantic judgements
are not official LoCoMo/LongMemEval leaderboard scores or human adjudication.
