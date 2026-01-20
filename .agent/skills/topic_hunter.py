#!/usr/bin/env python3
"""
TopicHunter: Autonomous Research Agent 🕵️‍♂️
Finds "Blue Ocean" content opportunities.
"""

import os
import sys
import json
import glob
import logging
import argparse
import re
import difflib
from typing import List, Dict, Union
from pydantic import BaseModel, Field

# Allow running from repo root without PYTHONPATH
AGENT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if AGENT_ROOT not in sys.path:
    sys.path.insert(0, AGENT_ROOT)

from config.manager import config
from shared.logger import get_logger
from skills.gemini_client import GeminiAgent
from skills.content_brain import ContentBrain

logger = get_logger("TopicHunter")

class TopicProposal(BaseModel):
    topic: str
    target_audience: str
    estimated_search_volume: Union[str, int] = Field(description="Low/Medium/High or Number")
    intent: str = Field(description="Informational/Transactional")
    gap_score: int = Field(description="0-100 score of how missing this is from our site")
    rationale: str
    content_type: str = "General"

class TopicHunter:
    def __init__(self):
        self.content_dir = config.get("paths.website_content_dir", "website/src/content/blog")
        self.agent = GeminiAgent()
        self.brain = ContentBrain()
        self.similarity_threshold = config.get("topic_dedup.similarity_threshold", 0.82)

    def run(self, domain="Physical Security Technology", content_type="General"):
        """Orchestrator method for Mission Control."""
        inventory = self.scan_inventory()
        self.hunt_opportunities(domain, inventory, content_type)

    def scan_inventory(self) -> List[str]:
        """Reads all existing blog post titles."""
        titles = []
        # MD files
        for filepath in glob.glob(os.path.join(self.content_dir, "**/*.md"), recursive=True):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.startswith("title:"):
                            titles.append(line.replace("title:", "").strip().strip('"'))
                            break
            except Exception:
                continue
                
        # JSON drafts
        drafts_dir = config.get("paths.drafts_dir", "drafts")
        for filepath in glob.glob(os.path.join(drafts_dir, "*.json")):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if 'title' in data:
                        titles.append(data['title'])
            except:
                pass
                
        # Include previously proposed topics to avoid repeats
        try:
            titles.extend(self.brain.list_topics())
        except Exception:
            pass
        logger.info("inventory_scanned", count=len(titles))
        return titles

    def _normalize(self, text: str) -> str:
        text = re.sub(r"[^a-z0-9\\s]", " ", (text or "").lower())
        return re.sub(r"\\s+", " ", text).strip()

    def _similarity(self, a: str, b: str) -> float:
        if not a or not b:
            return 0.0
        return difflib.SequenceMatcher(None, a, b).ratio()

    def _is_duplicate(self, topic: str, existing_norms: List[str]) -> bool:
        norm = self._normalize(topic)
        if not norm:
            return True
        for existing in existing_norms:
            if self._similarity(norm, existing) >= self.similarity_threshold:
                return True
        return False

    def hunt_opportunities(self, domain: str, existing_titles: List[str], content_type: str = "General") -> List[TopicProposal]:
        logger.info("hunting_started", domain=domain, type=content_type)
        
        prompt = f"""
        You are an elite SEO Strategist.
        Domain: {domain}
        Focus Content Type: {content_type}
        
        Tasks:
        1. Identify 5 high-impact Blue Ocean topics for 2026.
        2. Ensure they fit the specific Content Type: "{content_type}".
        3. Ensure they are distinct from: {json.dumps(existing_titles[:20])}...
        
        Return JSON list of objects (key "opportunities"):
        - topic
        - target_audience
        - estimated_search_volume
        - intent
        - gap_score (0-100)
        - rationale
        - content_type (Must be "{content_type}")
        """
        
        try:
            data = self.agent.generate_json(prompt)
            items = data.get("opportunities", []) if isinstance(data, dict) else data if isinstance(data, list) else []

            new_count = 0
            proposals = []
            existing_norms = [self._normalize(t) for t in existing_titles if t]
            kept_norms = list(existing_norms)
            for item in items:
                if 'topic' not in item and 'title' in item: item['topic'] = item['title']
                item['content_type'] = content_type

                if self._is_duplicate(item.get("topic", ""), kept_norms):
                    continue

                if self.brain.add_topic_proposal(item):
                    new_count += 1
                    kept_norms.append(self._normalize(item.get("topic", "")))
                    # Validate loosely
                    try:
                        proposals.append(TopicProposal(**item))
                    except:
                        pass
            
            logger.info("hunting_complete", new_topics=new_count)
            return proposals

        except Exception as e:
            logger.error("hunting_failed", error=str(e))
            return []

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--domain', default="Physical Security")
    parser.add_argument('--type', default="General")
    args = parser.parse_args()
    
    hunter = TopicHunter()
    hunter.run(args.domain, args.type)
