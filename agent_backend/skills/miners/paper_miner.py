"""
PaperMiner: Extracts content from academic papers.
Sources: arXiv, Semantic Scholar, Crossref.

Features:
- arXiv API for security/cryptography papers (cs.CR, cs.CY)
- Abstract and introduction extraction
- DOI-based lookup via Crossref
- High credibility weight (9) for peer-reviewed content
"""

import os
import re
import time
import xml.etree.ElementTree as ET
from typing import List, Optional
from datetime import datetime
from urllib.parse import urlencode, quote
import requests

from .base_miner import BaseMiner, EvidenceItem

from config.manager import config
from shared.logger import get_logger

logger = get_logger("PaperMiner")

# arXiv categories relevant to security
SECURITY_CATEGORIES = {
    "cs.CR": "Cryptography and Security",
    "cs.CY": "Computers and Society",
    "cs.NI": "Networking and Internet Architecture",
    "cs.SE": "Software Engineering",
}


class PaperMiner(BaseMiner):
    """
    Academic paper miner for peer-reviewed security research.
    
    Credibility weight: 9 (peer-reviewed academic sources)
    Sources:
        - arXiv (primary): Free access to preprints
        - Semantic Scholar: Paper metadata and citations
        - Crossref: DOI resolution and metadata
    """
    
    ARXIV_API_URL = "http://export.arxiv.org/api/query"
    SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1/paper"
    
    def __init__(self, timeout: int = 15):
        self.timeout = config.get("paper.request_timeout", timeout)
        self.rate_limit_delay = config.get("paper.rate_limit_delay", 1.0)
        self.max_abstract_length = config.get("paper.max_abstract_length", 2000)
    
    @property
    def source_type(self) -> str:
        return "paper"
    
    @property
    def default_credibility(self) -> int:
        return 9  # High credibility for peer-reviewed work
    
    def is_available(self) -> bool:
        """arXiv API is publicly available without authentication."""
        return True
    
    def _parse_arxiv_date(self, date_str: str) -> Optional[datetime]:
        """Parse arXiv date format (YYYY-MM-DDTHH:MM:SSZ)."""
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except Exception:
            return None
    
    def _clean_abstract(self, abstract: str) -> str:
        """Clean up abstract text."""
        if not abstract:
            return ""
        # Remove excessive whitespace
        abstract = re.sub(r'\s+', ' ', abstract)
        # Truncate if too long
        if len(abstract) > self.max_abstract_length:
            abstract = abstract[:self.max_abstract_length] + "..."
        return abstract.strip()
    
    def _extract_arxiv_id(self, url_or_id: str) -> Optional[str]:
        """Extract arXiv ID from URL or return if already an ID."""
        # Match patterns like: 2301.12345, cs/0612001, arXiv:2301.12345
        patterns = [
            r'arxiv\.org/abs/(\d{4}\.\d{4,5})',  # New format
            r'arxiv\.org/abs/([\w-]+/\d+)',      # Old format (cs/0612001)
            r'arXiv:(\d{4}\.\d{4,5})',           # Prefixed format
            r'^(\d{4}\.\d{4,5})$',                # Just the ID
        ]
        for pattern in patterns:
            match = re.search(pattern, url_or_id)
            if match:
                return match.group(1)
        return None
    
    def _search_arxiv(self, query: str, limit: int = 5) -> List[EvidenceItem]:
        """
        Search arXiv for papers matching query.
        Focuses on security-related categories (cs.CR, cs.CY).
        """
        evidence_items = []
        
        # Build query with security category preference
        search_query = f"all:{query} AND (cat:cs.CR OR cat:cs.CY OR cat:cs.NI)"
        
        params = {
            "search_query": search_query,
            "start": 0,
            "max_results": limit,
            "sortBy": "relevance",
            "sortOrder": "descending"
        }
        
        try:
            # Rate limiting
            time.sleep(self.rate_limit_delay)
            
            response = requests.get(
                self.ARXIV_API_URL,
                params=params,
                timeout=self.timeout,
                headers={"User-Agent": "SPS-ContentIntelligence/1.0"}
            )
            response.raise_for_status()
            
            # Parse Atom feed
            root = ET.fromstring(response.text)
            namespace = {"atom": "http://www.w3.org/2005/Atom"}
            
            for idx, entry in enumerate(root.findall("atom:entry", namespace)):
                if len(evidence_items) >= limit:
                    break
                
                title = entry.find("atom:title", namespace)
                title_text = title.text.strip() if title is not None and title.text else ""
                
                abstract = entry.find("atom:summary", namespace)
                abstract_text = abstract.text.strip() if abstract is not None and abstract.text else ""
                
                published = entry.find("atom:published", namespace)
                pub_date = self._parse_arxiv_date(published.text) if published is not None and published.text else None
                
                # Get arXiv ID from id element
                id_elem = entry.find("atom:id", namespace)
                arxiv_url = id_elem.text if id_elem is not None else ""
                arxiv_id = self._extract_arxiv_id(arxiv_url) or ""
                
                # Get authors
                authors = []
                for author in entry.findall("atom:author", namespace):
                    name = author.find("atom:name", namespace)
                    if name is not None and name.text:
                        authors.append(name.text)
                authors_str = ", ".join(authors[:3])
                if len(authors) > 3:
                    authors_str += f" et al."
                
                # Get categories
                categories = []
                for category in entry.findall("atom:category", namespace):
                    term = category.get("term", "")
                    if term in SECURITY_CATEGORIES:
                        categories.append(SECURITY_CATEGORIES[term])
                
                evidence_items.append(EvidenceItem(
                    id=self._make_id(len(evidence_items)),
                    title=title_text,
                    url=arxiv_url,
                    raw_content=self._clean_abstract(abstract_text),
                    source_type=self.source_type,
                    publisher=f"arXiv ({', '.join(categories) or 'Computer Science'})",
                    published=pub_date,
                    credibility_weight=self.default_credibility,
                    domain="arxiv.org",
                    snippet=self._clean_abstract(abstract_text)[:500],
                    identifier=arxiv_id,
                    metadata={
                        "authors": authors_str,
                        "arxiv_id": arxiv_id,
                        "categories": categories
                    }
                ))
                
        except requests.HTTPError as e:
            logger.warning("arxiv_search_failed", status=e.response.status_code if e.response else None, error=str(e))
        except Exception as e:
            logger.warning("arxiv_search_error", error=str(e))
        
        return evidence_items
    
    def _fetch_semantic_scholar(self, paper_id: str) -> Optional[dict]:
        """
        Fetch paper details from Semantic Scholar API.
        paper_id can be arXiv ID (e.g., "arXiv:2301.12345") or DOI.
        """
        try:
            # Rate limiting
            time.sleep(self.rate_limit_delay)
            
            # Semantic Scholar accepts arXiv IDs with prefix
            if not paper_id.startswith("arXiv:") and re.match(r'\d{4}\.\d{4,5}', paper_id):
                paper_id = f"arXiv:{paper_id}"
            
            url = f"{self.SEMANTIC_SCHOLAR_API}/{quote(paper_id)}"
            params = {"fields": "title,abstract,authors,year,citationCount,venue,url"}
            
            response = requests.get(
                url,
                params=params,
                timeout=self.timeout,
                headers={"User-Agent": "SPS-ContentIntelligence/1.0"}
            )
            
            if response.status_code == 200:
                return response.json()
            
        except Exception as e:
            logger.debug("semantic_scholar_fetch_failed", paper_id=paper_id, error=str(e))
        
        return None
    
    def fetch(self, query: str, limit: int = 5) -> List[EvidenceItem]:
        """
        Fetch academic papers matching the query.
        
        Args:
            query: Search query (e.g., "zero trust architecture")
            limit: Maximum number of papers to return
            
        Returns:
            List of EvidenceItem objects with paper abstracts
        """
        logger.info("paper_fetch_started", query=query[:100], limit=limit)
        
        # Primary: Search arXiv
        evidence_items = self._search_arxiv(query, limit)
        
        # Enrich with Semantic Scholar data if available
        for item in evidence_items:
            arxiv_id = item.metadata.get("arxiv_id", "")
            if arxiv_id:
                ss_data = self._fetch_semantic_scholar(arxiv_id)
                if ss_data:
                    item.metadata["citation_count"] = ss_data.get("citationCount", 0)
                    item.metadata["venue"] = ss_data.get("venue", "")
                    # Boost credibility if highly cited
                    if ss_data.get("citationCount", 0) > 100:
                        item.credibility_weight = 10
        
        logger.info("paper_fetch_complete", count=len(evidence_items))
        return evidence_items
    
    def fetch_by_arxiv_id(self, arxiv_id: str) -> Optional[EvidenceItem]:
        """
        Fetch a specific paper by arXiv ID.
        """
        # Clean the ID
        clean_id = self._extract_arxiv_id(arxiv_id) or arxiv_id
        
        params = {
            "id_list": clean_id,
            "max_results": 1
        }
        
        try:
            time.sleep(self.rate_limit_delay)
            
            response = requests.get(
                self.ARXIV_API_URL,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            root = ET.fromstring(response.text)
            namespace = {"atom": "http://www.w3.org/2005/Atom"}
            
            entry = root.find("atom:entry", namespace)
            if entry is None:
                return None
            
            title = entry.find("atom:title", namespace)
            abstract = entry.find("atom:summary", namespace)
            published = entry.find("atom:published", namespace)
            id_elem = entry.find("atom:id", namespace)
            
            return EvidenceItem(
                id="S1",
                title=title.text.strip() if title is not None and title.text else "",
                url=id_elem.text if id_elem is not None else f"https://arxiv.org/abs/{clean_id}",
                raw_content=self._clean_abstract(abstract.text if abstract is not None else ""),
                source_type=self.source_type,
                publisher="arXiv",
                published=self._parse_arxiv_date(published.text) if published is not None else None,
                credibility_weight=self.default_credibility,
                domain="arxiv.org",
                snippet=self._clean_abstract(abstract.text if abstract is not None else "")[:500],
                identifier=clean_id
            )
            
        except Exception as e:
            logger.warning("arxiv_fetch_by_id_failed", arxiv_id=arxiv_id, error=str(e))
            return None


# CLI testing
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Paper Miner CLI")
    parser.add_argument("--query", type=str, default="zero trust security architecture")
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--arxiv-id", type=str, help="Fetch specific arXiv paper by ID")
    args = parser.parse_args()
    
    miner = PaperMiner()
    
    if args.arxiv_id:
        result = miner.fetch_by_arxiv_id(args.arxiv_id)
        if result:
            print(f"\n📄 {result.title}")
            print(f"   arXiv: {result.identifier}")
            print(f"   Credibility: {result.credibility_weight}/10")
            print(f"   Abstract: {result.snippet}...\n")
    else:
        results = miner.fetch(args.query, args.limit)
        print(f"\n📄 Found {len(results)} papers:\n")
        for item in results:
            print(f"  [{item.id}] {item.title}")
            print(f"       arXiv: {item.identifier}")
            print(f"       Authors: {item.metadata.get('authors', 'Unknown')}")
            print(f"       Credibility: {item.credibility_weight}/10\n")
