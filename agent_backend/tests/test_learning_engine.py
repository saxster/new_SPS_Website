"""
Tests for Learning Engine - TDD First
Performance tracking and editorial weight adjustment.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
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
def mock_client():
    """Create a mock GeminiAgent."""
    mock = MagicMock()
    mock.generate_json.return_value = {
        "top_performing_patterns": ["long-form guides", "regulatory news"],
        "underperforming_patterns": ["general updates"],
        "recommended_adjustments": {"Guide": 1.15, "News": 1.1, "General": 0.85},
        "insights": ["Guides with 1500+ words perform 40% better"],
    }
    return mock


class TestLearningEngine:
    """Tests for LearningEngine class."""

    def test_engine_initialization(self, temp_db, mock_client):
        """Test LearningEngine can be initialized."""
        from skills.learning_engine import LearningEngine
        from skills.content_brain import ContentBrain

        brain = ContentBrain(db_path=temp_db)
        engine = LearningEngine(client=mock_client, brain=brain)
        assert engine is not None

    def test_update_weights_returns_insights(self, temp_db, mock_client):
        """Test that update_weights returns LearningInsights."""
        from skills.learning_engine import LearningEngine
        from skills.content_brain import ContentBrain
        from shared.models import LearningInsights

        brain = ContentBrain(db_path=temp_db)
        engine = LearningEngine(client=mock_client, brain=brain)

        insights = engine.update_weights()

        assert isinstance(insights, LearningInsights)

    def test_get_top_performers(self, temp_db, mock_client):
        """Test getting top performing articles."""
        from skills.learning_engine import LearningEngine
        from skills.content_brain import ContentBrain

        brain = ContentBrain(db_path=temp_db)
        engine = LearningEngine(client=mock_client, brain=brain)

        top = engine.get_top_performers(limit=10)
        assert isinstance(top, list)

    def test_get_bottom_performers(self, temp_db, mock_client):
        """Test getting bottom performing articles."""
        from skills.learning_engine import LearningEngine
        from skills.content_brain import ContentBrain

        brain = ContentBrain(db_path=temp_db)
        engine = LearningEngine(client=mock_client, brain=brain)

        bottom = engine.get_bottom_performers(limit=10)
        assert isinstance(bottom, list)

    def test_record_performance(self, temp_db, mock_client):
        """Test recording article performance metrics."""
        from skills.learning_engine import LearningEngine
        from skills.content_brain import ContentBrain
        from shared.models import ArticlePerformance

        brain = ContentBrain(db_path=temp_db)
        engine = LearningEngine(client=mock_client, brain=brain)

        perf = ArticlePerformance(
            article_slug="test-article",
            views=1000,
            avg_time_seconds=120.5,
            shares=15,
            bounce_rate=0.35,
            engagement_score=7.5,
        )

        result = engine.record_performance(perf)
        assert result is True

    def test_calculate_engagement_score(self, temp_db, mock_client):
        """Test engagement score calculation."""
        from skills.learning_engine import LearningEngine
        from skills.content_brain import ContentBrain

        brain = ContentBrain(db_path=temp_db)
        engine = LearningEngine(client=mock_client, brain=brain)

        score = engine.calculate_engagement_score(
            views=1000,
            avg_time_seconds=180,
            shares=20,
            bounce_rate=0.3,
        )

        assert isinstance(score, float)
        assert score >= 0

    def test_analyze_patterns_uses_llm(self, temp_db, mock_client):
        """Test that pattern analysis uses LLM."""
        from skills.learning_engine import LearningEngine
        from skills.content_brain import ContentBrain

        brain = ContentBrain(db_path=temp_db)
        engine = LearningEngine(client=mock_client, brain=brain)

        top = [{"slug": "good-article", "engagement_score": 9.0}]
        bottom = [{"slug": "bad-article", "engagement_score": 2.0}]

        patterns = engine._analyze_patterns(top, bottom)

        # Should have called the LLM
        mock_client.generate_json.assert_called()
        assert "recommended_adjustments" in patterns

    def test_weight_bounds_respected(self, temp_db, mock_client):
        """Test that weight adjustments stay within bounds."""
        from skills.learning_engine import LearningEngine
        from skills.content_brain import ContentBrain

        brain = ContentBrain(db_path=temp_db)
        engine = LearningEngine(client=mock_client, brain=brain)

        # Test bounds
        max_mult = engine.config.get("max_weight_multiplier", 2.0)
        min_mult = engine.config.get("min_weight_multiplier", 0.5)

        # Simulate extreme adjustment
        adjusted = engine._apply_bounds(3.0)  # Above max
        assert adjusted <= max_mult

        adjusted = engine._apply_bounds(0.1)  # Below min
        assert adjusted >= min_mult


class TestPerformanceTable:
    """Tests for performance table in ContentBrain."""

    def test_performance_table_exists(self, temp_db):
        """Test that performance table is created."""
        from skills.learning_engine import LearningEngine
        from skills.content_brain import ContentBrain

        brain = ContentBrain(db_path=temp_db)
        engine = LearningEngine(brain=brain)

        # Table should be created on init
        cur = brain.conn.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='article_performance'"
        )
        result = cur.fetchone()
        assert result is not None

    def test_store_and_retrieve_performance(self, temp_db):
        """Test storing and retrieving performance data."""
        from skills.learning_engine import LearningEngine
        from skills.content_brain import ContentBrain
        from shared.models import ArticlePerformance

        brain = ContentBrain(db_path=temp_db)
        engine = LearningEngine(brain=brain)

        # Store
        perf = ArticlePerformance(
            article_slug="test-perf-article",
            views=500,
            avg_time_seconds=90.0,
            shares=5,
            bounce_rate=0.4,
            engagement_score=5.5,
        )
        engine.record_performance(perf)

        # Retrieve
        stored = engine.get_performance("test-perf-article")
        assert stored is not None
        assert stored["views"] == 500
        assert stored["engagement_score"] == 5.5


class TestReflectionCycle:
    """Tests for the reflection cycle."""

    def test_should_reflect_after_interval(self, temp_db, mock_client):
        """Test reflection trigger based on interval."""
        from skills.learning_engine import LearningEngine
        from skills.content_brain import ContentBrain

        brain = ContentBrain(db_path=temp_db)
        engine = LearningEngine(client=mock_client, brain=brain)

        # Should reflect if never reflected
        assert engine.should_reflect() is True

    def test_reflection_updates_last_reflected(self, temp_db, mock_client):
        """Test that reflection updates the last reflected timestamp."""
        from skills.learning_engine import LearningEngine
        from skills.content_brain import ContentBrain

        brain = ContentBrain(db_path=temp_db)
        engine = LearningEngine(client=mock_client, brain=brain)

        old_time = engine.last_reflected

        engine.run_reflection_cycle()

        # Timestamp should be updated
        assert engine.last_reflected > old_time
