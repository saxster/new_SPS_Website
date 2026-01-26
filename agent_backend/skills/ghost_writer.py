#!/usr/bin/env python3
"""
GhostWriter V2: Orchestrator 👻
Coordinating the Autonomous Newsroom Agents.
"""
import os
import sys
import json
import argparse
import time
from typing import Dict, Optional, List
import tenacity
from tenacity import retry, stop_after_attempt, wait_exponential

# Allow running from repo root without PYTHONPATH
AGENT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if AGENT_ROOT not in sys.path:
    sys.path.insert(0, AGENT_ROOT)

from config.manager import config
from shared.logger import get_logger, setup_logging
from skills.content_brain import ContentBrain
from skills.gemini_client import GeminiAgent
from skills.art_director import ArtDirector
from skills.agents.researcher import ResearchAgent
from skills.agents.outliner import OutlinerAgent
from skills.agents.writer import WriterAgent
from skills.agents.editor import EditorAgent
from skills.quality_scorer import QualityScorer
from skills.citation_validator import CitationValidator
from skills.claim_ledger import ClaimLedger
from skills.miners.miner_factory import create_available_miners
from shared.models import ArticleDraft, ArticleSource, ArticleImage

# Initialize Logging
setup_logging()
logger = get_logger("GhostWriter")

