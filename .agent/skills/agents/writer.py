from typing import Dict, Union
from shared.logger import get_logger
from skills.gemini_client import GeminiAgent
from config.manager import config
from shared.models import ArticleDraft

logger = get_logger("Writer")

class WriterAgent:
    def __init__(self, client: GeminiAgent):
        self.client = client

    def write_draft(self, topic: Dict, outline: str, research: Dict) -> Union[ArticleDraft, None]:
        content_type = topic.get('content_type', 'Guide')
        specs = config.get(f"content_specs.{content_type}", config.get("content_specs.General"))
        
        logger.info("writing_draft", target_words=specs.min_words)
        research_notes = research.get("notes", {})
        evidence = research.get("evidence", [])
        
        prompt = f"""
You are a Senior Writer at The Economist. Write with precision, authority, and clarity.

OUTLINE TO EXECUTE:
{outline[:6000]}

RESEARCH TO DRAW FROM:
NOTES (with citations):
{research_notes}

EVIDENCE PACK (use citation IDs like [S1], [S2]):
{evidence}

═══════════════════════════════════════════════════════════════════════════════
MANDATORY STYLE RULES (STRUNK & WHITE):
═══════════════════════════════════════════════════════════════════════════════
1. OMIT NEEDLESS WORDS.
2. USE ACTIVE VOICE.
3. PUT STATEMENTS IN POSITIVE FORM.
4. USE SPECIFIC, CONCRETE LANGUAGE.
5. PLACE EMPHATIC WORDS AT THE END.

BRITISH ENGLISH (NON-NEGOTIABLE):
- Spellings: colour, organise, defence, centre
- Dates: 17 January 2026
- Currency: ₹5 lakh, ₹1.2 crore (Use INR for all costs)

INDIA CONTEXT (CRITICAL):
- You MUST cite specific Indian regulations (e.g., "Section 43A of IT Act", "IS 550:2014", "DPDP Act 2023").
- Use Indian examples, cities, and context where applicable.
- Reference Indian regulatory bodies (MHA, RBI, SEBI, BIS, CERT-In).

MANDATORY CITATION RULE:
- Every non-obvious factual claim must carry a citation like [S1].
- Use ONLY citation IDs from the evidence pack.
- End the article with a \"## Sources\" section listing each source as \"S# - Title (URL)\".

OUTPUT FORMAT (VALID JSON matching strict schema):
{{
    "title": "Max 70 chars",
    "description": "Max 160 chars",
    "topic": "{topic['topic']}",
    "category": "{topic.get('category', 'Security')}", 
    "content_type": "{content_type}",
    "tags": ["tag1", "tag2"],
    "regulations": ["Reg 1", "Reg 2"],
    "wordCount": <int>,
    "sources": [{{"id": "S1", "title": "Title", "url": "url"}}],
    "body": "# Full Markdown Content..."
}}

TARGET WORD COUNT: {specs.min_words} minimum
TARGET SOURCES: {specs.min_sources} minimum
"""
        try:
            data = self.client.generate_json(prompt)
            if isinstance(data, list) and data:
                data = data[0]
            
            # Validate with Pydantic
            draft = ArticleDraft(**data)
            return draft
        except Exception as e:
            logger.error(
                "draft_validation_failed",
                error=str(e),
                hint="Model output did not match schema. Ensure JSON keys + body are present."
            )
            return None

    def revise_draft(self, topic: Dict, outline: str, research: Dict, issues: list, prior_body: str) -> Union[ArticleDraft, None]:
        """Revise draft using explicit issues list."""
        content_type = topic.get('content_type', 'Guide')
        specs = config.get(f"content_specs.{content_type}", config.get("content_specs.General"))
        research_notes = research.get("notes", {})
        evidence = research.get("evidence", [])

        prompt = f"""
You are a Senior Editor and Writer. Revise the draft to FIX ALL ISSUES listed.

ISSUES TO FIX:
{issues}

OUTLINE TO FOLLOW:
{outline[:4000]}

EVIDENCE PACK (use citation IDs like [S1], [S2]):
{evidence}

CURRENT DRAFT:
{prior_body[:8000]}

MANDATORY:
- Fix structure and depth to meet {specs.min_words}+ words.
- Ensure every non-obvious factual claim has [S#] citation from evidence pack.
- End with a \"## Sources\" section with \"S# - Title (URL)\".
- British English.

OUTPUT FORMAT (VALID JSON matching strict schema):
{{
  \"title\": \"Max 70 chars\",
  \"description\": \"Max 160 chars\",
  \"topic\": \"{topic['topic']}\",
  \"category\": \"{topic.get('category', 'Security')}\",
  \"content_type\": \"{content_type}\",
  \"tags\": [\"tag1\", \"tag2\"],
  \"regulations\": [\"Reg 1\", \"Reg 2\"],
  \"wordCount\": <int>,
  \"sources\": [{{\"id\": \"S1\", \"title\": \"Title\", \"url\": \"url\"}}],
  \"body\": \"# Full Markdown Content...\"
}}
"""
        try:
            data = self.client.generate_json(prompt)
            if isinstance(data, list) and data:
                data = data[0]
            draft = ArticleDraft(**data)
            return draft
        except Exception as e:
            logger.error(
                "draft_revision_failed",
                error=str(e),
                hint="Revision JSON invalid. Ensure the revision prompt includes the full schema."
            )
            return None
