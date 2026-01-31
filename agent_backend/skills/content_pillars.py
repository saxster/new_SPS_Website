"""
ContentPillarManager: Reader-centric content pillar management.

Manages content pillars for reader-centric organization:
- scam_watch: Real-time fraud alerts (20%)
- economic_security: Markets, investment fraud (15%)
- personal_security: Home, travel, digital safety (15%)
- senior_safety: Elder-specific protection (10%)
- business_security: Practical SMB guides (20%)
- sector_intelligence: Industry deep dives (10%)
- product_reviews: Security product evaluations (10%)

Features:
- Pillar configuration and routing
- Content balance tracking
- Persona-based recommendations
- Health scoring and rebalancing
"""

import os
import sys
from typing import List, Dict, Optional, Any
from datetime import datetime

# Allow running from repo root without PYTHONPATH
AGENT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if AGENT_ROOT not in sys.path:
    sys.path.insert(0, AGENT_ROOT)

from config.manager import config
from shared.logger import get_logger
from shared.models import ContentPillar, AudiencePersona, SourcedTopic

logger = get_logger("ContentPillars")


# Default pillar definitions
DEFAULT_PILLARS = {
    "scam_watch": ContentPillar(
        slug="scam_watch",
        name="Scam Watch",
        priority=1,
        target_mix=0.20,
        sources=["scam_miner", "regulatory_miner"],
        target_personas=["citizen", "senior"],
        description="Real-time fraud alerts, prevention, reporting",
        icon="shield-alert",
    ),
    "economic_security": ContentPillar(
        slug="economic_security",
        name="Economic Security",
        priority=2,
        target_mix=0.15,
        sources=["market_miner", "regulatory_miner"],
        target_personas=["citizen", "smb", "compliance"],
        description="Markets, investment fraud, corporate crime",
        icon="trending-up",
    ),
    "personal_security": ContentPillar(
        slug="personal_security",
        name="Personal Security",
        priority=3,
        target_mix=0.15,
        sources=["serp_miner", "thinktank_miner"],
        target_personas=["citizen"],
        description="Home, travel, digital, physical safety",
        icon="user-shield",
    ),
    "senior_safety": ContentPillar(
        slug="senior_safety",
        name="Senior Safety",
        priority=4,
        target_mix=0.10,
        sources=["scam_miner", "serp_miner"],
        target_personas=["senior"],
        description="Elder-specific threats and protection",
        icon="heart",
    ),
    "business_security": ContentPillar(
        slug="business_security",
        name="Business Security",
        priority=5,
        target_mix=0.20,
        sources=["regulatory_miner", "thinktank_miner", "serp_miner"],
        target_personas=["smb", "professional"],
        description="Practical SMB security guides",
        icon="building",
    ),
    "sector_intelligence": ContentPillar(
        slug="sector_intelligence",
        name="Sector Intelligence",
        priority=6,
        target_mix=0.10,
        sources=["thinktank_miner", "regulatory_miner"],
        target_personas=["professional", "compliance"],
        description="Deep dives by industry",
        icon="layers",
    ),
    "product_reviews": ContentPillar(
        slug="product_reviews",
        name="Product Reviews",
        priority=7,
        target_mix=0.10,
        sources=["consumer_miner"],
        target_personas=["smb", "professional"],
        description="Security products and services evaluated",
        icon="star",
    ),
}

