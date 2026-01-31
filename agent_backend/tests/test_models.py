"""
Tests for shared models - TDD First
These tests validate the Pydantic models used across the autonomous newsroom.

Note: Full model tests are in test_adversarial_council.py
This file re-exports the key model tests.
"""

import pytest


class TestCouncilVerdictModel:
    """Tests for CouncilVerdict Pydantic model."""

    def test_council_verdict_publish_decision(self):
        """Test CouncilVerdict model with PUBLISH decision."""
        from shared.models import CouncilVerdict

        verdict = CouncilVerdict(
            decision="PUBLISH",
            confidence=0.85,
            advocate_score=90,
            skeptic_score=75,
            guardian_score=80,
            average_score=81.67,
            dissenting_views=[],
            required_fixes=[],
            kill_reason=None,
            debate_summary="All agents agree this is publishable.",
        )

        assert verdict.decision == "PUBLISH"
        assert verdict.confidence == 0.85
        assert verdict.advocate_score == 90
        assert verdict.average_score == 81.67
        assert verdict.kill_reason is None


class TestAgentViewModel:
    """Tests for AgentView Pydantic model."""

    def test_advocate_agent_view(self):
        """Test AgentView for advocate agent."""
        from shared.models import AgentView

        view = AgentView(
            agent="advocate",
            score=85,
            reasoning="This topic is highly timely and has strong audience demand.",
            key_points=["Breaking news angle", "High search volume"],
            concerns=["Competition may publish first"],
            recommendations=["Prioritize for immediate publish"],
        )

        assert view.agent == "advocate"
        assert view.score == 85
        assert len(view.key_points) == 2


class TestEditorialDirectiveModel:
    """Tests for EditorialDirective model."""

    def test_hunt_breaking_directive(self):
        """Test HUNT_BREAKING directive."""
        from shared.models import EditorialDirective

        directive = EditorialDirective(
            action="HUNT_BREAKING",
            urgency="critical",
            focus_topic="Major data breach at leading bank",
            reason="Breaking news detected with high relevance",
            signals=[{"source": "google_news", "trend": "rising"}],
            confidence=0.9,
        )

        assert directive.action == "HUNT_BREAKING"
        assert directive.urgency == "critical"
        assert directive.confidence == 0.9


class TestLearningModels:
    """Tests for Learning Loop models."""

    def test_article_performance_creation(self):
        """Test ArticlePerformance model."""
        from shared.models import ArticlePerformance

        perf = ArticlePerformance(
            article_slug="test-article-slug",
            views=1500,
            avg_time_seconds=180.5,
            shares=25,
            bounce_rate=0.35,
            scroll_depth=0.75,
            engagement_score=8.5,
        )

        assert perf.article_slug == "test-article-slug"
        assert perf.views == 1500
        assert perf.engagement_score == 8.5


# =============================================================================
# Pipeline Profile Models Tests (TDD)
# =============================================================================


class TestFastTrackConfig:
    """Tests for FastTrackConfig model."""

    def test_fast_track_defaults(self):
        """Test FastTrackConfig has correct defaults."""
        from shared.models import FastTrackConfig

        config = FastTrackConfig()

        assert config.enabled is False
        assert config.bypass_council is False
        assert config.bypass_fact_check is False
        assert config.max_publish_time_seconds == 300

    def test_fast_track_enabled_config(self):
        """Test FastTrackConfig with fast-track enabled."""
        from shared.models import FastTrackConfig

        config = FastTrackConfig(
            enabled=True,
            bypass_council=True,
            bypass_fact_check=True,
            max_publish_time_seconds=180,
        )

        assert config.enabled is True
        assert config.bypass_council is True
        assert config.max_publish_time_seconds == 180


class TestCouncilThresholds:
    """Tests for CouncilThresholds model."""

    def test_council_thresholds_defaults(self):
        """Test CouncilThresholds has correct defaults."""
        from shared.models import CouncilThresholds

        thresholds = CouncilThresholds()

        assert thresholds.require_unanimous is False
        assert thresholds.min_advocate == 70
        assert thresholds.min_skeptic == 60
        assert thresholds.min_guardian == 70

    def test_council_thresholds_research_profile(self):
        """Test CouncilThresholds for research profile (unanimous required)."""
        from shared.models import CouncilThresholds

        thresholds = CouncilThresholds(
            require_unanimous=True,
            min_advocate=75,
            min_skeptic=70,
            min_guardian=75,
        )

        assert thresholds.require_unanimous is True
        assert thresholds.min_advocate == 75


class TestQualityThresholds:
    """Tests for QualityThresholds model."""

    def test_quality_thresholds_defaults(self):
        """Test QualityThresholds has correct defaults."""
        from shared.models import QualityThresholds

        quality = QualityThresholds()

        assert quality.min_score == 60
        assert quality.min_sources == 2
        assert quality.min_citation_density == 0.3
        assert quality.min_regulations == 0

    def test_quality_thresholds_research_profile(self):
        """Test QualityThresholds for research profile (strict requirements)."""
        from shared.models import QualityThresholds

        quality = QualityThresholds(
            min_score=75,
            min_sources=5,
            min_citation_density=0.6,
            min_regulations=2,
        )

        assert quality.min_score == 75
        assert quality.min_sources == 5
        assert quality.min_regulations == 2


class TestRollbackConfig:
    """Tests for RollbackConfig model."""

    def test_rollback_config_defaults(self):
        """Test RollbackConfig has correct defaults."""
        from shared.models import RollbackConfig

        config = RollbackConfig()

        assert config.window_hours == 24
        assert config.auto_retract_on_contradiction is True


