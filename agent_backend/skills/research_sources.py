"""
Research Sources and Evidence Pack Builder
Retrieves sources from SerpAPI, Crossref, Semantic Scholar, and RSS feeds
and extracts a minimal full-text snippet for grounded summarisation.
"""

from __future__ import annotations

import os
import re
import time
import json
import hashlib
import logging
from dataclasses import dataclass
from typing import List, Dict, Optional
from urllib.parse import urlencode, urlparse

import requests
from bs4 import BeautifulSoup

from config.manager import config
from shared.logger import get_logger

logger = get_logger("ResearchSources")


@dataclass
class SourceItem:
    id: str
    title: str
    url: str
    publisher: str
    published: Optional[str]
    source_type: str
    snippet: str
    quality_score: int
    domain: str
    identifier: str
    accessed_at: str


class ResearchFetcher:
    def __init__(self):
        self.timeout = config.get("research.request_timeout", 15)
        self.max_sources = config.get("research.max_sources", 12)
        self.serpapi_key = os.getenv("SERPAPI_API_KEY")
        self.crossref_mailto = config.get("research.crossref_mailto", "")
        self.rss_feeds = config.get("research.rss_feeds", [])
        self.allowed_domains = set(config.get("research.allowed_domains", []))
        self.domain_weights = config.get("research.domain_weights", {})
        self.min_quality = config.get("research.min_quality", 60)
        self.cache_path = config.get("research.cache_path", ".agent/evidence_cache.json")
        self.cache = self._load_cache()

    def build_evidence_pack(self, query: str) -> List[SourceItem]:
        # Avoid network calls during tests
        if os.getenv("PYTEST_CURRENT_TEST") or os.getenv("RESEARCH_DISABLE_NETWORK") == "1":
            return []
        items: List[SourceItem] = []

        # 1) SerpAPI (general web)
        if self.serpapi_key:
            items.extend(self._serpapi_search(query))
        else:
            logger.warning("serpapi_key_missing", hint="Set SERPAPI_API_KEY to enable web search sources.")

        # 2) Crossref (academic)
        items.extend(self._crossref_search(query))

        # 3) RSS feeds (optional)
        items.extend(self._rss_search(query))

        # Deduplicate by URL and apply quality/domain filters
        deduped: Dict[str, SourceItem] = {}
        for item in items:
            if not item.url:
                continue
            if self.allowed_domains:
                if not any(item.url.startswith(d) or d in item.url for d in self.allowed_domains):
                    continue
            if item.quality_score < self.min_quality:
                continue
            deduped[item.url] = item
        # De-duplicate by similar titles and sort by quality
        final_items = self._dedupe_titles(list(deduped.values()))
        final_items = sorted(final_items, key=lambda x: x.quality_score, reverse=True)[: self.max_sources]
        self._save_cache()
        return final_items

    def _serpapi_search(self, query: str) -> List[SourceItem]:
        url = "https://serpapi.com/search.json"
        params = {
            "q": query,
            "engine": "google",
            "gl": "in",
            "hl": "en",
            "num": 10,
            "api_key": self.serpapi_key,
        }
        try:
            resp = requests.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            results = []
            for r in data.get("organic_results", []):
                title = r.get("title", "")
                link = r.get("link", "")
                snippet = r.get("snippet", "")
                publisher = r.get("source", "web")
                published = r.get("date", None)
                results.append(self._make_source(title, link, publisher, published, "web", snippet))
            return results
        except requests.HTTPError as e:
            status = getattr(e.response, "status_code", None)
            hint = "Check SERPAPI_API_KEY and quota."
            logger.error("serpapi_failed", status=status, error=str(e), hint=hint)
            return []
        except Exception as e:
            logger.error("serpapi_failed", error=str(e), hint="Network error or invalid response from SerpAPI.")
            return []

    def _crossref_search(self, query: str) -> List[SourceItem]:
        url = "https://api.crossref.org/works"
        params = {
            "query": query,
            "rows": 5,
        }
        headers = {}
        if self.crossref_mailto:
            headers["User-Agent"] = f"SPS-Newsroom/1.0 (mailto:{self.crossref_mailto})"
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            results = []
            for item in data.get("message", {}).get("items", []):
                title = (item.get("title") or [""])[0]
                link = item.get("URL", "")
                doi = item.get("DOI", "") or ""
                publisher = item.get("publisher", "Crossref")
                published = None
                if item.get("published-print"):
                    parts = item["published-print"].get("date-parts", [[None]])[0]
                    if parts and parts[0]:
                        published = "-".join(str(p) for p in parts if p)
                snippet = item.get("abstract", "") or ""
                snippet = self._clean_html(snippet)
                results.append(self._make_source(title, link, publisher, published, "academic", snippet, identifier=doi))
            return results
        except requests.HTTPError as e:
            status = getattr(e.response, "status_code", None)
            logger.error("crossref_failed", status=status, error=str(e), hint="Check Crossref rate limits or mailto header.")
            return []
        except Exception as e:
            logger.error("crossref_failed", error=str(e), hint="Network error or invalid response from Crossref.")
            return []

    def _rss_search(self, query: str) -> List[SourceItem]:
        try:
            import feedparser
        except Exception:
            return []
        results: List[SourceItem] = []
        for feed_url in self.rss_feeds:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:5]:
                    title = entry.get("title", "")
                    link = entry.get("link", "")
                    snippet = entry.get("summary", "")
                    publisher = entry.get("source", {}).get("title", "RSS") if isinstance(entry.get("source"), dict) else "RSS"
                    published = entry.get("published", None)
                    if query.lower() in (title + " " + snippet).lower():
                        results.append(self._make_source(title, link, publisher, published, "news", snippet))
            except Exception:
                continue
        return results

    def fetch_full_text(self, url: str) -> str:
        cached = self.cache.get(url)
        if cached and cached.get("snippet"):
            return cached.get("snippet", "")
        try:
            resp = requests.get(url, timeout=self.timeout, headers={"User-Agent": "SPS-Newsroom/1.0"})
            resp.raise_for_status()
            html = resp.text
            soup = BeautifulSoup(html, "lxml")
            # Prefer article/main content
            article = soup.find("article") or soup.find("main")
            if article:
                text = " ".join(p.get_text(" ", strip=True) for p in article.find_all("p"))
            else:
                text = " ".join(p.get_text(" ", strip=True) for p in soup.find_all("p"))
            snippet = self._clean_text(text)[:2000]
            self.cache[url] = {**(self.cache.get(url) or {}), "snippet": snippet, "cached_at": time.time()}
            return snippet
        except requests.HTTPError as e:
            status = getattr(e.response, "status_code", None)
            hint = "Source removed (410). Replace with alternate source." if status == 410 else "Check source availability."
            logger.warning("full_text_fetch_failed", url=url, status=status, error=str(e), hint=hint)
            return ""
        except Exception as e:
            logger.warning("full_text_fetch_failed", url=url, error=str(e), hint="Network error or blocked content.")
            return ""

    def _make_source(self, title: str, url: str, publisher: str, published: Optional[str], source_type: str, snippet: str, identifier: str = "") -> SourceItem:
        sid = self._make_id(title + url)
        domain = self._extract_domain(url)
        quality = self._score_domain(domain, source_type)
        accessed_at = time.strftime("%Y-%m-%d", time.gmtime())
        return SourceItem(
            id=sid,
            title=title.strip()[:300],
            url=url.strip(),
            publisher=publisher.strip() if publisher else "",
            published=published,
            source_type=source_type,
            snippet=self._clean_text(snippet)[:800],
            quality_score=quality,
            domain=domain,
            identifier=(identifier or "").strip(),
            accessed_at=accessed_at
        )

    def _make_id(self, text: str) -> str:
        return hashlib.md5(text.encode("utf-8")).hexdigest()[:8].upper()

    def _clean_html(self, text: str) -> str:
        return self._clean_text(re.sub(r"<[^>]+>", " ", text or ""))

    def _clean_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text or "").strip()

    def _extract_domain(self, url: str) -> str:
        try:
            return urlparse(url).netloc.lower()
        except Exception:
            return ""

    def _score_domain(self, domain: str, source_type: str) -> int:
        score = 60
        if domain.endswith(".gov.in") or domain.endswith(".gov") or domain.endswith(".nic.in"):
            score += 30
        if source_type == "academic":
            score += 20
        if domain in self.domain_weights:
            score += int(self.domain_weights.get(domain, 0))
        return max(0, min(100, score))

    def _dedupe_titles(self, items: List[SourceItem]) -> List[SourceItem]:
        import difflib
        kept: List[SourceItem] = []
        for item in items:
            title = (item.title or "").lower()
            if not title:
                kept.append(item)
                continue
            is_dup = False
            for existing in kept:
                ratio = difflib.SequenceMatcher(None, title, (existing.title or "").lower()).ratio()
                if ratio >= 0.85:
                    # keep higher quality item
                    if item.quality_score > existing.quality_score:
                        kept.remove(existing)
                        kept.append(item)
                    is_dup = True
                    break
            if not is_dup:
                kept.append(item)
        return kept

    def _load_cache(self) -> Dict:
        try:
            if os.path.exists(self.cache_path):
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _save_cache(self):
        try:
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, indent=2)
        except Exception:
            pass