# Default persona definitions
DEFAULT_PERSONAS = {
    "citizen": AudiencePersona(
        id="citizen",
        name="General Citizen",
        complexity_level="basic",
        actionability_weight=0.9,
        preferred_pillars=["scam_watch", "personal_security", "economic_security"],
        description="General public seeking actionable personal safety advice",
    ),
    "senior": AudiencePersona(
        id="senior",
        name="Senior Citizen",
        complexity_level="basic",
        actionability_weight=1.0,
        preferred_pillars=["scam_watch", "senior_safety", "personal_security"],
        description="60+ individuals needing simple, clear fraud prevention",
    ),
    "smb": AudiencePersona(
        id="smb",
        name="SMB Owner",
        complexity_level="intermediate",
        actionability_weight=0.85,
        preferred_pillars=["business_security", "scam_watch", "product_reviews"],
        description="Small business owners seeking budget-conscious security",
    ),
    "professional": AudiencePersona(
        id="professional",
        name="Security Professional",
        complexity_level="advanced",
        actionability_weight=0.6,
        preferred_pillars=[
            "sector_intelligence",
            "business_security",
            "product_reviews",
        ],
        description="Security managers requiring technical depth",
    ),
    "compliance": AudiencePersona(
        id="compliance",
        name="Compliance Officer",
        complexity_level="advanced",
        actionability_weight=0.7,
        preferred_pillars=[
            "sector_intelligence",
            "business_security",
            "economic_security",
        ],
        description="Regulatory officers tracking deadlines and policy updates",
    ),
}


