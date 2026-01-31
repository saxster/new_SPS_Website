#!/usr/bin/env python3
"""
Mission Control 🚀
Orchestrates the entire newsroom pipeline in a single Python process.

Now with:
- Editorial Brain v2 (LLM-powered editorial judgment)
- Adversarial Council integration
- Auto-publish pipeline
- Pillar-based content filtering
"""

import sys
import os
import argparse
from typing import List, Optional

# Allow running from repo root without PYTHONPATH
AGENT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if AGENT_ROOT not in sys.path:
    sys.path.insert(0, AGENT_ROOT)

from config.manager import config
from shared.logger import setup_logging, get_logger

# Import Skills
from skills.topic_hunter import TopicHunter
from skills.ghost_writer import GhostWriterV2
from skills.newsroom_watcher import NewsroomWatcher
from skills.chief_content_officer import ChiefContentOfficer

# New v2 components
from skills.editorial_brain import EditorialBrainV2
from skills.topic_sourcer import TopicSourcer

setup_logging()
logger = get_logger("MissionControl")


def parse_pillars(pillars_str: Optional[str]) -> Optional[List[str]]:
    """
    Parse comma-separated pillar string into list.

    Args:
        pillars_str: Comma-separated pillar names (e.g., "scam_watch,economic_security")

    Returns:
        List of pillar names, or None if input is empty/None
    """
    if not pillars_str:
        return None
    pillars = [p.strip() for p in pillars_str.split(",") if p.strip()]
    return pillars if pillars else None


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for run_mission command."""
    parser = argparse.ArgumentParser(description="Run the autonomous newsroom mission")
    parser.add_argument(
        "--dry-run", action="store_true", help="Run without saving drafts"
    )
    parser.add_argument(
        "--legacy-cco",
        action="store_true",
        help="Use legacy CCO instead of Editorial Brain v2",
    )
    parser.add_argument(
        "--pillars",
        type=str,
        default=None,
        help="Comma-separated list of content pillars to focus on (e.g., scam_watch,economic_security)",
    )
    parser.add_argument(
        "--max-articles",
        type=int,
        default=3,
        help="Maximum number of articles to generate (default: 3)",
    )
    return parser


def run_mission(
    dry_run: bool = False,
    use_editorial_brain: bool = True,
    pillars: Optional[List[str]] = None,
    max_articles: int = 3,
):
    """
    Run the autonomous newsroom mission.

    Args:
        dry_run: If True, don't save drafts
        use_editorial_brain: If True, use Editorial Brain v2 instead of legacy CCO
        pillars: List of content pillars to focus on (e.g., ["scam_watch", "economic_security"])
        max_articles: Maximum number of articles to generate
    """
    logger.info(
        "mission_start",
        version="v2",
        pillars=pillars,
        max_articles=max_articles,
    )

    try:
        # Phase -1: Topic Sourcing (proactive content discovery)
        if config.get("topic_sourcer.enabled", True):
            logger.info("phase_sourcing_start", pillars=pillars)
            try:
                sourcer = TopicSourcer()

                # Use pillar-specific sourcing if pillars specified
                if pillars:
                    # Source topics for each specified pillar
                    sourced_topics = []
                    for pillar in pillars:
                        pillar_topics = sourcer.source_topics(
                            strategy="by_pillar", pillar=pillar
                        )
                        sourced_topics.extend(pillar_topics)
                    # Remove duplicates while preserving order
                    seen = set()
                    unique_topics = []
                    for t in sourced_topics:
                        if t.id not in seen:
                            seen.add(t.id)
                            unique_topics.append(t)
                    sourced_topics = unique_topics
                else:
                    # Use all strategies
                    sourced_topics = sourcer.source_topics(strategy="all")

                logger.info(
                    "phase_sourcing_complete",
                    topics_found=len(sourced_topics),
                    top_sources=[t.source_type for t in sourced_topics[:5]],
                )
            except Exception as e:
                logger.warning("phase_sourcing_error", error=str(e))
                sourced_topics = []

        # Phase 0: Strategic Direction
        if use_editorial_brain and config.get("editorial_brain.enabled", True):
            logger.info("phase_0_editorial_brain")
            brain = EditorialBrainV2()
            directive = brain.analyze_landscape()
            logger.info(
                "editorial_directive",
                action=directive.action,
                urgency=directive.urgency,
            )

            # Map EditorialDirective actions to legacy format
            if directive.action in ["HUNT_BREAKING", "HUNT_TRENDING", "HUNT_GAP"]:
                action = "HUNT"
            elif directive.action == "WRITE_PRIORITY":
                action = "WRITE"  # Priority write from sourced topics
            else:
                action = "WRITE"

            legacy_directive = {
                "action": action,
                "focus_type": directive.focus_type or "General",
                "focus_topic": directive.focus_topic,
                "reason": directive.reason,
            }
        else:
            # Fallback to legacy CCO
            logger.info("phase_0_cco")
            cco = ChiefContentOfficer()
            legacy_directive = cco.decide_strategy()
            logger.info("cco_directive", directive=legacy_directive)

        # Phase 1: Hunt for Topics (if directed)
        if legacy_directive.get("action") == "HUNT":
            logger.info("phase_1_topic_hunter")
            hunter = TopicHunter()
            hunter.run(
                domain="Daily Security Trends India",
                content_type=legacy_directive.get("focus_type", "General"),
            )

        # Phase 2: Write Content (limited by max_articles)
        logger.info("phase_2_ghost_writer", max_articles=max_articles)
        writer = GhostWriterV2()
        articles_written = 0

        while articles_written < max_articles:
            topic = writer.brain.get_next_topic_to_write()
            if not topic:
                logger.info("no_more_topics_to_write")
                break

            draft = writer.run_pipeline(topic)
            if draft and not dry_run:
                writer.save_draft(topic["id"], draft)
                articles_written += 1
            elif not draft:
                # Failed to generate draft, continue to next topic
                continue

        logger.info("phase_2_complete", articles_written=articles_written)

        # Phase 3: Publish/Deploy (with Council integration)
        logger.info("phase_3_watcher")
        watcher = NewsroomWatcher()
        watcher.scan_and_publish()

        logger.info("mission_complete", articles_written=articles_written)

    except Exception as e:
        logger.error("mission_critical_failure", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    parser = create_parser()
    args = parser.parse_args()

    # Parse pillars from comma-separated string
    pillars_list = parse_pillars(args.pillars)

    run_mission(
        dry_run=args.dry_run,
        use_editorial_brain=not args.legacy_cco,
        pillars=pillars_list,
        max_articles=args.max_articles,
    )
