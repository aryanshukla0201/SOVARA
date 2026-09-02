from __future__ import annotations

from app.models.model_factory import ModelFactory


class SynthesisNode:
    def __init__(self, model=None):
        self.model = model or ModelFactory.create("qwen")

    def run(self, user_query: str, evidence: list[dict], data_results: list[dict], vision_results: list[dict]) -> dict:
        prompt = (
            "Use only the evidence and tool results provided. Do not invent facts. Do not claim something is supported if no evidence supports it. "
            "Clearly distinguish observations from conclusions. "
            f"User query: {user_query}. Evidence: {evidence}. Data results: {data_results}. Vision: {vision_results}."
        )
        result = self.model.generate(prompt)
        return {
            "answer": result,
            "evidence_references": [item.get("evidence_id") for item in evidence if isinstance(item, dict) and "evidence_id" in item],
            "confidence": 0.85,
        }
