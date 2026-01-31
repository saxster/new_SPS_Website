#!/usr/bin/env python3
"""
Mission Control 🚀
Orchestrates the entire newsroom pipeline in a single Python process.

Now with:
- Editorial Brain v2 (LLM-powered editorial judgment)
- Adversarial Council integration
- Auto-publish pipeline
"""

import sys
import os
import argparse

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


def run_mission(dry_run=False, use_editorial_brain=True):
    logger.info("mission_start", version="v2")

    try:
        # Phase -1: Topic Sourcing (proactive content discovery)
        if config.get("topic_sourcer.enabled", True):
            logger.info("phase_sourcing_start")
            try:
                sourcer = TopicSourcer()
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

        # Phase 2: Write Content
        logger.info("phase_2_ghost_writer")
        writer = GhostWriterV2()
        topic = writer.brain.get_next_topic_to_write()
        if topic:
            draft = writer.run_pipeline(topic)
            if draft and not dry_run:
                writer.save_draft(topic["id"], draft)

        # Phase 3: Publish/Deploy (with Council integration)
        logger.info("phase_3_watcher")
        watcher = NewsroomWatcher()
        watcher.scan_and_publish()

        logger.info("mission_complete")

    except Exception as e:
        logger.error("mission_critical_failure", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the autonomous newsroom mission")
    parser.add_argument(
        "--dry-run", action="store_true", help="Run without saving drafts"
    )
    parser.add_argument(
        "--legacy-cco",
        action="store_true",
        help="Use legacy CCO instead of Editorial Brain v2",
    )
    args = parser.parse_args()

    run_mission(dry_run=args.dry_run, use_editorial_brain=not args.legacy_cco)
