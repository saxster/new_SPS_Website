"""
Tests for Editorial Brain v2 - TDD First
LLM-powered editorial judgment system with news sense.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime


@pytest.fixture
def mock_brain():
    """Create a mock ContentBrain."""
    mock = MagicMock()
    mock.get_stats.return_value = {
        "status": {"PROPOSED": 5, "DRAFTED": 2, "PUBLISHED": 10},
        "types": {"Guide": 5, "Analysis": 3, "News": 2},
    }
    return mock


@pytest.fixture
def mock_client():
    """Create a mock GeminiAgent."""
    mock = MagicMock()
    mock.generate_json.return_value = {
        "news_sense": 75,
        "audience_fit": 80,
        "competitive_angle": 70,
        "feasibility": 85,
        "timing": 60,
        "reasoning": "Good topic for our audience",
        "recommended_angle": "Focus on compliance implications",
    }
    return mock


class TestEditorialBrainV2:
    """Tests for EditorialBrainV2 class."""

    def test_brain_initialization(self, mock_brain, mock_client):
        """Test EditorialBrainV2 can be initialized."""
        from skills.editorial_brain import EditorialBrainV2

        brain = EditorialBrainV2(client=mock_client, brain=mock_brain)
        assert brain is not None

    def test_analyze_landscape_returns_directive(self, mock_brain, mock_client):
        """Test that analyze_landscape returns an EditorialDirective."""
        from skills.editorial_brain import EditorialBrainV2
        from shared.models import EditorialDirective

        brain = EditorialBrainV2(client=mock_client, brain=mock_brain)
        directive = brain.analyze_landscape()

        assert isinstance(directive, EditorialDirective)
        assert directive.action in [
            "HUNT_BREAKING",
            "HUNT_TRENDING",
            "HUNT_GAP",
            "WRITE_PRIORITY",
            "WRITE_QUEUE",
            "HOLD",
        ]

    def test_evaluate_topic_returns_evaluation(self, mock_brain, mock_client):
        """Test that evaluate_topic returns a TopicEvaluation."""
        from skills.editorial_brain import EditorialBrainV2
        from shared.models import TopicEvaluation

        brain = EditorialBrainV2(client=mock_client, brain=mock_brain)

        topic = {
            "topic": "New RBI Cybersecurity Guidelines",
            "signals": [{"source": "google_news", "trend": "rising"}],
        }

        evaluation = brain.evaluate_topic(topic)

        assert isinstance(evaluation, TopicEvaluation)
        assert 0 <= evaluation.news_sense <= 100
        assert 0 <= evaluation.audience_fit <= 100
        assert 0 <= evaluation.overall_score <= 100

    def test_brain_uses_config_weights(self, mock_brain, mock_client):
        """Test that brain uses configured weights for scoring."""
        from skills.editorial_brain import EditorialBrainV2

        brain = EditorialBrainV2(client=mock_client, brain=mock_brain)

        # Check that weights exist and sum to 1.0 (or close to it)
        weights = brain.scoring_weights
        assert "news_sense" in weights
        assert "audience_fit" in weights
        assert "competitive_angle" in weights
        assert "feasibility" in weights
        assert "timing" in weights

        total = sum(weights.values())
        assert 0.99 <= total <= 1.01, f"Weights should sum to 1.0, got {total}"

    def test_brain_detects_breaking_news(self, mock_brain, mock_client):
        """Test that brain can detect breaking news signals."""
        from skills.editorial_brain import EditorialBrainV2

        brain = EditorialBrainV2(client=mock_client, brain=mock_brain)

        # Mock breaking news signals
        breaking_signals = [
            {
                "title": "Major data breach at leading bank",
                "source": "reuters",
                "published": datetime.now().isoformat(),
                "urgency": "high",
            }
        ]

        directive = brain._process_signals(breaking_signals)

        # Should recognize this as urgent
        assert directive.action in ["HUNT_BREAKING", "WRITE_PRIORITY"]
        assert directive.urgency in ["critical", "high"]

    def test_brain_identifies_content_gaps(self, mock_brain, mock_client):
        """Test that brain can identify content gaps."""
        from skills.editorial_brain import EditorialBrainV2

        brain = EditorialBrainV2(client=mock_client, brain=mock_brain)

        # Get gap analysis
        gaps = brain._analyze_content_gaps()

        assert isinstance(gaps, list)
        # Each gap should have topic and gap_score
        for gap in gaps:
            assert "topic" in gap or "sector" in gap or "content_type" in gap

    def test_fallback_to_cco_on_error(self, mock_brain, mock_client):
        """Test that brain falls back to CCO logic on error."""
        from skills.editorial_brain import EditorialBrainV2
        from shared.models import EditorialDirective

        brain = EditorialBrainV2(client=mock_client, brain=mock_brain)

        # Force an error scenario
        with patch.object(brain, "client", None):
            directive = brain._fallback_cco_logic()

        assert isinstance(directive, EditorialDirective)
        assert directive.action in ["WRITE_QUEUE", "HUNT_GAP"]

    def test_directive_includes_reason(self, mock_brain, mock_client):
        """Test that directives always include a reason."""
        from skills.editorial_brain import EditorialBrainV2

        brain = EditorialBrainV2(client=mock_client, brain=mock_brain)
        directive = brain.analyze_landscape()

        assert directive.reason is not None
        assert len(directive.reason) > 0

    def test_evaluate_topic_with_empty_signals(self, mock_brain, mock_client):
        """Test topic evaluation with no signals."""
        from skills.editorial_brain import EditorialBrainV2
        from shared.models import TopicEvaluation

        # Mock client returns lower timing for no signals
        mock_client.generate_json.return_value = {
            "news_sense": 60,
            "audience_fit": 70,
            "competitive_angle": 65,
            "feasibility": 80,
            "timing": 40,  # Lower for no signals
            "reasoning": "Evergreen topic, no urgency",
            "recommended_angle": None,
        }

        brain = EditorialBrainV2(client=mock_client, brain=mock_brain)

        topic = {
            "topic": "General Security Best Practices",
            "signals": [],
        }

        evaluation = brain.evaluate_topic(topic)

        assert isinstance(evaluation, TopicEvaluation)
        # Without signals, timing should be lower
        assert evaluation.timing <= 70

    def test_brain_respects_focus_sectors(self, mock_brain, mock_client):
        """Test that brain considers configured focus sectors."""
        from skills.editorial_brain import EditorialBrainV2

        brain = EditorialBrainV2(client=mock_client, brain=mock_brain)

        # Get focus sectors from config
        focus_sectors = brain.focus_sectors

        assert isinstance(focus_sectors, list)
        assert len(focus_sectors) > 0
        # Should include typical security sectors
        assert any(
            s in focus_sectors
            for s in ["physical_security", "cybersecurity", "security", "cyber"]
        )
