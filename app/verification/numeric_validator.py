from __future__ import annotations

import numbers
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
            r"(?<![\w.])-?\d{1,3}(?:,\d{3})+(?:\.\d+)?|(?<![\w.])-?\d+(?:\.\d+)?",
            answer,
        )

        return [float(value.replace(",", "")) for value in matches]

    def validate_data_result(
        self,
        answer: str,
        data_result: dict[str, Any],
        tolerance: float = 0.01,
    ) -> dict[str, Any]:

        # DataNode/CSVAnalyzer results are stored directly under
        # the result dictionary. Support the older wrapped schema
        # as well for backward compatibility.
        if isinstance(data_result.get("result"), dict):
            result = data_result["result"]
        else:
            result = data_result

        if not isinstance(result, dict):
            return {
                "valid": True,
                "checked": False,
                "reason": "data result is not structured numeric output",
            }

        analysis_type = result.get("analysis_type")

        # --------------------------------------------------
        # Compound analysis
        # --------------------------------------------------

        if analysis_type == "compound":
            analyses = result.get("analyses", [])

            if not isinstance(analyses, list) or not analyses:
                return {
                    "valid": True,
                    "checked": False,
                    "reason": "compound data result contains no analyses",
                }

            results = []

            for analysis in analyses:
                if not isinstance(analysis, dict):
                    continue

                validation = self.validate_data_result(
                    answer,
                    analysis,
                    tolerance,
                )

                results.append(validation)

            checked_results = [
                item for item in results
                if item.get("checked")
            ]

            if not checked_results:
                return {
                    "valid": True,
                    "checked": False,
                    "reason": "compound result contains no supported numeric analyses",
                }

            return {
                "valid": all(
                    item["valid"]
                    for item in checked_results
                ),
                "checked": True,
                "checks": checked_results,
            }

        # --------------------------------------------------
        # Single deterministic analysis
        # --------------------------------------------------

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
                "reason": (
                    f"numeric validation not implemented "
                    f"for {analysis_type}"
                ),
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
                "reason": (
                    "answer makes no numeric claims "
                    "about this data result"
                ),
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