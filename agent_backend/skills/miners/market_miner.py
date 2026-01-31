"""
MarketMiner: Economic security and market intelligence.

Tracks investment fraud, market warnings, corporate crime, and regulatory
enforcement actions that affect Indian investors and businesses.

Features:
- SEBI enforcement order tracking
- RBI circulars and warnings
- ED/CBI financial crime news
- MCA shell company prosecutions
- Investor warning aggregation

Sources:
- SEBI Orders (Penalties, warnings, debarments)
- RBI Circulars (Banking policy, payment)
- ED Actions (Money laundering)
- MCA Prosecutions (Shell companies, fraud)
- Economic news (ET, Livemint)
"""

import os
from typing import List, Dict, Optional, Literal
from datetime import datetime, timedelta
from urllib.parse import urlparse

from .base_miner import BaseMiner, EvidenceItem
from config.manager import config
from shared.logger import get_logger

logger = get_logger("MarketMiner")

# Check for SerpAPI dependency
try:
    from serpapi import GoogleSearch

    SERPAPI_AVAILABLE = True
except ImportError:
    SERPAPI_AVAILABLE = False
    GoogleSearch = None


# Market alert types
MarketAlertType = Literal[
    "sebi_order",  # SEBI enforcement
    "rbi_circular",  # RBI policy/warning
    "ed_action",  # ED money laundering
    "mca_prosecution",  # MCA corporate fraud
    "investor_warning",  # General investor alert
    "fraud_case",  # Financial fraud news
]


