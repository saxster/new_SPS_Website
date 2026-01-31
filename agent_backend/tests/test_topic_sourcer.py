"""
Tests for TopicSourcer.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestTopicSourcer:
    """Tests for TopicSourcer class."""

    @pytest.fixture
    def sourcer(self):
        """Create TopicSourcer instance with mocked dependencies."""
        with patch("skills.topic_sourcer.config") as mock_config:
            mock_config.get.side_effect = lambda key, default=None: {
                "topic_sourcer.enabled": True,
                "topic_sourcer.scoring": {
                    "timeliness": 0.30,
                    "authority": 0.30,
                    "demand": 0.20,
                    "gap": 0.20,
                },
                "topic_sourcer.auto_queue_threshold": 70,
                "topic_sourcer.require_review_below": 50,
            }.get(key, default)

            from skills.topic_sourcer import TopicSourcer

            return TopicSourcer()

    def test_enabled_by_default(self, sourcer):
        """Test sourcer is enabled by default."""
        assert sourcer.enabled is True

    def test_scoring_weights_configured(self, sourcer):
        """Test scoring weights are properly configured."""
        assert "timeliness" in sourcer.scoring_weights
        assert "authority" in sourcer.scoring_weights
        assert "demand" in sourcer.scoring_weights
        assert "gap" in sourcer.scoring_weights

        # Weights should sum to approximately 1.0
        total = sum(sourcer.scoring_weights.values())
        assert 0.99 <= total <= 1.01

    def test_source_topics_returns_list(self, sourcer):
        """Test source_topics returns a list."""
        with patch.object(sourcer, "_thinktank_miner", None):
            with patch.object(sourcer, "_regulatory_miner", None):
                with patch.object(sourcer, "_serp_miner", None):
                    with patch.object(sourcer, "_calendar_engine", None):
                        topics = sourcer.source_topics(strategy="all")
                        assert isinstance(topics, list)

    def test_source_topics_disabled(self):
        """Test source_topics returns empty when disabled."""
        with patch("skills.topic_sourcer.config") as mock_config:
            mock_config.get.side_effect = lambda key, default=None: {
                "topic_sourcer.enabled": False,
            }.get(key, default)

            from skills.topic_sourcer import TopicSourcer

            sourcer = TopicSourcer()
            topics = sourcer.source_topics()
            assert topics == []

    def test_prioritize_topics_sorts_by_score(self, sourcer):
        """Test prioritize_topics sorts topics by overall score."""
        from shared.models import SourcedTopic

        topics = [
            SourcedTopic(
                id="low",
                title="Low Score",
                source_type="gap",
                overall_score=30,
                urgency="low",
            ),
            SourcedTopic(
                id="high",
                title="High Score",
                source_type="breaking",
                overall_score=80,
                urgency="medium",
            ),
            SourcedTopic(
                id="medium",
                title="Medium Score",
                source_type="regulatory",
                overall_score=50,
                urgency="medium",
            ),
        ]

        sorted_topics = sourcer.prioritize_topics(topics)

        assert sorted_topics[0].id == "high"
        assert sorted_topics[-1].id == "low"

    def test_prioritize_topics_urgency_boost(self, sourcer):
        """Test critical urgency gets score boost."""
        from shared.models import SourcedTopic

        topics = [
            SourcedTopic(
                id="critical",
                title="Critical Topic",
                source_type="breaking",
                overall_score=60,
                urgency="critical",
            ),
            SourcedTopic(
                id="normal",
                title="Normal Topic",
                source_type="gap",
                overall_score=70,
                urgency="low",
            ),
        ]

        sorted_topics = sourcer.prioritize_topics(topics)

        # Critical topic should be first due to +20 boost
        assert sorted_topics[0].id == "critical"
        assert sorted_topics[0].overall_score == 80  # 60 + 20

    def test_deduplicate_topics(self, sourcer):
        """Test _deduplicate_topics removes duplicates."""
        from shared.models import SourcedTopic

        topics = [
            SourcedTopic(
                id="1",
                title="Same Topic Title",
                source_type="breaking",
                overall_score=80,
            ),
            SourcedTopic(
                id="2",
                title="Same Topic Title",  # Duplicate title
                source_type="regulatory",
                overall_score=70,
            ),
            SourcedTopic(
                id="3",
                title="Different Topic",
                source_type="gap",
                overall_score=60,
            ),
        ]

        unique = sourcer._deduplicate_topics(topics)

        assert len(unique) == 2
        # First occurrence should be kept
        assert unique[0].id == "1"
        assert unique[1].id == "3"

    def test_calculate_score_weighted(self, sourcer):
        """Test _calculate_score applies weights correctly."""
        score = sourcer._calculate_score(
            timeliness=100,
            authority=100,
            gap=100,
        )
        # With all at 100 (except demand at 50), should be high
        assert score > 70

        low_score = sourcer._calculate_score(
            timeliness=0,
            authority=0,
            gap=0,
        )
        # With all at 0 (except demand at 50), should be low
        assert low_score < 20

    def test_evidence_to_topic_conversion(self, sourcer):
        """Test _evidence_to_topic creates valid SourcedTopic."""
        from skills.miners.base_miner import EvidenceItem

        evidence = EvidenceItem(
            id="test123",
            title="Test Evidence Title",
            url="https://example.com/test",
            raw_content="Test content",
            source_type="news",
            publisher="Test Publisher",
            published=datetime.now() - timedelta(hours=2),
            credibility_weight=8,
            domain="example.com",
            snippet="Test snippet",
            metadata={"source_id": "test_source"},
        )

        topic = sourcer._evidence_to_topic(
            evidence,
            source_type="breaking",
            content_type="News",
            urgency="high",
        )

        assert topic.source_type == "breaking"
        assert topic.content_type == "News"
        assert topic.urgency == "high"
        assert topic.source_url == "https://example.com/test"
        assert topic.authority_score == 80  # 8 * 10

    def test_timeliness_calculation(self, sourcer):
        """Test timeliness score varies by recency."""
        from skills.miners.base_miner import EvidenceItem

        # Very recent item
        recent = EvidenceItem(
            id="recent",
            title="Recent Item",
            url="https://example.com",
            raw_content="Content",
            source_type="news",
            publisher="Publisher",
            published=datetime.now() - timedelta(hours=1),
            credibility_weight=5,
        )
        recent_topic = sourcer._evidence_to_topic(recent, "breaking", "News")
        assert recent_topic.timeliness_score == 100

        # Day old item
        day_old = EvidenceItem(
            id="day_old",
            title="Day Old Item",
            url="https://example.com",
            raw_content="Content",
            source_type="news",
            publisher="Publisher",
            published=datetime.now() - timedelta(hours=12),
            credibility_weight=5,
        )
        day_topic = sourcer._evidence_to_topic(day_old, "breaking", "News")
        assert day_topic.timeliness_score == 85

        # Week old item
        week_old = EvidenceItem(
            id="week_old",
            title="Week Old Item",
            url="https://example.com",
            raw_content="Content",
            source_type="news",
            publisher="Publisher",
            published=datetime.now() - timedelta(days=5),
            credibility_weight=5,
        )
        week_topic = sourcer._evidence_to_topic(week_old, "breaking", "News")
        assert week_topic.timeliness_score == 50

    def test_get_sourcer_stats(self, sourcer):
        """Test get_sourcer_stats returns expected structure."""
        stats = sourcer.get_sourcer_stats()

        assert "enabled" in stats
        assert "scoring_weights" in stats
        assert "miners" in stats
        assert isinstance(stats["miners"], dict)


class TestTopicSourcerStrategies:
    """Tests for individual sourcing strategies."""

    @pytest.fixture
    def sourcer_with_mocks(self):
        """Create sourcer with mocked miners."""
        from skills.topic_sourcer import TopicSourcer

        sourcer = TopicSourcer()

        # Mock all miners
        sourcer._thinktank_miner = Mock()
        sourcer._regulatory_miner = Mock()
        sourcer._serp_miner = Mock()
        sourcer._calendar_engine = Mock()

        return sourcer

    def test_get_breaking_topics_uses_serp(self, sourcer_with_mocks):
        """Test get_breaking_topics uses SerpMiner."""
        sourcer_with_mocks._serp_miner.fetch_breaking_news.return_value = []
        sourcer_with_mocks._regulatory_miner.fetch_alerts.return_value = []

        topics = sourcer_with_mocks.get_breaking_topics()

        assert isinstance(topics, list)
        sourcer_with_mocks._serp_miner.fetch_breaking_news.assert_called_once()

    def test_get_regulatory_topics_uses_miner(self, sourcer_with_mocks):
        """Test get_regulatory_topics uses RegulatoryMiner."""
        sourcer_with_mocks._regulatory_miner.fetch_alerts.return_value = []

        topics = sourcer_with_mocks.get_regulatory_topics()

        assert isinstance(topics, list)
        sourcer_with_mocks._regulatory_miner.fetch_alerts.assert_called_once()

    def test_get_intellectual_topics_uses_miner(self, sourcer_with_mocks):
        """Test get_intellectual_topics uses ThinkTankMiner."""
        sourcer_with_mocks._thinktank_miner.is_available.return_value = True
        sourcer_with_mocks._thinktank_miner.fetch_latest.return_value = []

        topics = sourcer_with_mocks.get_intellectual_topics()

        assert isinstance(topics, list)
        sourcer_with_mocks._thinktank_miner.fetch_latest.assert_called_once()

    def test_get_calendar_topics_uses_engine(self, sourcer_with_mocks):
        """Test get_calendar_topics uses CalendarEngine."""
        sourcer_with_mocks._calendar_engine.get_actionable_topics.return_value = []

        topics = sourcer_with_mocks.get_calendar_topics()

        assert isinstance(topics, list)
        sourcer_with_mocks._calendar_engine.get_actionable_topics.assert_called_once()
