from app.workflow.nodes.task_analyzer import TaskAnalyzer

analyzer = TaskAnalyzer()

tests = [
    "Calculate the sum of integers from 1 to 10.",
    "Write Python code to calculate the average.",
    "What is the capital of France?",
]

for query in tests:
    result = analyzer.analyze(query, [])
    print("\nQUERY:", query)
    print("INTENT:", result.intent)
    print("CAPABILITIES:", result.required_capabilities)
    print("REQUIRES CODE:", result.requires_code)
