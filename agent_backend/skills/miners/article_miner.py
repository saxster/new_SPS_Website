"""
ArticleMiner: Extracts content from web articles.
Uses trafilatura for robust article extraction.

Features:
- Full article text extraction
- Metadata extraction (title, author, date)
- Graceful paywall handling
- Domain-based credibility scoring
"""

import os
import re
from typing import List, Optional
from datetime import datetime
from urllib.parse import urlparse

from .base_miner import BaseMiner, EvidenceItem

try:
    import trafilatura
    from trafilatura.settings import use_config

    TRAFILATURA_AVAILABLE = True
except ImportError:
    TRAFILATURA_AVAILABLE = False
    trafilatura = None

try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None

from config.manager import config
from shared.logger import get_logger

logger = get_logger("ArticleMiner")


class ArticleMiner(BaseMiner):
    """
    Web article content miner.

    Credibility weights by domain type:
        9-10: Official government sources (.gov.in, .nic.in)
        8: Major news outlets (Reuters, Economic Times)
        7: Trade publications, industry reports
        6: Expert blogs, vendor documentation
        5: General web content
    """

    # High-credibility domains
    OFFICIAL_DOMAINS = {
        "rbi.org.in": 10,
        "mha.gov.in": 10,
        "cert-in.org.in": 10,
        "bis.gov.in": 10,
        "sebi.gov.in": 10,
        "meity.gov.in": 10,
        "pib.gov.in": 10,
        "nist.gov": 9,
        "cisa.gov": 9,
    }

    NEWS_DOMAINS = {
        "reuters.com": 8,
        "economictimes.com": 8,
        "livemint.com": 8,
        "thehindu.com": 8,
        "ndtv.com": 7,
        "business-standard.com": 7,
        "moneycontrol.com": 7,
        "securityweek.com": 8,
        "darkreading.com": 8,
        "bleepingcomputer.com": 7,
        "thehackernews.com": 7,
        "krebsonsecurity.com": 9,
    }

    TRADE_DOMAINS = {
        # Security Industry Associations (high credibility)
        "asisonline.org": 9,
        "asis.org": 9,
        "isaca.org": 9,
        "isc2.org": 9,
        "sans.org": 9,
        "securityindustry.org": 8,
        # Security Publications
        "csoonline.com": 7,
        "infosecurity-magazine.com": 7,
        "scmagazine.com": 7,
        "helpnetsecurity.com": 7,
        # Research & Analysis
        "gartner.com": 8,
        "forrester.com": 8,
    }

    def __init__(self, timeout: int = 15):
        self.timeout = config.get("article.request_timeout", timeout)
        self._config = None

        if TRAFILATURA_AVAILABLE:
            # Configure trafilatura for better extraction
            self._config = use_config()
            self._config.set("DEFAULT", "EXTRACTION_TIMEOUT", str(self.timeout))

    @property
    def source_type(self) -> str:
        return "article"

    @property
    def default_credibility(self) -> int:
        return 6

    def is_available(self) -> bool:
        """Check if ArticleMiner is properly configured."""
        if not TRAFILATURA_AVAILABLE:
            logger.warning("trafilatura not installed")
            return False
        return True

    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            # Remove www. prefix
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
        except Exception:
            return ""

    def _get_credibility_for_domain(self, domain: str) -> int:
        """
        Determine credibility weight based on domain.
        """
        # Check official sources first
        for official, weight in self.OFFICIAL_DOMAINS.items():
            if official in domain:
                return weight

        # Check news domains
        for news, weight in self.NEWS_DOMAINS.items():
            if news in domain:
                return weight

        # Check trade publications
        for trade, weight in self.TRADE_DOMAINS.items():
            if trade in domain:
                return weight

        # Check for government domains
        if ".gov" in domain or ".nic.in" in domain:
            return 9

        # Check for academic domains
        if ".edu" in domain or ".ac.in" in domain:
            return 8

        return self.default_credibility

    def _extract_article(self, url: str) -> Optional[dict]:
        """
        Extract article content and metadata from URL.
        """
        if not TRAFILATURA_AVAILABLE:
            return None

        try:
            # Download the page
            downloaded = trafilatura.fetch_url(url)
            if not downloaded:
                logger.debug("article_download_failed", url=url)
                return None

            # Extract content
            content = trafilatura.extract(
                downloaded,
                include_comments=False,
                include_tables=True,
                no_fallback=False,
                config=self._config,
            )

            if not content:
                logger.debug("article_extraction_failed", url=url)
                return None

            # Extract metadata
            metadata = trafilatura.extract_metadata(downloaded)

            title = ""
            author = ""
            date = None
            description = ""

            if metadata:
                title = metadata.title or ""
                author = metadata.author or ""
                description = metadata.description or ""
                if metadata.date:
                    try:
                        date = datetime.fromisoformat(metadata.date)
                    except Exception:
                        pass

            return {
                "content": content,
                "title": title,
                "author": author,
                "date": date,
                "description": description,
            }

        except Exception as e:
            logger.warning("article_extraction_error", url=url, error=str(e))
            return None

    def fetch(self, query: str, limit: int = 5) -> List[EvidenceItem]:
        """
        Fetch article content from URLs.

        Note: This method expects a list of URLs or uses web search.
        For query-based search, integrate with SerpAPI or Google Custom Search.

        Args:
            query: Search query or comma-separated URLs
            limit: Maximum number of articles to return

        Returns:
            List of EvidenceItem objects with article content
        """
        if not self.is_available():
            logger.error("article_miner_not_available")
            return []

        logger.info("article_fetch_started", query=query[:100], limit=limit)

        evidence_items = []

        # Check if query is a list of URLs
        urls = []
        if "http" in query:
            # Split by comma, semicolon, or newline
            urls = [
                u.strip()
                for u in re.split(r"[,;\n]", query)
                if u.strip().startswith("http")
            ]

        for idx, url in enumerate(urls[:limit]):
            article = self._extract_article(url)

            if not article or not article.get("content"):
                continue

            domain = self._get_domain(url)
            credibility = self._get_credibility_for_domain(domain)

            content = article["content"]

            evidence_items.append(
                EvidenceItem(
                    id=self._make_id(len(evidence_items)),
                    title=article.get("title") or f"Article from {domain}",
                    url=url,
                    raw_content=content,
                    source_type=self.source_type,
                    publisher=domain,
                    published=article.get("date"),
                    credibility_weight=credibility,
                    domain=domain,
                    snippet=content[:500] + "..." if len(content) > 500 else content,
                    identifier=url,
                    metadata={
                        "author": article.get("author", ""),
                        "description": article.get("description", ""),
                    },
                )
            )

        logger.info("article_fetch_complete", count=len(evidence_items))
        return evidence_items

    def fetch_url(self, url: str) -> Optional[EvidenceItem]:
        """
        Fetch content from a single URL.
        Convenience method for extracting individual articles.
        """
        results = self.fetch(url, limit=1)
        return results[0] if results else None


# CLI testing
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Article Miner CLI")
    parser.add_argument("--url", type=str, help="URL to extract")
    parser.add_argument("--urls", type=str, help="Comma-separated URLs")
    args = parser.parse_args()

    miner = ArticleMiner()

    if not miner.is_available():
        print("ArticleMiner not available. Install: pip install trafilatura")
    else:
        if args.url:
            result = miner.fetch_url(args.url)
            if result:
                print(f"\n📰 {result.title}")
                print(f"   Publisher: {result.publisher}")
                print(f"   Credibility: {result.credibility_weight}/10")
                print(f"   Content: {result.snippet}...\n")
        elif args.urls:
            results = miner.fetch(args.urls)
            print(f"\n📰 Extracted {len(results)} articles:\n")
            for item in results:
                print(f"  [{item.id}] {item.title}")
                print(f"       Publisher: {item.publisher}")
                print(f"       Credibility: {item.credibility_weight}/10\n")
