# Completed experimental log

## 1. Experimental Setup

Datasets: LoCoMo and full cleaned LongMemEval-S. The fixed development selection has 12 LoCoMo questions from two conversations and 12 LongMemEval-S questions from 12 gold-evidence components, across 14 source histories. Shared background sessions preclude treating all question rows as independent. No held-out answers were inspected. Source revisions, licenses, turn projection, dates and participant/evaluator separation are supplied in data.py, the source audit and the frozen pilot protocol.

The native raw-document participants are Mem0 infer=False with local Qdrant hybrid retrieval and native persisted LlamaIndex dense retrieval. Both use real local 384-dimensional BGE embeddings. No extraction LLM is called. The common native baseline is closed and cloned, preserving original physical IDs. A hash rule independent of questions/gold chooses source occurrences for two repeat deliveries; the first exits87 after native effects but before the study's logical batch acknowledgement. The process is then restarted. This is a post-effect batch-boundary failure, not packet loss or an interrupted database commit.

At most60 returned candidates feed at most10 whole records and12000 UTF-8 bytes in the serialized evidence array. This is not a token-budget claim. Mem0 internally over-fetches four times the requested result limit; LlamaIndex is a different native dense participant. Seven arms include clean delivery, native replay, authored sequential event admission, content admission, retrieval-time event dedup, no context and labelled oracle support. Oracle support is not a deployable method.

Sol requested gpt-6.1-sol through authorized personal Codex access, medium reasoning, twice per distinct prompt. Backend weights, system prompt, seed and temperature are unattested. Local mlx-community/Qwen3-4B-4bit uses revision4dcb3d101c2a062e5c1d4bb173588c54ea6c4d25; all11 files were hash checked; temperature0, maximum512 output tokens, thinking flag false and trust_remote_code false. Neither profile establishes universal reader determinism. No company credentials, private conversations or hosted employer services were used.

## 2. Raw Numeric Data

The eight rows below average Sol repeats within question; each dataset/backend/reader cell contains12 questions. The task labels are exploratory same-study automated judgments, not official leaderboard accuracy or independent human adjudication.

| Dataset | Backend | Reader | Questions | Clean task mean | Retry task mean | Read-event-dedup task mean |
|---|---|---|---:|---:|---:|---:|
| LoCoMo | mem0_raw | sol |12|0.833333|0.750000|0.833333|
| LongMemEval-S | mem0_raw | sol |12|0.916667|0.916667|0.916667|
| LoCoMo | mem0_raw | qwen |12|0.666667|0.666667|0.666667|
| LongMemEval-S | mem0_raw | qwen |12|0.583333|0.500000|0.583333|
| LoCoMo | llama_index | sol |12|0.583333|0.416667|0.583333|
| LongMemEval-S | llama_index | sol |12|0.916667|0.833333|0.916667|
| LoCoMo | llama_index | qwen |12|0.500000|0.416667|0.500000|
| LongMemEval-S | llama_index | qwen |12|0.583333|0.500000|0.583333|

The following full machine summary retains every arm, metric, uncertainty count, missingness count, paired transition and failed-calibration flag. It is an input record, not a claim that model-call or observation counts are independent samples.

