from app.workflow.nodes.code_pipeline import CodePipeline

pipeline = CodePipeline()

original_generate = pipeline.agent.generate

def broken_generate(**kwargs):
    return {
        "success": True,
        "code": "print(",
        "evidence_type": "generated_code",
        "model_used": "test",
    }

pipeline.agent.generate = broken_generate

print("=== TEST 29: AUTOMATIC REPAIR ===")

result = pipeline.run(
    "Calculate the sum of integers from 1 to 10."
)

print(result)

pipeline.agent.generate = original_generate