class GhostWriterV2:
    def __init__(
        self, 
        client: Optional[GeminiAgent] = None,
        brain: Optional[ContentBrain] = None,
        art_director: Optional[ArtDirector] = None
    ):
        # Dependency Injection for Testability
        self.client = client or GeminiAgent()
        self.brain = brain or ContentBrain()
        self.art = art_director or ArtDirector()
        
        # Initialize multi-source miners from config
        self.miners = create_available_miners()
        logger.info("miners_initialized", count=len(self.miners), 
                   types=[m.source_type for m in self.miners])
        
        # Instantiate Sub-Agents with miners
        self.researcher = ResearchAgent(self.client, miners=self.miners)
        self.outliner = OutlinerAgent(self.client)
        self.writer = WriterAgent(self.client)
        self.editor = EditorAgent(self.client)
        self.scorer = QualityScorer()
        self.citation_validator = CitationValidator()
        self.claims = ClaimLedger()
        self.stage_timings = {}
        self.current_stage = ""
        self.hints = []

    def _record_hint(self, message: str):
        if message:
            self.hints.append(message)

    def _compute_word_count(self, text: str) -> int:
        import re
        return len(re.findall(r"[A-Za-z0-9']+", text or ""))

    def _ensure_sources_section(self, body: str, sources: List[ArticleSource], evidence: Optional[List[Dict]] = None) -> str:
        if not sources:
            return body
        if "## Sources" in body:
            return body
        lines = ["", "## Sources"]
        ev_map = {e.get("id"): e for e in (evidence or []) if isinstance(e, dict)}
        for s in sources:
            sid = getattr(s, "id", "")
            title = getattr(s, "title", "")
            url = getattr(s, "url", "")
            meta = ev_map.get(sid, {})
            accessed = meta.get("accessed_at") or ""
            publisher = meta.get("publisher") or ""
            identifier = meta.get("identifier") or ""
            parts = [sid, title, url]
            if publisher:
                parts.append(publisher)
            if identifier:
                parts.append(f"ID: {identifier}")
            if accessed:
                parts.append(f"Accessed: {accessed}")
            lines.append(" | ".join([p for p in parts if p]))
        return body.rstrip() + "\n" + "\n".join(lines) + "\n"

    def _attach_sources(self, draft_obj: ArticleDraft, research: Dict) -> List[Dict]:
        evidence = research.get("evidence", [])
        sources = []
        for item in evidence:
            sources.append(ArticleSource(
                id=item.get("id"),
                title=item.get("title"),
                url=item.get("url")
            ))
        # Only override if sources provided
        if sources:
            draft_obj.sources = sources  # Pydantic will coerce to ArticleSource
        return sources

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def run_stage_with_retry(self, stage_name: str, func, *args, **kwargs):
        """Helper to retry individual stages"""
        try:
            self.current_stage = stage_name
            start = time.monotonic()
            return func(*args, **kwargs)
        except Exception as e:
            logger.warning(f"stage_retry", stage=stage_name, error=str(e))
            raise
        finally:
            if self.current_stage == stage_name:
                duration = round(time.monotonic() - start, 2)
                self.stage_timings[stage_name] = duration
                logger.info("stage_done", stage=stage_name, duration_s=duration)

    def run_pipeline(self, topic: Dict) -> Optional[Dict]:
        """
        Execute the full pipeline with retries and state tracking.
        """
        try:
            pipeline_start = time.monotonic()
            logger.info("pipeline_start", topic=topic['topic'])

            # 1. Research
            research = self.run_stage_with_retry("Research", self.researcher.research, topic)
            logger.info("stage_complete", stage="Research", evidence=len(research.get("evidence", [])))
            evidence = research.get("evidence", [])
            content_type = topic.get("content_type", "General")
            specs = config.get(f"content_specs.{content_type}", config.get("content_specs.General"))
            min_sources = getattr(specs, "min_sources", 3)
            summary_note = (research.get("notes") or {}).get("summary", "")
            if "insufficient" in str(summary_note).lower():
                logger.warning("research_insufficient_summary", note=summary_note)
                try:
                    self.brain.mark_topic_rejected(topic.get("id", ""), "Research summary indicates insufficient evidence.")
                except Exception:
                    pass
                self._record_hint("Research evidence is insufficient. Add sources or expand query scope.")
                total_s = round(time.monotonic() - pipeline_start, 2)
                logger.info("pipeline_summary", status="halted", reason="insufficient_evidence", total_s=total_s, stages=self.stage_timings)
                return None
            if len(evidence) < int(min_sources):
                logger.warning("insufficient_evidence", needed=min_sources, found=len(evidence))
                try:
                    self.brain.mark_topic_rejected(topic.get("id", ""), "Insufficient evidence for grounded drafting.")
                except Exception:
                    pass
                self._record_hint("Too few sources retrieved. Add SerpAPI key or adjust research sources.")
                total_s = round(time.monotonic() - pipeline_start, 2)
                logger.info("pipeline_summary", status="halted", reason="insufficient_evidence", total_s=total_s, stages=self.stage_timings)
                return None
            
            # 2. Outline
            outline = self.run_stage_with_retry("Outline", self.outliner.create_outline, topic, research)
            logger.info("stage_complete", stage="Outline", length=len(outline))
            
            # 3. Write
            draft_obj = self.run_stage_with_retry("Drafting", self.writer.write_draft, topic, outline, research)
            if not draft_obj:
                logger.error(
                    "stage_failed",
                    stage="Drafting",
                    reason="Drafting returned no valid ArticleDraft. See draft_validation_failed above."
                )
                total_s = round(time.monotonic() - pipeline_start, 2)
                logger.info("pipeline_summary", status="failed", reason="draft_validation_failed", total_s=total_s, stages=self.stage_timings)
                return None

            # 3a. Attach evidence sources + ensure Sources section
            sources = self._attach_sources(draft_obj, research)
            draft_obj.body = self._ensure_sources_section(draft_obj.body, sources, evidence)
            draft_obj.wordCount = self._compute_word_count(draft_obj.body)

            # 3b. Objective quality scoring and one revision pass if needed
            score_result = self.scorer.score(draft_obj.model_dump(mode="json"))
            draft_obj.qualityScore = score_result.get("score", 0)
            if not score_result.get("passes"):
                logger.warning("quality_gate_failed", issues=score_result.get("issues", []))
                self._record_hint("Quality gate failed. Increase depth/sections and include required regulations.")
                revised = self.writer.revise_draft(
                    topic=topic,
                    outline=outline,
                    research=research,
                    issues=score_result.get("issues", []),
                    prior_body=draft_obj.body
                )
                if revised:
                    draft_obj = revised
                    sources = self._attach_sources(draft_obj, research)
                    draft_obj.body = self._ensure_sources_section(draft_obj.body, sources, evidence)
                    draft_obj.wordCount = self._compute_word_count(draft_obj.body)
                    score_result = self.scorer.score(draft_obj.model_dump(mode="json"))
                    draft_obj.qualityScore = score_result.get("score", 0)

            # 3c. Citation validation pass (revise once if needed)
            citation_result = self.citation_validator.validate(draft_obj.model_dump(mode="json"), evidence)
            if not citation_result.get("passes"):
                logger.warning("citation_gate_failed", issues=citation_result.get("issues", []))
                self._record_hint("Citation gate failed. Ensure every factual claim has [S#] and sources are in body.")
                revised = self.writer.revise_draft(
                    topic=topic,
                    outline=outline,
                    research=research,
                    issues=citation_result.get("issues", []),
                    prior_body=draft_obj.body
                )
                if revised:
                    draft_obj = revised
                    sources = self._attach_sources(draft_obj, research)
                    draft_obj.body = self._ensure_sources_section(draft_obj.body, sources, evidence)
                    draft_obj.wordCount = self._compute_word_count(draft_obj.body)
                    citation_result = self.citation_validator.validate(draft_obj.model_dump(mode="json"), evidence)

            # 3d. Claim ledger and contradiction check (revise once if needed)
            claim_ledger = self.claims.build(draft_obj.model_dump(mode="json"), evidence)
            if claim_ledger.get("issues"):
                logger.warning("claim_ledger_issues", issues=claim_ledger.get("issues", [])[:5])
                self._record_hint("Claim ledger found unsupported claims. Add citations or remove claims.")
                revised = self.writer.revise_draft(
                    topic=topic,
                    outline=outline,
                    research=research,
                    issues=claim_ledger.get("issues", []),
                    prior_body=draft_obj.body
                )
                if revised:
                    draft_obj = revised
                    sources = self._attach_sources(draft_obj, research)
                    draft_obj.body = self._ensure_sources_section(draft_obj.body, sources, evidence)
                    draft_obj.wordCount = self._compute_word_count(draft_obj.body)
                    claim_ledger = self.claims.build(draft_obj.model_dump(mode="json"), evidence)

            # 3e. Trust layer: Enforce "No Single Point of Truth" principle
            low_confidence_count = claim_ledger.get("metrics", {}).get("low_confidence_count", 0)
            avg_confidence = claim_ledger.get("metrics", {}).get("average_confidence", 0)
            min_confidence = config.get("trust.min_confidence_score", 5.0)
            
            # Log trust metrics for observability
            logger.info("trust_metrics", 
                       claim_count=claim_ledger.get("metrics", {}).get("claim_count", 0),
                       avg_confidence=avg_confidence,
                       low_confidence=low_confidence_count,
                       min_required=min_confidence,
                       miners_used=len(self.miners))
            
            # Check for trust violations
            trust_violation = False
            trust_reasons = []
            
            if low_confidence_count > 0:
                trust_reasons.append(f"{low_confidence_count} claims with single-source or low-credibility evidence")
                if config.get("trust.warn_on_single_source", True):
                    logger.warning("low_confidence_claims_detected", 
                                 count=low_confidence_count,
                                 avg_confidence=avg_confidence,
                                 hint="Claims found with single-source or low-credibility evidence")
                    self._record_hint(f"Found {low_confidence_count} claims with low confidence. Add more sources.")
            
            if avg_confidence < min_confidence and avg_confidence > 0:
                trust_reasons.append(f"Average confidence {avg_confidence:.1f} below threshold {min_confidence}")
                trust_violation = True
            
            # ENFORCEMENT: Block publication if trust policy requires it
            if trust_violation and config.get("trust.block_on_low_confidence", True):
                logger.error("publication_blocked_trust_violation",
                           reasons=trust_reasons,
                           avg_confidence=avg_confidence,
                           low_confidence_count=low_confidence_count,
                           hint="Article blocked due to insufficient source credibility. Add more high-quality sources.")
                self._record_hint("BLOCKED: Article has insufficient source credibility. Add authoritative sources (govt, academic, major news).")
                total_s = round(time.monotonic() - pipeline_start, 2)
                logger.info("pipeline_summary", status="blocked", reason="trust_violation", total_s=total_s, stages=self.stage_timings)
                return None

            # 4. Art Direction (Inject Image)
            try:
                image_url = self.art.get_header_image(draft_obj.title, topic['topic'])
                if image_url:
                    draft_obj.image = ArticleImage(url=image_url, alt=topic['topic'])
            except Exception as e:
                logger.warning("art_direction_failed", error=str(e))
                # Non-critical failure, continue

            # 5. Edit
            review = self.run_stage_with_retry("Review", self.editor.review, draft_obj)
            editor_score = review.get('overall_score', 0)
            # Blend objective score with editor score for stability
            draft_obj.qualityScore = round((draft_obj.qualityScore + editor_score) / 2, 1) if draft_obj.qualityScore else editor_score
            draft_obj.reviewNotes = {
                "review": review,
                "quality": score_result,
                "citations": citation_result,
                "evidence": evidence,
                "claims": claim_ledger
            }
            
            verdict = review.get('verdict', 'REVISE')
            logger.info("stage_complete", stage="Review", score=draft_obj.qualityScore, verdict=verdict)

            if verdict == 'REJECT':
                logger.warning("draft_rejected", reason=review.get('verdict_reason'))
                # In the future, mark as rejected in DB
                self._record_hint("Editor rejected draft. Review editorial notes and revise.")
                total_s = round(time.monotonic() - pipeline_start, 2)
                logger.info("pipeline_summary", status="halted", reason="editor_reject", total_s=total_s, stages=self.stage_timings)
                return None 

            total_s = round(time.monotonic() - pipeline_start, 2)
            logger.info("pipeline_summary", status="success", total_s=total_s, stages=self.stage_timings)
            if self.hints:
                logger.info("troubleshooting_summary", tips=list(dict.fromkeys(self.hints)))
            return draft_obj.model_dump(mode='json')
            
        except Exception as e:
            logger.error(
                "pipeline_failed",
                error=str(e),
                stage=self.current_stage or "unknown",
                stages=self.stage_timings
            )
            if self.hints:
                logger.info("troubleshooting_summary", tips=list(dict.fromkeys(self.hints)))
            return None
    
    def save_draft(self, topic_id: str, draft: Dict) -> Optional[str]:
        try:
            # Create slug
            title = draft.get('title', 'untitled')
            slug = title.lower().replace(' ', '-')
            slug = "".join([c for c in slug if c.isalnum() or c == '-'])
            
            filename = f"{slug[:80]}.json"
            filepath = os.path.join(config.get("paths.drafts_dir", "drafts"), filename)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                # If draft is a dict (from model_dump above), it's already JSON-safe
                # but if passed as Pydantic model, we need to handle it.
                # Since run_pipeline returns dict, we are good.
                json.dump(draft, f, indent=2, ensure_ascii=False)
            
            # Update DB with explicit path and slug
            self.brain.mark_as_drafted(topic_id, slug, filepath, draft)
            
            logger.info("draft_saved", path=filepath)
            return filepath
            
        except Exception as e:
            logger.error("save_failed", error=str(e))
            return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--topic-id', type=str, help="Specific topic ID")
    parser.add_argument('--dry-run', action='store_true', help="Don't save")
    args = parser.parse_args()
    
    # Initialize components (DI Root)
    writer = GhostWriterV2()
    
    topic = writer.brain.get_next_topic_to_write()
    
    if not topic:
        logger.info("no_topics_found")
        return
    
    logger.info("activating_ghostwriter", topic=topic['topic'])
    draft = writer.run_pipeline(topic)
    
    if draft and not args.dry_run:
        writer.save_draft(topic['id'], draft)

if __name__ == "__main__":
    main()