class ContentPillarManager:
    """
    Manages content pillars for reader-centric organization.

    Provides pillar routing, balance tracking, and persona-based
    recommendations for the editorial pipeline.
    """

    def __init__(self, brain=None):
        """
        Initialize ContentPillarManager.

        Args:
            brain: Optional ContentBrain instance for database access
        """
        self.brain = brain
        self.pillars = self._load_pillars()
        self.personas = self._load_personas()

        # Current article counts (populated from brain if available)
        self._article_counts: Dict[str, int] = {}

    def _load_pillars(self) -> Dict[str, ContentPillar]:
        """Load pillars from config or use defaults."""
        pillar_config = config.get("content_pillars", {})

        if not pillar_config:
            logger.info("using_default_pillars")
            return DEFAULT_PILLARS.copy()

        pillars = {}
        for slug, cfg in pillar_config.items():
            try:
                pillar = ContentPillar(
                    slug=slug,
                    name=cfg.get("name", slug),
                    priority=cfg.get("priority", 5),
                    target_mix=cfg.get("target_mix", 0.1),
                    sources=cfg.get("sources", []),
                    target_personas=cfg.get("target_personas", []),
                    description=cfg.get("description", ""),
                    icon=cfg.get("icon", ""),
                )
                pillars[slug] = pillar
            except Exception as e:
                logger.warning("pillar_load_error", slug=slug, error=str(e))

        if not pillars:
            return DEFAULT_PILLARS.copy()

        logger.info("pillars_loaded", count=len(pillars))
        return pillars

    def _load_personas(self) -> Dict[str, AudiencePersona]:
        """Load personas from config or use defaults."""
        persona_config = config.get("personas", {})

        if not persona_config:
            logger.info("using_default_personas")
            return DEFAULT_PERSONAS.copy()

        personas = {}
        for pid, cfg in persona_config.items():
            try:
                persona = AudiencePersona(
                    id=pid,
                    name=cfg.get("name", pid),
                    complexity_level=cfg.get("complexity_level", "intermediate"),
                    actionability_weight=cfg.get("actionability_weight", 0.5),
                    preferred_pillars=cfg.get("preferred_pillars", []),
                    description=cfg.get("description", ""),
                )
                personas[pid] = persona
            except Exception as e:
                logger.warning("persona_load_error", id=pid, error=str(e))

        if not personas:
            return DEFAULT_PERSONAS.copy()

        logger.info("personas_loaded", count=len(personas))
        return personas

    def get_pillar(self, slug: str) -> Optional[ContentPillar]:
        """
        Get a pillar by slug.

        Args:
            slug: Pillar slug

        Returns:
            ContentPillar or None
        """
        return self.pillars.get(slug)

    def get_all_pillars(self) -> List[ContentPillar]:
        """Get all pillars sorted by priority."""
        return sorted(self.pillars.values(), key=lambda p: p.priority)

    def get_persona(self, persona_id: str) -> Optional[AudiencePersona]:
        """
        Get a persona by ID.

        Args:
            persona_id: Persona ID

        Returns:
            AudiencePersona or None
        """
        return self.personas.get(persona_id)

    def route_topic_to_pillar(self, topic: SourcedTopic) -> str:
        """
        Route a topic to the most appropriate pillar.

        Uses source type, tags, and content analysis to determine
        the best pillar for the topic.

        Args:
            topic: SourcedTopic to route

        Returns:
            Pillar slug
        """
        # If already assigned, return that
        if topic.primary_pillar:
            return topic.primary_pillar

        # Route based on source type
        source_routing = {
            "scam": "scam_watch",
            "market": "economic_security",
            "consumer": "product_reviews",
            "regulatory": "business_security",
            "thinktank": "sector_intelligence",
            "calendar": self._route_calendar_topic(topic),
            "breaking": self._route_breaking_topic(topic),
            "gap": "business_security",
        }

        pillar = source_routing.get(topic.source_type, "business_security")

        # Check tags for more specific routing
        tag_routing = self._route_by_tags(topic.tags)
        if tag_routing:
            pillar = tag_routing

        logger.debug(
            "topic_routed",
            topic=topic.title[:50],
            pillar=pillar,
            source_type=topic.source_type,
        )

        return pillar

    def _route_calendar_topic(self, topic: SourcedTopic) -> str:
        """Route calendar-based topics."""
        tags = [t.lower() for t in topic.tags]

        if any(t in tags for t in ["scam", "fraud", "cybercrime"]):
            return "scam_watch"
        if any(t in tags for t in ["senior", "elder"]):
            return "senior_safety"
        if any(t in tags for t in ["finance", "market", "sebi", "rbi"]):
            return "economic_security"
        if any(t in tags for t in ["compliance", "regulation", "deadline"]):
            return "business_security"

        return "personal_security"

    def _route_breaking_topic(self, topic: SourcedTopic) -> str:
        """Route breaking news topics."""
        text = f"{topic.title} {' '.join(topic.tags)}".lower()

        if any(kw in text for kw in ["scam", "fraud", "cheat", "dupe"]):
            return "scam_watch"
        if any(kw in text for kw in ["sebi", "rbi", "ed", "market"]):
            return "economic_security"
        if any(kw in text for kw in ["senior", "elder", "pensioner"]):
            return "senior_safety"

        return "personal_security"

    def _route_by_tags(self, tags: List[str]) -> Optional[str]:
        """Route based on topic tags."""
        tags_lower = [t.lower() for t in tags]

        tag_pillar_map = {
            "scam_watch": ["scam", "fraud", "phishing", "otp", "digital_arrest"],
            "economic_security": ["sebi", "rbi", "market", "investment", "ed"],
            "senior_safety": ["senior", "elder", "pension", "retirement"],
            "personal_security": ["home", "travel", "cyber", "privacy"],
            "business_security": ["compliance", "regulation", "policy", "smb"],
            "sector_intelligence": ["sector", "industry", "analysis", "report"],
            "product_reviews": ["review", "product", "comparison", "test"],
        }

        for pillar, keywords in tag_pillar_map.items():
            if any(kw in tags_lower for kw in keywords):
                return pillar

        return None

    def get_pillar_health(self) -> Dict[str, Dict]:
        """
        Get health metrics for all pillars.

        Returns:
            Dictionary with pillar health data
        """
        self._refresh_article_counts()

        total_articles = sum(self._article_counts.values()) or 1

        health = {}
        for slug, pillar in self.pillars.items():
            current_count = self._article_counts.get(slug, 0)
            current_ratio = current_count / total_articles
            target_ratio = pillar.target_mix

            # Calculate health score (0-100)
            # 100 = on target, lower = further from target
            deviation = abs(target_ratio - current_ratio)
            health_score = max(0, 100 - (deviation * 500))  # 20% deviation = 0 health

            health[slug] = {
                "name": pillar.name,
                "priority": pillar.priority,
                "article_count": current_count,
                "current_ratio": round(current_ratio, 3),
                "target_ratio": target_ratio,
                "deviation": round(deviation, 3),
                "health_score": round(health_score, 1),
                "status": self._get_health_status(health_score),
                "needs_content": current_ratio < target_ratio - 0.03,
            }

        return health

    def _get_health_status(self, score: float) -> str:
        """Get health status label."""
        if score >= 80:
            return "healthy"
        if score >= 60:
            return "moderate"
        if score >= 40:
            return "needs_attention"
        return "critical"

    def _refresh_article_counts(self):
        """Refresh article counts from brain."""
        if not self.brain:
            # Use mock data if no brain
            self._article_counts = {slug: 0 for slug in self.pillars}
            return

        try:
            # Query brain for pillar counts
            # This would be implemented when brain has pillar tracking
            stats = self.brain.get_stats()
            # For now, use empty counts
            self._article_counts = {slug: 0 for slug in self.pillars}
        except Exception as e:
            logger.warning("article_count_refresh_error", error=str(e))

    def get_rebalance_recommendations(self) -> List[Dict]:
        """
        Get recommendations for content rebalancing.

        Returns:
            List of pillar recommendations sorted by priority
        """
        health = self.get_pillar_health()

        recommendations = []
        for slug, data in health.items():
            if data["needs_content"]:
                pillar = self.pillars[slug]
                recommendations.append(
                    {
                        "pillar": slug,
                        "pillar_name": data["name"],
                        "priority": data["priority"],
                        "health_score": data["health_score"],
                        "current_ratio": data["current_ratio"],
                        "target_ratio": data["target_ratio"],
                        "deficit": round(
                            data["target_ratio"] - data["current_ratio"], 3
                        ),
                        "sources": pillar.sources,
                        "target_personas": pillar.target_personas,
                        "action": f"Increase {data['name']} content by sourcing from {', '.join(pillar.sources)}",
                    }
                )

        # Sort by priority (lower = more important) and deficit
        recommendations.sort(key=lambda r: (r["priority"], -r["deficit"]))

        return recommendations

    def get_persona_recommendations(self, persona_id: str) -> Dict:
        """
        Get content recommendations for a specific persona.

        Args:
            persona_id: Target persona

        Returns:
            Dictionary with persona-specific recommendations
        """
        persona = self.personas.get(persona_id)
        if not persona:
            return {"error": f"Unknown persona: {persona_id}"}

        # Get preferred pillars
        preferred_pillars = [
            self.pillars.get(slug)
            for slug in persona.preferred_pillars
            if slug in self.pillars
        ]

        return {
            "persona": {
                "id": persona.id,
                "name": persona.name,
                "complexity_level": persona.complexity_level,
                "actionability_weight": persona.actionability_weight,
            },
            "preferred_pillars": [
                {
                    "slug": p.slug,
                    "name": p.name,
                    "description": p.description,
                }
                for p in preferred_pillars
            ],
            "content_preferences": {
                "complexity": persona.complexity_level,
                "actionability": "high"
                if persona.actionability_weight > 0.7
                else "medium",
            },
            "sources_to_mine": list(
                set(source for p in preferred_pillars for source in p.sources)
            ),
        }

    def get_pillar_stats(self) -> Dict:
        """Get overall pillar statistics."""
        health = self.get_pillar_health()

        return {
            "total_pillars": len(self.pillars),
            "total_personas": len(self.personas),
            "healthy_pillars": sum(
                1 for h in health.values() if h["status"] == "healthy"
            ),
            "needs_attention": sum(
                1
                for h in health.values()
                if h["status"] in ["needs_attention", "critical"]
            ),
            "pillar_health": health,
        }


if __name__ == "__main__":
    # Quick test
    manager = ContentPillarManager()

    print("Content Pillars:")
    for pillar in manager.get_all_pillars():
        print(f"  {pillar.priority}. {pillar.name} ({pillar.target_mix:.0%})")

    print("\nPersonas:")
    for pid, persona in manager.personas.items():
        print(f"  - {persona.name}: {persona.preferred_pillars}")

    print("\nPillar Health:")
    health = manager.get_pillar_health()
    for slug, data in health.items():
        print(f"  {slug}: {data['health_score']:.1f} ({data['status']})")

    print("\nRebalance Recommendations:")
    recs = manager.get_rebalance_recommendations()
    for rec in recs[:3]:
        print(f"  - {rec['pillar_name']}: {rec['action']}")
