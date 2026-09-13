from __future__ import annotations

from app.services.execution_telemetry import ExecutionTelemetry
from app.workflow.nodes.code_agent import CodeAgent
from app.workflow.nodes.code_execution_node import CodeExecutionNode


class CodePipeline:
    MAX_ATTEMPTS = 3

    def __init__(
        self,
        telemetry: ExecutionTelemetry | None = None,
    ):
        self.telemetry = telemetry

        self.agent = CodeAgent(
            telemetry=telemetry,
        )

        self.executor = CodeExecutionNode(
            telemetry=telemetry,
        )

    def run(
        self,
        user_query: str,
        input_files: list[str] | None = None,
        output_files: list[str] | None = None,
        output_directory: str | None = None,
    ) -> dict:
        input_files = input_files or []
        output_files = output_files or []

        previous_code = ""
        previous_result: dict = {}
        

        for attempt in range(1, self.MAX_ATTEMPTS + 1):

            if attempt == 1:
                generation = self.agent.generate(
                    user_query=user_query,
                    input_files=[
                        {
                            "path": path,
                            "filename": path.rsplit("\\", 1)[-1].rsplit("/", 1)[-1],
                        }
                        for path in input_files
                    ],
                )
            else:
                generation = self.agent.repair(
                    user_query=user_query,
                    previous_code=previous_code,
                    execution_result=previous_result,
                )

            if not generation.get("success"):
                previous_result = {
                    "success": False,
                    "stdout": "",
                    "stderr": generation.get(
                        "validation_error",
                        "Code generation failed",
                    ),
                    "return_code": -1,
                    "timeout": False,
                    "docker_error": False,
                    "validation_error": True,
                    "output_files": [],
                    "attempt": attempt,
                    "generated_code": generation.get("code", ""),
                }

                continue

            previous_code = generation.get("code", "").strip()

            result = self.executor.run(
                code=previous_code,
                input_files=input_files,
                output_files=output_files,
                output_directory=output_directory,
            )

            result["attempt"] = attempt
            result["generated_code"] = previous_code

            previous_result = result

            if result.get("success"):
                return result

        return previous_result