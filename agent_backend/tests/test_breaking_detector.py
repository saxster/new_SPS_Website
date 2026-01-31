"""
Tests for BreakingDetector - Detects breaking news signals.
TDD First - Tests written before implementation.
"""

import pytest
from datetime import datetime, timedelta


class TestBreakingDetectorInit:
    """Tests for BreakingDetector initialization."""

    def test_breaking_detector_initializes(self):
        """Test that BreakingDetector initializes correctly."""
        from skills.breaking_detector import BreakingDetector

        detector = BreakingDetector()

        assert detector is not None
        assert hasattr(detector, "breaking_patterns")
        assert hasattr(detector, "recency_threshold_minutes")


class TestTitlePatternDetection:
    """Tests for breaking news title pattern detection."""

    def test_detects_breaking_prefix(self):
        """Test detection of BREAKING: prefix."""
        from skills.breaking_detector import BreakingDetector

        detector = BreakingDetector()

        indicators = detector.detect_title_indicators(
            "BREAKING: Major earthquake hits Mumbai"
        )

        assert "BREAKING:" in indicators

    def test_detects_just_in_prefix(self):
        """Test detection of JUST IN: prefix."""
        from skills.breaking_detector import BreakingDetector

        detector = BreakingDetector()

        indicators = detector.detect_title_indicators(
            "JUST IN: RBI announces rate decision"
        )

        assert "JUST IN:" in indicators

    def test_detects_urgent_prefix(self):
        """Test detection of URGENT: prefix."""
        from skills.breaking_detector import BreakingDetector

        detector = BreakingDetector()

        indicators = detector.detect_title_indicators("URGENT: Evacuation ordered")

        assert "URGENT:" in indicators

    def test_detects_flash_prefix(self):
        """Test detection of FLASH: prefix."""
        from skills.breaking_detector import BreakingDetector

        detector = BreakingDetector()

        indicators = detector.detect_title_indicators("FLASH: Market crashes")

        assert "FLASH:" in indicators

    def test_detects_alert_prefix(self):
        """Test detection of ALERT: prefix."""
        from skills.breaking_detector import BreakingDetector

        detector = BreakingDetector()

        indicators = detector.detect_title_indicators("ALERT: Security breach reported")

        assert "ALERT:" in indicators

    def test_detects_multiple_indicators(self):
        """Test detection of multiple patterns."""
        from skills.breaking_detector import BreakingDetector

        detector = BreakingDetector()

        # Title with breaking and developing
        indicators = detector.detect_title_indicators(
            "BREAKING: Developing situation at airport"
        )

        assert "BREAKING:" in indicators

    def test_no_indicators_in_normal_title(self):
        """Test that normal titles have no breaking indicators."""
        from skills.breaking_detector import BreakingDetector

        detector = BreakingDetector()

        indicators = detector.detect_title_indicators(
            "Security Industry Trends Report 2026"
        )

        assert len(indicators) == 0

    def test_case_insensitive_detection(self):
        """Test that detection is case-insensitive."""
        from skills.breaking_detector import BreakingDetector

        detector = BreakingDetector()

        indicators_upper = detector.detect_title_indicators("BREAKING: News")
        indicators_lower = detector.detect_title_indicators("breaking: News")
        indicators_mixed = detector.detect_title_indicators("Breaking: News")

        # All should detect the breaking pattern
        assert len(indicators_upper) > 0
        assert len(indicators_lower) > 0
        assert len(indicators_mixed) > 0


