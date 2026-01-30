"""
SerpMiner: Uses SerpAPI for Google News and Google Search results.
Provides real-time news and authoritative web sources.

Features:
- Google News API for breaking news
- Google Search for authoritative sources
- Domain-based credibility scoring
- Time-based filtering for recent news
"""

import os
from typing import List, Optional
from datetime import datetime
from urllib.parse import urlparse

from .base_miner import BaseMiner, EvidenceItem
from config.manager import config
from shared.logger import get_logger

logger = get_logger("SerpMiner")

# Check for serpapi dependency
try:
    from serpapi import GoogleSearch

    SERPAPI_AVAILABLE = True
except ImportError:
    SERPAPI_AVAILABLE = False
    GoogleSearch = None


class SerpMiner(BaseMiner):
    """
    SerpAPI-powered news and search miner.

    Provides access to:
    - Google News (real-time breaking news)
    - Google Search (authoritative web sources)

    Credibility weights by domain type:
        10: Official government sources
        9: Industry associations (ASIS, ISACA, etc.)
        8: Major news outlets, security publications
        7: Trade publications
        6: Expert blogs
        5: General web content
    """

    # High-credibility industry/security domains
    INDUSTRY_DOMAINS = {
        # Security Industry Associations
        "asisonline.org": 9,
        "asis.org": 9,
        "isaca.org": 9,
        "isc2.org": 9,
        "sans.org": 9,
        "securityindustry.org": 8,
        # Government/Official
        "rbi.org.in": 10,
        "mha.gov.in": 10,
        "cert-in.org.in": 10,
        "bis.gov.in": 10,
        "sebi.gov.in": 10,
        "nist.gov": 9,
        "cisa.gov": 9,
        "pib.gov.in": 10,
        # Security Publications
        "securityweek.com": 8,
        "darkreading.com": 8,
        "krebsonsecurity.com": 9,
        "theregister.com": 8,
        "bleepingcomputer.com": 7,
        "thehackernews.com": 7,
        "csoonline.com": 7,
        "infosecurity-magazine.com": 7,
        "scmagazine.com": 7,
        # Major News
        "reuters.com": 8,
        "economictimes.indiatimes.com": 8,
        "livemint.com": 8,
        "thehindu.com": 8,
        "ndtv.com": 7,
        "hindustantimes.com": 7,
        "indianexpress.com": 7,
        "moneycontrol.com": 7,
        # Research & Analysis
        "ibm.com": 8,
        "gartner.com": 8,
        "forrester.com": 8,
        "mckinsey.com": 8,
    }

    def __init__(self):
        self.api_key = os.getenv("SERPAPI_API_KEY")
        self.default_location = config.get("serp.location", "India")
        self.default_language = config.get("serp.language", "en")
        self.news_period = config.get("serp.news_period", "1d")  # 1d, 1w, 1m

    @property
    def source_type(self) -> str:
        return "news"

    @property
    def default_credibility(self) -> int:
        return 7  # News sources default to 7

    def is_available(self) -> bool:
        """Check if SerpAPI is available and configured."""
        if not SERPAPI_AVAILABLE:
            logger.warning(
                "serpapi_unavailable", reason="serpapi package not installed"
            )
            return False
        if not self.api_key:
            logger.warning("serpapi_unavailable", reason="SERPAPI_API_KEY not set")
            return False
        return True

    def fetch(self, query: str, limit: int = 5) -> List[EvidenceItem]:
        """
        Fetch news and search results from Google via SerpAPI.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of EvidenceItem objects
        """
        if not self.is_available():
            return []

        results: List[EvidenceItem] = []

        # Fetch from Google News
        news_results = self._fetch_google_news(query, limit)
        results.extend(news_results)

        # If we need more results, also search regular Google
        if len(results) < limit:
            search_results = self._fetch_google_search(query, limit - len(results))
            results.extend(search_results)

        logger.info("serp_fetch_complete", count=len(results), query=query[:50])
        return results[:limit]

    def _fetch_google_news(self, query: str, limit: int) -> List[EvidenceItem]:
        """Fetch from Google News API."""
        try:
            params = {
                "engine": "google_news",
                "q": query,
                "gl": "in",  # India
                "hl": self.default_language,
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
                date = item.get("date", "")

                if not link:
                    continue

                domain = self._extract_domain(link)
                credibility = self._get_domain_credibility(domain)

                evidence = EvidenceItem(
                    id=self._make_id(idx),
                    title=title,
                    url=link,
                    raw_content=snippet,
                    source_type="news",
                    publisher=source.get("name", domain),
                    published=self._parse_date(date),
                    credibility_weight=credibility,
                    domain=domain,
                    snippet=snippet[:500] if snippet else "",
                    metadata={"source": "serpapi_google_news", "original_date": date},
                )
                items.append(evidence)

            logger.info("google_news_fetched", count=len(items))
            return items

        except Exception as e:
            logger.error("google_news_error", error=str(e))
            return []

    def _fetch_google_search(self, query: str, limit: int) -> List[EvidenceItem]:
        """Fetch from regular Google Search for authoritative sources."""
        try:
            # Add India context and focus on authoritative sources
            enhanced_query = (
                f"{query} site:asisonline.org OR site:securityweek.com OR site:gov.in"
            )

            params = {
                "engine": "google",
                "q": enhanced_query,
                "gl": "in",
                "hl": self.default_language,
                "num": limit,
                "api_key": self.api_key,
            }

            search = GoogleSearch(params)
            results = search.get_dict()

            items = []
            organic_results = results.get("organic_results", [])

            # Start index after news results
            start_idx = limit  # Offset to avoid ID collision

            for idx, item in enumerate(organic_results[:limit]):
                title = item.get("title", "")
                link = item.get("link", "")
                snippet = item.get("snippet", "")

                if not link:
                    continue

                domain = self._extract_domain(link)
                credibility = self._get_domain_credibility(domain)

                evidence = EvidenceItem(
                    id=self._make_id(start_idx + idx),
                    title=title,
                    url=link,
                    raw_content=snippet,
                    source_type="article",
                    publisher=domain,
                    credibility_weight=credibility,
                    domain=domain,
                    snippet=snippet[:500] if snippet else "",
                    metadata={"source": "serpapi_google_search"},
                )
                items.append(evidence)

            logger.info("google_search_fetched", count=len(items))
            return items

        except Exception as e:
            logger.error("google_search_error", error=str(e))
            return []

    def fetch_breaking_news(self, limit: int = 10) -> List[EvidenceItem]:
        """
        Fetch breaking news from India without a specific query.
        Useful for real-time incident monitoring.
        """
        queries = [
            "breaking news India security incident",
            "India accident crash fire today",
            "India cyber attack breach today",
        ]

        all_results = []
        per_query_limit = limit // len(queries) + 1

        for query in queries:
            results = self._fetch_google_news(query, per_query_limit)
            all_results.extend(results)

        # Deduplicate by URL
        seen_urls = set()
        unique_results = []
        for item in all_results:
            if item.url not in seen_urls:
                seen_urls.add(item.url)
                unique_results.append(item)

        return unique_results[:limit]

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

    def _get_domain_credibility(self, domain: str) -> int:
        """Get credibility score for a domain."""
        # Check exact match
        if domain in self.INDUSTRY_DOMAINS:
            return self.INDUSTRY_DOMAINS[domain]

        # Check partial match (e.g., subdomain.asisonline.org)
        for known_domain, score in self.INDUSTRY_DOMAINS.items():
            if domain.endswith(known_domain):
                return score

        # Government domains get high credibility
        if ".gov" in domain or ".nic.in" in domain:
            return 9

        # Educational domains
        if ".edu" in domain or ".ac.in" in domain:
            return 7

        return self.default_credibility

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string from news results."""
        if not date_str:
            return None

        # Handle relative dates like "2 hours ago", "1 day ago"
        try:
            date_lower = date_str.lower()
            if "hour" in date_lower or "minute" in date_lower:
                return datetime.now()
            elif "day" in date_lower:
                return datetime.now()
            elif "week" in date_lower:
                return datetime.now()
            else:
                # Try ISO format
                return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except Exception:
            return None
