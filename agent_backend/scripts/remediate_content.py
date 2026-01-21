#!/usr/bin/env python3
"""
Content Remediation Script 🛠️
Automatically rewrites content that failed the audit to meet 'World Class' standards.
"""

import sys
import os
import logging
from typing import List

# Allow running from repo root without PYTHONPATH
AGENT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if AGENT_ROOT not in sys.path:
    sys.path.insert(0, AGENT_ROOT)

from skills.site_auditor import SiteAuditor, ContentItem
from skills.ghost_writer import GhostWriterV2
from skills.newsroom_watcher import NewsroomWatcher
from shared.logger import setup_logging

setup_logging()
logger = logging.getLogger("Remediator")

def remap_collection_to_type(collection: str) -> str:
    """Map file collection to Content Type for GhostWriter."""
    mapping = {
        "blog": "Guide",  # Blogs should be deep guides
        "qna": "Guide",   # Q&A should be authoritative guides
        "sectors": "Analysis", # Sector pages are deep analysis
        "casestudies": "CaseStudy"
    }
    return mapping.get(collection, "General")

def main():
    logger.info("Starting Content Remediation...")
    
    # 1. Audit to find targets
    auditor = SiteAuditor()
    items = auditor.scan_content()
    
    # Filter for failed items (in this case, we know they all failed, so we take all)
    # But strictly, we should audit them first or just take the list.
    # We will process ALL scanned items to ensure complete coverage.
    
    logger.info(f"Found {len(items)} items to remediate.")
    
    writer = GhostWriterV2()
    watcher = NewsroomWatcher()
    
    processed_count = 0
    
    for item in items:
        try:
            logger.info(f"Remediating: {item.id} ({item.title})")
            
            # Construct Topic with "World Class" constraints
            # We append context to the topic string for the Researcher, 
            # but we might want to keep the original title for the file.
            
            content_type = remap_collection_to_type(item.collection)
            
            topic = {
                "id": item.id, # Use existing ID to ensure overwrite
                "topic": item.title,
                "content_type": content_type,
                "target_audience": "Security Professionals, CSOs, and Facility Managers in India",
                "gap_score": 100, # Max priority
                "extra_context": "MUST include PSARA 2005, BNS 2023, and IS Standards. Deep technical detail required."
            }
            
            # Run Pipeline
            # The GhostWriter will research, outline, write, and critique itself.
            draft = writer.run_pipeline(topic)
            
            if draft:
                # Save draft
                writer.save_draft(topic['id'], draft)
                processed_count += 1
                logger.info(f"Draft saved for {item.id}")
            else:
                logger.error(f"Failed to generate draft for {item.id}")
                
        except Exception as e:
            logger.error(f"Error processing {item.id}: {e}")
            
    logger.info(f"Remediation generation complete. Generated {processed_count}/{len(items)} drafts.")
    
    if processed_count > 0:
        logger.info("Publishing drafts to website...")
        watcher.scan_and_publish(skip_quality=False) # Enforce quality gates during publish too
        logger.info("Publishing complete.")

if __name__ == "__main__":
    main()
