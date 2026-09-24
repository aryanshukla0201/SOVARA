from __future__ import annotations

import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from app.models.gateway import ModelGateway

from app.api.routes import run_multimodal_analysis


MACHINE_ID = "sovara-laptop-rtx5060"
WORKLOAD = "e2e_simple_analysis"
COLD_RUNS = 1
WARM_RUNS = 7

QUERY = (
    "Explain in concise technical terms how transformer attention works. "
    "Give exactly three numbered points and a one-sentence conclusion."
)

RESULT_DIR = (
    Path("benchmarks")
    / "results"
    / MACHINE_ID
    / "workflows"
)
RESULT_DIR.mkdir(parents=True, exist_ok=True)

def stats(values):
    values = [v for v in values if v is not None]

    if not values:
        return None

    values = sorted(values)
    n = len(values)

    def percentile(p):
        if n == 1:
            return values[0]

        k = (n - 1) * p
        f = int(k)
        c = min(f + 1, n - 1)

        if f == c:
            return values[f]

        return values[f] + (values[c] - values[f]) * (k - f)

    mean = sum(values) / n
    variance = sum((x - mean) ** 2 for x in values) / n

    return {
        "count": n,
        "min": values[0],
        "max": values[-1],
        "mean": mean,
        "median": values[n // 2] if n % 2 else (
            values[n // 2 - 1] + values[n // 2]
        ) / 2,
        "p95": percentile(0.95),
        "stddev": variance ** 0.5,
    }


def run_once(iteration: int, phase: str) -> dict[str, Any]:
    started = time.perf_counter()

    result: dict[str, Any] | None = None
    error: str | None = None

    try:
        result = run_multimodal_analysis(
            user_query=QUERY,
            files=[],
            requested_deliverable=None,
            conversation_id=None,
            task_id=None,
        )
        verification_status_raw = (
            result.get("verification_status")
            if result is not None
            else None
        )

        verification_status_normalized = (
            getattr(
                verification_status_raw,
                "value",
                verification_status_raw,
            )
        )

        success = (
            result is not None
            and str(verification_status_normalized).lower() == "passed"
        )
    except Exception as exc:
        success = False
        error = f"{type(exc).__name__}: {exc}"

    wall_duration_ms = (
        time.perf_counter() - started
    ) * 1000

    telemetry = (
        result.get("execution_telemetry", {})
        if result
        else {}
    )

    verification_status = (
        result.get("verification_status")
        if result
        else None
    )

    verification_results = (
        result.get("verification_results", [])
        if result
        else []
    )

    failure_type = None

    if not success:
        failure_type = (
            type(error).__name__
            if error
            else "workflow_failure"
        )

    elif verification_status not in (None, "passed"):
        failure_type = "verification_failure"

    return {
        "iteration": iteration,
        "phase": phase,
        "timestamp_utc": datetime.now(
            timezone.utc
        ).isoformat(),

        "workload": WORKLOAD,
        "success": success,
        "failure_type": failure_type,

        "wall_duration_ms": wall_duration_ms,

        "llm_duration_ms": (
            telemetry.get("llm_total_duration_ms")
            if telemetry.get("llm_total_duration_ms", 0.0) > 0
            else None
        ),
        "llm_calls": telemetry.get("llm_calls"),

        "sandbox_duration_ms": sum(
            event.get("duration_ms", 0.0) or 0.0
            for event in telemetry.get(
                "execution_events", []
            )
            if event.get("type") == "sandbox_execution"
        ),

        "sandbox_executions": telemetry.get(
            "sandbox_executions"
        ),

        "tools_used": telemetry.get(
            "tools_used", []
        ),

        "models_used": telemetry.get(
            "models_used", []
        ),

        "verification_status": verification_status,

        "verification_result_count": len(
            verification_results
        ),

        "external_api_calls": telemetry.get(
            "external_api_calls"
        ),

        "network_calls": telemetry.get(
            "network_calls"
        ),

        "cloud_uploads": telemetry.get(
            "cloud_uploads"
        ),

        "no_external_calls": telemetry.get(
            "no_external_calls"
        ),

        "request_id": (
            result.get("request_id")
            if result
            else None
        ),

        "task_id": (
            result.get("task_id")
            if result
            else None
        ),

        "traceability": (
            result.get("traceability", [])
            if result
            else []
        ),

        "raw_result": result,
        "error": error,
    }


def main() -> None:
    timestamp = datetime.now(
        timezone.utc
    ).strftime("%Y%m%dT%H%M%SZ")

    print("=" * 72)
    print("SOVARA P14 E2E WORKFLOW BENCHMARK")
    print("=" * 72)
    print(f"workload: {WORKLOAD}")
    print(f"cold runs: {COLD_RUNS}")
    print(f"warm runs: {WARM_RUNS}")
    print()

    runs: list[dict[str, Any]] = []

    print("[1/8] COLD RUN")

    # Ensure the cold run starts with the production reasoning model unloaded.
    ModelGateway().resolve("reasoning").unload()

    cold = run_once(
        iteration=1,
        phase="cold",
    )

    runs.append(cold)

    print(
        f"  success={cold['success']} "
        f"wall={cold['wall_duration_ms']:.2f} ms "
        f"llm={cold['llm_duration_ms']} ms "
        f"verification={cold['verification_status']}"
    )

    for iteration in range(1, WARM_RUNS + 1):
        print(
            f"[{iteration + 1}/8] WARM RUN {iteration}"
        )

        run = run_once(
            iteration=iteration,
            phase="warm",
        )

        runs.append(run)

        print(
            f"  success={run['success']} "
            f"wall={run['wall_duration_ms']:.2f} ms "
            f"llm={run['llm_duration_ms']} ms "
            f"verification={run['verification_status']}"
        )

    successful_runs = [
        run
        for run in runs
        if run["success"]
    ]

    warm_successful = [
        run
        for run in successful_runs
        if run["phase"] == "warm"
    ]

    summary = {
        "run_id": timestamp,
        "machine_id": MACHINE_ID,
        "workload": WORKLOAD,
        "query": QUERY,
        "configuration": {
            "cold_runs": COLD_RUNS,
            "warm_runs": WARM_RUNS,
            "requested_deliverable": None,
            "files": [],
        },

        "success_count": len(successful_runs),
        "failure_count": len(runs) - len(successful_runs),

        "cold": (
            {
                "wall_duration_ms": stats(
                    [
                        cold["wall_duration_ms"]
                    ]
                ),
                "llm_duration_ms": stats(
                    [
                        cold["llm_duration_ms"]
                    ]
                    if cold["llm_duration_ms"]
                    is not None
                    else []
                ),
            }
        ),

        "warm": {
            "wall_duration_ms": stats(
                [
                    run["wall_duration_ms"]
                    for run in warm_successful
                ]
            )
            if warm_successful
            else {},
            "llm_duration_ms": stats(
                [
                    run["llm_duration_ms"]
                    for run in warm_successful
                    if run["llm_duration_ms"]
                    is not None
                ]
            ),
        },

        "unsupported_contract_metrics": {
            "planner_duration_ms": None,
            "retrieval_duration_ms": None,
            "tool_duration_ms": None,
            "verification_duration_ms": None,
        },

        "raw_runs": runs,
    }

    output = (
        RESULT_DIR
        / f"{WORKLOAD}_{timestamp}.json"
    )

    latest = (
        RESULT_DIR
        / f"{WORKLOAD}_latest.json"
    )

    output.write_text(
        json.dumps(
            summary,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    latest.write_text(
        json.dumps(
            summary,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    print()
    print("=" * 72)
    print("BENCHMARK COMPLETE")
    print("=" * 72)
    print(f"artifact: {output}")
    print()
    print("WARM WALL LATENCY:")
    print(
        json.dumps(
            summary["warm"]["wall_duration_ms"],
            indent=2,
        )
    )
    print()
    print("WARM LLM LATENCY:")
    print(
        json.dumps(
            summary["warm"]["llm_duration_ms"],
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

