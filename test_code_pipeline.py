from app.workflow.nodes.code_pipeline import CodePipeline

pipeline = CodePipeline()

print("=== TEST 26: SIMPLE PIPELINE ===")

result = pipeline.run(
    "Calculate the sum of integers from 1 to 10."
)

print(result)


print("=== TEST 27: CSV PIPELINE ===")

result = pipeline.run(
    "Read test_input.csv and calculate the average salary.",
    input_files=["test_input.csv"],
)

print(result)


print("=== TEST 28: PIPELINE OUTPUT FILE ===")

result = pipeline.run(
    "Read test_input.csv and write the average salary to salary_report.txt.",
    input_files=["test_input.csv"],
    output_files=["salary_report.txt"],
    output_directory="test_outputs_pipeline",
)

print(result)
