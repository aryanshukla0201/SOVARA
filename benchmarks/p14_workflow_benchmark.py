from __future__ import annotations

import json
import statistics
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
OUTPUT_DIR = Path("benchmarks/results/sovara-laptop-rtx5060/workflows")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MODEL = "phi4-mini:latest"
WORKLOAD = "simple_planning"

COLD_RUNS = 1
WARM_RUNS = 7

PROMPT = """
Analyze this task and produce a concise execution plan.

Task:
Design a secure local workflow for analyzing a confidential engineering document.

Requirements:
1. Keep confidential data local.
2. Identify the required processing steps.
3. Identify where verification should occur.
4. Return a concise ordered plan.
""".strip()


def gpu_sample():
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=utilization.gpu,memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )

        line = result.stdout.strip().splitlines()[0]
        util, used, total = [float(x.strip()) for x in line.split(",")]

        return util, used, total

    except Exception:
        return None, None, None


def resource_sample():
    import psutil

    gpu_util, gpu_used, gpu_total = gpu_sample()
    memory = psutil.virtual_memory()

    return {
        "timestamp": time.perf_counter(),
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "memory_used_mb": memory.used / (1024 * 1024),
        "memory_percent": memory.percent,
        "gpu_utilization_percent": gpu_util,
        "gpu_memory_used_mb": gpu_used,
        "gpu_memory_total_mb": gpu_total,
    }


def unload_model():
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "prompt": "",
            "stream": False,
            "keep_alive": 0,
        },
        timeout=60,
    )

    response.raise_for_status()


def run_once(iteration: int, phase: str):
    before = resource_sample()
    start = time.perf_counter()

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "prompt": PROMPT,
            "stream": False,
            "options": {
                "num_predict": 256,
                "temperature": 0.2,
                "top_p": 0.9,
                "top_k": 20,
                "repeat_penalty": 1.1,
            },
            "keep_alive": "30m",
        },
        timeout=180,
    )

    wall_ms = (time.perf_counter() - start) * 1000
    after = resource_sample()

    response.raise_for_status()
    data = response.json()

    eval_count = data.get("eval_count", 0)
    eval_duration_ns = data.get("eval_duration", 0)

    generation_tps = (
        eval_count / (eval_duration_ns / 1_000_000_000)
        if eval_duration_ns
        else None
    )

    return {
        "iteration": iteration,
        "phase": phase,
        "model": MODEL,
        "workload": WORKLOAD,
        "success": True,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "wall_duration_ms": wall_ms,
        "ollama_total_duration_ms": data.get("total_duration", 0) / 1_000_000,
        "ollama_load_duration_ms": data.get("load_duration", 0) / 1_000_000,
        "prompt_eval_duration_ms": data.get("prompt_eval_duration", 0) / 1_000_000,
        "eval_duration_ms": data.get("eval_duration", 0) / 1_000_000,
        "prompt_eval_count": data.get("prompt_eval_count"),
        "eval_count": eval_count,
        "generation_tps": generation_tps,
        "cpu_before_percent": before["cpu_percent"],
        "cpu_after_percent": after["cpu_percent"],
        "memory_before_mb": before["memory_used_mb"],
        "memory_after_mb": after["memory_used_mb"],
        "memory_before_percent": before["memory_percent"],
        "memory_after_percent": after["memory_percent"],
        "gpu_util_before_percent": before["gpu_utilization_percent"],
        "gpu_util_after_percent": after["gpu_utilization_percent"],
        "gpu_memory_before_mb": before["gpu_memory_used_mb"],
        "gpu_memory_after_mb": after["gpu_memory_used_mb"],
        "gpu_memory_total_mb": after["gpu_memory_total_mb"],
        "gpu_memory_delta_mb": (
            after["gpu_memory_used_mb"] - before["gpu_memory_used_mb"]
            if after["gpu_memory_used_mb"] is not None
            and before["gpu_memory_used_mb"] is not None
            else None
        ),
        "output_chars": len(data.get("response", "")),
    }


def percentile(values, percentile_value):
    if not values:
        return None

    ordered = sorted(values)

    if len(ordered) == 1:
        return ordered[0]

    position = (len(ordered) - 1) * (percentile_value / 100)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower

    return ordered[lower] + (ordered[upper] - ordered[lower]) * weight


def statistics_block(values):
    if not values:
        return {}

    return {
        "count": len(values),
        "min": min(values),
        "max": max(values),
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "p95": percentile(values, 95),
        "stddev": statistics.stdev(values) if len(values) > 1 else 0.0,
    }


def summarize(results, phase):
    phase_results = [
        result
        for result in results
        if result["phase"] == phase and result["success"]
    ]

    walls = [result["wall_duration_ms"] for result in phase_results]

    tps = [
        result["generation_tps"]
        for result in phase_results
        if result["generation_tps"] is not None
    ]

    load_times = [
        result["ollama_load_duration_ms"]
        for result in phase_results
    ]

    gpu_deltas = [
        result["gpu_memory_delta_mb"]
        for result in phase_results
        if result["gpu_memory_delta_mb"] is not None
    ]

    return {
        "phase": phase,
        "statistics": {
            "wall_duration_ms": statistics_block(walls),
            "generation_tps": statistics_block(tps),
            "ollama_load_duration_ms": statistics_block(load_times),
            "gpu_memory_delta_mb": statistics_block(gpu_deltas),
        },
    }


def main():
    results = []

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    print("P14 workflow benchmark")
    print(f"Model: {MODEL}")
    print(f"Workload: {WORKLOAD}")
    print(f"Cold runs: {COLD_RUNS}")
    print(f"Warm runs: {WARM_RUNS}")
    print(f"Run ID: {run_id}")
    print()

    for iteration in range(1, COLD_RUNS + 1):
        print(f"Running cold iteration {iteration}/{COLD_RUNS}...")

        unload_model()

        result = run_once(iteration, "cold")
        results.append(result)

        print(
            f"  wall={result['wall_duration_ms']:.1f} ms | "
            f"load={result['ollama_load_duration_ms']:.1f} ms | "
            f"TPS={result['generation_tps']:.2f}"
        )

    for iteration in range(1, WARM_RUNS + 1):
        print(f"Running warm iteration {iteration}/{WARM_RUNS}...")

        result = run_once(iteration, "warm")
        results.append(result)

        print(
            f"  wall={result['wall_duration_ms']:.1f} ms | "
            f"TPS={result['generation_tps']:.2f}"
        )

    summary = {
        "run_id": run_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "model": MODEL,
        "workload": WORKLOAD,
        "configuration": {
            "cold_runs": COLD_RUNS,
            "warm_runs": WARM_RUNS,
            "num_predict": 256,
            "temperature": 0.2,
            "top_p": 0.9,
            "top_k": 20,
            "repeat_penalty": 1.1,
            "keep_alive": "30m",
        },
        "cold": summarize(results, "cold"),
        "warm": summarize(results, "warm"),
        "runs": results,
    }

    output = OUTPUT_DIR / f"{WORKLOAD}_{MODEL.replace(':', '_')}_{run_id}.json"

    output.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    latest = OUTPUT_DIR / f"{WORKLOAD}_{MODEL.replace(':', '_')}_latest.json"

    latest.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    print()
    print("PASS")
    print(f"Raw benchmark: {output}")
    print(f"Latest pointer: {latest}")


if __name__ == "__main__":
    main()