class TestRecencyDetection:
    """Tests for publication recency detection."""

    def test_very_recent_article(self):
        """Test that article from 5 minutes ago is detected as very recent."""
        from skills.breaking_detector import BreakingDetector

        detector = BreakingDetector()

        pub_time = datetime.now() - timedelta(minutes=5)
        recency = detector.get_recency_minutes(pub_time)

        assert recency == 5

    def test_recent_article(self):
        """Test that article from 30 minutes ago is detected."""
        from skills.breaking_detector import BreakingDetector

        detector = BreakingDetector()

        pub_time = datetime.now() - timedelta(minutes=30)
        recency = detector.get_recency_minutes(pub_time)

        assert recency == 30

    def test_old_article(self):
        """Test that article from 2 hours ago returns correct minutes."""
        from skills.breaking_detector import BreakingDetector

        detector = BreakingDetector()

        pub_time = datetime.now() - timedelta(hours=2)
        recency = detector.get_recency_minutes(pub_time)

        assert recency == 120

    def test_future_date_returns_zero(self):
        """Test that future dates return 0 minutes."""
        from skills.breaking_detector import BreakingDetector

        detector = BreakingDetector()

        pub_time = datetime.now() + timedelta(hours=1)
        recency = detector.get_recency_minutes(pub_time)

        assert recency == 0

    def test_none_date_returns_none(self):
        """Test that None date returns None."""
        from skills.breaking_detector import BreakingDetector

        detector = BreakingDetector()

        recency = detector.get_recency_minutes(None)

        assert recency is None


class TestBreakingAnalysis:
    """Tests for the full breaking news analysis."""

    def test_analyze_breaking_news_from_tier_1(self):
        """Test analysis of breaking news from tier 1 source."""
        from skills.breaking_detector import BreakingDetector
        from shared.models import ArticleDraft, ArticleSource

        detector = BreakingDetector()

        draft = ArticleDraft(
            title="BREAKING: RBI Raises Interest Rates",
            description="Reserve Bank announces rate hike",
            category="Finance",
            contentType="News",
            body="The RBI today announced...",
            wordCount=300,
            pubDate=datetime.now() - timedelta(minutes=10),
            sources=[
                ArticleSource(id="1", title="RBI", url="https://rbi.org.in/press/123")
            ],
        )

        analysis = detector.analyze(draft)

        assert analysis.is_breaking is True
        assert analysis.urgency == "critical"
        assert analysis.source_tier == "tier_1"
        assert analysis.confidence >= 0.8
        assert "BREAKING:" in analysis.title_indicators

    def test_analyze_breaking_news_from_tier_2(self):
        """Test analysis of breaking news from tier 2 source."""
        from skills.breaking_detector import BreakingDetector
        from shared.models import ArticleDraft, ArticleSource

        detector = BreakingDetector()

        draft = ArticleDraft(
            title="JUST IN: Major security incident at Delhi airport",
            description="Breaking news from Reuters",
            category="Security",
            contentType="News",
            body="Reuters reports...",
            wordCount=350,
            pubDate=datetime.now() - timedelta(minutes=15),
            sources=[
                ArticleSource(
                    id="1", title="Reuters", url="https://reuters.com/article/123"
                )
            ],
        )

        analysis = detector.analyze(draft)

        assert analysis.is_breaking is True
        assert analysis.urgency in ["critical", "high"]
        assert analysis.source_tier == "tier_2"

    def test_analyze_non_breaking_standard_news(self):
        """Test analysis of standard non-breaking news."""
        from skills.breaking_detector import BreakingDetector
        from shared.models import ArticleDraft, ArticleSource

        detector = BreakingDetector()

        draft = ArticleDraft(
            title="Security Industry Report 2026",
            description="Annual security industry analysis",
            category="Security",
            contentType="News",
            body="This comprehensive report...",
            wordCount=1000,
            pubDate=datetime.now() - timedelta(hours=24),
            sources=[
                ArticleSource(id="1", title="Report", url="https://example.com/report")
            ],
        )

        analysis = detector.analyze(draft)

        assert analysis.is_breaking is False
        assert analysis.urgency == "low"
        assert len(analysis.title_indicators) == 0

    def test_analyze_breaking_title_but_untrusted_source(self):
        """Test analysis of breaking title from untrusted source."""
        from skills.breaking_detector import BreakingDetector
        from shared.models import ArticleDraft, ArticleSource

        detector = BreakingDetector()

        draft = ArticleDraft(
            title="BREAKING: Unverified claim from blog",
            description="Breaking news",
            category="Security",
            contentType="News",
            body="Some blog reports...",
            wordCount=200,
            pubDate=datetime.now() - timedelta(minutes=5),
            sources=[
                ArticleSource(id="1", title="Blog", url="https://random-blog.com/post")
            ],
        )

        analysis = detector.analyze(draft)

        # Breaking indicators present but low confidence due to untrusted source
        assert "BREAKING:" in analysis.title_indicators
        assert analysis.source_tier is None
        # Should not be marked as breaking without trusted source
        assert analysis.is_breaking is False or analysis.confidence < 0.5

    def test_analyze_trusted_source_but_old_article(self):
        """Test analysis of trusted source but old article."""
        from skills.breaking_detector import BreakingDetector
        from shared.models import ArticleDraft, ArticleSource

        detector = BreakingDetector()

        draft = ArticleDraft(
            title="Government Policy Announcement",
            description="Policy change details",
            category="Compliance",
            contentType="News",
            body="The government announced...",
            wordCount=500,
            pubDate=datetime.now() - timedelta(hours=48),
            sources=[
                ArticleSource(id="1", title="PIB", url="https://pib.gov.in/release/123")
            ],
        )

        analysis = detector.analyze(draft)

        # Trusted source but old article - not breaking
        assert analysis.source_tier == "tier_1"
        assert analysis.is_breaking is False
        assert analysis.urgency in ["low", "medium"]

    def test_analyze_no_sources(self):
        """Test analysis of draft with no sources."""
        from skills.breaking_detector import BreakingDetector
        from shared.models import ArticleDraft

        detector = BreakingDetector()

        draft = ArticleDraft(
            title="BREAKING: Something happened",
            description="Breaking news",
            category="News",
            contentType="News",
            body="Content",
            wordCount=200,
            sources=[],
        )

        analysis = detector.analyze(draft)

        # No source means not breaking
        assert analysis.source_tier is None
        assert analysis.is_breaking is False


