from app.services.code_sandbox import CodeSandbox

sandbox = CodeSandbox()

print("=== TEST 4: CSV INPUT ===")

result = sandbox.execute(
    code="""
import csv

with open("/sandbox/input/test_input.csv", newline="", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

print(len(rows))
print(rows[0]["name"])
""",
    input_files=["test_input.csv"],
)

print(result)

print("=== TEST 5: INPUT WRITE PROTECTION ===")

result = sandbox.execute(
    code="""
with open("/sandbox/input/test_input.csv", "w") as f:
    f.write("modified")
""",
    input_files=["test_input.csv"],
)

print(result)

print("=== TEST 6: OUTPUT FILE ===")

result = sandbox.execute(
    code="""
with open("/sandbox/output/result.txt", "w") as f:
    f.write("SOVARA TEST")
""",
    output_files=["result.txt"],
)

print(result)

print("=== TEST 7: PERSISTENT OUTPUT ===")

result = sandbox.execute(
    code="""
with open("/sandbox/output/result.txt", "w") as f:
    f.write("SOVARA OUTPUT TEST")
""",
    output_files=["result.txt"],
    output_directory="test_outputs",
)

print(result)

print("=== TEST 12: NETWORK ISOLATION ===")

result = sandbox.execute(
    code="""
import urllib.request

urllib.request.urlopen(
    "https://example.com",
    timeout=2,
)
"""
)

print(result)


print("=== TEST 8: OUTPUT TRAVERSAL ===")
print(sandbox.execute(
    code="print(1)",
    output_files=["../evil.txt"],
))

print("=== TEST 9: ABSOLUTE OUTPUT PATH ===")
print(sandbox.execute(
    code="print(1)",
    output_files=["C:\\evil.txt"],
))

print("=== TEST 10: MISSING INPUT ===")
print(sandbox.execute(
    code="print(1)",
    input_files=["does_not_exist.csv"],
))

print("=== TEST 11: DUPLICATE INPUT FILENAMES ===")
print(sandbox.execute(
    code="print(1)",
    input_files=[
        "test_a/data.txt",
        "test_b/data.txt",
    ],
))

print("=== TEST 13: CPU TIMEOUT ===")
print(sandbox.execute(
    code="while True: pass",
))

print("=== TEST 14: MEMORY LIMIT ===")
print(sandbox.execute(
    code="x = bytearray(1024 * 1024 * 1024)",
))

print("=== TEST 15: PID LIMIT ===")
print(sandbox.execute(
    code="""
import os
children = []
for _ in range(200):
    children.append(os.fork())
""",
))