```json
{
  "phase": "Descriptive development pilot; NOT held-out confirmation or Q1-readiness evidence",
  "grading_calibration": {
    "status": "CALIBRATION_MISMATCH",
    "fixtures": 12,
    "mismatches": [
      {
        "id": "625db9ba9122cc9342ce5168",
        "label": "current_conflict",
        "expected": "no",
        "observed": "yes"
      },
      {
        "id": "e3cd6f47f59a67437521897e",
        "label": "current_conflict",
        "expected": "no",
        "observed": "yes"
      }
    ],
    "interpretation": "Authored rubric fixtures, not benchmark task samples or independent expert validation."
  },
  "semantic_claim_gate": "FAILED auxiliary calibration: task judgements exploratory; no definitive stale-state or semantic efficacy claim.",
  "unique_request_status_counts": {
    "sol/PASS": 298,
    "qwen/PASS": 149
  },
  "expected_unique_prompts": 149,
  "unique_questions": 24,
  "condition_observations": 1008,
  "graded_unique_answer_question_pairs": 447,
  "grade_failures": [],
  "summaries": [
    {
      "backend": "llama_index",
      "reader": "qwen",
      "dataset": "locomo",
      "arm": "clean",
      "unique_questions": 12,
      "condition_observations": 12,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0.5,
      "reader_failure_as_incorrect": 0.5,
      "supported_task_available_case": 0.4166666666666667,
      "locomo_token_proxy": 0.26970645095645096,
      "evidence_supported_counts": {
        "yes": 9,
        "uncertain": 2,
        "no": 1
      },
      "current_conflict_unvalidated_counts": {
        "no": 12
      },
      "mean_context_serialized_utf8_bytes": 2726.5,
      "duplicate_event_slots": 0,
      "positive_support_coverage": 0.625
    },
    {
      "backend": "llama_index",
      "reader": "qwen",
      "dataset": "locomo",
      "arm": "content_admission",
      "unique_questions": 12,
      "condition_observations": 12,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0.5,
      "reader_failure_as_incorrect": 0.5,
      "supported_task_available_case": 0.4166666666666667,
      "locomo_token_proxy": 0.26970645095645096,
      "evidence_supported_counts": {
        "yes": 9,
        "uncertain": 2,
        "no": 1
      },
      "current_conflict_unvalidated_counts": {
        "no": 12
      },
      "mean_context_serialized_utf8_bytes": 2726.5,
      "duplicate_event_slots": 0,
      "positive_support_coverage": 0.625
    },
    {
      "backend": "llama_index",
      "reader": "qwen",
      "dataset": "locomo",
      "arm": "event_admission",
      "unique_questions": 12,
      "condition_observations": 12,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0.5,
      "reader_failure_as_incorrect": 0.5,
      "supported_task_available_case": 0.4166666666666667,
      "locomo_token_proxy": 0.26970645095645096,
      "evidence_supported_counts": {
        "yes": 9,
        "uncertain": 2,
        "no": 1
      },
      "current_conflict_unvalidated_counts": {
        "no": 12
      },
      "mean_context_serialized_utf8_bytes": 2726.5,
      "duplicate_event_slots": 0,
      "positive_support_coverage": 0.625
    },
    {
      "backend": "llama_index",
      "reader": "qwen",
      "dataset": "locomo",
      "arm": "no_context",
      "unique_questions": 12,
      "condition_observations": 12,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0,
      "reader_failure_as_incorrect": 0,
      "supported_task_available_case": 0,
      "locomo_token_proxy": 0.008818342151675485,
      "evidence_supported_counts": {
        "uncertain": 8,
        "yes": 4
      },
      "current_conflict_unvalidated_counts": {
        "no": 12
      },
      "mean_context_serialized_utf8_bytes": 2,
      "duplicate_event_slots": 0,
      "positive_support_coverage": 0.0
    },
    {
      "backend": "llama_index",
      "reader": "qwen",
      "dataset": "locomo",
      "arm": "oracle_support",
      "unique_questions": 12,
      "condition_observations": 12,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0.6666666666666666,
      "reader_failure_as_incorrect": 0.6666666666666666,
      "supported_task_available_case": 0.6666666666666666,
      "locomo_token_proxy": 0.33162035333087964,
      "evidence_supported_counts": {
        "yes": 9,
        "no": 3
      },
      "current_conflict_unvalidated_counts": {
        "no": 12
      },
      "mean_context_serialized_utf8_bytes": 538.9166666666666,
      "duplicate_event_slots": 0,
      "positive_support_coverage": 1.0
    },
    {
      "backend": "llama_index",
      "reader": "qwen",
      "dataset": "locomo",
      "arm": "read_event_dedup",
      "unique_questions": 12,
      "condition_observations": 12,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0.5,
      "reader_failure_as_incorrect": 0.5,
      "supported_task_available_case": 0.4166666666666667,
      "locomo_token_proxy": 0.26970645095645096,
      "evidence_supported_counts": {
        "yes": 9,
        "uncertain": 2,
        "no": 1
      },
      "current_conflict_unvalidated_counts": {
        "no": 12
      },
      "mean_context_serialized_utf8_bytes": 2726.5,
      "duplicate_event_slots": 0,
      "positive_support_coverage": 0.625
    },
    {
      "backend": "llama_index",
      "reader": "qwen",
      "dataset": "locomo",
      "arm": "retry",
      "unique_questions": 12,
      "condition_observations": 12,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0.4166666666666667,
      "reader_failure_as_incorrect": 0.4166666666666667,
      "supported_task_available_case": 0.3333333333333333,
      "locomo_token_proxy": 0.21200670590416507,
      "evidence_supported_counts": {
        "yes": 8,
        "uncertain": 3,
        "no": 1
      },
      "current_conflict_unvalidated_counts": {
        "no": 12
      },
      "mean_context_serialized_utf8_bytes": 2662.3333333333335,
      "duplicate_event_slots": 3.1666666666666665,
      "positive_support_coverage": 0.4166666666666667
    },
    {
      "backend": "llama_index",
      "reader": "qwen",
      "dataset": "longmemeval",
      "arm": "clean",
      "unique_questions": 12,
      "condition_observations": 12,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0.5833333333333334,
      "reader_failure_as_incorrect": 0.5833333333333334,
      "supported_task_available_case": 0.5833333333333334,
      "locomo_token_proxy": null,
      "evidence_supported_counts": {
        "no": 4,
        "yes": 8
      },
      "current_conflict_unvalidated_counts": {
        "no": 12
      },
      "mean_context_serialized_utf8_bytes": 8005.583333333333,
      "duplicate_event_slots": 0,
      "positive_support_coverage": 0.9545454545454546
    },
    {
      "backend": "llama_index",
      "reader": "qwen",
      "dataset": "longmemeval",
      "arm": "content_admission",
      "unique_questions": 12,
      "condition_observations": 12,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0.5833333333333334,
      "reader_failure_as_incorrect": 0.5833333333333334,
      "supported_task_available_case": 0.5833333333333334,
      "locomo_token_proxy": null,
      "evidence_supported_counts": {
        "no": 4,
        "yes": 8
      },
      "current_conflict_unvalidated_counts": {
        "no": 12
      },
      "mean_context_serialized_utf8_bytes": 8005.583333333333,
      "duplicate_event_slots": 0,
      "positive_support_coverage": 0.9545454545454546
    },
    {
      "backend": "llama_index",
      "reader": "qwen",
      "dataset": "longmemeval",
      "arm": "event_admission",
      "unique_questions": 12,
      "condition_observations": 12,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0.5833333333333334,
      "reader_failure_as_incorrect": 0.5833333333333334,
      "supported_task_available_case": 0.5833333333333334,
      "locomo_token_proxy": null,
      "evidence_supported_counts": {
        "no": 4,
        "yes": 8
      },
      "current_conflict_unvalidated_counts": {
        "no": 12
      },
      "mean_context_serialized_utf8_bytes": 8005.583333333333,
      "duplicate_event_slots": 0,
      "positive_support_coverage": 0.9545454545454546
    },
    {
      "backend": "llama_index",
      "reader": "qwen",
      "dataset": "longmemeval",
      "arm": "no_context",
      "unique_questions": 12,
      "condition_observations": 12,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0.08333333333333333,
      "reader_failure_as_incorrect": 0.08333333333333333,
      "supported_task_available_case": 0.08333333333333333,
      "locomo_token_proxy": null,
      "evidence_supported_counts": {
        "uncertain": 6,
        "yes": 6
      },
      "current_conflict_unvalidated_counts": {
        "no": 12
      },
      "mean_context_serialized_utf8_bytes": 2,
      "duplicate_event_slots": 0,
      "positive_support_coverage": 0.0
    },
    {
      "backend": "llama_index",
      "reader": "qwen",
      "dataset": "longmemeval",
      "arm": "oracle_support",
      "unique_questions": 12,
      "condition_observations": 12,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0.5833333333333334,
      "reader_failure_as_incorrect": 0.5833333333333334,
      "supported_task_available_case": 0.5833333333333334,
      "locomo_token_proxy": null,
      "evidence_supported_counts": {
        "no": 5,
        "yes": 7
      },
      "current_conflict_unvalidated_counts": {
        "no": 12
      },
      "mean_context_serialized_utf8_bytes": 747,
      "duplicate_event_slots": 0,
      "positive_support_coverage": 1.0
    },
    {
      "backend": "llama_index",
      "reader": "qwen",
      "dataset": "longmemeval",
      "arm": "read_event_dedup",
      "unique_questions": 12,
      "condition_observations": 12,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0.5833333333333334,
      "reader_failure_as_incorrect": 0.5833333333333334,
      "supported_task_available_case": 0.5833333333333334,
      "locomo_token_proxy": null,
      "evidence_supported_counts": {
        "no": 4,
        "yes": 8
      },
      "current_conflict_unvalidated_counts": {
        "no": 12
      },
      "mean_context_serialized_utf8_bytes": 8005.583333333333,
      "duplicate_event_slots": 0,
      "positive_support_coverage": 0.9545454545454546
    },
    {
      "backend": "llama_index",
      "reader": "qwen",
      "dataset": "longmemeval",
      "arm": "retry",
      "unique_questions": 12,
      "condition_observations": 12,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0.5,
      "reader_failure_as_incorrect": 0.5,
      "supported_task_available_case": 0.5,
      "locomo_token_proxy": null,
      "evidence_supported_counts": {
        "no": 4,
        "yes": 8
      },
      "current_conflict_unvalidated_counts": {
        "no": 11,
        "yes": 1
      },
      "mean_context_serialized_utf8_bytes": 7379.416666666667,
      "duplicate_event_slots": 2.3333333333333335,
      "positive_support_coverage": 0.9090909090909091
    },
    {
      "backend": "llama_index",
      "reader": "sol",
      "dataset": "locomo",
      "arm": "clean",
      "unique_questions": 12,
      "condition_observations": 24,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0.5833333333333334,
      "reader_failure_as_incorrect": 0.5833333333333334,
      "supported_task_available_case": 0.5833333333333334,
      "locomo_token_proxy": 0.3053246045893105,
      "evidence_supported_counts": {
        "yes": 24
      },
      "current_conflict_unvalidated_counts": {
        "no": 24
      },
      "mean_context_serialized_utf8_bytes": 2726.5,
      "duplicate_event_slots": 0,
      "positive_support_coverage": 0.625
    },
    {
      "backend": "llama_index",
      "reader": "sol",
      "dataset": "locomo",
      "arm": "content_admission",
      "unique_questions": 12,
      "condition_observations": 24,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0.5833333333333334,
      "reader_failure_as_incorrect": 0.5833333333333334,
      "supported_task_available_case": 0.5833333333333334,
      "locomo_token_proxy": 0.3053246045893105,
      "evidence_supported_counts": {
        "yes": 24
      },
      "current_conflict_unvalidated_counts": {
        "no": 24
      },
      "mean_context_serialized_utf8_bytes": 2726.5,
      "duplicate_event_slots": 0,
      "positive_support_coverage": 0.625
    },
    {
      "backend": "llama_index",
      "reader": "sol",
      "dataset": "locomo",
      "arm": "event_admission",
      "unique_questions": 12,
      "condition_observations": 24,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0.5833333333333334,
      "reader_failure_as_incorrect": 0.5833333333333334,
      "supported_task_available_case": 0.5833333333333334,
      "locomo_token_proxy": 0.3053246045893105,
      "evidence_supported_counts": {
        "yes": 24
      },
      "current_conflict_unvalidated_counts": {
        "no": 24
      },
      "mean_context_serialized_utf8_bytes": 2726.5,
      "duplicate_event_slots": 0,
      "positive_support_coverage": 0.625
    },
    {
      "backend": "llama_index",
      "reader": "sol",
      "dataset": "locomo",
      "arm": "no_context",
      "unique_questions": 12,
      "condition_observations": 24,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0,
      "reader_failure_as_incorrect": 0,
      "supported_task_available_case": 0,
      "locomo_token_proxy": 0.04169497477353514,
      "evidence_supported_counts": {
        "yes": 17,
        "uncertain": 7
      },
      "current_conflict_unvalidated_counts": {
        "no": 24
      },
      "mean_context_serialized_utf8_bytes": 2,
      "duplicate_event_slots": 0,
      "positive_support_coverage": 0.0
    },
    {
      "backend": "llama_index",
      "reader": "sol",
      "dataset": "locomo",
      "arm": "oracle_support",
      "unique_questions": 12,
      "condition_observations": 24,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0.9166666666666666,
      "reader_failure_as_incorrect": 0.9166666666666666,
      "supported_task_available_case": 0.9166666666666666,
      "locomo_token_proxy": 0.34146345627769775,
      "evidence_supported_counts": {
        "yes": 24
      },
      "current_conflict_unvalidated_counts": {
        "no": 24
      },
      "mean_context_serialized_utf8_bytes": 538.9166666666666,
      "duplicate_event_slots": 0,
      "positive_support_coverage": 1.0
    },
    {
      "backend": "llama_index",
      "reader": "sol",
      "dataset": "locomo",
      "arm": "read_event_dedup",
      "unique_questions": 12,
      "condition_observations": 24,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0.5833333333333334,
      "reader_failure_as_incorrect": 0.5833333333333334,
      "supported_task_available_case": 0.5833333333333334,
      "locomo_token_proxy": 0.3053246045893105,
      "evidence_supported_counts": {
        "yes": 24
      },
      "current_conflict_unvalidated_counts": {
        "no": 24
      },
      "mean_context_serialized_utf8_bytes": 2726.5,
      "duplicate_event_slots": 0,
      "positive_support_coverage": 0.625
    },
    {
      "backend": "llama_index",
      "reader": "sol",
      "dataset": "locomo",
      "arm": "retry",
      "unique_questions": 12,
      "condition_observations": 24,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0.4166666666666667,
      "reader_failure_as_incorrect": 0.4166666666666667,
      "supported_task_available_case": 0.4166666666666667,
      "locomo_token_proxy": 0.2476929932812286,
      "evidence_supported_counts": {
        "yes": 24
      },
      "current_conflict_unvalidated_counts": {
        "no": 24
      },
      "mean_context_serialized_utf8_bytes": 2662.3333333333335,
      "duplicate_event_slots": 3.1666666666666665,
      "positive_support_coverage": 0.4166666666666667
    },
    {
      "backend": "llama_index",
      "reader": "sol",
      "dataset": "longmemeval",
      "arm": "clean",
      "unique_questions": 12,
      "condition_observations": 24,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0.9166666666666666,
      "reader_failure_as_incorrect": 0.9166666666666666,
      "supported_task_available_case": 0.9166666666666666,
      "locomo_token_proxy": null,
      "evidence_supported_counts": {
        "yes": 24
      },
      "current_conflict_unvalidated_counts": {
        "no": 24
      },
      "mean_context_serialized_utf8_bytes": 8005.583333333333,
      "duplicate_event_slots": 0,
      "positive_support_coverage": 0.9545454545454546
    },
    {
      "backend": "llama_index",
      "reader": "sol",
      "dataset": "longmemeval",
      "arm": "content_admission",
      "unique_questions": 12,
      "condition_observations": 24,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0.9166666666666666,
      "reader_failure_as_incorrect": 0.9166666666666666,
      "supported_task_available_case": 0.9166666666666666,
      "locomo_token_proxy": null,
      "evidence_supported_counts": {
        "yes": 24
      },
      "current_conflict_unvalidated_counts": {
        "no": 24
      },
      "mean_context_serialized_utf8_bytes": 8005.583333333333,
      "duplicate_event_slots": 0,
      "positive_support_coverage": 0.9545454545454546
    },
    {
      "backend": "llama_index",
      "reader": "sol",
      "dataset": "longmemeval",
      "arm": "event_admission",
      "unique_questions": 12,
      "condition_observations": 24,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0.9166666666666666,
      "reader_failure_as_incorrect": 0.9166666666666666,
      "supported_task_available_case": 0.9166666666666666,
      "locomo_token_proxy": null,
      "evidence_supported_counts": {
        "yes": 24
      },
      "current_conflict_unvalidated_counts": {
        "no": 24
      },
      "mean_context_serialized_utf8_bytes": 8005.583333333333,
      "duplicate_event_slots": 0,
      "positive_support_coverage": 0.9545454545454546
    },
    {
      "backend": "llama_index",
      "reader": "sol",
      "dataset": "longmemeval",
      "arm": "no_context",
      "unique_questions": 12,
      "condition_observations": 24,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0.08333333333333333,
      "reader_failure_as_incorrect": 0.08333333333333333,
      "supported_task_available_case": 0.08333333333333333,
      "locomo_token_proxy": null,
      "evidence_supported_counts": {
        "yes": 16,
        "uncertain": 8
      },
      "current_conflict_unvalidated_counts": {
        "no": 24
      },
      "mean_context_serialized_utf8_bytes": 2,
      "duplicate_event_slots": 0,
      "positive_support_coverage": 0.0
    },
    {
      "backend": "llama_index",
      "reader": "sol",
      "dataset": "longmemeval",
      "arm": "oracle_support",
      "unique_questions": 12,
      "condition_observations": 24,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0.9166666666666666,
      "reader_failure_as_incorrect": 0.9166666666666666,
      "supported_task_available_case": 0.875,
      "locomo_token_proxy": null,
      "evidence_supported_counts": {
        "yes": 23,
        "uncertain": 1
      },
      "current_conflict_unvalidated_counts": {
        "no": 24
      },
      "mean_context_serialized_utf8_bytes": 747,
      "duplicate_event_slots": 0,
      "positive_support_coverage": 1.0
    },
    {
      "backend": "llama_index",
      "reader": "sol",
      "dataset": "longmemeval",
      "arm": "read_event_dedup",
      "unique_questions": 12,
      "condition_observations": 24,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0.9166666666666666,
      "reader_failure_as_incorrect": 0.9166666666666666,
      "supported_task_available_case": 0.9166666666666666,
      "locomo_token_proxy": null,
      "evidence_supported_counts": {
        "yes": 24
      },
      "current_conflict_unvalidated_counts": {
        "no": 24
      },
      "mean_context_serialized_utf8_bytes": 8005.583333333333,
      "duplicate_event_slots": 0,
      "positive_support_coverage": 0.9545454545454546
    },
    {
      "backend": "llama_index",
      "reader": "sol",
      "dataset": "longmemeval",
      "arm": "retry",
      "unique_questions": 12,
      "condition_observations": 24,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0.8333333333333334,
      "reader_failure_as_incorrect": 0.8333333333333334,
      "supported_task_available_case": 0.8333333333333334,
      "locomo_token_proxy": null,
      "evidence_supported_counts": {
        "yes": 24
      },
      "current_conflict_unvalidated_counts": {
        "no": 24
      },
      "mean_context_serialized_utf8_bytes": 7379.416666666667,
      "duplicate_event_slots": 2.3333333333333335,
      "positive_support_coverage": 0.9090909090909091
    },
    {
      "backend": "mem0_raw",
      "reader": "qwen",
      "dataset": "locomo",
      "arm": "clean",
      "unique_questions": 12,
      "condition_observations": 12,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0.6666666666666666,
      "reader_failure_as_incorrect": 0.6666666666666666,
      "supported_task_available_case": 0.5833333333333334,
      "locomo_token_proxy": 0.3167249417249417,
      "evidence_supported_counts": {
        "yes": 9,
        "uncertain": 1,
        "no": 2
      },
      "current_conflict_unvalidated_counts": {
        "no": 12
      },
      "mean_context_serialized_utf8_bytes": 3227.1666666666665,
      "duplicate_event_slots": 0,
      "positive_support_coverage": 0.8888888888888888
    },
    {
      "backend": "mem0_raw",
      "reader": "qwen",
      "dataset": "locomo",
      "arm": "content_admission",
      "unique_questions": 12,
      "condition_observations": 12,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0.6666666666666666,
      "reader_failure_as_incorrect": 0.6666666666666666,
      "supported_task_available_case": 0.5833333333333334,
      "locomo_token_proxy": 0.3167249417249417,
      "evidence_supported_counts": {
        "yes": 9,
        "uncertain": 1,
        "no": 2
      },
      "current_conflict_unvalidated_counts": {
        "no": 12
      },
      "mean_context_serialized_utf8_bytes": 3227.1666666666665,
      "duplicate_event_slots": 0,
      "positive_support_coverage": 0.8888888888888888
    },
    {
      "backend": "mem0_raw",
      "reader": "qwen",
      "dataset": "locomo",
      "arm": "event_admission",
      "unique_questions": 12,
      "condition_observations": 12,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0.6666666666666666,
      "reader_failure_as_incorrect": 0.6666666666666666,
      "supported_task_available_case": 0.5833333333333334,
      "locomo_token_proxy": 0.3167249417249417,
      "evidence_supported_counts": {
        "yes": 9,
        "uncertain": 1,
        "no": 2
      },
      "current_conflict_unvalidated_counts": {
        "no": 12
      },
      "mean_context_serialized_utf8_bytes": 3227.1666666666665,
      "duplicate_event_slots": 0,
      "positive_support_coverage": 0.8888888888888888
    },
    {
      "backend": "mem0_raw",
      "reader": "qwen",
      "dataset": "locomo",
      "arm": "no_context",
      "unique_questions": 12,
      "condition_observations": 12,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0,
      "reader_failure_as_incorrect": 0,
      "supported_task_available_case": 0,
      "locomo_token_proxy": 0.008818342151675485,
      "evidence_supported_counts": {
        "uncertain": 8,
        "yes": 4
      },
      "current_conflict_unvalidated_counts": {
        "no": 12
      },
      "mean_context_serialized_utf8_bytes": 2,
      "duplicate_event_slots": 0,
      "positive_support_coverage": 0.0
    },
    {
      "backend": "mem0_raw",
      "reader": "qwen",
      "dataset": "locomo",
      "arm": "oracle_support",
      "unique_questions": 12,
      "condition_observations": 12,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0.6666666666666666,
      "reader_failure_as_incorrect": 0.6666666666666666,
      "supported_task_available_case": 0.6666666666666666,
      "locomo_token_proxy": 0.33162035333087964,
      "evidence_supported_counts": {
        "yes": 9,
        "no": 3
      },
      "current_conflict_unvalidated_counts": {
        "no": 12
      },
      "mean_context_serialized_utf8_bytes": 538.9166666666666,
      "duplicate_event_slots": 0,
      "positive_support_coverage": 1.0
    },
    {
      "backend": "mem0_raw",
      "reader": "qwen",
      "dataset": "locomo",
      "arm": "read_event_dedup",
      "unique_questions": 12,
      "condition_observations": 12,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0.6666666666666666,
      "reader_failure_as_incorrect": 0.6666666666666666,
      "supported_task_available_case": 0.5833333333333334,
      "locomo_token_proxy": 0.3474765974765975,
      "evidence_supported_counts": {
        "yes": 9,
        "uncertain": 1,
        "no": 2
      },
      "current_conflict_unvalidated_counts": {
        "no": 12
      },
      "mean_context_serialized_utf8_bytes": 3212.0833333333335,
      "duplicate_event_slots": 0,
      "positive_support_coverage": 0.8888888888888888
    },
    {
      "backend": "mem0_raw",
      "reader": "qwen",
      "dataset": "locomo",
      "arm": "retry",
      "unique_questions": 12,
      "condition_observations": 12,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0.6666666666666666,
      "reader_failure_as_incorrect": 0.6666666666666666,
      "supported_task_available_case": 0.5833333333333334,
      "locomo_token_proxy": 0.34660996729962246,
      "evidence_supported_counts": {
        "yes": 10,
        "uncertain": 1,
        "no": 1
      },
      "current_conflict_unvalidated_counts": {
        "no": 12
      },
      "mean_context_serialized_utf8_bytes": 3168.6666666666665,
      "duplicate_event_slots": 3.0833333333333335,
      "positive_support_coverage": 0.8055555555555556
    },
    {
      "backend": "mem0_raw",
      "reader": "qwen",
      "dataset": "longmemeval",
      "arm": "clean",
      "unique_questions": 12,
      "condition_observations": 12,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0.5833333333333334,
      "reader_failure_as_incorrect": 0.5833333333333334,
      "supported_task_available_case": 0.5833333333333334,
      "locomo_token_proxy": null,
      "evidence_supported_counts": {
        "no": 4,
        "yes": 8
      },
      "current_conflict_unvalidated_counts": {
        "no": 12
      },
      "mean_context_serialized_utf8_bytes": 10849.083333333334,
      "duplicate_event_slots": 0,
      "positive_support_coverage": 0.8409090909090909
    },
    {
      "backend": "mem0_raw",
      "reader": "qwen",
      "dataset": "longmemeval",
      "arm": "content_admission",
      "unique_questions": 12,
      "condition_observations": 12,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0.5833333333333334,
      "reader_failure_as_incorrect": 0.5833333333333334,
      "supported_task_available_case": 0.5833333333333334,
      "locomo_token_proxy": null,
      "evidence_supported_counts": {
        "no": 4,
        "yes": 8
      },
      "current_conflict_unvalidated_counts": {
        "no": 12
      },
      "mean_context_serialized_utf8_bytes": 10849.083333333334,
      "duplicate_event_slots": 0,
      "positive_support_coverage": 0.8409090909090909
    },
    {
      "backend": "mem0_raw",
      "reader": "qwen",
      "dataset": "longmemeval",
      "arm": "event_admission",
      "unique_questions": 12,
      "condition_observations": 12,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0.5833333333333334,
      "reader_failure_as_incorrect": 0.5833333333333334,
      "supported_task_available_case": 0.5833333333333334,
      "locomo_token_proxy": null,
      "evidence_supported_counts": {
        "no": 4,
        "yes": 8
      },
      "current_conflict_unvalidated_counts": {
        "no": 12
      },
      "mean_context_serialized_utf8_bytes": 10849.083333333334,
      "duplicate_event_slots": 0,
      "positive_support_coverage": 0.8409090909090909
    },
    {
      "backend": "mem0_raw",
      "reader": "qwen",
      "dataset": "longmemeval",
      "arm": "no_context",
      "unique_questions": 12,
      "condition_observations": 12,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0.08333333333333333,
      "reader_failure_as_incorrect": 0.08333333333333333,
      "supported_task_available_case": 0.08333333333333333,
      "locomo_token_proxy": null,
      "evidence_supported_counts": {
        "uncertain": 6,
        "yes": 6
      },
      "current_conflict_unvalidated_counts": {
        "no": 12
      },
      "mean_context_serialized_utf8_bytes": 2,
      "duplicate_event_slots": 0,
      "positive_support_coverage": 0.0
    },
    {
      "backend": "mem0_raw",
      "reader": "qwen",
      "dataset": "longmemeval",
      "arm": "oracle_support",
      "unique_questions": 12,
      "condition_observations": 12,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0.5833333333333334,
      "reader_failure_as_incorrect": 0.5833333333333334,
      "supported_task_available_case": 0.5833333333333334,
      "locomo_token_proxy": null,
      "evidence_supported_counts": {
        "no": 5,
        "yes": 7
      },
      "current_conflict_unvalidated_counts": {
        "no": 12
      },
      "mean_context_serialized_utf8_bytes": 747,
      "duplicate_event_slots": 0,
      "positive_support_coverage": 1.0
    },
    {
      "backend": "mem0_raw",
      "reader": "qwen",
      "dataset": "longmemeval",
      "arm": "read_event_dedup",
      "unique_questions": 12,
      "condition_observations": 12,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0.5833333333333334,
      "reader_failure_as_incorrect": 0.5833333333333334,
      "supported_task_available_case": 0.5833333333333334,
      "locomo_token_proxy": null,
      "evidence_supported_counts": {
        "no": 4,
        "yes": 8
      },
      "current_conflict_unvalidated_counts": {
        "no": 12
      },
      "mean_context_serialized_utf8_bytes": 10647.083333333334,
      "duplicate_event_slots": 0,
      "positive_support_coverage": 0.8409090909090909
    },
    {
      "backend": "mem0_raw",
      "reader": "qwen",
      "dataset": "longmemeval",
      "arm": "retry",
      "unique_questions": 12,
      "condition_observations": 12,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0.5,
      "reader_failure_as_incorrect": 0.5,
      "supported_task_available_case": 0.5,
      "locomo_token_proxy": null,
      "evidence_supported_counts": {
        "no": 4,
        "yes": 7,
        "uncertain": 1
      },
      "current_conflict_unvalidated_counts": {
        "no": 12
      },
      "mean_context_serialized_utf8_bytes": 10423.666666666666,
      "duplicate_event_slots": 2.3333333333333335,
      "positive_support_coverage": 0.8409090909090909
    },
    {
      "backend": "mem0_raw",
      "reader": "sol",
      "dataset": "locomo",
      "arm": "clean",
      "unique_questions": 12,
      "condition_observations": 24,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0.8333333333333334,
      "reader_failure_as_incorrect": 0.8333333333333334,
      "supported_task_available_case": 0.8333333333333334,
      "locomo_token_proxy": 0.34259541752889894,
      "evidence_supported_counts": {
        "yes": 24
      },
      "current_conflict_unvalidated_counts": {
        "no": 24
      },
      "mean_context_serialized_utf8_bytes": 3227.1666666666665,
      "duplicate_event_slots": 0,
      "positive_support_coverage": 0.8888888888888888
    },
    {
      "backend": "mem0_raw",
      "reader": "sol",
      "dataset": "locomo",
      "arm": "content_admission",
      "unique_questions": 12,
      "condition_observations": 24,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0.8333333333333334,
      "reader_failure_as_incorrect": 0.8333333333333334,
      "supported_task_available_case": 0.8333333333333334,
      "locomo_token_proxy": 0.34259541752889894,
      "evidence_supported_counts": {
        "yes": 24
      },
      "current_conflict_unvalidated_counts": {
        "no": 24
      },
      "mean_context_serialized_utf8_bytes": 3227.1666666666665,
      "duplicate_event_slots": 0,
      "positive_support_coverage": 0.8888888888888888
    },
    {
      "backend": "mem0_raw",
      "reader": "sol",
      "dataset": "locomo",
      "arm": "event_admission",
      "unique_questions": 12,
      "condition_observations": 24,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0.8333333333333334,
      "reader_failure_as_incorrect": 0.8333333333333334,
      "supported_task_available_case": 0.8333333333333334,
      "locomo_token_proxy": 0.34259541752889894,
      "evidence_supported_counts": {
        "yes": 24
      },
      "current_conflict_unvalidated_counts": {
        "no": 24
      },
      "mean_context_serialized_utf8_bytes": 3227.1666666666665,
      "duplicate_event_slots": 0,
      "positive_support_coverage": 0.8888888888888888
    },
    {
      "backend": "mem0_raw",
      "reader": "sol",
      "dataset": "locomo",
      "arm": "no_context",
      "unique_questions": 12,
      "condition_observations": 24,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0,
      "reader_failure_as_incorrect": 0,
      "supported_task_available_case": 0,
      "locomo_token_proxy": 0.04169497477353514,
      "evidence_supported_counts": {
        "yes": 17,
        "uncertain": 7
      },
      "current_conflict_unvalidated_counts": {
        "no": 24
      },
      "mean_context_serialized_utf8_bytes": 2,
      "duplicate_event_slots": 0,
      "positive_support_coverage": 0.0
    },
    {
      "backend": "mem0_raw",
      "reader": "sol",
      "dataset": "locomo",
      "arm": "oracle_support",
      "unique_questions": 12,
      "condition_observations": 24,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0.9166666666666666,
      "reader_failure_as_incorrect": 0.9166666666666666,
      "supported_task_available_case": 0.9166666666666666,
      "locomo_token_proxy": 0.34146345627769775,
      "evidence_supported_counts": {
        "yes": 24
      },
      "current_conflict_unvalidated_counts": {
        "no": 24
      },
      "mean_context_serialized_utf8_bytes": 538.9166666666666,
      "duplicate_event_slots": 0,
      "positive_support_coverage": 1.0
    },
    {
      "backend": "mem0_raw",
      "reader": "sol",
      "dataset": "locomo",
      "arm": "read_event_dedup",
      "unique_questions": 12,
      "condition_observations": 24,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0.8333333333333334,
      "reader_failure_as_incorrect": 0.8333333333333334,
      "supported_task_available_case": 0.8333333333333334,
      "locomo_token_proxy": 0.2927902953475036,
      "evidence_supported_counts": {
        "yes": 24
      },
      "current_conflict_unvalidated_counts": {
        "no": 24
      },
      "mean_context_serialized_utf8_bytes": 3212.0833333333335,
      "duplicate_event_slots": 0,
      "positive_support_coverage": 0.8888888888888888
    },
    {
      "backend": "mem0_raw",
      "reader": "sol",
      "dataset": "locomo",
      "arm": "retry",
      "unique_questions": 12,
      "condition_observations": 24,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0.75,
      "reader_failure_as_incorrect": 0.75,
      "supported_task_available_case": 0.75,
      "locomo_token_proxy": 0.3399441913224051,
      "evidence_supported_counts": {
        "yes": 24
      },
      "current_conflict_unvalidated_counts": {
        "no": 24
      },
      "mean_context_serialized_utf8_bytes": 3168.6666666666665,
      "duplicate_event_slots": 3.0833333333333335,
      "positive_support_coverage": 0.8055555555555556
    },
    {
      "backend": "mem0_raw",
      "reader": "sol",
      "dataset": "longmemeval",
      "arm": "clean",
      "unique_questions": 12,
      "condition_observations": 24,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0.9166666666666666,
      "reader_failure_as_incorrect": 0.9166666666666666,
      "supported_task_available_case": 0.9166666666666666,
      "locomo_token_proxy": null,
      "evidence_supported_counts": {
        "yes": 24
      },
      "current_conflict_unvalidated_counts": {
        "no": 24
      },
      "mean_context_serialized_utf8_bytes": 10849.083333333334,
      "duplicate_event_slots": 0,
      "positive_support_coverage": 0.8409090909090909
    },
    {
      "backend": "mem0_raw",
      "reader": "sol",
      "dataset": "longmemeval",
      "arm": "content_admission",
      "unique_questions": 12,
      "condition_observations": 24,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0.9166666666666666,
      "reader_failure_as_incorrect": 0.9166666666666666,
      "supported_task_available_case": 0.9166666666666666,
      "locomo_token_proxy": null,
      "evidence_supported_counts": {
        "yes": 24
      },
      "current_conflict_unvalidated_counts": {
        "no": 24
      },
      "mean_context_serialized_utf8_bytes": 10849.083333333334,
      "duplicate_event_slots": 0,
      "positive_support_coverage": 0.8409090909090909
    },
    {
      "backend": "mem0_raw",
      "reader": "sol",
      "dataset": "longmemeval",
      "arm": "event_admission",
      "unique_questions": 12,
      "condition_observations": 24,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0.9166666666666666,
      "reader_failure_as_incorrect": 0.9166666666666666,
      "supported_task_available_case": 0.9166666666666666,
      "locomo_token_proxy": null,
      "evidence_supported_counts": {
        "yes": 24
      },
      "current_conflict_unvalidated_counts": {
        "no": 24
      },
      "mean_context_serialized_utf8_bytes": 10849.083333333334,
      "duplicate_event_slots": 0,
      "positive_support_coverage": 0.8409090909090909
    },
    {
      "backend": "mem0_raw",
      "reader": "sol",
      "dataset": "longmemeval",
      "arm": "no_context",
      "unique_questions": 12,
      "condition_observations": 24,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0.08333333333333333,
      "reader_failure_as_incorrect": 0.08333333333333333,
      "supported_task_available_case": 0.08333333333333333,
      "locomo_token_proxy": null,
      "evidence_supported_counts": {
        "yes": 16,
        "uncertain": 8
      },
      "current_conflict_unvalidated_counts": {
        "no": 24
      },
      "mean_context_serialized_utf8_bytes": 2,
      "duplicate_event_slots": 0,
      "positive_support_coverage": 0.0
    },
    {
      "backend": "mem0_raw",
      "reader": "sol",
      "dataset": "longmemeval",
      "arm": "oracle_support",
      "unique_questions": 12,
      "condition_observations": 24,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0.9166666666666666,
      "reader_failure_as_incorrect": 0.9166666666666666,
      "supported_task_available_case": 0.875,
      "locomo_token_proxy": null,
      "evidence_supported_counts": {
        "yes": 23,
        "uncertain": 1
      },
      "current_conflict_unvalidated_counts": {
        "no": 24
      },
      "mean_context_serialized_utf8_bytes": 747,
      "duplicate_event_slots": 0,
      "positive_support_coverage": 1.0
    },
    {
      "backend": "mem0_raw",
      "reader": "sol",
      "dataset": "longmemeval",
      "arm": "read_event_dedup",
      "unique_questions": 12,
      "condition_observations": 24,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0.9166666666666666,
      "reader_failure_as_incorrect": 0.9166666666666666,
      "supported_task_available_case": 0.9166666666666666,
      "locomo_token_proxy": null,
      "evidence_supported_counts": {
        "yes": 24
      },
      "current_conflict_unvalidated_counts": {
        "no": 24
      },
      "mean_context_serialized_utf8_bytes": 10647.083333333334,
      "duplicate_event_slots": 0,
      "positive_support_coverage": 0.8409090909090909
    },
    {
      "backend": "mem0_raw",
      "reader": "sol",
      "dataset": "longmemeval",
      "arm": "retry",
      "unique_questions": 12,
      "condition_observations": 24,
      "missing_reader": 0,
      "missing_grade": 0,
      "task_correct_available_case": 0.9166666666666666,
      "reader_failure_as_incorrect": 0.9166666666666666,
      "supported_task_available_case": 0.9166666666666666,
      "locomo_token_proxy": null,
      "evidence_supported_counts": {
        "yes": 24
      },
      "current_conflict_unvalidated_counts": {
        "no": 24
      },
      "mean_context_serialized_utf8_bytes": 10423.666666666666,
      "duplicate_event_slots": 2.3333333333333335,
      "positive_support_coverage": 0.8409090909090909
    }
  ],
  "paired": [
    {
      "backend": "mem0_raw",
      "reader": "sol",
      "dataset": "locomo",
      "arm": "retry",
      "unique_questions_with_paired_grades": 12,
      "mean_paired_task_difference": -0.08333333333333333,
      "dependent_question_repeat_transitions": {
        "1_to_1": 18,
        "0_to_0": 4,
        "1_to_0": 2
      }
    },
    {
      "backend": "mem0_raw",
      "reader": "sol",
      "dataset": "locomo",
      "arm": "event_admission",
      "unique_questions_with_paired_grades": 12,
      "mean_paired_task_difference": 0,
      "dependent_question_repeat_transitions": {
        "1_to_1": 20,
        "0_to_0": 4
      }
    },
    {
      "backend": "mem0_raw",
      "reader": "sol",
      "dataset": "locomo",
      "arm": "content_admission",
      "unique_questions_with_paired_grades": 12,
      "mean_paired_task_difference": 0,
      "dependent_question_repeat_transitions": {
        "1_to_1": 20,
        "0_to_0": 4
      }
    },
    {
      "backend": "mem0_raw",
      "reader": "sol",
      "dataset": "locomo",
      "arm": "read_event_dedup",
      "unique_questions_with_paired_grades": 12,
      "mean_paired_task_difference": 0,
      "dependent_question_repeat_transitions": {
        "1_to_1": 20,
        "0_to_0": 4
      }
    },
    {
      "backend": "mem0_raw",
      "reader": "sol",
      "dataset": "longmemeval",
      "arm": "retry",
      "unique_questions_with_paired_grades": 12,
      "mean_paired_task_difference": 0,
      "dependent_question_repeat_transitions": {
        "1_to_1": 22,
        "0_to_0": 2
      }
    },
    {
      "backend": "mem0_raw",
      "reader": "sol",
      "dataset": "longmemeval",
      "arm": "event_admission",
      "unique_questions_with_paired_grades": 12,
      "mean_paired_task_difference": 0,
      "dependent_question_repeat_transitions": {
        "1_to_1": 22,
        "0_to_0": 2
      }
    },
    {
      "backend": "mem0_raw",
      "reader": "sol",
      "dataset": "longmemeval",
      "arm": "content_admission",
      "unique_questions_with_paired_grades": 12,
      "mean_paired_task_difference": 0,
      "dependent_question_repeat_transitions": {
        "1_to_1": 22,
        "0_to_0": 2
      }
    },
    {
      "backend": "mem0_raw",
      "reader": "sol",
      "dataset": "longmemeval",
      "arm": "read_event_dedup",
      "unique_questions_with_paired_grades": 12,
      "mean_paired_task_difference": 0,
      "dependent_question_repeat_transitions": {
        "1_to_1": 22,
        "0_to_0": 2
      }
    },
    {
      "backend": "mem0_raw",
      "reader": "qwen",
      "dataset": "locomo",
      "arm": "retry",
      "unique_questions_with_paired_grades": 12,
      "mean_paired_task_difference": 0,
      "dependent_question_repeat_transitions": {
        "1_to_1": 8,
        "0_to_0": 4
      }
    },
    {
      "backend": "mem0_raw",
      "reader": "qwen",
      "dataset": "locomo",
      "arm": "event_admission",
      "unique_questions_with_paired_grades": 12,
      "mean_paired_task_difference": 0,
      "dependent_question_repeat_transitions": {
        "1_to_1": 8,
        "0_to_0": 4
      }
    },
    {
      "backend": "mem0_raw",
      "reader": "qwen",
      "dataset": "locomo",
      "arm": "content_admission",
      "unique_questions_with_paired_grades": 12,
      "mean_paired_task_difference": 0,
      "dependent_question_repeat_transitions": {
        "1_to_1": 8,
        "0_to_0": 4
      }
    },
    {
      "backend": "mem0_raw",
      "reader": "qwen",
      "dataset": "locomo",
      "arm": "read_event_dedup",
      "unique_questions_with_paired_grades": 12,
      "mean_paired_task_difference": 0,
      "dependent_question_repeat_transitions": {
        "1_to_1": 8,
        "0_to_0": 4
      }
    },
    {
      "backend": "mem0_raw",
      "reader": "qwen",
      "dataset": "longmemeval",
      "arm": "retry",
      "unique_questions_with_paired_grades": 12,
      "mean_paired_task_difference": -0.08333333333333333,
      "dependent_question_repeat_transitions": {
        "0_to_0": 5,
        "1_to_1": 6,
        "1_to_0": 1
      }
    },
    {
      "backend": "mem0_raw",
      "reader": "qwen",
      "dataset": "longmemeval",
      "arm": "event_admission",
      "unique_questions_with_paired_grades": 12,
      "mean_paired_task_difference": 0,
      "dependent_question_repeat_transitions": {
        "0_to_0": 5,
        "1_to_1": 7
      }
    },
    {
      "backend": "mem0_raw",
      "reader": "qwen",
      "dataset": "longmemeval",
      "arm": "content_admission",
      "unique_questions_with_paired_grades": 12,
      "mean_paired_task_difference": 0,
      "dependent_question_repeat_transitions": {
        "0_to_0": 5,
        "1_to_1": 7
      }
    },
    {
      "backend": "mem0_raw",
      "reader": "qwen",
      "dataset": "longmemeval",
      "arm": "read_event_dedup",
      "unique_questions_with_paired_grades": 12,
      "mean_paired_task_difference": 0,
      "dependent_question_repeat_transitions": {
        "0_to_0": 5,
        "1_to_1": 7
      }
    },
    {
      "backend": "llama_index",
      "reader": "sol",
      "dataset": "locomo",
      "arm": "retry",
      "unique_questions_with_paired_grades": 12,
      "mean_paired_task_difference": -0.16666666666666666,
      "dependent_question_repeat_transitions": {
        "1_to_1": 10,
        "0_to_0": 10,
        "1_to_0": 4
      }
    },
    {
      "backend": "llama_index",
      "reader": "sol",
      "dataset": "locomo",
      "arm": "event_admission",
      "unique_questions_with_paired_grades": 12,
      "mean_paired_task_difference": 0,
      "dependent_question_repeat_transitions": {
        "1_to_1": 14,
        "0_to_0": 10
      }
    },
    {
      "backend": "llama_index",
      "reader": "sol",
      "dataset": "locomo",
      "arm": "content_admission",
      "unique_questions_with_paired_grades": 12,
      "mean_paired_task_difference": 0,
      "dependent_question_repeat_transitions": {
        "1_to_1": 14,
        "0_to_0": 10
      }
    },
    {
      "backend": "llama_index",
      "reader": "sol",
      "dataset": "locomo",
      "arm": "read_event_dedup",
      "unique_questions_with_paired_grades": 12,
      "mean_paired_task_difference": 0,
      "dependent_question_repeat_transitions": {
        "1_to_1": 14,
        "0_to_0": 10
      }
    },
    {
      "backend": "llama_index",
      "reader": "sol",
      "dataset": "longmemeval",
      "arm": "retry",
      "unique_questions_with_paired_grades": 12,
      "mean_paired_task_difference": -0.08333333333333333,
      "dependent_question_repeat_transitions": {
        "1_to_1": 20,
        "1_to_0": 2,
        "0_to_0": 2
      }
    },
    {
      "backend": "llama_index",
      "reader": "sol",
      "dataset": "longmemeval",
      "arm": "event_admission",
      "unique_questions_with_paired_grades": 12,
      "mean_paired_task_difference": 0,
      "dependent_question_repeat_transitions": {
        "1_to_1": 22,
        "0_to_0": 2
      }
    },
    {
      "backend": "llama_index",
      "reader": "sol",
      "dataset": "longmemeval",
      "arm": "content_admission",
      "unique_questions_with_paired_grades": 12,
      "mean_paired_task_difference": 0,
      "dependent_question_repeat_transitions": {
        "1_to_1": 22,
        "0_to_0": 2
      }
    },
    {
      "backend": "llama_index",
      "reader": "sol",
      "dataset": "longmemeval",
      "arm": "read_event_dedup",
      "unique_questions_with_paired_grades": 12,
      "mean_paired_task_difference": 0,
      "dependent_question_repeat_transitions": {
        "1_to_1": 22,
        "0_to_0": 2
      }
    },
    {
      "backend": "llama_index",
      "reader": "qwen",
      "dataset": "locomo",
      "arm": "retry",
      "unique_questions_with_paired_grades": 12,
      "mean_paired_task_difference": -0.08333333333333333,
      "dependent_question_repeat_transitions": {
        "1_to_1": 5,
        "0_to_0": 6,
        "1_to_0": 1
      }
    },
    {
      "backend": "llama_index",
      "reader": "qwen",
      "dataset": "locomo",
      "arm": "event_admission",
      "unique_questions_with_paired_grades": 12,
      "mean_paired_task_difference": 0,
      "dependent_question_repeat_transitions": {
        "1_to_1": 6,
        "0_to_0": 6
      }
    },
    {
      "backend": "llama_index",
      "reader": "qwen",
      "dataset": "locomo",
      "arm": "content_admission",
      "unique_questions_with_paired_grades": 12,
      "mean_paired_task_difference": 0,
      "dependent_question_repeat_transitions": {
        "1_to_1": 6,
        "0_to_0": 6
      }
    },
    {
      "backend": "llama_index",
      "reader": "qwen",
      "dataset": "locomo",
      "arm": "read_event_dedup",
      "unique_questions_with_paired_grades": 12,
      "mean_paired_task_difference": 0,
      "dependent_question_repeat_transitions": {
        "1_to_1": 6,
        "0_to_0": 6
      }
    },
    {
      "backend": "llama_index",
      "reader": "qwen",
      "dataset": "longmemeval",
      "arm": "retry",
      "unique_questions_with_paired_grades": 12,
      "mean_paired_task_difference": -0.08333333333333333,
      "dependent_question_repeat_transitions": {
        "0_to_0": 5,
        "1_to_0": 1,
        "1_to_1": 6
      }
    },
    {
      "backend": "llama_index",
      "reader": "qwen",
      "dataset": "longmemeval",
      "arm": "event_admission",
      "unique_questions_with_paired_grades": 12,
      "mean_paired_task_difference": 0,
      "dependent_question_repeat_transitions": {
        "0_to_0": 5,
        "1_to_1": 7
      }
    },
    {
      "backend": "llama_index",
      "reader": "qwen",
      "dataset": "longmemeval",
      "arm": "content_admission",
      "unique_questions_with_paired_grades": 12,
      "mean_paired_task_difference": 0,
      "dependent_question_repeat_transitions": {
        "0_to_0": 5,
        "1_to_1": 7
      }
    },
    {
      "backend": "llama_index",
      "reader": "qwen",
      "dataset": "longmemeval",
      "arm": "read_event_dedup",
      "unique_questions_with_paired_grades": 12,
      "mean_paired_task_difference": 0,
      "dependent_question_repeat_transitions": {
        "0_to_0": 5,
        "1_to_1": 7
      }
    }
  ],
  "clean_repeat_variation": [
    {
      "backend": "mem0_raw",
      "reader": "sol",
      "dataset": "locomo",
      "clean_repeat_task_transitions": {
        "1_to_1": 10,
        "0_to_0": 2
      }
    },
    {
      "backend": "mem0_raw",
      "reader": "sol",
      "dataset": "longmemeval",
      "clean_repeat_task_transitions": {
        "1_to_1": 11,
        "0_to_0": 1
      }
    },
    {
      "backend": "llama_index",
      "reader": "sol",
      "dataset": "locomo",
      "clean_repeat_task_transitions": {
        "1_to_1": 7,
        "0_to_0": 5
      }
    },
    {
      "backend": "llama_index",
      "reader": "sol",
      "dataset": "longmemeval",
      "clean_repeat_task_transitions": {
        "1_to_1": 11,
        "0_to_0": 1
      }
    }
  ],
  "native_metrics": "native_phase_metrics.json: application phase includes native persistence and study witness export; whole-process time includes startup. Pure query application latency was not separately recorded. Record-count deltas are not physical disk-write counts.",
  "token_metric_development_correction": {
    "reason": "The frozen proxy used stdlib re instead of upstream regex for article word boundaries. A separate corrected helper implements the intended published metric; frozen source and old proxy values are retained.",
    "provenance": {
      "analysis_version": "locomo-official-regex-v1",
      "official_repository": "https://github.com/snap-research/locomo",
      "official_commit": "3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376",
      "official_source_path": "task_eval/evaluation.py",
      "official_source_sha256": "8e3be5d57ff2ff9ec5cd05939592f468c5f3f1fd95d13e431932bdf6bf0fd6fd",
      "source_url": "https://github.com/snap-research/locomo/blob/3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376/task_eval/evaluation.py",
      "runtime_versions": {
        "regex": "2026.9.29",
        "nltk": "3.10.4",
        "numpy": "2.5.4"
      },
      "correction": "Use official regex article word boundaries; retain frozen-proxy scores and all model outputs separately.",
      "interpretation": "Category-specific published token overlap/abstention proxy, not semantic task accuracy."
    },
    "material_tolerance": 1e-12,
    "measured_material_differences": 0,
    "measured_bit_level_inequalities": 131,
    "maximum_absolute_difference": 1.1102230246251565e-16
  },
  "interpretation": "No p-values or population/IID interval; repetitions and shared-prompt aliases are dependent. Support annotations may be incomplete. Raw-document backends do not represent vendor inferred-memory defaults."
}
```

