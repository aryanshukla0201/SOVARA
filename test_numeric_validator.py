from app.verification.numeric_validator import NumericValidator


validator = NumericValidator()


# Regression: comma-formatted currency must remain one number.
answer = "The average salary is $65,833.33 and Diana earns $81,000."

numbers = validator.extract_numbers(answer)

assert numbers == [65833.33, 81000.0], numbers


# Regression: formatted numeric answer must pass data validation.
data_result = {
    "result": {
        "analysis_type": "average",
        "average": 65833.33,
    }
}

validation = validator.validate_data_result(
    answer,
    data_result,
)

assert validation["valid"] is True, validation
assert validation["checked"] is True, validation
assert validation["checks"]["average"] is True, validation


print("Numeric validator regression test: PASS")
print("Extracted numbers:", numbers)
print("Validation:", validation)