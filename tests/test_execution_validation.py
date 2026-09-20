from app.execution.validation import ExecutionRequestValidator


def test_valid_request():
    errors = ExecutionRequestValidator().validate(
        {
            "code": "print(1)",
            "input_files": ["data.csv"],
            "output_files": ["result.csv"],
        }
    )

    assert errors == []


def test_empty_code():
    errors = ExecutionRequestValidator().validate(
        {"code": " "}
    )

    assert "code cannot be empty." in errors


def test_non_string_code():
    errors = ExecutionRequestValidator().validate(
        {"code": 123}
    )

    assert "code must be a string." in errors


def test_code_length_limit():
    validator = ExecutionRequestValidator()
    validator.MAX_CODE_LENGTH = 3

    errors = validator.validate(
        {"code": "print(1)"}
    )

    assert "code exceeds maximum length." in errors


def test_input_files_must_be_list():
    errors = ExecutionRequestValidator().validate(
        {
            "code": "print(1)",
            "input_files": "data.csv",
        }
    )

    assert "input_files must be a list." in errors


def test_absolute_input_path_rejected():
    errors = ExecutionRequestValidator().validate(
        {
            "code": "print(1)",
            "input_files": [r"C:\secret.txt"],
        }
    )

    assert any(
        "Absolute input path" in error
        for error in errors
    )


def test_parent_input_traversal_rejected():
    errors = ExecutionRequestValidator().validate(
        {
            "code": "print(1)",
            "input_files": ["../secret.txt"],
        }
    )

    assert any(
        "Parent traversal" in error
        for error in errors
    )


def test_too_many_input_files():
    validator = ExecutionRequestValidator()
    validator.MAX_INPUT_FILES = 1

    errors = validator.validate(
        {
            "code": "print(1)",
            "input_files": ["a", "b"],
        }
    )

    assert "too many input files." in errors


def test_output_filename_must_be_flat():
    errors = ExecutionRequestValidator().validate(
        {
            "code": "print(1)",
            "output_files": ["nested/result.csv"],
        }
    )

    assert any(
        "Nested output path" in error
        for error in errors
    )


def test_absolute_output_path_rejected():
    errors = ExecutionRequestValidator().validate(
        {
            "code": "print(1)",
            "output_files": [r"C:\result.csv"],
        }
    )

    assert any(
        "Absolute output path" in error
        for error in errors
    )


def test_parent_output_traversal_rejected():
    errors = ExecutionRequestValidator().validate(
        {
            "code": "print(1)",
            "output_files": ["../result.csv"],
        }
    )

    assert any(
        "Nested output path" in error
        or "Parent traversal" in error
        for error in errors
    )


def test_output_files_must_be_list():
    errors = ExecutionRequestValidator().validate(
        {
            "code": "print(1)",
            "output_files": "result.csv",
        }
    )

    assert "output_files must be a list." in errors
