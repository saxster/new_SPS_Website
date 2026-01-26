"""
TopicProposer: The Editorial Brain 🧠
Discovers and proposes topics automatically for the Autonomous Newsroom.

This is the heart of the system - it makes the newsroom truly autonomous
by continuously discovering what's worth writing about.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json

from config.manager import config
from shared.logger import get_logger
from skills.content_brain import ContentBrain
from skills.gemini_client import GeminiAgent
from skills.news_miner import NewsMiner
from skills.editorial_validator import EditorialValidator

logger = get_logger("TopicProposer")


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class Signal:
    """Raw signal from any source (news, trends, gaps)."""
    id: str
    source: str           # 'news', 'trend', 'gap', 'calendar'
    title: str
    summary: str
    url: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    sector: str = "general"
    urgency: int = 5      # 1-10 scale
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TopicProposal:
    """A proposed topic ready for the content queue."""
    id: str
    topic: str                    # The actual topic string
    content_type: str             # 'News', 'Guide', 'Analysis'
    rationale: str                # Why this topic matters NOW
    signals: List[str]            # IDs of signals that led to this
    score: float                  # Composite score 0-1
    priority: str                 # 'urgent', 'high', 'medium', 'low'
    suggested_angle: str          # Unique angle to cover
    target_audience: str = "Security Professionals"
    estimated_demand: int = 5     # 1-10
    freshness_days: int = 7       # Days until stale
    sources_available: int = 0    # Pre-checked source count
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "topic": self.topic,
            "content_type": self.content_type,
            "rationale": self.rationale,
            "signals": self.signals,
            "score": self.score,
            "priority": self.priority,
            "suggested_angle": self.suggested_angle,
            "target_audience": self.target_audience,
            "estimated_demand": self.estimated_demand,
            "freshness_days": self.freshness_days,
            "sources_available": self.sources_available
        }


# =============================================================================
# TopicProposer Agent
# =============================================================================

class TopicProposer:
    """
    The Editorial Brain - Discovers and proposes topics automatically.
    
    Pipeline:
    1. Gather signals from multiple sources (news, trends, gaps)
    2. Extract potential topics using LLM
    3. Deduplicate against existing content
    4. Score and rank by value
    5. Generate proposals with rationale
    """
    
    def __init__(
        self, 
        brain: Optional[ContentBrain] = None,
        llm: Optional[GeminiAgent] = None,
        editorial_validator: Optional[EditorialValidator] = None
    ):
        self.brain = brain or ContentBrain()
        self.llm = llm or GeminiAgent()
        self.news_miner = NewsMiner()
        self.editorial_validator = editorial_validator or EditorialValidator()
        
        # Configuration
        self.max_proposals = config.get("topic_proposer.max_proposals_per_run", 10)
        self.auto_queue_threshold = config.get("topic_proposer.auto_queue_threshold", 0.8)
        self.focus_sectors = config.get("topic_proposer.focus_sectors", [
            "physical_security", "cybersecurity", "fire_safety", 
            "compliance", "risk_management"
        ])
        
        # Scoring weights
        self.weights = config.get("topic_proposer.scoring", {
            "timeliness": 0.25,
            "demand": 0.25,
            "coverage_gap": 0.20,
            "source_availability": 0.15,
            "brand_fit": 0.15
        })
        
        logger.info("topic_proposer_initialized", 
                   max_proposals=self.max_proposals,
                   focus_sectors=self.focus_sectors,
                   editorial_enabled=self.editorial_validator.enabled)
    
    # =========================================================================
    # Main Entry Point
    # =========================================================================
    
    def discover_topics(self) -> List[TopicProposal]:
        """
        Main entry point - run periodically to discover new topics.
        
        Returns:
            List of TopicProposal objects, ranked by score
        """
        logger.info("discovery_started")
        
        # 1. Gather signals from all sources
        signals = self._gather_signals()
        logger.info("signals_gathered", count=len(signals))
        
        if not signals:
            logger.warning("no_signals_found")
            return []
        
        # 2. Extract potential topics using LLM
        raw_topics = self._extract_topics(signals)
        logger.info("topics_extracted", count=len(raw_topics))
        
        # 3. Deduplicate against existing content
        unique_topics = self._deduplicate(raw_topics)
        logger.info("topics_deduplicated", 
                   original=len(raw_topics), 
                   unique=len(unique_topics))
        
        # 4. Score and rank
        scored_topics = self._score_topics(unique_topics)
        
        # 5. NEW: Validate through editorial pipeline (gatekeeper + red-team)
        validated_topics = self._validate_with_editorial_board(scored_topics)
        logger.info("topics_validated",
                   original=len(scored_topics),
                   approved=len(validated_topics))
        
        # 6. Generate full proposals with rationale
        proposals = self._generate_proposals(validated_topics[:self.max_proposals])
        logger.info("proposals_generated", count=len(proposals))
        
        return proposals
    
    # =========================================================================
    # Signal Gathering
    # =========================================================================
    
    def _gather_signals(self) -> List[Signal]:
        """Gather signals from all configured sources."""
        signals = []
        
        # Source 1: News signals from NewsMiner
        signals.extend(self._gather_news_signals())
        
        # Source 2: Gap signals from ContentBrain
        signals.extend(self._gather_gap_signals())
        
        # Source 3: Sector-specific news
        for sector in self.focus_sectors:
            signals.extend(self._gather_sector_signals(sector))
        
        return signals
    
    def _gather_news_signals(self) -> List[Signal]:
        """Fetch recent news signals."""
        signals = []
        
        # Default security query
        raw_signals = self.news_miner.fetch_signals(
            query="security breach OR cyber attack OR fire incident India",
            sector="General",
            limit=10
        )
        
        for item in raw_signals:
            if "error" in item:
                continue
            
            signal_id = hashlib.md5(item.get("title", "").encode()).hexdigest()[:12]
            signals.append(Signal(
                id=f"news_{signal_id}",
                source="news",
                title=item.get("title", ""),
                summary=item.get("summary", ""),
                url=item.get("url"),
                sector=item.get("sector", "General"),
                urgency=8,  # News is time-sensitive
                metadata={"query_used": item.get("query_used", "")}
            ))
        
        return signals
    
    def _gather_sector_signals(self, sector: str) -> List[Signal]:
        """Fetch signals for a specific sector."""
        signals = []
        
        # Map sector to search query
        sector_queries = {
            "physical_security": "CCTV security surveillance India",
            "cybersecurity": "data breach ransomware cyber attack India",
            "fire_safety": "fire incident factory building India",
            "compliance": "RBI SEBI regulatory compliance India",
            "risk_management": "enterprise risk security audit India"
        }
        
        query = sector_queries.get(sector, f"{sector} India")
        
        raw_signals = self.news_miner.fetch_signals(
            query=query,
            sector=sector,
            limit=5
        )
        
        for item in raw_signals:
            if "error" in item:
                continue
            
            signal_id = hashlib.md5(item.get("title", "").encode()).hexdigest()[:12]
            signals.append(Signal(
                id=f"sector_{signal_id}",
                source="sector_news",
                title=item.get("title", ""),
                summary=item.get("summary", ""),
                url=item.get("url"),
                sector=sector,
                urgency=6,
                metadata={"sector": sector}
            ))
        
        return signals
    
    def _gather_gap_signals(self) -> List[Signal]:
        """Identify content gaps from ContentBrain."""
        signals = []
        
        try:
            # Get recent articles to understand coverage
            stats = self.brain.get_stats()
            topics = self.brain.list_topics()
            
            # Identify sectors with low coverage
            covered_sectors = set()
            for topic in topics:
                if isinstance(topic, dict):
                    sector = topic.get("sector", "general")
                    covered_sectors.add(sector.lower())
            
            # Generate gap signals for uncovered sectors
            for sector in self.focus_sectors:
                if sector.lower() not in covered_sectors:
                    signals.append(Signal(
                        id=f"gap_{sector}",
                        source="gap",
                        title=f"Coverage gap: {sector.replace('_', ' ').title()}",
                        summary=f"No recent content covering {sector}. Consider writing about this sector.",
                        sector=sector,
                        urgency=4,  # Gaps are important but not urgent
                        metadata={"gap_type": "sector_coverage"}
                    ))
            
            logger.info("gap_analysis_complete", gaps_found=len(signals))
            
        except Exception as e:
            logger.warning("gap_analysis_failed", error=str(e))
        
        return signals
    
    # =========================================================================
    # Topic Extraction (LLM)
    # =========================================================================
    
    def _extract_topics(self, signals: List[Signal]) -> List[Dict]:
        """Use LLM to extract potential topics from signals."""
        
        # Format signals for LLM
        signals_text = "\n".join([
            f"- [{s.source}] {s.title}: {s.summary[:200]}"
            for s in signals[:20]  # Limit to avoid context overflow
        ])
        
        prompt = f"""You are an Editorial Director for a security publication focused on India.

