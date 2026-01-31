"""
Learning Engine - Performance Feedback Loop

Tracks article performance and feeds back into editorial weights.
Enables continuous improvement of content quality based on audience engagement.
"""

import os
import sys
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

# Allow running from repo root without PYTHONPATH
AGENT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if AGENT_ROOT not in sys.path:
    sys.path.insert(0, AGENT_ROOT)

from config.manager import config
from shared.logger import get_logger
from shared.models import ArticlePerformance, LearningInsights
from skills.gemini_client import GeminiAgent
from skills.content_brain import ContentBrain

logger = get_logger("LearningEngine")


class LearningEngine:
    """
    Feedback loop for editorial improvement.

    Tracks article performance and uses LLM analysis to identify
    patterns and adjust editorial weights.
    """

    def __init__(
        self,
        client: Optional[GeminiAgent] = None,
        brain: Optional[ContentBrain] = None,
    ):
        self.client = client or GeminiAgent()
        self.brain = brain or ContentBrain()

        self.config = {
            "reflection_interval_hours": config.get(
                "learning.reflection_interval_hours", 24
            ),
            "min_articles_for_learning": config.get(
                "learning.min_articles_for_learning", 10
            ),
            "weight_adjustment_rate": config.get(
                "learning.weight_adjustment_rate", 0.1
            ),
            "max_weight_multiplier": config.get(
                "autonomous.max_weight_multiplier", 2.0
            ),
            "min_weight_multiplier": config.get(
                "autonomous.min_weight_multiplier", 0.5
            ),
        }

        self.last_reflected = datetime.min
        self._ensure_performance_table()

    def _ensure_performance_table(self):
        """Create performance table if it doesn't exist."""
        cur = self.brain.conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS article_performance (
                article_slug TEXT PRIMARY KEY,
                views INTEGER DEFAULT 0,
                avg_time_seconds REAL DEFAULT 0,
                shares INTEGER DEFAULT 0,
                bounce_rate REAL DEFAULT 0,
                scroll_depth REAL DEFAULT 0,
                engagement_score REAL DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS learning_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reflection_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                insights_json TEXT,
                weight_adjustments_json TEXT
            )
        """)

        self.brain.conn.commit()

    def update_weights(self) -> LearningInsights:
        """
        Analyze performance and update editorial weights.

        Returns:
            LearningInsights with patterns and recommendations
        """
        logger.info("updating_weights")

        # Get top and bottom performers
        top_articles = self.get_top_performers(limit=20)
        bottom_articles = self.get_bottom_performers(limit=20)

        if len(top_articles) < self.config["min_articles_for_learning"]:
            logger.info("insufficient_data", count=len(top_articles))
            return LearningInsights(
                patterns_identified=["Insufficient data for learning"],
                analysis_date=datetime.now(),
            )

        # Analyze patterns using LLM
        patterns = self._analyze_patterns(top_articles, bottom_articles)

        # Build insights
        insights = LearningInsights(
            top_performing_topics=patterns.get("top_performing_patterns", []),
            underperforming_topics=patterns.get("underperforming_patterns", []),
            recommended_weight_adjustments=patterns.get("recommended_adjustments", {}),
            patterns_identified=patterns.get("insights", []),
            analysis_date=datetime.now(),
        )

        # Save to history
        self._save_learning_history(insights)

        logger.info("weights_updated", patterns=len(insights.patterns_identified))
        return insights

    def _has_article_columns(self) -> bool:
        """Check if articles table has the required columns for join."""
        cur = self.brain.conn.cursor()
        try:
            cur.execute("PRAGMA table_info(articles)")
            columns = {row[1] for row in cur.fetchall()}
            return "category" in columns and "content_type" in columns
        except Exception:
            return False

    def get_top_performers(self, limit: int = 20) -> List[Dict]:
        """Get top performing articles by engagement score."""
        cur = self.brain.conn.cursor()

        if self._has_article_columns():
            cur.execute(
                """
                SELECT ap.*, a.title, a.category, a.content_type
                FROM article_performance ap
                LEFT JOIN articles a ON ap.article_slug = a.slug
                ORDER BY ap.engagement_score DESC
                LIMIT ?
            """,
                (limit,),
            )
        else:
            cur.execute(
                """
                SELECT ap.*, NULL as title, NULL as category, NULL as content_type
                FROM article_performance ap
                ORDER BY ap.engagement_score DESC
                LIMIT ?
            """,
                (limit,),
            )

        return [dict(row) for row in cur.fetchall()]

    def get_bottom_performers(self, limit: int = 20) -> List[Dict]:
        """Get bottom performing articles by engagement score."""
        cur = self.brain.conn.cursor()

        if self._has_article_columns():
            cur.execute(
                """
                SELECT ap.*, a.title, a.category, a.content_type
                FROM article_performance ap
                LEFT JOIN articles a ON ap.article_slug = a.slug
                WHERE ap.engagement_score > 0
                ORDER BY ap.engagement_score ASC
                LIMIT ?
            """,
                (limit,),
            )
        else:
            cur.execute(
                """
                SELECT ap.*, NULL as title, NULL as category, NULL as content_type
                FROM article_performance ap
                WHERE ap.engagement_score > 0
                ORDER BY ap.engagement_score ASC
                LIMIT ?
            """,
                (limit,),
            )

        return [dict(row) for row in cur.fetchall()]

    def record_performance(self, perf: ArticlePerformance) -> bool:
        """
        Record or update performance metrics for an article.

        Args:
            perf: ArticlePerformance model with metrics

        Returns:
            True if successful
        """
        cur = self.brain.conn.cursor()

        cur.execute(
            """
            INSERT INTO article_performance (
                article_slug, views, avg_time_seconds, shares,
                bounce_rate, scroll_depth, engagement_score, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(article_slug) DO UPDATE SET
                views=excluded.views,
                avg_time_seconds=excluded.avg_time_seconds,
                shares=excluded.shares,
                bounce_rate=excluded.bounce_rate,
                scroll_depth=excluded.scroll_depth,
                engagement_score=excluded.engagement_score,
                last_updated=CURRENT_TIMESTAMP
        """,
            (
                perf.article_slug,
                perf.views,
                perf.avg_time_seconds,
                perf.shares,
                perf.bounce_rate,
                perf.scroll_depth,
                perf.engagement_score,
            ),
        )

        self.brain.conn.commit()
        return True

    def get_performance(self, slug: str) -> Optional[Dict]:
        """Get performance metrics for an article."""
        cur = self.brain.conn.cursor()

        cur.execute(
            "SELECT * FROM article_performance WHERE article_slug = ?",
            (slug,),
        )

        row = cur.fetchone()
        return dict(row) if row else None

    def calculate_engagement_score(
        self,
        views: int,
        avg_time_seconds: float,
        shares: int,
        bounce_rate: float,
    ) -> float:
        """
        Calculate engagement score from raw metrics.

        Score is 0-10 based on weighted factors.
        """
        # Normalize factors
        view_score = min(views / 1000, 1.0) * 2  # Max 2 points for 1000+ views
        time_score = min(avg_time_seconds / 180, 1.0) * 3  # Max 3 points for 3+ min
        share_score = min(shares / 50, 1.0) * 3  # Max 3 points for 50+ shares
        bounce_penalty = bounce_rate * 2  # Penalty up to 2 points

        score = view_score + time_score + share_score - bounce_penalty
        return max(0, min(10, score))

    def _analyze_patterns(self, top: List[Dict], bottom: List[Dict]) -> Dict:
        """Use LLM to identify success patterns."""
        if not self.client:
            return {"insights": ["No LLM available for pattern analysis"]}

        prompt = f"""Analyze these high-performing and low-performing articles to identify patterns.

TOP PERFORMERS (high engagement):
{self._format_articles(top[:10])}

BOTTOM PERFORMERS (low engagement):
{self._format_articles(bottom[:10])}

Identify patterns:
1. What topics/sectors perform best?
2. What content types (Guide/Analysis/News) work best?
3. What characteristics predict success?
4. What should we avoid?

Return JSON:
{{
    "top_performing_patterns": ["<pattern 1>", "<pattern 2>"],
    "underperforming_patterns": ["<pattern 1>", "<pattern 2>"],
    "recommended_adjustments": {{
        "<content_type>": <multiplier 0.5-2.0>,
        ...
    }},
    "insights": ["<actionable insight 1>", "<actionable insight 2>"]
}}"""

        try:
            return self.client.generate_json(prompt)
        except Exception as e:
            logger.error("pattern_analysis_error", error=str(e))
            return {"insights": [f"Analysis error: {str(e)}"]}

    def _format_articles(self, articles: List[Dict]) -> str:
        """Format articles for LLM prompt."""
        lines = []
        for a in articles:
            lines.append(
                f"- {a.get('title', 'Unknown')} "
                f"(type: {a.get('content_type', '?')}, "
                f"category: {a.get('category', '?')}, "
                f"score: {a.get('engagement_score', 0):.1f})"
            )
        return "\n".join(lines) if lines else "No articles"

    def _apply_bounds(self, value: float) -> float:
        """Apply min/max bounds to weight multiplier."""
        max_mult = self.config["max_weight_multiplier"]
        min_mult = self.config["min_weight_multiplier"]
        return max(min_mult, min(max_mult, value))

    def _save_learning_history(self, insights: LearningInsights):
        """Save learning insights to history."""
        import json

        cur = self.brain.conn.cursor()

        insights_json = json.dumps(
            {
                "top_performing_topics": insights.top_performing_topics,
                "underperforming_topics": insights.underperforming_topics,
                "patterns_identified": insights.patterns_identified,
            }
        )

        weights_json = json.dumps(insights.recommended_weight_adjustments)

        cur.execute(
            """
            INSERT INTO learning_history (insights_json, weight_adjustments_json)
            VALUES (?, ?)
        """,
            (insights_json, weights_json),
        )

        self.brain.conn.commit()

    def should_reflect(self) -> bool:
        """Check if it's time for a reflection cycle."""
        interval = timedelta(hours=self.config["reflection_interval_hours"])
        return datetime.now() - self.last_reflected > interval

    def run_reflection_cycle(self) -> Optional[LearningInsights]:
        """Run a full reflection cycle if due."""
        if not self.should_reflect():
            logger.info("reflection_not_due")
            return None

        logger.info("running_reflection_cycle")
        insights = self.update_weights()
        self.last_reflected = datetime.now()

        return insights


if __name__ == "__main__":
    # Quick test
    engine = LearningEngine()

    print("Checking for reflection...")
    if engine.should_reflect():
        insights = engine.run_reflection_cycle()
        if insights:
            print(f"Patterns: {insights.patterns_identified}")
            print(f"Weight adjustments: {insights.recommended_weight_adjustments}")
    else:
        print("Reflection not due yet")
