from __future__ import annotations

import os
import platform
import re
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class HardwareProfile:
    gpu_name: str | None
    vram_gb: float | None
    ram_gb: float | None
    platform: str


class HardwareDetector:
    @staticmethod
    def detect() -> HardwareProfile:
        return HardwareProfile(
            gpu_name=HardwareDetector._detect_gpu_name(),
            vram_gb=HardwareDetector._detect_vram(),
            ram_gb=HardwareDetector._detect_ram(),
            platform=platform.system(),
        )

    @staticmethod
    def _detect_gpu_name() -> str | None:
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=name",
                    "--format=csv,noheader",
                ],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )

            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip().splitlines()[0].strip()

        except (FileNotFoundError, subprocess.SubprocessError):
            pass

        return None

    @staticmethod
    def _detect_vram() -> float | None:
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=memory.total",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )

            if result.returncode == 0 and result.stdout.strip():
                value = float(result.stdout.strip().splitlines()[0])
                return round(value / 1024, 2)

        except (FileNotFoundError, ValueError, subprocess.SubprocessError):
            pass

        return None

    @staticmethod
    def _detect_ram() -> float | None:
        try:
            if os.name == "nt":
                result = subprocess.run(
                    [
                        "powershell",
                        "-NoProfile",
                        "-Command",
                        "(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )

                if result.returncode == 0 and result.stdout.strip():
                    bytes_total = float(result.stdout.strip())
                    return round(bytes_total / (1024 ** 3), 2)

        except (ValueError, subprocess.SubprocessError):
            pass

        return None
