from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass


@dataclass
class ResourceSample:
    timestamp: float
    cpu_percent: float
    memory_used_mb: float
    memory_percent: float
    gpu_utilization_percent: float | None
    gpu_memory_used_mb: float | None
    gpu_memory_total_mb: float | None


def gpu_sample() -> tuple[float | None, float | None, float | None]:
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


def sample() -> ResourceSample:
    import psutil

    gpu_util, gpu_used, gpu_total = gpu_sample()
    memory = psutil.virtual_memory()

    return ResourceSample(
        timestamp=time.perf_counter(),
        cpu_percent=psutil.cpu_percent(interval=0.1),
        memory_used_mb=memory.used / (1024 * 1024),
        memory_percent=memory.percent,
        gpu_utilization_percent=gpu_util,
        gpu_memory_used_mb=gpu_used,
        gpu_memory_total_mb=gpu_total,
    )


if __name__ == "__main__":
    print("Resource sampler self-test")
    for _ in range(5):
        print(sample())
        time.sleep(1)
