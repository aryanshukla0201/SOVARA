from __future__ import annotations


class ClaimValidator:
    def validate(self, claims: list[str], evidence: list[str]) -> bool:
        if not claims:
            return True
        return all(claim.strip() for claim in claims) and bool(evidence)
