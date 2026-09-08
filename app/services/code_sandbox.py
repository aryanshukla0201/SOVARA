from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


class CodeSandbox:
    def __init__(self, telemetry=None):
        self.telemetry = telemetry
    
    IMAGE = "sovara-sandbox:latest"
    TIMEOUT_SECONDS = 10

    def execute(self, code: str) -> dict:
        if not code or not code.strip():
            return {
                "success": False,
                "stdout": "",
                "stderr": "No code provided",
                "return_code": -1,
                "validation_error": True,
            }

        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = Path(temp_dir) / "main.py"
            script_path.write_text(code, encoding="utf-8")

            docker_exe = (
                Path.home()
                / "AppData/Local/Programs/DockerDesktop/resources/bin/docker.exe"
            )

            container_name = f"sovara-sandbox-{next(tempfile._get_candidate_names())}"

            try:
                result = subprocess.run(
                    [
                        str(docker_exe),
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
                        f"{temp_dir}:/sandbox/input:ro",
                        self.IMAGE,
                        "python",
                        "/sandbox/input/main.py",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=self.TIMEOUT_SECONDS,
                )

            except subprocess.TimeoutExpired as exc:
                subprocess.run(
                    [
                        str(docker_exe),
                        "rm",
                        "-f",
                        container_name,
                    ],
                    capture_output=True,
                    text=True,
                )

                if self.telemetry:
                    self.telemetry.record_sandbox_execution()

                return {
                    "success": False,
                    "stdout": exc.stdout or "",
                    "stderr": "Sandbox execution timed out",
                    "return_code": -1,
                    "timeout": True,
                }

            except FileNotFoundError:
                if self.telemetry:
                    self.telemetry.record_sandbox_execution()

                return {
                    "success": False,
                    "stdout": "",
                    "stderr": "Docker executable not found",
                    "return_code": -1,
                    "docker_error": True,
                }

            except OSError as exc:
                if self.telemetry:
                    self.telemetry.record_sandbox_execution()

                return {
                    "success": False,
                    "stdout": "",
                    "stderr": f"Docker execution failed: {exc}",
                    "return_code": -1,
                    "docker_error": True,
                }

            if self.telemetry:
                self.telemetry.record_sandbox_execution()

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode,
            }