from typing import Dict
from shared.logger import get_logger
from skills.gemini_client import GeminiAgent
from config.manager import config

logger = get_logger("Outliner")

class OutlinerAgent:
    def __init__(self, client: GeminiAgent):
        self.client = client

    def create_outline(self, topic: Dict, research: Dict) -> str:
        content_type = topic.get('content_type', 'Guide')
        specs = config.get(f"content_specs.{content_type}", config.get("content_specs.General"))
        
        logger.info("creating_outline", content_type=content_type)
        
        structure = self._get_structure(content_type)
        research_notes = research.get("notes", {})
        evidence = research.get("evidence", [])
        
        prompt = f"""
You are a Senior Editor at The Economist or Vox.
Create a DETAILED OUTLINE that will guide the writing of a {specs.min_words}+ word article.

CONTENT TYPE: {content_type}
TOPIC: {topic['topic']}

RESEARCH GATHERED:
NOTES (with citations):
{research_notes}

EVIDENCE PACK (IDs must be used in outline notes):
{evidence}

{structure}

FOR EACH SECTION IN YOUR OUTLINE:
1. Specify the key points to cover
2. List specific data/quotes from the research to include
2a. Include citation IDs like [S1] where used
3. Note the approximate word count
4. Suggest the emotional tone (authoritative, cautionary, encouraging, etc.)

ENSURE:
- Logical flow from section to section
- Each section builds on the previous
- No redundancy between sections
- The conclusion ties back to the opening hook

Output a structured outline that a writer can execute without guessing.
"""
        return self.client.generate(prompt)

    def _get_structure(self, content_type: str) -> str:
        # We can externalize these templates to YAML later
        templates = {
            "Guide": """
STRUCTURE FOR HOW-TO GUIDE (INDIA-CENTRIC):
1. HOOK (50 words): Anecdote or startling fact that grabs attention (India specific if possible)
2. WHY THIS MATTERS (150 words): Stakes for the reader, consequences of inaction
3. REGULATORY LANDSCAPE (INDIA) (300 words): MANDATORY section citing specific Acts (DPDP 2023, BNS, IS 550, etc.)
4. THE STEP-BY-STEP SOLUTION (1,000 words):
   - 5-8 major steps
   - Each step must include: What → Why → How → Pitfalls → Expert Tip
   - Localize prices (₹) and examples where applicable
5. COMMON MISTAKES TO AVOID (200 words): Real examples if available
6. ADVANCED CONSIDERATIONS (150 words): For sophisticated readers
7. CONCLUSION WITH CALL TO ACTION (100 words): Clear next steps
""",
            "Analysis": """
STRUCTURE FOR ANALYSIS/DEEP DIVE (INDIA-CENTRIC):
1. PROVOCATIVE OPENING (100 words): Challenge conventional wisdom or present a paradox
2. CENTRAL THESIS (50 words): One clear, arguable statement
3. REGULATORY LANDSCAPE (INDIA) (300 words): MANDATORY section citing specific Acts (DPDP 2023, BNS, IS 550, etc.)
4. EVIDENCE BLOCK 1 (400 words): Quantitative data + interpretation
5. EVIDENCE BLOCK 2 (400 words): Case study with lessons (Prefer Indian example)
6. EVIDENCE BLOCK 3 (400 words): Expert validation and quotes
7. COUNTER-ARGUMENTS (300 words): Steel-man the opposition, then refute
8. SYNTHESIS (200 words): Reconcile tensions, find the nuance
9. IMPLICATIONS AND FORECAST (150 words): What happens next, who should care
""",
            "QnA": """
STRUCTURE FOR Q&A (SEO OPTIMIZED):
1. THE DIRECT ANSWER (100 words): Immediate, concise answer to the specific question.
2. DETAILED EXPLANATION (400 words): The technical "Why" and "How".
3. REGULATORY CONTEXT (INDIA) (200 words): Relevant laws (PSARA, Fire Safety Act, etc.).
4. PRACTICAL CHECKLIST (200 words): 5-point action plan.
5. RELATED QUESTIONS (100 words): Link to broader context.
"""
        }
        return templates.get(content_type, templates["Guide"])
