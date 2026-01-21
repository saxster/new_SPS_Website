#!/usr/bin/env python3
"""
Mission Control 🚀
Orchestrates the entire newsroom pipeline in a single Python process.
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

setup_logging()
logger = get_logger("MissionControl")

def run_mission(dry_run=False):
    logger.info("mission_start")
    
    try:
        # 1. CCO Strategy
        logger.info("phase_0_cco")
        cco = ChiefContentOfficer()
        directive = cco.decide_strategy()
        logger.info("cco_directive", directive=directive)

        # 2. Hunt for Topics (if directed)
        if directive.get("action") == "HUNT":
            logger.info("phase_1_topic_hunter")
            hunter = TopicHunter()
            hunter.run(domain="Daily Security Trends India", content_type=directive.get("focus_type", "General"))
        
        # 3. Write Content
        logger.info("phase_2_ghost_writer")
        writer = GhostWriterV2()
        # Loop to process multiple topics? For now just one.
        topic = writer.brain.get_next_topic_to_write()
        if topic:
            draft = writer.run_pipeline(topic)
            if draft and not dry_run:
                writer.save_draft(topic['id'], draft)
        
        # 4. Publish/Deploy
        logger.info("phase_3_watcher")
        watcher = NewsroomWatcher()
        watcher.scan_and_publish() # Ensure Watcher has this
        
    except Exception as e:
        logger.error("mission_critical_failure", error=str(e))
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    
    run_mission(args.dry_run)
