#!/usr/bin/env python3
"""
Update watcher.
Checks published content for stale age or broken sources, and queues refresh.
"""

import os
import sys
import re
import json
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

import yaml
import requests

# Allow running from repo root without PYTHONPATH
AGENT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if AGENT_ROOT not in sys.path:
    sys.path.insert(0, AGENT_ROOT)

from config.manager import config
from shared.logger import get_logger, setup_logging

setup_logging()
logger = get_logger("UpdateWatcher")


def _parse_markdown(path: str) -> Tuple[Dict, str]:
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            fm = yaml.safe_load(parts[1]) or {}
            body = parts[2].lstrip()
            return fm, body
    return {}, text


def _extract_sources(body: str) -> List[str]:
    sources = []
    if "## Sources" not in body:
        return sources
    section = body.split("## Sources", 1)[1]
    for line in section.splitlines():
        match = re.search(r"(https?://\\S+)", line)
        if match:
            sources.append(match.group(1).rstrip(")"))
    return sources


def _check_url(url: str, timeout: int = 10) -> Optional[int]:
    try:
        resp = requests.head(url, timeout=timeout, allow_redirects=True)
        if resp.status_code >= 400:
            resp = requests.get(url, timeout=timeout, allow_redirects=True)
        return resp.status_code
    except Exception:
        return None


def run():
    content_dir = config.get("paths.output_dir", "website/src/content/blog")
    report_path = config.get("updates.report_path", "reports/update_watch.json")
    queue_dir = config.get("updates.queue_dir", "drafts/refresh_needed")
    queue_on_flag = config.get("updates.queue_on_flag", True)
    max_age_default = config.get("updates.max_age_days", 365)
    max_age_by_type = config.get("updates.max_age_days_by_type", {})

    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    if queue_on_flag:
        os.makedirs(queue_dir, exist_ok=True)

    results = []
    if not os.path.isdir(content_dir):
        logger.warning("content_dir_missing", path=content_dir)
        return

    for fname in os.listdir(content_dir):
        if not fname.endswith(".md"):
            continue
        path = os.path.join(content_dir, fname)
        frontmatter, body = _parse_markdown(path)
        reasons = []

        content_type = frontmatter.get("contentType") or frontmatter.get("content_type") or frontmatter.get("category")
        pub_date = frontmatter.get("pubDate")
        if pub_date:
            try:
                dt = datetime.fromisoformat(pub_date.replace("Z", ""))
                max_age = int(max_age_by_type.get(content_type, max_age_default))
                if dt < datetime.utcnow() - timedelta(days=max_age):
                    reasons.append(f"Article older than {max_age} days for type {content_type}.")
            except Exception:
                reasons.append("Unable to parse publication date.")

        sources = _extract_sources(body)
        broken = []
        for url in sources:
            status = _check_url(url)
            if status is None or status >= 400:
                broken.append({"url": url, "status": status})
        if broken:
            reasons.append("One or more sources appear broken.")

        if reasons:
            entry = {
                "file": path,
                "title": frontmatter.get("title"),
                "content_type": content_type,
                "reasons": reasons,
                "broken_sources": broken
            }
            results.append(entry)
            if queue_on_flag:
                queue_path = os.path.join(queue_dir, os.path.basename(path) + ".json")
                with open(queue_path, "w", encoding="utf-8") as f:
                    json.dump(entry, f, indent=2)

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    logger.info("update_watch_complete", flagged=len(results), report=report_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true", help="Run update watcher")
    args = parser.parse_args()
    if args.run:
        run()
