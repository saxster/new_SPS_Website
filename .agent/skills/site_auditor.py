"""
Site Auditor - Orchestration layer for content quality audits.

Scans all content collections, runs quality validation, and generates reports.
Combines QualityScorer + ConsensusFactChecker with ContentBrain persistence.
"""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from skills.quality_scorer import QualityScorer
from skills.content_brain import ContentBrain


@dataclass
class ContentItem:
    """Represents a parsed content file."""
    id: str
    collection: str
    file_path: str
    title: str
    body: str
    frontmatter: Dict[str, Any]
    content_type: str = "General"
    word_count: int = 0
    sources: List[Dict] = field(default_factory=list)
    regulations: List[str] = field(default_factory=list)


@dataclass
class AuditResult:
    """Result of auditing a single content item."""
    content_id: str
    status: str  # passed, review, failed
    quality_score: float
    fact_check_score: Optional[float] = None
    consensus_level: Optional[str] = None
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendation: str = ""


class SiteAuditor:
    """
    Orchestrates full-site or targeted content audits.
    Combines QualityScorer + ConsensusFactChecker.
    """

    COLLECTIONS = ["blog", "qna", "sectors", "casestudies"]

    def __init__(
        self,
        content_dir: str = "website/src/content",
        db_path: Optional[str] = None
    ):
        self.content_dir = Path(content_dir)
        self.quality_scorer = QualityScorer()
        self.brain = ContentBrain(db_path=db_path) if db_path else ContentBrain()

    def scan_content(self) -> List[ContentItem]:
        """Scan all content collections and return list of items."""
        items = []
        for collection in self.COLLECTIONS:
            collection_path = self.content_dir / collection
            if not collection_path.exists():
                continue

            for md_file in collection_path.glob("*.md"):
                try:
                    item = self._parse_content_file(md_file, collection)
                    if item:
                        items.append(item)
                except Exception as e:
                    # Log and continue on parse errors
                    print(f"Error parsing {md_file}: {e}")

        return items

    def _parse_content_file(self, file_path: Path, collection: str) -> Optional[ContentItem]:
        """Parse a markdown file and extract frontmatter + body."""
        content = file_path.read_text(encoding="utf-8")

        # Split frontmatter from body
        frontmatter = {}
        body = content

        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter_text = parts[1].strip()
                body = parts[2].strip()

                # Parse YAML frontmatter
                frontmatter = self._parse_yaml_frontmatter(frontmatter_text)

        # Extract content ID from filename
        slug = file_path.stem
        content_id = f"{collection}/{slug}"

        # Determine content type
        content_type = (
            frontmatter.get("contentType") or
            frontmatter.get("content_type") or
            frontmatter.get("category") or
            "General"
        )

        # Get title
        title = frontmatter.get("title") or frontmatter.get("question") or slug

        # Count words
        word_count = len(body.split())

        # Extract sources if present
        sources = frontmatter.get("sources", [])

        # Extract regulations if present
        regulations = frontmatter.get("regulations", [])

        return ContentItem(
            id=content_id,
            collection=collection,
            file_path=str(file_path),
            title=title,
            body=body,
            frontmatter=frontmatter,
            content_type=content_type,
            word_count=word_count,
            sources=sources,
            regulations=regulations
        )

    def _parse_yaml_frontmatter(self, text: str) -> Dict[str, Any]:
        """Simple YAML parser for frontmatter."""
        result = {}
        current_key = None
        current_list = None

        for line in text.split("\n"):
            line = line.rstrip()
            if not line:
                continue

            # Check for list item
            if line.startswith("  - ") or line.startswith("- "):
                if current_key and current_list is not None:
                    item = line.lstrip(" -").strip().strip('"').strip("'")
                    current_list.append(item)
                continue

            # Check for key: value
            if ":" in line:
                key, _, value = line.partition(":")
                key = key.strip()
                value = value.strip()

                # Handle arrays
                if value == "" or value.startswith("["):
                    if value.startswith("[") and value.endswith("]"):
                        # Inline array
                        items = value[1:-1].split(",")
                        result[key] = [
                            i.strip().strip('"').strip("'")
                            for i in items if i.strip()
                        ]
                        current_key = None
                        current_list = None
                    else:
                        # Multi-line array
                        current_key = key
                        current_list = []
                        result[key] = current_list
                else:
                    # Simple value
                    result[key] = value.strip('"').strip("'")
                    current_key = None
                    current_list = None

        return result

    def audit_item(self, item: ContentItem) -> AuditResult:
        """Run full audit pipeline on single content item."""
        # Build article dict for QualityScorer
        article = {
            "body": item.body,
            "content_type": item.content_type,
            "contentType": item.content_type,
            "sources": item.sources,
            "regulations": item.regulations
        }

        # Step 1: Quality pre-check
        quality_result = self.quality_scorer.score(article)

        # Determine status based on quality score
        if not quality_result["passes"]:
            status = "failed"
        elif quality_result["score"] >= 85:
            status = "passed"
        else:
            status = "review"

        # Build result
        result = AuditResult(
            content_id=item.id,
            status=status,
            quality_score=quality_result["score"],
            issues=quality_result.get("issues", []),
            warnings=quality_result.get("warnings", []),
            recommendation=quality_result.get("recommendation", "")
        )

        # Record in brain
        self.brain.record_audit(
            content_id=item.id,
            collection=item.collection,
            file_path=item.file_path,
            title=item.title,
            word_count=item.word_count,
            audit_data={
                "quality_score": quality_result["score"],
                "status": status,
                "issues": quality_result.get("issues", [])
            }
        )

        return result

    def audit_collection(self, collection: str) -> List[AuditResult]:
        """Audit all content in a specific collection."""
        items = [i for i in self.scan_content() if i.collection == collection]
        return [self.audit_item(item) for item in items]

    def audit_all(self) -> Dict[str, Any]:
        """Full site audit with report generation."""
        items = self.scan_content()
        results = [self.audit_item(item) for item in items]

        # Calculate summary
        passed = sum(1 for r in results if r.status == "passed")
        failed = sum(1 for r in results if r.status == "failed")
        review = sum(1 for r in results if r.status == "review")

        # Group by collection
        by_collection = {}
        for r in results:
            collection = r.content_id.split("/")[0]
            if collection not in by_collection:
                by_collection[collection] = []
            by_collection[collection].append(r)

        return {
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "review": review,
            "results": results,
            "by_collection": by_collection,
            "timestamp": datetime.now().isoformat()
        }

    def generate_markdown_report(self, report: Dict[str, Any]) -> str:
        """Generate markdown report from audit results."""
        lines = [
            "# Content Audit Report",
            "",
            f"Generated: {report.get('timestamp', datetime.now().isoformat())}",
            "",
            "## Summary",
            "",
            f"| Metric | Count |",
            f"|--------|-------|",
            f"| Total Content | {report['total']} |",
            f"| Passed | {report['passed']} |",
            f"| Needs Review | {report['review']} |",
            f"| Failed | {report['failed']} |",
            "",
        ]

        # By collection
        if report.get("by_collection"):
            lines.extend([
                "## By Collection",
                "",
            ])
            for collection, items in report["by_collection"].items():
                passed = sum(1 for r in items if r.status == "passed")
                lines.append(f"- **{collection}**: {len(items)} items ({passed} passed)")
            lines.append("")

        # Failed items
        failed_results = [r for r in report.get("results", []) if r.status == "failed"]
        if failed_results:
            lines.extend([
                "## Failed Items",
                "",
            ])
            for r in failed_results:
                lines.append(f"### {r.content_id}")
                lines.append(f"- Score: {r.quality_score:.1f}")
                if r.issues:
                    lines.append("- Issues:")
                    for issue in r.issues:
                        lines.append(f"  - {issue}")
                lines.append("")

        # Review items
        review_results = [r for r in report.get("results", []) if r.status == "review"]
        if review_results:
            lines.extend([
                "## Items Needing Review",
                "",
            ])
            for r in review_results:
                lines.append(f"- **{r.content_id}** (Score: {r.quality_score:.1f})")
            lines.append("")

        return "\n".join(lines)

    def save_report(self, report: Dict[str, Any], output_dir: str = "audit_reports") -> str:
        """Save report to file and return path."""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        report_file = output_path / f"audit_{timestamp}.md"

        markdown = self.generate_markdown_report(report)
        report_file.write_text(markdown)

        return str(report_file)
