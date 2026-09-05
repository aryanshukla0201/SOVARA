from __future__ import annotations

import re


class CitationValidator:

    def validate(self, answer: str, evidence_ids: list[str]) -> bool:

        # If there is no evidence, citations are not required.
        if not evidence_ids:
            return True

        # Find evidence citations in the format:
        # [file_123_ev_001]
        cited_ids = re.findall(r"\[([^\]]+)\]", answer)

        print("\n===== CITATION DEBUG =====")
        print("ANSWER:")
        print(answer)
        print("CITED IDS:")
        print(cited_ids)
        print("VALID EVIDENCE IDS:")
        print(evidence_ids)
        print("==========================")

        # Evidence-backed answers must contain at least one citation.
        if not cited_ids:
            return False

        # Every cited evidence ID must actually exist.
        valid_ids = set(evidence_ids)

        return all(citation in valid_ids for citation in cited_ids)