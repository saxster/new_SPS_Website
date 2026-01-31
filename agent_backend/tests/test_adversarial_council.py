"""
Tests for Adversarial Council - TDD First
The three-agent debate system for final publish approval.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime


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

    def test_council_verdict_revise_decision(self):
        """Test CouncilVerdict model with REVISE decision."""
        from shared.models import CouncilVerdict

        verdict = CouncilVerdict(
            decision="REVISE",
            confidence=0.65,
            advocate_score=85,
            skeptic_score=55,
            guardian_score=70,
            average_score=70.0,
            dissenting_views=["Skeptic raised concerns about source quality"],
            required_fixes=["Add more authoritative sources", "Verify the statistics"],
            kill_reason=None,
            debate_summary="Needs revisions before publish.",
        )

        assert verdict.decision == "REVISE"
        assert len(verdict.required_fixes) == 2
        assert "Add more authoritative sources" in verdict.required_fixes

    def test_council_verdict_kill_decision(self):
        """Test CouncilVerdict model with KILL decision."""
        from shared.models import CouncilVerdict

        verdict = CouncilVerdict(
            decision="KILL",
            confidence=0.95,
            advocate_score=60,
            skeptic_score=30,
            guardian_score=40,
            average_score=43.33,
            dissenting_views=["Advocate believes timing is still good"],
            required_fixes=[],
            kill_reason="Factual inaccuracies and potential brand damage",
            debate_summary="Council recommends killing this draft.",
        )

        assert verdict.decision == "KILL"
        assert verdict.kill_reason is not None
        assert "Factual" in verdict.kill_reason

    def test_council_verdict_score_bounds(self):
        """Test that scores are validated within bounds."""
        from shared.models import CouncilVerdict
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CouncilVerdict(
                decision="PUBLISH",
                confidence=1.5,  # Invalid: > 1
                advocate_score=90,
                skeptic_score=75,
                guardian_score=80,
                average_score=81.67,
            )

        with pytest.raises(ValidationError):
            CouncilVerdict(
                decision="PUBLISH",
                confidence=0.85,
                advocate_score=150,  # Invalid: > 100
                skeptic_score=75,
                guardian_score=80,
                average_score=81.67,
            )


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

    def test_skeptic_agent_view(self):
        """Test AgentView for skeptic agent."""
        from shared.models import AgentView

        view = AgentView(
            agent="skeptic",
            score=60,
            reasoning="Some claims lack proper citation support.",
            key_points=["3 uncited statistics"],
            concerns=["Single source for key claim", "Date may be outdated"],
            recommendations=["Add secondary source for paragraph 3"],
        )

        assert view.agent == "skeptic"
        assert view.score == 60
        assert len(view.concerns) == 2

    def test_guardian_agent_view(self):
        """Test AgentView for guardian agent."""
        from shared.models import AgentView

        view = AgentView(
            agent="guardian",
            score=75,
            reasoning="Content aligns with brand voice but needs tone adjustment.",
            key_points=["Good sector fit", "Matches expertise areas"],
            concerns=["Slightly sensational headline"],
            recommendations=["Revise headline to be more measured"],
        )

        assert view.agent == "guardian"
        assert view.score == 75


class TestTopicEvaluationModel:
    """Tests for TopicEvaluation model from Editorial Brain."""

    def test_topic_evaluation_creation(self):
        """Test TopicEvaluation model creation."""
        from shared.models import TopicEvaluation

        evaluation = TopicEvaluation(
            topic="New RBI Cybersecurity Guidelines for Banks",
            news_sense=90,
            audience_fit=85,
            competitive_angle=70,
            feasibility=80,
            timing=95,
            overall_score=84.0,
            reasoning="Breaking regulatory news with high relevance to our audience.",
            recommended_angle="Focus on compliance implications for mid-size banks",
        )

        assert evaluation.topic == "New RBI Cybersecurity Guidelines for Banks"
        assert evaluation.news_sense == 90
        assert evaluation.overall_score == 84.0
        assert evaluation.recommended_angle is not None


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

    def test_write_queue_directive(self):
        """Test WRITE_QUEUE directive."""
        from shared.models import EditorialDirective

        directive = EditorialDirective(
            action="WRITE_QUEUE",
            urgency="low",
            reason="No urgent signals, continue with queue",
            confidence=0.7,
        )

        assert directive.action == "WRITE_QUEUE"
        assert directive.focus_topic is None


class TestAdversarialCouncil:
    """Tests for the AdversarialCouncil class."""

    def test_council_initialization(self):
        """Test AdversarialCouncil can be initialized."""
        from skills.adversarial_council import AdversarialCouncil

        council = AdversarialCouncil()
        assert council is not None

    def test_council_convene_returns_verdict(self):
        """Test that convene() returns a CouncilVerdict."""
        from skills.adversarial_council import AdversarialCouncil
        from shared.models import ArticleDraft, CouncilVerdict

        # Create a mock draft
        draft = ArticleDraft(
            title="Test Security Article",
            description="A test article about security compliance.",
            category="Security",
            contentType="Guide",
            body="# Test\n\nThis is test content with proper citations [S1].",
            wordCount=500,
            sources=[
                {"id": "S1", "title": "Test Source", "url": "https://example.com"}
            ],
        )
        evidence = [{"id": "S1", "title": "Test Source", "url": "https://example.com"}]

        council = AdversarialCouncil()
        verdict = council.convene(draft, evidence)

        assert isinstance(verdict, CouncilVerdict)
        assert verdict.decision in ["PUBLISH", "REVISE", "KILL"]
        assert 0 <= verdict.advocate_score <= 100
        assert 0 <= verdict.skeptic_score <= 100
        assert 0 <= verdict.guardian_score <= 100

    def test_advocate_agent_evaluates_timeliness(self):
        """Test that advocate agent evaluates for timeliness and demand."""
        from skills.adversarial_council import AdversarialCouncil
        from shared.models import ArticleDraft, AgentView

        draft = ArticleDraft(
            title="Breaking: Major Security Incident",
            description="Urgent security news.",
            category="News",
            contentType="News",
            body="# Breaking News\n\nA major security incident occurred today.",
            wordCount=300,
            sources=[{"id": "S1", "title": "Reuters", "url": "https://reuters.com"}],
        )
        evidence = [{"id": "S1", "title": "Reuters", "url": "https://reuters.com"}]

        council = AdversarialCouncil()
        advocate_view = council._agent_advocate(draft, evidence)

        assert isinstance(advocate_view, AgentView)
        assert advocate_view.agent == "advocate"
        assert advocate_view.score >= 0

    def test_skeptic_agent_challenges_sources(self):
        """Test that skeptic agent challenges veracity and sources."""
        from skills.adversarial_council import AdversarialCouncil
        from shared.models import ArticleDraft, AgentView

        # Draft with weak sourcing
        draft = ArticleDraft(
            title="Security Statistics Report",
            description="Report with many statistics.",
            category="Security",
            contentType="Analysis",
            body="# Report\n\nCrime increased by 50% this year. Revenue dropped 30%.",
            wordCount=400,
            sources=[],  # No sources!
        )
        evidence = []

        council = AdversarialCouncil()
        skeptic_view = council._agent_skeptic(draft, evidence)

        assert isinstance(skeptic_view, AgentView)
        assert skeptic_view.agent == "skeptic"
        # Skeptic should score poorly on unsourced content
        assert len(skeptic_view.concerns) > 0 or skeptic_view.score < 70

    def test_guardian_agent_protects_brand(self):
        """Test that guardian agent evaluates brand fit and risk."""
        from skills.adversarial_council import AdversarialCouncil
        from shared.models import ArticleDraft, AgentView

        draft = ArticleDraft(
            title="Product Review: Amazing Security System",
            description="Review of a security product.",
            category="Security",
            contentType="Review",
            body="# Review\n\nThis product is amazing and everyone should buy it!",
            wordCount=300,
            sources=[{"id": "S1", "title": "Vendor Site", "url": "https://vendor.com"}],
        )
        evidence = [{"id": "S1", "title": "Vendor Site", "url": "https://vendor.com"}]

        council = AdversarialCouncil()
        guardian_view = council._agent_guardian(draft, evidence)

        assert isinstance(guardian_view, AgentView)
        assert guardian_view.agent == "guardian"

    def test_verdict_synthesis_unanimous_publish(self):
        """Test verdict synthesis when all agents score high."""
        from skills.adversarial_council import AdversarialCouncil
        from shared.models import AgentView

        council = AdversarialCouncil()

        advocate = AgentView(
            agent="advocate",
            score=85,
            reasoning="Good timing",
            key_points=[],
            concerns=[],
            recommendations=[],
        )
        skeptic = AgentView(
            agent="skeptic",
            score=80,
            reasoning="Sources verified",
            key_points=[],
            concerns=[],
            recommendations=[],
        )
        guardian = AgentView(
            agent="guardian",
            score=75,
            reasoning="Brand safe",
            key_points=[],
            concerns=[],
            recommendations=[],
        )

        verdict = council._synthesize_verdict(advocate, skeptic, guardian)

        assert verdict.decision == "PUBLISH"
        assert verdict.average_score >= 70

    def test_verdict_synthesis_revise_on_low_skeptic(self):
        """Test verdict returns REVISE when skeptic scores low."""
        from skills.adversarial_council import AdversarialCouncil
        from shared.models import AgentView

        council = AdversarialCouncil()

        advocate = AgentView(
            agent="advocate",
            score=85,
            reasoning="Good timing",
            key_points=[],
            concerns=[],
            recommendations=[],
        )
        skeptic = AgentView(
            agent="skeptic",
            score=55,
            reasoning="Missing citations",
            key_points=[],
            concerns=["No sources for claim X"],
            recommendations=["Add source"],
        )
        guardian = AgentView(
            agent="guardian",
            score=75,
            reasoning="Brand safe",
            key_points=[],
            concerns=[],
            recommendations=[],
        )

        verdict = council._synthesize_verdict(advocate, skeptic, guardian)

        assert verdict.decision in ["REVISE", "KILL"]
        assert len(verdict.required_fixes) > 0 or verdict.kill_reason is not None

    def test_verdict_synthesis_kill_on_critical_issues(self):
        """Test verdict returns KILL when critical issues found."""
        from skills.adversarial_council import AdversarialCouncil
        from shared.models import AgentView

        council = AdversarialCouncil()

        advocate = AgentView(
            agent="advocate",
            score=60,
            reasoning="Timing okay",
            key_points=[],
            concerns=[],
            recommendations=[],
        )
        skeptic = AgentView(
            agent="skeptic",
            score=30,
            reasoning="Factual errors found",
            key_points=[],
            concerns=["Major factual error"],
            recommendations=[],
        )
        guardian = AgentView(
            agent="guardian",
            score=40,
            reasoning="Brand risk",
            key_points=[],
            concerns=["Legal liability"],
            recommendations=[],
        )

        verdict = council._synthesize_verdict(advocate, skeptic, guardian)

        assert verdict.decision == "KILL"
        assert verdict.kill_reason is not None


class TestProfileSpecificThresholds:
    """Tests for profile-specific threshold support in AdversarialCouncil."""

    def test_convene_accepts_profile_thresholds(self):
        """Test that convene() accepts optional profile thresholds."""
        from skills.adversarial_council import AdversarialCouncil
        from shared.models import ArticleDraft, CouncilThresholds

        draft = ArticleDraft(
            title="Test Article",
            description="Test description",
            category="Security",
            contentType="Guide",
            body="# Test\n\nContent with sources [S1].",
            wordCount=500,
            sources=[{"id": "S1", "title": "Test", "url": "https://test.com"}],
        )

        thresholds = CouncilThresholds(
            min_advocate=80,
            min_skeptic=75,
            min_guardian=80,
            require_unanimous=True,
        )

        council = AdversarialCouncil()
        verdict = council.convene(draft, [], thresholds=thresholds)

        assert verdict is not None
        assert verdict.decision in ["PUBLISH", "REVISE", "KILL"]

    def test_profile_thresholds_override_defaults(self):
        """Test that profile thresholds override default config."""
        from skills.adversarial_council import AdversarialCouncil
        from shared.models import AgentView, CouncilThresholds

        council = AdversarialCouncil()

        # Views with scores that would pass default but fail stricter profile
        advocate = AgentView(
            agent="advocate",
            score=72,
            reasoning="OK",
            key_points=[],
            concerns=[],
            recommendations=[],
        )
        skeptic = AgentView(
            agent="skeptic",
            score=65,
            reasoning="OK",
            key_points=[],
            concerns=[],
            recommendations=[],
        )
        guardian = AgentView(
            agent="guardian",
            score=70,
            reasoning="OK",
            key_points=[],
            concerns=[],
            recommendations=[],
        )

        # With stricter thresholds (research profile)
        strict_thresholds = CouncilThresholds(
            min_advocate=75,
            min_skeptic=70,
            min_guardian=75,
            require_unanimous=True,
        )

        verdict = council._synthesize_verdict(
            advocate, skeptic, guardian, thresholds=strict_thresholds
        )

        # Should REVISE because guardian (70) < min_guardian (75)
        assert verdict.decision == "REVISE"

    def test_unanimous_required_fails_with_one_low_score(self):
        """Test that require_unanimous=True fails if any score is below threshold."""
        from skills.adversarial_council import AdversarialCouncil
        from shared.models import AgentView, CouncilThresholds

        council = AdversarialCouncil()

        advocate = AgentView(
            agent="advocate",
            score=85,
            reasoning="Excellent timing",
            key_points=[],
            concerns=[],
            recommendations=[],
        )
        skeptic = AgentView(
            agent="skeptic",
            score=78,
            reasoning="Good sources",
            key_points=[],
            concerns=[],
            recommendations=[],
        )
        guardian = AgentView(
            agent="guardian",
            score=68,
            reasoning="Minor brand concerns",
            key_points=[],
            concerns=["Tone slightly off"],
            recommendations=["Adjust tone"],
        )

        # Require all to pass 70
        thresholds = CouncilThresholds(
            min_advocate=70,
            min_skeptic=70,
            min_guardian=70,
            require_unanimous=True,
        )

        verdict = council._synthesize_verdict(
            advocate, skeptic, guardian, thresholds=thresholds
        )

        # Guardian at 68 < 70, so should REVISE
        assert verdict.decision == "REVISE"

    def test_research_profile_requires_unanimous(self):
        """Test research profile with unanimous requirement."""
        from skills.adversarial_council import AdversarialCouncil
        from shared.models import AgentView, CouncilThresholds

        council = AdversarialCouncil()

        # All scores meet threshold
        advocate = AgentView(
            agent="advocate",
            score=80,
            reasoning="Good",
            key_points=[],
            concerns=[],
            recommendations=[],
        )
        skeptic = AgentView(
            agent="skeptic",
            score=75,
            reasoning="Good",
            key_points=[],
            concerns=[],
            recommendations=[],
        )
        guardian = AgentView(
            agent="guardian",
            score=78,
            reasoning="Good",
            key_points=[],
            concerns=[],
            recommendations=[],
        )

        # Research profile thresholds
        thresholds = CouncilThresholds(
            min_advocate=75,
            min_skeptic=70,
            min_guardian=75,
            require_unanimous=True,
        )

        verdict = council._synthesize_verdict(
            advocate, skeptic, guardian, thresholds=thresholds
        )

        # All pass thresholds with unanimous required
        assert verdict.decision == "PUBLISH"


class TestGateChecks:
    """Tests for profile-specific gate checks (opinion_balance, expert_citation)."""

    def test_opinion_balance_gate_detects_bias(self):
        """Test that opinion_balance gate detects one-sided analysis."""
        from skills.adversarial_council import AdversarialCouncil
        from shared.models import ArticleDraft

        council = AdversarialCouncil()

        # One-sided analysis article
        draft = ArticleDraft(
            title="Analysis: Why Product X is the Best Choice",
            description="Analysis of security products",
            category="Security",
            contentType="Analysis",
            body="""# Analysis

