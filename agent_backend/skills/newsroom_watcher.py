#!/usr/bin/env python3
"""
Newsroom Watcher 🕵️
Monitors the `drafts/` directory and publishes to Astro.
Uses Unified Data Validation and DB-backed state.

Now with Pipeline Profile support:
- Breaking News: Fast-track publishing (< 5 minutes)
- Standard News: Normal council review (~30 minutes)
- Views/Analysis: Deliberate review (~2 hours)
- Research/Guides: Rigorous review (~24 hours)
"""

import os
import sys
import json
import glob
import yaml
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Allow running from repo root without PYTHONPATH
AGENT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if AGENT_ROOT not in sys.path:
    sys.path.insert(0, AGENT_ROOT)

from config.manager import config
from shared.logger import get_logger, setup_logging
from shared.models import ArticleDraft, PipelineProfile, CouncilVerdict
from skills.content_brain import ContentBrain
from skills.quality_scorer import QualityScorer
from skills.fact_check_runner import ConsensusFactChecker
from lib.fact_check.validators import ArticleInput
from skills.citation_validator import CitationValidator
from skills.claim_ledger import ClaimLedger
from skills.publish_policy import PublishPolicy
from skills.pipeline_router import PipelineRouter
from skills.breaking_detector import BreakingDetector
from skills.adversarial_council import AdversarialCouncil

# Initialize Logging
setup_logging()
logger = get_logger("NewsroomWatcher")