class TestUrgencyDetermination:
    """Tests for urgency level determination."""

    def test_critical_urgency_tier_1_recent_breaking(self):
        """Test that tier 1 source + recent + breaking = critical."""
        from skills.breaking_detector import BreakingDetector

        detector = BreakingDetector()

        urgency = detector.determine_urgency(
            title_indicators=["BREAKING:"],
            source_tier="tier_1",
            recency_minutes=10,
        )

        assert urgency == "critical"

    def test_high_urgency_tier_2_recent_breaking(self):
        """Test that tier 2 source + recent + breaking = high."""
        from skills.breaking_detector import BreakingDetector

        detector = BreakingDetector()

        urgency = detector.determine_urgency(
            title_indicators=["BREAKING:"],
            source_tier="tier_2",
            recency_minutes=15,
        )

        assert urgency in ["critical", "high"]

    def test_medium_urgency_tier_3_recent(self):
        """Test that tier 3 source + recent = medium at best."""
        from skills.breaking_detector import BreakingDetector

        detector = BreakingDetector()

        urgency = detector.determine_urgency(
            title_indicators=["BREAKING:"],
            source_tier="tier_3",
            recency_minutes=20,
        )

        assert urgency in ["medium", "high"]

    def test_low_urgency_old_article(self):
        """Test that old articles get low urgency."""
        from skills.breaking_detector import BreakingDetector

        detector = BreakingDetector()

        urgency = detector.determine_urgency(
            title_indicators=[],
            source_tier="tier_1",
            recency_minutes=180,  # 3 hours old
        )

        assert urgency in ["low", "medium"]

    def test_low_urgency_no_indicators(self):
        """Test that no indicators means low urgency."""
        from skills.breaking_detector import BreakingDetector

        detector = BreakingDetector()

        urgency = detector.determine_urgency(
            title_indicators=[],
            source_tier=None,
            recency_minutes=None,
        )

        assert urgency == "low"
