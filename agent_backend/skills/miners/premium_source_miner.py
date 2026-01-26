"""
Premium Source Miner: Browser-Based Content Extraction from Paywalled Sources

Supports:
- Browser automation (Playwright) for paywalled content
- RSS/API fallback for sources that support it
- Cookie persistence for session management
- Rate limiting (human-speed reading)
"""

from __future__ import annotations

import os
import json
import time
import hashlib
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from pathlib import Path

from config.manager import config
from shared.logger import get_logger
from lib.credential_vault import CredentialVault, AuthoritativeSource
from skills.taste_anchors import TasteAnchors
from skills.miners.base_miner import BaseMiner, EvidenceItem

# Optional dependencies
try:
    from playwright.sync_api import sync_playwright, Browser, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    sync_playwright = None

try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    FEEDPARSER_AVAILABLE = False
    feedparser = None

try:
    import trafilatura
    TRAFILATURA_AVAILABLE = True
except ImportError:
    TRAFILATURA_AVAILABLE = False
    trafilatura = None

logger = get_logger("PremiumSourceMiner")


@dataclass
class ExtractionResult:
    """Result of extracting an article from a premium source."""
    success: bool
    title: str
    content: str
    url: str
    word_count: int
    extraction_method: str  # "browser", "rss", "api"
    error: Optional[str] = None
    
    def to_evidence(self, source: AuthoritativeSource) -> EvidenceItem:
        """Convert to EvidenceItem for research pipeline."""
        return EvidenceItem(
            source_type="premium_article",
            title=self.title,
            url=self.url,
            snippet=self.content[:500],
            full_text=self.content,
            credibility_weight=source.credibility_weight,
            retrieved_at=datetime.now()
        )