class NewsroomWatcher:
    def __init__(self, brain: ContentBrain = None):
        self.drafts_dir = config.get("paths.drafts_dir", "drafts")
        self.output_dir = config.get("paths.output_dir", "output")
        self.metrics_path = config.get(
            "newsroom.metrics_path", "reports/pipeline_metrics.json"
        )
        self.metrics_history = config.get("newsroom.metrics_history", 200)
        self.brain = brain or ContentBrain()
        self.scorer = QualityScorer()
        self.fact_checker = ConsensusFactChecker()
        self.citation_validator = CitationValidator()
        self.claims = ClaimLedger()
        self.policy = PublishPolicy()

        # Pipeline profile components
        self.router = PipelineRouter()
        self.breaking_detector = BreakingDetector()
        self.council = (
            AdversarialCouncil() if config.get("council.enabled", True) else None
        )

        # Ensure directories
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(os.path.join(self.drafts_dir, "failed_quality"), exist_ok=True)
        os.makedirs(os.path.join(self.drafts_dir, "failed_schema"), exist_ok=True)
        os.makedirs(os.path.join(self.drafts_dir, "failed_fact_check"), exist_ok=True)
        os.makedirs(os.path.join(self.drafts_dir, "retry_fact_check"), exist_ok=True)
        os.makedirs(os.path.join(self.drafts_dir, "retry_research"), exist_ok=True)
        os.makedirs(os.path.join(self.drafts_dir, "retry_revision"), exist_ok=True)
        os.makedirs(os.path.join(self.drafts_dir, "hold"), exist_ok=True)
        os.makedirs(os.path.join(self.drafts_dir, "archive"), exist_ok=True)
        os.makedirs(os.path.join(self.drafts_dir, "deliberation"), exist_ok=True)

    def _get_pipeline_profile(
        self, draft: ArticleDraft
    ) -> tuple[PipelineProfile, Dict]:
        """
        Determine the pipeline profile for a draft.

        Returns:
            Tuple of (PipelineProfile, signals dict)
        """
        # Analyze for breaking news signals
        analysis = self.breaking_detector.analyze(draft)

        signals = {
            "urgency": analysis.urgency,
            "is_breaking": analysis.is_breaking,
            "source_tier": analysis.source_tier,
            "confidence": analysis.confidence,
        }

        # Get appropriate profile
        profile = self.router.get_profile(draft, signals)

        logger.info(
            "pipeline_profile_selected",
            title=draft.title[:50],
            profile=profile.name,
            urgency=analysis.urgency,
            is_breaking=analysis.is_breaking,
        )

        return profile, signals

    def _fast_track_publish(
        self,
        draft: ArticleDraft,
        profile: PipelineProfile,
        filename: str,
        filepath: str,
    ) -> Dict:
        """
        Fast-track publish for breaking news from trusted sources.

        Bypasses council review and fact-checking for speed.
        """
        # Add DEVELOPING label if configured
        if profile.label:
            draft.title = f"[{profile.label}] {draft.title}"

        # Calculate correction window
        rollback_hours = profile.rollback.window_hours
        correction_window_expires = datetime.now() + timedelta(hours=rollback_hours)

        # Create minimal verdict for fast-track (auto-approved)
        verdict = CouncilVerdict(
            decision="PUBLISH",
            confidence=0.95,
            advocate_score=90,
            skeptic_score=85,
            guardian_score=85,
            average_score=86.67,
            debate_summary="Fast-tracked: Trusted source, breaking news",
        )

        # Publish to database with pipeline tracking
        slug = filename.replace(".json", "")
        self.brain.publish_article(
            slug,
            draft,
            verdict,
            pipeline_profile=profile.name,
            fast_tracked=True,
            rollback_eligible=True,
            correction_window_expires=correction_window_expires,
        )

        # Also write markdown for SEO
        self._publish_to_markdown(draft, filename)

        # Archive source file
        os.rename(filepath, os.path.join(self.drafts_dir, "archive", filename))

        logger.info(
            "fast_track_published",
            slug=slug,
            profile=profile.name,
            correction_window_hours=rollback_hours,
        )

        return {
            "status": "published",
            "pipeline_profile": profile.name,
            "fast_tracked": True,
            "quality_score": draft.qualityScore,
        }

    def _check_deliberation(
        self,
        draft: ArticleDraft,
        profile: PipelineProfile,
        filename: str,
        filepath: str,
    ) -> Optional[Dict]:
        """
        Check if content needs deliberation delay.

        Returns result dict if held for deliberation, None if ready to proceed.
        """
        if not profile.deliberation or profile.deliberation.min_hours == 0:
            return None

        # Check if draft has a creation timestamp we can use
        # For now, we'll use file modification time as a proxy
        file_mtime = os.path.getmtime(filepath)
        file_age_hours = (datetime.now().timestamp() - file_mtime) / 3600

        if file_age_hours < profile.deliberation.min_hours:
            # Move to deliberation hold
            os.rename(filepath, os.path.join(self.drafts_dir, "deliberation", filename))
            logger.info(
                "held_for_deliberation",
                file=filename,
                profile=profile.name,
                required_hours=profile.deliberation.min_hours,
                current_hours=round(file_age_hours, 2),
            )
            return {
                "status": "held_deliberation",
                "pipeline_profile": profile.name,
                "required_hours": profile.deliberation.min_hours,
            }

        return None

    def scan_and_publish(self, skip_quality=False):
        """Main execution loop."""

        # In a real unified system, we might query the DB for 'DRAFT' items
        # instead of scanning files, but scanning files allows for manual interventions.
        files = glob.glob(os.path.join(self.drafts_dir, "*.json"))
        if not files:
            logger.info("no_drafts_found")
            return

        stats = {
            "run_at": datetime.utcnow().isoformat() + "Z",
            "total": len(files),
            "published": 0,
            "failed_schema": 0,
            "failed_citation": 0,
            "failed_fact_check": 0,
            "retry_fact_check": 0,
            "failed_quality": 0,
            "failed_other": 0,
            "quality_scores": [],
            "consensus_scores": [],
            "citation_density": [],
        }

        for filepath in files:
            try:
                result = self._process_file(filepath, skip_quality)
                status = (result or {}).get("status", "failed_other")
                if status in stats:
                    stats[status] += 1
                else:
                    stats["failed_other"] += 1
                quality = (result or {}).get("quality_score")
                if isinstance(quality, (int, float)):
                    stats["quality_scores"].append(quality)
                consensus = (result or {}).get("consensus_score")
                if isinstance(consensus, (int, float)):
                    stats["consensus_scores"].append(consensus)
                density = (result or {}).get("citation_density")
                if isinstance(density, (int, float)):
                    stats["citation_density"].append(density)
                if (result or {}).get("quality_failed"):
                    stats["failed_quality"] += 1
            except Exception as e:
                logger.error("processing_error", file=filepath, error=str(e))
                stats["failed_other"] += 1

        self._write_metrics(stats)
        logger.info("cycle_complete", stats=stats)

    def _process_file(self, filepath: str, skip_quality: bool):
        filename = os.path.basename(filepath)

        with open(filepath, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        # 1. Validate against Pydantic Model (Strict Schema)
        try:
            draft = ArticleDraft(**raw_data)
        except Exception as e:
            logger.error("validation_failed", file=filename, error=str(e))
            # Move to failed/schema to avoid reprocessing loop
            os.rename(
                filepath, os.path.join(self.drafts_dir, "failed_schema", filename)
            )
            return {"status": "failed_schema"}

        # Normalise word count from body to avoid stale values
        try:
            import re

            draft.wordCount = len(re.findall(r"[A-Za-z0-9']+", draft.body or ""))
        except Exception:
            pass

        # Normalize reviewNotes to dict
        if not isinstance(draft.reviewNotes, dict):
            draft.reviewNotes = {}

        # 1b. Determine pipeline profile
        profile, signals = self._get_pipeline_profile(draft)

        # 1c. Check for fast-track path (breaking news from trusted source)
        if profile.fast_track.enabled:
            return self._fast_track_publish(draft, profile, filename, filepath)

        # 1d. Check for deliberation delay (views, research)
        deliberation_result = self._check_deliberation(
            draft, profile, filename, filepath
        )
        if deliberation_result:
            return deliberation_result

        # Continue with standard processing, but record the profile
        # 2. Objective Quality Check (no publish gating; auto-publish with warnings)
        if not skip_quality:
            quality = self.scorer.score(draft.model_dump(mode="json"))
            draft.qualityScore = quality.get("score", draft.qualityScore)
            review_notes = draft.reviewNotes or {}
            review_notes["quality"] = quality
            draft.reviewNotes = review_notes
            if not quality.get("passes"):
                logger.warning(
                    "quality_gate_failed",
                    file=filename,
                    issues=quality.get("issues", []),
                )
                # Do not block publish but record for metrics
                quality_failed = True
            else:
                quality_failed = False
        else:
            quality_failed = False

        # 2b. Citation validation (hard gate)
        try:
            evidence = (draft.reviewNotes or {}).get("evidence", [])
            if not evidence and draft.sources:
                evidence = []
                for s in draft.sources:
                    url = s.url or ""
                    domain = ""
                    if "://" in url:
                        domain = url.split("://", 1)[1].split("/", 1)[0]
                    evidence.append(
                        {"id": s.id, "title": s.title, "url": url, "domain": domain}
                    )
            citation_result = self.citation_validator.validate(
                draft.model_dump(mode="json"), evidence
            )
            review_notes = draft.reviewNotes or {}
            review_notes["citations"] = citation_result
            draft.reviewNotes = review_notes
            if not citation_result.get("passes"):
                logger.warning(
                    "citation_gate_failed",
                    file=filename,
                    issues=citation_result.get("issues", []),
                )
                target_dir = self._retry_bucket_for_issues(
                    citation_result.get("issues", [])
                )
                os.rename(filepath, os.path.join(self.drafts_dir, target_dir, filename))
                return {
                    "status": "failed_citation",
                    "quality_score": draft.qualityScore,
                    "citation_density": self._citation_density(draft, citation_result),
                }
        except Exception as e:
            logger.error("citation_validation_failed", file=filename, error=str(e))
            os.rename(
                filepath, os.path.join(self.drafts_dir, "failed_fact_check", filename)
            )
            return {"status": "failed_citation"}

        # 2c. Claim ledger validation
        try:
            claim_ledger = self.claims.build(draft.model_dump(mode="json"), evidence)
            review_notes = draft.reviewNotes or {}
            review_notes["claims"] = claim_ledger
            draft.reviewNotes = review_notes
            if claim_ledger.get("issues"):
                logger.warning(
                    "claim_ledger_issues",
                    file=filename,
                    issues=claim_ledger.get("issues", [])[:5],
                )
        except Exception as e:
            logger.error("claim_ledger_failed", file=filename, error=str(e))
            claim_ledger = {}

        # 3. Adversarial consensus review (publish only if passes)
        try:
            summary = draft.body[:4000]
            article_input = ArticleInput(
                article_title=draft.title,
                article_summary=summary,
                proposed_regulations=draft.regulations or [],
                proposed_costs="Not specified",
                topic=draft.category,
            )
            consensus = self.fact_checker.validate(article_input)
            # Merge review notes
            review_notes = draft.reviewNotes or {}
            review_notes["fact_check"] = consensus
            draft.reviewNotes = review_notes
            synthesized = consensus.get("synthesized", {})
            if synthesized.get("factual_errors"):
                logger.warning(
                    "fact_check_errors",
                    file=filename,
                    errors=synthesized.get("factual_errors", []),
                )
            # Consensus gate
            consensus_min = config.get("fact_check.consensus_min", 85)
            consensus_score = consensus.get("consensus", {}).get("score", 0.0)
            consensus_level = consensus.get("consensus", {}).get("level", "")
            if consensus_level in ("skipped", ""):
                logger.warning(
                    "fact_check_skipped",
                    file=filename,
                    reason="no_providers_or_failed_init",
                )
                os.rename(
                    filepath,
                    os.path.join(self.drafts_dir, "failed_fact_check", filename),
                )
                return {
                    "status": "failed_fact_check",
                    "consensus_score": consensus_score,
                }
            if synthesized.get("factual_errors"):
                logger.warning("fact_check_blocked_due_to_errors", file=filename)
                os.rename(
                    filepath,
                    os.path.join(self.drafts_dir, "failed_fact_check", filename),
                )
                return {
                    "status": "failed_fact_check",
                    "consensus_score": consensus_score,
                }
            if consensus_score < consensus_min:
                logger.warning(
                    "fact_check_below_threshold",
                    file=filename,
                    score=consensus_score,
                    min=consensus_min,
                )
                os.rename(
                    filepath,
                    os.path.join(self.drafts_dir, "failed_fact_check", filename),
                )
                return {
                    "status": "failed_fact_check",
                    "consensus_score": consensus_score,
                }
        except Exception as e:
            err = str(e).lower()
            if any(
                k in err
                for k in [
                    "timeout",
                    "timed out",
                    "connection",
                    "service unavailable",
                    "name or service not known",
                    "temporary failure",
                ]
            ):
                logger.error("fact_check_network_issue", file=filename, error=str(e))
                os.rename(
                    filepath,
                    os.path.join(self.drafts_dir, "retry_fact_check", filename),
                )
                return {"status": "retry_fact_check"}
            logger.error("fact_check_failed", file=filename, error=str(e))
            os.rename(
                filepath, os.path.join(self.drafts_dir, "failed_fact_check", filename)
            )
            return {"status": "failed_fact_check"}

        # 3b. Publish policy decision
        citation_density = self._citation_density(draft, citation_result)
        policy = self.policy.evaluate(
            draft=draft.model_dump(mode="json"),
            evidence=evidence,
            fact_check=consensus,
            citation_result=citation_result,
            claim_ledger=claim_ledger,
            citation_density=citation_density,
        )
        review_notes = draft.reviewNotes or {}
        review_notes["policy"] = policy
        draft.reviewNotes = review_notes
        if policy.get("decision") != "publish":
            logger.warning(
                "policy_blocked_publish",
                file=filename,
                reasons=policy.get("reasons", []),
            )
            if policy.get("decision") == "hold":
                dest = self._hold_bucket_for_policy(policy.get("reasons", []))
            else:
                dest = "failed_fact_check"
            os.rename(filepath, os.path.join(self.drafts_dir, dest, filename))
            return {
                "status": "failed_fact_check",
                "consensus_score": consensus_score,
                "citation_density": citation_density,
            }

        # 4. Publish to Markdown
        self._publish_to_markdown(draft, filename)

        # 5. Update DB State with pipeline profile
        slug = filename.replace(".json", "")

        # Create council verdict from consensus data for standard pipeline
        verdict = CouncilVerdict(
            decision="PUBLISH",
            confidence=consensus_score / 100.0 if consensus_score else 0.8,
            advocate_score=int(consensus_score) if consensus_score else 75,
            skeptic_score=int(consensus_score) if consensus_score else 70,
            guardian_score=int(consensus_score) if consensus_score else 72,
            average_score=float(consensus_score) if consensus_score else 72.33,
            debate_summary=f"Standard pipeline: {profile.name}",
        )

        self.brain.publish_article(
            slug,
            draft,
            verdict,
            pipeline_profile=profile.name,
            fast_tracked=False,
            rollback_eligible=False,
        )

        # 6. Archive Source File
        os.rename(filepath, os.path.join(self.drafts_dir, "archive", filename))
        return {
            "status": "published",
            "pipeline_profile": profile.name,
            "quality_score": draft.qualityScore,
            "consensus_score": consensus_score,
            "citation_density": citation_density,
            "quality_failed": quality_failed,
        }

    def _retry_bucket_for_issues(self, issues: List[str]) -> str:
        issue_text = " ".join(issues).lower()
        if (
            "insufficient" in issue_text
            or "no evidence" in issue_text
            or "sources" in issue_text
        ):
            return "retry_research"
        return "retry_revision"

    def _hold_bucket_for_policy(self, reasons: List[str]) -> str:
        reason_text = " ".join(reasons).lower()
        if "insufficient sources" in reason_text or "evidence" in reason_text:
            return "retry_research"
        if "citation" in reason_text or "claim" in reason_text:
            return "retry_revision"
        return "hold"

    def _citation_density(self, draft: ArticleDraft, citation_result: Dict) -> float:
        try:
            body = draft.body or ""
            word_count = max(1, len(body.split()))
            citations = citation_result.get("metrics", {}).get("citation_count", 0)
            return round((citations / word_count) * 1000, 2)
        except Exception:
            return 0.0

    def _write_metrics(self, stats: Dict):
        try:
            os.makedirs(os.path.dirname(self.metrics_path), exist_ok=True)
            history = []
            if os.path.exists(self.metrics_path):
                with open(self.metrics_path, "r", encoding="utf-8") as f:
                    history = json.load(f) or []
            stats["quality_avg"] = (
                round(sum(stats["quality_scores"]) / len(stats["quality_scores"]), 2)
                if stats["quality_scores"]
                else 0.0
            )
            stats["consensus_avg"] = (
                round(
                    sum(stats["consensus_scores"]) / len(stats["consensus_scores"]), 2
                )
                if stats["consensus_scores"]
                else 0.0
            )
            stats["citation_density_avg"] = (
                round(
                    sum(stats["citation_density"]) / len(stats["citation_density"]), 2
                )
                if stats["citation_density"]
                else 0.0
            )
            stats.pop("quality_scores", None)
            stats.pop("consensus_scores", None)
            stats.pop("citation_density", None)
            history.append(stats)
            if len(history) > int(self.metrics_history):
                history = history[-int(self.metrics_history) :]
            with open(self.metrics_path, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            logger.error("metrics_write_failed", error=str(e))

    def _publish_to_markdown(self, draft: ArticleDraft, filename: str):
        # Prepare Frontmatter
        # Convert Pydantic model to dict, exclude body/internal fields
        frontmatter_dict = draft.dict(
            exclude={"body", "reviewNotes", "regulations"}, exclude_none=True
        )

        # Ensure dates are strings for YAML
        if frontmatter_dict.get("pubDate"):
            frontmatter_dict["pubDate"] = frontmatter_dict["pubDate"].isoformat()

        # Dump YAML
        yaml_frontmatter = yaml.dump(
            frontmatter_dict, sort_keys=False, allow_unicode=True
        )

        md_content = f"---\n{yaml_frontmatter}---\n\n{draft.body}\n"

        slug = filename.replace(".json", "")
        output_path = os.path.join(self.output_dir, f"{slug}.md")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        logger.info("published_markdown", path=output_path)


if __name__ == "__main__":
    watcher = NewsroomWatcher()
    watcher.scan_and_publish()
