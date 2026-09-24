# SOVARA P14 Benchmark Contract

## Purpose

P14 measures SOVARA performance across the development laptop and HP Z4 G5
deployment/benchmark machine using the same workloads, model settings,
iteration counts, and measurement definitions.

## Machine Identity

Every benchmark result MUST identify:

- machine_id
- hostname
- operating_system
- cpu
- gpu
- gpu_memory_gb
- system_memory_gb
- python_version
- sovara_git_commit
- benchmark_timestamp

## Model Metrics

For every model benchmark:

- model
- workload
- run_type: cold | warm
- iteration
- wall_duration_ms
- ollama_total_duration_ms
- load_duration_ms
- prompt_eval_duration_ms
- eval_duration_ms
- prompt_eval_count
- eval_count
- generation_tokens_per_second
- success

## Streaming Metrics

Where streaming is tested:

- time_to_first_token_ms
- total_stream_duration_ms
- generated_tokens
- generation_tokens_per_second

TTFT is measured from benchmark request start until the first non-empty
generated chunk is received.

## System Metrics

Where supported:

- cpu_percent
- memory_used_mb
- memory_percent
- gpu_memory_used_mb
- gpu_memory_total_mb
- gpu_utilization_percent

## Workflow Metrics

For end-to-end SOVARA workloads:

- workload
- iteration
- wall_duration_ms
- llm_duration_ms
- planner_duration_ms
- retrieval_duration_ms
- tool_duration_ms
- verification_duration_ms
- sandbox_duration_ms
- success
- failure_type

## Statistical Reporting

For repeated measurements report:

- count
- minimum
- maximum
- mean
- median
- p95
- standard deviation

Never report a single run as a performance baseline.

## Required Comparisons

P14 MUST compare:

1. Cold vs warm model execution
2. Laptop vs HP Z4 G5
3. P14 model throughput vs P11 baseline
4. End-to-end workflow latency
5. Sequential vs concurrent execution
6. Resource utilization under load

## Benchmark Rules

- Same prompts across machines.
- Same model versions across machines.
- Same generation parameters.
- Same number of iterations.
- Warmup runs are excluded from measured statistics.
- Cold runs explicitly unload the model before measurement.
- No unrelated workloads during measurement.
- No architecture changes based on a single measurement.
- Every optimization must be followed by a repeat benchmark.
- Raw results are preserved.
- Results from different machines MUST NOT be mixed into one raw dataset.

## Output

Raw results:

    benchmarks/results/<machine_id>/

Derived reports:

    benchmarks/results/<machine_id>/summary.json

Human-readable report:

    benchmarks/results/<machine_id>/report.md
