"""
Tests for PipelineRouter - Routes content to appropriate pipeline profiles.
TDD First - Tests written before implementation.
"""

import pytest


class TestPipelineRouterInit:
    """Tests for PipelineRouter initialization."""

    def test_pipeline_router_loads_profiles_from_config(self):
        """Test that PipelineRouter loads profiles from settings.yaml."""
        from skills.pipeline_router import PipelineRouter

        router = PipelineRouter()

        # Should have loaded all 4 profiles
        assert "news_breaking" in router.profiles
        assert "news_standard" in router.profiles
        assert "views" in router.profiles
        assert "research" in router.profiles

    def test_pipeline_router_loads_trusted_sources(self):
        """Test that PipelineRouter loads trusted sources from config."""
        from skills.pipeline_router import PipelineRouter

        router = PipelineRouter()

        # Should have loaded trusted sources by tier
        assert "tier_1" in router.trusted_sources
        assert "tier_2" in router.trusted_sources
        assert "tier_3" in router.trusted_sources

        # Verify specific sources
        assert "pib.gov.in" in router.trusted_sources["tier_1"]
        assert "reuters.com" in router.trusted_sources["tier_2"]


class TestSourceTierDetection:
    """Tests for source tier detection."""

    def test_get_source_tier_tier_1_government(self):
        """Test detection of tier 1 government sources."""
        from skills.pipeline_router import PipelineRouter

        router = PipelineRouter()

        # PIB is tier 1
        assert (
            router.get_source_tier("https://pib.gov.in/press-release/123") == "tier_1"
        )
        # RBI is tier 1
        assert router.get_source_tier("https://rbi.org.in/announcement") == "tier_1"
        # CERT-IN is tier 1
        assert router.get_source_tier("https://cert-in.org.in/advisory") == "tier_1"

    def test_get_source_tier_tier_2_wire_services(self):
        """Test detection of tier 2 wire services."""
        from skills.pipeline_router import PipelineRouter

        router = PipelineRouter()

        # Reuters is tier 2
        assert (
            router.get_source_tier("https://reuters.com/world/india/breaking")
            == "tier_2"
        )
        # AP News is tier 2
        assert (
            router.get_source_tier("https://apnews.com/article/india-security")
            == "tier_2"
        )
        # PTI is tier 2
        assert router.get_source_tier("https://pti.in/story/123") == "tier_2"

    def test_get_source_tier_tier_3_trusted_media(self):
        """Test detection of tier 3 trusted media sources."""
        from skills.pipeline_router import PipelineRouter

        router = PipelineRouter()

        # Economic Times is tier 3
        assert (
            router.get_source_tier("https://economictimes.indiatimes.com/news/123")
            == "tier_3"
        )
        # The Hindu is tier 3
        assert (
            router.get_source_tier("https://thehindu.com/news/national/article123")
            == "tier_3"
        )

    def test_get_source_tier_unknown_source(self):
        """Test that unknown sources return None."""
        from skills.pipeline_router import PipelineRouter

        router = PipelineRouter()

        # Unknown blog
        assert router.get_source_tier("https://random-blog.com/post/123") is None
        # Social media
        assert router.get_source_tier("https://twitter.com/user/status/123") is None


