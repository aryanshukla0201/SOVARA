from __future__ import annotations

import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from app.api.routes import run_multimodal_analysis


MACHINE_ID = "sovara-laptop-rtx5060"
WORKLOAD = "e2e_simple_analysis"
TASK_COUNT = 4

QUERY = (
    "Explain in concise technical terms how transformer attention works. "
    "Give exactly three numbered points and a one-sentence conclusion."
)

OUTPUT_DIR = (
    Path("benchmarks")
    / "results"
    / MACHINE_ID
    / "workflows"
)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def run_task(task_index: int, mode: str) -> dict:
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
            "mode": mode,
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
            "mode": mode,
            "success": False,
            "failure_type": type(exc).__name__,
            "wall_duration_ms": wall_duration_ms,
            "verification_status": None,
            "llm_duration_ms": None,
            "llm_calls": None,
            "models_used": [],
            "error": str(exc),
        }


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


def run_sequential() -> tuple[list[dict], float]:
    results = []

    started = time.perf_counter()

    for i in range(TASK_COUNT):
        results.append(run_task(i + 1, "sequential"))

    batch_wall_ms = (time.perf_counter() - started) * 1000

    return results, batch_wall_ms


def run_concurrent() -> tuple[list[dict], float]:
    results = []

    started = time.perf_counter()

    with ThreadPoolExecutor(max_workers=TASK_COUNT) as executor:
        futures = [
            executor.submit(run_task, i + 1, "concurrent")
            for i in range(TASK_COUNT)
        ]

        for future in as_completed(futures):
            results.append(future.result())

    batch_wall_ms = (time.perf_counter() - started) * 1000

    results.sort(key=lambda x: x["task_index"])

    return results, batch_wall_ms


def main() -> None:
    run_id = utc_timestamp()

    print("=" * 72)
    print("SOVARA P14 SEQUENTIAL VS CONCURRENT BENCHMARK")
    print("=" * 72)
    print(f"Machine: {MACHINE_ID}")
    print(f"Workload: {WORKLOAD}")
    print(f"Tasks: {TASK_COUNT}")
    print()

    print("[1/2] Running sequential...")
    sequential_results, sequential_batch_wall_ms = run_sequential()

    print(
        f"Sequential batch: "
        f"{sequential_batch_wall_ms:.2f} ms"
    )

    print()
    print("[2/2] Running concurrent...")
    concurrent_results, concurrent_batch_wall_ms = run_concurrent()

    print(
        f"Concurrent batch: "
        f"{concurrent_batch_wall_ms:.2f} ms"
    )

    sequential_task_times = [
        r["wall_duration_ms"]
        for r in sequential_results
    ]

    concurrent_task_times = [
        r["wall_duration_ms"]
        for r in concurrent_results
    ]

    sequential_success = sum(
        1 for r in sequential_results if r["success"]
    )

    concurrent_success = sum(
        1 for r in concurrent_results if r["success"]
    )

    speedup = (
        sequential_batch_wall_ms / concurrent_batch_wall_ms
        if concurrent_batch_wall_ms > 0
        else None
    )

    result = {
        "run_id": run_id,
        "machine_id": MACHINE_ID,
        "workload": WORKLOAD,
        "task_count": TASK_COUNT,
        "query": QUERY,
        "comparison": {
            "sequential_batch_wall_ms": sequential_batch_wall_ms,
            "concurrent_batch_wall_ms": concurrent_batch_wall_ms,
            "batch_speedup": speedup,
        },
        "sequential": {
            "success_count": sequential_success,
            "failure_count": TASK_COUNT - sequential_success,
            "task_wall_stats_ms": stats(sequential_task_times),
            "results": sequential_results,
        },
        "concurrent": {
            "success_count": concurrent_success,
            "failure_count": TASK_COUNT - concurrent_success,
            "task_wall_stats_ms": stats(concurrent_task_times),
            "results": concurrent_results,
        },
        "raw_runs": sequential_results + concurrent_results,
    }

    timestamped = (
        OUTPUT_DIR
        / f"sequential_vs_concurrent_{run_id}.json"
    )

    latest = (
        OUTPUT_DIR
        / "sequential_vs_concurrent_latest.json"
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
    print(f"Sequential: {sequential_batch_wall_ms:.2f} ms")
    print(f"Concurrent: {concurrent_batch_wall_ms:.2f} ms")

    if speedup is not None:
        print(f"Batch speedup: {speedup:.2f}x")

    print(
        f"Sequential success: "
        f"{sequential_success}/{TASK_COUNT}"
    )
    print(
        f"Concurrent success: "
        f"{concurrent_success}/{TASK_COUNT}"
    )

    print()
    print(f"Artifact: {timestamped}")
    print(f"Latest:   {latest}")


if __name__ == "__main__":
    main()
