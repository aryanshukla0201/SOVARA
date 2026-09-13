from __future__ import annotations

import json

from app.models.model_factory import ModelFactory
from app.workflow.nodes.code_sanitizer import CodeSanitizer
from app.workflow.nodes.code_validator import CodeValidator
from app.services.execution_telemetry import ExecutionTelemetry


class CodeAgent:
    def __init__(
        self,
        model=None,
        telemetry: ExecutionTelemetry | None = None,
    ):
        self.telemetry = telemetry

        self.model = model or ModelFactory.create(
            "qwen_coder",
            telemetry=telemetry,
        )

    def generate(
        self,
        user_query: str,
        input_files: list[dict] | None = None,
    ) -> dict:
        input_files = input_files or []

        file_context = json.dumps(
            input_files,
            default=str,
        )

        prompt = f"""
You are SOVARA's Code Agent.

Generate Python code that solves the user's request.

USER REQUEST:
{user_query}

AVAILABLE INPUT FILES:
{file_context}

EXECUTION ENVIRONMENT:
- Python standard library only.
- No pandas.
- No numpy.
- No openpyxl.
- No network access.
- No package installation.
- No subprocess.
- Input files are under /sandbox/input/.
- Output files are under /sandbox/output/.
- Never access paths outside /sandbox/.

RULES:
1. Return ONLY executable Python source code.
2. Do NOT use Markdown code fences.
3. Do NOT explain the code.
4. Do NOT output JSON.
5. Do NOT output internal reasoning.
6. Do NOT fabricate input data.
7. Preserve exact numerical values from input data.
8. Write requested output files to /sandbox/output/.
9. Print concise useful results to stdout.
10. If required input is missing, print a clear explanation.
"""

        generated_code = self.model.generate(
            prompt,
            system_prompt=(
                "You are SOVARA's local Code Agent. "
                "Generate executable Python source code only. "
                "Never output Markdown, JSON, explanations, "
                "or internal reasoning. "
                "Never use network access."
            ),
        )

        generated_code = CodeSanitizer.sanitize(generated_code)

        validation = CodeValidator.validate(generated_code)
        if not validation["valid"]:
            return {
                "success": False,
                "code": generated_code,
                "evidence_type": "generated_code",
                "model_used": "qwen2.5-coder:7b-instruct",
                "validation_error": validation["error"],
            }

        return {
            "success": bool(generated_code and generated_code.strip()),
            "code": generated_code.strip(),
            "evidence_type": "generated_code",
            "model_used": "qwen2.5-coder:7b-instruct",
        }

    def repair(
        self,
        user_query: str,
        previous_code: str,
        execution_result: dict,
    ) -> dict:
        prompt = f"""
You are SOVARA's Code Repair Agent.

Fix the previously generated Python code.

USER REQUEST:
{user_query}

PREVIOUS CODE:
{previous_code}

EXECUTION RESULT:
return_code: {execution_result.get("return_code", -1)}

STDOUT:
{execution_result.get("stdout", "")}

STDERR:
{execution_result.get("stderr", "")}

ENVIRONMENT:
- Python standard library only.
- No pandas.
- No numpy.
- No openpyxl.
- No network access.
- No package installation.
- No subprocess.
- Input files are under /sandbox/input/.
- Output files are under /sandbox/output/.
- Never access paths outside /sandbox/.

RULES:
1. Return ONLY executable Python source code.
2. Do NOT use Markdown.
3. Do NOT use code fences.
4. Do NOT output JSON.
5. Do NOT explain anything.
6. Do NOT output internal reasoning.
7. Do NOT fabricate input data.
8. Preserve exact numerical values.
"""

        generated_code = self.model.generate(
            prompt,
            system_prompt=(
                "You are SOVARA's local Code Repair Agent. "
                "Return executable Python source code only. "
                "Never output Markdown, JSON, explanations, "
                "or internal reasoning. "
                "Never use network access."
            ),
        )

        generated_code = CodeSanitizer.sanitize(generated_code)

        validation = CodeValidator.validate(generated_code)
        if not validation["valid"]:
            return {
                "success": False,
                "code": generated_code,
                "evidence_type": "repaired_code",
                "model_used": "qwen2.5-coder:7b-instruct",
                "validation_error": validation["error"],
            }

        return {
            "success": bool(generated_code and generated_code.strip()),
            "code": generated_code.strip(),
            "evidence_type": "repaired_code",
            "model_used": "qwen2.5-coder:7b-instruct",
        }