class TestProfileRouting:
    """Tests for profile routing based on content type and signals."""

    def test_get_profile_news_breaking_critical_tier_1(self):
        """Test routing breaking news from tier 1 source to fast-track."""
        from skills.pipeline_router import PipelineRouter
        from shared.models import ArticleDraft, ArticleSource

        router = PipelineRouter()

        draft = ArticleDraft(
            title="RBI Announces Major Policy Change",
            description="Reserve Bank of India announces key policy decision",
            category="Finance",
            contentType="News",
            body="# RBI Policy\n\nThe Reserve Bank of India today announced...",
            wordCount=500,
            sources=[
                ArticleSource(
                    id="1",
                    title="RBI Press Release",
                    url="https://rbi.org.in/press/123",
                )
            ],
        )

        signals = {"urgency": "critical"}

        profile = router.get_profile(draft, signals)

        assert profile.name == "news_breaking"
        assert profile.fast_track.enabled is True

    def test_get_profile_news_breaking_high_tier_2(self):
        """Test routing breaking news from tier 2 source to fast-track."""
        from skills.pipeline_router import PipelineRouter
        from shared.models import ArticleDraft, ArticleSource

        router = PipelineRouter()

        draft = ArticleDraft(
            title="BREAKING: Major Security Incident Reported",
            description="Breaking news about security incident",
            category="Security",
            contentType="News",
            body="# Breaking News\n\nReuters reports that...",
            wordCount=400,
            sources=[
                ArticleSource(
                    id="1", title="Reuters", url="https://reuters.com/article/123"
                )
            ],
        )

        signals = {"urgency": "high"}

        profile = router.get_profile(draft, signals)

        assert profile.name == "news_breaking"
        assert profile.fast_track.enabled is True

    def test_get_profile_news_standard_low_urgency(self):
        """Test routing standard news to normal pipeline."""
        from skills.pipeline_router import PipelineRouter
        from shared.models import ArticleDraft, ArticleSource

        router = PipelineRouter()

        draft = ArticleDraft(
            title="Security Industry Trends Report",
            description="Analysis of current trends",
            category="Security",
            contentType="News",
            body="# Industry Trends\n\nThe security industry...",
            wordCount=600,
            sources=[
                ArticleSource(
                    id="1", title="Industry Report", url="https://example.com/report"
                )
            ],
        )

        signals = {"urgency": "low"}

        profile = router.get_profile(draft, signals)

        assert profile.name == "news_standard"
        assert profile.fast_track.enabled is False

    def test_get_profile_news_untrusted_source_not_fast_tracked(self):
        """Test that news from untrusted sources is not fast-tracked."""
        from skills.pipeline_router import PipelineRouter
        from shared.models import ArticleDraft, ArticleSource

        router = PipelineRouter()

        draft = ArticleDraft(
            title="BREAKING: Unverified Report",
            description="Breaking news from unknown source",
            category="Security",
            contentType="News",
            body="# Breaking\n\nSome unknown blog reports...",
            wordCount=400,
            sources=[
                ArticleSource(
                    id="1", title="Unknown Blog", url="https://random-blog.com/breaking"
                )
            ],
        )

        signals = {"urgency": "critical"}

        profile = router.get_profile(draft, signals)

        # Should fall back to standard news, not breaking
        assert profile.name == "news_standard"
        assert profile.fast_track.enabled is False

    def test_get_profile_analysis_routes_to_views(self):
        """Test routing Analysis content to views profile."""
        from skills.pipeline_router import PipelineRouter
        from shared.models import ArticleDraft, ArticleSource

        router = PipelineRouter()

        draft = ArticleDraft(
            title="Analysis: Future of Physical Security",
            description="In-depth analysis of security trends",
            category="Security",
            contentType="Analysis",
            body="# Analysis\n\nIn this analysis, we examine...",
            wordCount=1500,
            sources=[
                ArticleSource(id="1", title="Source 1", url="https://example.com/1"),
                ArticleSource(id="2", title="Source 2", url="https://example.com/2"),
            ],
        )

        signals = {}

        profile = router.get_profile(draft, signals)

        assert profile.name == "views"
        assert profile.deliberation is not None
        assert profile.deliberation.min_hours == 2
        assert "opinion_balance" in profile.gates

    def test_get_profile_review_routes_to_views(self):
        """Test routing Review content to views profile."""
        from skills.pipeline_router import PipelineRouter
        from shared.models import ArticleDraft, ArticleSource

        router = PipelineRouter()

        draft = ArticleDraft(
            title="Review: Latest Access Control System",
            description="Product review and analysis",
            category="Technology",
            contentType="Review",
            body="# Review\n\nWe tested the latest...",
            wordCount=1200,
            sources=[
                ArticleSource(
                    id="1", title="Product Page", url="https://example.com/product"
                )
            ],
        )

        signals = {}

        profile = router.get_profile(draft, signals)

        assert profile.name == "views"

    def test_get_profile_guide_routes_to_research(self):
        """Test routing Guide content to research profile."""
        from skills.pipeline_router import PipelineRouter
        from shared.models import ArticleDraft, ArticleSource

        router = PipelineRouter()

        draft = ArticleDraft(
            title="Complete Guide to CCTV Installation",
            description="Comprehensive guide for security professionals",
            category="Security",
            contentType="Guide",
            body="# Installation Guide\n\nThis comprehensive guide covers...",
            wordCount=2000,
            sources=[
                ArticleSource(id="1", title="Source 1", url="https://example.com/1"),
                ArticleSource(id="2", title="Source 2", url="https://example.com/2"),
            ],
        )

        signals = {}

        profile = router.get_profile(draft, signals)

        assert profile.name == "research"
        assert profile.council.require_unanimous is True
        assert profile.deliberation.min_hours == 24
        assert "expert_citation" in profile.gates

    def test_get_profile_general_defaults_to_news_standard(self):
        """Test that General content defaults to news_standard profile."""
        from skills.pipeline_router import PipelineRouter
        from shared.models import ArticleDraft, ArticleSource

        router = PipelineRouter()

        draft = ArticleDraft(
            title="General Article",
            description="A general article",
            category="Security",
            contentType="General",
            body="# Article\n\nContent here...",
            wordCount=800,
            sources=[ArticleSource(id="1", title="Source", url="https://example.com")],
        )

        signals = {}

        profile = router.get_profile(draft, signals)

        assert profile.name == "news_standard"


class TestProfileSelection:
    """Tests for profile matching logic."""

    def test_applies_to_content_type_matching(self):
        """Test that profiles correctly match content types."""
        from skills.pipeline_router import PipelineRouter

        router = PipelineRouter()

        # News types should match news profiles
        assert router._content_type_matches_profile(
            "News", router.profiles["news_breaking"]
        )
        assert router._content_type_matches_profile(
            "News", router.profiles["news_standard"]
        )

        # Analysis should match views
        assert router._content_type_matches_profile(
            "Analysis", router.profiles["views"]
        )

        # Guide should match research
        assert router._content_type_matches_profile(
            "Guide", router.profiles["research"]
        )

    def test_breaking_trigger_requires_both_urgency_and_source(self):
        """Test that breaking news requires both high urgency and trusted source."""
        from skills.pipeline_router import PipelineRouter
        from shared.models import ArticleDraft, ArticleSource

        router = PipelineRouter()

        # High urgency but untrusted source - should NOT trigger breaking
        draft = ArticleDraft(
            title="Breaking News",
            description="Test",
            category="News",
            contentType="News",
            body="Content",
            wordCount=300,
            sources=[
                ArticleSource(id="1", title="Blog", url="https://random-blog.com/post")
            ],
        )
        signals = {"urgency": "critical"}

        profile = router.get_profile(draft, signals)
        assert profile.name == "news_standard"

        # Trusted source but low urgency - should NOT trigger breaking
        draft2 = ArticleDraft(
            title="Standard News",
            description="Test",
            category="News",
            contentType="News",
            body="Content",
            wordCount=300,
            sources=[
                ArticleSource(id="1", title="PIB", url="https://pib.gov.in/release")
            ],
        )
        signals2 = {"urgency": "low"}

        profile2 = router.get_profile(draft2, signals2)
        assert profile2.name == "news_standard"
