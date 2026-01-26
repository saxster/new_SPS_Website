"""
TasteModel: The learned preferences of the Autopoietic Newsroom.
Adjusts weights based on feedback to develop editorial taste over time.
"""

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import random

from config.manager import config
from shared.logger import get_logger
from skills.taste_memory import TasteMemory, ArticleFeedback

logger = get_logger("TasteModel")


@dataclass
class TasteWeights:
    """Current state of learned weights."""
    sectors: Dict[str, float]
    content_types: Dict[str, float]
    sources: Dict[str, float]
    
    def to_dict(self) -> Dict[str, Dict[str, float]]:
        return {
            'sectors': dict(self.sectors),
            'content_types': dict(self.content_types),
            'sources': dict(self.sources)
        }


class TasteModel:
    """
    The learned taste of the Autonomous Newsroom.
    
    Adjusts weights through reinforcement:
    - Success → Boost weight
    - Failure → Reduce weight
    - Exploration → Sometimes ignore weights
    """
    
    def __init__(self, memory: Optional[TasteMemory] = None):
        self.memory = memory or TasteMemory()
        
        # Configuration
        self.learning_rate = config.get("autonomous.learning_rate", 0.1)
        self.exploration_rate = config.get("autonomous.exploration_rate", 0.2)
        self.max_weight = config.get("autonomous.max_weight_multiplier", 2.0)
        self.min_weight = config.get("autonomous.min_weight_multiplier", 0.5)
        self.boost_threshold = config.get("autonomous.boost_on_quality_above", 75)
        self.penalize_threshold = config.get("autonomous.penalize_on_quality_below", 50)
        
        # Load weights from memory
        self.sector_weights = defaultdict(lambda: 1.0)
        self.content_type_weights = defaultdict(lambda: 1.0)
        self.source_weights = defaultdict(lambda: 1.0)
        self._load_weights()
        
        logger.info("taste_model_initialized", 
                   learning_rate=self.learning_rate,
                   exploration_rate=self.exploration_rate)
    
    # =========================================================================
    # Weight Management
    # =========================================================================
    
    def _load_weights(self):
        """Load weights from persistent memory."""
        sector_weights = self.memory.get_all_weights("sector")
        for k, v in sector_weights.items():
            self.sector_weights[k] = v
        
        content_type_weights = self.memory.get_all_weights("content_type")
        for k, v in content_type_weights.items():
            self.content_type_weights[k] = v
        
        source_weights = self.memory.get_all_weights("source")
        for k, v in source_weights.items():
            self.source_weights[k] = v
        
        logger.info("weights_loaded", 
                   sectors=len(sector_weights),
                   content_types=len(content_type_weights),
                   sources=len(source_weights))
    
    def _save_weights(self):
        """Persist current weights to memory."""
        for k, v in self.sector_weights.items():
            self.memory.save_weight("sector", k, v)
        
        for k, v in self.content_type_weights.items():
            self.memory.save_weight("content_type", k, v)
        
        for k, v in self.source_weights.items():
            self.memory.save_weight("source", k, v)
    
    def get_weights(self) -> TasteWeights:
        """Get current weight state."""
        return TasteWeights(
            sectors=dict(self.sector_weights),
            content_types=dict(self.content_type_weights),
            sources=dict(self.source_weights)
        )
    
    # =========================================================================
    # Learning
    # =========================================================================
    
    def update(self, feedback: ArticleFeedback):
        """
        Update weights based on feedback.
        
        Learning rules:
        - High quality published → Boost
        - Blocked or low quality → Penalize
        - Within normal range → Small adjustment
        """
        sector = feedback.sector or "unknown"
        content_type = feedback.content_type or "unknown"
        
        # Record feedback in memory
        self.memory.record_feedback(feedback)
        
        # Determine adjustment
        if feedback.was_published and feedback.quality_score >= self.boost_threshold:
            # Success! Boost weights
            adjustment = 1.0 + self.learning_rate
            logger.info("taste_boost", 
                       sector=sector, 
                       content_type=content_type,
                       quality=feedback.quality_score)
        
        elif feedback.was_blocked or feedback.quality_score < self.penalize_threshold:
            # Failure. Reduce weights
            adjustment = 1.0 - self.learning_rate
            logger.info("taste_penalize", 
                       sector=sector, 
                       content_type=content_type,
                       blocked=feedback.was_blocked,
                       quality=feedback.quality_score)
        
        else:
            # Normal performance. Small adjustment based on prediction error
            error = feedback.prediction_error
            adjustment = 1.0 + (error * self.learning_rate * 0.5)
        
        # Apply adjustment with bounds
        self.sector_weights[sector] = self._bound_weight(
            self.sector_weights[sector] * adjustment
        )
        self.content_type_weights[content_type] = self._bound_weight(
            self.content_type_weights[content_type] * adjustment
        )
        
        # Persist
        self._save_weights()
    
    def _bound_weight(self, weight: float) -> float:
        """Clamp weight to configured bounds."""
        return max(self.min_weight, min(self.max_weight, weight))
    
    # =========================================================================
    # Scoring
    # =========================================================================
    
    def adjust_score(self, proposal: Any) -> float:
        """
        Apply learned taste to a proposal's score.
        
        Args:
            proposal: TopicProposal with score, sector, content_type
            
        Returns:
            Adjusted score incorporating learned preferences
        """
        base_score = getattr(proposal, 'score', 0.5)
        sector = getattr(proposal, 'sector', None) or self._infer_sector(proposal)
        content_type = getattr(proposal, 'content_type', 'Guide')
        
        # Get multipliers
        sector_mult = self.sector_weights.get(sector, 1.0)
        type_mult = self.content_type_weights.get(content_type, 1.0)
        
        # Combine multiplicatively
        adjusted = base_score * sector_mult * type_mult
        
        # Normalize back to 0-1 range
        return min(1.0, max(0.0, adjusted))
    
    def _infer_sector(self, proposal: Any) -> str:
        """Infer sector from proposal topic text."""
        topic = getattr(proposal, 'topic', '').lower()
        
        sector_keywords = {
            'cybersecurity': ['cyber', 'breach', 'hack', 'ransomware', 'data'],
            'physical_security': ['cctv', 'surveillance', 'guard', 'access control'],
            'fire_safety': ['fire', 'evacuation', 'smoke', 'sprinkler'],
            'compliance': ['compliance', 'regulation', 'rbi', 'sebi', 'gdpr'],
            'risk_management': ['risk', 'audit', 'assessment', 'enterprise']
        }
        
        for sector, keywords in sector_keywords.items():
            if any(kw in topic for kw in keywords):
                return sector
        
        return 'general'
    
    # =========================================================================
    # Filtering
    # =========================================================================
    
    def filter_proposals(
        self, 
        proposals: List[Any], 
        max_count: int = 5
    ) -> List[Any]:
        """
        Filter and rank proposals using learned taste.
        
        Includes exploration: occasionally picks lower-ranked proposals.
        """
        if not proposals:
            return []
        
        # Adjust all scores with taste
        for p in proposals:
            p.adjusted_score = self.adjust_score(p)
        
        # Sort by adjusted score
        ranked = sorted(proposals, key=lambda p: p.adjusted_score, reverse=True)
        
        # Exploitation: Take top performers
        exploit_count = int(max_count * (1 - self.exploration_rate))
        selected = ranked[:exploit_count]
        
        # Exploration: Add some random picks from remaining
        remaining = ranked[exploit_count:]
        explore_count = max_count - exploit_count
        if remaining and explore_count > 0:
            explored = random.sample(remaining, min(explore_count, len(remaining)))
            selected.extend(explored)
            logger.info("exploration_applied", 
                       exploited=exploit_count, 
                       explored=len(explored))
        
        return selected[:max_count]
    
    # =========================================================================
    # Reflection
    # =========================================================================
    
    def get_taste_summary(self) -> Dict:
        """Get a summary of current taste preferences."""
        sector_perf = self.memory.get_sector_performance(30)
        content_perf = self.memory.get_content_type_performance(30)
        
        # Find favorites
        top_sector = max(self.sector_weights.items(), key=lambda x: x[1], default=("none", 1.0))
        top_type = max(self.content_type_weights.items(), key=lambda x: x[1], default=("none", 1.0))
        
        return {
            'favorite_sector': top_sector[0],
            'favorite_sector_weight': top_sector[1],
            'favorite_content_type': top_type[0],
            'favorite_type_weight': top_type[1],
            'sector_performance': sector_perf,
            'content_type_performance': content_perf,
            'overall_success_rate': self.memory.get_success_rate(30)
        }
    
    def reflect(self, llm=None) -> str:
        """
        Generate a reflection on current taste and performance.
        
        Uses LLM to analyze patterns and suggest adjustments.
        """
        if llm is None:
            try:
                from skills.gemini_client import GeminiAgent
                llm = GeminiAgent()
            except Exception:
                return "Reflection unavailable (no LLM)"
        
        summary = self.get_taste_summary()
        recent = self.memory.get_recent_feedback(14)
        
        successes = [f.topic for f in recent if f.success]
        failures = [f.topic for f in recent if not f.success]
        
        prompt = f"""You are an editorial AI reflecting on your recent performance.

CURRENT TASTE:
- Favorite sector: {summary['favorite_sector']} (weight: {summary['favorite_sector_weight']:.2f})
- Favorite content type: {summary['favorite_content_type']} (weight: {summary['favorite_type_weight']:.2f})
- Overall success rate: {summary['overall_success_rate']:.1%}

RECENT SUCCESSES ({len(successes)}):
{chr(10).join(successes[:5]) if successes else "None yet"}

RECENT FAILURES ({len(failures)}):
{chr(10).join(failures[:5]) if failures else "None yet"}

Reflect on:
1. What patterns do you see?
2. What should you do more of?
3. What should you avoid?
4. Any emerging opportunities?

Be brief and actionable (3-4 sentences max)."""

        try:
            reflection = llm.generate(prompt)
            
            # Store reflection
            self.memory.save_reflection(reflection, {
                'summary': summary,
                'successes': len(successes),
                'failures': len(failures)
            })
            
            return reflection
        except Exception as e:
            logger.error("reflection_failed", error=str(e))
            return f"Reflection failed: {e}"


# CLI for testing
if __name__ == "__main__":
    model = TasteModel()
    print("Current weights:")
    weights = model.get_weights()
    print(f"  Sectors: {weights.sectors}")
    print(f"  Content types: {weights.content_types}")
    print(f"\nTaste summary:")
    print(model.get_taste_summary())
