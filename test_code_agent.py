from app.workflow.nodes.code_agent import CodeAgent

agent = CodeAgent()

print("=== TEST 23: SIMPLE CODE GENERATION ===")
r = agent.generate(
    "Calculate the sum of integers from 1 to 10."
)
print(r)

print("=== GENERATED CODE ===")
print(r.get("code", ""))

print("=== TEST 24: CSV CODE GENERATION ===")
r = agent.generate(
    "Read test_input.csv and calculate the average salary."
)
print(r)

print("=== GENERATED CODE ===")
print(r.get("code", ""))

print("=== TEST 25: STANDARD LIBRARY COMPLIANCE ===")
r = agent.generate(
    "Read test_input.csv and calculate the average salary "
    "using only the Python standard library. "
    "Do not use pandas, numpy, or any external package."
)
print(r)

print("=== GENERATED CODE ===")
print(r.get("code", ""))
