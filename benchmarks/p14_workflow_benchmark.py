from __future__ import annotations

import json
import statistics
import subprocess
import time
from pathlib import Path

import requests

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
OUTPUT_DIR = Path("benchmarks/results/sovara-laptop-rtx5060/workflows")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MODEL = "phi4-mini:latest"

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


def run_once(iteration: int):
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
        "model": MODEL,
        "workload": "simple_planning",
        "success": True,
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
        "gpu_util_before_percent": before["gpu_utilization_percent"],
        "gpu_util_after_percent": after["gpu_utilization_percent"],
        "gpu_memory_before_mb": before["gpu_memory_used_mb"],
        "gpu_memory_after_mb": after["gpu_memory_used_mb"],
        "gpu_memory_total_mb": after["gpu_memory_total_mb"],
        "output_chars": len(data.get("response", "")),
    }


def main():
    results = []

    print("P14 workflow benchmark")
    print(f"Model: {MODEL}")
    print("Workload: simple_planning")
    print()

    for iteration in range(1, 4):
        print(f"Running iteration {iteration}/3...")
        result = run_once(iteration)
        results.append(result)

        print(
            f"  wall={result['wall_duration_ms']:.1f} ms | "
            f"TPS={result['generation_tps']:.2f} | "
            f"eval_tokens={result['eval_count']}"
        )

    walls = [r["wall_duration_ms"] for r in results]
    tps = [r["generation_tps"] for r in results if r["generation_tps"]]

    summary = {
        "model": MODEL,
        "workload": "simple_planning",
        "iterations": len(results),
        "wall_duration_ms": {
            "min": min(walls),
            "max": max(walls),
            "mean": statistics.mean(walls),
            "median": statistics.median(walls),
        },
        "generation_tps": {
            "min": min(tps),
            "max": max(tps),
            "mean": statistics.mean(tps),
            "median": statistics.median(tps),
        },
        "runs": results,
    }

    output = OUTPUT_DIR / "simple_planning_phi4-mini.json"
    output.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print()
    print("PASS")
    print(f"Saved: {output}")


if __name__ == "__main__":
    main()