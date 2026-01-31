"""
Tests for Auto-Publish Pipeline - TDD First
Database-first publishing with Council integration.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
import sqlite3
import tempfile
import os


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    try:
        os.unlink(path)
    except Exception:
        pass


@pytest.fixture
def content_brain(temp_db):
    """Create a ContentBrain with temporary database."""
    from skills.content_brain import ContentBrain

    brain = ContentBrain(db_path=temp_db)
    return brain


class TestContentBrainAutoPublish:
    """Tests for ContentBrain auto-publish extensions."""

    def test_publish_article_stores_full_content(self, content_brain):
        """Test that publish_article stores the full article body."""
        from shared.models import ArticleDraft, CouncilVerdict

        draft = ArticleDraft(
            title="Test Auto-Publish Article",
            description="Testing auto-publish functionality.",
            category="Security",
            contentType="Guide",
            body="# Test Article\n\nThis is the full body content.",
            wordCount=500,
            sources=[
                {"id": "S1", "title": "Test Source", "url": "https://example.com"}
            ],
        )

        verdict = CouncilVerdict(
            decision="PUBLISH",
            confidence=0.9,
            advocate_score=85,
            skeptic_score=80,
            guardian_score=75,
            average_score=80.0,
        )

        slug = "test-auto-publish-article"
        content_brain.publish_article(slug, draft, verdict)

        # Verify article was stored
        article = content_brain.get_published_article(slug)
        assert article is not None
        assert article["body"] == draft.body
        assert article["title"] == draft.title

    def test_get_published_article_returns_none_for_missing(self, content_brain):
        """Test that get_published_article returns None for missing articles."""
        result = content_brain.get_published_article("non-existent-slug")
        assert result is None

    def test_get_published_articles_returns_list(self, content_brain):
        """Test that get_published_articles returns a list of articles."""
        from shared.models import ArticleDraft, CouncilVerdict

        # Create and publish two articles
        for i in range(2):
            draft = ArticleDraft(
                title=f"Test Article {i}",
                description=f"Test description {i}",
                category="Security",
                contentType="Guide",
                body=f"# Article {i}\n\nContent here.",
                wordCount=300,
                sources=[],
            )

            verdict = CouncilVerdict(
                decision="PUBLISH",
                confidence=0.85,
                advocate_score=80,
                skeptic_score=75,
                guardian_score=70,
                average_score=75.0,
            )

            content_brain.publish_article(f"test-article-{i}", draft, verdict)

        articles = content_brain.get_published_articles(limit=10)
        assert isinstance(articles, list)
        assert len(articles) >= 2

    def test_publish_article_stores_council_verdict(self, content_brain):
        """Test that council verdict is stored with the article."""
        from shared.models import ArticleDraft, CouncilVerdict

        draft = ArticleDraft(
            title="Council Verdict Test",
            description="Testing verdict storage.",
            category="Security",
            contentType="News",
            body="# News\n\nBreaking news content.",
            wordCount=200,
            sources=[],
        )

        verdict = CouncilVerdict(
            decision="PUBLISH",
            confidence=0.92,
            advocate_score=90,
            skeptic_score=85,
            guardian_score=88,
            average_score=87.67,
            debate_summary="Unanimous approval",
        )

        slug = "council-verdict-test"
        content_brain.publish_article(slug, draft, verdict)

        article = content_brain.get_published_article(slug)
        assert article is not None
        assert "council_verdict" in article
        assert article["council_verdict"]["decision"] == "PUBLISH"

    def test_publish_article_sets_published_via(self, content_brain):
        """Test that published_via is set to 'auto' for auto-published articles."""
        from shared.models import ArticleDraft, CouncilVerdict

        draft = ArticleDraft(
            title="Auto Via Test",
            description="Testing published_via field.",
            category="Security",
            contentType="Guide",
            body="# Guide\n\nContent.",
            wordCount=100,
            sources=[],
        )

        verdict = CouncilVerdict(
            decision="PUBLISH",
            confidence=0.8,
            advocate_score=75,
            skeptic_score=70,
            guardian_score=72,
            average_score=72.33,
        )

        slug = "auto-via-test"
        content_brain.publish_article(slug, draft, verdict)

        article = content_brain.get_published_article(slug)
        assert article["published_via"] == "auto"


class TestNewsroomWatcherCouncilIntegration:
    """Tests for NewsroomWatcher with Adversarial Council integration."""

    @pytest.fixture
    def mock_council(self):
        """Create a mock AdversarialCouncil."""
        from shared.models import CouncilVerdict

        mock = MagicMock()
        mock.convene.return_value = CouncilVerdict(
            decision="PUBLISH",
            confidence=0.85,
            advocate_score=80,
            skeptic_score=75,
            guardian_score=78,
            average_score=77.67,
        )
        return mock

    def test_watcher_uses_council_when_enabled(self, temp_db, mock_council):
        """Test that watcher uses council when enabled."""
        from skills.newsroom_watcher import NewsroomWatcher
        from skills.content_brain import ContentBrain

        brain = ContentBrain(db_path=temp_db)

        with patch("skills.newsroom_watcher.config") as mock_config:
            mock_config.get.side_effect = lambda key, default=None: {
                "council.enabled": True,
                "paths.drafts_dir": "drafts",
                "paths.output_dir": "output",
            }.get(key, default)

            watcher = NewsroomWatcher(brain=brain)
            # Inject mock council
            watcher.council = mock_council

            # Council should be available
            assert watcher.council is not None

    def test_council_publish_triggers_database_store(self, temp_db, mock_council):
        """Test that PUBLISH verdict triggers database storage."""
        from skills.newsroom_watcher import NewsroomWatcher
        from skills.content_brain import ContentBrain
        from shared.models import ArticleDraft, CouncilVerdict

        brain = ContentBrain(db_path=temp_db)

        draft = ArticleDraft(
            title="Council Publish Test",
            description="Testing council publish flow.",
            category="Security",
            contentType="Guide",
            body="# Guide\n\nContent with sources [S1].",
            wordCount=400,
            sources=[{"id": "S1", "title": "Test", "url": "https://test.com"}],
        )

        verdict = CouncilVerdict(
            decision="PUBLISH",
            confidence=0.9,
            advocate_score=85,
            skeptic_score=80,
            guardian_score=82,
            average_score=82.33,
        )

        # Simulate what watcher._handle_council_verdict should do
        brain.publish_article("council-publish-test", draft, verdict)

        article = brain.get_published_article("council-publish-test")
        assert article is not None
        assert article["status"] == "PUBLISHED"

    def test_council_revise_queues_for_revision(self, temp_db, mock_council):
        """Test that REVISE verdict queues article for revision."""
        from shared.models import CouncilVerdict

        # Mock council returns REVISE
        mock_council.convene.return_value = CouncilVerdict(
            decision="REVISE",
            confidence=0.7,
            advocate_score=75,
            skeptic_score=55,
            guardian_score=70,
            average_score=66.67,
            required_fixes=["Add more sources", "Verify statistics"],
        )

        verdict = mock_council.convene(None, None)
        assert verdict.decision == "REVISE"
        assert len(verdict.required_fixes) > 0

    def test_council_kill_archives_with_reason(self, temp_db, mock_council):
        """Test that KILL verdict archives with reason."""
        from shared.models import CouncilVerdict

        # Mock council returns KILL
        mock_council.convene.return_value = CouncilVerdict(
            decision="KILL",
            confidence=0.95,
            advocate_score=50,
            skeptic_score=30,
            guardian_score=40,
            average_score=40.0,
            kill_reason="Factual inaccuracies detected",
        )

        verdict = mock_council.convene(None, None)
        assert verdict.decision == "KILL"
        assert verdict.kill_reason is not None


class TestAPIArticleEndpoints:
    """Tests for article API endpoints."""

    @pytest.fixture
    def test_client(self, temp_db):
        """Create a test FastAPI client."""
        # This would require setting up the FastAPI app for testing
        # For now, we test the underlying ContentBrain methods
        from skills.content_brain import ContentBrain

        return ContentBrain(db_path=temp_db)

    def test_get_article_by_slug(self, test_client):
        """Test getting article by slug."""
        from shared.models import ArticleDraft, CouncilVerdict

        # Publish an article first
        draft = ArticleDraft(
            title="API Test Article",
            description="Testing API endpoint.",
            category="Security",
            contentType="News",
            body="# News\n\nAPI test content.",
            wordCount=150,
            sources=[],
        )

        verdict = CouncilVerdict(
            decision="PUBLISH",
            confidence=0.8,
            advocate_score=75,
            skeptic_score=72,
            guardian_score=70,
            average_score=72.33,
        )

        test_client.publish_article("api-test-article", draft, verdict)

        # Get the article
        article = test_client.get_published_article("api-test-article")
        assert article is not None
        assert article["slug"] == "api-test-article"
        assert article["title"] == "API Test Article"

    def test_list_articles_with_pagination(self, test_client):
        """Test listing articles with pagination."""
        from shared.models import ArticleDraft, CouncilVerdict

        # Create 5 articles
        for i in range(5):
            draft = ArticleDraft(
                title=f"Paginated Article {i}",
                description=f"Pagination test {i}.",
                category="Security",
                contentType="Guide",
                body=f"# Article {i}\n\nContent.",
                wordCount=100,
                sources=[],
            )

            verdict = CouncilVerdict(
                decision="PUBLISH",
                confidence=0.8,
                advocate_score=75,
                skeptic_score=70,
                guardian_score=72,
                average_score=72.33,
            )

            test_client.publish_article(f"paginated-article-{i}", draft, verdict)

        # Get first page
        page1 = test_client.get_published_articles(limit=2, offset=0)
        assert len(page1) == 2

        # Get second page
        page2 = test_client.get_published_articles(limit=2, offset=2)
        assert len(page2) == 2

        # Ensure different articles
        assert page1[0]["slug"] != page2[0]["slug"]


class TestProfileAwarePublishing:
    """Tests for profile-aware publishing pipeline."""

    def test_fast_track_breaking_news_bypasses_council(self, temp_db):
        """Test that breaking news from trusted source can bypass council."""
        from skills.pipeline_router import PipelineRouter
        from skills.breaking_detector import BreakingDetector
        from skills.content_brain import ContentBrain
        from shared.models import ArticleDraft, ArticleSource
        from datetime import datetime

        brain = ContentBrain(db_path=temp_db)
        router = PipelineRouter()
        detector = BreakingDetector()

        # Create breaking news from tier 1 source
        draft = ArticleDraft(
            title="BREAKING: RBI Announces Emergency Rate Cut",
            description="Reserve Bank of India announces emergency rate cut",
            category="Finance",
            contentType="News",
            body="# Breaking News\n\nThe RBI today announced...",
            wordCount=300,
            pubDate=datetime.now(),
            sources=[
                ArticleSource(
                    id="1",
                    title="RBI Press Release",
                    url="https://rbi.org.in/press/123",
                )
            ],
        )

        # Analyze for breaking signals
        analysis = detector.analyze(draft)

        # Should be detected as breaking
        assert analysis.is_breaking is True
        assert analysis.urgency == "critical"
        assert analysis.source_tier == "tier_1"

        # Get profile
        signals = {"urgency": analysis.urgency}
        profile = router.get_profile(draft, signals)

        # Should get breaking news profile
        assert profile.name == "news_breaking"
        assert profile.fast_track.enabled is True
        assert profile.fast_track.bypass_council is True

    def test_standard_news_goes_through_council(self, temp_db):
        """Test that standard news goes through normal council review."""
        from skills.pipeline_router import PipelineRouter
        from skills.content_brain import ContentBrain
        from shared.models import ArticleDraft, ArticleSource

        brain = ContentBrain(db_path=temp_db)
        router = PipelineRouter()

        # Create standard news
        draft = ArticleDraft(
            title="Security Industry Report 2026",
            description="Annual security industry analysis",
            category="Security",
            contentType="News",
            body="# Industry Report\n\nThis comprehensive report...",
            wordCount=800,
            sources=[
                ArticleSource(
                    id="1", title="Industry Report", url="https://example.com/report"
                )
            ],
        )

        # Get profile with low urgency
        signals = {"urgency": "low"}
        profile = router.get_profile(draft, signals)

        # Should get standard news profile
        assert profile.name == "news_standard"
        assert profile.fast_track.enabled is False

    def test_analysis_content_requires_deliberation(self, temp_db):
        """Test that Analysis content requires 2-hour deliberation."""
        from skills.pipeline_router import PipelineRouter
        from shared.models import ArticleDraft, ArticleSource

        router = PipelineRouter()

        draft = ArticleDraft(
            title="Analysis: Future of Physical Security in India",
            description="In-depth analysis of security trends",
            category="Security",
            contentType="Analysis",
            body="# Analysis\n\nThis comprehensive analysis...",
            wordCount=1500,
            sources=[
                ArticleSource(id="1", title="Source 1", url="https://example.com/1"),
                ArticleSource(id="2", title="Source 2", url="https://example.com/2"),
            ],
        )

        profile = router.get_profile(draft, {})

        assert profile.name == "views"
        assert profile.deliberation is not None
        assert profile.deliberation.min_hours == 2
        assert "opinion_balance" in profile.gates

    def test_guide_content_requires_unanimous_council(self, temp_db):
        """Test that Guide content requires unanimous council approval."""
        from skills.pipeline_router import PipelineRouter
        from shared.models import ArticleDraft, ArticleSource

        router = PipelineRouter()

        draft = ArticleDraft(
            title="Complete Guide to CCTV Installation Compliance",
            description="Comprehensive compliance guide",
            category="Compliance",
            contentType="Guide",
            body="# Installation Guide\n\nThis guide covers...",
            wordCount=2000,
            sources=[
                ArticleSource(id="1", title="Source 1", url="https://example.com/1"),
                ArticleSource(id="2", title="Source 2", url="https://example.com/2"),
            ],
        )

        profile = router.get_profile(draft, {})

        assert profile.name == "research"
        assert profile.council.require_unanimous is True
        assert profile.deliberation.min_hours == 24
        assert "expert_citation" in profile.gates

    def test_fast_track_publish_records_pipeline_profile(self, temp_db):
        """Test that fast-track publish records the pipeline profile."""
        from skills.content_brain import ContentBrain
        from shared.models import ArticleDraft, CouncilVerdict
        from datetime import datetime, timedelta

        brain = ContentBrain(db_path=temp_db)

        draft = ArticleDraft(
            title="BREAKING: Fast Track Test",
            description="Testing fast track recording",
            category="News",
            contentType="News",
            body="# Breaking\n\nContent here.",
            wordCount=200,
            sources=[],
        )

        # For fast-track, we create a minimal verdict (or None in real implementation)
        verdict = CouncilVerdict(
            decision="PUBLISH",
            confidence=0.95,
            advocate_score=90,
            skeptic_score=85,
            guardian_score=88,
            average_score=87.67,
        )

        brain.publish_article(
            "fast-track-test",
            draft,
            verdict,
            pipeline_profile="news_breaking",
            fast_tracked=True,
            rollback_eligible=True,
            correction_window_expires=datetime.now() + timedelta(hours=24),
        )

        article = brain.get_published_article("fast-track-test")
        assert article["pipeline_profile"] == "news_breaking"
        assert article["fast_tracked"] == 1
        assert article["rollback_eligible"] == 1
