"""
Content Intelligence Platform: Pluggable Miners
Multi-source content ingestion for the Autonomous Newsroom.
"""

from .base_miner import BaseMiner, EvidenceItem
from .youtube_miner import YouTubeMiner
from .article_miner import ArticleMiner
from .paper_miner import PaperMiner

__all__ = ["BaseMiner", "EvidenceItem", "YouTubeMiner", "ArticleMiner", "PaperMiner"]