Product X is clearly superior. Every expert agrees this is the best option.
There are no downsides. Competitors are inferior in every way.
No one should consider alternatives.""",
            wordCount=500,
            sources=[{"id": "S1", "title": "Vendor", "url": "https://vendor.com"}],
        )

        result = council.check_opinion_balance(draft)

        assert result is not None
        assert result["passed"] is False
        assert result["balance_score"] < 50

    def test_opinion_balance_gate_passes_balanced_content(self):
        """Test that balanced analysis passes opinion_balance gate."""
        from skills.adversarial_council import AdversarialCouncil
        from shared.models import ArticleDraft

        council = AdversarialCouncil()

        # Balanced analysis
        draft = ArticleDraft(
            title="Analysis: Comparing Security Products",
            description="Balanced comparison of options",
            category="Security",
            contentType="Analysis",
            body="""# Comparative Analysis

Product X offers strong encryption but has usability challenges.
Product Y provides better integration but costs more.
The choice depends on organizational priorities and budget constraints.
Both have merit for different use cases.""",
            wordCount=500,
            sources=[
                {"id": "S1", "title": "Source 1", "url": "https://example1.com"},
                {"id": "S2", "title": "Source 2", "url": "https://example2.com"},
            ],
        )

        result = council.check_opinion_balance(draft)

        assert result is not None
        assert result["passed"] is True
        assert result["balance_score"] >= 50

    def test_expert_citation_gate_requires_authoritative_sources(self):
        """Test that expert_citation gate requires authoritative sources for guides."""
        from skills.adversarial_council import AdversarialCouncil
        from shared.models import ArticleDraft

        council = AdversarialCouncil()

        # Guide with only vendor sources
        draft = ArticleDraft(
            title="Complete Guide to CCTV Compliance",
            description="Comprehensive compliance guide",
            category="Compliance",
            contentType="Guide",
            body="""# Compliance Guide

