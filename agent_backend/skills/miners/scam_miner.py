"""
ScamMiner: Real-time fraud and scam intelligence.

The highest priority miner for India's #1 reader pain point - scams and fraud.
Digital arrest scams, UPI fraud, job scams affect millions of Indians daily.

Features:
- Real-time scam alert fetching
- Scam type classification
- Trending scam detection
- Region-based scam tracking
- Prevention tips generation

Sources:
- cybercrime.gov.in (Official portal)
- RBI Sachet (Unauthorized entities)
- CERT-IN Advisories (Cyber threats)
- State Police Cyber Cells (Regional alerts)
- Consumer Helpline (Complaint patterns)
"""

import os
import hashlib
from typing import List, Dict, Optional, Literal
from datetime import datetime, timedelta
from urllib.parse import urlparse

from .base_miner import BaseMiner, EvidenceItem
from config.manager import config
from shared.logger import get_logger

logger = get_logger("ScamMiner")

# Check for SerpAPI dependency (used for Google News on scam topics)
try:
    from serpapi import GoogleSearch

    SERPAPI_AVAILABLE = True
except ImportError:
    SERPAPI_AVAILABLE = False
    GoogleSearch = None


# Scam type taxonomy
ScamType = Literal[
    "phishing",  # Fake emails, OTP fraud, smishing
    "investment",  # Ponzi, crypto, forex scams
    "job",  # Fake recruitment, work-from-home
    "banking",  # UPI fraud, card cloning, digital arrest
    "impersonation",  # Fake police, KYC fraud, fake officials
    "ecommerce",  # Fake websites, non-delivery
    "loan",  # Fake loan apps, illegal lending
    "lottery",  # Fake lottery, lucky draw scams
]


