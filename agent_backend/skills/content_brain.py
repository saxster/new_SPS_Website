"""
Content Brain 🧠 V2
The persistent memory for the Autonomous Newsroom.
Tracks Topics through their lifecycle.
"""

import sqlite3
import hashlib
import json
from typing import Dict, Optional, List
from datetime import datetime

from config.manager import config
from shared.logger import get_logger

logger = get_logger("ContentBrain")


class ContentBrain:
    """
    Persistent storage for the Autonomous Newsroom.
    Single Source of Truth for Topic and Article Lifecycle.
    """

    def __init__(self, db_path: Optional[str] = None):
        # Allow injection of db_path for testing
        self.db_path = db_path or config.get("database.path", ".agent/content_brain.db")
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        cur = self.conn.cursor()

        # Topics Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS topics (
                id TEXT PRIMARY KEY,
                topic TEXT NOT NULL,
                target_audience TEXT,
                gap_score INTEGER,
                content_type TEXT DEFAULT 'General',
                status TEXT DEFAULT 'PROPOSED',
                rejection_reason TEXT,
                revision_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Articles Metadata Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                slug TEXT PRIMARY KEY,
                topic_id TEXT,
                title TEXT,
                content_type TEXT,
                word_count INTEGER,
                quality_score REAL,
                source_count INTEGER,
                regulation_count INTEGER,
                image_path TEXT,
                sources JSON,
                revision INTEGER DEFAULT 1,
                status TEXT DEFAULT 'DRAFT',
                scheduled_date DATE,
                published_date TIMESTAMP,
                content_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(topic_id) REFERENCES topics(id)
            )
        """)

        # Revision History Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS article_revisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_slug TEXT NOT NULL,
                revision INTEGER NOT NULL,
                content_snapshot JSON,
                quality_score REAL,
                review_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(article_slug) REFERENCES articles(slug)
            )
        """)

        # Content Audit Table - tracks fact-checking results
        cur.execute("""
            CREATE TABLE IF NOT EXISTS content_audit (
                id TEXT PRIMARY KEY,
                collection TEXT NOT NULL,
                file_path TEXT NOT NULL,
                title TEXT,
                word_count INTEGER,
                quality_score REAL,
                fact_check_score REAL,
                consensus_level TEXT,
                audit_status TEXT DEFAULT 'pending',
                issues_json TEXT,
                last_audited TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ─────────────────────────────────────────────────────────────────────────
        # User Authentication & Dashboard Tables
        # ─────────────────────────────────────────────────────────────────────────

        # Users Table - links Clerk auth to local data
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                clerk_id TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                display_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # User Sector Preferences - which sectors user cares about
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_sector_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                sector_slug TEXT NOT NULL,
                priority INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, sector_slug)
            )
        """)

        # User Bookmarks - saved articles
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_bookmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                article_slug TEXT NOT NULL,
                article_title TEXT,
                saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, article_slug)
            )
        """)

        # Expert Conversations - chat sessions with AI expert
        cur.execute("""
            CREATE TABLE IF NOT EXISTS expert_conversations (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                session_id TEXT,
                title TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Expert Messages - individual messages in conversations
        cur.execute("""
            CREATE TABLE IF NOT EXISTS expert_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL REFERENCES expert_conversations(id) ON DELETE CASCADE,
                sender TEXT NOT NULL CHECK (sender IN ('user', 'expert')),
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ─────────────────────────────────────────────────────────────────────────
        # Alert Notification System Tables
        # ─────────────────────────────────────────────────────────────────────────

        # Alert Subscribers - users who want to receive alerts
        cur.execute("""
            CREATE TABLE IF NOT EXISTS alert_subscribers (
                id TEXT PRIMARY KEY,
                user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
                email TEXT,
                phone TEXT,
                frequency TEXT DEFAULT 'instant' CHECK (frequency IN ('instant', 'daily', 'weekly')),
                channels TEXT DEFAULT 'email',
                verified INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Alert Sector Subscriptions - which sectors a subscriber follows
        cur.execute("""
            CREATE TABLE IF NOT EXISTS alert_sector_subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subscriber_id TEXT NOT NULL REFERENCES alert_subscribers(id) ON DELETE CASCADE,
                sector_slug TEXT NOT NULL,
                severity_threshold TEXT DEFAULT 'high' CHECK (severity_threshold IN ('low', 'medium', 'high', 'critical')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(subscriber_id, sector_slug)
            )
        """)

        # Alert Queue - pending alerts to be sent
        cur.execute("""
            CREATE TABLE IF NOT EXISTS alert_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subscriber_id TEXT NOT NULL REFERENCES alert_subscribers(id) ON DELETE CASCADE,
                incident_id TEXT NOT NULL,
                incident_title TEXT,
                incident_sector TEXT,
                incident_severity TEXT,
                channel TEXT NOT NULL CHECK (channel IN ('email', 'sms', 'push')),
                status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'failed', 'cancelled')),
                scheduled_for TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Alert Log - history of sent alerts
        cur.execute("""
            CREATE TABLE IF NOT EXISTS alert_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subscriber_id TEXT NOT NULL,
                incident_id TEXT NOT NULL,
                channel TEXT NOT NULL,
                status TEXT NOT NULL,
                external_id TEXT,
                error_message TEXT,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Incidents Table - Source of Truth for Security Map
        cur.execute("""
            CREATE TABLE IF NOT EXISTS incidents (
                id TEXT PRIMARY KEY,
                title TEXT,
                date TEXT,
                type TEXT,
                severity TEXT,
                location_lat REAL,
                location_lng REAL,
                city TEXT,
                summary TEXT,
                url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ─────────────────────────────────────────────────────────────────────────
        # Topic Sourcing System Tables
        # ─────────────────────────────────────────────────────────────────────────

        # Sourced Topics - topics discovered from external sources
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sourced_topics (
                id TEXT PRIMARY KEY,
                topic_id TEXT REFERENCES topics(id),
                source_type TEXT NOT NULL,
                source_id TEXT,
                source_url TEXT,
                urgency TEXT DEFAULT 'medium',
                timeliness_score INTEGER,
                authority_score INTEGER,
                gap_score INTEGER,
                overall_score REAL,
                evidence_json TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Calendar Events - recurring and one-time events
        cur.execute("""
            CREATE TABLE IF NOT EXISTS calendar_events (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                event_type TEXT NOT NULL,
                event_date DATE NOT NULL,
                recurring TEXT,
                source TEXT,
                content_type TEXT,
                priority TEXT DEFAULT 'medium',
                lead_days INTEGER DEFAULT 7,
                tags TEXT,
                description TEXT,
                last_triggered TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Regulatory Document Tracking
        cur.execute("""
            CREATE TABLE IF NOT EXISTS regulatory_tracking (
                id TEXT PRIMARY KEY,
                regulator TEXT NOT NULL,
                document_type TEXT,
                title TEXT,
                url TEXT,
                published_date DATE,
                compliance_deadline DATE,
                status TEXT DEFAULT 'new',
                topic_id TEXT REFERENCES topics(id),
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ─────────────────────────────────────────────────────────────────────────
        # Scam Intelligence Tables (Reader-Centric)
        # ─────────────────────────────────────────────────────────────────────────

        # Scam tracking for real-time fraud intelligence
        cur.execute("""
            CREATE TABLE IF NOT EXISTS scam_intelligence (
                id TEXT PRIMARY KEY,
                scam_type TEXT NOT NULL,
                title TEXT,
                description TEXT,
                affected_regions TEXT,
                target_demographics TEXT,
                reported_losses_inr INTEGER,
                status TEXT DEFAULT 'active',
                prevention_tips TEXT,
                source_url TEXT,
                source_credibility INTEGER,
                first_seen TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Content pillar health tracking
        cur.execute("""
            CREATE TABLE IF NOT EXISTS content_pillars (
                pillar_slug TEXT PRIMARY KEY,
                name TEXT,
                article_count INTEGER DEFAULT 0,
                target_ratio REAL DEFAULT 0.1,
                current_ratio REAL DEFAULT 0.0,
                health_score INTEGER DEFAULT 50,
                last_calculated TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Product reviews for consumer intelligence
        cur.execute("""
            CREATE TABLE IF NOT EXISTS product_reviews (
                id TEXT PRIMARY KEY,
                product_name TEXT NOT NULL,
                category TEXT,
                brand TEXT,
                overall_rating REAL,
                certification_status TEXT,
                price_range TEXT,
                india_available INTEGER DEFAULT 1,
                pros TEXT,
                cons TEXT,
                our_verdict TEXT,
                source_url TEXT,
                reviewed_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self._run_migrations(cur)
        self.conn.commit()

    def _run_migrations(self, cur):
        """Minimal defensive column additions."""
        migrations = [
            ("topics", "content_type", "TEXT DEFAULT 'General'"),
            ("topics", "rejection_reason", "TEXT"),
            ("topics", "revision_count", "INTEGER DEFAULT 0"),
            ("articles", "quality_score", "REAL"),
            ("articles", "sources", "JSON"),
            ("articles", "content_path", "TEXT"),
        ]
        for table, col, type_def in migrations:
            self._safe_add_column(cur, table, col, type_def)

    def _safe_add_column(self, cur, table: str, col: str, type_def: str):
        """Safely adds a column if it doesn't exist, validating identifiers."""
        # Simple validation to prevent SQL injection via identifiers
        if not table.replace("_", "").isalnum():
            logger.error(f"Invalid table name in migration: {table}")
            return
        if not col.replace("_", "").isalnum():
            logger.error(f"Invalid column name in migration: {col}")
            return

        try:
            # SQLite doesn't support parameters for identifiers, so f-string is necessary.
            # Validation above mitigates risk.
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {type_def}")
        except sqlite3.OperationalError:
            # Column likely exists
            pass

    def save_incidents(self, incidents: List[Dict]):
        """Upsert a batch of incidents."""
        cur = self.conn.cursor()
        for inc in incidents:
            loc = inc.get("location", {})
            cur.execute(
                """
                INSERT INTO incidents (
                    id, title, date, type, severity, 
                    location_lat, location_lng, city, summary, url, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title,
                    type=excluded.type,
                    severity=excluded.severity,
                    location_lat=excluded.location_lat,
                    location_lng=excluded.location_lng,
                    city=excluded.city,
                    summary=excluded.summary,
                    url=excluded.url,
                    updated_at=CURRENT_TIMESTAMP
            """,
                (
                    inc.get("id"),
                    inc.get("title"),
                    inc.get("date"),
                    inc.get("type"),
                    inc.get("severity"),
                    loc.get("lat"),
                    loc.get("lng"),
                    inc.get("city"),
                    inc.get("summary"),
                    inc.get("url"),
                ),
            )
        self.conn.commit()

    def get_incidents(self, limit: int = 100) -> List[Dict]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM incidents ORDER BY date DESC LIMIT ?", (limit,))
        rows = cur.fetchall()
        results = []
        for row in rows:
            d = dict(row)
            # Reconstruct nested location object
            d["location"] = {"lat": d.pop("location_lat"), "lng": d.pop("location_lng")}
            results.append(d)
        return results

    def _generate_id(self, text: str) -> str:
        return hashlib.md5(text.lower().strip().encode()).hexdigest()

    def add_topic_proposal(self, topic: Dict) -> bool:
        tid = self._generate_id(topic["topic"])
        cur = self.conn.cursor()

        try:
            cur.execute(
                """
                INSERT INTO topics (id, topic, target_audience, gap_score, content_type, status)
                VALUES (?, ?, ?, ?, ?, 'PROPOSED')
            """,
                (
                    tid,
                    topic["topic"],
                    topic["target_audience"],
                    topic["gap_score"],
                    topic.get("content_type", "General"),
                ),
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_next_topic_to_write(self) -> Optional[Dict]:
        cur = self.conn.cursor()
        cur.execute("""
            SELECT * FROM topics 
            WHERE status = 'PROPOSED' 
            ORDER BY gap_score DESC 
            LIMIT 1
        """)
        row = cur.fetchone()
        return dict(row) if row else None

    def list_topics(self) -> List[str]:
        cur = self.conn.cursor()
        cur.execute("SELECT topic FROM topics")
        return [row["topic"] for row in cur.fetchall() if row["topic"]]

    def mark_as_drafted(
        self, topic_id: str, article_slug: str, filepath: str, draft_data: Dict
    ):
        """
        Updates topic status and creates/updates article record.
        """
        cur = self.conn.cursor()

        # Update Topic
        cur.execute(
            "UPDATE topics SET status = 'DRAFTED', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (topic_id,),
        )

        # Upsert Article
        sources_json = json.dumps(draft_data.get("sources", []))

        cur.execute(
            """
            INSERT INTO articles (
                slug, topic_id, title, content_type, word_count, 
                quality_score, sources, status, content_path, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'DRAFT', ?, CURRENT_TIMESTAMP)
            ON CONFLICT(slug) DO UPDATE SET
                word_count=excluded.word_count,
                quality_score=excluded.quality_score,
                sources=excluded.sources,
                content_path=excluded.content_path,
                updated_at=CURRENT_TIMESTAMP
        """,
            (
                article_slug,
                topic_id,
                draft_data.get("title"),
                draft_data.get("contentType"),
                draft_data.get("wordCount"),
                draft_data.get("qualityScore"),
                sources_json,
                filepath,
            ),
        )

        self.conn.commit()

    def get_drafts_ready_for_review(self) -> List[Dict]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM articles WHERE status = 'DRAFT'")
        return [dict(row) for row in cur.fetchall()]

    def mark_as_published(self, article_slug: str, public_url: str = ""):
        cur = self.conn.cursor()
        cur.execute(
            """
            UPDATE articles 
            SET status = 'PUBLISHED', published_date = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP 
            WHERE slug = ?
        """,
            (article_slug,),
        )

        # Also update the topic to DONE/PUBLISHED
        cur.execute(
            """
            UPDATE topics 
            SET status = 'PUBLISHED', updated_at = CURRENT_TIMESTAMP 
            WHERE id = (SELECT topic_id FROM articles WHERE slug = ?)
        """,
            (article_slug,),
        )

        self.conn.commit()

    def get_stats(self):
        cur = self.conn.cursor()
        cur.execute("SELECT status, COUNT(*) as count FROM topics GROUP BY status")
        status_stats = {row["status"]: row["count"] for row in cur.fetchall()}
        cur.execute(
            "SELECT content_type, COUNT(*) as count FROM topics GROUP BY content_type"
        )
        type_stats = {row["content_type"]: row["count"] for row in cur.fetchall()}
        return {"status": status_stats, "types": type_stats}

    def mark_topic_rejected(self, topic_id: str, reason: str):
        if not topic_id:
            return
        cur = self.conn.cursor()
        cur.execute(
            """
            UPDATE topics
            SET status = 'REJECTED', rejection_reason = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """,
            (reason, topic_id),
        )
        self.conn.commit()

    # ─────────────────────────────────────────────────────────────────────────
    # Content Audit Methods
    # ─────────────────────────────────────────────────────────────────────────

    def record_audit(
        self,
        content_id: str,
        collection: str,
        file_path: str,
        title: str,
        word_count: int,
        audit_data: Dict,
    ):
        """
        Record or update an audit result for a content piece.

        Args:
            content_id: Unique identifier (e.g., "blog/article-slug")
            collection: Content collection (blog, qna, sectors, casestudies)
            file_path: Path to the content file
            title: Content title
            word_count: Word count of the content
            audit_data: Dict with quality_score, fact_check_score, consensus_level,
                        status, issues
        """
        cur = self.conn.cursor()
        now = datetime.now().isoformat()

        issues_json = json.dumps(audit_data.get("issues", []))

        cur.execute(
            """
            INSERT INTO content_audit (
                id, collection, file_path, title, word_count,
                quality_score, fact_check_score, consensus_level,
                audit_status, issues_json, last_audited, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                collection=excluded.collection,
                file_path=excluded.file_path,
                title=excluded.title,
                word_count=excluded.word_count,
                quality_score=excluded.quality_score,
                fact_check_score=excluded.fact_check_score,
                consensus_level=excluded.consensus_level,
                audit_status=excluded.audit_status,
                issues_json=excluded.issues_json,
                last_audited=excluded.last_audited,
                updated_at=excluded.updated_at
        """,
            (
                content_id,
                collection,
                file_path,
                title,
                word_count,
                audit_data.get("quality_score"),
                audit_data.get("fact_check_score"),
                audit_data.get("consensus_level"),
                audit_data.get("status", "pending"),
                issues_json,
                now,
                now,
                now,
            ),
        )
        self.conn.commit()

    def get_audit_by_id(self, content_id: str) -> Optional[Dict]:
        """Get audit result for a specific content piece."""
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM content_audit WHERE id = ?", (content_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def get_audits_by_collection(self, collection: str) -> List[Dict]:
        """Get all audits for a specific collection."""
        cur = self.conn.cursor()
        cur.execute(
            "SELECT * FROM content_audit WHERE collection = ? ORDER BY last_audited DESC",
            (collection,),
        )
        return [dict(row) for row in cur.fetchall()]

    def get_audits_by_status(self, status: str) -> List[Dict]:
        """Get all audits with a specific status."""
        cur = self.conn.cursor()
        cur.execute(
            "SELECT * FROM content_audit WHERE audit_status = ? ORDER BY last_audited DESC",
            (status,),
        )
        return [dict(row) for row in cur.fetchall()]

    def get_stale_audits(self, days: int = 30) -> List[Dict]:
        """Get content not audited in the last N days."""
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT * FROM content_audit
            WHERE last_audited < datetime('now', ? || ' days')
            ORDER BY last_audited ASC
        """,
            (f"-{days}",),
        )
        return [dict(row) for row in cur.fetchall()]

    def get_audit_summary(self) -> Dict:
        """Get summary statistics for all audits."""
        cur = self.conn.cursor()

        # Total count
        cur.execute("SELECT COUNT(*) as count FROM content_audit")
        total = cur.fetchone()["count"]

        # By status
        cur.execute("""
            SELECT audit_status, COUNT(*) as count
            FROM content_audit
            GROUP BY audit_status
        """)
        status_counts = {row["audit_status"]: row["count"] for row in cur.fetchall()}

        # By collection
        cur.execute("""
            SELECT collection, COUNT(*) as count
            FROM content_audit
            GROUP BY collection
        """)
        collection_counts = {row["collection"]: row["count"] for row in cur.fetchall()}

        return {
            "total": total,
            "passed": status_counts.get("passed", 0),
            "failed": status_counts.get("failed", 0),
            "review": status_counts.get("review", 0),
            "pending": status_counts.get("pending", 0),
            "by_collection": collection_counts,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Auto-Publish Methods
    # ─────────────────────────────────────────────────────────────────────────

    def _ensure_auto_publish_columns(self):
        """Ensure auto-publish columns exist in articles table."""
        cur = self.conn.cursor()
        migrations = [
            ("articles", "body", "TEXT"),
            ("articles", "frontmatter", "TEXT"),
            ("articles", "council_verdict", "TEXT"),
            ("articles", "published_via", "TEXT DEFAULT 'manual'"),
            ("articles", "description", "TEXT"),
            ("articles", "category", "TEXT"),
            ("articles", "tags", "TEXT"),
            # Pipeline tracking columns
            ("articles", "pipeline_profile", "TEXT"),
            ("articles", "fast_tracked", "INTEGER DEFAULT 0"),
            ("articles", "rollback_eligible", "INTEGER DEFAULT 0"),
            ("articles", "correction_window_expires", "TIMESTAMP"),
            ("articles", "correction_status", "TEXT DEFAULT 'none'"),
        ]
        for table, col, type_def in migrations:
            self._safe_add_column(cur, table, col, type_def)
        self.conn.commit()

    def publish_article(
        self,
        slug: str,
        draft,
        verdict,
        pipeline_profile: Optional[str] = None,
        fast_tracked: bool = False,
        rollback_eligible: bool = False,
        correction_window_expires: Optional[datetime] = None,
    ) -> bool:
        """
        Publish an article directly to the database.

        Args:
            slug: URL-friendly article identifier
            draft: ArticleDraft model with full content
            verdict: CouncilVerdict from the adversarial council
            pipeline_profile: Name of the pipeline profile used (e.g., "news_breaking")
            fast_tracked: Whether this article was fast-tracked
            rollback_eligible: Whether this article can be rolled back
            correction_window_expires: When the correction window expires

        Returns:
            True if successful
        """
        self._ensure_auto_publish_columns()
        cur = self.conn.cursor()

        # Serialize complex objects
        frontmatter = json.dumps(
            {
                "title": draft.title,
                "description": draft.description,
                "pubDate": draft.pubDate.isoformat() if draft.pubDate else None,
                "author": draft.author,
                "tags": draft.tags,
                "category": draft.category,
                "contentType": draft.contentType,
                "image": draft.image.model_dump() if draft.image else None,
            }
        )

        council_verdict = json.dumps(
            {
                "decision": verdict.decision,
                "confidence": verdict.confidence,
                "advocate_score": verdict.advocate_score,
                "skeptic_score": verdict.skeptic_score,
                "guardian_score": verdict.guardian_score,
                "average_score": verdict.average_score,
                "debate_summary": verdict.debate_summary,
            }
        )

        sources_json = json.dumps(
            [s.model_dump() if hasattr(s, "model_dump") else s for s in draft.sources]
        )
        tags_json = json.dumps(draft.tags)

        # Format correction window expires
        correction_window_str = None
        if correction_window_expires:
            correction_window_str = correction_window_expires.isoformat()

        cur.execute(
            """
            INSERT INTO articles (
                slug, title, description, category, content_type,
                body, frontmatter, sources, council_verdict,
                word_count, quality_score, status, published_via,
                published_date, tags, pipeline_profile, fast_tracked,
                rollback_eligible, correction_window_expires, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PUBLISHED', 'auto', CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(slug) DO UPDATE SET
                title=excluded.title,
                description=excluded.description,
                category=excluded.category,
                content_type=excluded.content_type,
                body=excluded.body,
                frontmatter=excluded.frontmatter,
                sources=excluded.sources,
                council_verdict=excluded.council_verdict,
                word_count=excluded.word_count,
                quality_score=excluded.quality_score,
                status='PUBLISHED',
                published_via='auto',
                published_date=CURRENT_TIMESTAMP,
                tags=excluded.tags,
                pipeline_profile=excluded.pipeline_profile,
                fast_tracked=excluded.fast_tracked,
                rollback_eligible=excluded.rollback_eligible,
                correction_window_expires=excluded.correction_window_expires,
                updated_at=CURRENT_TIMESTAMP
        """,
            (
                slug,
                draft.title,
                draft.description,
                draft.category,
                draft.contentType,
                draft.body,
                frontmatter,
                sources_json,
                council_verdict,
                draft.wordCount,
                draft.qualityScore,
                tags_json,
                pipeline_profile,
                1 if fast_tracked else 0,
                1 if rollback_eligible else 0,
                correction_window_str,
            ),
        )

        self.conn.commit()
        logger.info("article_published", slug=slug, via="auto")
        return True

    def get_published_article(self, slug: str) -> Optional[Dict]:
        """
        Get a published article by slug.

        Args:
            slug: Article slug

        Returns:
            Dict with article data or None if not found
        """
        self._ensure_auto_publish_columns()
        cur = self.conn.cursor()

        cur.execute(
            """
            SELECT slug, title, description, category, content_type,
                   body, frontmatter, sources, council_verdict,
                   word_count, quality_score, status, published_via,
                   published_date, tags, pipeline_profile, fast_tracked,
                   rollback_eligible, correction_window_expires, correction_status,
                   created_at, updated_at
            FROM articles
            WHERE slug = ? AND status = 'PUBLISHED'
        """,
            (slug,),
        )

        row = cur.fetchone()
        if not row:
            return None

        article = dict(row)

        # Parse JSON fields
        if article.get("frontmatter"):
            try:
                article["frontmatter"] = json.loads(article["frontmatter"])
            except Exception:
                pass

        if article.get("sources"):
            try:
                article["sources"] = json.loads(article["sources"])
            except Exception:
                pass

        if article.get("council_verdict"):
            try:
                article["council_verdict"] = json.loads(article["council_verdict"])
            except Exception:
                pass

        if article.get("tags"):
            try:
                article["tags"] = json.loads(article["tags"])
            except Exception:
                pass

        return article

    def get_published_articles(self, limit: int = 20, offset: int = 0) -> List[Dict]:
        """
        Get list of published articles with pagination.

        Args:
            limit: Maximum number of articles to return
            offset: Number of articles to skip

        Returns:
            List of article dicts
        """
        self._ensure_auto_publish_columns()
        cur = self.conn.cursor()

        cur.execute(
            """
            SELECT slug, title, description, category, content_type,
                   word_count, quality_score, status, published_via,
                   published_date, tags, created_at, updated_at
            FROM articles
            WHERE status = 'PUBLISHED'
            ORDER BY published_date DESC
            LIMIT ? OFFSET ?
        """,
            (limit, offset),
        )

        articles = []
        for row in cur.fetchall():
            article = dict(row)
            if article.get("tags"):
                try:
                    article["tags"] = json.loads(article["tags"])
                except Exception:
                    pass
            articles.append(article)

        return articles

    def get_fast_tracked_articles(self, limit: int = 50) -> List[Dict]:
        """
        Get list of fast-tracked articles.

        Args:
            limit: Maximum number of articles to return

        Returns:
            List of fast-tracked article dicts
        """
        self._ensure_auto_publish_columns()
        cur = self.conn.cursor()

        cur.execute(
            """
            SELECT slug, title, description, category, content_type,
                   word_count, quality_score, status, published_via,
                   published_date, pipeline_profile, fast_tracked,
                   rollback_eligible, correction_window_expires, correction_status
            FROM articles
            WHERE status = 'PUBLISHED' AND fast_tracked = 1
            ORDER BY published_date DESC
            LIMIT ?
        """,
            (limit,),
        )

        return [dict(row) for row in cur.fetchall()]

    def get_articles_in_correction_window(self) -> List[Dict]:
        """
        Get articles that are still in their correction window.

        Returns:
            List of article dicts within correction window
        """
        self._ensure_auto_publish_columns()
        cur = self.conn.cursor()

        # Use Python's current datetime for comparison since we store ISO format
        now = datetime.now().isoformat()

        cur.execute(
            """
            SELECT slug, title, description, category, content_type,
                   word_count, quality_score, status, published_via,
                   published_date, pipeline_profile, fast_tracked,
                   rollback_eligible, correction_window_expires, correction_status
            FROM articles
            WHERE status = 'PUBLISHED'
              AND fast_tracked = 1
              AND rollback_eligible = 1
              AND correction_window_expires > ?
            ORDER BY published_date DESC
        """,
            (now,),
        )

        return [dict(row) for row in cur.fetchall()]

    # ─────────────────────────────────────────────────────────────────────────
    # Topic Sourcing Methods
    # ─────────────────────────────────────────────────────────────────────────

    def save_sourced_topic(self, topic_data: Dict) -> bool:
        """
        Save a sourced topic to the database.

        Args:
            topic_data: Dict with topic data (id, source_type, source_id, etc.)

        Returns:
            True if saved successfully
        """
        cur = self.conn.cursor()

        evidence_json = json.dumps(topic_data.get("evidence", {}))

        try:
            cur.execute(
                """
                INSERT INTO sourced_topics (
                    id, topic_id, source_type, source_id, source_url,
                    urgency, timeliness_score, authority_score, gap_score,
                    overall_score, evidence_json, status, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET
                    urgency=excluded.urgency,
                    timeliness_score=excluded.timeliness_score,
                    authority_score=excluded.authority_score,
                    gap_score=excluded.gap_score,
                    overall_score=excluded.overall_score,
                    evidence_json=excluded.evidence_json,
                    updated_at=CURRENT_TIMESTAMP
            """,
                (
                    topic_data.get("id"),
                    topic_data.get("topic_id"),
                    topic_data.get("source_type"),
                    topic_data.get("source_id"),
                    topic_data.get("source_url"),
                    topic_data.get("urgency", "medium"),
                    topic_data.get("timeliness_score"),
                    topic_data.get("authority_score"),
                    topic_data.get("gap_score"),
                    topic_data.get("overall_score"),
                    evidence_json,
                ),
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error("save_sourced_topic_error", error=str(e))
            return False

    def get_sourced_topics(
        self,
        source_type: Optional[str] = None,
        status: str = "pending",
        limit: int = 50,
    ) -> List[Dict]:
        """
        Get sourced topics from the database.

        Args:
            source_type: Optional filter by source type
            status: Filter by status (default: pending)
            limit: Maximum number of results

        Returns:
            List of sourced topic dicts
        """
        cur = self.conn.cursor()

        if source_type:
            cur.execute(
                """
                SELECT * FROM sourced_topics
                WHERE source_type = ? AND status = ?
                ORDER BY overall_score DESC
                LIMIT ?
            """,
                (source_type, status, limit),
            )
        else:
            cur.execute(
                """
                SELECT * FROM sourced_topics
                WHERE status = ?
                ORDER BY overall_score DESC
                LIMIT ?
            """,
                (status, limit),
            )

        results = []
        for row in cur.fetchall():
            topic = dict(row)
            if topic.get("evidence_json"):
                try:
                    topic["evidence"] = json.loads(topic["evidence_json"])
                except Exception:
                    pass
            results.append(topic)

        return results

    def update_sourced_topic_status(self, topic_id: str, status: str) -> bool:
        """
        Update the status of a sourced topic.

        Args:
            topic_id: ID of the sourced topic
            status: New status (pending, queued, written, rejected)

        Returns:
            True if updated successfully
        """
        cur = self.conn.cursor()
        cur.execute(
            """
            UPDATE sourced_topics
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """,
            (status, topic_id),
        )
        self.conn.commit()
        return cur.rowcount > 0

    def save_calendar_event(self, event_data: Dict) -> bool:
        """
        Save a calendar event to the database.

        Args:
            event_data: Dict with event data

        Returns:
            True if saved successfully
        """
        cur = self.conn.cursor()

        tags_json = json.dumps(event_data.get("tags", []))

        try:
            cur.execute(
                """
                INSERT INTO calendar_events (
                    id, title, event_type, event_date, recurring,
                    source, content_type, priority, lead_days,
                    tags, description, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title,
                    event_date=excluded.event_date,
                    priority=excluded.priority,
                    lead_days=excluded.lead_days,
                    tags=excluded.tags,
                    description=excluded.description,
                    updated_at=CURRENT_TIMESTAMP
            """,
                (
                    event_data.get("id"),
                    event_data.get("title"),
                    event_data.get("event_type"),
                    event_data.get("event_date"),
                    event_data.get("recurring"),
                    event_data.get("source"),
                    event_data.get("content_type"),
                    event_data.get("priority", "medium"),
                    event_data.get("lead_days", 7),
                    tags_json,
                    event_data.get("description", ""),
                ),
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error("save_calendar_event_error", error=str(e))
            return False

    def get_calendar_events(self, days_ahead: int = 60) -> List[Dict]:
        """
        Get upcoming calendar events.

        Args:
            days_ahead: Number of days to look ahead

        Returns:
            List of calendar event dicts
        """
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT * FROM calendar_events
            WHERE event_date >= date('now')
              AND event_date <= date('now', ? || ' days')
            ORDER BY event_date ASC
        """,
            (f"+{days_ahead}",),
        )

        results = []
        for row in cur.fetchall():
            event = dict(row)
            if event.get("tags"):
                try:
                    event["tags"] = json.loads(event["tags"])
                except Exception:
                    pass
            results.append(event)

        return results

    def mark_calendar_event_triggered(self, event_id: str) -> bool:
        """
        Mark a calendar event as triggered.

        Args:
            event_id: ID of the calendar event

        Returns:
            True if updated successfully
        """
        cur = self.conn.cursor()
        cur.execute(
            """
            UPDATE calendar_events
            SET last_triggered = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """,
            (event_id,),
        )
        self.conn.commit()
        return cur.rowcount > 0

    def save_regulatory_document(self, doc_data: Dict) -> bool:
        """
        Save a regulatory document to tracking.

        Args:
            doc_data: Dict with document data

        Returns:
            True if saved successfully
        """
        cur = self.conn.cursor()

        try:
            cur.execute(
                """
                INSERT INTO regulatory_tracking (
                    id, regulator, document_type, title, url,
                    published_date, compliance_deadline, status, notes, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title,
                    compliance_deadline=excluded.compliance_deadline,
                    status=excluded.status,
                    notes=excluded.notes,
                    updated_at=CURRENT_TIMESTAMP
            """,
                (
                    doc_data.get("id"),
                    doc_data.get("regulator"),
                    doc_data.get("document_type"),
                    doc_data.get("title"),
                    doc_data.get("url"),
                    doc_data.get("published_date"),
                    doc_data.get("compliance_deadline"),
                    doc_data.get("status", "new"),
                    doc_data.get("notes", ""),
                ),
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error("save_regulatory_document_error", error=str(e))
            return False

    def get_regulatory_documents(
        self, regulator: Optional[str] = None, status: str = "new", limit: int = 50
    ) -> List[Dict]:
        """
        Get regulatory documents from tracking.

        Args:
            regulator: Optional filter by regulator
            status: Filter by status
            limit: Maximum number of results

        Returns:
            List of regulatory document dicts
        """
        cur = self.conn.cursor()

        if regulator:
            cur.execute(
                """
                SELECT * FROM regulatory_tracking
                WHERE regulator = ? AND status = ?
                ORDER BY published_date DESC
                LIMIT ?
            """,
                (regulator, status, limit),
            )
        else:
            cur.execute(
                """
                SELECT * FROM regulatory_tracking
                WHERE status = ?
                ORDER BY published_date DESC
                LIMIT ?
            """,
                (status, limit),
            )

        return [dict(row) for row in cur.fetchall()]

    def get_upcoming_compliance_deadlines(self, days_ahead: int = 90) -> List[Dict]:
        """
        Get upcoming compliance deadlines.

        Args:
            days_ahead: Number of days to look ahead

        Returns:
            List of regulatory documents with deadlines
        """
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT * FROM regulatory_tracking
            WHERE compliance_deadline IS NOT NULL
              AND compliance_deadline >= date('now')
              AND compliance_deadline <= date('now', ? || ' days')
            ORDER BY compliance_deadline ASC
        """,
            (f"+{days_ahead}",),
        )

        return [dict(row) for row in cur.fetchall()]

    def get_topic_sourcing_stats(self) -> Dict:
        """
        Get statistics about topic sourcing.

        Returns:
            Dict with sourcing statistics
        """
        cur = self.conn.cursor()

        stats = {}

        # Sourced topics by source type
        cur.execute("""
            SELECT source_type, COUNT(*) as count
            FROM sourced_topics
            GROUP BY source_type
        """)
        stats["sourced_by_type"] = {
            row["source_type"]: row["count"] for row in cur.fetchall()
        }

        # Sourced topics by status
        cur.execute("""
            SELECT status, COUNT(*) as count
            FROM sourced_topics
            GROUP BY status
        """)
        stats["sourced_by_status"] = {
            row["status"]: row["count"] for row in cur.fetchall()
        }

        # Calendar events count
        cur.execute("SELECT COUNT(*) as count FROM calendar_events")
        stats["calendar_events"] = cur.fetchone()["count"]

        # Regulatory documents count
        cur.execute("SELECT COUNT(*) as count FROM regulatory_tracking")
        stats["regulatory_documents"] = cur.fetchone()["count"]

        return stats

    # ─────────────────────────────────────────────────────────────────────────
    # Scam Intelligence Methods
    # ─────────────────────────────────────────────────────────────────────────

    def save_scam(self, scam_data: Dict) -> bool:
        """
        Save a scam alert to the intelligence database.

        Args:
            scam_data: Dictionary with scam details

        Returns:
            True if saved successfully
        """
        cur = self.conn.cursor()

        try:
            cur.execute(
                """
                INSERT INTO scam_intelligence (
                    id, scam_type, title, description, affected_regions,
                    target_demographics, reported_losses_inr, status,
                    prevention_tips, source_url, source_credibility, first_seen
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title,
                    description=excluded.description,
                    affected_regions=excluded.affected_regions,
                    reported_losses_inr=excluded.reported_losses_inr,
                    status=excluded.status,
                    last_updated=CURRENT_TIMESTAMP
            """,
                (
                    scam_data.get("id"),
                    scam_data.get("scam_type"),
                    scam_data.get("title"),
                    scam_data.get("description"),
                    json.dumps(scam_data.get("affected_regions", [])),
                    json.dumps(scam_data.get("target_demographics", [])),
                    scam_data.get("reported_losses_inr"),
                    scam_data.get("status", "active"),
                    json.dumps(scam_data.get("prevention_tips", [])),
                    scam_data.get("source_url"),
                    scam_data.get("source_credibility"),
                ),
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error("save_scam_error", error=str(e))
            return False

    def get_active_scams(
        self, scam_type: Optional[str] = None, limit: int = 50
    ) -> List[Dict]:
        """
        Get active scam alerts.

        Args:
            scam_type: Optional filter by scam type
            limit: Maximum results

        Returns:
            List of active scam dictionaries
        """
        cur = self.conn.cursor()

        if scam_type:
            cur.execute(
                """
                SELECT * FROM scam_intelligence
                WHERE status = 'active' AND scam_type = ?
                ORDER BY last_updated DESC
                LIMIT ?
            """,
                (scam_type, limit),
            )
        else:
            cur.execute(
                """
                SELECT * FROM scam_intelligence
                WHERE status = 'active'
                ORDER BY last_updated DESC
                LIMIT ?
            """,
                (limit,),
            )

        results = []
        for row in cur.fetchall():
            scam = dict(row)
            # Parse JSON fields
            for field in ["affected_regions", "target_demographics", "prevention_tips"]:
                if scam.get(field):
                    try:
                        scam[field] = json.loads(scam[field])
                    except Exception:
                        pass
            results.append(scam)

        return results

    def get_scam_stats(self) -> Dict:
        """Get scam intelligence statistics."""
        cur = self.conn.cursor()

        stats = {}

        # By type
        cur.execute("""
            SELECT scam_type, COUNT(*) as count
            FROM scam_intelligence
            WHERE status = 'active'
            GROUP BY scam_type
        """)
        stats["by_type"] = {row["scam_type"]: row["count"] for row in cur.fetchall()}

        # Total active
        cur.execute(
            "SELECT COUNT(*) as count FROM scam_intelligence WHERE status = 'active'"
        )
        stats["active_count"] = cur.fetchone()["count"]

        # Total reported losses
        cur.execute("SELECT SUM(reported_losses_inr) as total FROM scam_intelligence")
        result = cur.fetchone()
        stats["total_reported_losses_inr"] = result["total"] if result["total"] else 0

        return stats

    # ─────────────────────────────────────────────────────────────────────────
    # Content Pillar Methods
    # ─────────────────────────────────────────────────────────────────────────

    def update_pillar_stats(
        self, pillar_slug: str, article_count: int, health_score: int
    ):
        """
        Update statistics for a content pillar.

        Args:
            pillar_slug: Pillar identifier
            article_count: Number of articles in this pillar
            health_score: Current health score (0-100)
        """
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO content_pillars (pillar_slug, article_count, health_score, last_calculated)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(pillar_slug) DO UPDATE SET
                article_count=excluded.article_count,
                health_score=excluded.health_score,
                last_calculated=CURRENT_TIMESTAMP,
                updated_at=CURRENT_TIMESTAMP
        """,
            (pillar_slug, article_count, health_score),
        )
        self.conn.commit()

    def get_pillar_stats(self) -> Dict[str, Dict]:
        """Get statistics for all content pillars."""
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM content_pillars ORDER BY pillar_slug")

        return {row["pillar_slug"]: dict(row) for row in cur.fetchall()}

    # ─────────────────────────────────────────────────────────────────────────
    # Product Review Methods
    # ─────────────────────────────────────────────────────────────────────────

    def save_product_review(self, review_data: Dict) -> bool:
        """
        Save a product review.

        Args:
            review_data: Dictionary with review details

        Returns:
            True if saved successfully
        """
        cur = self.conn.cursor()

        try:
            cur.execute(
                """
                INSERT INTO product_reviews (
                    id, product_name, category, brand, overall_rating,
                    certification_status, price_range, india_available,
                    pros, cons, our_verdict, source_url, reviewed_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    overall_rating=excluded.overall_rating,
                    certification_status=excluded.certification_status,
                    pros=excluded.pros,
                    cons=excluded.cons,
                    our_verdict=excluded.our_verdict,
                    updated_at=CURRENT_TIMESTAMP
            """,
                (
                    review_data.get("id"),
                    review_data.get("product_name"),
                    review_data.get("category"),
                    review_data.get("brand"),
                    review_data.get("overall_rating"),
                    json.dumps(review_data.get("certification_status", {})),
                    review_data.get("price_range"),
                    1 if review_data.get("india_available", True) else 0,
                    json.dumps(review_data.get("pros", [])),
                    json.dumps(review_data.get("cons", [])),
                    review_data.get("our_verdict"),
                    review_data.get("source_url"),
                    review_data.get("reviewed_date"),
                ),
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error("save_product_review_error", error=str(e))
            return False

    def get_product_reviews(
        self, category: Optional[str] = None, limit: int = 20
    ) -> List[Dict]:
        """
        Get product reviews.

        Args:
            category: Optional filter by category
            limit: Maximum results

        Returns:
            List of product review dictionaries
        """
        cur = self.conn.cursor()

        if category:
            cur.execute(
                """
                SELECT * FROM product_reviews
                WHERE category = ?
                ORDER BY reviewed_date DESC
                LIMIT ?
            """,
                (category, limit),
            )
        else:
            cur.execute(
                """
                SELECT * FROM product_reviews
                ORDER BY reviewed_date DESC
                LIMIT ?
            """,
                (limit,),
            )

        results = []
        for row in cur.fetchall():
            review = dict(row)
            # Parse JSON fields
            for field in ["certification_status", "pros", "cons"]:
                if review.get(field):
                    try:
                        review[field] = json.loads(review[field])
                    except Exception:
                        pass
            results.append(review)

        return results

    def get_product_review_stats(self) -> Dict:
        """Get product review statistics."""
        cur = self.conn.cursor()

        stats = {}

        # By category
        cur.execute("""
            SELECT category, COUNT(*) as count, AVG(overall_rating) as avg_rating
            FROM product_reviews
            GROUP BY category
        """)
        stats["by_category"] = {
            row["category"]: {"count": row["count"], "avg_rating": row["avg_rating"]}
            for row in cur.fetchall()
        }

        # Total count
        cur.execute("SELECT COUNT(*) as count FROM product_reviews")
        stats["total_reviews"] = cur.fetchone()["count"]

        return stats
