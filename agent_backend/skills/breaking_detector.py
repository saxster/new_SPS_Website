"""
Breaking Detector - Detects breaking news signals.

Analyzes articles for breaking news indicators:
- Title patterns (BREAKING:, JUST IN:, etc.)
- Recency (published within last 30 minutes)
- Source tier lookup
"""

import os
import re
import sys
from datetime import datetime
from typing import List, Optional

# Allow running from repo root without PYTHONPATH
AGENT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if AGENT_ROOT not in sys.path:
    sys.path.insert(0, AGENT_ROOT)

from shared.logger import get_logger
from shared.models import ArticleDraft, BreakingAnalysis
from skills.pipeline_router import PipelineRouter

logger = get_logger("BreakingDetector")


class BreakingDetector:
    """
    Detects breaking news signals from article drafts.

    Analyzes:
    - Title patterns (BREAKING:, JUST IN:, URGENT:, etc.)
    - Publication recency
    - Source credibility tier
    """

    def __init__(self):
        self.router = PipelineRouter()
        self.recency_threshold_minutes = (
            30  # Articles older than this are not "breaking"
        )

        # Breaking news title patterns (case-insensitive)
        self.breaking_patterns = [
            r"BREAKING:",
            r"JUST IN:",
            r"URGENT:",
            r"FLASH:",
            r"ALERT:",
            r"DEVELOPING:",
            r"LIVE:",
            r"UPDATE:",
        ]

    def detect_title_indicators(self, title: str) -> List[str]:
        """
        Detect breaking news indicators in a title.

        Args:
            title: The article title

        Returns:
            List of detected indicators (e.g., ["BREAKING:", "DEVELOPING:"])
        """
        if not title:
            return []

        indicators = []
        title_upper = title.upper()

        for pattern in self.breaking_patterns:
            # Check if pattern appears in title (case-insensitive)
            if re.search(pattern, title_upper):
                indicators.append(pattern.replace(r"\\", "").rstrip(":") + ":")

        return indicators

    def get_recency_minutes(self, pub_date: Optional[datetime]) -> Optional[int]:
        """
        Calculate how many minutes ago the article was published.

        Args:
            pub_date: The publication datetime

        Returns:
            Minutes since publication, or None if pub_date is None
        """
        if pub_date is None:
            return None

        now = datetime.now()
        if pub_date.tzinfo is not None:
            # If pub_date has timezone, use naive comparison
            pub_date = pub_date.replace(tzinfo=None)

        delta = now - pub_date

        # If future date, return 0
        if delta.total_seconds() < 0:
            return 0

        return int(delta.total_seconds() / 60)

    def determine_urgency(
        self,
        title_indicators: List[str],
        source_tier: Optional[str],
        recency_minutes: Optional[int],
    ) -> str:
        """
        Determine urgency level based on signals.

        Args:
            title_indicators: List of breaking patterns found in title
            source_tier: Source trust tier (tier_1, tier_2, tier_3, or None)
            recency_minutes: Minutes since publication

        Returns:
            Urgency level: "critical", "high", "medium", or "low"
        """
        score = 0

        # Title indicators add urgency
        if title_indicators:
            if any(
                ind in ["BREAKING:", "FLASH:", "URGENT:"] for ind in title_indicators
            ):
                score += 3
            elif any(ind in ["JUST IN:", "ALERT:"] for ind in title_indicators):
                score += 2
            else:
                score += 1

        # Source tier affects urgency
        tier_scores = {"tier_1": 3, "tier_2": 2, "tier_3": 1}
        if source_tier:
            score += tier_scores.get(source_tier, 0)

        # Recency affects urgency
        if recency_minutes is not None:
            if recency_minutes <= 15:
                score += 3
            elif recency_minutes <= 30:
                score += 2
            elif recency_minutes <= 60:
                score += 1
            # Older articles get no recency boost

        # Map score to urgency level
        if score >= 7:
            return "critical"
        elif score >= 5:
            return "high"
        elif score >= 3:
            return "medium"
        else:
            return "low"

    def analyze(self, draft: ArticleDraft) -> BreakingAnalysis:
        """
        Perform full breaking news analysis on a draft.

        Args:
            draft: The article draft to analyze

        Returns:
            BreakingAnalysis with all detection results
        """
        # Detect title indicators
        title_indicators = self.detect_title_indicators(draft.title)

        # Get source tier from first source
        source_tier = None
        if draft.sources:
            first_source = draft.sources[0]
            source_url = first_source.url if first_source.url else ""
            source_tier = self.router.get_source_tier(source_url)

        # Calculate recency
        recency_minutes = self.get_recency_minutes(draft.pubDate)

        # Determine urgency
        urgency = self.determine_urgency(title_indicators, source_tier, recency_minutes)

        # Build signals list
        signals = []
        if title_indicators:
            signals.append("breaking_title_pattern")
        if source_tier in ["tier_1", "tier_2"]:
            signals.append("trusted_source")
        if source_tier == "tier_1":
            signals.append("government_source")
        if recency_minutes is not None and recency_minutes <= 30:
            signals.append("very_recent")

        # Determine if this qualifies as breaking news
        # Requires: (trusted source OR recent) AND (title indicator OR very recent)
        is_breaking = False
        confidence = 0.0

        if source_tier in ["tier_1", "tier_2"]:
            # Trusted source path
            if title_indicators and (recency_minutes is None or recency_minutes <= 60):
                is_breaking = True
                confidence = 0.9 if source_tier == "tier_1" else 0.8
            elif (
                recency_minutes is not None
                and recency_minutes <= 15
                and title_indicators
            ):
                is_breaking = True
                confidence = 0.85

        elif title_indicators and recency_minutes is not None and recency_minutes <= 15:
            # Breaking title + very recent but untrusted source
            # Don't mark as breaking, but indicate potential
            is_breaking = False
            confidence = 0.4

        # Log the analysis
        logger.debug(
            "breaking_analysis",
            title=draft.title[:50],
            is_breaking=is_breaking,
            urgency=urgency,
            source_tier=source_tier,
            recency_minutes=recency_minutes,
            confidence=confidence,
        )

        return BreakingAnalysis(
            is_breaking=is_breaking,
            urgency=urgency,
            source_tier=source_tier,
            confidence=confidence,
            signals=signals,
            title_indicators=title_indicators,
            recency_minutes=recency_minutes,
        )


if __name__ == "__main__":
    # Quick test
    from shared.models import ArticleSource

    detector = BreakingDetector()

    # Test title detection
    test_titles = [
        "BREAKING: RBI announces rate hike",
        "JUST IN: Major security incident",
        "Security Industry Report 2026",
        "URGENT: Evacuation ordered at mall",
    ]

    print("Title indicator detection:")
    for title in test_titles:
        indicators = detector.detect_title_indicators(title)
        print(f"  {title[:40]} -> {indicators}")

    # Test full analysis
    test_draft = ArticleDraft(
        title="BREAKING: Government issues cybersecurity advisory",
        description="CERT-IN releases urgent advisory",
        category="Cyber",
        contentType="News",
        body="The government today issued...",
        wordCount=300,
        pubDate=datetime.now(),
        sources=[
            ArticleSource(
                id="1", title="CERT-IN", url="https://cert-in.org.in/advisory/123"
            )
        ],
    )

    print("\nFull analysis:")
    analysis = detector.analyze(test_draft)
    print(f"  Is breaking: {analysis.is_breaking}")
    print(f"  Urgency: {analysis.urgency}")
    print(f"  Source tier: {analysis.source_tier}")
    print(f"  Confidence: {analysis.confidence}")
    print(f"  Signals: {analysis.signals}")
