from __future__ import annotations

import re


class CodeSanitizer:
    @staticmethod
    def sanitize(code: str) -> str:
        if not code:
            return ""

        code = code.strip()

        # Remove <think>...</think> blocks if a model ever emits them.
        code = re.sub(
            r"<think>.*?</think>",
            "",
            code,
            flags=re.DOTALL | re.IGNORECASE,
        ).strip()

        # Remove Markdown code fences.
        if code.startswith("```"):
            lines = code.splitlines()

            if lines and lines[0].strip().startswith("```"):
                lines = lines[1:]

            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]

            code = "\n".join(lines).strip()

        return code