class ScamMiner(BaseMiner):
    """
    Real-time scam and fraud intelligence miner.

    Highest priority miner because scams are the #1 reader pain point in India.
    Provides real-time alerts, classification, and prevention tips.

    Target pillars: scam_watch, senior_safety, personal_security
    Target personas: citizen, senior
    """

    # Scam keywords for detection and classification
    SCAM_KEYWORDS = {
        "phishing": [
            "otp fraud",
            "otp scam",
            "phishing",
            "fake email",
            "smishing",
            "sms fraud",
            "link fraud",
            "verify your account",
        ],
        "investment": [
            "ponzi",
            "investment scam",
            "crypto scam",
            "forex fraud",
            "trading scam",
            "guaranteed returns",
            "double your money",
            "part time job investment",
            "task scam",
        ],
        "job": [
            "job scam",
            "fake recruitment",
            "work from home fraud",
            "part time job",
            "data entry scam",
            "job offer fraud",
            "placement scam",
            "telegram job",
        ],
        "banking": [
            "upi fraud",
            "digital arrest",
            "card cloning",
            "atm skimming",
            "bank fraud",
            "account freeze scam",
            "kyc update scam",
            "upi scam",
            "money transfer fraud",
        ],
        "impersonation": [
            "fake police",
            "fake cbi",
            "fake ed",
            "cyber police scam",
            "government official fraud",
            "aadhaar fraud",
            "pan fraud",
            "customs fraud",
            "courier scam",
        ],
        "ecommerce": [
            "fake website",
            "non-delivery",
            "online shopping scam",
            "flipkart scam",
            "amazon scam",
            "olx fraud",
            "cod fraud",
        ],
        "loan": [
            "fake loan app",
            "illegal lending",
            "loan shark",
            "instant loan fraud",
            "chinese loan app",
            "loan app harassment",
        ],
        "lottery": [
            "lottery scam",
            "lucky draw",
            "kaun banega crorepati fraud",
            "whatsapp lottery",
            "prize scam",
            "gift card scam",
        ],
    }

    # High-priority scam sources
    OFFICIAL_SOURCES = {
        "cybercrime.gov.in": 10,
        "rbi.org.in": 10,
        "sachet.rbi.org.in": 10,
        "cert-in.org.in": 10,
        "cybercelldelhipolice.nic.in": 9,
        "mumbaipolice.gov.in": 9,
        "bcp.karnataka.gov.in": 9,
        "consumerhelpline.gov.in": 9,
        "pib.gov.in": 10,
        "meity.gov.in": 10,
    }

    def __init__(self):
        self.api_key = os.getenv("SERPAPI_API_KEY")
        self.config = config.get("scam_miner", {})
        self.enabled = self.config.get("enabled", True)

    @property
    def source_type(self) -> str:
        return "scam"

    @property
    def default_credibility(self) -> int:
        return 8  # Scam alerts are high-credibility public interest

    def is_available(self) -> bool:
        """Check if miner is available (SerpAPI for news)."""
        if not self.enabled:
            return False
        # SerpAPI is optional but enhances functionality
        return True

    def fetch(self, query: str, limit: int = 5) -> List[EvidenceItem]:
        """
        Fetch scam-related evidence.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of EvidenceItem objects
        """
        results: List[EvidenceItem] = []

        # Add scam context to query if not present
        if not any(kw in query.lower() for kw in ["scam", "fraud", "alert", "warning"]):
            query = f"{query} scam fraud alert India"

        # Fetch from Google News if SerpAPI available
        if SERPAPI_AVAILABLE and self.api_key:
            news_results = self._fetch_scam_news(query, limit)
            results.extend(news_results)

        logger.info("scam_fetch_complete", count=len(results), query=query[:50])
        return results[:limit]

    def fetch_active_scams(self, hours: int = 24) -> List[EvidenceItem]:
        """
        Fetch currently active scam alerts.

        Args:
            hours: Look back period in hours

        Returns:
            List of active scam alerts
        """
        queries = [
            "India scam alert warning today",
            "digital arrest scam India",
            "UPI fraud alert India",
            "online fraud warning India",
            "cyber crime alert India",
        ]

        all_results = []
        per_query = 5

        for query in queries:
            results = self._fetch_scam_news(query, per_query)
            all_results.extend(results)

        # Deduplicate and filter by recency
        unique = self._deduplicate(all_results)
        recent = [
            r
            for r in unique
            if r.published
            and (datetime.now() - r.published).total_seconds() < hours * 3600
        ]

        # Add urgency metadata
        for result in recent:
            result.metadata["urgency"] = self._calculate_urgency(result)

        logger.info("active_scams_fetched", count=len(recent), hours=hours)
        return recent

    def fetch_by_type(self, scam_type: ScamType, limit: int = 10) -> List[EvidenceItem]:
        """
        Fetch scams of a specific type.

        Args:
            scam_type: Type of scam to fetch
            limit: Maximum results

        Returns:
            List of scam alerts matching the type
        """
        keywords = self.SCAM_KEYWORDS.get(scam_type, [])
        if not keywords:
            return []

        # Build query from type keywords
        query = f"India {' OR '.join(keywords[:3])} alert warning"

        results = self._fetch_scam_news(query, limit)

        # Tag results with scam type
        for result in results:
            result.metadata["scam_type"] = scam_type

        logger.info("scams_by_type", scam_type=scam_type, count=len(results))
        return results

    def get_trending_scams(self, limit: int = 10) -> List[Dict]:
        """
        Get trending scam patterns.

        Returns structured data about current scam trends.

        Args:
            limit: Maximum number of trends

        Returns:
            List of trending scam dictionaries
        """
        # Fetch from multiple scam type queries
        all_scams = []

        for scam_type in ["banking", "impersonation", "job", "investment"]:
            scams = self.fetch_by_type(scam_type, limit=5)
            for scam in scams:
                all_scams.append(
                    {
                        "id": scam.id,
                        "type": scam_type,
                        "title": scam.title,
                        "source": scam.publisher,
                        "url": scam.url,
                        "urgency": scam.metadata.get("urgency", "medium"),
                        "published": scam.published.isoformat()
                        if scam.published
                        else None,
                        "snippet": scam.snippet,
                    }
                )

        # Sort by urgency and recency
        urgency_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        all_scams.sort(
            key=lambda x: (
                urgency_order.get(x["urgency"], 2),
                x["published"] or "",
            ),
            reverse=True,
        )

        return all_scams[:limit]

    def classify_scam(self, title: str, content: str) -> Optional[ScamType]:
        """
        Classify content into a scam type.

        Args:
            title: Title of the content
            content: Full text content

        Returns:
            Detected scam type or None
        """
        text = f"{title} {content}".lower()

        scores = {}
        for scam_type, keywords in self.SCAM_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                scores[scam_type] = score

        if not scores:
            return None

        # Return the type with highest score
        return max(scores, key=scores.get)

    def get_prevention_tips(self, scam_type: ScamType) -> List[str]:
        """
        Get prevention tips for a scam type.

        Args:
            scam_type: Type of scam

        Returns:
            List of prevention tips
        """
        tips = {
            "phishing": [
                "Never share OTP with anyone, including bank officials",
                "Verify sender email addresses carefully",
                "Don't click on suspicious links in SMS or email",
                "Report suspicious messages to cybercrime.gov.in",
            ],
            "investment": [
                "Be wary of guaranteed high returns",
                "Verify company registration with MCA",
                "Check if entity is registered with SEBI/RBI",
                "Never invest via WhatsApp/Telegram groups",
            ],
            "job": [
                "Legitimate companies never ask for money upfront",
                "Verify job postings on official company websites",
                "Be suspicious of work-from-home offers with high pay",
                "Don't share personal documents without verification",
            ],
            "banking": [
                "Never share card CVV, PIN, or OTP",
                "Bank officials never ask for sensitive details",
                "Use official bank apps only",
                "Enable transaction alerts on your phone",
            ],
            "impersonation": [
                "Government agencies don't threaten arrest over phone",
                "Verify caller identity through official channels",
                "Don't transfer money under pressure",
                "Hang up and call official helpline numbers",
            ],
            "ecommerce": [
                "Check website URL carefully for misspellings",
                "Use trusted payment gateways only",
                "Be wary of deals that seem too good",
                "Prefer cash on delivery for unknown sellers",
            ],
            "loan": [
                "Use only RBI-registered lending apps",
                "Check app permissions carefully",
                "Never share contacts/photos for loans",
                "Report harassment to cybercrime.gov.in",
            ],
            "lottery": [
                "You can't win a lottery you didn't enter",
                "Never pay processing fees to claim prizes",
                "Block and report lottery spam messages",
                "Real prizes don't require upfront payment",
            ],
        }

        return tips.get(
            scam_type,
            [
                "Be cautious of unsolicited contacts",
                "Verify before you trust",
                "Never share sensitive information",
                "Report suspicious activity to cybercrime.gov.in",
            ],
        )

    def _fetch_scam_news(self, query: str, limit: int) -> List[EvidenceItem]:
        """Fetch scam news from Google News via SerpAPI."""
        if not SERPAPI_AVAILABLE or not self.api_key:
            logger.debug("serpapi_unavailable_for_scams")
            return []

        try:
            params = {
                "engine": "google_news",
                "q": query,
                "gl": "in",
                "hl": "en",
                "api_key": self.api_key,
            }

            search = GoogleSearch(params)
            results = search.get_dict()

            items = []
            news_results = results.get("news_results", [])

            for idx, item in enumerate(news_results[:limit]):
                title = item.get("title", "")
                link = item.get("link", "")
                snippet = item.get("snippet", "")
                source = item.get("source", {})
                date_str = item.get("date", "")

                if not link:
                    continue

                domain = self._extract_domain(link)
                credibility = self._get_source_credibility(domain)

                # Classify scam type
                scam_type = self.classify_scam(title, snippet)

                evidence = EvidenceItem(
                    id=self._make_id(idx),
                    title=title,
                    url=link,
                    raw_content=snippet,
                    source_type="scam",
                    publisher=source.get("name", domain),
                    published=self._parse_date(date_str),
                    credibility_weight=credibility,
                    domain=domain,
                    snippet=snippet[:500] if snippet else "",
                    metadata={
                        "source": "scam_miner",
                        "scam_type": scam_type,
                        "original_date": date_str,
                        "pillar": "scam_watch",
                        "target_personas": ["citizen", "senior"],
                    },
                )
                items.append(evidence)

            return items

        except Exception as e:
            logger.error("scam_news_fetch_error", error=str(e))
            return []

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

    def _get_source_credibility(self, domain: str) -> int:
        """Get credibility score for source domain."""
        # Check official sources first
        if domain in self.OFFICIAL_SOURCES:
            return self.OFFICIAL_SOURCES[domain]

        # Check for government domains
        if ".gov" in domain or ".nic.in" in domain:
            return 9

        # Major news outlets
        if domain in ["economictimes.indiatimes.com", "livemint.com", "thehindu.com"]:
            return 8

        return self.default_credibility

    def _calculate_urgency(self, item: EvidenceItem) -> str:
        """Calculate urgency level of a scam alert."""
        # Keywords that indicate high urgency
        high_urgency_keywords = [
            "warning",
            "alert",
            "urgent",
            "active",
            "million",
            "crore",
            "arrested",
            "busted",
        ]

        critical_keywords = [
            "digital arrest",
            "nationwide",
            "rbi warning",
            "cert-in",
            "government advisory",
            "mass fraud",
        ]

        text = f"{item.title} {item.snippet}".lower()

        if any(kw in text for kw in critical_keywords):
            return "critical"
        if any(kw in text for kw in high_urgency_keywords):
            return "high"
        if item.credibility_weight >= 9:
            return "high"

        return "medium"

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string from news results."""
        if not date_str:
            return None

        try:
            date_lower = date_str.lower()
            if "hour" in date_lower or "minute" in date_lower:
                return datetime.now()
            elif "day" in date_lower:
                return datetime.now()
            elif "week" in date_lower:
                return datetime.now() - timedelta(days=7)
            else:
                return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except Exception:
            return None

    def _deduplicate(self, items: List[EvidenceItem]) -> List[EvidenceItem]:
        """Remove duplicate items by URL."""
        seen_urls = set()
        unique = []
        for item in items:
            if item.url not in seen_urls:
                seen_urls.add(item.url)
                unique.append(item)
        return unique


if __name__ == "__main__":
    # Quick test
    miner = ScamMiner()

    print(f"ScamMiner available: {miner.is_available()}")

    print("\nFetching trending scams...")
    trending = miner.get_trending_scams(limit=5)
    for scam in trending:
        print(f"  [{scam['type']}] {scam['title'][:60]}...")

    print("\nPrevention tips for banking scams:")
    tips = miner.get_prevention_tips("banking")
    for tip in tips:
        print(f"  - {tip}")
