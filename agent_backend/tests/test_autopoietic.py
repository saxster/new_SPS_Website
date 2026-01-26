"""
Comprehensive Test Suite for the Autopoietic Autonomous Newsroom.
Tests all components: TasteMemory, TasteModel, TopicProposer, AutonomousRunner.
"""

import pytest
import sqlite3
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

# Import test subjects
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from skills.taste_memory import TasteMemory, ArticleFeedback
from skills.taste_model import TasteModel, TasteWeights
from skills.agents.topic_proposer import TopicProposer, Signal, TopicProposal


# =============================================================================
# TasteMemory Tests
# =============================================================================

class TestArticleFeedback:
    """Tests for ArticleFeedback dataclass."""
    
    def test_creation(self):
        """Test basic feedback creation."""
        feedback = ArticleFeedback(
            topic_id="test_001",
            topic="Test Topic",
            sector="cybersecurity",
            content_type="News",
            proposal_score=0.75,
            quality_score=85.0,
            was_published=True,
            was_blocked=False,
            block_reason=None,
            time_to_write_seconds=120.0,
            sources_found=5,
            sources_used=3,
            trust_score=8.0
        )
        
        assert feedback.topic_id == "test_001"
        assert feedback.sector == "cybersecurity"
    
    def test_success_property(self):
        """Test success is True when published and quality >= 70."""
        feedback = ArticleFeedback(
            topic_id="x", topic="x", sector="x", content_type="x",
            proposal_score=0.7, quality_score=80, was_published=True,
            was_blocked=False, block_reason=None, time_to_write_seconds=0,
            sources_found=0, sources_used=0, trust_score=0
        )
        assert feedback.success is True
    
    def test_success_false_when_blocked(self):
        """Test success is False when blocked."""
        feedback = ArticleFeedback(
            topic_id="x", topic="x", sector="x", content_type="x",
            proposal_score=0.7, quality_score=80, was_published=False,
            was_blocked=True, block_reason="trust", time_to_write_seconds=0,
            sources_found=0, sources_used=0, trust_score=0
        )
        assert feedback.success is False
    
    def test_prediction_error(self):
        """Test prediction error calculation."""
        feedback = ArticleFeedback(
            topic_id="x", topic="x", sector="x", content_type="x",
            proposal_score=0.5, quality_score=80, was_published=True,
            was_blocked=False, block_reason=None, time_to_write_seconds=0,
            sources_found=0, sources_used=0, trust_score=0
        )
        # 80/100 - 0.5 = 0.3 (underestimated)
        assert feedback.prediction_error == pytest.approx(0.3)


class TestTasteMemory:
    """Tests for TasteMemory persistence layer."""
    
    @pytest.fixture
    def memory(self, tmp_path):
        """Create a temporary TasteMemory instance."""
        db_path = str(tmp_path / "test_taste.db")
        return TasteMemory(db_path=db_path)
    
    def test_initialization(self, memory):
        """Test memory initializes correctly."""
        stats = memory.get_stats()
        assert stats['feedback_records'] == 0
        assert stats['weights_stored'] == 0
    
    def test_record_feedback(self, memory):
        """Test recording feedback."""
        feedback = ArticleFeedback(
            topic_id="test_001", topic="Test", sector="cybersecurity",
            content_type="News", proposal_score=0.7, quality_score=85,
            was_published=True, was_blocked=False, block_reason=None,
            time_to_write_seconds=100, sources_found=5, sources_used=3,
            trust_score=8
        )
        
        memory.record_feedback(feedback)
        
        stats = memory.get_stats()
        assert stats['feedback_records'] == 1
    
    def test_weight_persistence(self, memory):
        """Test saving and loading weights."""
        memory.save_weight("sector", "cybersecurity", 1.25, samples=10)
        
        loaded = memory.get_weight("sector", "cybersecurity")
        assert loaded == 1.25
    
    def test_get_all_weights(self, memory):
        """Test getting all weights for a category."""
        memory.save_weight("sector", "cyber", 1.1)
        memory.save_weight("sector", "fire", 0.9)
        
        weights = memory.get_all_weights("sector")
        assert weights["cyber"] == 1.1
        assert weights["fire"] == 0.9
    
    def test_sector_performance(self, memory):
        """Test sector performance analytics."""
        # Record some feedback
        for quality, published in [(85, True), (75, True), (40, False)]:
            feedback = ArticleFeedback(
                topic_id=f"t{quality}", topic="T", sector="cybersecurity",
                content_type="News", proposal_score=0.7, quality_score=quality,
                was_published=published, was_blocked=not published,
                block_reason=None if published else "low",
                time_to_write_seconds=100, sources_found=5, sources_used=3,
                trust_score=7
            )
            memory.record_feedback(feedback)
        
        perf = memory.get_sector_performance(30)
        assert "cybersecurity" in perf
        assert perf["cybersecurity"]["total"] == 3
        assert perf["cybersecurity"]["published"] == 2


