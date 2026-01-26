"""
TasteMemory: Persistent memory for the Autopoietic Newsroom.
Stores feedback and learned preferences across sessions.
"""

import sqlite3
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

from config.manager import config
from shared.logger import get_logger

logger = get_logger("TasteMemory")


@dataclass
class ArticleFeedback:
    """Feedback record for a completed article."""
    topic_id: str
    topic: str
    sector: str
    content_type: str
    proposal_score: float      # Original prediction (0-1)
    quality_score: float       # Actual quality achieved (0-100)
    was_published: bool
    was_blocked: bool
    block_reason: Optional[str]
    time_to_write_seconds: float
    sources_found: int
    sources_used: int
    trust_score: float
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    @property
    def success(self) -> bool:
        """Was this a successful outcome?"""
        return self.was_published and self.quality_score >= 70
    
    @property
    def prediction_error(self) -> float:
        """How wrong was our prediction? Positive = underestimated."""
        return (self.quality_score / 100) - self.proposal_score
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['created_at'] = self.created_at.isoformat() if self.created_at else None
        return d


class TasteMemory:
    """
    Persistent memory for the autopoietic feedback loop.
    
    Stores:
    - Article feedback records
    - Learned weights (sector, content_type, source)
    - Reflection notes
    """
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or config.get(
            "autonomous.memory_path", 
            ".agent/taste_memory.db"
        )
        # Ensure directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self._init_tables()
        logger.info("taste_memory_initialized", db_path=self.db_path)
    
    def _init_tables(self):
        """Create database tables."""
        cur = self.conn.cursor()
        
        # Feedback records
        cur.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id TEXT NOT NULL,
                topic TEXT,
                sector TEXT,
                content_type TEXT,
                proposal_score REAL,
                quality_score REAL,
                was_published INTEGER,
                was_blocked INTEGER,
                block_reason TEXT,
                time_to_write_seconds REAL,
                sources_found INTEGER,
                sources_used INTEGER,
                trust_score REAL,
                created_at TEXT
            )
        """)
        
        # Learned weights
        cur.execute("""
            CREATE TABLE IF NOT EXISTS weights (
                category TEXT NOT NULL,
                key TEXT NOT NULL,
                weight REAL DEFAULT 1.0,
                samples INTEGER DEFAULT 0,
                updated_at TEXT,
                PRIMARY KEY (category, key)
            )
        """)
        
        # Reflection notes
        cur.execute("""
            CREATE TABLE IF NOT EXISTS reflections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reflection TEXT,
                insights TEXT,
                created_at TEXT
            )
        """)
        
        self.conn.commit()
    
    # =========================================================================
    # Feedback Recording
    # =========================================================================
    
    def record_feedback(self, feedback: ArticleFeedback):
        """Store a feedback record."""
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO feedback (
                topic_id, topic, sector, content_type, proposal_score,
                quality_score, was_published, was_blocked, block_reason,
                time_to_write_seconds, sources_found, sources_used,
                trust_score, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            feedback.topic_id,
            feedback.topic,
            feedback.sector,
            feedback.content_type,
            feedback.proposal_score,
            feedback.quality_score,
            1 if feedback.was_published else 0,
            1 if feedback.was_blocked else 0,
            feedback.block_reason,
            feedback.time_to_write_seconds,
            feedback.sources_found,
            feedback.sources_used,
            feedback.trust_score,
            feedback.created_at.isoformat() if feedback.created_at else None
        ))
        self.conn.commit()
        logger.info("feedback_recorded", topic_id=feedback.topic_id, success=feedback.success)
    
    def get_recent_feedback(self, days: int = 30) -> List[ArticleFeedback]:
        """Get feedback from the last N days."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        cur = self.conn.cursor()
        cur.execute("""
            SELECT topic_id, topic, sector, content_type, proposal_score,
                   quality_score, was_published, was_blocked, block_reason,
                   time_to_write_seconds, sources_found, sources_used,
                   trust_score, created_at
            FROM feedback
            WHERE created_at > ?
            ORDER BY created_at DESC
        """, (cutoff,))
        
        results = []
        for row in cur.fetchall():
            results.append(ArticleFeedback(
                topic_id=row[0],
                topic=row[1],
                sector=row[2],
                content_type=row[3],
                proposal_score=row[4],
                quality_score=row[5],
                was_published=bool(row[6]),
                was_blocked=bool(row[7]),
                block_reason=row[8],
                time_to_write_seconds=row[9],
                sources_found=row[10],
                sources_used=row[11],
                trust_score=row[12],
                created_at=datetime.fromisoformat(row[13]) if row[13] else None
            ))
        return results
    
    # =========================================================================
    # Weight Persistence
    # =========================================================================
    
    def save_weight(self, category: str, key: str, weight: float, samples: int = 0):
        """Save or update a weight."""
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO weights (category, key, weight, samples, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(category, key) DO UPDATE SET
                weight = excluded.weight,
                samples = excluded.samples,
                updated_at = excluded.updated_at
        """, (category, key, weight, samples, datetime.now().isoformat()))
        self.conn.commit()
    
    def get_weight(self, category: str, key: str, default: float = 1.0) -> float:
        """Get a weight value."""
        cur = self.conn.cursor()
        cur.execute(
            "SELECT weight FROM weights WHERE category = ? AND key = ?",
            (category, key)
        )
        row = cur.fetchone()
        return row[0] if row else default
    
    def get_all_weights(self, category: str) -> Dict[str, float]:
        """Get all weights for a category."""
        cur = self.conn.cursor()
        cur.execute(
            "SELECT key, weight FROM weights WHERE category = ?",
            (category,)
        )
        return {row[0]: row[1] for row in cur.fetchall()}
    
    # =========================================================================
    # Performance Analytics
    # =========================================================================
    
    def get_sector_performance(self, days: int = 30) -> Dict[str, Dict]:
        """Get performance metrics by sector."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        cur = self.conn.cursor()
        cur.execute("""
            SELECT sector,
                   COUNT(*) as total,
                   SUM(CASE WHEN was_published = 1 THEN 1 ELSE 0 END) as published,
                   AVG(quality_score) as avg_quality,
                   AVG(proposal_score) as avg_proposal
            FROM feedback
            WHERE created_at > ? AND sector IS NOT NULL
            GROUP BY sector
        """, (cutoff,))
        
        results = {}
        for row in cur.fetchall():
            sector = row[0]
            total = row[1]
            published = row[2]
            results[sector] = {
                'total': total,
                'published': published,
                'publish_rate': published / total if total > 0 else 0,
                'avg_quality': row[3] or 0,
                'avg_proposal_score': row[4] or 0
            }
        return results
    
    def get_content_type_performance(self, days: int = 30) -> Dict[str, Dict]:
        """Get performance metrics by content type."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        cur = self.conn.cursor()
        cur.execute("""
            SELECT content_type,
                   COUNT(*) as total,
                   SUM(CASE WHEN was_published = 1 THEN 1 ELSE 0 END) as published,
                   AVG(quality_score) as avg_quality
            FROM feedback
            WHERE created_at > ? AND content_type IS NOT NULL
            GROUP BY content_type
        """, (cutoff,))
        
        results = {}
        for row in cur.fetchall():
            ctype = row[0]
            total = row[1]
            published = row[2]
            results[ctype] = {
                'total': total,
                'published': published,
                'publish_rate': published / total if total > 0 else 0,
                'avg_quality': row[3] or 0
            }
        return results
    
    def get_success_rate(self, days: int = 30) -> float:
        """Overall success rate in the time period."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        cur = self.conn.cursor()
        cur.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN was_published = 1 AND quality_score >= 70 THEN 1 ELSE 0 END) as success
            FROM feedback
            WHERE created_at > ?
        """, (cutoff,))
        row = cur.fetchone()
        total, success = row[0], row[1] or 0
        return success / total if total > 0 else 0
    
    # =========================================================================
    # Reflection
    # =========================================================================
    
    def save_reflection(self, reflection: str, insights: Dict = None):
        """Save a reflection note."""
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO reflections (reflection, insights, created_at)
            VALUES (?, ?, ?)
        """, (reflection, json.dumps(insights or {}), datetime.now().isoformat()))
        self.conn.commit()
    
    def get_recent_reflections(self, limit: int = 5) -> List[Dict]:
        """Get recent reflection notes."""
        cur = self.conn.cursor()
        cur.execute("""
            SELECT reflection, insights, created_at
            FROM reflections
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        
        results = []
        for row in cur.fetchall():
            results.append({
                'reflection': row[0],
                'insights': json.loads(row[1]) if row[1] else {},
                'created_at': row[2]
            })
        return results
    
    def get_stats(self) -> Dict:
        """Get overall memory statistics."""
        cur = self.conn.cursor()
        
        cur.execute("SELECT COUNT(*) FROM feedback")
        feedback_count = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM weights")
        weight_count = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM reflections")
        reflection_count = cur.fetchone()[0]
        
        return {
            'feedback_records': feedback_count,
            'weights_stored': weight_count,
            'reflections': reflection_count,
            'success_rate_30d': self.get_success_rate(30)
        }


# CLI for testing
if __name__ == "__main__":
    memory = TasteMemory()
    print(f"Stats: {memory.get_stats()}")
    print(f"Sector performance: {memory.get_sector_performance()}")
