"""
Tests for notification_services.py

Tests verify:
1. HTML email template renders with correct content
2. Template is loaded from external file (code hygiene)
3. Severity colors are applied correctly
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest


class TestRenderAlertEmail:
    """Test the render_alert_email function."""

    def test_renders_title_and_description(self):
        """Should include title and description in output."""
        from skills.notification_services import render_alert_email

        html = render_alert_email(
            title="Security Breach Detected",
            sector="Financial",
            severity="high",
            description="Unauthorized access detected in the system."
        )

        assert "Security Breach Detected" in html
        assert "Unauthorized access detected in the system." in html
        assert "Financial" in html

    def test_renders_severity_badge(self):
        """Should render severity as uppercase badge."""
        from skills.notification_services import render_alert_email

        html = render_alert_email(
            title="Test Alert",
            sector="Test",
            severity="critical",
            description="Test description"
        )

        assert "CRITICAL ALERT" in html

    def test_applies_correct_severity_color(self):
        """Should apply correct color for each severity level."""
        from skills.notification_services import render_alert_email

        test_cases = [
            ("low", "#3B82F6"),
            ("medium", "#F59E0B"),
            ("high", "#EF4444"),
            ("critical", "#7C3AED"),
        ]

        for severity, expected_color in test_cases:
            html = render_alert_email(
                title="Test",
                sector="Test",
                severity=severity,
                description="Test"
            )
            assert expected_color in html, f"Expected {expected_color} for {severity} severity"

    def test_includes_action_url(self):
        """Should include custom action URL when provided."""
        from skills.notification_services import render_alert_email

        custom_url = "https://example.com/custom-action"
        html = render_alert_email(
            title="Test",
            sector="Test",
            severity="low",
            description="Test",
            action_url=custom_url
        )

        assert custom_url in html

    def test_uses_default_action_url(self):
        """Should use default action URL when not provided."""
        from skills.notification_services import render_alert_email

        html = render_alert_email(
            title="Test",
            sector="Test",
            severity="low",
            description="Test"
        )

        assert "https://sps-security.com/intelligence" in html


class TestEmailTemplateHygiene:
    """Test that email template follows code hygiene practices."""

    def test_template_file_exists(self):
        """Template should be loaded from external file."""
        template_path = Path(__file__).parent.parent / "skills" / "templates" / "alert_email.html"
        assert template_path.exists(), (
            f"Template file not found at {template_path}. "
            "HTML templates should be externalized for maintainability."
        )

    def test_template_file_contains_placeholders(self):
        """Template file should contain format placeholders."""
        template_path = Path(__file__).parent.parent / "skills" / "templates" / "alert_email.html"

        if not template_path.exists():
            pytest.skip("Template file not yet created")

        content = template_path.read_text()

        # Should have placeholders for dynamic content
        assert "{title}" in content or "{{title}}" in content
        assert "{sector}" in content or "{{sector}}" in content
        assert "{severity_upper}" in content or "{{severity_upper}}" in content or "{severity}" in content
        assert "{description}" in content or "{{description}}" in content

    def test_function_does_not_have_inline_html(self):
        """The render_alert_email function should not have inline HTML."""
        import inspect
        from skills.notification_services import render_alert_email

        source = inspect.getsource(render_alert_email)

        # Should not have large HTML blocks inline
        assert '<!DOCTYPE html>' not in source, (
            "render_alert_email should load HTML from template file, not have it inline"
        )
        assert '<html>' not in source, (
            "render_alert_email should load HTML from template file, not have it inline"
        )
