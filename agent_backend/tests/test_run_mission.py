"""
Tests for run_mission.py with pillar filtering support.

TDD: These tests define the expected behavior before implementation.
"""

import pytest
from unittest.mock import patch, MagicMock
import sys
import os
import argparse

# Add root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Mock heavy dependencies before importing run_mission
sys.modules["openai"] = MagicMock()
sys.modules["chromadb"] = MagicMock()
sys.modules["chromadb.utils"] = MagicMock()
sys.modules["chromadb.utils.embedding_functions"] = MagicMock()


class TestRunMissionArgParser:
    """Tests for run_mission.py command-line argument parsing."""

    def test_accepts_pillars_argument(self):
        """run_mission should accept --pillars argument."""
        from skills.run_mission import create_parser

        parser = create_parser()
        args = parser.parse_args(["--pillars", "scam_watch,economic_security"])

        assert args.pillars == "scam_watch,economic_security"

    def test_accepts_max_articles_argument(self):
        """run_mission should accept --max-articles argument."""
        from skills.run_mission import create_parser

        parser = create_parser()
        args = parser.parse_args(["--max-articles", "5"])

        assert args.max_articles == 5

    def test_pillars_optional(self):
        """--pillars should be optional."""
        from skills.run_mission import create_parser

        parser = create_parser()
        args = parser.parse_args([])

        assert args.pillars is None

    def test_max_articles_default(self):
        """--max-articles should default to 3."""
        from skills.run_mission import create_parser

        parser = create_parser()
        args = parser.parse_args([])

        assert args.max_articles == 3


class TestRunMissionPillarFiltering:
    """Tests for pillar filtering in run_mission."""

    def test_sources_by_pillar_when_pillars_specified(self):
        """run_mission should source topics by pillar when --pillars is specified."""
        with (
            patch("skills.run_mission.TopicSourcer") as mock_sourcer,
            patch("skills.run_mission.EditorialBrainV2") as mock_brain,
            patch("skills.run_mission.GhostWriterV2") as mock_writer,
            patch("skills.run_mission.NewsroomWatcher") as mock_watcher,
            patch("skills.run_mission.TopicHunter") as mock_hunter,
            patch("skills.run_mission.ChiefContentOfficer") as mock_cco,
        ):
            from skills.run_mission import run_mission

            # Setup mocks
            mock_sourcer_instance = MagicMock()
            mock_sourcer.return_value = mock_sourcer_instance
            mock_sourcer_instance.source_topics.return_value = []

            mock_brain_instance = MagicMock()
            mock_brain.return_value = mock_brain_instance
            mock_brain_instance.analyze_landscape.return_value = MagicMock(
                action="WRITE",
                focus_type="scam",
                focus_topic=None,
                reason="test",
                urgency="high",
            )

            mock_writer_instance = MagicMock()
            mock_writer.return_value = mock_writer_instance
            mock_writer_instance.brain.get_next_topic_to_write.return_value = None

            mock_watcher_instance = MagicMock()
            mock_watcher.return_value = mock_watcher_instance

            # Run with pillars
            run_mission(pillars=["scam_watch"], max_articles=1)

            # Verify source_topics was called with pillar filtering
            mock_sourcer_instance.source_topics.assert_called()
            call_args = mock_sourcer_instance.source_topics.call_args
            # Should use by_pillar strategy with the pillar argument
            assert call_args[1].get("strategy") == "by_pillar"
            assert call_args[1].get("pillar") == "scam_watch"

    def test_uses_all_strategy_when_no_pillars(self):
        """run_mission should use 'all' strategy when no pillars specified."""
        with (
            patch("skills.run_mission.TopicSourcer") as mock_sourcer,
            patch("skills.run_mission.EditorialBrainV2") as mock_brain,
            patch("skills.run_mission.GhostWriterV2") as mock_writer,
            patch("skills.run_mission.NewsroomWatcher") as mock_watcher,
            patch("skills.run_mission.TopicHunter") as mock_hunter,
            patch("skills.run_mission.ChiefContentOfficer") as mock_cco,
        ):
            from skills.run_mission import run_mission

            # Setup mocks
            mock_sourcer_instance = MagicMock()
            mock_sourcer.return_value = mock_sourcer_instance
            mock_sourcer_instance.source_topics.return_value = []

            mock_brain_instance = MagicMock()
            mock_brain.return_value = mock_brain_instance
            mock_brain_instance.analyze_landscape.return_value = MagicMock(
                action="WRITE",
                focus_type=None,
                focus_topic=None,
                reason="test",
                urgency="medium",
            )

            mock_writer_instance = MagicMock()
            mock_writer.return_value = mock_writer_instance
            mock_writer_instance.brain.get_next_topic_to_write.return_value = None

            mock_watcher_instance = MagicMock()
            mock_watcher.return_value = mock_watcher_instance

            # Run without pillars
            run_mission()

            # Verify source_topics was called with 'all' strategy
            mock_sourcer_instance.source_topics.assert_called()
            call_args = mock_sourcer_instance.source_topics.call_args
            assert call_args[1].get("strategy") == "all"


class TestParsePillarsHelper:
    """Tests for the parse_pillars helper function."""

    def test_parse_pillars_from_comma_separated_string(self):
        """parse_pillars should split comma-separated string."""
        from skills.run_mission import parse_pillars

        result = parse_pillars("scam_watch,economic_security,personal_security")

        assert result == ["scam_watch", "economic_security", "personal_security"]

    def test_parse_pillars_returns_none_for_empty_string(self):
        """parse_pillars should return None for empty string."""
        from skills.run_mission import parse_pillars

        result = parse_pillars("")

        assert result is None

    def test_parse_pillars_returns_none_for_none(self):
        """parse_pillars should return None for None input."""
        from skills.run_mission import parse_pillars

        result = parse_pillars(None)

        assert result is None

    def test_parse_pillars_strips_whitespace(self):
        """parse_pillars should strip whitespace from pillar names."""
        from skills.run_mission import parse_pillars

        result = parse_pillars("scam_watch , economic_security")

        assert result == ["scam_watch", "economic_security"]
