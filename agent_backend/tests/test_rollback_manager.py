"""
Tests for RollbackManager - Handles corrections and retractions for fast-tracked articles.
TDD First - Tests written before implementation.
"""

import pytest
import tempfile
import os
from datetime import datetime, timedelta


class TestRollbackManagerInit:
    """Tests for RollbackManager initialization."""

    def test_rollback_manager_initializes(self):
        """Test that RollbackManager initializes correctly."""
        from skills.rollback_manager import RollbackManager
        from skills.content_brain import ContentBrain

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            brain = ContentBrain(db_path=db_path)
            manager = RollbackManager(brain=brain)

            assert manager is not None
            assert manager.brain is not None
        finally:
            os.unlink(db_path)


class TestCorrectionRecording:
    """Tests for recording corrections."""

    def test_record_minor_correction(self):
        """Test recording a minor correction (typo, formatting)."""
        from skills.rollback_manager import RollbackManager
        from skills.content_brain import ContentBrain

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            brain = ContentBrain(db_path=db_path)
            manager = RollbackManager(brain=brain)

            # Record a minor correction
            result = manager.record_correction(
                article_slug="test-article",
                correction_type="minor",
                reason="Fixed typo in headline",
            )

            assert result is True

            # Verify correction was recorded
            corrections = manager.get_corrections("test-article")
            assert len(corrections) == 1
            assert corrections[0]["correction_type"] == "minor"
            assert "typo" in corrections[0]["reason"].lower()
        finally:
            os.unlink(db_path)

    def test_record_major_correction(self):
        """Test recording a major correction (factual error)."""
        from skills.rollback_manager import RollbackManager
        from skills.content_brain import ContentBrain

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            brain = ContentBrain(db_path=db_path)
            manager = RollbackManager(brain=brain)

            result = manager.record_correction(
                article_slug="test-article",
                correction_type="major",
                reason="Corrected incorrect statistics from initial report",
            )

            assert result is True

            corrections = manager.get_corrections("test-article")
            assert len(corrections) == 1
            assert corrections[0]["correction_type"] == "major"
        finally:
            os.unlink(db_path)

    def test_record_retraction(self):
        """Test recording a full retraction."""
        from skills.rollback_manager import RollbackManager
        from skills.content_brain import ContentBrain

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            brain = ContentBrain(db_path=db_path)
            manager = RollbackManager(brain=brain)

            result = manager.record_correction(
                article_slug="test-article",
                correction_type="retraction",
                reason="Original report was based on unverified information",
            )

            assert result is True

            corrections = manager.get_corrections("test-article")
            assert len(corrections) == 1
            assert corrections[0]["correction_type"] == "retraction"
        finally:
            os.unlink(db_path)

    def test_multiple_corrections_on_same_article(self):
        """Test recording multiple corrections on the same article."""
        from skills.rollback_manager import RollbackManager
        from skills.content_brain import ContentBrain

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            brain = ContentBrain(db_path=db_path)
            manager = RollbackManager(brain=brain)

            # Record first correction
            manager.record_correction(
                article_slug="test-article",
                correction_type="minor",
                reason="Fixed typo",
            )

            # Record second correction
            manager.record_correction(
                article_slug="test-article",
                correction_type="major",
                reason="Updated statistics",
            )

            corrections = manager.get_corrections("test-article")
            assert len(corrections) == 2
        finally:
            os.unlink(db_path)


class TestCorrectionWindowCheck:
    """Tests for checking if article is within correction window."""

    def test_article_in_correction_window(self):
        """Test that recently published article is in correction window."""
        from skills.rollback_manager import RollbackManager
        from skills.content_brain import ContentBrain

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            brain = ContentBrain(db_path=db_path)
            manager = RollbackManager(brain=brain)

            # Simulate article published 1 hour ago with 24-hour window
            window_expires = datetime.now() + timedelta(hours=23)

            is_in_window = manager.is_in_correction_window(
                correction_window_expires=window_expires
            )

            assert is_in_window is True
        finally:
            os.unlink(db_path)

    def test_article_outside_correction_window(self):
        """Test that old article is outside correction window."""
        from skills.rollback_manager import RollbackManager
        from skills.content_brain import ContentBrain

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            brain = ContentBrain(db_path=db_path)
            manager = RollbackManager(brain=brain)

            # Simulate article with expired correction window
            window_expires = datetime.now() - timedelta(hours=1)

            is_in_window = manager.is_in_correction_window(
                correction_window_expires=window_expires
            )

            assert is_in_window is False
        finally:
            os.unlink(db_path)

    def test_no_correction_window(self):
        """Test that article with no correction window returns False."""
        from skills.rollback_manager import RollbackManager
        from skills.content_brain import ContentBrain

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            brain = ContentBrain(db_path=db_path)
            manager = RollbackManager(brain=brain)

            is_in_window = manager.is_in_correction_window(
                correction_window_expires=None
            )

            assert is_in_window is False
        finally:
            os.unlink(db_path)