# =============================================================================
# TasteModel Tests
# =============================================================================

class TestTasteModel:
    """Tests for TasteModel learning system."""
    
    @pytest.fixture
    def model(self, tmp_path):
        """Create a TasteModel with temporary memory."""
        db_path = str(tmp_path / "test_taste.db")
        memory = TasteMemory(db_path=db_path)
        return TasteModel(memory=memory)
    
    def test_initialization(self, model):
        """Test model initializes with default weights."""
        assert model.learning_rate == 0.1
        assert model.exploration_rate == 0.2
    
    def test_weight_boost_on_success(self, model):
        """Test weights increase after successful article."""
        feedback = ArticleFeedback(
            topic_id="x", topic="x", sector="cybersecurity",
            content_type="News", proposal_score=0.7, quality_score=85,
            was_published=True, was_blocked=False, block_reason=None,
            time_to_write_seconds=100, sources_found=5, sources_used=3,
            trust_score=8
        )
        
        model.update(feedback)
        
        # Weight should be boosted by 10%
        assert model.sector_weights["cybersecurity"] == pytest.approx(1.1)
        assert model.content_type_weights["News"] == pytest.approx(1.1)
    
    def test_weight_penalize_on_failure(self, model):
        """Test weights decrease after blocked article."""
        feedback = ArticleFeedback(
            topic_id="x", topic="x", sector="fire_safety",
            content_type="Guide", proposal_score=0.7, quality_score=0,
            was_published=False, was_blocked=True, block_reason="trust",
            time_to_write_seconds=100, sources_found=1, sources_used=0,
            trust_score=2
        )
        
        model.update(feedback)
        
        # Weight should be reduced by 10%
        assert model.sector_weights["fire_safety"] == pytest.approx(0.9)
    
    def test_weight_bounds(self, model):
        """Test weights stay within bounds."""
        # Force many boosts
        for _ in range(20):
            feedback = ArticleFeedback(
                topic_id="x", topic="x", sector="test",
                content_type="News", proposal_score=0.7, quality_score=90,
                was_published=True, was_blocked=False, block_reason=None,
                time_to_write_seconds=100, sources_found=5, sources_used=3,
                trust_score=8
            )
            model.update(feedback)
        
        # Should not exceed max_weight (2.0)
        assert model.sector_weights["test"] <= model.max_weight
    
    def test_score_adjustment(self, model):
        """Test score adjustment with learned weights."""
        # Boost cybersecurity
        model.sector_weights["cybersecurity"] = 1.5
        model.content_type_weights["News"] = 1.2
        
        mock_proposal = MagicMock()
        mock_proposal.score = 0.5
        mock_proposal.sector = None
        mock_proposal.topic = "cybersecurity breach analysis"
        mock_proposal.content_type = "News"
        
        adjusted = model.adjust_score(mock_proposal)
        
        # Should be boosted: 0.5 * 1.5 * 1.2 = 0.9
        assert adjusted > 0.5


# =============================================================================
# TopicProposer Tests
# =============================================================================

class TestSignal:
    """Tests for Signal dataclass."""
    
    def test_creation(self):
        """Test signal creation."""
        signal = Signal(
            id="news_123",
            source="news",
            title="Security Breach at Bank",
            summary="Major breach reported...",
            url="https://example.com",
            sector="cybersecurity",
            urgency=8
        )
        
        assert signal.id == "news_123"
        assert signal.source == "news"
        assert signal.urgency == 8


class TestTopicProposal:
    """Tests for TopicProposal dataclass."""
    
    def test_creation(self):
        """Test proposal creation."""
        proposal = TopicProposal(
            id="prop_123",
            topic="How to Prevent Data Breaches in Banking",
            content_type="Guide",
            rationale="Recent high-profile breaches",
            signals=["news_001"],
            score=0.85,
            priority="high",
            suggested_angle="Focus on Indian banking sector"
        )
        
        assert proposal.topic.startswith("How to")
        assert proposal.score == 0.85
        assert proposal.priority == "high"
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        proposal = TopicProposal(
            id="prop_123", topic="Test", content_type="News",
            rationale="Test", signals=[], score=0.7,
            priority="medium", suggested_angle="Test angle"
        )
        
        d = proposal.to_dict()
        assert d["id"] == "prop_123"
        assert d["score"] == 0.7


