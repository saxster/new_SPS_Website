"""
Tests for MarketMiner - Economic security intelligence.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from skills.miners.market_miner import MarketMiner


class TestMarketMiner:
    """Test MarketMiner functionality."""

    def test_init(self):
        """Test MarketMiner initialization."""
        miner = MarketMiner()
        assert miner.source_type == "market"
        assert miner.default_credibility == 8

    def test_is_available_enabled(self):
        """Test availability when enabled."""
        miner = MarketMiner()
        assert miner.is_available()

    def test_classify_alert_sebi_order(self):
        """Test alert classification for SEBI orders."""
        miner = MarketMiner()
        alert_type = miner._classify_alert(
            "SEBI Penalty on XYZ Company",
            "SEBI order imposing fine for market manipulation",
        )
        assert alert_type == "sebi_order"

    def test_classify_alert_rbi_circular(self):
        """Test alert classification for RBI circulars."""
        miner = MarketMiner()
        alert_type = miner._classify_alert(
            "RBI Issues New Guideline", "RBI circular on digital lending regulations"
        )
        assert alert_type == "rbi_circular"

    def test_classify_alert_ed_action(self):
        """Test alert classification for ED actions."""
        miner = MarketMiner()
        alert_type = miner._classify_alert(
            "ED Arrests Business Tycoon", "Money laundering investigation under PMLA"
        )
        assert alert_type == "ed_action"

    def test_classify_alert_investor_warning(self):
        """Test alert classification for investor warnings."""
        miner = MarketMiner()
        alert_type = miner._classify_alert(
            "SEBI Investor Warning",
            "Beware of unauthorized scheme offering guaranteed returns",
        )
        assert alert_type == "investor_warning"

    def test_classify_alert_fraud_case(self):
        """Test alert classification for fraud cases."""
        miner = MarketMiner()
        alert_type = miner._classify_alert(
            "Bank Fraud Case Registered",
            "Loan fraud case involving embezzlement of funds",
        )
        assert alert_type == "fraud_case"

    def test_regulatory_sources_credibility(self):
        """Test regulatory sources have correct credibility."""
        miner = MarketMiner()

        assert miner.REGULATORY_SOURCES.get("sebi.gov.in") == 10
        assert miner.REGULATORY_SOURCES.get("rbi.org.in") == 10
        assert miner.REGULATORY_SOURCES.get("enforcementdirectorate.gov.in") == 10
        assert miner.REGULATORY_SOURCES.get("mca.gov.in") == 10

    def test_financial_news_sources_credibility(self):
        """Test financial news sources have correct credibility."""
        miner = MarketMiner()

        assert miner.FINANCIAL_NEWS.get("economictimes.indiatimes.com") == 8
        assert miner.FINANCIAL_NEWS.get("livemint.com") == 8
        assert miner.FINANCIAL_NEWS.get("moneycontrol.com") == 8

    def test_extract_domain(self):
        """Test domain extraction from URLs."""
        miner = MarketMiner()

        assert miner._extract_domain("https://www.sebi.gov.in/order") == "sebi.gov.in"
        assert (
            miner._extract_domain("https://economictimes.indiatimes.com/news")
            == "economictimes.indiatimes.com"
        )

    def test_get_source_credibility_regulatory(self):
        """Test source credibility for regulatory sources."""
        miner = MarketMiner()

        assert miner._get_source_credibility("sebi.gov.in") == 10
        assert miner._get_source_credibility("rbi.org.in") == 10

    def test_get_source_credibility_news(self):
        """Test source credibility for news sources."""
        miner = MarketMiner()

        assert miner._get_source_credibility("economictimes.indiatimes.com") == 8
        assert miner._get_source_credibility("livemint.com") == 8

    def test_get_source_credibility_government(self):
        """Test source credibility for government domains."""
        miner = MarketMiner()

        assert miner._get_source_credibility("some.gov.in") == 9

    def test_calculate_urgency_regulatory_source(self):
        """Test urgency calculation for regulatory sources."""
        miner = MarketMiner()

        mock_item = Mock()
        mock_item.domain = "sebi.gov.in"
        mock_item.title = "SEBI Order"
        mock_item.snippet = "Penalty imposed"

        urgency = miner._calculate_urgency(mock_item, "sebi_order")
        assert urgency == "high"

    def test_calculate_urgency_ed_arrest(self):
        """Test urgency calculation for ED arrests."""
        miner = MarketMiner()

        mock_item = Mock()
        mock_item.domain = "news.com"
        mock_item.title = "ED Arrest in Rs 500 Crore Fraud"
        mock_item.snippet = "Businessman arrested in money laundering case"

        urgency = miner._calculate_urgency(mock_item, "ed_action")
        assert urgency == "critical"

    def test_calculate_urgency_large_amount(self):
        """Test urgency calculation for large amount cases."""
        miner = MarketMiner()

        mock_item = Mock()
        mock_item.domain = "news.com"
        mock_item.title = "Rs 1000 Crore Bank Fraud"
        mock_item.snippet = "Major financial fraud case"

        urgency = miner._calculate_urgency(mock_item, "fraud_case")
        assert urgency == "high"

    @patch("skills.miners.market_miner.SERPAPI_AVAILABLE", False)
    def test_fetch_without_serpapi(self):
        """Test fetch returns empty when SerpAPI unavailable."""
        miner = MarketMiner()
        results = miner.fetch("test market", limit=5)
        assert results == []

    def test_alert_keywords_coverage(self):
        """Test that all alert types have keywords defined."""
        miner = MarketMiner()
        expected_types = [
            "sebi_order",
            "rbi_circular",
            "ed_action",
            "mca_prosecution",
            "investor_warning",
            "fraud_case",
        ]

        for alert_type in expected_types:
            assert alert_type in miner.ALERT_KEYWORDS
            assert len(miner.ALERT_KEYWORDS[alert_type]) > 0


class TestMarketMinerIntegration:
    """Integration tests for MarketMiner (requires SerpAPI)."""

    @pytest.mark.skipif(True, reason="Requires SERPAPI_API_KEY")
    def test_fetch_regulatory_actions_live(self):
        """Test fetching regulatory actions with live API."""
        miner = MarketMiner()
        if not miner.api_key:
            pytest.skip("SERPAPI_API_KEY not set")

        actions = miner.fetch_regulatory_actions(days=30)
        assert isinstance(actions, list)

    @pytest.mark.skipif(True, reason="Requires SERPAPI_API_KEY")
    def test_get_market_alerts_summary_live(self):
        """Test getting market alerts summary with live API."""
        miner = MarketMiner()
        if not miner.api_key:
            pytest.skip("SERPAPI_API_KEY not set")

        summary = miner.get_market_alerts_summary(days=7)
        assert "total_alerts" in summary
        assert "by_type" in summary
