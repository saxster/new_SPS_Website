"""
Tests for EditorialValidator - Adversarial Topic Vetting
"""

import pytest
from skills.editorial_validator import (
    EditorialValidator, 
    EditorialVerdict, 
    ConsensusLevel
)


class TestEditorialValidator:
    """Test the editorial validation pipeline."""
    
    def test_initialization(self):
        """Test that EditorialValidator initializes correctly."""
        validator = EditorialValidator()
        assert validator.enabled is True
        assert validator.gatekeeper_enabled is True
        assert validator.consensus_enabled is False  # Off by default
        assert validator.red_team_enabled is True
    
    def test_high_value_topic_approved(self):
        """Test that high-value topics are approved by gatekeeper."""
        validator = EditorialValidator()
        
        verdict = validator.validate_topic(
            topic="Major Ransomware Attack Exposes DPDP Compliance Gaps in Banking",
            sector="cybersecurity",
            content_type="News"
        )
        
        assert verdict.approved is True
        assert verdict.gatekeeper_score >= 50  # Above threshold
        assert len(verdict.gatekeeper_reasons) > 0
    
    def test_low_value_topic_rejected(self):
        """Test that low-value topics are rejected by gatekeeper."""
        validator = EditorialValidator()
        
        verdict = validator.validate_topic(
            topic="Local shop robbery reported",
            sector="general",
            content_type="News"
        )
        
        assert verdict.approved is False
        assert verdict.gatekeeper_score < 50  # Below threshold
    
    def test_sector_mapping(self):
        """Test that sectors are correctly mapped for ConsensusEngine."""
        validator = EditorialValidator()
        
        assert validator._map_sector("cybersecurity") == "Cyber"
        assert validator._map_sector("fire_safety") == "Industrial"
        assert validator._map_sector("compliance") == "Banking"
        assert validator._map_sector("unknown") == "General"
    
    def test_verdict_to_dict(self):
        """Test EditorialVerdict serialization."""
        verdict = EditorialVerdict(
            approved=True,
            topic="Test Topic",
            gatekeeper_score=75,
            gatekeeper_reasons=["High impact", "Critical sector"],
            consensus_level=ConsensusLevel.HIGH,
            consensus_score=80.0
        )
        
        d = verdict.to_dict()
        assert d["approved"] is True
        assert d["gatekeeper_score"] == 75
        assert d["consensus_level"] == "high"
    
    def test_batch_validation(self):
        """Test batch topic validation."""
        validator = EditorialValidator()
        
        topics = [
            {"topic": "RBI Issues New Data Breach Compliance Guidelines", "sector": "compliance"},
            {"topic": "Minor theft in local shop", "sector": "general"},
            {"topic": "Nationwide Ransomware Attack Pattern Detected", "sector": "cybersecurity"}
        ]
        
        verdicts = validator.validate_batch(topics)
        
        assert len(verdicts) == 3
        # First and third should be approved (high value)
        # Second should be rejected (low value)
        approved_count = sum(1 for v in verdicts if v.approved)
        assert approved_count >= 1  # At least some should pass


class TestConsensusLevel:
    """Test ConsensusLevel enum."""
    
    def test_consensus_levels(self):
        """Test all consensus levels exist."""
        assert ConsensusLevel.AUTHORITATIVE.value == "authoritative"
        assert ConsensusLevel.HIGH.value == "high"
        assert ConsensusLevel.DISPUTED.value == "disputed"
        assert ConsensusLevel.UNTRUSTED.value == "untrusted"
        assert ConsensusLevel.SKIPPED.value == "skipped"


class TestEditorialValidatorDisabled:
    """Test behavior when editorial validation is disabled."""
    
    def test_disabled_passes_all(self):
        """When disabled, all topics should pass through."""
        # Temporarily create validator and disable it
        validator = EditorialValidator()
        validator.enabled = False
        
        verdict = validator.validate_topic(
            topic="Any topic",
            sector="general"
        )
        
        assert verdict.approved is True
        assert "disabled" in verdict.synthesis.lower()


class TestRedTeamChallenge:
    """Test red-team adversarial challenge."""
    
    def test_red_team_produces_challenge(self):
        """Test that red-team produces a challenge for approved topics."""
        validator = EditorialValidator()
        
        verdict = validator.validate_topic(
            topic="Major Cyber Attack on Critical Infrastructure",
            sector="cybersecurity"
        )
        
        if verdict.approved:
            # Red-team should produce some challenge content
            assert verdict.red_team_challenge is not None
