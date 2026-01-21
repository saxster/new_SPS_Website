import os
import tempfile
import json
from datetime import datetime, timedelta
from skills.content_brain import ContentBrain

def test_content_brain_stats_types():
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        brain = ContentBrain(db_path=tmp.name)
        brain.add_topic_proposal({
            "topic": "Test Guide",
            "target_audience": "CISOs",
            "gap_score": 90,
            "content_type": "Guide"
        })
        brain.add_topic_proposal({
            "topic": "Test Analysis",
            "target_audience": "Leaders",
            "gap_score": 80,
            "content_type": "Analysis"
        })
        stats = brain.get_stats()
        assert "types" in stats
        assert stats["types"].get("Guide", 0) >= 1
        assert stats["types"].get("Analysis", 0) >= 1


class TestContentAudit:
    """Tests for content audit functionality in ContentBrain."""

    def test_record_audit_creates_entry(self):
        """Test that record_audit creates a new audit entry."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            brain = ContentBrain(db_path=tmp.name)

            audit_data = {
                "quality_score": 85.0,
                "fact_check_score": 90.0,
                "consensus_level": "high",
                "status": "passed",
                "issues": []
            }

            brain.record_audit(
                content_id="blog/test-article",
                collection="blog",
                file_path="website/src/content/blog/test-article.md",
                title="Test Article",
                word_count=1500,
                audit_data=audit_data
            )

            result = brain.get_audit_by_id("blog/test-article")
            assert result is not None
            assert result["collection"] == "blog"
            assert result["quality_score"] == 85.0
            assert result["fact_check_score"] == 90.0
            assert result["audit_status"] == "passed"
            os.unlink(tmp.name)

    def test_record_audit_updates_existing(self):
        """Test that record_audit updates an existing audit entry."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            brain = ContentBrain(db_path=tmp.name)

            # First audit
            brain.record_audit(
                content_id="blog/test-article",
                collection="blog",
                file_path="website/src/content/blog/test-article.md",
                title="Test Article",
                word_count=1500,
                audit_data={"quality_score": 70.0, "status": "review"}
            )

            # Second audit (update)
            brain.record_audit(
                content_id="blog/test-article",
                collection="blog",
                file_path="website/src/content/blog/test-article.md",
                title="Test Article Updated",
                word_count=1800,
                audit_data={"quality_score": 90.0, "status": "passed"}
            )

            result = brain.get_audit_by_id("blog/test-article")
            assert result["quality_score"] == 90.0
            assert result["audit_status"] == "passed"
            assert result["word_count"] == 1800
            os.unlink(tmp.name)

    def test_get_audits_by_collection(self):
        """Test filtering audits by collection."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            brain = ContentBrain(db_path=tmp.name)

            brain.record_audit("blog/a1", "blog", "path/a1.md", "A1", 1000, {"status": "passed"})
            brain.record_audit("blog/a2", "blog", "path/a2.md", "A2", 1200, {"status": "passed"})
            brain.record_audit("qna/q1", "qna", "path/q1.md", "Q1", 500, {"status": "passed"})

            blog_audits = brain.get_audits_by_collection("blog")
            assert len(blog_audits) == 2

            qna_audits = brain.get_audits_by_collection("qna")
            assert len(qna_audits) == 1
            os.unlink(tmp.name)

    def test_get_audits_by_status(self):
        """Test filtering audits by status."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            brain = ContentBrain(db_path=tmp.name)

            brain.record_audit("blog/pass", "blog", "path/pass.md", "Pass", 1000, {"status": "passed"})
            brain.record_audit("blog/review", "blog", "path/review.md", "Review", 1000, {"status": "review"})
            brain.record_audit("blog/fail", "blog", "path/fail.md", "Fail", 500, {"status": "failed"})

            passed = brain.get_audits_by_status("passed")
            assert len(passed) == 1
            assert passed[0]["id"] == "blog/pass"

            failed = brain.get_audits_by_status("failed")
            assert len(failed) == 1
            os.unlink(tmp.name)

    def test_get_stale_audits(self):
        """Test finding content not audited in N days."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            brain = ContentBrain(db_path=tmp.name)

            # Record audit, then manually backdate it
            brain.record_audit("blog/old", "blog", "path/old.md", "Old", 1000, {"status": "passed"})

            cur = brain.conn.cursor()
            old_date = (datetime.now() - timedelta(days=60)).isoformat()
            cur.execute("UPDATE content_audit SET last_audited = ? WHERE id = ?", (old_date, "blog/old"))
            brain.conn.commit()

            brain.record_audit("blog/new", "blog", "path/new.md", "New", 1000, {"status": "passed"})

            stale = brain.get_stale_audits(days=30)
            assert len(stale) == 1
            assert stale[0]["id"] == "blog/old"
            os.unlink(tmp.name)

    def test_get_audit_summary(self):
        """Test getting audit summary statistics."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            brain = ContentBrain(db_path=tmp.name)

            brain.record_audit("blog/a1", "blog", "p1", "A1", 1000, {"status": "passed", "quality_score": 90})
            brain.record_audit("blog/a2", "blog", "p2", "A2", 1000, {"status": "passed", "quality_score": 85})
            brain.record_audit("blog/a3", "blog", "p3", "A3", 500, {"status": "failed", "quality_score": 50})
            brain.record_audit("qna/q1", "qna", "p4", "Q1", 300, {"status": "review", "quality_score": 75})

            summary = brain.get_audit_summary()

            assert summary["total"] == 4
            assert summary["passed"] == 2
            assert summary["failed"] == 1
            assert summary["review"] == 1
            assert "blog" in summary["by_collection"]
            assert summary["by_collection"]["blog"] == 3
            os.unlink(tmp.name)
