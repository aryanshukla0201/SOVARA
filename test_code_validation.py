from app.workflow.nodes.code_sanitizer import CodeSanitizer
from app.workflow.nodes.code_validator import CodeValidator

print("=== SANITIZER 1 ===")
print(CodeSanitizer.sanitize("```python\nprint(55)\n```"))

print("=== SANITIZER 2 ===")
print(CodeSanitizer.sanitize("<think>internal reasoning</think>\nprint(55)"))

print("=== VALIDATOR 1: VALID ===")
print(CodeValidator.validate("print(55)"))

print("=== VALIDATOR 2: SYNTAX ===")
print(CodeValidator.validate("print("))

print("=== VALIDATOR 3: SUBPROCESS ===")
print(CodeValidator.validate("import subprocess"))

print("=== VALIDATOR 4: EVAL ===")
print(CodeValidator.validate('eval("1+1")'))
