from __future__ import annotations

import json
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from app.api.routes import run_multimodal_analysis
from benchmarks.p14_resource_sampler import sample


MACHINE_ID = "sovara-laptop-rtx5060"
WORKLOAD = "e2e_concurrent_resource_load"
TASK_COUNT = 4
SAMPLE_INTERVAL_SEC = 1.0

QUERY = (
    "Explain in concise technical terms how transformer attention works. "
    "Give exactly three numbered points and a one-sentence conclusion."
)

OUTPUT_DIR = (
    Path("benchmarks")
    / "results"
    / MACHINE_ID
    / "system"
)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def run_task(task_index: int) -> dict:
    started = time.perf_counter()

    try:
        result = run_multimodal_analysis(
            user_query=QUERY,
            files=[],
            requested_deliverable=None,
            conversation_id=None,
            task_id=None,
        )

        wall_duration_ms = (time.perf_counter() - started) * 1000

        verification_status_raw = (
            result.get("verification_status")
            if result is not None
            else None
        )

        verification_status = getattr(
            verification_status_raw,
            "value",
            verification_status_raw,
        )

        success = (
            result is not None
            and str(verification_status).lower() == "passed"
        )

        telemetry = (
            result.get("execution_telemetry", {})
            if result
            else {}
        )

        return {
            "task_index": task_index,
            "success": success,
            "failure_type": None if success else "verification_failure",
            "wall_duration_ms": wall_duration_ms,
            "verification_status": verification_status,
            "llm_duration_ms": (
                telemetry.get("llm_total_duration_ms")
                if telemetry.get("llm_total_duration_ms", 0.0) > 0
                else None
            ),
            "llm_calls": telemetry.get("llm_calls"),
            "models_used": telemetry.get("models_used", []),
        }

    except Exception as exc:
        wall_duration_ms = (time.perf_counter() - started) * 1000

        return {
            "task_index": task_index,
            "success": False,
            "failure_type": type(exc).__name__,
            "wall_duration_ms": wall_duration_ms,
            "verification_status": None,
            "llm_duration_ms": None,
            "llm_calls": None,
            "models_used": [],
            "error": str(exc),
        }


def collect_resources(
    samples: list,
    stop_event: threading.Event,
) -> None:
    while not stop_event.is_set():
        samples.append(sample())
        stop_event.wait(SAMPLE_INTERVAL_SEC)


def stats(values: list[float]) -> dict | None:
    if not values:
        return None

    values = sorted(values)
    n = len(values)

    def percentile(p: float) -> float:
        if n == 1:
            return values[0]

        k = (n - 1) * p
        f = int(k)
        c = min(f + 1, n - 1)

        if f == c:
            return values[f]

        return values[f] + (values[c] - values[f]) * (k - f)

    mean = statistics.mean(values)

    return {
        "count": n,
        "min": values[0],
        "max": values[-1],
        "mean": mean,
        "median": statistics.median(values),
        "p95": percentile(0.95),
        "stddev": statistics.pstdev(values),
    }


def serialize_sample(item) -> dict:
    return {
        "timestamp": item.timestamp,
        "cpu_percent": item.cpu_percent,
        "memory_used_mb": item.memory_used_mb,
        "memory_percent": item.memory_percent,
        "gpu_utilization_percent": item.gpu_utilization_percent,
        "gpu_memory_used_mb": item.gpu_memory_used_mb,
        "gpu_memory_total_mb": item.gpu_memory_total_mb,
    }


