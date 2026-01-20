"""
Tests for SiteAuditor - the orchestration layer for content quality audits.
"""

import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from skills.site_auditor import SiteAuditor, ContentItem, AuditResult


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database file."""
    return str(tmp_path / "test_brain.db")


class TestContentItemParsing:
    """Tests for parsing markdown content files."""

    def test_parse_blog_markdown(self, tmp_path, temp_db):
        """Test parsing a blog markdown file with frontmatter."""
        blog_dir = tmp_path / "blog"
        blog_dir.mkdir()

        md_content = """---
title: "Test CCTV Guide"
description: "A comprehensive guide to CCTV systems"
pubDate: 2025-01-15
author: "SPS Team"
category: "Security"
contentType: "Guide"
tags: ["cctv", "surveillance"]
---

## Introduction

This is a test article about CCTV systems in India.

## DPDP Act Compliance

According to the Digital Personal Data Protection Act 2023...

## RBI Guidelines

The Reserve Bank of India mandates...

## Conclusion

Security is important.
"""
        (blog_dir / "test-cctv-guide.md").write_text(md_content)

        auditor = SiteAuditor(content_dir=str(tmp_path), db_path=temp_db)
        items = auditor.scan_content()

        assert len(items) == 1
        item = items[0]
        assert item.id == "blog/test-cctv-guide"
        assert item.collection == "blog"
        assert item.title == "Test CCTV Guide"
        assert item.content_type == "Guide"
        assert "CCTV" in item.body
        assert "DPDP Act" in item.body

    def test_parse_qna_markdown(self, tmp_path, temp_db):
        """Test parsing a Q&A markdown file."""
        qna_dir = tmp_path / "qna"
        qna_dir.mkdir()

        md_content = """---
question: "How do I file an FIR?"
author: "Security Manager"
role: "Plant Manager"
sector: "Manufacturing"
date: 2025-01-10
answer: "Visit your local police station with relevant documents."
answeredBy: "SPS Legal Team"
tags: ["legal", "fir"]
---

## Additional Details

More information about FIR filing under BNSS...
"""
        (qna_dir / "fir-filing.md").write_text(md_content)

        auditor = SiteAuditor(content_dir=str(tmp_path), db_path=temp_db)
        items = auditor.scan_content()

        assert len(items) == 1
        item = items[0]
        assert item.id == "qna/fir-filing"
        assert item.collection == "qna"


class TestAuditItem:
    """Tests for auditing individual content items."""

    def test_audit_passing_content(self, tmp_path, temp_db):
        """Test auditing content that passes quality checks."""
        blog_dir = tmp_path / "blog"
        blog_dir.mkdir()

        # Create content that meets Guide thresholds
        # Guide requires: 1500 words, 5 sections, 5 sources, 2 regulations
        body_sections = """
## Introduction

This comprehensive guide explains security camera installation in India.
According to DSCI Report 2024, surveillance spending increased 45% [DSCI-2024].

## Legal Framework

The DPDP Act 2023 mandates data protection compliance. The IT Act 2000
Section 43A requires reasonable security practices [IT-ACT-001].

## RBI Guidelines

The Reserve Bank of India cyber security framework outlines specific
requirements for financial institutions [RBI-2024].

## PSARA Compliance

The Private Security Agencies Regulation Act governs security agencies.
State-level PSARA rules vary significantly [PSARA-2024].

## Technical Standards

NBC 2016 (National Building Code) specifies fire safety requirements.
CERT-In provides cybersecurity guidelines [NBC-2016].

## Implementation Steps

Organisations should implement surveillance according to industry best
practices outlined by NASSCOM [NASSCOM-2024].

## Case Study

A major bank implemented zero-trust architecture per MeitY guidelines.
The Ministry of Home Affairs recommends such approaches [MHA-2024].

## Conclusion

Security implementation requires understanding multiple regulatory frameworks
including NDMA disaster management guidelines [NDMA-2024].
"""
        # Repeat to meet word count (body_sections is ~150 words, need 1500+)
        body = body_sections * 12

        md_content = f"""---
title: "Comprehensive CCTV Installation Guide for India"
description: "A complete guide to installing CCTV systems in compliance with Indian regulations"
pubDate: 2025-01-15
author: "SPS Team"
category: "Security"
contentType: "Guide"
tags: ["cctv", "surveillance", "compliance"]
---

{body}
"""
        (blog_dir / "cctv-guide.md").write_text(md_content)

        auditor = SiteAuditor(content_dir=str(tmp_path), db_path=temp_db)
        items = auditor.scan_content()
        result = auditor.audit_item(items[0])

        assert result.status in ["passed", "review"]
        assert result.quality_score > 50

    def test_audit_failing_content(self, tmp_path, temp_db):
        """Test auditing content that fails quality checks."""
        blog_dir = tmp_path / "blog"
        blog_dir.mkdir()

        # Create content that fails Guide thresholds (too short)
        md_content = """---
title: "Short Article"
description: "A short article"
pubDate: 2025-01-15
contentType: "Guide"
---

## Introduction

This is too short.

## Conclusion

The end.
"""
        (blog_dir / "short-article.md").write_text(md_content)

        auditor = SiteAuditor(content_dir=str(tmp_path), db_path=temp_db)
        items = auditor.scan_content()
        result = auditor.audit_item(items[0])

        assert result.status == "failed"
        assert len(result.issues) > 0


class TestAuditCollection:
    """Tests for auditing entire collections."""

    def test_audit_blog_collection(self, tmp_path, temp_db):
        """Test auditing all items in a collection."""
        blog_dir = tmp_path / "blog"
        blog_dir.mkdir()

        # Create multiple articles
        for i in range(3):
            md_content = f"""---
title: "Article {i}"
contentType: "News"
---

## Section 1

Content for article {i}. This is a test.
"""
            (blog_dir / f"article-{i}.md").write_text(md_content)

        auditor = SiteAuditor(content_dir=str(tmp_path), db_path=temp_db)
        results = auditor.audit_collection("blog")

        assert len(results) == 3
        assert all(isinstance(r, AuditResult) for r in results)


class TestAuditReport:
    """Tests for report generation."""

    def test_generate_report(self, tmp_path, temp_db):
        """Test generating an audit report."""
        blog_dir = tmp_path / "blog"
        blog_dir.mkdir()

        md_content = """---
title: "Test Article"
contentType: "News"
---

## Test

Content here.
"""
        (blog_dir / "test.md").write_text(md_content)

        auditor = SiteAuditor(content_dir=str(tmp_path), db_path=temp_db)
        report = auditor.audit_all()

        assert "total" in report
        assert "passed" in report
        assert "failed" in report
        assert "results" in report

    def test_report_markdown_output(self, tmp_path, temp_db):
        """Test generating markdown report output."""
        blog_dir = tmp_path / "blog"
        blog_dir.mkdir()

        md_content = """---
title: "Test Article"
contentType: "News"
---

## Test

Content here.
"""
        (blog_dir / "test.md").write_text(md_content)

        auditor = SiteAuditor(content_dir=str(tmp_path), db_path=temp_db)
        report = auditor.audit_all()
        markdown = auditor.generate_markdown_report(report)

        assert "# Content Audit Report" in markdown
        assert "Summary" in markdown
