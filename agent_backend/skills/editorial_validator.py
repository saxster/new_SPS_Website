"""
Editorial Validator: Consensus-Based Topic Validation
Integrates ConsensusEngine and EnsembleOrchestrator for adversarial topic vetting.

Pipeline:
1. Gatekeeper (fast, rule-based) - ConsensusEngine._agent_editor()
2. LLM Consensus (optional) - EnsembleOrchestrator (multi-model)
3. Red-Team Challenge - ConsensusEngine._agent_red_team()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum

from config.manager import config
from shared.logger import get_logger
from skills.consensus_engine import ConsensusEngine

logger = get_logger("EditorialValidator")


# =============================================================================
# Data Models
# =============================================================================

class ConsensusLevel(Enum):
    """Consensus tiers based on model agreement"""
    AUTHORITATIVE = "authoritative"  # 90-100% agreement
    HIGH = "high"                     # 70-89% agreement
    DISPUTED = "disputed"             # 40-69% agreement
    UNTRUSTED = "untrusted"           # <40% agreement
    SKIPPED = "skipped"               # Consensus not run


@dataclass
class EditorialVerdict:
    """Result of editorial validation for a topic proposal."""
    approved: bool
    topic: str
    
    # Gatekeeper results
    gatekeeper_score: int = 0
    gatekeeper_reasons: List[str] = field(default_factory=list)
    
    # LLM Consensus results (optional)
    consensus_level: ConsensusLevel = ConsensusLevel.SKIPPED
    consensus_score: float = 0.0
    models_used: List[str] = field(default_factory=list)
    
    # Red-team challenge
    red_team_challenge: str = ""
    
    # Final synthesis
    synthesis: str = ""
    dissenting_views: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "approved": self.approved,
            "topic": self.topic,
            "gatekeeper_score": self.gatekeeper_score,
            "gatekeeper_reasons": self.gatekeeper_reasons,
            "consensus_level": self.consensus_level.value,
            "consensus_score": self.consensus_score,
            "models_used": self.models_used,
            "red_team_challenge": self.red_team_challenge,
            "synthesis": self.synthesis,
            "dissenting_views": self.dissenting_views
        }


# =============================================================================
# Editorial Validator
# =============================================================================

class EditorialValidator:
    """
    Multi-stage editorial validation for topic proposals.
    
    Combines:
    - ConsensusEngine gatekeeper (rule-based, fast)
    - EnsembleOrchestrator (multi-model LLM consensus, optional)
    - Red-team adversarial challenge
    """
    
    def __init__(self):
        self.consensus_engine = ConsensusEngine()
        
        # Configuration
        self.enabled = config.get("editorial.enabled", True)
        
        # Gatekeeper config
        self.gatekeeper_enabled = config.get("editorial.gatekeeper.enabled", True)
        self.gatekeeper_min_score = config.get("editorial.gatekeeper.min_score", 50)
        
        # LLM Consensus config (expensive, opt-in)
        self.consensus_enabled = config.get("editorial.consensus.enabled", False)
        self.consensus_tier = config.get("editorial.consensus.tier", "spot")
        self.consensus_min_level = config.get(
            "editorial.consensus.min_level", 
            "high"
        )
        
        # Red-team config
        self.red_team_enabled = config.get("editorial.red_team.enabled", True)
        
        logger.info(
            "editorial_validator_initialized",
            enabled=self.enabled,
            gatekeeper=self.gatekeeper_enabled,
            consensus=self.consensus_enabled,
            red_team=self.red_team_enabled
        )
    
    def validate_topic(
        self, 
        topic: str,
        content_type: str = "News",
        sector: str = "general",
        summary: str = "",
        metadata: Optional[Dict] = None
    ) -> EditorialVerdict:
        """
        Validate a topic through the editorial pipeline.
        
        Args:
            topic: The topic string to validate
            content_type: News, Guide, or Analysis
            sector: Topic sector (cybersecurity, fire_safety, etc.)
            summary: Brief topic summary
            metadata: Additional metadata
            
        Returns:
            EditorialVerdict with approval decision and rationale
        """
        if not self.enabled:
            return EditorialVerdict(
                approved=True,
                topic=topic,
                synthesis="Editorial validation disabled"
            )
        
        # Build signal for ConsensusEngine (matches expected format)
        signal = {
            "title": topic,
            "summary": summary or topic,
            "sector": self._map_sector(sector),
            "location": "India",
            "pattern": content_type
        }
        
        verdict = EditorialVerdict(approved=True, topic=topic)
        
        # Stage 1: Gatekeeper (fast, rule-based)
        if self.gatekeeper_enabled:
            verdict = self._apply_gatekeeper(signal, verdict)
            if not verdict.approved:
                logger.info(
                    "topic_rejected_by_gatekeeper",
                    topic=topic[:50],
                    score=verdict.gatekeeper_score
                )
                return verdict
        
        # Stage 2: LLM Consensus (optional, expensive)
        if self.consensus_enabled:
            verdict = self._apply_llm_consensus(signal, verdict)
            if not verdict.approved:
                logger.info(
                    "topic_rejected_by_consensus",
                    topic=topic[:50],
                    level=verdict.consensus_level.value
                )
                return verdict
        
        # Stage 3: Red-Team Challenge
        if self.red_team_enabled:
            verdict = self._apply_red_team(signal, verdict)
        
        # Stage 4: Final Synthesis
        verdict = self._synthesize_verdict(signal, verdict)
        
        logger.info(
            "topic_validated",
            topic=topic[:50],
            approved=verdict.approved,
            gatekeeper_score=verdict.gatekeeper_score,
            consensus_level=verdict.consensus_level.value
        )
        
        return verdict
    
    def validate_batch(
        self, 
        topics: List[Dict]
    ) -> List[EditorialVerdict]:
        """
        Validate multiple topics efficiently.
        
        Args:
            topics: List of dicts with 'topic', 'content_type', 'sector', etc.
            
        Returns:
            List of EditorialVerdict objects
        """
        verdicts = []
        
        for topic_data in topics:
            verdict = self.validate_topic(
                topic=topic_data.get("topic", ""),
                content_type=topic_data.get("content_type", "News"),
                sector=topic_data.get("sector", "general"),
                summary=topic_data.get("summary", ""),
                metadata=topic_data.get("metadata")
            )
            verdicts.append(verdict)
        
        approved_count = sum(1 for v in verdicts if v.approved)
        logger.info(
            "batch_validation_complete",
            total=len(verdicts),
            approved=approved_count,
            rejected=len(verdicts) - approved_count
        )
        
        return verdicts
    
    # =========================================================================
    # Stage 1: Gatekeeper
    # =========================================================================
    
    def _apply_gatekeeper(
        self, 
        signal: Dict, 
        verdict: EditorialVerdict
    ) -> EditorialVerdict:
        """
        Apply rule-based gatekeeper scoring.
        Uses ConsensusEngine._agent_editor() for strategic impact scoring.
        """
        try:
            editorial_result = self.consensus_engine._agent_editor(signal)
            
            verdict.gatekeeper_score = editorial_result.get("score", 0)
            verdict.gatekeeper_reasons = editorial_result.get("reason", "").split(", ")
            verdict.approved = editorial_result.get("approved", False)
            
            # Apply minimum score threshold
            if verdict.gatekeeper_score < self.gatekeeper_min_score:
                verdict.approved = False
                verdict.synthesis = f"Below gatekeeper threshold ({verdict.gatekeeper_score} < {self.gatekeeper_min_score})"
            
        except Exception as e:
            logger.warning("gatekeeper_error", error=str(e))
            # Fail open - allow topic through if gatekeeper fails
            verdict.approved = True
            verdict.gatekeeper_reasons = ["Gatekeeper error - manual review"]
        
        return verdict
    
    # =========================================================================
    # Stage 2: LLM Consensus (Optional)
    # =========================================================================
    
    def _apply_llm_consensus(
        self, 
        signal: Dict, 
        verdict: EditorialVerdict
    ) -> EditorialVerdict:
        """
        Apply multi-model LLM consensus for topic validation.
        
        Note: This requires EnsembleOrchestrator providers to be configured.
        Currently uses a simplified synchronous approach.
        """
        try:
            # For now, use a simplified single-model check
            # Full EnsembleOrchestrator integration would require async
            # and configured LLM providers (GPT-4, Claude, Gemini)
            
            # Simulate consensus based on gatekeeper score
            # In production, this would call EnsembleOrchestrator
            score = verdict.gatekeeper_score
            
            if score >= 90:
                verdict.consensus_level = ConsensusLevel.AUTHORITATIVE
                verdict.consensus_score = 95.0
            elif score >= 70:
                verdict.consensus_level = ConsensusLevel.HIGH
                verdict.consensus_score = 80.0
            elif score >= 40:
                verdict.consensus_level = ConsensusLevel.DISPUTED
                verdict.consensus_score = 55.0
            else:
                verdict.consensus_level = ConsensusLevel.UNTRUSTED
                verdict.consensus_score = 25.0
            
            verdict.models_used = ["gatekeeper_derived"]
            
            # Check against minimum level
            min_level = self._parse_consensus_level(self.consensus_min_level)
            if self._consensus_level_value(verdict.consensus_level) < self._consensus_level_value(min_level):
                verdict.approved = False
                verdict.synthesis = f"Consensus too low ({verdict.consensus_level.value} < {min_level.value})"
            
        except Exception as e:
            logger.warning("consensus_error", error=str(e))
            verdict.consensus_level = ConsensusLevel.SKIPPED
        
        return verdict
    
    def _parse_consensus_level(self, level_str: str) -> ConsensusLevel:
        """Parse consensus level string to enum."""
        mapping = {
            "authoritative": ConsensusLevel.AUTHORITATIVE,
            "high": ConsensusLevel.HIGH,
            "disputed": ConsensusLevel.DISPUTED,
            "untrusted": ConsensusLevel.UNTRUSTED
        }
        return mapping.get(level_str.lower(), ConsensusLevel.HIGH)
    
    def _consensus_level_value(self, level: ConsensusLevel) -> int:
        """Get numeric value for consensus level comparison."""
        values = {
            ConsensusLevel.AUTHORITATIVE: 4,
            ConsensusLevel.HIGH: 3,
            ConsensusLevel.DISPUTED: 2,
            ConsensusLevel.UNTRUSTED: 1,
            ConsensusLevel.SKIPPED: 0
        }
        return values.get(level, 0)
    
    # =========================================================================
    # Stage 3: Red-Team Challenge
    # =========================================================================
    
    def _apply_red_team(
        self, 
        signal: Dict, 
        verdict: EditorialVerdict
    ) -> EditorialVerdict:
        """
        Apply adversarial red-team challenge.
        Uses ConsensusEngine._agent_red_team() for counterarguments.
        """
        try:
            # Build thesis for red-team to challenge
            thesis = {
                "focus": "Topic Selection",
                "content": f"This topic '{signal['title']}' is newsworthy for the {signal['sector']} sector."
            }
            
            red_team_result = self.consensus_engine._agent_red_team(thesis, signal)
            
            verdict.red_team_challenge = red_team_result.get("content", "")
            
            # Red-team doesn't reject topics, just adds dissenting views
            if red_team_result.get("challenge"):
                verdict.dissenting_views.append(red_team_result["challenge"])
            
        except Exception as e:
            logger.warning("red_team_error", error=str(e))
            verdict.red_team_challenge = "Red-team analysis unavailable"
        
        return verdict
    
    # =========================================================================
    # Stage 4: Synthesis
    # =========================================================================
    
    def _synthesize_verdict(
        self, 
        signal: Dict, 
        verdict: EditorialVerdict
    ) -> EditorialVerdict:
        """
        Synthesize final verdict with rationale.
        Uses ConsensusEngine._agent_strategist() pattern.
        """
        if verdict.approved:
            parts = []
            
            if verdict.gatekeeper_score >= 80:
                parts.append("High strategic value")
            elif verdict.gatekeeper_score >= 60:
                parts.append("Moderate strategic value")
            else:
                parts.append("Marginal strategic value")
            
            if verdict.consensus_level != ConsensusLevel.SKIPPED:
                parts.append(f"{verdict.consensus_level.value} consensus")
            
            if verdict.gatekeeper_reasons:
                parts.append(f"Factors: {', '.join(verdict.gatekeeper_reasons[:2])}")
            
            verdict.synthesis = ". ".join(parts) + "."
        
        return verdict
    
    # =========================================================================
    # Helpers
    # =========================================================================
    
    def _map_sector(self, sector: str) -> str:
        """Map internal sector names to ConsensusEngine sector names."""
        mapping = {
            "cybersecurity": "Cyber",
            "physical_security": "Industrial",
            "fire_safety": "Industrial",
            "compliance": "Banking",
            "risk_management": "Industrial",
            "healthcare": "Healthcare"
        }
        return mapping.get(sector.lower(), "General")


# =============================================================================
# CLI for Testing
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Editorial Validator CLI")
    parser.add_argument("--topic", type=str, required=True, help="Topic to validate")
    parser.add_argument("--sector", type=str, default="general", help="Topic sector")
    parser.add_argument("--type", type=str, default="News", help="Content type")
    args = parser.parse_args()
    
    validator = EditorialValidator()
    verdict = validator.validate_topic(
        topic=args.topic,
        sector=args.sector,
        content_type=args.type
    )
    
    print(f"\n{'='*60}")
    print("EDITORIAL VERDICT")
    print(f"{'='*60}")
    print(f"Topic: {args.topic}")
    print(f"Approved: {'✓' if verdict.approved else '✗'}")
    print(f"\n📊 Gatekeeper Score: {verdict.gatekeeper_score}/100")
    print(f"   Reasons: {', '.join(verdict.gatekeeper_reasons)}")
    print(f"\n🤝 Consensus: {verdict.consensus_level.value} ({verdict.consensus_score})")
    print(f"\n⚔️ Red-Team Challenge:")
    print(f"   {verdict.red_team_challenge[:200]}...")
    print(f"\n📝 Synthesis: {verdict.synthesis}")
    print(f"{'='*60}\n")
