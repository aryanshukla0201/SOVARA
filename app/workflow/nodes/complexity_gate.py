from __future__ import annotations


class ComplexityGate:
    def evaluate(self, result_state: dict) -> dict:
        document_results = result_state.get("document_results", [])
        data_results = result_state.get("data_results", [])
        vision_results = result_state.get("vision_results", [])

        if len(document_results) > 0 and len(data_results) > 0:
            return {"synthesis_required": True, "reason": "multiple evidence sources require interpretation"}
        if len(document_results) > 0 and len(vision_results) > 0:
            return {"synthesis_required": True, "reason": "multiple evidence sources require interpretation"}
        if len(data_results) > 1:
            return {"synthesis_required": True, "reason": "multiple deterministic calculations require interpretation"}
        return {"synthesis_required": False, "reason": "deterministic calculation already satisfies request"}