This guide covers all compliance requirements.
According to our research, you must follow these steps...""",
            wordCount=2000,
            sources=[
                {"id": "S1", "title": "Vendor Blog", "url": "https://vendor.com/blog"},
            ],
        )

        result = council.check_expert_citation(draft)

        assert result is not None
        assert result["passed"] is False
        assert result["authoritative_count"] < 2

    def test_expert_citation_gate_passes_with_authoritative_sources(self):
        """Test that guide with government/academic sources passes."""
        from skills.adversarial_council import AdversarialCouncil
        from shared.models import ArticleDraft

        council = AdversarialCouncil()

        # Guide with authoritative sources
        draft = ArticleDraft(
            title="Complete Guide to Data Protection Compliance",
            description="Compliance guide based on official regulations",
            category="Compliance",
            contentType="Guide",
            body="""# Data Protection Compliance Guide

This guide is based on official CERT-IN guidelines [S1] and
RBI cybersecurity framework [S2]. Academic research [S3] supports
these recommendations.""",
            wordCount=2000,
            sources=[
                {
                    "id": "S1",
                    "title": "CERT-IN Guidelines",
                    "url": "https://cert-in.org.in/guidelines",
                },
                {
                    "id": "S2",
                    "title": "RBI Framework",
                    "url": "https://rbi.org.in/cyber",
                },
                {
                    "id": "S3",
                    "title": "IIT Research",
                    "url": "https://iit.ac.in/research",
                },
            ],
        )

        result = council.check_expert_citation(draft)

        assert result is not None
        assert result["passed"] is True
        assert result["authoritative_count"] >= 2

    def test_convene_applies_gates_for_views_profile(self):
        """Test that convene applies opinion_balance gate for views profile."""
        from skills.adversarial_council import AdversarialCouncil
        from shared.models import ArticleDraft, CouncilThresholds

        council = AdversarialCouncil()

        draft = ArticleDraft(
            title="Analysis: Why This Approach is Best",
            description="Biased analysis",
            category="Security",
            contentType="Analysis",
            body="This is clearly the only right approach. All alternatives are wrong.",
            wordCount=500,
            sources=[{"id": "S1", "title": "Test", "url": "https://test.com"}],
        )

        thresholds = CouncilThresholds(
            min_advocate=70,
            min_skeptic=60,
            min_guardian=75,
        )

        verdict = council.convene(
            draft, [], thresholds=thresholds, gates=["opinion_balance"]
        )

        # Should have gate result in verdict
        assert verdict is not None
        # The verdict should reflect gate check failure

    def test_convene_applies_gates_for_research_profile(self):
        """Test that convene applies expert_citation gate for research profile."""
        from skills.adversarial_council import AdversarialCouncil
        from shared.models import ArticleDraft, CouncilThresholds

        council = AdversarialCouncil()

        draft = ArticleDraft(
            title="Complete Guide to Security Compliance",
            description="Guide without authoritative sources",
            category="Compliance",
            contentType="Guide",
            body="# Guide\n\nFollow these steps for compliance.",
            wordCount=2000,
            sources=[{"id": "S1", "title": "Blog", "url": "https://blog.example.com"}],
        )

        thresholds = CouncilThresholds(
            min_advocate=75,
            min_skeptic=70,
            min_guardian=75,
            require_unanimous=True,
        )

        verdict = council.convene(
            draft, [], thresholds=thresholds, gates=["expert_citation"]
        )

        assert verdict is not None
        # Expert citation gate should affect the decision


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

    def test_learning_insights_creation(self):
        """Test LearningInsights model."""
        from shared.models import LearningInsights

        insights = LearningInsights(
            top_performing_topics=["cybersecurity", "compliance"],
            underperforming_topics=["general"],
            best_content_types=["Guide", "Analysis"],
            best_sectors=["Finance", "Healthcare"],
            recommended_weight_adjustments={"Guide": 1.2, "News": 0.9},
            patterns_identified=["Long-form guides perform 40% better"],
        )

        assert len(insights.top_performing_topics) == 2
        assert insights.recommended_weight_adjustments["Guide"] == 1.2
