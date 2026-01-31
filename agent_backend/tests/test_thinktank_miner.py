"""
Tests for ThinkTankMiner.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestThinkTankMiner:
    """Tests for ThinkTankMiner class."""

    @pytest.fixture
    def mock_feedparser(self):
        """Create mock feedparser module."""
        with patch.dict("sys.modules", {"feedparser": MagicMock()}):
            yield

    @pytest.fixture
    def miner(self, mock_feedparser):
        """Create ThinkTankMiner instance with mocked feedparser."""
        with patch("skills.miners.thinktank_miner.FEEDPARSER_AVAILABLE", True):
            from skills.miners.thinktank_miner import ThinkTankMiner

            return ThinkTankMiner()

    def test_source_type(self, miner):
        """Test source_type property returns correct value."""
        assert miner.source_type == "thinktank"

    def test_default_credibility(self, miner):
        """Test default_credibility returns expected value."""
        assert miner.default_credibility == 8

    def test_is_available_with_feedparser(self, miner):
        """Test is_available returns True when feedparser is available."""
        assert miner.is_available() is True

    def test_is_available_without_feedparser(self):
        """Test is_available returns False when feedparser is not available."""
        with patch("skills.miners.thinktank_miner.FEEDPARSER_AVAILABLE", False):
            from skills.miners.thinktank_miner import ThinkTankMiner

            miner = ThinkTankMiner()
            assert miner.is_available() is False

    def test_security_keywords_defined(self, miner):
        """Test that security keywords set is properly defined."""
        assert len(miner.SECURITY_KEYWORDS) > 0
        assert "security" in miner.SECURITY_KEYWORDS
        assert "cyber" in miner.SECURITY_KEYWORDS

    def test_is_security_relevant_positive(self, miner):
        """Test _is_security_relevant returns True for security content."""
        assert (
            miner._is_security_relevant(
                "Cybersecurity Threats in India",
                "Analysis of recent cyber attacks",
            )
            is True
        )

    def test_is_security_relevant_negative(self, miner):
        """Test _is_security_relevant returns False for non-security content."""
        assert (
            miner._is_security_relevant(
                "Recipe for chocolate cake",
                "How to bake a delicious cake",
            )
            is False
        )

    def test_generate_id(self, miner):
        """Test _generate_id produces consistent hashes."""
        id1 = miner._generate_id("test-url")
        id2 = miner._generate_id("test-url")
        assert id1 == id2
        assert len(id1) == 12

    def test_extract_domain(self, miner):
        """Test _extract_domain correctly extracts domain."""
        assert miner._extract_domain("https://www.example.com/path") == "example.com"
        assert miner._extract_domain("https://orfonline.org/article") == "orfonline.org"
        assert miner._extract_domain("") == ""

    def test_get_source_stats(self, miner):
        """Test get_source_stats returns expected structure."""
        stats = miner.get_source_stats()
        assert "total_sources" in stats
        assert "by_tier" in stats
        assert "available" in stats
        assert isinstance(stats["total_sources"], int)

    def test_fetch_returns_empty_when_unavailable(self):
        """Test fetch returns empty list when feedparser unavailable."""
        with patch("skills.miners.thinktank_miner.FEEDPARSER_AVAILABLE", False):
            from skills.miners.thinktank_miner import ThinkTankMiner

            miner = ThinkTankMiner()
            result = miner.fetch("test query")
            assert result == []

    def test_fetch_latest_returns_empty_when_unavailable(self):
        """Test fetch_latest returns empty list when feedparser unavailable."""
        with patch("skills.miners.thinktank_miner.FEEDPARSER_AVAILABLE", False):
            from skills.miners.thinktank_miner import ThinkTankMiner

            miner = ThinkTankMiner()
            result = miner.fetch_latest(days=7)
            assert result == []

    @patch("skills.miners.thinktank_miner.feedparser")
    def test_fetch_rss_parses_entries(self, mock_fp, miner):
        """Test _fetch_rss correctly parses RSS entries."""
        # Setup mock feed with recent date (within cutoff)
        now = datetime.now()
        mock_entry = {
            "title": "Cybersecurity Report 2024",
            "link": "https://example.org/report",
            "summary": "Analysis of security trends in India",
            "published_parsed": (now.year, now.month, now.day, 10, 0, 0, 0, 0, 0),
        }
        mock_fp.parse.return_value = Mock(
            bozo=False,
            entries=[mock_entry],
        )

        source = {
            "id": "test_source",
            "name": "Test Think Tank",
            "rss": "https://example.org/feed",
            "credibility": 9,
            "focus": ["security"],
        }

        cutoff = datetime.now() - timedelta(days=30)
        items = miner._fetch_rss(source, cutoff)

        assert len(items) == 1
        assert items[0].title == "Cybersecurity Report 2024"
        assert items[0].credibility_weight == 9


class TestThinkTankMinerIntegration:
    """Integration tests for ThinkTankMiner (require network)."""

    @pytest.fixture
    def live_miner(self):
        """Create live ThinkTankMiner instance."""
        try:
            from skills.miners.thinktank_miner import ThinkTankMiner

            return ThinkTankMiner()
        except ImportError:
            pytest.skip("feedparser not installed")

    @pytest.mark.integration
    def test_fetch_latest_live(self, live_miner):
        """Test fetching latest content from real feeds."""
        if not live_miner.is_available():
            pytest.skip("feedparser not available")

        items = live_miner.fetch_latest(days=30)
        # We don't assert on count since feeds may be empty
        assert isinstance(items, list)
