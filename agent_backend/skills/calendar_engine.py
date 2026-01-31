"""
CalendarEngine: Event and deadline-driven topic sourcing.

Tracks and generates topics from:
- Annual reports (CERT-IN, NCRB, etc.)
- Compliance deadlines
- Industry conferences
- Important anniversaries
- Policy review dates

Provides calendar-driven content planning for the editorial pipeline.
"""

import os
import sys
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
import hashlib

# Allow running from repo root without PYTHONPATH
AGENT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if AGENT_ROOT not in sys.path:
    sys.path.insert(0, AGENT_ROOT)

from config.manager import config
from shared.logger import get_logger
from shared.models import CalendarEvent, SourcedTopic

logger = get_logger("CalendarEngine")


class CalendarEngine:
    """
    Calendar-driven topic sourcing engine.

    Manages a calendar of recurring and one-time events that
    should trigger content creation at appropriate lead times.
    """

    def __init__(self, brain=None):
        """
        Initialize CalendarEngine.

        Args:
            brain: Optional ContentBrain instance for database access
        """
        self.brain = brain
        self.events = self._load_events()
        self.lead_times = config.get(
            "calendar_engine.lead_times",
            {
                "report": 7,
                "deadline": 30,
                "conference": 14,
                "anniversary": 7,
            },
        )

    def _load_events(self) -> List[CalendarEvent]:
        """Load calendar events from config."""
        events = []
        event_configs = config.get("calendar_engine.events", [])

        for evt in event_configs:
            try:
                # Calculate event date for this year
                event_date = self._calculate_event_date(evt)
                if not event_date:
                    continue

                calendar_event = CalendarEvent(
                    id=evt.get("id", self._generate_id(evt.get("title", ""))),
                    title=evt.get("title", ""),
                    event_type=evt.get("event_type", "report"),
                    event_date=event_date,
                    recurring=evt.get("recurring"),
                    source=evt.get("source", ""),
                    content_type=evt.get("content_type", "Analysis"),
                    priority=evt.get("priority", "medium"),
                    lead_days=evt.get("lead_days", 7),
                    tags=evt.get("tags", []),
                    description=evt.get("description", ""),
                )
                events.append(calendar_event)
            except Exception as e:
                logger.warning(
                    "event_load_error",
                    event_id=evt.get("id", "unknown"),
                    error=str(e),
                )

        if not events:
            events = self._get_default_events()

        logger.info("calendar_events_loaded", count=len(events))
        return events

    def _calculate_event_date(self, evt: Dict) -> Optional[date]:
        """Calculate the next occurrence date for an event."""
        today = date.today()
        current_year = today.year

        month = evt.get("month")
        day = evt.get("day", 1)

        if not month:
            # For events without a fixed month (e.g., bimonthly)
            return None

        # Calculate date for this year
        try:
            event_date = date(current_year, month, day)
        except ValueError:
            # Invalid date (e.g., Feb 30)
            event_date = date(current_year, month, 28)

        # If event has passed this year, get next year's date
        recurring = evt.get("recurring")
        if recurring == "annual" and event_date < today:
            event_date = date(current_year + 1, month, day)

        return event_date

    def _get_default_events(self) -> List[CalendarEvent]:
        """Default events if config is missing."""
        today = date.today()
        current_year = today.year

        defaults = [
            CalendarEvent(
                id="cert_in_annual",
                title="CERT-IN Annual Report",
                event_type="report",
                event_date=date(current_year, 3, 15),
                recurring="annual",
                source="CERT-IN",
                content_type="Analysis",
                priority="high",
                lead_days=7,
                tags=["cybersecurity", "government", "statistics"],
            ),
            CalendarEvent(
                id="ncrb_crime_report",
                title="NCRB Crime in India Report",
                event_type="report",
                event_date=date(current_year, 8, 15),
                recurring="annual",
                source="NCRB",
                content_type="Analysis",
                priority="high",
                lead_days=7,
                tags=["crime", "statistics", "security"],
            ),
            CalendarEvent(
                id="union_budget",
                title="Union Budget",
                event_type="report",
                event_date=date(current_year, 2, 1),
                recurring="annual",
                source="Ministry of Finance",
                content_type="Analysis",
                priority="critical",
                lead_days=14,
                tags=["budget", "policy", "economy"],
            ),
            CalendarEvent(
                id="cybersecurity_awareness_month",
                title="Cybersecurity Awareness Month",
                event_type="anniversary",
                event_date=date(current_year, 10, 1),
                recurring="annual",
                source="Global",
                content_type="Guide",
                priority="high",
                lead_days=30,
                tags=["cybersecurity", "awareness", "education"],
            ),
            CalendarEvent(
                id="dpdp_anniversary",
                title="DPDP Act Anniversary",
                event_type="anniversary",
                event_date=date(current_year, 8, 11),
                recurring="annual",
                source="MeitY",
                content_type="Analysis",
                priority="medium",
                lead_days=14,
                tags=["privacy", "data_protection", "compliance"],
            ),
        ]

        # Adjust dates if past this year
        result = []
        for evt in defaults:
            if evt.event_date < today and evt.recurring == "annual":
                evt.event_date = date(
                    current_year + 1, evt.event_date.month, evt.event_date.day
                )
            result.append(evt)

        return result

    def get_upcoming_events(self, days: int = 30) -> List[CalendarEvent]:
        """
        Get events occurring within the next N days.

        Args:
            days: Number of days to look ahead

        Returns:
            List of CalendarEvent objects sorted by date
        """
        today = date.today()
        end_date = today + timedelta(days=days)

        upcoming = []
        for event in self.events:
            # Check if event is within the window
            if today <= event.event_date <= end_date:
                upcoming.append(event)

        # Sort by date
        upcoming.sort(key=lambda x: x.event_date)

        logger.info("upcoming_events", count=len(upcoming), days=days)
        return upcoming

    def get_actionable_topics(self) -> List[SourcedTopic]:
        """
        Get topics that should be created based on calendar events.

        Only returns topics for events where:
        - We are within the lead time window
        - The topic hasn't been created recently

        Returns:
            List of SourcedTopic objects
        """
        today = date.today()
        topics = []

        for event in self.events:
            # Calculate when we should start covering this event
            action_date = event.event_date - timedelta(days=event.lead_days)

            # Check if we're in the action window
            if action_date <= today <= event.event_date:
                # Check if already triggered recently (if brain available)
                if event.last_triggered:
                    days_since = (datetime.now() - event.last_triggered).days
                    if days_since < event.lead_days:
                        continue

                # Create topic from event
                topic = self._event_to_topic(event)
                topics.append(topic)

        # Sort by urgency and date
        urgency_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        topics.sort(
            key=lambda x: (
                urgency_order.get(x.urgency, 2),
                -x.timeliness_score,
            )
        )

        logger.info("actionable_topics", count=len(topics))
        return topics

    def _event_to_topic(self, event: CalendarEvent) -> SourcedTopic:
        """Convert a CalendarEvent to a SourcedTopic."""
        today = date.today()
        days_until = (event.event_date - today).days

        # Calculate timeliness score (higher = more urgent)
        if days_until <= 0:
            timeliness = 100  # Event is today or past
        elif days_until <= 3:
            timeliness = 90
        elif days_until <= 7:
            timeliness = 75
        elif days_until <= 14:
            timeliness = 60
        else:
            timeliness = 40

        # Generate suggested angle based on event type
        angle = self._generate_angle(event)

        # Generate key points
        key_points = self._generate_key_points(event)

        return SourcedTopic(
            id=f"cal_{event.id}_{today.isoformat()}",
            title=f"{event.title}: What to Expect",
            source_type="calendar",
            source_id=event.id,
            urgency=event.priority,
            content_type=event.content_type,
            source_url=None,
            timeliness_score=timeliness,
            authority_score=80,  # Calendar events are authoritative
            gap_score=70,  # Usually gaps in coverage
            overall_score=self._calculate_score(timeliness, 80, 70),
            suggested_angle=angle,
            key_points=key_points,
            tags=event.tags,
        )

    def _generate_angle(self, event: CalendarEvent) -> str:
        """Generate a suggested editorial angle for the event."""
        angles = {
            "report": f"Analysis of key findings from the upcoming {event.title}",
            "deadline": f"Compliance checklist: Preparing for {event.title}",
            "conference": f"Key themes and sessions to watch at {event.title}",
            "anniversary": f"Looking back: Impact of {event.title} on the industry",
        }
        return angles.get(event.event_type, f"Coverage of {event.title}")

    def _generate_key_points(self, event: CalendarEvent) -> List[str]:
        """Generate key points to cover for the event."""
        points = {
            "report": [
                "Key statistics and trends",
                "Year-over-year comparisons",
                "Implications for the industry",
                "Actionable recommendations",
            ],
            "deadline": [
                "What needs to be done",
                "Who is affected",
                "Penalties for non-compliance",
                "Step-by-step preparation guide",
            ],
            "conference": [
                "Keynote speakers and topics",
                "Important sessions to attend",
                "Networking opportunities",
                "Key takeaways expected",
            ],
            "anniversary": [
                "Historical context",
                "Impact since implementation",
                "Current state of affairs",
                "Future outlook",
            ],
        }
        return points.get(event.event_type, ["Overview", "Key points", "Analysis"])

    def _calculate_score(self, timeliness: int, authority: int, gap: int) -> float:
        """Calculate overall score using configured weights."""
        weights = config.get(
            "topic_sourcer.scoring",
            {
                "timeliness": 0.30,
                "authority": 0.30,
                "demand": 0.20,
                "gap": 0.20,
            },
        )

        # Use demand as 50 (neutral) for calendar events
        demand = 50

        score = (
            timeliness * weights.get("timeliness", 0.25)
            + authority * weights.get("authority", 0.25)
            + demand * weights.get("demand", 0.25)
            + gap * weights.get("gap", 0.25)
        )

        return round(score, 2)

    def add_compliance_deadline(
        self,
        title: str,
        deadline_date: date,
        regulator: str,
        tags: Optional[List[str]] = None,
    ) -> bool:
        """
        Add a compliance deadline to the calendar.

        Args:
            title: Deadline title
            deadline_date: Date of the deadline
            regulator: Regulator imposing the deadline
            tags: Optional tags for the event

        Returns:
            True if successfully added
        """
        event_id = self._generate_id(f"{title}_{deadline_date.isoformat()}")

        new_event = CalendarEvent(
            id=event_id,
            title=title,
            event_type="deadline",
            event_date=deadline_date,
            recurring=None,
            source=regulator,
            content_type="Guide",
            priority="high",
            lead_days=30,
            tags=tags or ["compliance", "deadline"],
        )

        self.events.append(new_event)
        logger.info(
            "deadline_added",
            title=title,
            date=deadline_date.isoformat(),
            regulator=regulator,
        )

        return True

    def add_event(self, event: CalendarEvent) -> bool:
        """
        Add a custom event to the calendar.

        Args:
            event: CalendarEvent to add

        Returns:
            True if successfully added
        """
        # Check for duplicates
        existing_ids = {e.id for e in self.events}
        if event.id in existing_ids:
            logger.warning("duplicate_event", event_id=event.id)
            return False

        self.events.append(event)
        logger.info("event_added", event_id=event.id, title=event.title)
        return True

    def remove_event(self, event_id: str) -> bool:
        """
        Remove an event from the calendar.

        Args:
            event_id: ID of the event to remove

        Returns:
            True if successfully removed
        """
        original_count = len(self.events)
        self.events = [e for e in self.events if e.id != event_id]

        if len(self.events) < original_count:
            logger.info("event_removed", event_id=event_id)
            return True

        logger.warning("event_not_found", event_id=event_id)
        return False

    def _generate_id(self, seed: str) -> str:
        """Generate a unique ID from a seed string."""
        return hashlib.md5(seed.encode()).hexdigest()[:12]

    def get_calendar_stats(self) -> Dict[str, Any]:
        """Get statistics about the calendar."""
        today = date.today()

        stats = {
            "total_events": len(self.events),
            "by_type": {},
            "upcoming_7_days": 0,
            "upcoming_30_days": 0,
        }

        for event in self.events:
            # Count by type
            event_type = event.event_type
            stats["by_type"][event_type] = stats["by_type"].get(event_type, 0) + 1

            # Count upcoming
            days_until = (event.event_date - today).days
            if 0 <= days_until <= 7:
                stats["upcoming_7_days"] += 1
            if 0 <= days_until <= 30:
                stats["upcoming_30_days"] += 1

        return stats


if __name__ == "__main__":
    # Quick test
    engine = CalendarEngine()

    print("Calendar Stats:")
    print(engine.get_calendar_stats())

    print("\nUpcoming Events (60 days):")
    for event in engine.get_upcoming_events(days=60):
        print(f"  - {event.title} ({event.event_date})")

    print("\nActionable Topics:")
    for topic in engine.get_actionable_topics():
        print(f"  - [{topic.urgency}] {topic.title} (score: {topic.overall_score})")
