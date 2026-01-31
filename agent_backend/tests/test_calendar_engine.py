"""
Tests for CalendarEngine.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import date, datetime, timedelta

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestCalendarEngine:
    """Tests for CalendarEngine class."""

    @pytest.fixture
    def engine(self):
        """Create CalendarEngine instance."""
        from skills.calendar_engine import CalendarEngine

        return CalendarEngine()

    def test_events_loaded(self, engine):
        """Test that events are loaded on initialization."""
        assert len(engine.events) > 0

    def test_lead_times_defined(self, engine):
        """Test that lead times are properly defined."""
        assert "report" in engine.lead_times
        assert "deadline" in engine.lead_times
        assert "conference" in engine.lead_times
        assert "anniversary" in engine.lead_times

    def test_get_upcoming_events_returns_list(self, engine):
        """Test get_upcoming_events returns a list."""
        events = engine.get_upcoming_events(days=365)
        assert isinstance(events, list)

    def test_get_upcoming_events_sorted_by_date(self, engine):
        """Test events are sorted by date."""
        events = engine.get_upcoming_events(days=365)
        if len(events) > 1:
            for i in range(len(events) - 1):
                assert events[i].event_date <= events[i + 1].event_date

    def test_get_actionable_topics_returns_list(self, engine):
        """Test get_actionable_topics returns a list of SourcedTopic."""
        topics = engine.get_actionable_topics()
        assert isinstance(topics, list)

    def test_event_to_topic_conversion(self, engine):
        """Test _event_to_topic creates valid SourcedTopic."""
        from shared.models import CalendarEvent

        event = CalendarEvent(
            id="test_event",
            title="Test Conference",
            event_type="conference",
            event_date=date.today() + timedelta(days=5),
            source="Test Org",
            content_type="News",
            priority="medium",
            lead_days=7,
            tags=["test"],
        )

        topic = engine._event_to_topic(event)

        assert topic.source_type == "calendar"
        assert topic.source_id == "test_event"
        assert topic.content_type == "News"
        assert topic.urgency == "medium"
        assert "test" in topic.tags

    def test_timeliness_score_calculation(self, engine):
        """Test timeliness score varies by proximity."""
        from shared.models import CalendarEvent

        # Event today
        event_today = CalendarEvent(
            id="today",
            title="Today Event",
            event_type="conference",
            event_date=date.today(),
            priority="medium",
            lead_days=7,
        )
        topic_today = engine._event_to_topic(event_today)
        assert topic_today.timeliness_score == 100

        # Event in 10 days
        event_future = CalendarEvent(
            id="future",
            title="Future Event",
            event_type="conference",
            event_date=date.today() + timedelta(days=10),
            priority="medium",
            lead_days=14,
        )
        topic_future = engine._event_to_topic(event_future)
        assert topic_future.timeliness_score < 100

    def test_generate_angle_by_event_type(self, engine):
        """Test angle generation varies by event type."""
        from shared.models import CalendarEvent

        report_event = CalendarEvent(
            id="report",
            title="Annual Report",
            event_type="report",
            event_date=date.today() + timedelta(days=5),
            priority="medium",
            lead_days=7,
        )
        angle = engine._generate_angle(report_event)
        assert "Analysis" in angle or "findings" in angle

        deadline_event = CalendarEvent(
            id="deadline",
            title="Compliance Deadline",
            event_type="deadline",
            event_date=date.today() + timedelta(days=5),
            priority="high",
            lead_days=30,
        )
        angle = engine._generate_angle(deadline_event)
        assert "Compliance" in angle or "checklist" in angle

    def test_generate_key_points_by_event_type(self, engine):
        """Test key points vary by event type."""
        from shared.models import CalendarEvent

        event = CalendarEvent(
            id="anniversary",
            title="Act Anniversary",
            event_type="anniversary",
            event_date=date.today() + timedelta(days=5),
            priority="medium",
            lead_days=7,
        )
        points = engine._generate_key_points(event)
        assert len(points) > 0
        assert any("historical" in p.lower() or "impact" in p.lower() for p in points)

    def test_add_compliance_deadline(self, engine):
        """Test adding a new compliance deadline."""
        initial_count = len(engine.events)

        result = engine.add_compliance_deadline(
            title="New Compliance Deadline",
            deadline_date=date.today() + timedelta(days=60),
            regulator="Test Regulator",
            tags=["compliance", "test"],
        )

        assert result is True
        assert len(engine.events) == initial_count + 1

        # Find the new event
        new_event = next(
            e for e in engine.events if e.title == "New Compliance Deadline"
        )
        assert new_event.event_type == "deadline"
        assert new_event.source == "Test Regulator"

    def test_add_event(self, engine):
        """Test adding a custom event."""
        from shared.models import CalendarEvent

        initial_count = len(engine.events)

        event = CalendarEvent(
            id="custom_test_event",
            title="Custom Test Event",
            event_type="conference",
            event_date=date.today() + timedelta(days=30),
            source="Test",
            priority="medium",
            lead_days=7,
        )

        result = engine.add_event(event)
        assert result is True
        assert len(engine.events) == initial_count + 1

    def test_add_duplicate_event_fails(self, engine):
        """Test adding duplicate event returns False."""
        from shared.models import CalendarEvent

        # Use an existing event ID
        if engine.events:
            existing_id = engine.events[0].id
            event = CalendarEvent(
                id=existing_id,
                title="Duplicate Event",
                event_type="conference",
                event_date=date.today() + timedelta(days=30),
                priority="medium",
                lead_days=7,
            )

            result = engine.add_event(event)
            assert result is False

    def test_remove_event(self, engine):
        """Test removing an event."""
        from shared.models import CalendarEvent

        # First add an event
        event = CalendarEvent(
            id="to_remove",
            title="Event to Remove",
            event_type="conference",
            event_date=date.today() + timedelta(days=30),
            priority="low",
            lead_days=7,
        )
        engine.add_event(event)
        initial_count = len(engine.events)

        # Now remove it
        result = engine.remove_event("to_remove")
        assert result is True
        assert len(engine.events) == initial_count - 1

    def test_remove_nonexistent_event(self, engine):
        """Test removing non-existent event returns False."""
        result = engine.remove_event("nonexistent_event_id")
        assert result is False

    def test_get_calendar_stats(self, engine):
        """Test get_calendar_stats returns expected structure."""
        stats = engine.get_calendar_stats()

        assert "total_events" in stats
        assert "by_type" in stats
        assert "upcoming_7_days" in stats
        assert "upcoming_30_days" in stats
        assert isinstance(stats["total_events"], int)
        assert isinstance(stats["by_type"], dict)

    def test_calculate_score_weighted(self, engine):
        """Test score calculation uses weights."""
        score = engine._calculate_score(
            timeliness=100,
            authority=100,
            gap=100,
        )
        # With all scores at 100, should be close to 100
        assert 85 <= score <= 100

        low_score = engine._calculate_score(
            timeliness=20,
            authority=20,
            gap=20,
        )
        # With all scores at 20, should be around 30 (includes neutral demand)
        assert low_score < 50

    def test_generate_id(self, engine):
        """Test _generate_id produces consistent hashes."""
        id1 = engine._generate_id("test-seed")
        id2 = engine._generate_id("test-seed")
        assert id1 == id2
        assert len(id1) == 12