class TestRollbackEligibility:
    """Tests for rollback eligibility checking."""

    def test_fast_tracked_article_is_rollback_eligible(self):
        """Test that fast-tracked article is eligible for rollback."""
        from skills.rollback_manager import RollbackManager
        from skills.content_brain import ContentBrain

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            brain = ContentBrain(db_path=db_path)
            manager = RollbackManager(brain=brain)

            is_eligible = manager.check_rollback_eligible(
                rollback_eligible=True,
                correction_window_expires=datetime.now() + timedelta(hours=20),
            )

            assert is_eligible is True
        finally:
            os.unlink(db_path)

    def test_non_fast_tracked_article_not_rollback_eligible(self):
        """Test that non-fast-tracked article is not eligible for rollback."""
        from skills.rollback_manager import RollbackManager
        from skills.content_brain import ContentBrain

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            brain = ContentBrain(db_path=db_path)
            manager = RollbackManager(brain=brain)

            is_eligible = manager.check_rollback_eligible(
                rollback_eligible=False,
                correction_window_expires=datetime.now() + timedelta(hours=20),
            )

            assert is_eligible is False
        finally:
            os.unlink(db_path)

    def test_expired_window_not_rollback_eligible(self):
        """Test that expired correction window makes article ineligible."""
        from skills.rollback_manager import RollbackManager
        from skills.content_brain import ContentBrain

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            brain = ContentBrain(db_path=db_path)
            manager = RollbackManager(brain=brain)

            is_eligible = manager.check_rollback_eligible(
                rollback_eligible=True,
                correction_window_expires=datetime.now() - timedelta(hours=1),
            )

            assert is_eligible is False
        finally:
            os.unlink(db_path)


class TestCorrectionStatus:
    """Tests for article correction status management."""

    def test_update_correction_status(self):
        """Test updating article correction status."""
        from skills.rollback_manager import RollbackManager
        from skills.content_brain import ContentBrain

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            brain = ContentBrain(db_path=db_path)
            manager = RollbackManager(brain=brain)

            # This test assumes the article exists in DB
            # For now, just test the method exists and returns
            result = manager.update_article_correction_status(
                article_slug="test-article",
                correction_status="corrected",
            )

            # Method should complete without error
            assert result in [True, False]
        finally:
            os.unlink(db_path)

    def test_get_pending_corrections(self):
        """Test getting articles with pending corrections."""
        from skills.rollback_manager import RollbackManager
        from skills.content_brain import ContentBrain

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            brain = ContentBrain(db_path=db_path)
            manager = RollbackManager(brain=brain)

            # Record some corrections
            manager.record_correction(
                article_slug="article-1",
                correction_type="minor",
                reason="Test correction 1",
            )
            manager.record_correction(
                article_slug="article-2",
                correction_type="major",
                reason="Test correction 2",
            )

            # Get all corrections
            all_corrections = manager.get_all_corrections()

            assert len(all_corrections) >= 2
        finally:
            os.unlink(db_path)


class TestContradictionDetection:
    """Tests for contradiction detection (stub for future implementation)."""

    def test_check_for_contradictions_returns_result(self):
        """Test that contradiction check returns a result."""
        from skills.rollback_manager import RollbackManager
        from skills.content_brain import ContentBrain

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            brain = ContentBrain(db_path=db_path)
            manager = RollbackManager(brain=brain)

            # Check for contradictions (stub implementation)
            result = manager.check_for_contradictions(
                article_slug="test-article",
                original_claims=["Claim 1", "Claim 2"],
            )

            # Should return a dict with contradiction info
            assert isinstance(result, dict)
            assert "has_contradiction" in result
            assert "confidence" in result
        finally:
            os.unlink(db_path)
