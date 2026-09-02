from __future__ import annotations


class NumericValidator:
    def validate_reported_value(self, expected: float, actual: float, tolerance: float = 0.01) -> bool:
        return abs(float(expected) - float(actual)) <= tolerance

    def validate_expression(self, expression: str, expected: float) -> bool:
        try:
            value = eval(expression, {"__builtins__": {}}, {})
            return self.validate_reported_value(expected, value)
        except Exception:
            return False
