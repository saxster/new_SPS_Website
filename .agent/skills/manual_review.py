#!/usr/bin/env python3
"""
Manual review tool for fact-check failures.
Allows approve/publish or reject/archive with audit notes.
"""

import os
import sys
import json
import argparse
import re
from datetime import datetime
from typing import Optional, Dict

# Allow running from repo root without PYTHONPATH
AGENT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if AGENT_ROOT not in sys.path:
    sys.path.insert(0, AGENT_ROOT)

from shared.logger import setup_logging, get_logger
from shared.models import ArticleDraft
from skills.newsroom_watcher import NewsroomWatcher

setup_logging()
logger = get_logger("ManualReview")


def _load_draft(path: str) -> Optional[ArticleDraft]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return ArticleDraft(**data)
    except Exception as e:
        logger.error("manual_review_load_failed", file=path, error=str(e))
        return None


def _write_audit(path: str, note: str, reviewer: str, decision: str):
    audit_path = path + ".review.json"
    record = {
        "reviewed_at": datetime.utcnow().isoformat() + "Z",
        "reviewer": reviewer,
        "decision": decision,
        "note": note
    }
    with open(audit_path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)
    _append_audit_log(record)

def _append_audit_log(record: Dict):
    try:
        os.makedirs("reports", exist_ok=True)
        with open("reports/manual_review_audit.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception:
        pass

def _summarise_fact_check(draft: ArticleDraft) -> str:
    notes = draft.reviewNotes or {}
    fc = notes.get("fact_check", {})
    consensus = fc.get("consensus", {})
    synthesized = fc.get("synthesized", {})
    lines = []
    if consensus:
        lines.append(f"Consensus: level={consensus.get('level')} score={consensus.get('score')}")
        lines.append(f"Models: {', '.join(consensus.get('models', []))}")
    if synthesized:
        errs = synthesized.get("factual_errors", [])
        warns = synthesized.get("factual_warnings", [])
        missing = synthesized.get("regulations_missing", [])
        if errs:
            lines.append("Factual errors: " + "; ".join(errs[:5]))
        if warns:
            lines.append("Factual warnings: " + "; ".join(warns[:5]))
        if missing:
            lines.append("Missing regulations: " + "; ".join(missing[:5]))
    return "\n".join(lines) if lines else "No fact-check notes found."

def _excerpt(body: str, max_chars: int = 1200) -> str:
    return (body or "")[:max_chars] + ("..." if body and len(body) > max_chars else "")

def _paginate(text: str, lines_per_page: int = 30):
    lines = (text or "").splitlines()
    if not lines:
        print("(empty)")
        return
    idx = 0
    total = len(lines)
    while idx < total:
        chunk = lines[idx:idx + lines_per_page]
        print("\n".join(chunk))
        idx += lines_per_page
        if idx < total:
            cont = input("\n--More-- (Enter to continue, q to quit): ").strip().lower()
            if cont == "q":
                break

def _show_sources(draft: ArticleDraft):
    if not draft.sources:
        print("No sources listed.")
        return
    print("Sources (clickable):")
    for s in draft.sources:
        print(f"- [{s.id}] {s.title}\n  {s.url}")

def _show_fact_check_json(draft: ArticleDraft):
    notes = draft.reviewNotes or {}
    fc = notes.get("fact_check", {})
    if not fc:
        print("No fact-check notes found.")
        return
    print(json.dumps(fc, indent=2))

def _search_body(draft: ArticleDraft, term: str):
    if not term:
        print("No term provided.")
        return
    lines = (draft.body or "").splitlines()
    matches = [l for l in lines if term.lower() in l.lower()]
    if not matches:
        print("No matches.")
        return
    print("\n".join(matches[:50]))

def _source_map(draft: ArticleDraft):
    return {s.id: s for s in (draft.sources or [])}

def _side_by_side(draft: ArticleDraft):
    src_map = _source_map(draft)
    paragraphs = [p.strip() for p in (draft.body or "").split("\n\n") if p.strip()]
    if not paragraphs:
        print("No body content.")
        return
    for i, para in enumerate(paragraphs, 1):
        citations = re.findall(r"\\[(S\\d+)\\]", para)
        print("\n" + "=" * 80)
        print(f"Paragraph {i}/{len(paragraphs)}")
        print("-" * 80)
        print(para)
        if citations:
            print("\nSources referenced:")
            for cid in sorted(set(citations)):
                s = src_map.get(cid)
                if s:
                    print(f"- [{cid}] {s.title}\n  {s.url}")
                else:
                    print(f"- {cid} (not found in sources list)")
        else:
            print("\nSources referenced: none")
        action = input("Enter to continue, 'q' to quit: ").strip().lower()
        if action == "q":
            break

def interactive_review(drafts_dir: str):
    failed_dir = os.path.join(drafts_dir, "failed_fact_check")
    if not os.path.isdir(failed_dir):
        print("No failed_fact_check directory found.")
        return
    files = [f for f in os.listdir(failed_dir) if f.endswith(".json")]
    if not files:
        print("No failed drafts found.")
        return

    print("Failed drafts:")
    for i, f in enumerate(files, 1):
        print(f"{i}. {f}")
    choice = input("Select a draft number to review: ").strip()
    if not choice.isdigit():
        print("Invalid selection.")
        return
    idx = int(choice) - 1
    if idx < 0 or idx >= len(files):
        print("Selection out of range.")
        return
    filename = files[idx]
    path = os.path.join(failed_dir, filename)
    draft = _load_draft(path)
    if not draft:
        print("Failed to load draft.")
        return

    while True:
        print("\n=== Draft Summary ===")
        print(f"Title: {draft.title}")
        print(f"Description: {draft.description}")
        print(f"Category: {draft.category} | Type: {draft.contentType}")
        print(f"WordCount: {draft.wordCount}")
        print("\n=== Fact Check Summary ===")
        print(_summarise_fact_check(draft))
        print("\nOptions:")
        print("1) Show sources")
        print("2) Show excerpt")
        print("3) Show full body (paged)")
        print("4) Show fact-check JSON")
        print("5) Search in body")
        print("6) Evidence side-by-side")
        print("7) Approve")
        print("8) Reject")
        print("9) Back")
        choice = input("Select: ").strip()

        if choice == "1":
            _show_sources(draft)
        elif choice == "2":
            print(_excerpt(draft.body))
        elif choice == "3":
            _paginate(draft.body)
        elif choice == "4":
            _show_fact_check_json(draft)
        elif choice == "5":
            term = input("Search term: ").strip()
            _search_body(draft, term)
        elif choice == "6":
            _side_by_side(draft)
        elif choice == "7":
            reviewer = input("Reviewer name: ").strip() or "anonymous"
            note = input("Add audit note (optional): ").strip()
            review_file(drafts_dir, filename, "approve", note, reviewer)
            return
        elif choice == "8":
            reviewer = input("Reviewer name: ").strip() or "anonymous"
            note = input("Add audit note (optional): ").strip()
            review_file(drafts_dir, filename, "reject", note, reviewer)
            return
        elif choice == "9":
            print("Back.")
            return
        else:
            print("Invalid choice.")


def list_failed(drafts_dir: str):
    failed_dir = os.path.join(drafts_dir, "failed_fact_check")
    if not os.path.isdir(failed_dir):
        print("No failed_fact_check directory found.")
        return
    files = [f for f in os.listdir(failed_dir) if f.endswith(".json")]
    if not files:
        print("No failed drafts found.")
        return
    for f in files:
        print(f)


def review_file(drafts_dir: str, filename: str, decision: str, note: str, reviewer: str = "anonymous"):
    failed_dir = os.path.join(drafts_dir, "failed_fact_check")
    target = os.path.join(failed_dir, filename)
    if not os.path.exists(target):
        raise SystemExit(f"File not found: {target}")

    draft = _load_draft(target)
    if not draft:
        raise SystemExit("Failed to parse draft.")

    watcher = NewsroomWatcher()

    if decision == "approve":
        # Publish and archive
        watcher._publish_to_markdown(draft, filename)
        watcher.brain.mark_as_published(filename.replace(".json", ""))
        _write_audit(target, note or "Approved by manual review", reviewer, decision)
        os.rename(target, os.path.join(drafts_dir, "archive", filename))
        print("Approved and published.")
        return

    if decision == "reject":
        _write_audit(target, note or "Rejected by manual review", reviewer, decision)
        rejected_dir = os.path.join(drafts_dir, "rejected")
        os.makedirs(rejected_dir, exist_ok=True)
        os.rename(target, os.path.join(rejected_dir, filename))
        print("Rejected and archived.")
        return

    raise SystemExit("Unknown decision. Use approve or reject.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--list", action="store_true", help="List failed drafts")
    parser.add_argument("--file", type=str, help="Filename in drafts/failed_fact_check")
    parser.add_argument("--decision", type=str, choices=["approve", "reject"], help="Decision")
    parser.add_argument("--note", type=str, default="", help="Audit note")
    parser.add_argument("--interactive", action="store_true", help="Interactive review mode")
    parser.add_argument("--drafts-dir", type=str, default="drafts")
    args = parser.parse_args()

    if args.list:
        list_failed(args.drafts_dir)
        return

    if args.file and args.decision:
        review_file(args.drafts_dir, args.file, args.decision, args.note)
        return

    if args.interactive:
        interactive_review(args.drafts_dir)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
