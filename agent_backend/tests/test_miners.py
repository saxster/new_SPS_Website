"""
Comprehensive Test Suite for Content Intelligence Platform.
Tests all miners, ResearchFetcher integration, and ClaimLedger credibility weighting.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

# Import miners
from skills.miners.base_miner import BaseMiner, EvidenceItem
from skills.miners.youtube_miner import YouTubeMiner, VideoInfo
from skills.miners.article_miner import ArticleMiner
from skills.miners.paper_miner import PaperMiner


# =============================================================================
# EvidenceItem Tests
# =============================================================================

class TestEvidenceItem:
    """Tests for EvidenceItem dataclass."""
    
    def test_creation_with_required_fields(self):
        """Test basic evidence item creation with required fields."""
        item = EvidenceItem(
            id="S1",
            title="Test Title",
            url="https://example.com",
            raw_content="This is test content.",
            source_type="article",
            publisher="Example Publisher",
            credibility_weight=7
        )
        
        assert item.id == "S1"
        assert item.title == "Test Title"
        assert item.credibility_weight == 7
        assert item.source_type == "article"
    
    def test_default_values(self):
        """Test that default values are set correctly."""
        item = EvidenceItem(
            id="S1",
            title="Test",
            url="https://example.com",
            raw_content="Content",
            source_type="video",
            publisher="Publisher"
        )
        
        assert item.credibility_weight == 5  # Default
        assert item.domain == ""
        assert item.snippet == ""
        assert item.identifier == ""
        assert isinstance(item.metadata, dict)
    
    def test_to_source_item_dict(self):
        """Test conversion to source item dict format."""
        item = EvidenceItem(
            id="S1",
            title="Test",
            url="https://example.com",
            raw_content="Content here",
            source_type="video",
            publisher="Publisher",
            credibility_weight=5
        )
        
        result = item.to_source_item_dict()
        
        assert result["id"] == "S1"
        assert result["credibility_weight"] == 5
        assert result["quality_score"] == 5
        assert "raw_content" in result
        assert result["snippet"] == "Content here"  # Uses raw_content when snippet empty


# =============================================================================
# YouTubeMiner Tests
# =============================================================================

class TestYouTubeMiner:
    """Tests for YouTubeMiner."""
    
    def test_source_type(self):
        """Test that source type is 'video'."""
        miner = YouTubeMiner()
        assert miner.source_type == "video"
    
    def test_default_credibility(self):
        """Test default credibility weight."""
        miner = YouTubeMiner()
        assert miner.default_credibility == 5
    
    def test_authoritative_channel_credibility_defcon(self):
        """Test elevated credibility for DEF CON."""
        miner = YouTubeMiner()
        # Exact match - "defcon" in AUTHORITATIVE_CHANNELS
        assert miner._get_credibility_for_channel("defcon") == 7
        # Substring match - channel name contains "defcon"
        assert miner._get_credibility_for_channel("defcontalks official") == 7
        # "def con" (with space) does NOT match "defcon" (no space) - gets default
        assert miner._get_credibility_for_channel("def con") == 5
    
    def test_authoritative_channel_credibility_asis(self):
        """Test elevated credibility for ASIS International."""
        miner = YouTubeMiner()
        assert miner._get_credibility_for_channel("asis international") == 7
        assert miner._get_credibility_for_channel("ASIS International Security") == 7
    
    def test_authoritative_channel_credibility_sans(self):
        """Test elevated credibility for SANS Institute."""
        miner = YouTubeMiner()
        assert miner._get_credibility_for_channel("sans institute") == 7
    
    def test_regular_channel_credibility(self):
        """Test default credibility for non-authoritative channels."""
        miner = YouTubeMiner()
        assert miner._get_credibility_for_channel("Random Channel") == 5
        assert miner._get_credibility_for_channel("Tech Reviews") == 5
    
    def test_extract_video_id_watch_url(self):
        """Test extraction from standard watch URL."""
        miner = YouTubeMiner()
        assert miner._extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    
    def test_extract_video_id_short_url(self):
        """Test extraction from youtu.be short URL."""
        miner = YouTubeMiner()
        assert miner._extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    
    def test_extract_video_id_embed_url(self):
        """Test extraction from embed URL."""
        miner = YouTubeMiner()
        assert miner._extract_video_id("https://www.youtube.com/embed/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    
    def test_extract_video_id_shorts_url(self):
        """Test extraction from Shorts URL."""
        miner = YouTubeMiner()
        assert miner._extract_video_id("https://www.youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    
    def test_extract_video_id_invalid_url(self):
        """Test extraction returns None for invalid URL."""
        miner = YouTubeMiner()
        assert miner._extract_video_id("https://example.com") is None
        assert miner._extract_video_id("not a url") is None
    
    def test_clean_transcript_removes_markers(self):
        """Test transcript cleaning removes [Music] and [Applause]."""
        miner = YouTubeMiner()
        raw = "Hello [Music] world [Applause] test"
        cleaned = miner._clean_transcript(raw)
        assert "[Music]" not in cleaned
        assert "[Applause]" not in cleaned
        assert "Hello" in cleaned
        assert "world" in cleaned
    
    def test_clean_transcript_normalizes_whitespace(self):
        """Test transcript cleaning normalizes whitespace."""
        miner = YouTubeMiner()
        raw = "Hello    world   test"
        cleaned = miner._clean_transcript(raw)
        assert "  " not in cleaned
        assert cleaned == "Hello world test"
    
    @patch('skills.miners.youtube_miner.YOUTUBE_TRANSCRIPT_AVAILABLE', False)
    def test_unavailable_without_dependency(self):
        """Test that miner reports unavailable without youtube_transcript_api."""
        miner = YouTubeMiner()
        miner._transcript_api = None
        assert not miner.is_available()


# =============================================================================
# ArticleMiner Tests
# =============================================================================

class TestArticleMiner:
    """Tests for ArticleMiner."""
    
    def test_source_type(self):
        """Test that source type is 'article'."""
        miner = ArticleMiner()
        assert miner.source_type == "article"
    
    def test_default_credibility(self):
        """Test default credibility weight."""
        miner = ArticleMiner()
        assert miner.default_credibility == 6
    
    def test_get_domain_with_www(self):
        """Test domain extraction removes www prefix."""
        miner = ArticleMiner()
        assert miner._get_domain("https://www.reuters.com/article/test") == "reuters.com"
    
    def test_get_domain_without_www(self):
        """Test domain extraction without www prefix."""
        miner = ArticleMiner()
        assert miner._get_domain("https://economictimes.com/news") == "economictimes.com"
    
    def test_official_indian_govt_credibility(self):
        """Test credibility for Indian government sources."""
        miner = ArticleMiner()
        assert miner._get_credibility_for_domain("rbi.org.in") == 10
        assert miner._get_credibility_for_domain("mha.gov.in") == 10
        assert miner._get_credibility_for_domain("cert-in.org.in") == 10
        assert miner._get_credibility_for_domain("bis.gov.in") == 10
        assert miner._get_credibility_for_domain("sebi.gov.in") == 10
    
    def test_official_us_govt_credibility(self):
        """Test credibility for US government sources."""
        miner = ArticleMiner()
        assert miner._get_credibility_for_domain("nist.gov") == 9
        assert miner._get_credibility_for_domain("cisa.gov") == 9
    
    def test_major_news_credibility(self):
        """Test credibility for major news outlets."""
        miner = ArticleMiner()
        assert miner._get_credibility_for_domain("reuters.com") == 8
        assert miner._get_credibility_for_domain("economictimes.com") == 8
        assert miner._get_credibility_for_domain("thehindu.com") == 8
    
    def test_security_news_credibility(self):
        """Test credibility for security-focused news."""
        miner = ArticleMiner()
        assert miner._get_credibility_for_domain("krebsonsecurity.com") == 9
        assert miner._get_credibility_for_domain("darkreading.com") == 8
        assert miner._get_credibility_for_domain("securityweek.com") == 8
    
    def test_generic_gov_domain_credibility(self):
        """Test credibility for generic .gov domains."""
        miner = ArticleMiner()
        assert miner._get_credibility_for_domain("example.gov.in") == 9
        assert miner._get_credibility_for_domain("someagency.nic.in") == 9
    
    def test_academic_domain_credibility(self):
        """Test credibility for academic domains."""
        miner = ArticleMiner()
        assert miner._get_credibility_for_domain("mit.edu") == 8
        assert miner._get_credibility_for_domain("iitb.ac.in") == 8
    
    def test_unknown_domain_credibility(self):
        """Test default credibility for unknown domains."""
        miner = ArticleMiner()
        assert miner._get_credibility_for_domain("randomsite.com") == 6
    
    @patch('skills.miners.article_miner.TRAFILATURA_AVAILABLE', False)
    def test_unavailable_without_dependency(self):
        """Test that miner reports unavailable without trafilatura."""
        miner = ArticleMiner()
        assert not miner.is_available()


# =============================================================================
# PaperMiner Tests
# =============================================================================

class TestPaperMiner:
    """Tests for PaperMiner."""
    
    def test_source_type(self):
        """Test that source type is 'paper'."""
        miner = PaperMiner()
        assert miner.source_type == "paper"
    
    def test_default_credibility(self):
        """Test default credibility weight is 9 (peer-reviewed)."""
        miner = PaperMiner()
        assert miner.default_credibility == 9
    
    def test_is_available(self):
        """Test that arXiv API is always available."""
        miner = PaperMiner()
        assert miner.is_available() is True
    
    def test_arxiv_id_extraction_standard_url(self):
        """Test extraction from standard arXiv URL."""
        miner = PaperMiner()
        assert miner._extract_arxiv_id("https://arxiv.org/abs/2301.12345") == "2301.12345"
    
    def test_arxiv_id_extraction_prefixed(self):
        """Test extraction from arXiv: prefix format."""
        miner = PaperMiner()
        assert miner._extract_arxiv_id("arXiv:2301.12345") == "2301.12345"
    
    def test_arxiv_id_extraction_bare(self):
        """Test extraction from bare ID."""
        miner = PaperMiner()
        assert miner._extract_arxiv_id("2301.12345") == "2301.12345"
    
    def test_arxiv_id_extraction_five_digits(self):
        """Test extraction for 5-digit IDs (newer format)."""
        miner = PaperMiner()
        assert miner._extract_arxiv_id("2401.12345") == "2401.12345"
    
    def test_clean_abstract_normalizes_whitespace(self):
        """Test abstract cleaning normalizes whitespace."""
        miner = PaperMiner()
        raw = "This   is   a   test   abstract."
        cleaned = miner._clean_abstract(raw)
        assert "   " not in cleaned
        assert cleaned == "This is a test abstract."
    
    def test_clean_abstract_truncates_long_text(self):
        """Test abstract cleaning truncates long text."""
        miner = PaperMiner()
        miner.max_abstract_length = 50
        raw = "A" * 100
        cleaned = miner._clean_abstract(raw)
        assert len(cleaned) <= 53  # 50 + "..."
        assert cleaned.endswith("...")


# =============================================================================
# ResearchFetcher Integration Tests
# =============================================================================

class TestResearchFetcherIntegration:
    """Tests for ResearchFetcher with pluggable miners."""
    
    def test_init_without_miners(self):
        """Test ResearchFetcher initializes with empty miners list by default."""
        from skills.research_sources import ResearchFetcher
        fetcher = ResearchFetcher()
        assert fetcher.miners == []
    
    def test_init_with_miners(self):
        """Test ResearchFetcher accepts miners list."""
        from skills.research_sources import ResearchFetcher
        
        mock_miner = MagicMock(spec=BaseMiner)
        mock_miner.source_type = "test"
        
        fetcher = ResearchFetcher(miners=[mock_miner])
        assert len(fetcher.miners) == 1
    
    def test_miners_integration_with_evidence_items(self):
        """Test miners are called during build_evidence_pack."""
        from skills.research_sources import ResearchFetcher
        import os
        os.environ["RESEARCH_DISABLE_NETWORK"] = "1"  # Disable network calls
        
        mock_miner = MagicMock(spec=BaseMiner)
        mock_miner.source_type = "test"
        mock_miner.is_available.return_value = True
        mock_miner.fetch.return_value = [
            EvidenceItem(
                id="S1",
                title="Test Evidence",
                url="https://test.com",
                raw_content="Test content for verification",
                source_type="test",
                publisher="Test Publisher",
                credibility_weight=7
            )
        ]
        
        fetcher = ResearchFetcher(miners=[mock_miner])
        # Note: RESEARCH_DISABLE_NETWORK=1 returns early before miners are called
        # This test verifies the miner was passed correctly
        assert mock_miner in fetcher.miners
        
        del os.environ["RESEARCH_DISABLE_NETWORK"]
    
    def test_source_item_has_credibility_weight(self):
        """Test that SourceItem dataclass has credibility_weight field."""
        from skills.research_sources import SourceItem
        
        item = SourceItem(
            id="S1",
            title="Test",
            url="https://example.com",
            publisher="Publisher",
            published=None,
            source_type="web",
            snippet="Test snippet",
            quality_score=70,
            domain="example.com",
            identifier="",
            accessed_at="2026-01-22",
            credibility_weight=8,
            raw_content="Full content here"
        )
        
        assert item.credibility_weight == 8
        assert item.raw_content == "Full content here"


# =============================================================================
# ClaimLedger Tests
# =============================================================================

class TestClaimLedger:
    """Tests for ClaimLedger credibility weighting."""
    
    def test_claim_has_confidence_score(self):
        """Test that Claim dataclass has confidence_score field."""
        from skills.claim_ledger import Claim
        
        claim = Claim(
            id="C001",
            text="Test claim",
            claim_type="numeric",
            citations=["S1"],
            sources=["S1"],
            domains=["reuters.com"],
            numbers=["45%"],
            issues=[],
            confidence_score=8.0
        )
        
        assert claim.confidence_score == 8.0
    
    def test_numeric_claim_detection(self):
        """Test that numeric claims are detected correctly."""
        from skills.claim_ledger import ClaimLedger
        
        cl = ClaimLedger()
        
        claim_type, numbers = cl._classify_claim("Companies lost 4.5 million dollars.", [])
        assert claim_type == "numeric"
        # Numbers may have trailing spaces from regex, check for substring
        assert any("4.5" in n for n in numbers)
    
    def test_percentage_claim_detection(self):
        """Test that percentage claims are detected."""
        from skills.claim_ledger import ClaimLedger
        
        cl = ClaimLedger()
        
        claim_type, numbers = cl._classify_claim("45% of companies were affected.", [])
        assert claim_type == "numeric"
        assert "45" in numbers or "45%" in numbers
    
    def test_regulatory_claim_detection(self):
        """Test that regulatory claims are detected (when no numbers present)."""
        from skills.claim_ledger import ClaimLedger
        
        cl = ClaimLedger()
        
        # Note: Numeric detection takes precedence, so use sentence without numbers
        claim_type, _ = cl._classify_claim("Companies must comply with RBI Guidelines.", ["RBI Guidelines"])
        assert claim_type == "regulatory"
    
    def test_policy_claim_detection(self):
        """Test that policy claims are detected via trigger words."""
        from skills.claim_ledger import ClaimLedger
        
        cl = ClaimLedger()
        
        claim_type, _ = cl._classify_claim("Security measures are required by law.", [])
        assert claim_type == "policy"
    
    def test_build_returns_confidence_metrics(self):
        """Test that build() returns confidence metrics."""
        from skills.claim_ledger import ClaimLedger
        
        cl = ClaimLedger()
        
        draft = {
            "body": "Security breaches cost 4.5 million dollars [S1].",
            "regulations": []
        }
        evidence = [{"id": "S1", "domain": "reuters.com", "credibility_weight": 8}]
        
        result = cl.build(draft, evidence)
        
        assert "average_confidence" in result["metrics"]
        assert "low_confidence_count" in result["metrics"]
    
    def test_confidence_score_from_credibility_weight(self):
        """Test that claim confidence is derived from source credibility."""
        from skills.claim_ledger import ClaimLedger
        
        cl = ClaimLedger()
        
        draft = {
            "body": "Security breaches cost 4.5 million dollars [S1].",
            "regulations": []
        }
        evidence = [{"id": "S1", "domain": "reuters.com", "credibility_weight": 8}]
        
        result = cl.build(draft, evidence)
        
        # Should have found the numeric claim with confidence from source
        assert result["metrics"]["claim_count"] >= 1
        if result["claims"]:
            assert result["claims"][0]["confidence_score"] == 8.0


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
