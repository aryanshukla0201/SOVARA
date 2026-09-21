from __future__ import annotations

from pathlib import Path
from typing import Any


class ExecutionRequestValidator:
    MAX_CODE_LENGTH = 100_000
    MAX_INPUT_FILES = 32
    MAX_OUTPUT_FILES = 32

    def validate(self, arguments: dict[str, Any]) -> list[str]:
        errors: list[str] = []

        code = arguments.get("code")

        if not isinstance(code, str):
            errors.append("code must be a string.")
        elif not code.strip():
            errors.append("code cannot be empty.")
        elif len(code) > self.MAX_CODE_LENGTH:
            errors.append("code exceeds maximum length.")

        input_files = arguments.get("input_files", [])

        if not isinstance(input_files, list):
            errors.append("input_files must be a list.")
        elif len(input_files) > self.MAX_INPUT_FILES:
            errors.append("too many input files.")
        else:
            errors.extend(
                self._validate_input_path(path)
                for path in input_files
            )

        output_files = arguments.get("output_files", [])

        if not isinstance(output_files, list):
            errors.append("output_files must be a list.")
        elif len(output_files) > self.MAX_OUTPUT_FILES:
            errors.append("too many output files.")
        else:
            for filename in output_files:
                error = self._validate_output_filename(filename)
                if error:
                    errors.append(error)

        output_directory = arguments.get("output_directory")

        if output_directory is not None:
            if not isinstance(output_directory, (str, Path)):
                errors.append(
                    "output_directory must be a path string."
                )

        return [
            error
            for error in errors
            if error
        ]

    @staticmethod
    def _validate_input_path(path: Any) -> str:
        if not isinstance(path, (str, Path)):
            return "input_files must contain paths."

        candidate = Path(path)

        if candidate.is_absolute():
            return (
                f"Absolute input path is not allowed: {path}"
            )

        if ".." in candidate.parts:
            return (
                f"Parent traversal is not allowed: {path}"
            )

        return ""

    @staticmethod
    def _validate_output_filename(filename: Any) -> str:
        if not isinstance(filename, str):
            return "output_files must contain strings."

        if not filename.strip():
            return "Output filename cannot be empty."

        path = Path(filename)

        if path.is_absolute():
            return (
                f"Absolute output path is not allowed: {filename}"
            )

        if path.name != filename:
            return (
                f"Nested output path is not allowed: {filename}"
            )

        if ".." in path.parts:
            return (
                f"Parent traversal is not allowed: {filename}"
            )

        return ""
