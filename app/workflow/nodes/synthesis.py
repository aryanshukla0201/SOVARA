from __future__ import annotations

from app.models.model_factory import ModelFactory
from app.services.execution_telemetry import ExecutionTelemetry


class SynthesisNode:
    def __init__(self, model=None,telemetry: ExecutionTelemetry | None = None):
        self.model = model or ModelFactory.create("qwen", telemetry=telemetry)

    def run(
        self,
        user_query: str,
        evidence: list[dict],
        data_results: list[dict],
        vision_results: list[dict],
    ) -> dict:

        prompt = f"""
You are the synthesis stage of a grounded AI analysis system.

USER REQUEST:
{user_query}

DOCUMENT EVIDENCE:
{evidence}

DATA ANALYSIS RESULTS:
{data_results}

VISION ANALYSIS RESULTS:
{vision_results}

SYNTHESIS RULES:

1. Use ONLY the information contained in the provided evidence and
   tool results.

2. Do NOT invent facts, explanations, causes, trends, or relationships.

3. Clearly distinguish:
   - VERIFIED OBSERVATIONS directly supported by the sources
   - INFERENCES or POTENTIAL IMPLICATIONS reasonably derived by
     connecting those observations
   - LIMITATIONS where the available evidence cannot establish a claim

4. PRESERVE DOCUMENT CITATIONS.

   Every claim that depends on document evidence MUST include the
   exact corresponding evidence ID in square brackets.

   Valid format:
   [file_45aa400e_ev_001]

   IMPORTANT:
   - Use the exact evidence ID provided.
   - Do NOT modify the evidence ID.
   - Do NOT put Markdown formatting inside the brackets.
   - Do NOT invent evidence IDs.
   - Do NOT write citations such as [**file_45aa400e_ev_001**].
   - Do NOT remove citations from the final answer.

5. DATA RESULTS:

   Preserve deterministic numerical results exactly.

   If the data results say:
   start = 100
   end = 180
   percentage_change = 80

   you may state:
   "Revenue increased from 100 to 180, an 80% increase."

   Do NOT introduce additional claims that are not supported by the
   supplied data.

6. CROSS-MODAL REASONING:

   You MAY derive reasonable implications by connecting observations
   from different sources, but you MUST clearly label them as
   interpretations or potential contributions.

   For example:

   - VERIFIED OBSERVATION:
     Revenue increased from 100 to 180 [data_xxx].

   - DOCUMENT OBSERVATION:
     The proposed solution includes buyer linkages and profit
     simulation [file_xxx].

   - REASONED IMPLICATION:
     These features could contribute to revenue growth by improving
     market access and crop-level decision making.

   Do NOT present such an implication as an established fact.

   NEVER claim:
   "The presentation features caused the revenue increase."

   unless the supplied evidence explicitly establishes that causal
   relationship.

7. If the available sources cannot establish a conclusion, explicitly
   say so.

8. Organize the response clearly using headings or bullet points when
   useful.

9. Return ONLY the final synthesized answer.
"""

        result = self.model.generate(
            prompt,
            system_prompt=(
                "You are a rigorous evidence-grounded synthesis engine. "
                "Preserve exact evidence citations. "
                "Never invent facts or relationships. "
                "Preserve deterministic numerical results. "
                "Clearly distinguish observations, conclusions, and limitations."
            ),
        )

        return {
            "answer": result,
            "evidence_references": [
                item.get("evidence_id")
                for item in evidence
                if isinstance(item, dict) and item.get("evidence_id")
            ],
            "confidence": 0.85,
        }