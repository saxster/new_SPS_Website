#!/usr/bin/env python3
"""
Site-wide content audit CLI.

Usage:
    # Audit entire site
    python scripts/audit_site.py --report

    # Audit specific collection
    python scripts/audit_site.py --collection blog --report

    # Audit single piece
    python scripts/audit_site.py --content-id blog/fir-filing-guide-india

    # JSON output for programmatic use
    python scripts/audit_site.py --collection blog --json

    # Find stale content not audited in N days
    python scripts/audit_site.py --stale-days 30
"""

import argparse
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from skills.site_auditor import SiteAuditor, AuditResult


def print_result(result: AuditResult, as_json: bool = False):
    """Print a single audit result."""
    if as_json:
        print(json.dumps({
            "content_id": result.content_id,
            "status": result.status,
            "quality_score": result.quality_score,
            "fact_check_score": result.fact_check_score,
            "consensus_level": result.consensus_level,
            "issues": result.issues,
            "warnings": result.warnings
        }, indent=2))
    else:
        status_icon = {
            "passed": "[PASS]",
            "review": "[REVIEW]",
            "failed": "[FAIL]"
        }.get(result.status, "[?]")

        print(f"{status_icon} {result.content_id}")
        print(f"    Score: {result.quality_score:.1f}")
        if result.issues:
            print("    Issues:")
            for issue in result.issues:
                print(f"      - {issue}")
        if result.warnings:
            print("    Warnings:")
            for warning in result.warnings:
                print(f"      - {warning}")
        print()


def print_summary(results: list, as_json: bool = False):
    """Print summary of audit results."""
    if as_json:
        output = [{
            "content_id": r.content_id,
            "status": r.status,
            "quality_score": r.quality_score,
            "issues": r.issues
        } for r in results]
        print(json.dumps(output, indent=2))
    else:
        passed = sum(1 for r in results if r.status == "passed")
        failed = sum(1 for r in results if r.status == "failed")
        review = sum(1 for r in results if r.status == "review")

        print("=" * 60)
        print("CONTENT AUDIT SUMMARY")
        print("=" * 60)
        print(f"Total:  {len(results)}")
        print(f"Passed: {passed}")
        print(f"Review: {review}")
        print(f"Failed: {failed}")
        print("=" * 60)
        print()

        if failed > 0:
            print("FAILED ITEMS:")
            print("-" * 40)
            for r in results:
                if r.status == "failed":
                    print_result(r)

        if review > 0:
            print("ITEMS NEEDING REVIEW:")
            print("-" * 40)
            for r in results:
                if r.status == "review":
                    print(f"  - {r.content_id} (Score: {r.quality_score:.1f})")
            print()


def main():
    parser = argparse.ArgumentParser(
        description="Audit SPS website content for quality and accuracy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--collection",
        choices=["blog", "qna", "sectors", "casestudies"],
        help="Audit specific collection only"
    )
    parser.add_argument(
        "--content-id",
        help="Audit single content piece (e.g., blog/fir-filing-guide-india)"
    )
    parser.add_argument(
        "--stale-days",
        type=int,
        default=0,
        help="Find content not audited in N days"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate and save markdown report"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )
    parser.add_argument(
        "--content-dir",
        default="../website/src/content",
        help="Path to content directory (default: ../website/src/content)"
    )

    args = parser.parse_args()

    # Resolve content directory relative to script location
    script_dir = Path(__file__).parent
    content_dir = (script_dir / args.content_dir).resolve()

    if not content_dir.exists():
        # Try from .agent directory
        content_dir = (script_dir.parent.parent / "website/src/content").resolve()

    if not content_dir.exists():
        print(f"Error: Content directory not found: {content_dir}", file=sys.stderr)
        sys.exit(1)

    # Resolve database path relative to .agent directory
    db_path = str(script_dir.parent / "content_brain.db")
    auditor = SiteAuditor(content_dir=str(content_dir), db_path=db_path)

    if args.content_id:
        # Audit single item
        items = auditor.scan_content()
        target = [i for i in items if i.id == args.content_id]
        if not target:
            print(f"Error: Content not found: {args.content_id}", file=sys.stderr)
            sys.exit(1)
        result = auditor.audit_item(target[0])
        print_result(result, args.json)

    elif args.stale_days > 0:
        # Find stale content
        stale = auditor.brain.get_stale_audits(days=args.stale_days)
        if args.json:
            print(json.dumps(stale, indent=2, default=str))
        else:
            print(f"Content not audited in {args.stale_days} days:")
            print("-" * 40)
            for item in stale:
                print(f"  - {item['id']} (last: {item.get('last_audited', 'never')})")
            if not stale:
                print("  None found!")

    elif args.collection:
        # Audit collection
        results = auditor.audit_collection(args.collection)
        print_summary(results, args.json)
        if args.report:
            report = {
                "total": len(results),
                "passed": sum(1 for r in results if r.status == "passed"),
                "failed": sum(1 for r in results if r.status == "failed"),
                "review": sum(1 for r in results if r.status == "review"),
                "results": results,
                "by_collection": {args.collection: results}
            }
            report_path = auditor.save_report(report, str(script_dir.parent / "audit_reports"))
            print(f"Report saved: {report_path}")

    else:
        # Full site audit
        report = auditor.audit_all()
        if args.json:
            # Serialize AuditResult objects
            serializable = {
                k: v for k, v in report.items()
                if k not in ["results", "by_collection"]
            }
            serializable["results"] = [{
                "content_id": r.content_id,
                "status": r.status,
                "quality_score": r.quality_score,
                "issues": r.issues
            } for r in report["results"]]
            print(json.dumps(serializable, indent=2))
        else:
            print_summary(report["results"], as_json=False)

        if args.report:
            report_path = auditor.save_report(report, str(script_dir.parent / "audit_reports"))
            print(f"Report saved: {report_path}")


if __name__ == "__main__":
    main()
