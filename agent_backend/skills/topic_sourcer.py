"""
TopicSourcer: Orchestrates all topic sourcing strategies.

Combines multiple sourcing channels:
- Breaking news (SerpMiner + alerts)
- Regulatory intelligence (RegulatoryMiner)
- Intellectual content (ThinkTankMiner)
- Calendar-driven topics (CalendarEngine)
- Gap-based topics (existing TopicHunter)

Provides a unified interface for the editorial pipeline.
"""

import os
import sys
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
import hashlib

# Allow running from repo root without PYTHONPATH
AGENT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if AGENT_ROOT not in sys.path:
    sys.path.insert(0, AGENT_ROOT)

from config.manager import config
from shared.logger import get_logger
from shared.models import SourcedTopic

logger = get_logger("TopicSourcer")


class TopicSourcer:
    """
    Orchestrates all topic sourcing strategies.

    Aggregates topics from multiple sources and prioritizes them
    based on configurable scoring weights:
    - Timeliness: How time-sensitive is this topic?
    - Authority: How credible is the source?
    - Demand: What's the audience interest?
    - Gap: Do we have coverage gaps here?
    """

    def __init__(self, brain=None):
        """
        Initialize TopicSourcer.

        Args:
            brain: Optional ContentBrain instance for database access
        """
        self.brain = brain
        self.enabled = config.get("topic_sourcer.enabled", True)
        self.scoring_weights = config.get(
            "topic_sourcer.scoring",
            {
                "timeliness": 0.30,
                "authority": 0.30,
                "demand": 0.20,
                "gap": 0.20,
            },
        )
        self.auto_queue_threshold = config.get("topic_sourcer.auto_queue_threshold", 70)
        self.require_review_below = config.get("topic_sourcer.require_review_below", 50)

        # Lazy-load miners
        self._thinktank_miner = None
        self._regulatory_miner = None
        self._serp_miner = None
        self._calendar_engine = None
        self._scam_miner = None
        self._market_miner = None
        self._consumer_miner = None
        self._pillar_manager = None

    @property
    def thinktank_miner(self):
        """Lazy-load ThinkTankMiner."""
        if self._thinktank_miner is None:
            try:
                from skills.miners.thinktank_miner import ThinkTankMiner

                self._thinktank_miner = ThinkTankMiner()
            except Exception as e:
                logger.warning("thinktank_miner_unavailable", error=str(e))
        return self._thinktank_miner

    @property
    def regulatory_miner(self):
        """Lazy-load RegulatoryMiner."""
        if self._regulatory_miner is None:
            try:
                from skills.miners.regulatory_miner import RegulatoryMiner

                self._regulatory_miner = RegulatoryMiner()
            except Exception as e:
                logger.warning("regulatory_miner_unavailable", error=str(e))
        return self._regulatory_miner

    @property
    def serp_miner(self):
        """Lazy-load SerpMiner."""
        if self._serp_miner is None:
            try:
                from skills.miners.serp_miner import SerpMiner

                miner = SerpMiner()
                if miner.is_available():
                    self._serp_miner = miner
            except Exception as e:
                logger.warning("serp_miner_unavailable", error=str(e))
        return self._serp_miner

    @property
    def calendar_engine(self):
        """Lazy-load CalendarEngine."""
        if self._calendar_engine is None:
            try:
                from skills.calendar_engine import CalendarEngine

                self._calendar_engine = CalendarEngine(brain=self.brain)
            except Exception as e:
                logger.warning("calendar_engine_unavailable", error=str(e))
        return self._calendar_engine

    @property
    def scam_miner(self):
        """Lazy-load ScamMiner (highest priority)."""
        if self._scam_miner is None:
            try:
                from skills.miners.scam_miner import ScamMiner

                miner = ScamMiner()
                if miner.is_available():
                    self._scam_miner = miner
            except Exception as e:
                logger.warning("scam_miner_unavailable", error=str(e))
        return self._scam_miner

    @property
    def market_miner(self):
        """Lazy-load MarketMiner for economic security."""
        if self._market_miner is None:
            try:
                from skills.miners.market_miner import MarketMiner

                miner = MarketMiner()
                if miner.is_available():
                    self._market_miner = miner
            except Exception as e:
                logger.warning("market_miner_unavailable", error=str(e))
        return self._market_miner

    @property
    def consumer_miner(self):
        """Lazy-load ConsumerMiner for product reviews."""
        if self._consumer_miner is None:
            try:
                from skills.miners.consumer_miner import ConsumerMiner

                miner = ConsumerMiner()
                if miner.is_available():
                    self._consumer_miner = miner
            except Exception as e:
                logger.warning("consumer_miner_unavailable", error=str(e))
        return self._consumer_miner

    @property
    def pillar_manager(self):
        """Lazy-load ContentPillarManager."""
        if self._pillar_manager is None:
            try:
                from skills.content_pillars import ContentPillarManager

                self._pillar_manager = ContentPillarManager(brain=self.brain)
            except Exception as e:
                logger.warning("pillar_manager_unavailable", error=str(e))
        return self._pillar_manager

    def source_topics(
        self,
        strategy: Literal[
            "all",
            "breaking",
            "regulatory",
            "intellectual",
            "calendar",
            "gap",
            "scam",
            "market",
            "consumer",
            "by_pillar",
        ] = "all",
        pillar: Optional[str] = None,
    ) -> List[SourcedTopic]:
        """
        Source topics using specified strategy.

        Args:
            strategy: Which sourcing strategy to use
                - "all": All strategies combined
                - "breaking": SerpMiner + alerts only
                - "regulatory": RegulatoryMiner only
                - "intellectual": ThinkTankMiner only
                - "calendar": CalendarEngine only
                - "gap": Gap analysis only
                - "scam": ScamMiner only (highest priority)
                - "market": MarketMiner only
                - "consumer": ConsumerMiner only
                - "by_pillar": Source for a specific pillar
            pillar: Pillar slug when using "by_pillar" strategy

        Returns:
            List of SourcedTopic objects, prioritized by score
        """
        if not self.enabled:
            logger.info("topic_sourcer_disabled")
            return []

        topics: List[SourcedTopic] = []

        # Scam topics first (highest priority for reader value)
        if strategy in ["all", "scam"]:
            topics.extend(self.get_scam_topics())

        if strategy in ["all", "breaking"]:
            topics.extend(self.get_breaking_topics())

        # Market topics for economic security
        if strategy in ["all", "market"]:
            topics.extend(self.get_market_topics())

        if strategy in ["all", "regulatory"]:
            topics.extend(self.get_regulatory_topics())

        if strategy in ["all", "intellectual"]:
            topics.extend(self.get_intellectual_topics())

        if strategy in ["all", "calendar"]:
            topics.extend(self.get_calendar_topics())

        # Consumer topics for product reviews
        if strategy in ["all", "consumer"]:
            topics.extend(self.get_consumer_topics())

        if strategy in ["all", "gap"]:
            topics.extend(self.get_gap_topics())

        # Pillar-specific sourcing
        if strategy == "by_pillar" and pillar:
            topics = self.source_by_pillar(pillar)

        # Remove duplicates and prioritize
        topics = self._deduplicate_topics(topics)
        topics = self.prioritize_topics(topics)

        # Assign pillars to topics that don't have them
        if self.pillar_manager:
            for topic in topics:
                if not topic.primary_pillar:
                    topic.primary_pillar = self.pillar_manager.route_topic_to_pillar(
                        topic
                    )

        logger.info(
            "topics_sourced",
            strategy=strategy,
            count=len(topics),
        )

        return topics

    def get_breaking_topics(self) -> List[SourcedTopic]:
        """
        Get breaking news topics from SerpMiner and alerts.

        Returns:
            List of SourcedTopic objects for breaking news
        """
        topics = []

        # Try SerpMiner for breaking news
        if self.serp_miner:
            try:
                items = self.serp_miner.fetch_breaking_news(limit=10)
                for item in items:
                    topic = self._evidence_to_topic(
                        item,
                        source_type="breaking",
                        content_type="News",
                    )
                    topics.append(topic)
            except Exception as e:
                logger.warning("serp_breaking_error", error=str(e))

        # Also check regulatory miner for critical alerts
        if self.regulatory_miner:
            try:
                alerts = self.regulatory_miner.fetch_alerts(hours=24)
                critical_alerts = [
                    a
                    for a in alerts
                    if a.metadata.get("urgency") in ["critical", "high"]
                ]
                for item in critical_alerts[:5]:
                    topic = self._evidence_to_topic(
                        item,
                        source_type="breaking",
                        content_type="News",
                        urgency=item.metadata.get("urgency", "high"),
                    )
                    topics.append(topic)
            except Exception as e:
                logger.warning("regulatory_alerts_error", error=str(e))

        logger.info("breaking_topics", count=len(topics))
        return topics

    def get_regulatory_topics(self) -> List[SourcedTopic]:
        """
        Get regulatory intelligence topics.

        Returns:
            List of SourcedTopic objects for regulatory content
        """
        topics = []

        if not self.regulatory_miner:
            return topics

        try:
            # Get recent regulatory content
            items = self.regulatory_miner.fetch_alerts(hours=168)  # Last week

            for item in items[:15]:
                doc_type = item.metadata.get("document_type", "general")

                # Determine content type based on document type
                if doc_type in ["circular", "regulation", "framework"]:
                    content_type = "Guide"
                elif doc_type in ["advisory", "alert"]:
                    content_type = "News"
                else:
                    content_type = "Analysis"

                topic = self._evidence_to_topic(
                    item,
                    source_type="regulatory",
                    content_type=content_type,
                    urgency=item.metadata.get("urgency", "medium"),
                )
                topics.append(topic)

        except Exception as e:
            logger.warning("regulatory_topics_error", error=str(e))

        logger.info("regulatory_topics", count=len(topics))
        return topics

    def get_intellectual_topics(self) -> List[SourcedTopic]:
        """
        Get intellectual content topics from think tanks.

        Returns:
            List of SourcedTopic objects for analysis content
        """
        topics = []

        if not self.thinktank_miner or not self.thinktank_miner.is_available():
            return topics

        try:
            items = self.thinktank_miner.fetch_latest(days=14)

            for item in items[:15]:
                topic = self._evidence_to_topic(
                    item,
                    source_type="thinktank",
                    content_type="Analysis",
                    urgency="medium",
                )
                topics.append(topic)

        except Exception as e:
            logger.warning("thinktank_topics_error", error=str(e))

        logger.info("intellectual_topics", count=len(topics))
        return topics

    def get_calendar_topics(self) -> List[SourcedTopic]:
        """
        Get calendar-driven topics.

        Returns:
            List of SourcedTopic objects for calendar events
        """
        if not self.calendar_engine:
            return []

        try:
            topics = self.calendar_engine.get_actionable_topics()
            logger.info("calendar_topics", count=len(topics))
            return topics

        except Exception as e:
            logger.warning("calendar_topics_error", error=str(e))
            return []

    def get_scam_topics(self) -> List[SourcedTopic]:
        """
        Get scam/fraud topics from ScamMiner.

        Highest priority source for reader value.

        Returns:
            List of SourcedTopic objects for scam alerts
        """
        topics = []

        if not self.scam_miner:
            return topics

        try:
            # Get active scams
            items = self.scam_miner.fetch_active_scams(hours=48)

            for item in items[:15]:
                scam_type = item.metadata.get("scam_type", "unknown")
                urgency = item.metadata.get("urgency", "high")

                # Scams are always high priority for citizens and seniors
                topic = SourcedTopic(
                    id=f"scam_{item.id}",
                    title=item.title,
                    source_type="scam",
                    source_id=item.domain,
                    urgency=urgency,
                    content_type="News",
                    source_url=item.url,
                    timeliness_score=95 if urgency == "critical" else 85,
                    authority_score=item.credibility_weight * 10,
                    gap_score=80,  # Scams always have high gap score
                    overall_score=self._calculate_score(
                        90 if urgency == "critical" else 80,
                        item.credibility_weight * 10,
                        80,
                    ),
                    suggested_angle=f"Scam Alert: {item.title[:80]}",
                    key_points=[item.snippet[:200]] if item.snippet else [],
                    tags=[scam_type, "scam", "fraud", "alert"],
                    primary_pillar="scam_watch",
                    target_personas=["citizen", "senior"],
                    actionability_score=90,  # Scams are highly actionable
                    india_specificity=85,
                )
                topics.append(topic)

        except Exception as e:
            logger.warning("scam_topics_error", error=str(e))

        logger.info("scam_topics", count=len(topics))
        return topics

    def get_market_topics(self) -> List[SourcedTopic]:
        """
        Get economic security topics from MarketMiner.

        Returns:
            List of SourcedTopic objects for economic security
        """
        topics = []

        if not self.market_miner:
            return topics

        try:
            # Get regulatory actions and investor warnings
            items = self.market_miner.fetch_regulatory_actions(days=30)

            for item in items[:10]:
                alert_type = item.metadata.get("alert_type", "other")
                urgency = item.metadata.get("urgency", "medium")

                topic = SourcedTopic(
                    id=f"market_{item.id}",
                    title=item.title,
                    source_type="market",
                    source_id=item.domain,
                    urgency=urgency,
                    content_type="News" if alert_type == "fraud_case" else "Analysis",
                    source_url=item.url,
                    timeliness_score=80,
                    authority_score=item.credibility_weight * 10,
                    gap_score=70,
                    overall_score=self._calculate_score(
                        80, item.credibility_weight * 10, 70
                    ),
                    suggested_angle=f"Economic Security: {item.title[:80]}",
                    key_points=[item.snippet[:200]] if item.snippet else [],
                    tags=[alert_type, "market", "investor", "regulatory"],
                    primary_pillar="economic_security",
                    target_personas=["citizen", "smb", "compliance"],
                    actionability_score=75,
                    india_specificity=90,
                )
                topics.append(topic)

        except Exception as e:
            logger.warning("market_topics_error", error=str(e))

        logger.info("market_topics", count=len(topics))
        return topics

    def get_consumer_topics(self) -> List[SourcedTopic]:
        """
        Get product review topics from ConsumerMiner.

        Returns:
            List of SourcedTopic objects for product reviews
        """
        topics = []

        if not self.consumer_miner:
            return topics

        try:
            # Get trending products across categories
            products = self.consumer_miner.get_trending_products(limit=10)

            for idx, product in enumerate(products):
                topic = SourcedTopic(
                    id=f"consumer_{idx}_{product.get('category', 'unknown')}",
                    title=product.get("title", ""),
                    source_type="consumer",
                    source_id=product.get("source", ""),
                    urgency="low",
                    content_type="Review",
                    source_url=product.get("url"),
                    timeliness_score=40,  # Reviews are less time-sensitive
                    authority_score=product.get("credibility", 6) * 10,
                    gap_score=70,
                    overall_score=self._calculate_score(
                        40, product.get("credibility", 6) * 10, 70
                    ),
                    suggested_angle=f"Product Review: {product.get('title', '')[:60]}",
                    key_points=[product.get("snippet", "")[:200]],
                    tags=[product.get("category", ""), "review", "product"],
                    primary_pillar="product_reviews",
                    target_personas=["smb", "professional"],
                    actionability_score=85,  # Reviews help with purchase decisions
                    india_specificity=70,
                )
                topics.append(topic)

        except Exception as e:
            logger.warning("consumer_topics_error", error=str(e))

        logger.info("consumer_topics", count=len(topics))
        return topics

    def source_by_pillar(self, pillar_slug: str) -> List[SourcedTopic]:
        """
        Source topics for a specific content pillar.

        Args:
            pillar_slug: Content pillar to source for

        Returns:
            List of SourcedTopic objects for the pillar
        """
        pillar_miners = {
            "scam_watch": [self.get_scam_topics],
            "economic_security": [self.get_market_topics, self.get_regulatory_topics],
            "personal_security": [
                self.get_breaking_topics,
                self.get_intellectual_topics,
            ],
            "senior_safety": [self.get_scam_topics],  # Reuse scam topics
            "business_security": [
                self.get_regulatory_topics,
                self.get_intellectual_topics,
            ],
            "sector_intelligence": [self.get_intellectual_topics],
            "product_reviews": [self.get_consumer_topics],
        }

        miners = pillar_miners.get(pillar_slug, [])
        topics = []

        for miner_func in miners:
            try:
                miner_topics = miner_func()
                # Tag topics with the target pillar
                for topic in miner_topics:
                    topic.primary_pillar = pillar_slug
                topics.extend(miner_topics)
            except Exception as e:
                logger.warning(
                    "pillar_sourcing_error", pillar=pillar_slug, error=str(e)
                )

        logger.info("pillar_topics_sourced", pillar=pillar_slug, count=len(topics))
        return topics

    def get_gap_topics(self) -> List[SourcedTopic]:
        """
        Get topics based on coverage gaps.

        Uses existing TopicHunter logic to find gaps.

        Returns:
            List of SourcedTopic objects for gap-filling content
        """
        topics = []

        if not self.brain:
            return topics

        try:
            # Get content type distribution
            stats = self.brain.get_stats()
            type_stats = stats.get("types", {})
            total = sum(type_stats.values()) or 1

            # Target mix from config
            target_mix = config.get(
                "topic_proposer.content_mix",
                {"News": 0.4, "Guide": 0.35, "Analysis": 0.25},
            )

            # Find gaps
            for content_type, target_ratio in target_mix.items():
                current_ratio = type_stats.get(content_type, 0) / total
                gap = target_ratio - current_ratio

                if gap > 0.05:  # More than 5% deficit
                    topic = SourcedTopic(
                        id=f"gap_{content_type}_{datetime.now().strftime('%Y%m%d')}",
                        title=f"Coverage gap: {content_type} content needed",
                        source_type="gap",
                        source_id="content_brain",
                        urgency="low" if gap < 0.1 else "medium",
                        content_type=content_type,
                        timeliness_score=30,
                        authority_score=50,
                        gap_score=int(gap * 100),
                        overall_score=self._calculate_score(30, 50, int(gap * 100)),
                        suggested_angle=f"Find {content_type.lower()} topics to balance content mix",
                        key_points=[
                            f"Current {content_type} ratio: {current_ratio:.1%}",
                            f"Target ratio: {target_ratio:.1%}",
                            f"Gap: {gap:.1%}",
                        ],
                        tags=[content_type.lower(), "content_gap"],
                    )
                    topics.append(topic)

        except Exception as e:
            logger.warning("gap_topics_error", error=str(e))

        logger.info("gap_topics", count=len(topics))
        return topics

    def prioritize_topics(self, topics: List[SourcedTopic]) -> List[SourcedTopic]:
        """
        Prioritize topics by overall score.

        Also applies urgency boosts:
        - Critical: +20 to overall score
        - High: +10 to overall score

        Args:
            topics: List of topics to prioritize

        Returns:
            Sorted list of topics
        """
        urgency_boost = {
            "critical": 20,
            "high": 10,
            "medium": 0,
            "low": -5,
        }

        # Apply urgency boosts
        for topic in topics:
            boost = urgency_boost.get(topic.urgency, 0)
            topic.overall_score = min(100, topic.overall_score + boost)

        # Sort by overall score (descending)
        topics.sort(key=lambda x: x.overall_score, reverse=True)

        return topics

    def _evidence_to_topic(
        self,
        item,
        source_type: str,
        content_type: str,
        urgency: str = "medium",
    ) -> SourcedTopic:
        """
        Convert an EvidenceItem to a SourcedTopic.

        Args:
            item: EvidenceItem from a miner
            source_type: Type of source (breaking, regulatory, thinktank)
            content_type: Recommended content type (News, Analysis, Guide)
            urgency: Urgency level

        Returns:
            SourcedTopic object
        """
        # Calculate timeliness based on publication date
        timeliness = 50
        if item.published:
            hours_ago = (datetime.now() - item.published).total_seconds() / 3600
            if hours_ago < 6:
                timeliness = 100
            elif hours_ago < 24:
                timeliness = 85
            elif hours_ago < 72:
                timeliness = 70
            elif hours_ago < 168:
                timeliness = 50
            else:
                timeliness = 30

        # Authority from credibility weight
        authority = item.credibility_weight * 10  # Convert 1-10 to 10-100

        # Default gap score
        gap = 50

        # Calculate overall score
        overall = self._calculate_score(timeliness, authority, gap)

        return SourcedTopic(
            id=f"{source_type}_{item.id}",
            title=item.title,
            source_type=source_type,
            source_id=item.metadata.get("source_id", item.domain),
            urgency=urgency,
            content_type=content_type,
            source_url=item.url,
            timeliness_score=timeliness,
            authority_score=authority,
            gap_score=gap,
            overall_score=overall,
            suggested_angle=f"Analyze and report on: {item.title[:100]}",
            key_points=[item.snippet[:200]] if item.snippet else [],
            tags=item.metadata.get("tags", []),
        )

    def _calculate_score(self, timeliness: int, authority: int, gap: int) -> float:
        """Calculate weighted overall score."""
        # Use demand as 50 (neutral) since we don't have real demand data
        demand = 50

        score = (
            timeliness * self.scoring_weights.get("timeliness", 0.25)
            + authority * self.scoring_weights.get("authority", 0.25)
            + demand * self.scoring_weights.get("demand", 0.25)
            + gap * self.scoring_weights.get("gap", 0.25)
        )

        return round(score, 2)

    def _deduplicate_topics(self, topics: List[SourcedTopic]) -> List[SourcedTopic]:
        """
        Remove duplicate topics based on title similarity.

        Args:
            topics: List of topics that may contain duplicates

        Returns:
            Deduplicated list of topics
        """
        seen_titles = set()
        unique_topics = []

        for topic in topics:
            # Normalize title for comparison
            normalized = topic.title.lower().strip()

            # Simple dedup - could use fuzzy matching for better results
            if normalized not in seen_titles:
                seen_titles.add(normalized)
                unique_topics.append(topic)

        return unique_topics

    def get_sourcer_stats(self) -> Dict[str, Any]:
        """Get statistics about the topic sourcer."""
        stats = {
            "enabled": self.enabled,
            "scoring_weights": self.scoring_weights,
            "miners": {
                "thinktank": self.thinktank_miner is not None
                and (
                    self.thinktank_miner.is_available()
                    if hasattr(self.thinktank_miner, "is_available")
                    else True
                ),
                "regulatory": self.regulatory_miner is not None,
                "serp": self.serp_miner is not None,
                "calendar": self.calendar_engine is not None,
                "scam": self.scam_miner is not None,
                "market": self.market_miner is not None,
                "consumer": self.consumer_miner is not None,
            },
            "pillars": self.pillar_manager is not None,
        }

        # Add pillar stats if available
        if self.pillar_manager:
            stats["pillar_health"] = self.pillar_manager.get_pillar_health()

        return stats


if __name__ == "__main__":
    # Quick test
    sourcer = TopicSourcer()

    print("TopicSourcer Stats:")
    print(sourcer.get_sourcer_stats())

    print("\nSourcing all topics...")
    topics = sourcer.source_topics(strategy="all")

    print(f"\nFound {len(topics)} topics:")
    for t in topics[:10]:
        print(f"  [{t.source_type}] {t.title[:60]}... (score: {t.overall_score})")
