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
        if not table.replace('_', '').isalnum():
            logger.error(f"Invalid table name in migration: {table}")
            return
        if not col.replace('_', '').isalnum():
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
            loc = inc.get('location', {})
            cur.execute("""
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
            """, (
                inc.get('id'),
                inc.get('title'),
                inc.get('date'),
                inc.get('type'),
                inc.get('severity'),
                loc.get('lat'),
                loc.get('lng'),
                inc.get('city'),
                inc.get('summary'),
                inc.get('url')
            ))
        self.conn.commit()

    def get_incidents(self, limit: int = 100) -> List[Dict]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM incidents ORDER BY date DESC LIMIT ?", (limit,))
        rows = cur.fetchall()
        results = []
        for row in rows:
            d = dict(row)
            # Reconstruct nested location object
            d['location'] = {'lat': d.pop('location_lat'), 'lng': d.pop('location_lng')}
            results.append(d)
        return results

    def _generate_id(self, text: str) -> str:
        return hashlib.md5(text.lower().strip().encode()).hexdigest()

    def add_topic_proposal(self, topic: Dict) -> bool:
        tid = self._generate_id(topic['topic'])
        cur = self.conn.cursor()
        
        try:
            cur.execute("""
                INSERT INTO topics (id, topic, target_audience, gap_score, content_type, status)
                VALUES (?, ?, ?, ?, ?, 'PROPOSED')
            """, (
                tid, 
                topic['topic'], 
                topic['target_audience'], 
                topic['gap_score'], 
                topic.get('content_type', 'General')
            ))
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

    def mark_as_drafted(self, topic_id: str, article_slug: str, filepath: str, draft_data: Dict):
        """
        Updates topic status and creates/updates article record.
        """
        cur = self.conn.cursor()
        
        # Update Topic
        cur.execute("UPDATE topics SET status = 'DRAFTED', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (topic_id,))
        
        # Upsert Article
        sources_json = json.dumps(draft_data.get('sources', []))
        
        cur.execute("""
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
        """, (
            article_slug,
            topic_id,
            draft_data.get('title'),
            draft_data.get('contentType'),
            draft_data.get('wordCount'),
            draft_data.get('qualityScore'),
            sources_json,
            filepath
        ))
        
        self.conn.commit()

    def get_drafts_ready_for_review(self) -> List[Dict]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM articles WHERE status = 'DRAFT'")
        return [dict(row) for row in cur.fetchall()]

    def mark_as_published(self, article_slug: str, public_url: str = ""):
        cur = self.conn.cursor()
        cur.execute("""
            UPDATE articles 
            SET status = 'PUBLISHED', published_date = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP 
            WHERE slug = ?
        """, (article_slug,))
        
        # Also update the topic to DONE/PUBLISHED
        cur.execute("""
            UPDATE topics 
            SET status = 'PUBLISHED', updated_at = CURRENT_TIMESTAMP 
            WHERE id = (SELECT topic_id FROM articles WHERE slug = ?)
        """, (article_slug,))
        
        self.conn.commit()

    def get_stats(self):
        cur = self.conn.cursor()
        cur.execute("SELECT status, COUNT(*) as count FROM topics GROUP BY status")
        status_stats = {row['status']: row['count'] for row in cur.fetchall()}
        cur.execute("SELECT content_type, COUNT(*) as count FROM topics GROUP BY content_type")
        type_stats = {row['content_type']: row['count'] for row in cur.fetchall()}
        return {"status": status_stats, "types": type_stats}

    def mark_topic_rejected(self, topic_id: str, reason: str):
        if not topic_id:
            return
        cur = self.conn.cursor()
        cur.execute("""
            UPDATE topics
            SET status = 'REJECTED', rejection_reason = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (reason, topic_id))
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
        audit_data: Dict
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

        cur.execute("""
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
        """, (
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
            now
        ))
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
            (collection,)
        )
        return [dict(row) for row in cur.fetchall()]

    def get_audits_by_status(self, status: str) -> List[Dict]:
        """Get all audits with a specific status."""
        cur = self.conn.cursor()
        cur.execute(
            "SELECT * FROM content_audit WHERE audit_status = ? ORDER BY last_audited DESC",
            (status,)
        )
        return [dict(row) for row in cur.fetchall()]

    def get_stale_audits(self, days: int = 30) -> List[Dict]:
        """Get content not audited in the last N days."""
        cur = self.conn.cursor()
        cur.execute("""
            SELECT * FROM content_audit
            WHERE last_audited < datetime('now', ? || ' days')
            ORDER BY last_audited ASC
        """, (f"-{days}",))
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
            "by_collection": collection_counts
        }
