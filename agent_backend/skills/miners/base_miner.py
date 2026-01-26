"""
BaseMiner: Abstract interface for all content miners.
Defines the common schema for multi-source evidence ingestion.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime


@dataclass
class EvidenceItem:
    """
    Common schema for all evidence sources.
    
    All miners must return evidence in this format so that
    the GhostWriter pipeline can process them uniformly.
    """
    id: str
    title: str
    url: str
    raw_content: str  # Transcript, article text, abstract, etc.
    source_type: str  # "video", "article", "paper", "rss", "podcast"
    publisher: str
    published: Optional[datetime] = None
    credibility_weight: int = 5  # 1-10 scale (10 = highest credibility)
    domain: str = ""
    snippet: str = ""  # Short excerpt for display
    identifier: str = ""  # DOI, video ID, etc.
    accessed_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: dict = field(default_factory=dict)  # Source-specific metadata
    
    def to_source_item_dict(self) -> dict:
        """Convert to dict compatible with existing SourceItem format."""
        return {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "publisher": self.publisher,
            "published": self.published.isoformat() if self.published else None,
            "source_type": self.source_type,
            "snippet": self.snippet or self.raw_content[:500],
            "quality_score": self.credibility_weight,
            "domain": self.domain,
            "identifier": self.identifier,
            "accessed_at": self.accessed_at,
            "credibility_weight": self.credibility_weight,
            "raw_content": self.raw_content
        }


class BaseMiner(ABC):
    """
    Abstract interface for all content miners.
    
    Implement this to create new source integrations (YouTube, articles, papers, etc.).
    All miners must return List[EvidenceItem] from their fetch() method.
    
    Credibility Weight Guidelines:
        10: Official government sources (RBI, MHA, BIS circulars)
         9: Peer-reviewed academic papers
         8: Major news outlets (Reuters, ET, ToI)
         7: Trade publications, industry reports
         6: Expert blogs, vendor documentation
         5: Video content (conferences, webinars)
         4: Podcasts, interviews
         3: Social media, forums
         2: User-generated content
         1: Unverified sources
    """
    
    @property
    @abstractmethod
    def source_type(self) -> str:
        """
        Return the source type identifier.
        
        Examples: "video", "article", "paper", "rss", "podcast"
        """
        pass
    
    @property
    def default_credibility(self) -> int:
        """Default credibility weight for this source type."""
        return 5
    
    @abstractmethod
    def fetch(self, query: str, limit: int = 5) -> List[EvidenceItem]:
        """
        Fetch evidence from this source.
        
        Args:
            query: Search query or topic
            limit: Maximum number of items to return
            
        Returns:
            List of EvidenceItem objects
        """
        pass
    
    def is_available(self) -> bool:
        """
        Check if this miner is properly configured and available.
        
        Override to check for API keys, network connectivity, etc.
        """
        return True
    
    def _make_id(self, index: int) -> str:
        """Generate evidence ID in S# format."""
        return f"S{index + 1}"