class PremiumSourceMiner(BaseMiner):
    """
    Miner for premium/paywalled news sources.
    
    Strategies (in order of preference):
    1. RSS/API (if available) - fastest, most reliable
    2. Browser automation (Playwright) - for paywalled content
    3. Trafilatura fallback - for public content
    """
    
    @property
    def source_type(self) -> str:
        """Return the source type identifier."""
        return "premium"
    
    def __init__(
        self, 
        vault: Optional[CredentialVault] = None,
        anchors: Optional[TasteAnchors] = None
    ):
        self.vault = vault or CredentialVault()
        self.anchors = anchors or TasteAnchors()
        
        # Configuration
        self.human_speed_delay = config.get(
            "premium_sources.human_speed_delay_seconds", 
            30
        )
        self.max_articles = config.get(
            "premium_sources.max_articles_per_source", 
            50
        )
        
        # Browser session (lazy initialization)
        self._browser = None
        self._page = None
        
        # Cookies storage path
        self.cookies_dir = Path(".agent/cookies")
        self.cookies_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(
            "premium_source_miner_initialized",
            playwright=PLAYWRIGHT_AVAILABLE,
            feedparser=FEEDPARSER_AVAILABLE,
            trafilatura=TRAFILATURA_AVAILABLE
        )
    
    @property
    def required_dependencies(self) -> List[str]:
        """List of required dependencies."""
        return ["feedparser", "trafilatura"]  # Playwright is optional
    
    def get_status(self) -> Dict[str, Any]:
        """Get miner status."""
        sources = self.vault.list_sources()
        return {
            "available": True,
            "sources_configured": len(sources),
            "sources_enabled": sum(1 for s in sources if s.enabled),
            "playwright_available": PLAYWRIGHT_AVAILABLE,
            "rss_available": FEEDPARSER_AVAILABLE
        }
    
    # =========================================================================
    # Main Entry Points
    # =========================================================================
    
    def fetch(self, query: str = "") -> List[EvidenceItem]:
        """
        Fetch articles from all enabled premium sources.
        
        Args:
            query: Optional filter (not typically used for premium sources)
            
        Returns:
            List of EvidenceItem from premium sources
        """
        sources = self.vault.list_sources(enabled_only=True)
        evidence = []
        
        for source in sources:
            try:
                results = self.sync_source(source)
                evidence.extend([r.to_evidence(source) for r in results])
            except Exception as e:
                logger.error(
                    "source_fetch_failed",
                    source_id=source.id,
                    error=str(e)
                )
        
        return evidence
    
    def sync_source(self, source: AuthoritativeSource) -> List[ExtractionResult]:
        """
        Sync a single source, extracting new articles.
        
        Tries strategies in order:
        1. RSS/API if configured
        2. Browser automation if credentials available
        3. Public scraping via trafilatura
        """
        logger.info("syncing_source", source_id=source.id, name=source.name)
        
        results = []
        
        # Strategy 1: RSS/API (if available)
        if FEEDPARSER_AVAILABLE:
            rss_results = self._try_rss_extraction(source)
            if rss_results:
                results.extend(rss_results)
                logger.info(
                    "rss_extraction_success",
                    source_id=source.id,
                    count=len(rss_results)
                )
        
        # Strategy 2: Browser automation (if credentials and Playwright available)
        if not results and PLAYWRIGHT_AVAILABLE:
            if self.vault.has_credentials(source.id):
                browser_results = self._try_browser_extraction(source)
                if browser_results:
                    results.extend(browser_results)
                    logger.info(
                        "browser_extraction_success",
                        source_id=source.id,
                        count=len(browser_results)
                    )
        
        # Strategy 3: Public content via trafilatura
        if not results and TRAFILATURA_AVAILABLE:
            public_results = self._try_public_extraction(source)
            if public_results:
                results.extend(public_results)
                logger.info(
                    "public_extraction_success",
                    source_id=source.id,
                    count=len(public_results)
                )
        
        # Store as taste anchors
        for result in results:
            if result.success and result.content:
                self.anchors.add_exemplar(
                    source_id=source.id,
                    title=result.title,
                    content=result.content,
                    url=result.url,
                    credibility_weight=source.credibility_weight
                )
        
        # Update sync status
        self.vault.update_sync_status(source.id, len(results))
        
        return results
    
    # =========================================================================
    # Strategy 1: RSS/API Extraction
    # =========================================================================
    
    def _try_rss_extraction(
        self, 
        source: AuthoritativeSource
    ) -> List[ExtractionResult]:
        """Try extracting via RSS feed."""
        results = []
        
        # Common RSS feed patterns
        rss_patterns = [
            f"{source.base_url}/rss",
            f"{source.base_url}/feed",
            f"{source.base_url}/feeds/rss",
            f"{source.base_url}/rss.xml",
            f"{source.base_url}/feed.xml",
        ]
        
        # Try each pattern
        for rss_url in rss_patterns:
            try:
                feed = feedparser.parse(rss_url)
                
                if feed.entries:
                    logger.info("rss_feed_found", url=rss_url, entries=len(feed.entries))
                    
                    for entry in feed.entries[:source.max_articles_per_sync]:
                        # Extract full content
                        content = self._extract_entry_content(entry)
                        
                        if content:
                            results.append(ExtractionResult(
                                success=True,
                                title=entry.get("title", "Untitled"),
                                content=content,
                                url=entry.get("link", ""),
                                word_count=len(content.split()),
                                extraction_method="rss"
                            ))
                        
                        # Human-speed delay
                        time.sleep(self.human_speed_delay / 10)  # Faster for RSS
                    
                    break  # Found working RSS, stop trying patterns
                    
            except Exception as e:
                logger.debug("rss_pattern_failed", url=rss_url, error=str(e))
                continue
        
        return results
    
    def _extract_entry_content(self, entry: Dict) -> Optional[str]:
        """Extract full content from RSS entry."""
        # Try content field first
        if "content" in entry and entry["content"]:
            return entry["content"][0].get("value", "")
        
        # Try summary
        if "summary" in entry:
            summary = entry["summary"]
            
            # If summary is short, try to fetch full article
            if len(summary) < 500 and "link" in entry and TRAFILATURA_AVAILABLE:
                try:
                    full_text = trafilatura.fetch_url(entry["link"])
                    if full_text:
                        extracted = trafilatura.extract(full_text)
                        if extracted:
                            return extracted
                except Exception:
                    pass
            
            return summary
        
        return None
    
    # =========================================================================
    # Strategy 2: Browser Automation
    # =========================================================================
    
    def _try_browser_extraction(
        self, 
        source: AuthoritativeSource
    ) -> List[ExtractionResult]:
        """Try extracting via browser automation with login."""
        if not PLAYWRIGHT_AVAILABLE:
            return []
        
        results = []
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context()
                
                # Load saved cookies if available
                cookies_file = self.cookies_dir / f"{source.id}_cookies.json"
                if cookies_file.exists():
                    cookies = json.loads(cookies_file.read_text())
                    context.add_cookies(cookies)
                
                page = context.new_page()
                
                # Navigate to base URL
                page.goto(source.base_url, wait_until="networkidle")
                
                # Check if login needed
                if self._needs_login(page, source):
                    self._perform_login(page, source)
                    
                    # Save cookies after login
                    cookies = context.cookies()
                    cookies_file.write_text(json.dumps(cookies))
                
                # Extract articles
                articles = self._discover_articles(page, source)
                
                for article_url in articles[:source.max_articles_per_sync]:
                    result = self._extract_article(page, article_url, source)
                    if result.success:
                        results.append(result)
                    
                    # Human-speed delay
                    time.sleep(self.human_speed_delay)
                
                browser.close()
                
        except Exception as e:
            logger.error("browser_extraction_failed", source_id=source.id, error=str(e))
        
        return results
    
    def _needs_login(self, page: Any, source: AuthoritativeSource) -> bool:
        """Check if page requires login."""
        # Look for common login indicators
        indicators = [
            "login",
            "sign-in",
            "signin",
            "subscribe",
            "paywall"
        ]
        
        try:
            page_text = page.content().lower()
            return any(ind in page_text for ind in indicators)
        except:
            return False
    
    def _perform_login(self, page: Any, source: AuthoritativeSource):
        """Perform login on the page."""
        credentials = self.vault.get_credentials(source.id)
        if not credentials:
            return
        
        username, password = credentials
        
        try:
            # Navigate to login page
            if source.login_url:
                page.goto(source.login_url, wait_until="networkidle")
            
            # Fill credentials
            if source.username_selector:
                page.fill(source.username_selector, username)
            if source.password_selector:
                page.fill(source.password_selector, password)
            
            # Submit
            if source.submit_selector:
                page.click(source.submit_selector)
                page.wait_for_load_state("networkidle")
            
            logger.info("login_successful", source_id=source.id)
            
        except Exception as e:
            logger.error("login_failed", source_id=source.id, error=str(e))
    
    def _discover_articles(self, page: Any, source: AuthoritativeSource) -> List[str]:
        """Discover article URLs on the page."""
        article_urls = []
        
        try:
            # Look for article links
            links = page.query_selector_all("a")
            
            for link in links:
                href = link.get_attribute("href")
                if href and self._looks_like_article(href, source):
                    if href.startswith("/"):
                        href = source.base_url.rstrip("/") + href
                    article_urls.append(href)
            
            # Deduplicate
            article_urls = list(set(article_urls))
            
        except Exception as e:
            logger.warning("article_discovery_failed", error=str(e))
        
        return article_urls[:source.max_articles_per_sync]
    
    def _looks_like_article(self, url: str, source: AuthoritativeSource) -> bool:
        """Check if URL looks like an article."""
        # Filter out common non-article patterns
        skip_patterns = [
            "/tag/", "/category/", "/author/", "/search",
            "/login", "/subscribe", "/about", "/contact",
            ".jpg", ".png", ".pdf", "/wp-content/"
        ]
        
        url_lower = url.lower()
        return not any(p in url_lower for p in skip_patterns)
    
    def _extract_article(
        self, 
        page: Any, 
        url: str, 
        source: AuthoritativeSource
    ) -> ExtractionResult:
        """Extract a single article."""
        try:
            page.goto(url, wait_until="networkidle")
            
            # Try custom selector first
            content = ""
            if source.article_selector:
                try:
                    element = page.query_selector(source.article_selector)
                    if element:
                        content = element.inner_text()
                except:
                    pass
            
            # Fallback to trafilatura
            if not content and TRAFILATURA_AVAILABLE:
                html = page.content()
                content = trafilatura.extract(html) or ""
            
            # Get title
            title = ""
            try:
                title_element = page.query_selector("h1")
                if title_element:
                    title = title_element.inner_text()
            except:
                title = url.split("/")[-1].replace("-", " ").title()
            
            return ExtractionResult(
                success=bool(content),
                title=title,
                content=content,
                url=url,
                word_count=len(content.split()),
                extraction_method="browser"
            )
            
        except Exception as e:
            return ExtractionResult(
                success=False,
                title="",
                content="",
                url=url,
                word_count=0,
                extraction_method="browser",
                error=str(e)
            )
    
    # =========================================================================
    # Strategy 3: Public Content Extraction
    # =========================================================================
    
    def _try_public_extraction(
        self, 
        source: AuthoritativeSource
    ) -> List[ExtractionResult]:
        """Try extracting public content via trafilatura."""
        if not TRAFILATURA_AVAILABLE:
            return []
        
        results = []
        
        try:
            # Fetch and extract from base URL
            downloaded = trafilatura.fetch_url(source.base_url)
            if not downloaded:
                return []
            
            # Try to find article links
            from trafilatura import extract_metadata
            metadata = extract_metadata(downloaded)
            
            # Extract main content as sample
            content = trafilatura.extract(downloaded)
            if content:
                results.append(ExtractionResult(
                    success=True,
                    title=metadata.title if metadata else source.name,
                    content=content,
                    url=source.base_url,
                    word_count=len(content.split()),
                    extraction_method="public"
                ))
                
        except Exception as e:
            logger.debug("public_extraction_failed", error=str(e))
        
        return results
    
    # =========================================================================
    # Cleanup
    # =========================================================================
    
    def close(self):
        """Clean up browser resources."""
        if self._browser:
            self._browser.close()
            self._browser = None


# =============================================================================
# CLI for Testing
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Premium Source Miner CLI")
    parser.add_argument("--sync", type=str, help="Sync a specific source by ID")
    parser.add_argument("--list", action="store_true", help="List all sources")
    parser.add_argument("--status", action="store_true", help="Show miner status")
    args = parser.parse_args()
    
    miner = PremiumSourceMiner()
    
    if args.status:
        print(json.dumps(miner.get_status(), indent=2))
    
    elif args.list:
        vault = CredentialVault()
        for source in vault.list_sources():
            status = "✓" if source.enabled else "✗"
            print(f"[{status}] {source.name} ({source.id}) - weight: {source.credibility_weight}")
    
    elif args.sync:
        vault = CredentialVault()
        source = vault.get_source(args.sync)
        if source:
            results = miner.sync_source(source)
            print(f"\nSynced {len(results)} articles from {source.name}")
            for r in results:
                print(f"  - {r.title} ({r.word_count} words) [{r.extraction_method}]")
        else:
            print(f"Source not found: {args.sync}")
    
    else:
        print("Premium Source Miner")
        print("Usage: python -m skills.miners.premium_source_miner --help")
