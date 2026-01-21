"""
Publish policy layer.
Centralizes safety rules for publish/hold/reject decisions.
"""

from typing import Dict, List, Optional
from config.manager import config


class PublishPolicy:
    def __init__(self):
        self.min_quality = config.get("publish_policy.min_quality", 75)
        self.min_citation_density = config.get("publish_policy.min_citation_density", 0.6)
        self.min_sources = config.get("publish_policy.min_sources", 3)
        self.min_consensus = config.get("fact_check.consensus_min", 85)
        self.block_on_claim_issues = config.get("publish_policy.block_on_claim_issues", True)
        self.block_on_contradictions = config.get("publish_policy.block_on_contradictions", True)
        self.block_on_citation_issues = config.get("publish_policy.block_on_citation_issues", True)

    def evaluate(
        self,
        draft: Dict,
        evidence: Optional[List[Dict]] = None,
        fact_check: Optional[Dict] = None,
        citation_result: Optional[Dict] = None,
        claim_ledger: Optional[Dict] = None,
        citation_density: float = 0.0
    ) -> Dict:
        reasons = []
        decision = "publish"

        # Evidence sufficiency
        if evidence is not None and len(evidence) < int(self.min_sources):
            reasons.append("Insufficient sources for publication.")
            decision = "hold"

        # Quality threshold
        if float(draft.get("qualityScore", 0)) < float(self.min_quality):
            reasons.append(f"Quality score below threshold ({self.min_quality}).")
            decision = "hold"

        if citation_density and citation_density < float(self.min_citation_density):
            reasons.append("Citation density below threshold.")
            decision = "hold"

        if citation_result and not citation_result.get("passes"):
            reasons.append("Citation validation failed.")
            if self.block_on_citation_issues:
                decision = "hold"

        # Claim ledger
        if claim_ledger:
            if self.block_on_claim_issues and claim_ledger.get("issues"):
                reasons.append("Claim ledger issues present.")
                decision = "hold"
            if self.block_on_contradictions and claim_ledger.get("contradictions"):
                reasons.append("Internal contradictions detected.")
                decision = "hold"

        # Fact check gate
        if fact_check:
            synthesized = fact_check.get("synthesized", {})
            consensus = fact_check.get("consensus", {})
            if synthesized.get("factual_errors"):
                reasons.append("Factual errors detected by adversarial review.")
                decision = "reject"
            score = consensus.get("score", 0)
            level = consensus.get("level", "")
            if level in ("skipped", ""):
                reasons.append("Fact check skipped or unavailable.")
                decision = "hold"
            if score < self.min_consensus:
                reasons.append(f"Consensus below threshold ({self.min_consensus}).")
                decision = "hold"

        return {"decision": decision, "reasons": reasons}
