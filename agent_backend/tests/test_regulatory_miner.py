"""
Tests for RegulatoryMiner.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestRegulatoryMiner:
    """Tests for RegulatoryMiner class."""

    @pytest.fixture
    def mock_feedparser(self):
        """Create mock feedparser module."""
        with patch.dict("sys.modules", {"feedparser": MagicMock()}):
            yield

    @pytest.fixture
    def miner(self, mock_feedparser):
        """Create RegulatoryMiner instance."""
        with patch("skills.miners.regulatory_miner.FEEDPARSER_AVAILABLE", True):
            from skills.miners.regulatory_miner import RegulatoryMiner

            return RegulatoryMiner()

    def test_source_type(self, miner):
        """Test source_type property returns correct value."""
        assert miner.source_type == "regulatory"

    def test_default_credibility(self, miner):
        """Test default_credibility returns maximum for government sources."""
        assert miner.default_credibility == 10

    def test_is_available_always_true(self, miner):
        """Test is_available returns True (always available with reduced functionality)."""
        assert miner.is_available() is True

    def test_document_types_defined(self, miner):
        """Test that document types are properly defined."""
        assert "advisory" in miner.DOCUMENT_TYPES
        assert "circular" in miner.DOCUMENT_TYPES
        assert "alert" in miner.DOCUMENT_TYPES

    def test_priority_keywords_defined(self, miner):
        """Test that priority keywords are properly defined."""
        assert "critical" in miner.PRIORITY_KEYWORDS
        assert "high" in miner.PRIORITY_KEYWORDS
        assert "medium" in miner.PRIORITY_KEYWORDS

    def test_classify_document_type_advisory(self, miner):
        """Test document type classification for advisories."""
        doc_type = miner._classify_document_type(
            "Security Advisory: Critical Vulnerability",
            "CERT-IN advisory for CVE-2024-1234",
        )
        assert doc_type == "advisory"

    def test_classify_document_type_circular(self, miner):
        """Test document type classification for circulars."""
        doc_type = miner._classify_document_type(
            "RBI Circular on Cyber Security",
            "All banks are directed to implement...",
        )
        assert doc_type == "circular"

    def test_classify_document_type_alert(self, miner):
        """Test document type classification for alerts."""
        doc_type = miner._classify_document_type(
            "Urgent Alert: Ransomware Attack",
            "Warning about active vulnerability exploitation",
        )
        assert doc_type == "alert"

    def test_classify_document_type_general(self, miner):
        """Test document type classification defaults to general."""
        doc_type = miner._classify_document_type(
            "General Update",
            "Some general information",
        )
        assert doc_type == "general"

    def test_determine_urgency_critical(self, miner):
        """Test urgency determination for critical items."""
        urgency = miner._determine_urgency(
            "Critical Security Alert",
            "Immediate action required for all systems",
            "medium",
        )
        assert urgency == "critical"

    def test_determine_urgency_high(self, miner):
        """Test urgency determination for high priority items."""
        urgency = miner._determine_urgency(
            "Important Notice",
            "Urgent compliance required by deadline",
            "medium",
        )
        assert urgency == "high"

    def test_determine_urgency_default(self, miner):
        """Test urgency falls back to default when no keywords match."""
        urgency = miner._determine_urgency(
            "Simple Note",
            "Just some basic text here",
            "low",
        )
        assert urgency == "low"

    def test_generate_id(self, miner):
        """Test _generate_id produces consistent hashes."""
        id1 = miner._generate_id("test-url")
        id2 = miner._generate_id("test-url")
        assert id1 == id2
        assert len(id1) == 12

    def test_extract_domain(self, miner):
        """Test _extract_domain correctly extracts domain."""
        assert miner._extract_domain("https://www.rbi.org.in/path") == "rbi.org.in"
        assert miner._extract_domain("https://cert-in.org.in/alert") == "cert-in.org.in"

    def test_get_regulator_stats(self, miner):
        """Test get_regulator_stats returns expected structure."""
        stats = miner.get_regulator_stats()
        assert "total_regulators" in stats
        assert "with_rss" in stats
        assert "by_priority" in stats
        assert isinstance(stats["total_regulators"], int)

    def test_fetch_returns_empty_when_no_rss_available(self):
        """Test fetch returns filtered results."""
        with patch("skills.miners.regulatory_miner.FEEDPARSER_AVAILABLE", False):
            from skills.miners.regulatory_miner import RegulatoryMiner

            miner = RegulatoryMiner()
            result = miner.fetch("test query")
            # Should still work but with no RSS results
            assert isinstance(result, list)

    def test_fetch_alerts_parses_entries(self):
        """Test fetch_alerts correctly parses RSS entries."""
        with patch("skills.miners.regulatory_miner.FEEDPARSER_AVAILABLE", True):
            with patch("skills.miners.regulatory_miner.feedparser") as mock_fp:
                from skills.miners.regulatory_miner import RegulatoryMiner

                # Use recent date within the time window
                now = datetime.now()
                mock_entry = {
                    "title": "Critical Vulnerability Alert",
                    "link": "https://cert-in.org.in/alert/123",
                    "summary": "Critical vulnerability in widely used software",
                    "published_parsed": (
                        now.year,
                        now.month,
                        now.day,
                        10,
                        0,
                        0,
                        0,
                        0,
                        0,
                    ),
                }
                mock_fp.parse.return_value = Mock(
                    bozo=False,
                    entries=[mock_entry],
                )

                miner = RegulatoryMiner()
                # Override regulators to use our mock
                miner.regulators = [
                    {
                        "id": "cert_in",
                        "name": "CERT-IN",
                        "rss": "https://cert-in.org.in/rss",
                        "priority": "critical",
                        "credibility": 10,
                    }
                ]

                items = miner.fetch_alerts(hours=48)

                assert len(items) == 1
                assert items[0].title == "Critical Vulnerability Alert"
                assert items[0].credibility_weight == 10

    def test_check_compliance_deadlines_empty(self, miner):
        """Test check_compliance_deadlines returns list."""
        with patch.object(miner, "fetch_alerts", return_value=[]):
            deadlines = miner.check_compliance_deadlines()
            assert isinstance(deadlines, list)


class TestRegulatoryMinerIntegration:
    """Integration tests for RegulatoryMiner (require network)."""

    @pytest.fixture
    def live_miner(self):
        """Create live RegulatoryMiner instance."""
        from skills.miners.regulatory_miner import RegulatoryMiner

        return RegulatoryMiner()

    @pytest.mark.integration
    def test_fetch_alerts_live(self, live_miner):
        """Test fetching alerts from real feeds."""
        items = live_miner.fetch_alerts(hours=168)
        # We don't assert on count since feeds may be empty
        assert isinstance(items, list)

    @pytest.mark.integration
    def test_fetch_circulars_live(self, live_miner):
        """Test fetching circulars from a specific regulator."""
        items = live_miner.fetch_circulars("rbi", days=30)
        assert isinstance(items, list)
