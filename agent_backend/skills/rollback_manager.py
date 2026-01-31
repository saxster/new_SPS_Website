"""
Rollback Manager - Handles corrections and retractions for fast-tracked articles.

Monitors fast-tracked articles during correction window:
- Periodically checks for contradicting information
- Auto-retracts if contradiction confidence > 90%
- Issues correction notices for confirmed errors
"""

import os
import sys
from datetime import datetime
from typing import Dict, List, Optional

# Allow running from repo root without PYTHONPATH
AGENT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if AGENT_ROOT not in sys.path:
    sys.path.insert(0, AGENT_ROOT)

from shared.logger import get_logger
from skills.content_brain import ContentBrain

logger = get_logger("RollbackManager")


class RollbackManager:
    """
    Manages corrections and retractions for fast-tracked articles.

    Provides:
    - Correction recording (minor, major, retraction)
    - Correction window tracking
    - Rollback eligibility checking
    - Contradiction detection (stub for future LLM integration)
    """

    def __init__(self, brain: Optional[ContentBrain] = None):
        self.brain = brain or ContentBrain()
        self._ensure_corrections_table()

    def _ensure_corrections_table(self):
        """Ensure the article_corrections table exists."""
        cur = self.brain.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS article_corrections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_slug TEXT NOT NULL,
                correction_type TEXT NOT NULL,
                reason TEXT NOT NULL,
                issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.brain.conn.commit()

    def record_correction(
        self,
        article_slug: str,
        correction_type: str,
        reason: str,
    ) -> bool:
        """
        Record a correction for an article.

        Args:
            article_slug: The article's slug
            correction_type: "minor", "major", or "retraction"
            reason: Explanation for the correction

        Returns:
            True if recorded successfully
        """
        if correction_type not in ["minor", "major", "retraction"]:
            logger.warning(
                "invalid_correction_type",
                correction_type=correction_type,
                article_slug=article_slug,
            )
            return False

        try:
            cur = self.brain.conn.cursor()
            cur.execute(
                """
                INSERT INTO article_corrections (article_slug, correction_type, reason)
                VALUES (?, ?, ?)
                """,
                (article_slug, correction_type, reason),
            )
            self.brain.conn.commit()

            logger.info(
                "correction_recorded",
                article_slug=article_slug,
                correction_type=correction_type,
            )
            return True

        except Exception as e:
            logger.error(
                "correction_record_error",
                article_slug=article_slug,
                error=str(e),
            )
            return False

    def get_corrections(self, article_slug: str) -> List[Dict]:
        """
        Get all corrections for an article.

        Args:
            article_slug: The article's slug

        Returns:
            List of correction records
        """
        cur = self.brain.conn.cursor()
        cur.execute(
            """
            SELECT id, article_slug, correction_type, reason, issued_at
            FROM article_corrections
            WHERE article_slug = ?
            ORDER BY issued_at DESC
            """,
            (article_slug,),
        )
        return [dict(row) for row in cur.fetchall()]

    def get_all_corrections(self) -> List[Dict]:
        """
        Get all corrections across all articles.

        Returns:
            List of all correction records
        """
        cur = self.brain.conn.cursor()
        cur.execute("""
            SELECT id, article_slug, correction_type, reason, issued_at
            FROM article_corrections
            ORDER BY issued_at DESC
        """)
        return [dict(row) for row in cur.fetchall()]

    def is_in_correction_window(
        self, correction_window_expires: Optional[datetime]
    ) -> bool:
        """
        Check if article is within its correction window.

        Args:
            correction_window_expires: When the correction window expires

        Returns:
            True if within correction window
        """
        if correction_window_expires is None:
            return False

        now = datetime.now()

        # Handle timezone-aware datetime
        if correction_window_expires.tzinfo is not None:
            correction_window_expires = correction_window_expires.replace(tzinfo=None)

        return now < correction_window_expires

    def check_rollback_eligible(
        self,
        rollback_eligible: bool,
        correction_window_expires: Optional[datetime],
    ) -> bool:
        """
        Check if an article is eligible for rollback.

        An article is eligible if:
        1. It was marked as rollback_eligible (fast-tracked)
        2. It's still within the correction window

        Args:
            rollback_eligible: Whether article was marked rollback eligible
            correction_window_expires: When the correction window expires

        Returns:
            True if eligible for rollback
        """
        if not rollback_eligible:
            return False

        return self.is_in_correction_window(correction_window_expires)

    def update_article_correction_status(
        self,
        article_slug: str,
        correction_status: str,
    ) -> bool:
        """
        Update the correction status of an article.

        Args:
            article_slug: The article's slug
            correction_status: New status ("none", "corrected", "retracted")

        Returns:
            True if updated successfully
        """
        if correction_status not in ["none", "corrected", "retracted"]:
            logger.warning(
                "invalid_correction_status",
                correction_status=correction_status,
                article_slug=article_slug,
            )
            return False

        try:
            # Ensure the column exists
            cur = self.brain.conn.cursor()
            try:
                cur.execute(
                    "ALTER TABLE articles ADD COLUMN correction_status TEXT DEFAULT 'none'"
                )
            except Exception:
                pass  # Column likely exists

            cur.execute(
                """
                UPDATE articles
                SET correction_status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE slug = ?
                """,
                (correction_status, article_slug),
            )
            self.brain.conn.commit()

            logger.info(
                "correction_status_updated",
                article_slug=article_slug,
                correction_status=correction_status,
            )
            return True

        except Exception as e:
            logger.error(
                "correction_status_update_error",
                article_slug=article_slug,
                error=str(e),
            )
            return False

    def check_for_contradictions(
        self,
        article_slug: str,
        original_claims: List[str],
    ) -> Dict:
        """
        Check if there are contradicting reports for an article's claims.

        This is a stub for future LLM-based contradiction detection.

        Args:
            article_slug: The article's slug
            original_claims: List of claims from the original article

        Returns:
            Dict with has_contradiction, confidence, details
        """
        # Stub implementation - will be enhanced with LLM integration
        logger.debug(
            "checking_contradictions",
            article_slug=article_slug,
            claim_count=len(original_claims),
        )

        # For now, return no contradictions
        return {
            "has_contradiction": False,
            "confidence": 0.0,
            "contradicting_sources": [],
            "details": "Contradiction detection not yet implemented",
        }

    def process_auto_retractions(self) -> List[str]:
        """
        Process articles eligible for auto-retraction.

        Checks all fast-tracked articles within correction window
        for contradictions and auto-retracts if confidence > 90%.

        Returns:
            List of article slugs that were retracted
        """
        retracted = []

        # This would query for fast-tracked articles in correction window
        # and check each for contradictions
        # For now, return empty list as contradiction detection is not implemented

        logger.info("auto_retraction_check_complete", retracted_count=len(retracted))
        return retracted


if __name__ == "__main__":
    # Quick test
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        brain = ContentBrain(db_path=db_path)
        manager = RollbackManager(brain=brain)

        # Test recording corrections
        print("Recording corrections...")
        manager.record_correction(
            article_slug="test-article-1",
            correction_type="minor",
            reason="Fixed typo in headline",
        )
        manager.record_correction(
            article_slug="test-article-1",
            correction_type="major",
            reason="Updated incorrect statistics",
        )

        # Get corrections
        corrections = manager.get_corrections("test-article-1")
        print(f"Corrections for test-article-1: {len(corrections)}")
        for c in corrections:
            print(f"  - {c['correction_type']}: {c['reason']}")

        # Test correction window
        from datetime import timedelta

        window_expires = datetime.now() + timedelta(hours=23)
        print(
            f"\nIn correction window: {manager.is_in_correction_window(window_expires)}"
        )

        expired_window = datetime.now() - timedelta(hours=1)
        print(f"In expired window: {manager.is_in_correction_window(expired_window)}")

    finally:
        os.unlink(db_path)