Analyze these signals and extract SPECIFIC, ACTIONABLE article topics.

SIGNALS:
{signals_text}

FOCUS AREAS: Physical Security, Cybersecurity, Fire Safety, Regulatory Compliance, Risk Management

For each topic, provide:
1. topic: A specific, compelling article topic (not generic)
2. content_type: "News" (timely), "Guide" (evergreen), or "Analysis" (deep-dive)
3. angle: The unique perspective or hook
4. audience: Who specifically benefits
5. demand: 1-10 how likely people search for this

Return a JSON array of 5-8 topics. Be SPECIFIC - not "Cybersecurity Guide" but "How Indian Banks Can Implement Zero Trust After the ABC Breach".

Return ONLY valid JSON array, no markdown."""

        try:
            result = self.llm.generate_json(prompt)
            if isinstance(result, list):
                return result
            return []
        except Exception as e:
            logger.error("topic_extraction_failed", error=str(e))
            return []
    
    # =========================================================================
    # Deduplication
    # =========================================================================
    
    def _deduplicate(self, topics: List[Dict]) -> List[Dict]:
        """Remove topics too similar to existing content."""
        if not topics:
            return []
        
        # Get existing articles from ContentBrain
        try:
            existing = self.brain.list_topics()
            existing_titles = {
                t.get("topic", "").lower() 
                for t in existing 
                if isinstance(t, dict)
            }
        except Exception:
            existing_titles = set()
        
        unique = []
        for topic in topics:
            topic_text = topic.get("topic", "").lower()
            
            # Simple similarity check
            is_duplicate = False
            for existing_title in existing_titles:
                if self._similarity(topic_text, existing_title) > 0.7:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique.append(topic)
        
        return unique
    
    def _similarity(self, a: str, b: str) -> float:
        """Simple word overlap similarity."""
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        
        if not words_a or not words_b:
            return 0.0
        
        intersection = words_a.intersection(words_b)
        union = words_a.union(words_b)
        
        return len(intersection) / len(union)
    
    # =========================================================================
    # Scoring
    # =========================================================================
    
    def _score_topics(self, topics: List[Dict]) -> List[Dict]:
        """Score topics using multi-factor analysis."""
        
        for topic in topics:
            # Timeliness: News = 1.0, Guide = 0.5, Analysis = 0.7
            content_type = topic.get("content_type", "Guide")
            timeliness = {"News": 1.0, "Guide": 0.5, "Analysis": 0.7}.get(content_type, 0.5)
            
            # Demand: From LLM estimation (normalize to 0-1)
            demand = topic.get("demand", 5) / 10.0
            
            # Coverage gap: Assume 0.7 since we already deduplicated
            coverage_gap = 0.7
            
            # Source availability: Would need to check, assume 0.5
            source_availability = 0.5
            
            # Brand fit: Check if matches focus sectors
            topic_text = topic.get("topic", "").lower()
            brand_fit = 0.8 if any(s in topic_text for s in self.focus_sectors) else 0.5
            
            # Compute weighted score
            score = (
                timeliness * self.weights.get("timeliness", 0.25) +
                demand * self.weights.get("demand", 0.25) +
                coverage_gap * self.weights.get("coverage_gap", 0.20) +
                source_availability * self.weights.get("source_availability", 0.15) +
                brand_fit * self.weights.get("brand_fit", 0.15)
            )
            
            topic["score"] = round(score, 3)
            topic["priority"] = self._score_to_priority(score)
        
        # Sort by score descending
        return sorted(topics, key=lambda t: t.get("score", 0), reverse=True)
    
    def _score_to_priority(self, score: float) -> str:
        """Convert numeric score to priority label."""
        if score >= 0.8:
            return "urgent"
        elif score >= 0.6:
            return "high"
        elif score >= 0.4:
            return "medium"
        else:
            return "low"
    
    # =========================================================================
    # Editorial Validation
    # =========================================================================
    
    def _validate_with_editorial_board(self, topics: List[Dict]) -> List[Dict]:
        """
        Validate topics through the Editorial Board pipeline.
        
        Pipeline:
        1. Gatekeeper - Fast rule-based filtering (ConsensusEngine)
        2. LLM Consensus - Multi-model voting (optional, expensive)
        3. Red-Team Challenge - Adversarial counterarguments
        
        Args:
            topics: List of scored topic dicts
            
        Returns:
            Filtered list of approved topics with editorial metadata
        """
        if not self.editorial_validator.enabled:
            return topics
        
        approved = []
        
        for topic in topics:
            verdict = self.editorial_validator.validate_topic(
                topic=topic.get("topic", ""),
                content_type=topic.get("content_type", "News"),
                sector=self._infer_sector(topic.get("topic", "")),
                summary=topic.get("angle", "")
            )
            
            if verdict.approved:
                # Enrich topic with editorial metadata
                topic["editorial"] = {
                    "gatekeeper_score": verdict.gatekeeper_score,
                    "consensus_level": verdict.consensus_level.value,
                    "red_team_challenge": verdict.red_team_challenge[:200] if verdict.red_team_challenge else "",
                    "synthesis": verdict.synthesis
                }
                approved.append(topic)
            else:
                logger.debug(
                    "topic_rejected",
                    topic=topic.get("topic", "")[:50],
                    reason=verdict.synthesis
                )
        
        return approved
    
    def _infer_sector(self, topic: str) -> str:
        """Infer sector from topic text."""
        topic_lower = topic.lower()
        
        if any(kw in topic_lower for kw in ["cyber", "ransomware", "breach", "hack", "data"]):
            return "cybersecurity"
        elif any(kw in topic_lower for kw in ["fire", "blaze", "explosion", "smoke"]):
            return "fire_safety"
        elif any(kw in topic_lower for kw in ["cctv", "surveillance", "guard", "access"]):
            return "physical_security"
        elif any(kw in topic_lower for kw in ["rbi", "sebi", "compliance", "regulation", "policy"]):
            return "compliance"
        elif any(kw in topic_lower for kw in ["risk", "audit", "assessment"]):
            return "risk_management"
        else:
            return "general"
    
    # =========================================================================
    # Proposal Generation
    # =========================================================================
    
    def _generate_proposals(self, scored_topics: List[Dict]) -> List[TopicProposal]:
        """Convert scored topics to full proposals."""
        proposals = []
        
        for topic in scored_topics:
            proposal_id = hashlib.md5(
                topic.get("topic", "").encode()
            ).hexdigest()[:12]
            
            proposals.append(TopicProposal(
                id=f"prop_{proposal_id}",
                topic=topic.get("topic", ""),
                content_type=topic.get("content_type", "Guide"),
                rationale=f"Based on recent signals. Angle: {topic.get('angle', 'General coverage')}",
                signals=[],  # Would link to actual signal IDs
                score=topic.get("score", 0),
                priority=topic.get("priority", "medium"),
                suggested_angle=topic.get("angle", ""),
                target_audience=topic.get("audience", "Security Professionals"),
                estimated_demand=topic.get("demand", 5),
                freshness_days=7 if topic.get("content_type") == "News" else 30
            ))
        
        return proposals
    
    # =========================================================================
    # Queue Management
    # =========================================================================
    
    def queue_proposals(self, proposals: List[TopicProposal], auto_queue: bool = False) -> int:
        """
        Add proposals to the ContentBrain topic queue.
        
        Args:
            proposals: List of TopicProposal objects
            auto_queue: If True, only queue proposals above threshold
            
        Returns:
            Number of proposals queued
        """
        queued = 0
        
        for proposal in proposals:
            # Check auto-queue threshold
            if auto_queue and proposal.score < self.auto_queue_threshold:
                logger.info("proposal_below_threshold", 
                          topic=proposal.topic[:50],
                          score=proposal.score)
                continue
            
            try:
                self.brain.add_topic_proposal({
                    "topic": proposal.topic,
                    "content_type": proposal.content_type,
                    "source": "topic_proposer",
                    "priority": proposal.priority,
                    "target_audience": proposal.target_audience,
                    "metadata": proposal.to_dict()
                })
                queued += 1
                logger.info("proposal_queued", 
                          topic=proposal.topic[:50],
                          priority=proposal.priority)
                
            except Exception as e:
                logger.error("queue_failed", topic=proposal.topic[:50], error=str(e))
        
        return queued


# =============================================================================
# CLI for Testing
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="TopicProposer CLI")
    parser.add_argument("--discover", action="store_true", help="Run discovery")
    parser.add_argument("--queue", action="store_true", help="Queue discovered topics")
    parser.add_argument("--limit", type=int, default=5, help="Max proposals")
    args = parser.parse_args()
    
    proposer = TopicProposer()
    
    if args.discover:
        print("\n🧠 TopicProposer: Discovering topics...\n")
        proposals = proposer.discover_topics()
        
        for i, p in enumerate(proposals[:args.limit], 1):
            print(f"{i}. [{p.priority.upper()}] {p.topic}")
            print(f"   Type: {p.content_type} | Score: {p.score:.2f}")
            print(f"   Angle: {p.suggested_angle}")
            print()
        
        if args.queue:
            queued = proposer.queue_proposals(proposals)
            print(f"\n✓ Queued {queued} topics")
    else:
        parser.print_help()
