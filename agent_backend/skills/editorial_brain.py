"""
Editorial Brain v2 - LLM-Powered Editorial Judgment

Replaces the statistical CCO with an LLM-powered editorial judgment system
that thinks like a 20-year veteran editor.

Features:
- Breaking news detection
- Trending topic identification
- Content gap analysis
- Multi-factor topic scoring
- Fallback to CCO logic on error
"""

import os
import sys
from typing import List, Dict, Any, Optional
from datetime import datetime

# Allow running from repo root without PYTHONPATH
AGENT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if AGENT_ROOT not in sys.path:
    sys.path.insert(0, AGENT_ROOT)

from config.manager import config
from shared.logger import get_logger
from shared.models import EditorialDirective, TopicEvaluation, SourcedTopic
from skills.gemini_client import GeminiAgent
from skills.content_brain import ContentBrain

logger = get_logger("EditorialBrain")

# Lazy import for ContentPillarManager to avoid circular imports
ContentPillarManager = None

# Lazy import for TopicSourcer to avoid circular imports
TopicSourcer = None


class EditorialBrainV2:
    """
    LLM-powered editorial judgment with news sense.

    Replaces the rule-based CCO with intelligent decision-making
    based on multiple signals: breaking news, trends, gaps, and audience fit.
    """

    def __init__(
        self,
        client: Optional[GeminiAgent] = None,
        brain: Optional[ContentBrain] = None,
    ):
        self.client = client or GeminiAgent()
        self.brain = brain or ContentBrain()

        # Load scoring weights from config
        self.scoring_weights = {
            "news_sense": config.get("editorial_brain.news_sense_weight", 0.25),
            "audience_fit": config.get("editorial_brain.audience_fit_weight", 0.25),
            "competitive_angle": config.get("editorial_brain.competitive_weight", 0.20),
            "feasibility": config.get("editorial_brain.feasibility_weight", 0.15),
            "timing": config.get("editorial_brain.timing_weight", 0.15),
        }

        # Load focus sectors
        self.focus_sectors = config.get(
            "topic_proposer.focus_sectors",
            [
                "physical_security",
                "cybersecurity",
                "fire_safety",
                "compliance",
                "risk_management",
            ],
        )

        # Fallback flag
        self.fallback_to_cco = config.get("editorial_brain.fallback_to_cco", True)

        # Topic sourcer (lazy loaded)
        self._topic_sourcer = None

        # Content pillar manager (lazy loaded)
        self._pillar_manager = None

        # Enhanced scoring weights (reader-centric)
        self.enhanced_weights = config.get(
            "topic_scoring",
            {
                "news_sense": 0.15,
                "audience_fit": 0.15,
                "timing": 0.10,
                "actionability": 0.20,
                "india_specificity": 0.10,
                "comprehensiveness": 0.10,
                "source_availability": 0.10,
                "competitive_angle": 0.10,
            },
        )

    @property
    def topic_sourcer(self):
        """Lazy-load TopicSourcer to avoid circular imports."""
        if self._topic_sourcer is None:
            try:
                from skills.topic_sourcer import TopicSourcer

                self._topic_sourcer = TopicSourcer(brain=self.brain)
            except Exception as e:
                logger.warning("topic_sourcer_unavailable", error=str(e))
        return self._topic_sourcer

    @property
    def pillar_manager(self):
        """Lazy-load ContentPillarManager to avoid circular imports."""
        if self._pillar_manager is None:
            try:
                from skills.content_pillars import ContentPillarManager

                self._pillar_manager = ContentPillarManager(brain=self.brain)
            except Exception as e:
                logger.warning("pillar_manager_unavailable", error=str(e))
        return self._pillar_manager

    def analyze_landscape(self) -> EditorialDirective:
        """
        Strategic analysis of what to cover next.

        Gathers signals from multiple sources and uses LLM judgment
        to determine the best action.
        """
        logger.info("analyzing_landscape")

        try:
            # 0. Check TopicSourcer for proactively sourced topics
            sourced_topics = self._get_sourced_topics()
            if sourced_topics:
                top_topic = sourced_topics[0]
                if top_topic.urgency in ["critical", "high"]:
                    logger.info(
                        "sourced_topic_priority",
                        topic=top_topic.title[:50],
                        source_type=top_topic.source_type,
                        urgency=top_topic.urgency,
                    )
                    return EditorialDirective(
                        action="HUNT_BREAKING"
                        if top_topic.source_type == "breaking"
                        else "WRITE_PRIORITY",
                        urgency=top_topic.urgency,
                        focus_type=top_topic.content_type,
                        focus_topic=top_topic.title,
                        reason=f"[{top_topic.source_type}] {top_topic.title[:60]}",
                        signals=[
                            {"topic": t.title, "score": t.overall_score}
                            for t in sourced_topics[:3]
                        ],
                        confidence=0.85,
                    )

            # 1. Gather signals
            breaking_signals = self._get_breaking_news()
            content_gaps = self._analyze_content_gaps()
            queue_health = self._check_queue_health()

            # 2. Process signals through LLM
            if breaking_signals:
                directive = self._process_signals(breaking_signals)
                if directive.urgency in ["critical", "high"]:
                    return directive

            # 3. Check for calendar/regulatory topics (medium urgency)
            if sourced_topics:
                # We have sourced topics but none were critical/high
                medium_topics = [t for t in sourced_topics if t.urgency == "medium"]
                if medium_topics:
                    top_topic = medium_topics[0]
                    return EditorialDirective(
                        action="WRITE_PRIORITY",
                        urgency="medium",
                        focus_type=top_topic.content_type,
                        focus_topic=top_topic.title,
                        reason=f"Sourced: {top_topic.title[:60]}",
                        signals=[
                            {"topic": t.title, "score": t.overall_score}
                            for t in medium_topics[:3]
                        ],
                        confidence=0.75,
                    )

            # 4. Check queue health
            if queue_health.get("starving", False):
                return EditorialDirective(
                    action="HUNT_GAP",
                    urgency="medium",
                    focus_type=queue_health.get("deficit_type", "Guide"),
                    reason=f"Queue starving: {queue_health.get('proposed_count', 0)} topics",
                    confidence=0.8,
                )

            # 5. Check for content gaps
            if content_gaps:
                top_gap = content_gaps[0]
                return EditorialDirective(
                    action="HUNT_GAP",
                    urgency="low",
                    focus_type=top_gap.get("content_type"),
                    focus_topic=top_gap.get("topic"),
                    reason=f"Content gap identified: {top_gap.get('topic', 'unknown')}",
                    signals=content_gaps[:3],
                    confidence=0.7,
                )

            # 6. Default: continue with queue
            return EditorialDirective(
                action="WRITE_QUEUE",
                urgency="low",
                reason="No urgent signals, continue with queue",
                confidence=0.6,
            )

        except Exception as e:
            logger.error("landscape_analysis_error", error=str(e))
            if self.fallback_to_cco:
                return self._fallback_cco_logic()
            raise

    def _get_sourced_topics(self) -> List[SourcedTopic]:
        """
        Get proactively sourced topics from TopicSourcer.

        Returns prioritized list of sourced topics.
        """
        if not self.topic_sourcer:
            return []

        try:
            # Get topics from all strategies
            topics = self.topic_sourcer.source_topics(strategy="all")
            logger.info("sourced_topics_fetched", count=len(topics))
            return topics[:10]  # Return top 10

        except Exception as e:
            logger.warning("sourced_topics_error", error=str(e))
            return []

    def evaluate_topic(self, topic: Dict[str, Any]) -> TopicEvaluation:
        """
        Deep evaluation of a single topic's newsworthiness.

        Uses LLM to assess the topic on multiple dimensions.
        """
        topic_text = topic.get("topic", str(topic))
        signals = topic.get("signals", [])

        prompt = f"""You are a veteran newsroom editor with 20 years experience.

TOPIC: {topic_text}
SIGNALS: {signals}

Evaluate this topic on:
1. NEWS SENSE (0-100): Is this genuinely newsworthy? Why now?
2. AUDIENCE FIT (0-100): Will our security-focused audience care?
3. COMPETITIVE ANGLE (0-100): What unique perspective can we offer?
4. FEASIBILITY (0-100): Can we research and write this well?
5. TIMING (0-100): Is this the right moment to publish?

Our focus areas: {self.focus_sectors}

Return JSON:
{{
    "news_sense": <score>,
    "audience_fit": <score>,
    "competitive_angle": <score>,
    "feasibility": <score>,
    "timing": <score>,
    "reasoning": "<your editorial judgment>",
    "recommended_angle": "<suggested approach>"
}}"""

        try:
            result = self.client.generate_json(prompt)

            # Calculate weighted overall score
            scores = {
                "news_sense": result.get("news_sense", 50),
                "audience_fit": result.get("audience_fit", 50),
                "competitive_angle": result.get("competitive_angle", 50),
                "feasibility": result.get("feasibility", 50),
                "timing": result.get("timing", 50),
            }

            overall = sum(scores[k] * self.scoring_weights.get(k, 0.2) for k in scores)

            return TopicEvaluation(
                topic=topic_text,
                news_sense=scores["news_sense"],
                audience_fit=scores["audience_fit"],
                competitive_angle=scores["competitive_angle"],
                feasibility=scores["feasibility"],
                timing=scores["timing"],
                overall_score=round(overall, 2),
                reasoning=result.get("reasoning", ""),
                recommended_angle=result.get("recommended_angle"),
            )

        except Exception as e:
            logger.error("topic_evaluation_error", error=str(e))
            # Return conservative evaluation on error
            return TopicEvaluation(
                topic=topic_text,
                news_sense=50,
                audience_fit=50,
                competitive_angle=50,
                feasibility=50,
                timing=30 if not signals else 50,
                overall_score=46.0,
                reasoning=f"Evaluation error: {str(e)}",
            )

    def evaluate_topic_enhanced(self, topic: Dict[str, Any]) -> TopicEvaluation:
        """
        Enhanced topic evaluation with persona-based scoring and pillar assignment.

        Uses LLM to assess topics on reader-centric dimensions including
        actionability, India-specificity, and persona relevance.

        Args:
            topic: Topic dictionary with 'topic', 'signals', and optional metadata

        Returns:
            TopicEvaluation with enhanced scoring dimensions
        """
        topic_text = topic.get("topic", str(topic))
        signals = topic.get("signals", [])
        source_type = topic.get("source_type", "unknown")
        tags = topic.get("tags", [])

        prompt = f"""You are a veteran Indian newsroom editor with 20 years experience.
Your publication serves diverse Indian audiences: general citizens, senior citizens,
small business owners, security professionals, and compliance officers.

TOPIC: {topic_text}
SIGNALS: {signals}
SOURCE TYPE: {source_type}
TAGS: {tags}

Evaluate this topic on these dimensions (0-100 each):

EDITORIAL QUALITY:
- NEWS_SENSE: Is this genuinely newsworthy for Indian readers?
- AUDIENCE_FIT: Will security-conscious Indians care about this?
- TIMING: Is this the right moment to publish?

PRACTICAL VALUE (Critical for our readers):
- ACTIONABILITY: Can the reader take concrete steps after reading? (Very important)
- INDIA_SPECIFICITY: Does this relate to Indian laws, prices in INR, local examples?
- COMPREHENSIVENESS: Does this topic need thorough coverage or is it a quick update?

SOURCE QUALITY:
- SOURCE_AVAILABILITY: Can we find 3+ reliable sources for this?
- COMPETITIVE_ANGLE: What unique perspective can we offer?

PERSONA RELEVANCE (0-100 for each):
- CITIZEN: How relevant to the general public?
- SENIOR: How relevant to 60+ individuals? (Simple language, scam prevention)
- SMB: How relevant to small business owners?
- PROFESSIONAL: How relevant to security managers?
- COMPLIANCE: How relevant to regulatory officers?

PILLAR ASSIGNMENT:
Choose the PRIMARY pillar this topic belongs to:
- scam_watch: Fraud alerts, prevention, reporting
- economic_security: Markets, investment fraud, corporate crime
- personal_security: Home, travel, digital, physical safety
- senior_safety: Elder-specific threats and protection
- business_security: Practical SMB security guides
- sector_intelligence: Industry deep dives
- product_reviews: Security products and services

Return JSON:
{{
    "news_sense": <score>,
    "audience_fit": <score>,
    "timing": <score>,
    "actionability": <score>,
    "india_specificity": <score>,
    "comprehensiveness": <score>,
    "source_availability": <score>,
    "competitive_angle": <score>,
    "persona_scores": {{
        "citizen": <score>,
        "senior": <score>,
        "smb": <score>,
        "professional": <score>,
        "compliance": <score>
    }},
    "primary_pillar": "<pillar_slug>",
    "secondary_pillars": ["<pillar1>", "<pillar2>"],
    "reasoning": "<your editorial judgment>",
    "recommended_angle": "<suggested approach for Indian readers>",
    "evergreen_factor": <0-100, 0=breaking news, 100=evergreen content>
}}"""

        try:
            result = self.client.generate_json(prompt)

            # Extract all scores
            scores = {
                "news_sense": result.get("news_sense", 50),
                "audience_fit": result.get("audience_fit", 50),
                "timing": result.get("timing", 50),
                "competitive_angle": result.get("competitive_angle", 50),
                "actionability": result.get("actionability", 50),
                "india_specificity": result.get("india_specificity", 50),
                "comprehensiveness": result.get("comprehensiveness", 50),
                "source_availability": result.get("source_availability", 50),
            }

            # Calculate weighted overall score using enhanced weights
            overall = sum(
                scores[k] * self.enhanced_weights.get(k, 0.1)
                for k in scores
                if k in self.enhanced_weights
            )

            # Normalize overall score
            weight_sum = sum(self.enhanced_weights.get(k, 0.1) for k in scores)
            if weight_sum > 0:
                overall = overall / weight_sum * 100 / 100

            # Get persona scores
            persona_scores = result.get(
                "persona_scores",
                {
                    "citizen": 50,
                    "senior": 50,
                    "smb": 50,
                    "professional": 50,
                    "compliance": 50,
                },
            )

            # Get pillar assignment
            primary_pillar = result.get("primary_pillar", "business_security")
            secondary_pillars = result.get("secondary_pillars", [])

            evaluation = TopicEvaluation(
                topic=topic_text,
                news_sense=scores["news_sense"],
                audience_fit=scores["audience_fit"],
                competitive_angle=scores["competitive_angle"],
                feasibility=scores["source_availability"],  # Map to feasibility
                timing=scores["timing"],
                overall_score=round(overall, 2),
                reasoning=result.get("reasoning", ""),
                recommended_angle=result.get("recommended_angle"),
                # Enhanced dimensions
                actionability=scores["actionability"],
                india_specificity=scores["india_specificity"],
                evergreen_factor=result.get("evergreen_factor", 50),
                persona_scores=persona_scores,
                primary_pillar=primary_pillar,
                secondary_pillars=secondary_pillars,
            )

            logger.info(
                "enhanced_topic_evaluated",
                topic=topic_text[:50],
                overall=evaluation.overall_score,
                pillar=primary_pillar,
                actionability=scores["actionability"],
            )

            return evaluation

        except Exception as e:
            logger.error("enhanced_topic_evaluation_error", error=str(e))
            # Fall back to basic evaluation
            return self.evaluate_topic(topic)

    def get_pillar_recommendations(self) -> List[Dict]:
        """
        Get content recommendations based on pillar balance.

        Returns:
            List of pillar recommendations for rebalancing
        """
        if not self.pillar_manager:
            return []

        return self.pillar_manager.get_rebalance_recommendations()

    def get_persona_focus(self, persona_id: str) -> Dict:
        """
        Get content recommendations for a specific persona.

        Args:
            persona_id: Target persona (citizen, senior, smb, professional, compliance)

        Returns:
            Dictionary with persona-specific content recommendations
        """
        if not self.pillar_manager:
            return {"error": "Pillar manager not available"}

        return self.pillar_manager.get_persona_recommendations(persona_id)

    def _get_breaking_news(self) -> List[Dict]:
        """
        Get breaking news signals from available sources.

        In production, this would query SerpAPI, RSS feeds, etc.
        """
        # For now, return empty list - will be populated by miners
        # This is a hook for future integration with news sources
        try:
            # Check if there are any recent high-priority signals
            # This would integrate with NewsMiner or SerpMiner
            return []
        except Exception as e:
            logger.warning("breaking_news_fetch_error", error=str(e))
            return []

    def _process_signals(self, signals: List[Dict]) -> EditorialDirective:
        """
        Process breaking news signals and determine action.
        """
        if not signals:
            return EditorialDirective(
                action="WRITE_QUEUE",
                urgency="low",
                reason="No breaking signals",
                confidence=0.5,
            )

        # Analyze signal urgency
        urgent_signals = [
            s for s in signals if s.get("urgency") in ["critical", "high"]
        ]

        if urgent_signals:
            top_signal = urgent_signals[0]
            return EditorialDirective(
                action="HUNT_BREAKING",
                urgency="critical"
                if top_signal.get("urgency") == "critical"
                else "high",
                focus_topic=top_signal.get("title", ""),
                reason=f"Breaking: {top_signal.get('title', 'urgent news detected')[:80]}",
                signals=urgent_signals[:3],
                confidence=0.9,
            )

        # Check for trending signals
        trending_signals = [s for s in signals if s.get("trend") == "rising"]

        if trending_signals:
            top_signal = trending_signals[0]
            return EditorialDirective(
                action="HUNT_TRENDING",
                urgency="medium",
                focus_topic=top_signal.get("title", ""),
                reason=f"Trending: {top_signal.get('title', 'topic gaining momentum')[:80]}",
                signals=trending_signals[:3],
                confidence=0.75,
            )

        return EditorialDirective(
            action="WRITE_QUEUE",
            urgency="low",
            reason="Signals analyzed, no urgent action needed",
            signals=signals[:3],
            confidence=0.6,
        )

    def _analyze_content_gaps(self) -> List[Dict]:
        """
        Analyze content gaps in our coverage.
        """
        try:
            stats = self.brain.get_stats()

            # Target content mix from config
            target_mix = config.get(
                "topic_proposer.content_mix",
                {"News": 0.4, "Guide": 0.35, "Analysis": 0.25},
            )

            # Calculate current mix
            type_stats = stats.get("types", {})
            total = sum(type_stats.values()) or 1

            gaps = []
            for content_type, target_ratio in target_mix.items():
                current_ratio = type_stats.get(content_type, 0) / total
                gap = target_ratio - current_ratio

                if gap > 0.05:  # More than 5% deficit
                    gaps.append(
                        {
                            "content_type": content_type,
                            "gap_score": round(gap * 100, 1),
                            "topic": f"{content_type} content needed",
                            "sector": "general",
                        }
                    )

            # Sort by gap score
            gaps.sort(key=lambda x: x.get("gap_score", 0), reverse=True)

            return gaps

        except Exception as e:
            logger.warning("gap_analysis_error", error=str(e))
            return []

    def _check_queue_health(self) -> Dict:
        """
        Check the health of the topic queue.
        """
        try:
            stats = self.brain.get_stats()
            proposed_count = stats.get("status", {}).get("PROPOSED", 0)

            if proposed_count < 3:
                # Find biggest deficit
                type_stats = stats.get("types", {})
                target_mix = {
                    "Guide": 0.40,
                    "Analysis": 0.25,
                    "News": 0.20,
                    "Review": 0.15,
                }
                total = sum(type_stats.values()) or 1

                biggest_deficit = None
                max_diff = -1.0

                for content_type, target in target_mix.items():
                    current = type_stats.get(content_type, 0) / total
                    diff = target - current
                    if diff > max_diff:
                        max_diff = diff
                        biggest_deficit = content_type

                return {
                    "starving": True,
                    "proposed_count": proposed_count,
                    "deficit_type": biggest_deficit or "Guide",
                }

            return {
                "starving": False,
                "proposed_count": proposed_count,
            }

        except Exception as e:
            logger.warning("queue_health_error", error=str(e))
            return {"starving": False, "proposed_count": 0}

    def _fallback_cco_logic(self) -> EditorialDirective:
        """
        Fallback to simple CCO logic when LLM fails.
        """
        try:
            queue_health = self._check_queue_health()

            if queue_health.get("starving", False):
                return EditorialDirective(
                    action="HUNT_GAP",
                    urgency="medium",
                    focus_type=queue_health.get("deficit_type", "Guide"),
                    reason=f"Fallback: Queue has {queue_health.get('proposed_count', 0)} topics",
                    confidence=0.5,
                )

            return EditorialDirective(
                action="WRITE_QUEUE",
                urgency="low",
                reason="Fallback: Queue healthy, continue publishing",
                confidence=0.5,
            )

        except Exception:
            # Ultimate fallback
            return EditorialDirective(
                action="WRITE_QUEUE",
                urgency="low",
                reason="Fallback: Default to queue processing",
                confidence=0.3,
            )


if __name__ == "__main__":
    # Quick test
    brain = EditorialBrainV2()

    print("Analyzing landscape...")
    directive = brain.analyze_landscape()
    print(f"Action: {directive.action}")
    print(f"Urgency: {directive.urgency}")
    print(f"Reason: {directive.reason}")

    print("\nEvaluating topic...")
    topic = {"topic": "New RBI Cybersecurity Guidelines for Banks", "signals": []}
    evaluation = brain.evaluate_topic(topic)
    print(f"Topic: {evaluation.topic}")
    print(f"Overall Score: {evaluation.overall_score}")
    print(f"Reasoning: {evaluation.reasoning}")