class TestDeliberationConfig:
    """Tests for DeliberationConfig model."""

    def test_deliberation_config_defaults(self):
        """Test DeliberationConfig has correct defaults."""
        from shared.models import DeliberationConfig

        config = DeliberationConfig()

        assert config.min_hours == 0

    def test_deliberation_config_views_profile(self):
        """Test DeliberationConfig for views profile (2 hour delay)."""
        from shared.models import DeliberationConfig

        config = DeliberationConfig(min_hours=2)

        assert config.min_hours == 2


class TestPipelineProfile:
    """Tests for PipelineProfile model."""

    def test_pipeline_profile_news_breaking(self):
        """Test PipelineProfile for breaking news fast-track."""
        from shared.models import (
            PipelineProfile,
            FastTrackConfig,
            QualityThresholds,
            RollbackConfig,
        )

        profile = PipelineProfile(
            name="news_breaking",
            applies_to=["News"],
            fast_track=FastTrackConfig(
                enabled=True,
                bypass_council=True,
                bypass_fact_check=True,
                max_publish_time_seconds=300,
            ),
            quality=QualityThresholds(min_score=50, min_sources=1),
            rollback=RollbackConfig(
                window_hours=24, auto_retract_on_contradiction=True
            ),
            label="DEVELOPING",
        )

        assert profile.name == "news_breaking"
        assert "News" in profile.applies_to
        assert profile.fast_track.enabled is True
        assert profile.fast_track.bypass_council is True
        assert profile.label == "DEVELOPING"

    def test_pipeline_profile_views(self):
        """Test PipelineProfile for views/analysis content."""
        from shared.models import (
            PipelineProfile,
            CouncilThresholds,
            QualityThresholds,
            DeliberationConfig,
        )

        profile = PipelineProfile(
            name="views",
            applies_to=["Analysis", "Review"],
            council=CouncilThresholds(min_advocate=70, min_skeptic=60, min_guardian=75),
            quality=QualityThresholds(
                min_score=65, min_sources=4, min_citation_density=0.4
            ),
            deliberation=DeliberationConfig(min_hours=2),
            gates=["opinion_balance", "brand_voice"],
        )

        assert profile.name == "views"
        assert "Analysis" in profile.applies_to
        assert "Review" in profile.applies_to
        assert profile.deliberation.min_hours == 2
        assert "opinion_balance" in profile.gates

    def test_pipeline_profile_research(self):
        """Test PipelineProfile for research/guide content."""
        from shared.models import (
            PipelineProfile,
            CouncilThresholds,
            QualityThresholds,
            DeliberationConfig,
        )

        profile = PipelineProfile(
            name="research",
            applies_to=["Guide"],
            council=CouncilThresholds(
                require_unanimous=True,
                min_advocate=75,
                min_skeptic=70,
                min_guardian=75,
            ),
            quality=QualityThresholds(
                min_score=75,
                min_sources=5,
                min_citation_density=0.6,
                min_regulations=2,
            ),
            deliberation=DeliberationConfig(min_hours=24),
            gates=["expert_citation", "depth_verification"],
        )

        assert profile.name == "research"
        assert profile.council.require_unanimous is True
        assert profile.deliberation.min_hours == 24
        assert "expert_citation" in profile.gates


class TestBreakingAnalysis:
    """Tests for BreakingAnalysis model."""

    def test_breaking_analysis_not_breaking(self):
        """Test BreakingAnalysis for non-breaking content."""
        from shared.models import BreakingAnalysis

        analysis = BreakingAnalysis()

        assert analysis.is_breaking is False
        assert analysis.urgency == "low"
        assert analysis.source_tier is None
        assert analysis.confidence == 0.0

    def test_breaking_analysis_tier_1_source(self):
        """Test BreakingAnalysis for tier 1 government source."""
        from shared.models import BreakingAnalysis

        analysis = BreakingAnalysis(
            is_breaking=True,
            urgency="critical",
            source_tier="tier_1",
            confidence=0.95,
            signals=["government_source", "official_announcement"],
            title_indicators=["BREAKING:"],
            recency_minutes=5,
        )

        assert analysis.is_breaking is True
        assert analysis.urgency == "critical"
        assert analysis.source_tier == "tier_1"
        assert analysis.confidence == 0.95
        assert len(analysis.signals) == 2
        assert analysis.recency_minutes == 5

    def test_breaking_analysis_urgency_validation(self):
        """Test BreakingAnalysis urgency field validation."""
        from shared.models import BreakingAnalysis

        # Test all valid urgency values
        for urgency in ["critical", "high", "medium", "low"]:
            analysis = BreakingAnalysis(urgency=urgency)
            assert analysis.urgency == urgency

    def test_breaking_analysis_confidence_bounds(self):
        """Test BreakingAnalysis confidence is bounded 0-1."""
        from shared.models import BreakingAnalysis
        import pytest

        # Valid confidence
        analysis = BreakingAnalysis(confidence=0.5)
        assert analysis.confidence == 0.5

        # Boundary values
        analysis = BreakingAnalysis(confidence=0.0)
        assert analysis.confidence == 0.0

        analysis = BreakingAnalysis(confidence=1.0)
        assert analysis.confidence == 1.0

        # Invalid confidence should raise validation error
        with pytest.raises(ValueError):
            BreakingAnalysis(confidence=1.5)

        with pytest.raises(ValueError):
            BreakingAnalysis(confidence=-0.1)
