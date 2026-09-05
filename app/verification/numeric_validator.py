from __future__ import annotations

import re
from typing import Any


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

        if result.get("analysis_type") != "trend_analysis":
            return {
                "valid": True,
                "checked": False,
                "reason": "numeric validation not implemented for this analysis type",
            }

        expected_values = {
            "start_value": result.get("start_value"),
            "end_value": result.get("end_value"),
            "percentage_change": result.get("percentage_change"),
        }

        numbers = self.extract_numbers(answer)

        if len(numbers) < 3:
            return {
                "valid": False,
                "checked": True,
                "reason": "could not find enough numeric claims in answer",
                "expected": expected_values,
                "reported_numbers": numbers,
            }

        def contains_expected_value(
            expected: float,
            reported_numbers: list[float],
        ) -> bool:
            return any(
                self.validate_reported_value(
                    expected,
                    actual,
                    tolerance,
                )
                for actual in reported_numbers
            )


        checks = {
            "start_value": contains_expected_value(
                expected_values["start_value"],
                numbers,
            ),
            "end_value": contains_expected_value(
                expected_values["end_value"],
                numbers,
            ),
            "percentage_change": contains_expected_value(
                expected_values["percentage_change"],
                numbers,
            ),
        }

        return {
            "valid": all(checks.values()),
            "checked": True,
            "checks": checks,
            "expected": expected_values,
            "reported_numbers": numbers,
        }