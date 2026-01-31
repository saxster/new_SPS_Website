import os
import tempfile
import json
from datetime import datetime, timedelta
from skills.content_brain import ContentBrain


def test_content_brain_stats_types():
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        brain = ContentBrain(db_path=tmp.name)
        brain.add_topic_proposal(
            {
                "topic": "Test Guide",
                "target_audience": "CISOs",
                "gap_score": 90,
                "content_type": "Guide",
            }
        )
        brain.add_topic_proposal(
            {
                "topic": "Test Analysis",
                "target_audience": "Leaders",
                "gap_score": 80,
                "content_type": "Analysis",
            }
        )
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
                "issues": [],
            }

            brain.record_audit(
                content_id="blog/test-article",
                collection="blog",
                file_path="website/src/content/blog/test-article.md",
                title="Test Article",
                word_count=1500,
                audit_data=audit_data,
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
                audit_data={"quality_score": 70.0, "status": "review"},
            )

            # Second audit (update)
            brain.record_audit(
                content_id="blog/test-article",
                collection="blog",
                file_path="website/src/content/blog/test-article.md",
                title="Test Article Updated",
                word_count=1800,
                audit_data={"quality_score": 90.0, "status": "passed"},
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

            brain.record_audit(
                "blog/a1", "blog", "path/a1.md", "A1", 1000, {"status": "passed"}
            )
            brain.record_audit(
                "blog/a2", "blog", "path/a2.md", "A2", 1200, {"status": "passed"}
            )
            brain.record_audit(
                "qna/q1", "qna", "path/q1.md", "Q1", 500, {"status": "passed"}
            )

            blog_audits = brain.get_audits_by_collection("blog")
            assert len(blog_audits) == 2

            qna_audits = brain.get_audits_by_collection("qna")
            assert len(qna_audits) == 1
            os.unlink(tmp.name)

    def test_get_audits_by_status(self):
        """Test filtering audits by status."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            brain = ContentBrain(db_path=tmp.name)

            brain.record_audit(
                "blog/pass", "blog", "path/pass.md", "Pass", 1000, {"status": "passed"}
            )
            brain.record_audit(
                "blog/review",
                "blog",
                "path/review.md",
                "Review",
                1000,
                {"status": "review"},
            )
            brain.record_audit(
                "blog/fail", "blog", "path/fail.md", "Fail", 500, {"status": "failed"}
            )

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
            brain.record_audit(
                "blog/old", "blog", "path/old.md", "Old", 1000, {"status": "passed"}
            )

            cur = brain.conn.cursor()
            old_date = (datetime.now() - timedelta(days=60)).isoformat()
            cur.execute(
                "UPDATE content_audit SET last_audited = ? WHERE id = ?",
                (old_date, "blog/old"),
            )
            brain.conn.commit()

            brain.record_audit(
                "blog/new", "blog", "path/new.md", "New", 1000, {"status": "passed"}
            )

            stale = brain.get_stale_audits(days=30)
            assert len(stale) == 1
            assert stale[0]["id"] == "blog/old"
            os.unlink(tmp.name)

    def test_get_audit_summary(self):
        """Test getting audit summary statistics."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            brain = ContentBrain(db_path=tmp.name)

            brain.record_audit(
                "blog/a1",
                "blog",
                "p1",
                "A1",
                1000,
                {"status": "passed", "quality_score": 90},
            )
            brain.record_audit(
                "blog/a2",
                "blog",
                "p2",
                "A2",
                1000,
                {"status": "passed", "quality_score": 85},
            )
            brain.record_audit(
                "blog/a3",
                "blog",
                "p3",
                "A3",
                500,
                {"status": "failed", "quality_score": 50},
            )
            brain.record_audit(
                "qna/q1",
                "qna",
                "p4",
                "Q1",
                300,
                {"status": "review", "quality_score": 75},
            )

            summary = brain.get_audit_summary()

            assert summary["total"] == 4
            assert summary["passed"] == 2
            assert summary["failed"] == 1
            assert summary["review"] == 1
            assert "blog" in summary["by_collection"]
            assert summary["by_collection"]["blog"] == 3
            os.unlink(tmp.name)


class TestAutoPublish:
    """Tests for auto-publish functionality in ContentBrain."""

    def test_publish_article_stores_full_content(self):
        """Test that publish_article stores the full article body."""
        from shared.models import ArticleDraft, CouncilVerdict

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            brain = ContentBrain(db_path=tmp.name)

            draft = ArticleDraft(
                title="Test Auto-Publish Article",
                description="Testing auto-publish functionality.",
                category="Security",
                contentType="Guide",
                body="# Test Article\n\nThis is the full body content.",
                wordCount=500,
                sources=[
                    {"id": "S1", "title": "Test Source", "url": "https://example.com"}
                ],
            )

            verdict = CouncilVerdict(
                decision="PUBLISH",
                confidence=0.9,
                advocate_score=85,
                skeptic_score=80,
                guardian_score=75,
                average_score=80.0,
            )

            slug = "test-auto-publish-article"
            brain.publish_article(slug, draft, verdict)

            # Verify article was stored
            article = brain.get_published_article(slug)
            assert article is not None
            assert article["body"] == draft.body
            assert article["title"] == draft.title
            os.unlink(tmp.name)

    def test_get_published_article_returns_none_for_missing(self):
        """Test that get_published_article returns None for missing articles."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            brain = ContentBrain(db_path=tmp.name)
            result = brain.get_published_article("non-existent-slug")
            assert result is None
            os.unlink(tmp.name)

    def test_get_published_articles_returns_list(self):
        """Test that get_published_articles returns a list of articles."""
        from shared.models import ArticleDraft, CouncilVerdict

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            brain = ContentBrain(db_path=tmp.name)

            # Create and publish two articles
            for i in range(2):
                draft = ArticleDraft(
                    title=f"Test Article {i}",
                    description=f"Test description {i}",
                    category="Security",
                    contentType="Guide",
                    body=f"# Article {i}\n\nContent here.",
                    wordCount=300,
                    sources=[],
                )

                verdict = CouncilVerdict(
                    decision="PUBLISH",
                    confidence=0.85,
                    advocate_score=80,
                    skeptic_score=75,
                    guardian_score=70,
                    average_score=75.0,
                )

                brain.publish_article(f"test-article-{i}", draft, verdict)

            articles = brain.get_published_articles(limit=10)
            assert isinstance(articles, list)
            assert len(articles) >= 2
            os.unlink(tmp.name)

    def test_publish_article_stores_council_verdict(self):
        """Test that council verdict is stored with the article."""
        from shared.models import ArticleDraft, CouncilVerdict

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            brain = ContentBrain(db_path=tmp.name)

            draft = ArticleDraft(
                title="Council Verdict Test",
                description="Testing verdict storage.",
                category="Security",
                contentType="News",
                body="# News\n\nBreaking news content.",
                wordCount=200,
                sources=[],
            )

            verdict = CouncilVerdict(
                decision="PUBLISH",
                confidence=0.92,
                advocate_score=90,
                skeptic_score=85,
                guardian_score=88,
                average_score=87.67,
                debate_summary="Unanimous approval",
            )

            slug = "council-verdict-test"
            brain.publish_article(slug, draft, verdict)

            article = brain.get_published_article(slug)
            assert article is not None
            assert "council_verdict" in article
            assert article["council_verdict"]["decision"] == "PUBLISH"
            os.unlink(tmp.name)

    def test_publish_article_sets_published_via(self):
        """Test that published_via is set to 'auto' for auto-published articles."""
        from shared.models import ArticleDraft, CouncilVerdict

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            brain = ContentBrain(db_path=tmp.name)

            draft = ArticleDraft(
                title="Auto Via Test",
                description="Testing published_via field.",
                category="Security",
                contentType="Guide",
                body="# Guide\n\nContent.",
                wordCount=100,
                sources=[],
            )

            verdict = CouncilVerdict(
                decision="PUBLISH",
                confidence=0.8,
                advocate_score=75,
                skeptic_score=70,
                guardian_score=72,
                average_score=72.33,
            )

            slug = "auto-via-test"
            brain.publish_article(slug, draft, verdict)

            article = brain.get_published_article(slug)
            assert article["published_via"] == "auto"
            os.unlink(tmp.name)


class TestPipelineTracking:
    """Tests for pipeline profile tracking in ContentBrain."""

    def test_publish_article_with_pipeline_profile(self):
        """Test that publish_article stores pipeline profile info."""
        from shared.models import ArticleDraft, CouncilVerdict

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            brain = ContentBrain(db_path=tmp.name)

            draft = ArticleDraft(
                title="Breaking News Article",
                description="Fast-tracked breaking news.",
                category="News",
                contentType="News",
                body="# Breaking\n\nBreaking news content.",
                wordCount=300,
                sources=[],
            )

            verdict = CouncilVerdict(
                decision="PUBLISH",
                confidence=0.85,
                advocate_score=80,
                skeptic_score=75,
                guardian_score=78,
                average_score=77.67,
            )

            slug = "breaking-news-test"
            brain.publish_article(
                slug,
                draft,
                verdict,
                pipeline_profile="news_breaking",
                fast_tracked=True,
            )

            article = brain.get_published_article(slug)
            assert article is not None
            assert article.get("pipeline_profile") == "news_breaking"
            assert article.get("fast_tracked") == 1
            os.unlink(tmp.name)

    def test_publish_article_with_rollback_eligible(self):
        """Test that publish_article stores rollback eligibility."""
        from shared.models import ArticleDraft, CouncilVerdict
        from datetime import timedelta

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            brain = ContentBrain(db_path=tmp.name)

            draft = ArticleDraft(
                title="Rollback Eligible Article",
                description="Article with rollback window.",
                category="News",
                contentType="News",
                body="# News\n\nContent.",
                wordCount=200,
                sources=[],
            )

            verdict = CouncilVerdict(
                decision="PUBLISH",
                confidence=0.9,
                advocate_score=85,
                skeptic_score=80,
                guardian_score=82,
                average_score=82.33,
            )

            correction_expires = datetime.now() + timedelta(hours=24)
            slug = "rollback-eligible-test"
            brain.publish_article(
                slug,
                draft,
                verdict,
                pipeline_profile="news_breaking",
                fast_tracked=True,
                rollback_eligible=True,
                correction_window_expires=correction_expires,
            )

            article = brain.get_published_article(slug)
            assert article is not None
            assert article.get("rollback_eligible") == 1
            assert article.get("correction_window_expires") is not None
            os.unlink(tmp.name)

    def test_get_fast_tracked_articles(self):
        """Test getting list of fast-tracked articles."""
        from shared.models import ArticleDraft, CouncilVerdict
        from datetime import timedelta

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            brain = ContentBrain(db_path=tmp.name)

            # Create fast-tracked article
            draft1 = ArticleDraft(
                title="Fast-Tracked 1",
                description="Description",
                category="News",
                contentType="News",
                body="Content 1",
                wordCount=200,
                sources=[],
            )
            verdict = CouncilVerdict(
                decision="PUBLISH",
                confidence=0.85,
                advocate_score=80,
                skeptic_score=75,
                guardian_score=78,
                average_score=77.67,
            )
            brain.publish_article(
                "fast-tracked-1",
                draft1,
                verdict,
                pipeline_profile="news_breaking",
                fast_tracked=True,
                rollback_eligible=True,
                correction_window_expires=datetime.now() + timedelta(hours=20),
            )

            # Create normal article
            draft2 = ArticleDraft(
                title="Normal Article",
                description="Description",
                category="Security",
                contentType="Guide",
                body="Content 2",
                wordCount=500,
                sources=[],
            )
            brain.publish_article(
                "normal-article",
                draft2,
                verdict,
                pipeline_profile="research",
                fast_tracked=False,
            )

            # Get fast-tracked articles
            fast_tracked = brain.get_fast_tracked_articles()
            assert len(fast_tracked) == 1
            assert fast_tracked[0]["slug"] == "fast-tracked-1"
            os.unlink(tmp.name)

    def test_get_articles_in_correction_window(self):
        """Test getting articles still in correction window."""
        from shared.models import ArticleDraft, CouncilVerdict
        from datetime import timedelta

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            brain = ContentBrain(db_path=tmp.name)

            draft = ArticleDraft(
                title="In Window Article",
                description="Description",
                category="News",
                contentType="News",
                body="Content",
                wordCount=200,
                sources=[],
            )
            verdict = CouncilVerdict(
                decision="PUBLISH",
                confidence=0.85,
                advocate_score=80,
                skeptic_score=75,
                guardian_score=78,
                average_score=77.67,
            )

            # Article in correction window
            brain.publish_article(
                "in-window",
                draft,
                verdict,
                pipeline_profile="news_breaking",
                fast_tracked=True,
                rollback_eligible=True,
                correction_window_expires=datetime.now() + timedelta(hours=20),
            )

            # Article with expired window
            brain.publish_article(
                "expired-window",
                draft,
                verdict,
                pipeline_profile="news_breaking",
                fast_tracked=True,
                rollback_eligible=True,
                correction_window_expires=datetime.now() - timedelta(hours=1),
            )

            # Get articles in correction window
            in_window = brain.get_articles_in_correction_window()
            slugs = [a["slug"] for a in in_window]
            assert "in-window" in slugs
            assert "expired-window" not in slugs
            os.unlink(tmp.name)
