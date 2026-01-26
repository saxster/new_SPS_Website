from typing import Dict, Any, List, Optional
from shared.logger import get_logger
from skills.gemini_client import GeminiAgent
from config.manager import config
from skills.research_sources import ResearchFetcher

logger = get_logger("Researcher")

class ResearchAgent:
    def __init__(self, client: GeminiAgent, miners: Optional[List] = None):
        """
        Initialize ResearchAgent with optional miners for multi-source evidence.
        
        Args:
            client: GeminiAgent for LLM operations
            miners: Optional list of BaseMiner instances for multi-source ingestion
        """
        self.client = client
        self.fetcher = ResearchFetcher(miners=miners or [])

    def research(self, topic: Dict) -> Dict[str, Any]:
        """Conducts grounded research and returns an evidence pack with notes."""
        topic_str = topic.get('topic', '').strip()
        content_type = topic.get('content_type', 'Guide')
        
        # Security: Basic sanitization
        if "Ignore previous" in topic_str:
            logger.warning("potential_prompt_injection_detected", topic=topic_str)
            topic_str = topic_str.replace("Ignore previous", "")

        specs = config.get(f"content_specs.{content_type}", config.get("content_specs.General"))
        
        logger.info("starting_research", topic=topic_str)

        evidence_items = self.fetcher.build_evidence_pack(topic_str)
        # Enrich with full-text snippets where possible
        for item in evidence_items:
            if not item.snippet:
                item.snippet = self.fetcher.fetch_full_text(item.url)
        if evidence_items:
            try:
                self.fetcher._save_cache()
            except Exception:
                pass

        evidence = [
            {
                "id": f"S{idx+1}",
                "title": item.title,
                "url": item.url,
                "publisher": item.publisher,
                "published": item.published,
                "source_type": item.source_type,
                "snippet": item.snippet,
                "domain": item.domain,
                "quality_score": item.quality_score,
                "identifier": getattr(item, "identifier", ""),
                "accessed_at": getattr(item, "accessed_at", ""),
                "credibility_weight": getattr(item, "credibility_weight", 5),
                "raw_content": getattr(item, "raw_content", "")
            }
            for idx, item in enumerate(evidence_items)
        ]

        if not evidence:
            return {
                "topic": topic_str,
                "content_type": content_type,
                "evidence": [],
                "notes": {
                    "summary": "Insufficient evidence retrieved to ground this topic.",
                    "definitions": [],
                    "statistics": [],
                    "regulations": [],
                    "case_studies": [],
                    "costs": [],
                    "gaps": ["Evidence retrieval returned no sources. Add sources before publishing."]
                }
            }

        prompt = f"""
You are a Senior Research Analyst at a Bloomberg-level publication.
Your research will form the backbone of a {specs.min_words}+ word article.

TOPIC: {topic_str}
TARGET AUDIENCE: {topic.get('target_audience', 'Security Professionals')}
CONTENT TYPE: {content_type}

You MUST use ONLY the evidence pack below. If evidence is insufficient, say so explicitly.

EVIDENCE PACK (use citation IDs like [S1], [S2]):
{evidence}

Return JSON with these keys:
{{
  "summary": "3-5 sentence research synthesis with citations",
  "definitions": ["Term - definition [S#]"],
  "statistics": ["Stat with source and year [S#]"],
  "regulations": ["Full name and year + relevance [S#]"],
  "case_studies": ["Org, location, what, outcome [S#]"],
  "costs": ["Cost ranges with context [S#]"],
  "gaps": ["Known gaps or conflicting data [S# or 'no evidence']"]
}}
"""
        notes = self.client.generate_json(prompt)
        return {
            "topic": topic_str,
            "content_type": content_type,
            "evidence": evidence,
            "notes": notes
        }