## 3. Qualitative and mechanistic interpretation

# Concrete findings and remaining limits

Aditya Mantri — independent research. This report extends the public working
study with a development pilot; it is not a journal acceptance claim, external
peer review or held-out confirmation.

## A directly inspectable answer failure

The released LongMemEval question asks how many of Emma's recipes the user has
tried. Its reference answer is **3**. The dated source history says **2** on
May 29 and **3** on May 30. With clean LlamaIndex retrieval, both Sol 6.1 and
Qwen answer **3**. After controlled delivery repetition, the selected context
has six duplicate event slots and omits the May 30 count; both readers answer
**2**. Every original stored record remains present and unchanged.

Sol produces the same clean-correct/retry-incorrect task transition in both
repeats. Source-event dedup restores the clean LlamaIndex prompt. Because the
complete prompt bytes are then identical, the protocol explicitly reuses the
archived clean response; this is input restoration, not a new recovery model
generation. The raw question key is `f65dcff812445376dbc709ef`.

## Finite-pilot task outcomes

All 447 distinct reader requests and all 75 grading batches completed. Those
responses map to 1,008 condition observations through documented prompt aliases.
They are not 1,008 independent questions. The underlying development set has
24 questions, with shared conversations and background sessions.

Automated task grading flags seven backend/reader/question loss combinations
across four underlying questions and eleven dependent repeat transitions.
It flags no gains in this task label. Retrieval-time event dedup restores the
clean task label in every flagged combination. Five LlamaIndex combinations
restore byte-identical clean prompts and reuse responses; two Mem0 combinations
use different dedup prompts and separately collected responses.