def main() -> None:
    run_id = utc_timestamp()

    print("=" * 72)
    print("SOVARA P14 RESOURCE UTILIZATION UNDER CONCURRENT LOAD")
    print("=" * 72)
    print(f"Machine: {MACHINE_ID}")
    print(f"Workload: {WORKLOAD}")
    print(f"Concurrent tasks: {TASK_COUNT}")
    print(f"Sampling interval: {SAMPLE_INTERVAL_SEC}s")
    print()

    resource_samples = []
    stop_event = threading.Event()

    sampler_thread = threading.Thread(
        target=collect_resources,
        args=(resource_samples, stop_event),
        daemon=True,
    )

    print("[1/2] Starting resource sampler...")
    sampler_thread.start()

    print("[2/2] Running concurrent workload...")

    batch_started = time.perf_counter()

    results = []

    with ThreadPoolExecutor(max_workers=TASK_COUNT) as executor:
        futures = [
            executor.submit(run_task, i + 1)
            for i in range(TASK_COUNT)
        ]

        for future in as_completed(futures):
            results.append(future.result())

    batch_wall_ms = (time.perf_counter() - batch_started) * 1000

    stop_event.set()
    sampler_thread.join(timeout=2)

    results.sort(key=lambda x: x["task_index"])

    cpu_values = [
        s.cpu_percent
        for s in resource_samples
    ]

    memory_percent_values = [
        s.memory_percent
        for s in resource_samples
    ]

    memory_used_values = [
        s.memory_used_mb
        for s in resource_samples
    ]

    gpu_util_values = [
        s.gpu_utilization_percent
        for s in resource_samples
        if s.gpu_utilization_percent is not None
    ]

    gpu_memory_values = [
        s.gpu_memory_used_mb
        for s in resource_samples
        if s.gpu_memory_used_mb is not None
    ]

    gpu_memory_total_values = [
        s.gpu_memory_total_mb
        for s in resource_samples
        if s.gpu_memory_total_mb is not None
    ]

    success_count = sum(
        1 for r in results if r["success"]
    )

    baseline_gpu_memory = (
        gpu_memory_values[0]
        if gpu_memory_values
        else None
    )

    peak_gpu_memory = (
        max(gpu_memory_values)
        if gpu_memory_values
        else None
    )

    result = {
        "run_id": run_id,
        "machine_id": MACHINE_ID,
        "workload": WORKLOAD,
        "task_count": TASK_COUNT,
        "sample_interval_sec": SAMPLE_INTERVAL_SEC,
        "batch_wall_duration_ms": batch_wall_ms,
        "success_count": success_count,
        "failure_count": TASK_COUNT - success_count,
        "resource_summary": {
            "sample_count": len(resource_samples),
            "cpu_percent": stats(cpu_values),
            "memory_used_mb": stats(memory_used_values),
            "memory_percent": stats(memory_percent_values),
            "gpu_utilization_percent": stats(gpu_util_values),
            "gpu_memory_used_mb": stats(gpu_memory_values),
            "gpu_memory_baseline_mb": baseline_gpu_memory,
            "gpu_memory_peak_mb": peak_gpu_memory,
            "gpu_memory_delta_mb": (
                peak_gpu_memory - baseline_gpu_memory
                if peak_gpu_memory is not None
                and baseline_gpu_memory is not None
                else None
            ),
            "gpu_memory_total_mb": (
                gpu_memory_total_values[-1]
                if gpu_memory_total_values
                else None
            ),
        },
        "task_results": results,
        "resource_samples": [
            serialize_sample(s)
            for s in resource_samples
        ],
    }

    timestamped = (
        OUTPUT_DIR
        / f"p14_concurrent_load_{run_id}.json"
    )

    latest = (
        OUTPUT_DIR
        / "p14_concurrent_load_latest.json"
    )

    payload = json.dumps(
        result,
        indent=2,
        default=str,
    )

    timestamped.write_text(payload, encoding="utf-8")
    latest.write_text(payload, encoding="utf-8")

    print()
    print("=" * 72)
    print("RESULT")
    print("=" * 72)
    print(f"Batch wall time: {batch_wall_ms:.2f} ms")
    print(f"Success: {success_count}/{TASK_COUNT}")
    print(f"Samples: {len(resource_samples)}")

    if cpu_values:
        print(
            f"CPU mean/peak: "
            f"{statistics.mean(cpu_values):.2f}% / "
            f"{max(cpu_values):.2f}%"
        )

    if memory_percent_values:
        print(
            f"RAM mean/peak: "
            f"{statistics.mean(memory_percent_values):.2f}% / "
            f"{max(memory_percent_values):.2f}%"
        )

    if gpu_util_values:
        print(
            f"GPU utilization mean/peak: "
            f"{statistics.mean(gpu_util_values):.2f}% / "
            f"{max(gpu_util_values):.2f}%"
        )

    if gpu_memory_values:
        print(
            f"VRAM baseline/peak: "
            f"{baseline_gpu_memory:.0f} / "
            f"{peak_gpu_memory:.0f} MB"
        )

    print()
    print(f"Artifact: {timestamped}")
    print(f"Latest:   {latest}")


if __name__ == "__main__":
    main()
