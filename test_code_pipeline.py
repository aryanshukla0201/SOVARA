from pathlib import Path
import shutil

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

output_directory = Path("test_outputs_pipeline")

if output_directory.exists():
    shutil.rmtree(output_directory)

output_directory.mkdir(parents=True, exist_ok=True)

result = pipeline.run(
    "Read test_input.csv and write the average salary to salary_report.txt.",
    input_files=["test_input.csv"],
    output_files=["salary_report.txt"],
    output_directory=str(output_directory),
)

print(result)

output_file = output_directory / "salary_report.txt"

print("OUTPUT EXISTS:", output_file.exists())

if output_file.exists():
    print("OUTPUT CONTENT:", output_file.read_text(encoding="utf-8"))