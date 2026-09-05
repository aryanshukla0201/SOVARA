from __future__ import annotations


class ComplexityGate:
    def evaluate(self, result_state: dict) -> dict:
        document_results = result_state.get("document_results", [])
        data_results = result_state.get("data_results", [])
        vision_results = result_state.get("vision_results", [])

        modality_count = sum(
            [
                bool(document_results),
                bool(data_results),
                bool(vision_results),
            ]
        )

        # ---------------------------------------------------------
        # MULTIMODAL SYNTHESIS
        # ---------------------------------------------------------
        # If evidence comes from two or more different modalities,
        # the results should be interpreted together.
        if modality_count >= 2:
            return {
                "synthesis_required": True,
                "reason": "multiple modalities require cross-modal synthesis",
            }

        # ---------------------------------------------------------
        # MULTIPLE DATA SOURCES
        # ---------------------------------------------------------
        # Even within a single modality, multiple deterministic
        # analyses may need interpretation together.
        if len(data_results) > 1:
            return {
                "synthesis_required": True,
                "reason": "multiple data analyses require interpretation",
            }

        # ---------------------------------------------------------
        # SINGLE SOURCE
        # ---------------------------------------------------------
        return {
            "synthesis_required": False,
            "reason": "single evidence source is sufficient",
        }