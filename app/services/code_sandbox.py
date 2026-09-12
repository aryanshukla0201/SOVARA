from __future__ import annotations

import shutil
import subprocess
import tempfile
import time
from pathlib import Path


class CodeSandbox:
    IMAGE = "sovara-sandbox:latest"
    TIMEOUT_SECONDS = 10

    def __init__(self, telemetry=None):
        self.telemetry = telemetry

    def execute(
        self,
        code: str,
        input_files: list[str | Path] | None = None,
        output_files: list[str] | None = None,
        output_directory: str | Path | None = None,
    ) -> dict:
        if not code or not code.strip():
            return {
                "success": False,
                "stdout": "",
                "stderr": "No code provided",
                "return_code": -1,
                "timeout": False,
                "docker_error": False,
                "validation_error": True,
                "output_files": [],
            }

        input_files = input_files or []
        output_files = output_files or []
        for filename in output_files:
            path = Path(filename)

            if path.is_absolute() or path.name != filename:
                return {
                    "success": False,
                    "stdout": "",
                    "stderr": f"Invalid output filename: {filename}",
                    "return_code": -1,
                    "timeout": False,
                    "docker_error": False,
                    "validation_error": True,
                    "output_files": [],
                }
        persistent_output_dir = (
            Path(output_directory)
            if output_directory
            else None
        )

        if persistent_output_dir:
            persistent_output_dir.mkdir(
                parents=True,
                exist_ok=True,
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = Path(temp_dir) / "main.py"
            script_path.write_text(code, encoding="utf-8")

            input_dir = Path(temp_dir) / "input"
            input_dir.mkdir()

            shutil.copy2(
                script_path,
                input_dir / "main.py",
            )

            for input_file in input_files:
                source = Path(input_file)

                if not source.is_file():
                    continue

                destination = input_dir / source.name
                shutil.copy2(source, destination)

            output_dir = Path(temp_dir) / "output"
            output_dir.mkdir()

            docker_exe = "docker"
            container_name = (
                f"sovara-sandbox-{next(tempfile._get_candidate_names())}"
            )

            start_time = time.perf_counter()

            try:
                result = subprocess.run(
                    [
                        docker_exe,
                        "run",
                        "--name",
                        container_name,
                        "--rm",
                        "--network=none",
                        "--pull=never",
                        "--cap-drop=ALL",
                        "--security-opt=no-new-privileges:true",
                        "--cpus=1",
                        "--memory=512m",
                        "--pids-limit=64",
                        "--read-only",
                        "--tmpfs",
                        "/tmp:rw,noexec,nosuid,size=64m",
                        "-v",
                        f"{input_dir}:/sandbox/input:ro",
                        "-v",
                        f"{temp_dir}/output:/sandbox/output:rw",
                        self.IMAGE,
                        "python",
                        "/sandbox/input/main.py",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=self.TIMEOUT_SECONDS,
                )

                duration_ms = (time.perf_counter() - start_time) * 1000

            except subprocess.TimeoutExpired as exc:
                duration_ms = (time.perf_counter() - start_time) * 1000

                subprocess.run(
                    [
                        docker_exe,
                        "rm",
                        "-f",
                        container_name,
                    ],
                    capture_output=True,
                    text=True,
                )

                if self.telemetry:
                    self.telemetry.record_sandbox_execution(
                        success=False,
                        return_code=-1,
                        duration_ms=duration_ms,
                        timeout=True,
                    )

                return {
                    "success": False,
                    "stdout": exc.stdout or "",
                    "stderr": "Sandbox execution timed out",
                    "return_code": -1,
                    "timeout": True,
                    "docker_error": False,
                    "validation_error": False,
                    "output_files": [],
                }

            except FileNotFoundError:
                duration_ms = (time.perf_counter() - start_time) * 1000

                if self.telemetry:
                    self.telemetry.record_sandbox_execution(
                        success=False,
                        return_code=-1,
                        duration_ms=duration_ms,
                    )

                return {
                    "success": False,
                    "stdout": "",
                    "stderr": "Docker executable not found",
                    "return_code": -1,
                    "timeout": False,
                    "docker_error": True,
                    "validation_error": False,
                    "output_files": [],
                }

            except OSError as exc:
                duration_ms = (time.perf_counter() - start_time) * 1000

                if self.telemetry:
                    self.telemetry.record_sandbox_execution(
                        success=False,
                        return_code=-1,
                        duration_ms=duration_ms,
                    )

                return {
                    "success": False,
                    "stdout": "",
                    "stderr": f"Docker execution failed: {exc}",
                    "return_code": -1,
                    "docker_error": True,
                }

            if self.telemetry:
                self.telemetry.record_sandbox_execution(
                    success=result.returncode == 0,
                    return_code=result.returncode,
                    duration_ms=duration_ms,
                )
            persistent_output_files: list[str] = []

            if persistent_output_dir:
                for filename in output_files:
                    source = Path(temp_dir) / "output" / filename

                    if source.is_file():
                        destination = persistent_output_dir / Path(filename).name
                        shutil.copy2(source, destination)
                        persistent_output_files.append(str(destination))
            
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode,
                "timeout": False,
                "docker_error": False,
                "validation_error": False,
                "output_files": persistent_output_files,
            }