These labels remain **exploratory**. The authored calibration matched 12/12
task labels but only 10/12 current-conflict labels. The failed auxiliary gate
is retained; no definitive stale-state or semantic-efficacy claim follows.
Sol is a same-study judge, including of its own outputs, without human
adjudication. One Qwen out-of-context citation remains recorded.

The published LoCoMo token metric is reported separately. It does not uniformly
decrease: Qwen's Mem0 token score increases while its task labels are unchanged
on those LoCoMo questions. Token overlap, annotated support and semantic task
correctness measure different things. No significance test, population failure
rate or superiority of an elaborate repair is established.

## A second, mechanically verified layer

Visible duplicate removal need not restore the original ranking. It restores
all 24 dense LlamaIndex contexts here, but 16/24 Mem0 contexts retain different
event sets at the common returned-candidate budget. This comparison concerns
context identity, not a residual task loss: task labels still recover.

A separately frozen, explicitly post-hoc diagnostic repeats all 24 Mem0 queries
on copies of clean and replayed stores. With a full candidate pool, 10/24 selected
event sets and 17/24 event orders still differ after event dedup. Original-point
semantic scores and entity contributions remain stable; normalized BM25 and
final scores change in all 24 queries. All ten changed sets contain a strict
lost/gained score-order reversal, rather than only a tie-order change.

