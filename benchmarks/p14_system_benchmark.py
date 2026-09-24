from __future__ import annotations

import json
import platform
import statistics
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from p14_resource_sampler import sample


OUTPUT_DIR = Path("benchmarks/results/sovara-laptop-rtx5060/system")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DURATION_SECONDS = 60
SAMPLE_INTERVAL_SECONDS = 1.0


def percentile(values: list[float], percentile_value: float) -> float:
    if not values:
        return 0.0

    ordered = sorted(values)

    if len(ordered) == 1:
        return ordered[0]

    rank = (len(ordered) - 1) * percentile_value / 100
    lower = int(rank)
    upper = min(lower + 1, len(ordered))
    weight = rank - lower

    return ordered[lower] + (ordered[upper] - ordered[lower]) * weight


def statistics_block(values: list[float]) -> dict[str, float | int]:
    if not values:
        return {
            "count": 0,
            "min": 0.0,
            "max": 0.0,
            "mean": 0.0,
            "median": 0.0,
            "p95": 0.0,
            "stddev": 0.0,
        }

    return {
        "count": len(values),
        "min": min(values),
        "max": max(values),
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "p95": percentile(values, 95),
        "stddev": statistics.stdev(values) if len(values) > 1 else 0.0,
    }


def git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
        return result.stdout.strip()
    except Exception:
        return None


def machine_identity() -> dict:
    gpu_name = None
    gpu_total_mb = None

    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )

        line = result.stdout.strip().splitlines()[0]
        name, total = [x.strip() for x in line.split(",")]
        gpu_name = name
        gpu_total_mb = float(total)
    except Exception:
        pass

    import psutil

    return {
        "machine_id": "sovara-laptop-rtx5060",
        "hostname": platform.node(),
        "os": platform.platform(),
        "python": platform.python_version(),
        "cpu": platform.processor(),
        "logical_cpus": psutil.cpu_count(logical=True),
        "physical_cpus": psutil.cpu_count(logical=False),
        "ram_mb": round(psutil.virtual_memory().total / (1024 * 1024)),
        "gpu": gpu_name,
        "gpu_vram_mb": gpu_total_mb,
        "git_commit": git_commit(),
    }


def main() -> None:
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    print("P14 system/resource benchmark")
    print(f"Run ID: {run_id}")
    print(f"Duration: {DURATION_SECONDS}s")
    print(f"Sampling interval: {SAMPLE_INTERVAL_SECONDS}s")
    print()

    samples = []

    start = time.perf_counter()
    next_sample = start

    while time.perf_counter() - start < DURATION_SECONDS:
        current = sample()
        samples.append(current)

        elapsed = time.perf_counter() - start
        print(
            f"[{elapsed:6.1f}s] "
            f"CPU={current.cpu_percent:5.1f}% "
            f"RAM={current.memory_percent:5.1f}% "
            f"GPU={current.gpu_utilization_percent if current.gpu_utilization_percent is not None else 'NA'}% "
            f"VRAM={current.gpu_memory_used_mb if current.gpu_memory_used_mb is not None else 'NA'}MB"
        )

        next_sample += SAMPLE_INTERVAL_SECONDS
        sleep_for = next_sample - time.perf_counter()

        if sleep_for > 0:
            time.sleep(sleep_for)

    cpu_values = [x.cpu_percent for x in samples]
    memory_values = [x.memory_percent for x in samples]

    gpu_util_values = [
        x.gpu_utilization_percent
        for x in samples
        if x.gpu_utilization_percent is not None
    ]

    gpu_memory_values = [
        x.gpu_memory_used_mb
        for x in samples
        if x.gpu_memory_used_mb is not None
    ]

    result = {
        "run_id": run_id,
        "benchmark": "p14_system_resource",
        "machine": machine_identity(),
        "configuration": {
            "duration_seconds": DURATION_SECONDS,
            "sample_interval_seconds": SAMPLE_INTERVAL_SECONDS,
            "sample_count": len(samples),
        },
        "statistics": {
            "cpu_percent": statistics_block(cpu_values),
            "memory_percent": statistics_block(memory_values),
            "gpu_utilization_percent": statistics_block(gpu_util_values),
            "gpu_memory_used_mb": statistics_block(gpu_memory_values),
        },
        "resource_summary": {
            "cpu_peak_percent": max(cpu_values) if cpu_values else None,
            "memory_peak_percent": max(memory_values) if memory_values else None,
            "gpu_utilization_peak_percent": (
                max(gpu_util_values) if gpu_util_values else None
            ),
            "gpu_memory_baseline_mb": gpu_memory_values[0]
            if gpu_memory_values
            else None,
            "gpu_memory_peak_mb": max(gpu_memory_values)
            if gpu_memory_values
            else None,
            "gpu_memory_delta_mb": (
                max(gpu_memory_values) - gpu_memory_values[0]
                if gpu_memory_values
                else None
            ),
        },
        "samples": [
            {
                "timestamp": item.timestamp,
                "cpu_percent": item.cpu_percent,
                "memory_used_mb": item.memory_used_mb,
                "memory_percent": item.memory_percent,
                "gpu_utilization_percent": item.gpu_utilization_percent,
                "gpu_memory_used_mb": item.gpu_memory_used_mb,
                "gpu_memory_total_mb": item.gpu_memory_total_mb,
            }
            for item in samples
        ],
    }

    output_path = OUTPUT_DIR / f"p14_system_{run_id}.json"

    output_path.write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )

    print()
    print(f"Samples: {len(samples)}")
    print(f"CPU mean: {statistics.mean(cpu_values):.2f}%")
    print(f"RAM mean: {statistics.mean(memory_values):.2f}%")

    if gpu_util_values:
        print(f"GPU utilization mean: {statistics.mean(gpu_util_values):.2f}%")

    if gpu_memory_values:
        print(
            f"VRAM baseline: {gpu_memory_values[0]:.0f} MB | "
            f"peak: {max(gpu_memory_values):.0f} MB | "
            f"delta: {max(gpu_memory_values) - gpu_memory_values[0]:.0f} MB"
        )

    print(f"Artifact: {output_path}")


if __name__ == "__main__":
    main()