from __future__ import annotations

import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parent.parent
MACHINE_ID = "sovara-laptop-rtx5060"
OUTPUT_DIR = ROOT / "benchmarks" / "results" / MACHINE_ID / "models"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OLLAMA_URL = "http://127.0.0.1:11434"

MODELS = {
    "phi4-mini": "phi4-mini:latest",
    "qwen2.5-coder": "qwen2.5-coder:7b-instruct",
    "gemma3": "gemma3:4b-it-qat",
}

PROMPT = (
    "Explain in concise technical terms what a transformer attention mechanism "
    "does. Give exactly three numbered points and a one-sentence conclusion."
)

OPTIONS = {
    "num_predict": 128,
    "temperature": 0.2,
    "top_p": 0.9,
    "top_k": 20,
    "repeat_penalty": 1.1,
}


def unload(model: str) -> None:
    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": model,
            "prompt": "",
            "stream": False,
            "keep_alive": 0,
        },
        timeout=30,
    )
    response.raise_for_status()


def run_stream(model: str, run_type: str, iteration: int) -> dict:
    payload = {
        "model": model,
        "prompt": PROMPT,
        "stream": True,
        "keep_alive": "30m",
        "options": OPTIONS,
    }

    started = time.perf_counter()
    first_token_at = None
    chunks = []
    final_metrics = {}

    with requests.post(
        f"{OLLAMA_URL}/api/generate",
        json=payload,
        stream=True,
        timeout=300,
    ) as response:
        response.raise_for_status()

        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue

            event = json.loads(line)

            text = event.get("response", "")
            if text and first_token_at is None:
                first_token_at = time.perf_counter()

            if text:
                chunks.append(text)

            if event.get("done"):
                final_metrics = event

    finished = time.perf_counter()

    wall_ms = (finished - started) * 1000
    ttft_ms = (
        (first_token_at - started) * 1000
        if first_token_at is not None
        else None
    )

    eval_count = final_metrics.get("eval_count")
    eval_duration_ns = final_metrics.get("eval_duration")

    generation_tps = None
    if eval_count and eval_duration_ns:
        generation_tps = eval_count / (eval_duration_ns / 1_000_000_000)

    return {
        "machine_id": MACHINE_ID,
        "model": model,
        "run_type": run_type,
        "iteration": iteration,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "success": True,
        "wall_duration_ms": round(wall_ms, 3),
        "ttft_ms": round(ttft_ms, 3) if ttft_ms is not None else None,
        "generated_tokens": eval_count,
        "generation_tokens_per_second": (
            round(generation_tps, 3)
            if generation_tps is not None
            else None
        ),
        "ollama": {
            "total_duration_ns": final_metrics.get("total_duration"),
            "load_duration_ns": final_metrics.get("load_duration"),
            "prompt_eval_duration_ns": final_metrics.get("prompt_eval_duration"),
            "eval_duration_ns": final_metrics.get("eval_duration"),
            "prompt_eval_count": final_metrics.get("prompt_eval_count"),
            "eval_count": final_metrics.get("eval_count"),
        },
        "prompt_chars": len(PROMPT),
        "output_chars": sum(len(chunk) for chunk in chunks),
    }


def summarize(runs: list[dict]) -> dict:
    def values(key: str) -> list[float]:
        return [
            float(run[key])
            for run in runs
            if run.get(key) is not None
        ]

    def stats(key: str) -> dict:
        data = values(key)
        if not data:
            return {}

        ordered = sorted(data)
        p95_index = max(0, min(len(ordered) - 1, int(len(ordered) * 0.95) - 1))

        return {
            "count": len(data),
            "min": round(min(data), 3),
            "max": round(max(data), 3),
            "mean": round(statistics.mean(data), 3),
            "median": round(statistics.median(data), 3),
            "p95": round(ordered[p95_index], 3),
            "stddev": round(statistics.stdev(data), 3) if len(data) > 1 else 0.0,
        }

    return {
        "machine_id": MACHINE_ID,
        "model": runs[0]["model"],
        "measured_runs": len(runs),
        "wall_duration_ms": stats("wall_duration_ms"),
        "ttft_ms": stats("ttft_ms"),
        "generation_tokens_per_second": stats("generation_tokens_per_second"),
        "generated_tokens": stats("generated_tokens"),
    }


def main() -> None:
    all_results = []

    for key, model in MODELS.items():
        print(f"\n=== {key} ({model}) ===")

        # Explicit cold measurement.
        print("cold: unloading model...")
        unload(model)

        print("cold: measuring...")
        cold = run_stream(model, "cold", 1)
        all_results.append(cold)
        print(json.dumps(cold, indent=2))

        # Three warm measurements, matching the P11 comparison baseline.
        warm_runs = []

        for iteration in range(1, 4):
            print(f"warm {iteration}/3...")
            result = run_stream(model, "warm", iteration)
            warm_runs.append(result)
            all_results.append(result)
            print(
                f"  wall={result['wall_duration_ms']} ms | "
                f"ttft={result['ttft_ms']} ms | "
                f"tps={result['generation_tokens_per_second']}"
            )

        model_output = {
            "machine_id": MACHINE_ID,
            "model_key": key,
            "model": model,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "settings": OPTIONS,
            "prompt": PROMPT,
            "cold": cold,
            "warm": warm_runs,
            "warm_summary": summarize(warm_runs),
        }

        output_file = OUTPUT_DIR / f"{key.replace('.', '_')}.json"
        output_file.write_text(
            json.dumps(model_output, indent=2),
            encoding="utf-8",
        )

        print(f"SAVED: {output_file}")

    combined = OUTPUT_DIR / "p14_model_raw.json"
    combined.write_text(
        json.dumps(
            {
                "machine_id": MACHINE_ID,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "results": all_results,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"\nSAVED: {combined}")
    print("\nP14 MODEL BENCHMARK COMPLETE")


if __name__ == "__main__":
    main()
