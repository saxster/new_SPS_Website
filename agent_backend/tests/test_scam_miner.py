"""
Tests for ScamMiner - Real-time fraud intelligence.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from skills.miners.scam_miner import ScamMiner


class TestScamMiner:
    """Test ScamMiner functionality."""

    def test_init(self):
        """Test ScamMiner initialization."""
        miner = ScamMiner()
        assert miner.source_type == "scam"
        assert miner.default_credibility == 8

    def test_is_available_without_api_key(self):
        """Test availability without API key."""
        with patch.dict("os.environ", {}, clear=True):
            miner = ScamMiner()
            # Should still be available, just without SerpAPI
            assert miner.is_available()

    def test_classify_scam_banking(self):
        """Test scam classification for banking fraud."""
        miner = ScamMiner()
        scam_type = miner.classify_scam(
            "Digital Arrest Scam Warning from Police",
            "Fraudsters posing as police officers demanding UPI payments",
        )
        assert scam_type == "banking"

    def test_classify_scam_phishing(self):
        """Test scam classification for phishing."""
        miner = ScamMiner()
        scam_type = miner.classify_scam(
            "OTP Fraud Alert", "Scammers asking for OTP to verify bank account"
        )
        assert scam_type == "phishing"

    def test_classify_scam_investment(self):
        """Test scam classification for investment fraud."""
        miner = ScamMiner()
        scam_type = miner.classify_scam(
            "Crypto Trading Scam Warning",
            "Ponzi scheme promising guaranteed returns in cryptocurrency",
        )
        assert scam_type == "investment"

    def test_classify_scam_job(self):
        """Test scam classification for job scams."""
        miner = ScamMiner()
        scam_type = miner.classify_scam(
            "Fake Recruitment Alert",
            "Work from home fraud asking for registration fees",
        )
        assert scam_type == "job"

    def test_classify_scam_impersonation(self):
        """Test scam classification for impersonation."""
        miner = ScamMiner()
        scam_type = miner.classify_scam(
            "Fake CBI Officer Scam",
            "Fraudsters impersonating government officials for customs fraud",
        )
        assert scam_type == "impersonation"

    def test_classify_scam_no_match(self):
        """Test scam classification with no matching type."""
        miner = ScamMiner()
        scam_type = miner.classify_scam(
            "General News Article", "This is about something unrelated to scams"
        )
        assert scam_type is None

    def test_get_prevention_tips_banking(self):
        """Test getting prevention tips for banking scams."""
        miner = ScamMiner()
        tips = miner.get_prevention_tips("banking")

        assert len(tips) > 0
        assert any("OTP" in tip or "PIN" in tip for tip in tips)

    def test_get_prevention_tips_phishing(self):
        """Test getting prevention tips for phishing scams."""
        miner = ScamMiner()
        tips = miner.get_prevention_tips("phishing")

        assert len(tips) > 0
        assert any("OTP" in tip for tip in tips)

    def test_get_prevention_tips_unknown(self):
        """Test getting prevention tips for unknown scam type."""
        miner = ScamMiner()
        tips = miner.get_prevention_tips("unknown_type")

        # Should return default tips
        assert len(tips) > 0
        assert any("cybercrime.gov.in" in tip for tip in tips)

    def test_scam_keywords_coverage(self):
        """Test that all scam types have keywords defined."""
        miner = ScamMiner()
        expected_types = [
            "phishing",
            "investment",
            "job",
            "banking",
            "impersonation",
            "ecommerce",
            "loan",
            "lottery",
        ]

        for scam_type in expected_types:
            assert scam_type in miner.SCAM_KEYWORDS
            assert len(miner.SCAM_KEYWORDS[scam_type]) > 0

    def test_official_sources(self):
        """Test official sources are properly configured."""
        miner = ScamMiner()

        # Key sources should have high credibility
        assert miner.OFFICIAL_SOURCES.get("cybercrime.gov.in") == 10
        assert miner.OFFICIAL_SOURCES.get("rbi.org.in") == 10
        assert miner.OFFICIAL_SOURCES.get("cert-in.org.in") == 10

    def test_extract_domain(self):
        """Test domain extraction from URLs."""
        miner = ScamMiner()

        assert miner._extract_domain("https://www.example.com/path") == "example.com"
        assert (
            miner._extract_domain("https://cybercrime.gov.in/alert")
            == "cybercrime.gov.in"
        )
        assert miner._extract_domain("http://sub.domain.com") == "sub.domain.com"

    def test_get_source_credibility(self):
        """Test source credibility scoring."""
        miner = ScamMiner()

        # Official sources
        assert miner._get_source_credibility("cybercrime.gov.in") == 10
        assert miner._get_source_credibility("rbi.org.in") == 10

        # Government domains
        assert miner._get_source_credibility("some.gov.in") == 9

        # Unknown sources
        assert miner._get_source_credibility("random-site.com") == 8

    @patch("skills.miners.scam_miner.SERPAPI_AVAILABLE", False)
    def test_fetch_without_serpapi(self):
        """Test fetch returns empty when SerpAPI unavailable."""
        miner = ScamMiner()
        results = miner.fetch("test scam", limit=5)
        assert results == []

    def test_calculate_urgency_critical(self):
        """Test urgency calculation for critical alerts."""
        miner = ScamMiner()

        mock_item = Mock()
        mock_item.title = "Digital Arrest Nationwide Scam Alert"
        mock_item.snippet = "RBI warning about digital arrest fraud"
        mock_item.credibility_weight = 10

        urgency = miner._calculate_urgency(mock_item)
        assert urgency == "critical"

    def test_calculate_urgency_high(self):
        """Test urgency calculation for high alerts."""
        miner = ScamMiner()

        mock_item = Mock()
        mock_item.title = "Urgent Warning: New Scam Alert"
        mock_item.snippet = "Police warning about ongoing fraud"
        mock_item.credibility_weight = 8

        urgency = miner._calculate_urgency(mock_item)
        assert urgency == "high"

    def test_calculate_urgency_medium(self):
        """Test urgency calculation for medium alerts."""
        miner = ScamMiner()

        mock_item = Mock()
        mock_item.title = "Scam Report Filed"
        mock_item.snippet = "A complaint was filed about online fraud"
        mock_item.credibility_weight = 6

        urgency = miner._calculate_urgency(mock_item)
        assert urgency == "medium"


class TestScamMinerIntegration:
    """Integration tests for ScamMiner (requires SerpAPI)."""

    @pytest.mark.skipif(
        True,  # Skip by default since it requires API key
        reason="Requires SERPAPI_API_KEY",
    )
    def test_fetch_active_scams_live(self):
        """Test fetching active scams with live API."""
        miner = ScamMiner()
        if not miner.api_key:
            pytest.skip("SERPAPI_API_KEY not set")

        scams = miner.fetch_active_scams(hours=48)
        assert isinstance(scams, list)

    @pytest.mark.skipif(True, reason="Requires SERPAPI_API_KEY")
    def test_get_trending_scams_live(self):
        """Test getting trending scams with live API."""
        miner = ScamMiner()
        if not miner.api_key:
            pytest.skip("SERPAPI_API_KEY not set")

        trending = miner.get_trending_scams(limit=5)
        assert isinstance(trending, list)