class MarketMiner(BaseMiner):
    """
    Economic security and market intelligence miner.

    Tracks regulatory enforcement, investment fraud, and financial crime
    to protect investors and businesses.

    Target pillars: economic_security, business_security
    Target personas: citizen, smb, compliance
    """

    # Regulatory sources with credibility
    REGULATORY_SOURCES = {
        "sebi.gov.in": 10,
        "rbi.org.in": 10,
        "enforcementdirectorate.gov.in": 10,
        "mca.gov.in": 10,
        "cbi.gov.in": 10,
        "dor.gov.in": 10,  # Dept of Revenue
        "incometaxindia.gov.in": 10,
    }

    # Financial news sources
    FINANCIAL_NEWS = {
        "economictimes.indiatimes.com": 8,
        "livemint.com": 8,
        "moneycontrol.com": 8,
        "business-standard.com": 8,
        "thehindubusinessline.com": 8,
        "financialexpress.com": 7,
        "cnbctv18.com": 7,
    }

    # Keywords for different alert types
    ALERT_KEYWORDS = {
        "sebi_order": [
            "sebi order",
            "sebi penalty",
            "sebi bars",
            "sebi debarment",
            "sebi warning",
            "sebi interim order",
            "market ban",
        ],
        "rbi_circular": [
            "rbi circular",
            "rbi guideline",
            "rbi directive",
            "rbi warning",
            "rbi caution",
            "license cancelled",
            "banking restriction",
        ],
        "ed_action": [
            "ed arrest",
            "ed raid",
            "money laundering",
            "pmla",
            "ed attachment",
            "proceeds of crime",
            "ed investigation",
        ],
        "mca_prosecution": [
            "shell company",
            "bogus company",
            "company fraud",
            "director disqualified",
            "mca prosecution",
            "csr fraud",
        ],
        "investor_warning": [
            "investor warning",
            "unauthorized scheme",
            "ponzi scheme",
            "chit fund fraud",
            "nidhi company fraud",
            "collective investment",
        ],
        "fraud_case": [
            "financial fraud",
            "bank fraud",
            "loan fraud",
            "scam",
            "embezzlement",
            "misappropriation",
            "stock manipulation",
        ],
    }

    def __init__(self):
        self.api_key = os.getenv("SERPAPI_API_KEY")
        self.config = config.get("market_miner", {})
        self.enabled = self.config.get("enabled", True)

    @property
    def source_type(self) -> str:
        return "market"

    @property
    def default_credibility(self) -> int:
        return 8  # Financial news is high credibility

    def is_available(self) -> bool:
        """Check if miner is available."""
        return self.enabled

    def fetch(self, query: str, limit: int = 5) -> List[EvidenceItem]:
        """
        Fetch market/economic security evidence.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of EvidenceItem objects
        """
        results: List[EvidenceItem] = []

        # Add economic security context if not present
        if not any(kw in query.lower() for kw in ["sebi", "rbi", "fraud", "investor"]):
            query = f"{query} India investor warning fraud"

        if SERPAPI_AVAILABLE and self.api_key:
            news_results = self._fetch_market_news(query, limit)
            results.extend(news_results)

        logger.info("market_fetch_complete", count=len(results), query=query[:50])
        return results[:limit]

    def fetch_regulatory_actions(self, days: int = 30) -> List[EvidenceItem]:
        """
        Fetch recent regulatory enforcement actions.

        Args:
            days: Look back period in days

        Returns:
            List of regulatory action alerts
        """
        queries = [
            "SEBI order penalty debarment India",
            "RBI circular warning bank India",
            "ED arrest money laundering India",
            "MCA shell company prosecution India",
        ]

        all_results = []
        per_query = 5

        for query in queries:
            results = self._fetch_market_news(query, per_query)
            all_results.extend(results)

        # Deduplicate and classify
        unique = self._deduplicate(all_results)

        for result in unique:
            alert_type = self._classify_alert(result.title, result.snippet)
            result.metadata["alert_type"] = alert_type
            result.metadata["urgency"] = self._calculate_urgency(result, alert_type)

        logger.info("regulatory_actions_fetched", count=len(unique), days=days)
        return unique

    def fetch_investor_warnings(self) -> List[EvidenceItem]:
        """
        Fetch current investor warnings and alerts.

        Returns:
            List of investor warning alerts
        """
        queries = [
            "SEBI investor warning unauthorized India",
            "RBI caution fraudulent scheme India",
            "investment fraud warning India",
            "ponzi scheme warning India",
        ]

        all_results = []

        for query in queries:
            results = self._fetch_market_news(query, 5)
            for result in results:
                result.metadata["alert_type"] = "investor_warning"
                result.metadata["pillar"] = "economic_security"
                result.metadata["target_personas"] = ["citizen", "smb"]
            all_results.extend(results)

        unique = self._deduplicate(all_results)
        logger.info("investor_warnings_fetched", count=len(unique))
        return unique

    def fetch_fraud_cases(self, limit: int = 10) -> List[EvidenceItem]:
        """
        Fetch financial fraud cases.

        Args:
            limit: Maximum results

        Returns:
            List of fraud case reports
        """
        queries = [
            "bank fraud case India crore",
            "financial scam India arrest",
            "corporate fraud India investigation",
        ]

        all_results = []
        per_query = limit // len(queries) + 1

        for query in queries:
            results = self._fetch_market_news(query, per_query)
            for result in results:
                result.metadata["alert_type"] = "fraud_case"
            all_results.extend(results)

        unique = self._deduplicate(all_results)
        logger.info("fraud_cases_fetched", count=len(unique))
        return unique[:limit]

    def get_market_alerts_summary(self, days: int = 7) -> Dict:
        """
        Get summary of market alerts by type.

        Args:
            days: Look back period

        Returns:
            Dictionary with alert counts and highlights
        """
        regulatory = self.fetch_regulatory_actions(days)

        # Group by alert type
        by_type = {}
        for alert in regulatory:
            alert_type = alert.metadata.get("alert_type", "other")
            if alert_type not in by_type:
                by_type[alert_type] = []
            by_type[alert_type].append(
                {
                    "title": alert.title,
                    "source": alert.publisher,
                    "url": alert.url,
                    "urgency": alert.metadata.get("urgency", "medium"),
                }
            )

        return {
            "period_days": days,
            "total_alerts": len(regulatory),
            "by_type": by_type,
            "high_urgency": [
                a
                for a in regulatory
                if a.metadata.get("urgency") in ["critical", "high"]
            ][:5],
        }

    def _fetch_market_news(self, query: str, limit: int) -> List[EvidenceItem]:
        """Fetch market/financial news via SerpAPI."""
        if not SERPAPI_AVAILABLE or not self.api_key:
            logger.debug("serpapi_unavailable_for_market")
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

                evidence = EvidenceItem(
                    id=self._make_id(idx),
                    title=title,
                    url=link,
                    raw_content=snippet,
                    source_type="market",
                    publisher=source.get("name", domain),
                    published=self._parse_date(date_str),
                    credibility_weight=credibility,
                    domain=domain,
                    snippet=snippet[:500] if snippet else "",
                    metadata={
                        "source": "market_miner",
                        "original_date": date_str,
                        "pillar": "economic_security",
                    },
                )
                items.append(evidence)

            return items

        except Exception as e:
            logger.error("market_news_fetch_error", error=str(e))
            return []

    def _classify_alert(self, title: str, content: str) -> str:
        """Classify content into an alert type."""
        text = f"{title} {content}".lower()

        scores = {}
        for alert_type, keywords in self.ALERT_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                scores[alert_type] = score

        if not scores:
            return "other"

        return max(scores, key=scores.get)

    def _calculate_urgency(self, item: EvidenceItem, alert_type: str) -> str:
        """Calculate urgency based on alert type and content."""
        # SEBI/RBI official orders are always high priority
        if item.domain in self.REGULATORY_SOURCES:
            return "high"

        # ED arrests/raids are critical
        if alert_type == "ed_action":
            text = f"{item.title} {item.snippet}".lower()
            if any(kw in text for kw in ["arrest", "raid", "crore"]):
                return "critical"
            return "high"

        # Large amounts involved
        text = f"{item.title} {item.snippet}".lower()
        if any(kw in text for kw in ["crore", "million", "billion"]):
            return "high"

        # New schemes/warnings
        if alert_type == "investor_warning":
            if any(kw in text for kw in ["new scheme", "beware", "caution"]):
                return "high"

        return "medium"

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
        if domain in self.REGULATORY_SOURCES:
            return self.REGULATORY_SOURCES[domain]
        if domain in self.FINANCIAL_NEWS:
            return self.FINANCIAL_NEWS[domain]

        # Government domains
        if ".gov" in domain or ".nic.in" in domain:
            return 9

        return self.default_credibility

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
    miner = MarketMiner()

    print(f"MarketMiner available: {miner.is_available()}")

    print("\nFetching market alerts summary...")
    summary = miner.get_market_alerts_summary(days=7)
    print(f"Total alerts: {summary['total_alerts']}")
    print(f"Alert types: {list(summary['by_type'].keys())}")
