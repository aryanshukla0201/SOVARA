from __future__ import annotations

import ast


class CodeValidator:
    FORBIDDEN_IMPORTS = {
        "subprocess",
        "socket",
        "requests",
        "urllib",
        "http",
        "ftplib",
    }

    FORBIDDEN_CALLS = {
        "eval",
        "exec",
        "compile",
        "__import__",
    }

    @classmethod
    def validate(cls, code: str) -> dict:
        if not code or not code.strip():
            return {
                "valid": False,
                "error": "Generated code is empty",
            }

        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            return {
                "valid": False,
                "error": f"Syntax error: {exc}",
            }

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]

                    if root in cls.FORBIDDEN_IMPORTS:
                        return {
                            "valid": False,
                            "error": f"Forbidden import: {alias.name}",
                        }

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    root = node.module.split(".")[0]

                    if root in cls.FORBIDDEN_IMPORTS:
                        return {
                            "valid": False,
                            "error": f"Forbidden import: {node.module}",
                        }

            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in cls.FORBIDDEN_CALLS:
                        return {
                            "valid": False,
                            "error": f"Forbidden function: {node.func.id}",
                        }

        return {
            "valid": True,
            "error": None,
        }
    