The pinned local Qdrant implementation computes inverse document frequency
from physical sparse-vector document counts:

`idf(t) = log(1 + (N - df(t) + 0.5) / (df(t) + 0.5))`.

Extra physical copies change `N` and term document frequencies although the
logical source-event set is unchanged. Mem0 combines semantic similarity with
query-normalized BM25 additively; the tested path is not reciprocal-rank fusion.
Mem0 internally over-fetches four times the requested limit. The full-pool
diagnostic removes that candidate truncation as an explanation of the residual.

In a second counterfactual, duplicate records remain searchable, but Qdrant's
native IDF corpus parameter uses the original clean physical IDs. All 24 full-pool
contexts and all original-point score components return to clean values within
the declared numerical tolerance. This is a mechanism diagnostic using known
clean IDs, not an oracle-free deployed method or a new IDF algorithm.

The independent auditor reconciles native payloads, point membership, score
equations and 12,320 original-point comparisons. The 120 diagnostic queries
reuse the same 24 questions; they are not additional task samples. See
`worker_review_ranking_audit.md` and the two post-hoc protocol directories.

## What is novel, and what is established

Duplicate documents distorting IDF and relevance ranking are established IR;
[Frieder, Grossman and Chowdhury (2003)](https://ir.cs.georgetown.edu/publications/downloads/NCA03-Keynote.pdf)
discuss this explicitly in section 2. Recent duplicate-evidence studies,
including CUE-R and Schelpe's byte-exact-deduplication study, are mandatory close
comparisons. The latter also studies an indexed high-redundancy corpus.

The candidate contribution is a reproducible **native delivery replay → stored
multiplicity → corpus-statistics drift/selection change → task outcome** trace,
with distinct storage, retrieval and answer contracts. It is a bounded systems
measurement and conformance contribution. New mathematical principles, first
discovery of duplicate harm, a novel deduplication algorithm, natural production
incidence and Q1 readiness are not established. The complete source-grounded
novelty assessment is in `literature/posthoc_ranking_probe_v1_audit/`.

The storage participants are local Mem0 `infer=False` and persisted raw-document
LlamaIndex. This does not reproduce inferred-memory defaults or managed services.
The recovery boundary is an actual worker exit after native effects but before
the study's logical batch acknowledgement, not a network-packet or mid-commit
failure. Full independent confirmation and external expert assessment remain
necessary before a strong journal submission claim.

## 4. Independent evidence and supporting scope

Storage audit:308 processes,84 actual expected worker exits,196 retained native stores,14320 original backend-event records,3840 replayed backend-events per delivery,11520 native candidate rows. Reader audit:447 physical responses,149 unique prompts,336 aliases and1008 dependent observations. Grading audit:75 primary batches,447 decisions,56 group summaries,32 paired contrasts and196 native application phases. The recipe latest count moves from native rank5 to rank11 while remaining physically present; retry context has six duplicate slots. Twelve physical response files underlie its21 condition observations.

First post-hoc ranking diagnostic:96 native queries on copies,24 reused questions. All48 K60 condition reproductions match retained physical order and scores. Full-pool results leave10 changed sets and17 changed event orders after dedup. All10 set changes include a strict lost/gained score-order reversal;23 questions have at least one strict original-point reversal. Second post-hoc fixed-IDF diagnostic:24 native queries, duplicates remain searchable, original clean physical IDs supply only IDF statistics through the native corpus parameter. All24 context orders and five score components restore across12320 original-point comparisons. This is an oracle mechanism diagnostic. The two probes provide120 technical queries and52740 audited rows, not120 new task samples. A separate raw sparse-dot-product reconstruction is not retained.

The Unicode correction is explicit and does not alter frozen generation/grade drivers or answers. The corrected metric matches205 official AST cases. Across504 measured LoCoMo aliases there are0 material differences at1e-12 and131 rounding-only inequalities, maximum1.11e-16. One physical Qwen invalid citation maps to four condition aliases and is retained. Sol raw CLI event streams are not archived; tool absence is checked against retained summaries.

The immutable v0.3.0 source at manuscript/main.tex and main.pdf provides older, separately denominated D/P/R and inferred-Mem0 experiments. It must remain unchanged because the new pilot pins its released PDF. The new manuscript belongs to revisions/benchmark_impact/manuscript. Older reruns are not extra benchmark observations. Research scope is independent public/newly authored data only.

The novelty audit in literature/posthoc_ranking_probe_v1_audit establishes direct classical duplicate/IDF antecedents and recent duplicated-evidence/indexed-corpus studies. Use those exact verified entries and preserve metadata conflicts. Candidate value is operational recovery-to-ranking and task conformance evidence; no first discovery, new transaction algorithm, novel IDF, production failure rate or Q1-readiness claim is supported.
