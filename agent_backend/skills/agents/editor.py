from typing import Dict, Union
from shared.logger import get_logger
from skills.gemini_client import GeminiAgent
from config.manager import config
from shared.models import ArticleDraft

logger = get_logger("Editor")

class EditorAgent:
    def __init__(self, client: GeminiAgent):
        self.client = client

    def review(self, draft: ArticleDraft) -> Dict:
        specs = config.get(f"content_specs.{draft.contentType}", config.get("content_specs.General"))
        
        logger.info("reviewing_draft", title=draft.title)
        
        prompt = f"""
You are a Senior Editor conducting a CRITICAL review before publication.

ARTICLE: {draft.title}
TYPE: {draft.contentType}
BODY:
{draft.body[:10000]}

EVALUATION CRITERIA:
1. STRUNK & WHITE COMPLIANCE
2. DEPTH CHECK (Target {specs.min_sources} sources)
3. BRITISH ENGLISH
4. BANNED PHRASES (game-changer, best-in-class, etc.)

OUTPUT FORMAT (JSON):
{{
    "overall_score": <0-100>,
    "verdict": "PUBLISH" | "REVISE" | "REJECT",
    "verdict_reason": "string",
    "critical_fixes_needed": ["fix1", "fix2"]
}}
"""
        return self.client.generate_json(prompt)
