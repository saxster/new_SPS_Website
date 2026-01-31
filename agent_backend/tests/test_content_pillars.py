"""
Tests for ContentPillarManager - Reader-centric content organization.
"""

import pytest
from unittest.mock import Mock, patch

from skills.content_pillars import (
    ContentPillarManager,
    DEFAULT_PILLARS,
    DEFAULT_PERSONAS,
)
from shared.models import SourcedTopic, ContentPillar, AudiencePersona


class TestContentPillarManager:
    """Test ContentPillarManager functionality."""

    def test_init_with_defaults(self):
        """Test initialization with default pillars and personas."""
        manager = ContentPillarManager()

        assert len(manager.pillars) == 7
        assert len(manager.personas) == 5

    def test_get_pillar(self):
        """Test getting a pillar by slug."""
        manager = ContentPillarManager()

        pillar = manager.get_pillar("scam_watch")
        assert pillar is not None
        assert pillar.name == "Scam Watch"
        assert pillar.priority == 1
        assert pillar.target_mix == 0.20

    def test_get_pillar_not_found(self):
        """Test getting a non-existent pillar."""
        manager = ContentPillarManager()

        pillar = manager.get_pillar("nonexistent")
        assert pillar is None

    def test_get_all_pillars_sorted(self):
        """Test getting all pillars sorted by priority."""
        manager = ContentPillarManager()

        pillars = manager.get_all_pillars()
        assert len(pillars) == 7

        # Should be sorted by priority
        priorities = [p.priority for p in pillars]
        assert priorities == sorted(priorities)

    def test_get_persona(self):
        """Test getting a persona by ID."""
        manager = ContentPillarManager()

        persona = manager.get_persona("citizen")
        assert persona is not None
        assert persona.name == "General Citizen"
        assert persona.complexity_level == "basic"
        assert persona.actionability_weight == 0.9

    def test_get_persona_not_found(self):
        """Test getting a non-existent persona."""
        manager = ContentPillarManager()

        persona = manager.get_persona("nonexistent")
        assert persona is None

    def test_route_topic_scam(self):
        """Test routing scam topics to scam_watch pillar."""
        manager = ContentPillarManager()

        topic = SourcedTopic(
            id="test_1",
            title="Digital Arrest Scam Alert",
            source_type="scam",
            source_id="test",
        )

        pillar = manager.route_topic_to_pillar(topic)
        assert pillar == "scam_watch"

    def test_route_topic_market(self):
        """Test routing market topics to economic_security pillar."""
        manager = ContentPillarManager()

        topic = SourcedTopic(
            id="test_2",
            title="SEBI Warning on Investment Fraud",
            source_type="market",
            source_id="test",
        )

        pillar = manager.route_topic_to_pillar(topic)
        assert pillar == "economic_security"

    def test_route_topic_consumer(self):
        """Test routing consumer topics to product_reviews pillar."""
        manager = ContentPillarManager()

        topic = SourcedTopic(
            id="test_3",
            title="Best CCTV Cameras 2024",
            source_type="consumer",
            source_id="test",
        )

        pillar = manager.route_topic_to_pillar(topic)
        assert pillar == "product_reviews"

    def test_route_topic_with_existing_pillar(self):
        """Test that existing pillar assignment is preserved."""
        manager = ContentPillarManager()

        topic = SourcedTopic(
            id="test_4",
            title="Some Topic",
            source_type="breaking",
            source_id="test",
            primary_pillar="senior_safety",
        )

        pillar = manager.route_topic_to_pillar(topic)
        assert pillar == "senior_safety"

    def test_route_topic_by_tags_scam(self):
        """Test routing by scam-related tags."""
        manager = ContentPillarManager()

        topic = SourcedTopic(
            id="test_5",
            title="New Alert",
            source_type="breaking",
            source_id="test",
            tags=["fraud", "alert"],
        )

        pillar = manager.route_topic_to_pillar(topic)
        assert pillar == "scam_watch"

    def test_route_topic_by_tags_senior(self):
        """Test routing by senior-related tags."""
        manager = ContentPillarManager()

        topic = SourcedTopic(
            id="test_6",
            title="Safety Tips",
            source_type="breaking",
            source_id="test",
            tags=["senior", "safety"],
        )

        pillar = manager.route_topic_to_pillar(topic)
        assert pillar == "senior_safety"

    def test_get_pillar_health(self):
        """Test getting pillar health metrics."""
        manager = ContentPillarManager()

        health = manager.get_pillar_health()

        assert len(health) == 7
        for slug, data in health.items():
            assert "name" in data
            assert "priority" in data
            assert "article_count" in data
            assert "current_ratio" in data
            assert "target_ratio" in data
            assert "health_score" in data
            assert "status" in data
            assert "needs_content" in data

    def test_health_status_labels(self):
        """Test health status label assignment."""
        manager = ContentPillarManager()

        assert manager._get_health_status(85) == "healthy"
        assert manager._get_health_status(65) == "moderate"
        assert manager._get_health_status(45) == "needs_attention"
        assert manager._get_health_status(30) == "critical"

    def test_get_rebalance_recommendations(self):
        """Test getting rebalance recommendations."""
        manager = ContentPillarManager()

        recs = manager.get_rebalance_recommendations()

        # Should be a list
        assert isinstance(recs, list)

        # All recs should have required fields
        for rec in recs:
            assert "pillar" in rec
            assert "pillar_name" in rec
            assert "priority" in rec
            assert "sources" in rec
            assert "action" in rec

    def test_get_persona_recommendations(self):
        """Test getting persona-specific recommendations."""
        manager = ContentPillarManager()

        recs = manager.get_persona_recommendations("citizen")

        assert "persona" in recs
        assert "preferred_pillars" in recs
        assert "content_preferences" in recs
        assert "sources_to_mine" in recs

        assert recs["persona"]["id"] == "citizen"
        assert recs["content_preferences"]["actionability"] == "high"

    def test_get_persona_recommendations_unknown(self):
        """Test getting recommendations for unknown persona."""
        manager = ContentPillarManager()

        recs = manager.get_persona_recommendations("unknown")

        assert "error" in recs

    def test_get_pillar_stats(self):
        """Test getting overall pillar statistics."""
        manager = ContentPillarManager()

        stats = manager.get_pillar_stats()

        assert stats["total_pillars"] == 7
        assert stats["total_personas"] == 5
        assert "healthy_pillars" in stats
        assert "needs_attention" in stats
        assert "pillar_health" in stats


