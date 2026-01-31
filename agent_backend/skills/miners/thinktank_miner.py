"""
ThinkTankMiner: Fetches research and analysis from think tanks.

Sources include:
- Tier 1 (Indian): IDSA, ORF, Carnegie India, Takshashila, Gateway House
- Tier 2 (International): CSIS, Brookings, RAND, Chatham House, IISS
- Tier 3 (Industry): DSCI, NASSCOM, FICCI, CII

Provides high-quality analytical content for the editorial pipeline.
"""

import os
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from urllib.parse import urlparse
import hashlib

from .base_miner import BaseMiner, EvidenceItem
from config.manager import config
from shared.logger import get_logger

logger = get_logger("ThinkTankMiner")

# Check for feedparser dependency
try:
    import feedparser

    FEEDPARSER_AVAILABLE = True
except ImportError:
    FEEDPARSER_AVAILABLE = False
    feedparser = None


class ThinkTankMiner(BaseMiner):
    """
    Miner for think tank research and analysis.

    Fetches from RSS feeds of major think tanks focused on:
    - Security and defence
    - Cybersecurity and technology
    - Geopolitics and foreign policy
    - Compliance and governance

    Credibility weights:
        9-10: Major international/national think tanks
        8: Industry associations
        7: Regional/specialized think tanks
    """

    # Keyword filters for security-relevant content
    SECURITY_KEYWORDS = {
        "security",
        "cyber",
        "defence",
        "defense",
        "threat",
        "vulnerability",
        "attack",
        "privacy",
        "data protection",
        "compliance",
        "regulation",
        "risk",
        "intelligence",
        "terrorism",
        "crime",
        "surveillance",
        "encryption",
        "infrastructure",
        "critical",
        "resilience",
        "incident",
        "breach",
        "hack",
        "malware",
        "ransomware",
        "phishing",
        "fraud",
        "geopolitics",
        "conflict",
        "warfare",
        "military",
        "strategic",
        "national security",
        "border",
        "espionage",
        "sanctions",
        "policy",
        "governance",
        "audit",
        "framework",
        "standard",
        "certification",
        "dpdp",
        "gdpr",
        "iso",
        "nist",
        "india",
        "indian",
        "asia",
        "pacific",
        "indo-pacific",
    }

    def __init__(self):
        self.sources = self._load_sources()
        self.max_items_per_source = config.get(
            "thinktank_miner.max_items_per_source", 10
        )

    def _load_sources(self) -> Dict[str, List[Dict]]:
        """Load think tank sources from config."""
        sources = {
            "tier_1_india": [],
            "tier_2_international": [],
            "tier_3_industry": [],
        }

        for tier in sources.keys():
            tier_sources = config.get(f"thinktank_miner.sources.{tier}", [])
            if tier_sources:
                sources[tier] = tier_sources

        # Fallback to defaults if config is empty
        if not any(sources.values()):
            sources = self._get_default_sources()

        return sources

    def _get_default_sources(self) -> Dict[str, List[Dict]]:
        """Default sources if config is missing."""
        return {
            "tier_1_india": [
                {
                    "id": "idsa",
                    "name": "IDSA",
                    "rss": "https://www.idsa.in/rss",
                    "credibility": 9,
                    "focus": ["defence", "security", "strategic"],
                },
                {
                    "id": "orf",
                    "name": "ORF",
                    "rss": "https://www.orfonline.org/feed/",
                    "credibility": 9,
                    "focus": ["technology", "cyber", "geopolitics"],
                },
                {
                    "id": "carnegie_india",
                    "name": "Carnegie India",
                    "rss": "https://carnegieindia.org/rss/solr.xml",
                    "credibility": 9,
                    "focus": ["technology", "foreign_policy"],
                },
            ],
            "tier_2_international": [
                {
                    "id": "csis",
                    "name": "CSIS",
                    "rss": "https://www.csis.org/rss.xml",
                    "credibility": 9,
                    "focus": ["cyber", "technology", "defence"],
                },
                {
                    "id": "brookings",
                    "name": "Brookings",
                    "rss": "https://www.brookings.edu/feed/",
                    "credibility": 9,
                    "focus": ["technology", "governance", "policy"],
                },
            ],
            "tier_3_industry": [
                {
                    "id": "dsci",
                    "name": "DSCI",
                    "url": "https://www.dsci.in",
                    "credibility": 8,
                    "focus": ["data_protection", "privacy", "compliance"],
                },
            ],
        }

    @property
    def source_type(self) -> str:
        return "thinktank"

    @property
    def default_credibility(self) -> int:
        return 8

    def is_available(self) -> bool:
        """Check if feedparser is available."""
        if not FEEDPARSER_AVAILABLE:
            logger.warning(
                "thinktank_miner_unavailable",
                reason="feedparser package not installed",
            )
            return False
        return True

    def fetch(self, query: str, limit: int = 10) -> List[EvidenceItem]:
        """
        Fetch think tank content matching a query.

        Args:
            query: Search query to filter content
            limit: Maximum number of results

        Returns:
            List of EvidenceItem objects
        """
        if not self.is_available():
            return []

        all_items = self.fetch_latest(days=30)

        # Filter by query
        query_lower = query.lower()
        query_words = set(query_lower.split())

        filtered = []
        for item in all_items:
            text = f"{item.title} {item.raw_content}".lower()
            if any(word in text for word in query_words):
                filtered.append(item)

        logger.info("thinktank_query_complete", query=query[:50], count=len(filtered))
        return filtered[:limit]

    def fetch_latest(self, days: int = 7) -> List[EvidenceItem]:
        """
        Fetch latest content from all think tank sources.

        Args:
            days: Only include content from the last N days

        Returns:
            List of EvidenceItem objects sorted by date
        """
        if not self.is_available():
            return []

        all_items: List[EvidenceItem] = []
        cutoff_date = datetime.now() - timedelta(days=days)

        for tier_name, tier_sources in self.sources.items():
            for source in tier_sources:
                rss_url = source.get("rss")
                if not rss_url:
                    continue

                try:
                    items = self._fetch_rss(source, cutoff_date)
                    all_items.extend(items)
                except Exception as e:
                    logger.warning(
                        "thinktank_source_error",
                        source=source.get("id"),
                        error=str(e),
                    )

        # Sort by date (newest first)
        all_items.sort(
            key=lambda x: x.published or datetime.min,
            reverse=True,
        )

        logger.info("thinktank_fetch_complete", count=len(all_items), days=days)
        return all_items

    def fetch_by_topic(self, topic: str) -> List[EvidenceItem]:
        """
        Fetch content specifically related to a topic.

        Args:
            topic: Topic to search for

        Returns:
            List of relevant EvidenceItem objects
        """
        return self.fetch(topic, limit=20)

    def _fetch_rss(
        self, source: Dict[str, Any], cutoff_date: datetime
    ) -> List[EvidenceItem]:
        """
        Fetch and parse RSS feed from a single source.

        Args:
            source: Source configuration dict
            cutoff_date: Only include items after this date

        Returns:
            List of EvidenceItem objects
        """
        rss_url = source.get("rss")
        source_id = source.get("id", "unknown")
        source_name = source.get("name", source_id)
        credibility = source.get("credibility", self.default_credibility)

        feed = feedparser.parse(rss_url)

        if feed.bozo and not feed.entries:
            logger.warning(
                "rss_parse_error",
                source=source_id,
                error=str(feed.bozo_exception)
                if hasattr(feed, "bozo_exception")
                else "unknown",
            )
            return []

        items = []
        for idx, entry in enumerate(feed.entries[: self.max_items_per_source]):
            # Parse publication date
            pub_date = self._parse_entry_date(entry)
            if pub_date and pub_date < cutoff_date:
                continue

            # Extract content
            title = entry.get("title", "")
            link = entry.get("link", "")
            summary = self._extract_summary(entry)

            # Filter for security-relevant content
            if not self._is_security_relevant(title, summary):
                continue

            # Generate unique ID
            item_id = self._generate_id(link or f"{source_id}-{idx}")

            domain = self._extract_domain(link)

            evidence = EvidenceItem(
                id=item_id,
                title=title,
                url=link,
                raw_content=summary,
                source_type="thinktank",
                publisher=source_name,
                published=pub_date,
                credibility_weight=credibility,
                domain=domain,
                snippet=summary[:500] if summary else "",
                metadata={
                    "source_id": source_id,
                    "source_tier": self._get_tier(source_id),
                    "focus_areas": source.get("focus", []),
                },
            )
            items.append(evidence)

        logger.debug(
            "rss_fetched",
            source=source_id,
            total_entries=len(feed.entries),
            relevant=len(items),
        )
        return items

    def _parse_entry_date(self, entry: Dict) -> Optional[datetime]:
        """Parse publication date from RSS entry."""
        date_fields = ["published_parsed", "updated_parsed", "created_parsed"]

        for field in date_fields:
            time_struct = entry.get(field)
            if time_struct:
                try:
                    return datetime(*time_struct[:6])
                except Exception:
                    pass

        return None

    def _extract_summary(self, entry: Dict) -> str:
        """Extract summary/description from RSS entry."""
        # Try different fields
        for field in ["summary", "description", "content"]:
            content = entry.get(field)
            if content:
                if isinstance(content, list) and content:
                    content = content[0].get("value", "")
                if isinstance(content, str):
                    # Strip HTML tags (basic)
                    import re

                    clean = re.sub(r"<[^>]+>", " ", content)
                    clean = re.sub(r"\s+", " ", clean).strip()
                    return clean[:2000]

        return ""

    def _is_security_relevant(self, title: str, summary: str) -> bool:
        """Check if content is relevant to security topics."""
        text = f"{title} {summary}".lower()
        return any(keyword in text for keyword in self.SECURITY_KEYWORDS)

    def _generate_id(self, seed: str) -> str:
        """Generate a unique ID from a seed string."""
        return hashlib.md5(seed.encode()).hexdigest()[:12]

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
        except Exception:
            return ""

    def _get_tier(self, source_id: str) -> str:
        """Get tier for a source ID."""
        for tier, sources in self.sources.items():
            for source in sources:
                if source.get("id") == source_id:
                    return tier
        return "unknown"

    def get_source_stats(self) -> Dict[str, Any]:
        """Get statistics about configured sources."""
        stats = {
            "total_sources": 0,
            "by_tier": {},
            "available": self.is_available(),
        }

        for tier, sources in self.sources.items():
            count = len(sources)
            stats["by_tier"][tier] = count
            stats["total_sources"] += count

        return stats
