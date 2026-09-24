from __future__ import annotations

import json
import os
import platform
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import psutil


ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "benchmarks" / "results" / "sovara-laptop-rtx5060"
RESULTS.mkdir(parents=True, exist_ok=True)


def run_command(*args: str) -> str | None:
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def gpu_info() -> list[dict]:
    output = run_command(
        "nvidia-smi",
        "--query-gpu=name,memory.total,driver_version",
        "--format=csv,noheader,nounits",
    )

    if not output:
        return []

    gpus = []
    for line in output.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 3:
            gpus.append(
                {
                    "name": parts[0],
                    "vram_mb": int(float(parts[1])),
                    "driver_version": parts[2],
                }
            )
    return gpus


def git_commit() -> str | None:
    return run_command("git", "-C", str(ROOT), "rev-parse", "HEAD")


def main() -> None:
    memory = psutil.virtual_memory()

    probe = {
        "machine_id": "sovara-laptop-rtx5060",
        "hostname": socket.gethostname(),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "os": platform.platform(),
        "python": platform.python_version(),
        "cpu": platform.processor(),
        "logical_cpus": psutil.cpu_count(logical=True),
        "physical_cpus": psutil.cpu_count(logical=False),
        "ram_mb": round(memory.total / (1024 * 1024)),
        "git_commit": git_commit(),
        "gpus": gpu_info(),
        "working_directory": str(ROOT),
    }

    output = RESULTS / "machine_identity.json"
    output.write_text(
        json.dumps(probe, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(probe, indent=2))
    print(f"\nSAVED: {output}")


if __name__ == "__main__":
    main()