class TestDefaultPillars:
    """Test default pillar configurations."""

    def test_pillar_count(self):
        """Test correct number of default pillars."""
        assert len(DEFAULT_PILLARS) == 7

    def test_pillar_slugs(self):
        """Test all expected pillar slugs exist."""
        expected = [
            "scam_watch",
            "economic_security",
            "personal_security",
            "senior_safety",
            "business_security",
            "sector_intelligence",
            "product_reviews",
        ]
        for slug in expected:
            assert slug in DEFAULT_PILLARS

    def test_pillar_target_mix_sums_to_one(self):
        """Test that target mixes sum to approximately 1.0."""
        total_mix = sum(p.target_mix for p in DEFAULT_PILLARS.values())
        assert abs(total_mix - 1.0) < 0.01

    def test_pillar_priorities_unique(self):
        """Test that pillar priorities are unique."""
        priorities = [p.priority for p in DEFAULT_PILLARS.values()]
        assert len(priorities) == len(set(priorities))

    def test_scam_watch_is_priority_one(self):
        """Test that scam_watch is the highest priority pillar."""
        scam_watch = DEFAULT_PILLARS["scam_watch"]
        assert scam_watch.priority == 1
        assert scam_watch.target_mix == 0.20


class TestDefaultPersonas:
    """Test default persona configurations."""

    def test_persona_count(self):
        """Test correct number of default personas."""
        assert len(DEFAULT_PERSONAS) == 5

    def test_persona_ids(self):
        """Test all expected persona IDs exist."""
        expected = ["citizen", "senior", "smb", "professional", "compliance"]
        for pid in expected:
            assert pid in DEFAULT_PERSONAS

    def test_citizen_persona(self):
        """Test citizen persona configuration."""
        citizen = DEFAULT_PERSONAS["citizen"]
        assert citizen.complexity_level == "basic"
        assert citizen.actionability_weight == 0.9
        assert "scam_watch" in citizen.preferred_pillars

    def test_senior_persona(self):
        """Test senior persona configuration."""
        senior = DEFAULT_PERSONAS["senior"]
        assert senior.complexity_level == "basic"
        assert senior.actionability_weight == 1.0
        assert "scam_watch" in senior.preferred_pillars
        assert "senior_safety" in senior.preferred_pillars

    def test_smb_persona(self):
        """Test SMB owner persona configuration."""
        smb = DEFAULT_PERSONAS["smb"]
        assert smb.complexity_level == "intermediate"
        assert "business_security" in smb.preferred_pillars

    def test_professional_persona(self):
        """Test professional persona configuration."""
        professional = DEFAULT_PERSONAS["professional"]
        assert professional.complexity_level == "advanced"
        assert "sector_intelligence" in professional.preferred_pillars

    def test_compliance_persona(self):
        """Test compliance officer persona configuration."""
        compliance = DEFAULT_PERSONAS["compliance"]
        assert compliance.complexity_level == "advanced"
        assert "sector_intelligence" in compliance.preferred_pillars
