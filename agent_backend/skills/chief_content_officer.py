"""
Chief Content Officer (CCO) 🧠👔
The Strategic Strategist.
Maintains the "Authority Mix" of content.
Decides whether to Hunt or Write, and what TYPE to focus on.
"""

import logging
import random
from skills.content_brain import ContentBrain

logger = logging.getLogger("CCO")

# The Golden Ratio for Authority Sites
AUTHORITY_MIX = {
    "Guide": 0.40,       # Evergreen specific how-tos
    "Analysis": 0.25,    # Deep dives / Trends
    "News": 0.20,        # Timely updates
    "Review": 0.15       # Product/Tech reviews
}

class ChiefContentOfficer:
    def __init__(self):
        self.brain = ContentBrain()
        self.mix = AUTHORITY_MIX

    def analyze_current_mix(self):
        stats = self.brain.get_stats()
        total_topics = sum(stats['types'].values())
        
        if total_topics == 0:
            return {k: 0 for k in self.mix.keys()}
            
        current_ratios = {
            k: stats['types'].get(k, 0) / total_topics 
            for k in self.mix.keys()
        }
        return current_ratios

    def decide_strategy(self):
        """
        Returns a directive: 
        {"action": "HUNT"|"WRITE", "params": {...}}
        """
        stats = self.brain.get_stats()
        
        # 1. Pipeline Health Check
        proposed_count = stats['status'].get('PROPOSED', 0)
        
        # If queue is starving, we MUST hunt
        if proposed_count < 3:
            # Diagnose WHAT to hunt for
            current = self.analyze_current_mix()
            
            # Find biggest deficit
            biggest_deficit = None
            max_diff = -1.0
            
            for type_, target in self.mix.items():
                diff = target - current.get(type_, 0)
                if diff > max_diff:
                    max_diff = diff
                    biggest_deficit = type_
            
            logger.info(f"📉 Deficit Alert: We need more {biggest_deficit} (Target: {self.mix[biggest_deficit]:.0%}, Current: {current.get(biggest_deficit, 0):.0%})")
            
            return {
                "action": "HUNT",
                "focus_type": biggest_deficit,
                "reason": f"Replenishing queue with {biggest_deficit}"
            }
            
        # 2. If queue is healthy, we WRITE
        # Pick a topic that helps the mix? 
        # For now, GhostWriter picks the best gap_score regardless of type.
        # But CCO could filter the ID.
        return {
            "action": "WRITE",
            "reason": "Queue healthy, continue publishing."
        }

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    cco = ChiefContentOfficer()
    print(cco.decide_strategy())
