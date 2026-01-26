"""
Taste Anchors: Exemplar-Based Quality Scoring

Stores embeddings from premium sources as "taste anchors" and uses them
to score new drafts by cosine similarity to high-quality journalism.
"""

from __future__ import annotations

import sqlite3
import hashlib
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from config.manager import config
from shared.logger import get_logger

logger = get_logger("TasteAnchors")


@dataclass
class Exemplar:
    """An exemplar article from a premium source."""
    id: str
    source_id: str
    title: str
    url: str
    embedding: Optional[List[float]]
    credibility_weight: int
    ingested_at: datetime
    word_count: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "title": self.title,
            "url": self.url,
            "credibility_weight": self.credibility_weight,
            "ingested_at": self.ingested_at.isoformat(),
            "word_count": self.word_count
        }


class TasteAnchors:
    """
    Exemplar-based quality scoring system.
    
    Stores embeddings from premium articles and uses them to:
    1. Score new drafts by similarity to high-quality journalism
    2. Provide weighted quality distance from "master" writing
    3. Calibrate TasteModel's editorial preferences
    """
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or config.get(
            "premium_sources.anchors_path",
            ".agent/taste_anchors.db"
        )
        
        # Ensure directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_db()
        
        # Cache for weighted mean embedding
        self._weighted_mean_cache = None
        self._cache_valid = False
        
        logger.info("taste_anchors_initialized", db_path=self.db_path)
    
    def _init_db(self):
        """Initialize SQLite database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS exemplars (
                    id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT,
                    embedding BLOB,
                    credibility_weight INTEGER DEFAULT 5,
                    ingested_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    word_count INTEGER DEFAULT 0
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_exemplars_source 
                ON exemplars(source_id)
            """)
            
            conn.commit()
    
    # =========================================================================
    # Exemplar Management
    # =========================================================================
    
    def add_exemplar(
        self,
        source_id: str,
        title: str,
        content: str,
        url: str = "",
        credibility_weight: int = 5,
        embedding: Optional[List[float]] = None
    ) -> str:
        """
        Add an exemplar article from a premium source.
        
        Args:
            source_id: ID of the authoritative source
            title: Article title
            content: Full article text (for embedding if not provided)
            url: Article URL
            credibility_weight: Source credibility (1-10)
            embedding: Pre-computed embedding (optional)
            
        Returns:
            Exemplar ID
        """
        # Generate ID from content hash
        exemplar_id = hashlib.md5(
            f"{source_id}:{title}:{content[:500]}".encode()
        ).hexdigest()[:16]
        
        # Generate embedding if not provided
        if embedding is None:
            embedding = self._generate_embedding(content)
        
        # Serialize embedding
        embedding_blob = self._serialize_embedding(embedding) if embedding else None
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO exemplars 
                (id, source_id, title, url, embedding, credibility_weight, 
                 ingested_at, word_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                exemplar_id, source_id, title, url, embedding_blob,
                credibility_weight, datetime.now().isoformat(),
                len(content.split())
            ))
            conn.commit()
        
        # Invalidate cache
        self._cache_valid = False
        
        logger.info(
            "exemplar_added",
            exemplar_id=exemplar_id,
            source_id=source_id,
            title=title[:50]
        )
        
        return exemplar_id
    
    def get_exemplar(self, exemplar_id: str) -> Optional[Exemplar]:
        """Get an exemplar by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM exemplars WHERE id = ?",
                (exemplar_id,)
            ).fetchone()
            
            if row:
                return self._row_to_exemplar(row)
            return None
    
    def list_exemplars(
        self, 
        source_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Exemplar]:
        """List exemplars, optionally filtered by source."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            if source_id:
                rows = conn.execute(
                    "SELECT * FROM exemplars WHERE source_id = ? ORDER BY ingested_at DESC LIMIT ?",
                    (source_id, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM exemplars ORDER BY credibility_weight DESC, ingested_at DESC LIMIT ?",
                    (limit,)
                ).fetchall()
            
            return [self._row_to_exemplar(row) for row in rows]
    
    def delete_exemplar(self, exemplar_id: str) -> bool:
        """Delete an exemplar."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM exemplars WHERE id = ?", (exemplar_id,))
            conn.commit()
        
        self._cache_valid = False
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about stored exemplars."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            total = conn.execute("SELECT COUNT(*) as count FROM exemplars").fetchone()["count"]
            
            by_source = conn.execute("""
                SELECT source_id, COUNT(*) as count, AVG(credibility_weight) as avg_weight
                FROM exemplars GROUP BY source_id
            """).fetchall()
            
            return {
                "total_exemplars": total,
                "by_source": [
                    {
                        "source_id": row["source_id"],
                        "count": row["count"],
                        "avg_weight": round(row["avg_weight"], 2)
                    }
                    for row in by_source
                ]
            }
    
    # =========================================================================
    # Quality Scoring
    # =========================================================================
    
    def score_against_exemplars(
        self, 
        text: str,
        embedding: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Score text against exemplar embeddings.
        
        Returns:
            Dict with overall score and per-source breakdown
        """
        if embedding is None:
            embedding = self._generate_embedding(text)
        
        if embedding is None:
            return {"score": 0.5, "error": "Could not generate embedding"}
        
        # Get all exemplars with embeddings
        exemplars = self._get_exemplars_with_embeddings()
        
        if not exemplars:
            return {"score": 0.5, "message": "No exemplars available"}
        
        # Calculate weighted similarity
        similarities = []
        weights = []
        source_scores = {}
        
        for exemplar in exemplars:
            if exemplar.embedding:
                sim = self._cosine_similarity(embedding, exemplar.embedding)
                weight = exemplar.credibility_weight
                
                similarities.append(sim)
                weights.append(weight)
                
                # Track per-source
                if exemplar.source_id not in source_scores:
                    source_scores[exemplar.source_id] = {"similarities": [], "weights": []}
                source_scores[exemplar.source_id]["similarities"].append(sim)
                source_scores[exemplar.source_id]["weights"].append(weight)
        
        if not similarities:
            return {"score": 0.5, "message": "No embeddings available"}
        
        # Weighted average
        total_weight = sum(weights)
        weighted_score = sum(s * w for s, w in zip(similarities, weights)) / total_weight
        
        # Per-source breakdown
        source_breakdown = {}
        for source_id, data in source_scores.items():
            w_sum = sum(data["weights"])
            source_breakdown[source_id] = {
                "score": sum(s * w for s, w in zip(data["similarities"], data["weights"])) / w_sum,
                "exemplar_count": len(data["similarities"])
            }
        
        return {
            "score": round(weighted_score, 4),
            "exemplar_count": len(similarities),
            "source_breakdown": source_breakdown,
            "quality_tier": self._score_to_tier(weighted_score)
        }
    
    def get_weighted_mean_embedding(self) -> Optional[List[float]]:
        """
        Get the weighted mean of all exemplar embeddings.
        Useful for fast comparison.
        """
        if self._cache_valid and self._weighted_mean_cache is not None:
            return self._weighted_mean_cache
        
        exemplars = self._get_exemplars_with_embeddings()
        
        if not exemplars:
            return None
        
        embeddings = []
        weights = []
        
        for ex in exemplars:
            if ex.embedding:
                embeddings.append(ex.embedding)
                weights.append(ex.credibility_weight)
        
        if not embeddings:
            return None
        
        # Weighted mean
        embeddings_arr = np.array(embeddings)
        weights_arr = np.array(weights).reshape(-1, 1)
        
        weighted_mean = (embeddings_arr * weights_arr).sum(axis=0) / weights_arr.sum()
        
        self._weighted_mean_cache = weighted_mean.tolist()
        self._cache_valid = True
        
        return self._weighted_mean_cache
    
    # =========================================================================
    # Embedding Helpers
    # =========================================================================
    
    def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text using available model."""
        try:
            # Try using Gemini embeddings
            from skills.gemini_client import GeminiAgent
            agent = GeminiAgent()
            return agent.generate_embedding(text[:8000])  # Limit to avoid token overflow
        except Exception as e:
            logger.warning("embedding_generation_failed", error=str(e))
            return None
    
    def _serialize_embedding(self, embedding: List[float]) -> bytes:
        """Serialize embedding to bytes for storage."""
        return json.dumps(embedding).encode()
    
    def _deserialize_embedding(self, blob: bytes) -> List[float]:
        """Deserialize embedding from storage."""
        return json.loads(blob.decode())
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        a_arr = np.array(a)
        b_arr = np.array(b)
        
        dot_product = np.dot(a_arr, b_arr)
        norm_a = np.linalg.norm(a_arr)
        norm_b = np.linalg.norm(b_arr)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return float(dot_product / (norm_a * norm_b))
    
    def _score_to_tier(self, score: float) -> str:
        """Convert numeric score to quality tier."""
        if score >= 0.85:
            return "exemplary"
        elif score >= 0.70:
            return "high"
        elif score >= 0.55:
            return "moderate"
        elif score >= 0.40:
            return "below_average"
        else:
            return "low"
    
    def _get_exemplars_with_embeddings(self) -> List[Exemplar]:
        """Get all exemplars that have embeddings."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM exemplars WHERE embedding IS NOT NULL"
            ).fetchall()
            return [self._row_to_exemplar(row) for row in rows]
    
    def _row_to_exemplar(self, row: sqlite3.Row) -> Exemplar:
        """Convert database row to Exemplar."""
        embedding = None
        if row["embedding"]:
            embedding = self._deserialize_embedding(row["embedding"])
        
        return Exemplar(
            id=row["id"],
            source_id=row["source_id"],
            title=row["title"],
            url=row["url"] or "",
            embedding=embedding,
            credibility_weight=row["credibility_weight"],
            ingested_at=datetime.fromisoformat(row["ingested_at"]),
            word_count=row["word_count"]
        )


# =============================================================================
# CLI for Testing
# =============================================================================

if __name__ == "__main__":
    anchors = TasteAnchors()
    
    # Add a mock exemplar
    print("Adding mock exemplar...")
    exemplar_id = anchors.add_exemplar(
        source_id="economist",
        title="The Future of AI Regulation",
        content="A comprehensive analysis of global AI regulatory frameworks...",
        url="https://economist.com/ai-regulation",
        credibility_weight=10
    )
    print(f"  Added: {exemplar_id}")
    
    print("\nStats:")
    stats = anchors.get_stats()
    print(f"  Total exemplars: {stats['total_exemplars']}")
    
    print("\nScoring test text...")
    result = anchors.score_against_exemplars(
        "This is a test article about cybersecurity trends."
    )
    print(f"  Score: {result.get('score', 'N/A')}")
    print(f"  Tier: {result.get('quality_tier', 'N/A')}")
