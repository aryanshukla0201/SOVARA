from __future__ import annotations


class ComplexityGate:
    def evaluate(self, result_state: dict) -> dict:
        document_results = result_state.get("document_results", [])
        data_results = result_state.get("data_results", [])
        vision_results = result_state.get("vision_results", [])
        retrieved_evidence = result_state.get("retrieved_evidence", [])

        modality_count = sum(
            [
                bool(document_results),
                bool(data_results),
                bool(vision_results),
                bool(retrieved_evidence),
            ]
        )

        if modality_count >= 2:
            return {
                "synthesis_required": True,
                "reason": "multiple evidence modalities require synthesis",
            }

        if retrieved_evidence:
            return {
                "synthesis_required": True,
                "reason": "retrieved knowledge evidence requires grounded synthesis",
            }

        if len(data_results) > 1:
            return {
                "synthesis_required": True,
                "reason": "multiple data analyses require interpretation",
            }

        return {
            "synthesis_required": False,
            "reason": "single deterministic evidence source is sufficient",
        }