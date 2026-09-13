from app.services.execution_telemetry import ExecutionTelemetry
from app.services.code_sandbox import CodeSandbox

print("=== TEST 31: TELEMETRY SUCCESS ===")

telemetry = ExecutionTelemetry()

result = CodeSandbox(
    telemetry=telemetry
).execute(
    code="print(55)"
)

print(result)
print(telemetry)


print("=== TEST 32: TELEMETRY TIMEOUT ===")

telemetry = ExecutionTelemetry()

result = CodeSandbox(
    telemetry=telemetry
).execute(
    code="while True: pass"
)

print(result)
print(telemetry)