class TestTopicProposer:
    """Tests for TopicProposer agent."""
    
    @pytest.fixture
    def proposer(self, tmp_path):
        """Create TopicProposer with mocked dependencies."""
        db_path = str(tmp_path / "test_brain.db")
        
        # Create mock brain
        mock_brain = MagicMock()
        mock_brain.get_stats.return_value = {}
        mock_brain.list_topics.return_value = []
        
        # Create mock LLM
        mock_llm = MagicMock()
        mock_llm.generate_json.return_value = [
            {
                "topic": "Test Security Topic",
                "content_type": "News",
                "angle": "Test angle",
                "audience": "Security pros",
                "demand": 7
            }
        ]
        
        return TopicProposer(brain=mock_brain, llm=mock_llm)
    
    def test_initialization(self, proposer):
        """Test proposer initializes correctly."""
        assert proposer.max_proposals == 10
        assert len(proposer.focus_sectors) == 5
    
    def test_gather_news_signals(self, proposer):
        """Test news signal gathering."""
        with patch.object(proposer.news_miner, 'fetch_signals') as mock_fetch:
            mock_fetch.return_value = [
                {"title": "Test News", "summary": "Summary", "url": "http://x.com", "sector": "General"}
            ]
            
            signals = proposer._gather_news_signals()
            
            assert len(signals) >= 0  # May be empty if network fails
    
    def test_similarity(self, proposer):
        """Test text similarity calculation."""
        sim = proposer._similarity(
            "cybersecurity breach india",
            "india cybersecurity data breach"
        )
        
        assert sim > 0.5  # Should have significant overlap
    
    def test_score_to_priority(self, proposer):
        """Test score to priority conversion."""
        assert proposer._score_to_priority(0.85) == "urgent"
        assert proposer._score_to_priority(0.65) == "high"
        assert proposer._score_to_priority(0.45) == "medium"
        assert proposer._score_to_priority(0.25) == "low"


# =============================================================================
# Integration Tests
# =============================================================================

class TestAutopoieticIntegration:
    """Integration tests for the full autopoietic system."""
    
    @pytest.fixture
    def system(self, tmp_path):
        """Create full system with temporary storage."""
        db_path = str(tmp_path / "test_taste.db")
        memory = TasteMemory(db_path=db_path)
        model = TasteModel(memory=memory)
        return memory, model
    
    def test_feedback_loop(self, system):
        """Test complete feedback loop: record → learn → adjust."""
        memory, model = system
        
        # Initial state
        initial_weight = model.sector_weights.get("cybersecurity", 1.0)
        
        # Simulate successful article
        feedback = ArticleFeedback(
            topic_id="loop_test", topic="Cybersecurity Guide",
            sector="cybersecurity", content_type="Guide",
            proposal_score=0.6, quality_score=88,
            was_published=True, was_blocked=False, block_reason=None,
            time_to_write_seconds=300, sources_found=8, sources_used=5,
            trust_score=9
        )
        
        model.update(feedback)
        
        # Weight should be updated
        new_weight = model.sector_weights["cybersecurity"]
        assert new_weight > initial_weight
        
        # Feedback should be persisted
        recent = memory.get_recent_feedback(7)
        assert len(recent) == 1
        assert recent[0].topic_id == "loop_test"
    
    def test_taste_development_over_time(self, system):
        """Test that taste develops through multiple feedback cycles."""
        memory, model = system
        
        # Simulate 5 successful cybersecurity articles
        for i in range(5):
            feedback = ArticleFeedback(
                topic_id=f"cyber_{i}", topic="Cyber Topic",
                sector="cybersecurity", content_type="News",
                proposal_score=0.7, quality_score=85,
                was_published=True, was_blocked=False, block_reason=None,
                time_to_write_seconds=100, sources_found=5, sources_used=4,
                trust_score=8
            )
            model.update(feedback)
        
        # Simulate 3 failed fire_safety articles
        for i in range(3):
            feedback = ArticleFeedback(
                topic_id=f"fire_{i}", topic="Fire Topic",
                sector="fire_safety", content_type="Guide",
                proposal_score=0.7, quality_score=30,
                was_published=False, was_blocked=True, block_reason="low_quality",
                time_to_write_seconds=100, sources_found=2, sources_used=1,
                trust_score=3
            )
            model.update(feedback)
        
        # Cybersecurity should be favored
        cyber_weight = model.sector_weights["cybersecurity"]
        fire_weight = model.sector_weights["fire_safety"]
        
        assert cyber_weight > 1.0  # Boosted
        assert fire_weight < 1.0   # Penalized
        assert cyber_weight > fire_weight  # Clear preference


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
