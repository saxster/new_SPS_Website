"""
RegulatoryMiner: Monitors government and regulatory sources.

Sources include:
- PIB (Press Information Bureau)
- CERT-IN (Cyber Emergency Response Team)
- MeitY (Ministry of Electronics and IT)
- RBI (Reserve Bank of India)
- SEBI (Securities and Exchange Board)
- TRAI (Telecom Regulatory Authority)
- BIS (Bureau of Indian Standards)

Provides regulatory intelligence for compliance and policy content.
"""

import os
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from urllib.parse import urlparse
import hashlib

from .base_miner import BaseMiner, EvidenceItem
from config.manager import config
from shared.logger import get_logger

logger = get_logger("RegulatoryMiner")

# Check for feedparser dependency
try:
    import feedparser

    FEEDPARSER_AVAILABLE = True
except ImportError:
    FEEDPARSER_AVAILABLE = False
    feedparser = None


class RegulatoryMiner(BaseMiner):
    """
    Miner for regulatory and government sources.

    Fetches alerts, circulars, and policy updates from:
    - Central government ministries
    - Regulatory bodies
    - Standards organizations

    All government sources get maximum credibility (10).
    """

    # Document type indicators
    DOCUMENT_TYPES = {
        "advisory": ["advisory", "advisories", "guidance", "guideline"],
        "alert": ["alert", "warning", "urgent", "vulnerability", "cve"],
        "circular": ["circular", "notification", "order", "direction"],
        "regulation": ["regulation", "act", "rule", "amendment", "gazette"],
        "framework": ["framework", "standard", "policy", "draft"],
        "press_release": ["press", "release", "statement", "announcement"],
    }

    # Priority keywords that indicate high urgency
    PRIORITY_KEYWORDS = {
        "critical": [
            "critical",
            "emergency",
            "immediate",
            "severe",
            "high severity",
            "urgent action",
        ],
        "high": [
            "important",
            "urgent",
            "mandatory",
            "deadline",
            "compliance required",
            "high",
        ],
        "medium": ["advisory", "recommended", "guidance", "update", "amendment"],
        "low": ["information", "reference", "archive", "historical"],
    }

    def __init__(self):
        self.regulators = self._load_regulators()
        self.sync_interval = config.get("regulatory_miner.sync_interval_hours", 4)

    def _load_regulators(self) -> List[Dict[str, Any]]:
        """Load regulator sources from config."""
        regulators = config.get("regulatory_miner.regulators", [])

        if not regulators:
            regulators = self._get_default_regulators()

        return regulators

    def _get_default_regulators(self) -> List[Dict[str, Any]]:
        """Default regulators if config is missing."""
        return [
            {
                "id": "pib",
                "name": "PIB",
                "rss": "https://pib.gov.in/RssMain.aspx",
                "priority": "medium",
                "credibility": 10,
                "types": ["press_release"],
            },
            {
                "id": "cert_in",
                "name": "CERT-IN",
                "url": "https://www.cert-in.org.in",
                "priority": "critical",
                "credibility": 10,
                "types": ["advisory", "alert", "vulnerability"],
            },
            {
                "id": "rbi",
                "name": "RBI",
                "rss": "https://www.rbi.org.in/rss/rss.aspx",
                "priority": "high",
                "credibility": 10,
                "types": ["circular", "framework", "guideline"],
            },
            {
                "id": "sebi",
                "name": "SEBI",
                "url": "https://www.sebi.gov.in",
                "priority": "high",
                "credibility": 10,
                "types": ["circular", "regulation", "order"],
            },
            {
                "id": "meity",
                "name": "MeitY",
                "url": "https://www.meity.gov.in",
                "priority": "high",
                "credibility": 10,
                "types": ["notification", "policy", "circular"],
            },
        ]

    @property
    def source_type(self) -> str:
        return "regulatory"

    @property
    def default_credibility(self) -> int:
        return 10  # Government sources are highest credibility

    def is_available(self) -> bool:
        """Check if feedparser is available for RSS sources."""
        if not FEEDPARSER_AVAILABLE:
            logger.warning(
                "regulatory_miner_limited",
                reason="feedparser not installed, RSS sources unavailable",
            )
        return True  # Always available, but may have reduced functionality

    def fetch(self, query: str, limit: int = 10) -> List[EvidenceItem]:
        """
        Fetch regulatory content matching a query.

        Args:
            query: Search query to filter content
            limit: Maximum number of results

        Returns:
            List of EvidenceItem objects
        """
        all_items = self.fetch_alerts(hours=168)  # Last week

        # Filter by query
        query_lower = query.lower()
        query_words = set(query_lower.split())

        filtered = []
        for item in all_items:
            text = f"{item.title} {item.raw_content}".lower()
            if any(word in text for word in query_words):
                filtered.append(item)

        logger.info("regulatory_query_complete", query=query[:50], count=len(filtered))
        return filtered[:limit]

    def fetch_alerts(self, hours: int = 24) -> List[EvidenceItem]:
        """
        Fetch recent alerts and advisories.

        Args:
            hours: Only include content from the last N hours

        Returns:
            List of EvidenceItem objects sorted by urgency and date
        """
        all_items: List[EvidenceItem] = []
        cutoff_date = datetime.now() - timedelta(hours=hours)

        for regulator in self.regulators:
            try:
                # Only fetch from RSS sources for now
                if regulator.get("rss"):
                    items = self._fetch_rss(regulator, cutoff_date)
                    all_items.extend(items)
            except Exception as e:
                logger.warning(
                    "regulatory_source_error",
                    source=regulator.get("id"),
                    error=str(e),
                )

        # Sort by urgency (critical first) then by date
        urgency_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        all_items.sort(
            key=lambda x: (
                urgency_order.get(x.metadata.get("urgency", "medium"), 2),
                -(x.published or datetime.min).timestamp(),
            )
        )

        logger.info("regulatory_alerts_complete", count=len(all_items), hours=hours)
        return all_items

    def fetch_circulars(self, regulator: str, days: int = 30) -> List[EvidenceItem]:
        """
        Fetch circulars from a specific regulator.

        Args:
            regulator: Regulator ID (e.g., "rbi", "sebi")
            days: Only include content from the last N days

        Returns:
            List of EvidenceItem objects
        """
        cutoff_date = datetime.now() - timedelta(days=days)

        # Find the regulator config
        reg_config = None
        for r in self.regulators:
            if r.get("id") == regulator:
                reg_config = r
                break

        if not reg_config:
            logger.warning("regulator_not_found", regulator=regulator)
            return []

        if not reg_config.get("rss"):
            logger.info(
                "regulator_no_rss",
                regulator=regulator,
                message="No RSS feed configured",
            )
            return []

        try:
            items = self._fetch_rss(reg_config, cutoff_date)
            # Filter for circular-type documents
            circulars = [
                item
                for item in items
                if item.metadata.get("document_type") in ["circular", "notification"]
            ]
            return circulars
        except Exception as e:
            logger.error("circular_fetch_error", regulator=regulator, error=str(e))
            return []

    def check_compliance_deadlines(self) -> List[Dict[str, Any]]:
        """
        Check for upcoming compliance deadlines in recent regulatory content.

        Returns:
            List of deadline info dicts with title, deadline, regulator
        """
        deadlines = []

        # Fetch recent regulatory content
        items = self.fetch_alerts(hours=720)  # Last 30 days

        # Look for deadline indicators
        deadline_keywords = [
            "deadline",
            "compliance date",
            "effective from",
            "must comply by",
            "last date",
            "by",
            "before",
            "within",
            "not later than",
        ]

        for item in items:
            text = f"{item.title} {item.raw_content}".lower()
            if any(keyword in text for keyword in deadline_keywords):
                deadlines.append(
                    {
                        "title": item.title,
                        "url": item.url,
                        "regulator": item.publisher,
                        "published": item.published.isoformat()
                        if item.published
                        else None,
                        "snippet": item.snippet[:200],
                    }
                )

        logger.info("compliance_deadlines_found", count=len(deadlines))
        return deadlines

    def _fetch_rss(
        self, regulator: Dict[str, Any], cutoff_date: datetime
    ) -> List[EvidenceItem]:
        """
        Fetch and parse RSS feed from a regulator.

        Args:
            regulator: Regulator configuration dict
            cutoff_date: Only include items after this date

        Returns:
            List of EvidenceItem objects
        """
        if not FEEDPARSER_AVAILABLE:
            return []

        rss_url = regulator.get("rss")
        reg_id = regulator.get("id", "unknown")
        reg_name = regulator.get("name", reg_id)
        credibility = regulator.get("credibility", self.default_credibility)
        default_priority = regulator.get("priority", "medium")

        feed = feedparser.parse(rss_url)

        if feed.bozo and not feed.entries:
            logger.warning(
                "rss_parse_error",
                source=reg_id,
                error=str(feed.bozo_exception)
                if hasattr(feed, "bozo_exception")
                else "unknown",
            )
            return []

        items = []
        for idx, entry in enumerate(feed.entries[:20]):  # Max 20 per source
            # Parse publication date
            pub_date = self._parse_entry_date(entry)
            if pub_date and pub_date < cutoff_date:
                continue

            # Extract content
            title = entry.get("title", "")
            link = entry.get("link", "")
            summary = self._extract_summary(entry)

            # Determine document type and urgency
            doc_type = self._classify_document_type(title, summary)
            urgency = self._determine_urgency(title, summary, default_priority)

            # Generate unique ID
            item_id = self._generate_id(link or f"{reg_id}-{idx}")

            domain = self._extract_domain(link)

            evidence = EvidenceItem(
                id=item_id,
                title=title,
                url=link,
                raw_content=summary,
                source_type="regulatory",
                publisher=reg_name,
                published=pub_date,
                credibility_weight=credibility,
                domain=domain,
                snippet=summary[:500] if summary else "",
                metadata={
                    "regulator_id": reg_id,
                    "document_type": doc_type,
                    "urgency": urgency,
                    "types": regulator.get("types", []),
                },
            )
            items.append(evidence)

        logger.debug(
            "rss_fetched",
            source=reg_id,
            total_entries=len(feed.entries),
            parsed=len(items),
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
        import re

        for field in ["summary", "description", "content"]:
            content = entry.get(field)
            if content:
                if isinstance(content, list) and content:
                    content = content[0].get("value", "")
                if isinstance(content, str):
                    clean = re.sub(r"<[^>]+>", " ", content)
                    clean = re.sub(r"\s+", " ", clean).strip()
                    return clean[:2000]

        return ""

    def _classify_document_type(self, title: str, summary: str) -> str:
        """Classify the type of regulatory document."""
        text = f"{title} {summary}".lower()

        for doc_type, keywords in self.DOCUMENT_TYPES.items():
            if any(keyword in text for keyword in keywords):
                return doc_type

        return "general"

    def _determine_urgency(self, title: str, summary: str, default: str) -> str:
        """Determine urgency level of the document."""
        text = f"{title} {summary}".lower()

        for urgency, keywords in self.PRIORITY_KEYWORDS.items():
            if any(keyword in text for keyword in keywords):
                return urgency

        return default

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

    def get_regulator_stats(self) -> Dict[str, Any]:
        """Get statistics about configured regulators."""
        stats = {
            "total_regulators": len(self.regulators),
            "with_rss": sum(1 for r in self.regulators if r.get("rss")),
            "by_priority": {},
        }

        for regulator in self.regulators:
            priority = regulator.get("priority", "medium")
            stats["by_priority"][priority] = stats["by_priority"].get(priority, 0) + 1

        return stats
