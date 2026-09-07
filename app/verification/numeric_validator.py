from __future__ import annotations

import numbers
import re
from typing import Any
from unittest import result


class NumericValidator:
    def validate_reported_value(
        self,
        expected: float,
        actual: float,
        tolerance: float = 0.01,
    ) -> bool:
        return abs(float(expected) - float(actual)) <= tolerance

    def validate_expression(
        self,
        expression: str,
        expected: float,
    ) -> bool:
        try:
            value = eval(
                expression,
                {"__builtins__": {}},
                {},
            )
            return self.validate_reported_value(
                expected,
                value,
            )
        except Exception:
            return False

    def extract_numbers(self, answer: str) -> list[float]:
        """
        Extract numeric values from a generated answer.

        Supports integers, decimals, and negative numbers.
        Percentage symbols are ignored because the numeric value
        itself is what we compare.
        """
        matches = re.findall(
            r"(?<![\w.])-?\d+(?:\.\d+)?",
            answer,
        )

        return [float(value) for value in matches]

    def validate_data_result(
        self,
        answer: str,
        data_result: dict[str, Any],
        tolerance: float = 0.01,
    ) -> dict[str, Any]:

        result = data_result.get("result", {})

        if not isinstance(result, dict):
            return {
                "valid": True,
                "checked": False,
                "reason": "data result is not structured numeric output",
            }

        analysis_type = result.get("analysis_type")

        expected_fields = {
            "trend_analysis": [
                "start_value",
                "end_value",
                "percentage_change",
            ],
            "average": ["average"],
            "sum": ["sum"],
            "minimum": ["minimum"],
            "maximum": ["maximum"],
        }

        fields = expected_fields.get(analysis_type)

        if not fields:
            return {
                "valid": True,
                "checked": False,
                "reason": f"numeric validation not implemented for {analysis_type}",
            }

        expected_values = {
            field: result.get(field)
            for field in fields
        }

        numbers = self.extract_numbers(answer)

        if not numbers:
            return {
                "valid": True,
                "checked": False,
                "reason": "answer makes no numeric claims about this data result",
                "expected": expected_values,
                "reported_numbers": [],
            }

        def contains_expected_value(
            expected: float,
            reported_numbers: list[float],
        ) -> bool:
            if expected is None:
                return True

            return any(
                self.validate_reported_value(
                    expected,
                    actual,
                    tolerance,
                )
                for actual in reported_numbers
            )

        checks = {
            field: contains_expected_value(
                expected_values[field],
                numbers,
            )
            for field in fields
        }

        return {
            "valid": all(checks.values()),
            "checked": True,
            "checks": checks,
            "expected": expected_values,
            "reported_numbers": numbers,
        }