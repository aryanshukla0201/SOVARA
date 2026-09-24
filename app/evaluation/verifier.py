from __future__ import annotations

from typing import Any

from app.evaluation.models import VerificationResult, VerificationStatus


class DeterministicVerifier:
    """Performs deterministic, side-effect-free verification checks."""

    def verify_output(
        self,
        actual: Any,
        expected: Any,
        check: str = "output_match",
    ) -> VerificationResult:
        if actual == expected:
            return VerificationResult(
                status=VerificationStatus.PASSED,
                check=check,
                reason="actual output matches expected output",
            )

        return VerificationResult(
            status=VerificationStatus.FAILED,
            check=check,
            reason="actual output does not match expected output",
            details={
                "expected": expected,
                "actual": actual,
            },
        )

    def verify_success(
        self,
        success: bool,
        check: str = "execution_success",
    ) -> VerificationResult:
        if success:
            return VerificationResult(
                status=VerificationStatus.PASSED,
                check=check,
                reason="execution completed successfully",
            )

        return VerificationResult(
            status=VerificationStatus.FAILED,
            check=check,
            reason="execution did not complete successfully",
        )

    def verify_required_fields(
        self,
        data: dict[str, Any],
        required_fields: list[str] | tuple[str, ...],
        check: str = "required_fields",
    ) -> VerificationResult:
        missing = sorted(field for field in required_fields if field not in data)

        if not missing:
            return VerificationResult(
                status=VerificationStatus.PASSED,
                check=check,
                reason="all required fields are present",
            )

        return VerificationResult(
            status=VerificationStatus.FAILED,
            check=check,
            reason="required fields are missing",
            details={"missing_fields": missing},
        )

    def verify(
        self,
        actual: Any,
        expected: Any,
        *,
        check: str = "output_match",
    ) -> VerificationResult:
        return self.verify_output(actual, expected, check=check)
