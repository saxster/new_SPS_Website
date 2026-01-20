"""
Alert Dispatcher - Real-time Security Incident Notification System

Orchestrates notifications across multiple channels:
- Email (via Resend)
- SMS (via Twilio)
- Web Push

Triggered by news_miner.py when high-severity incidents are detected.
"""

import os
import hashlib
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum

from content_brain import ContentBrain
from shared.logger import get_logger

logger = get_logger("AlertDispatcher")


class AlertSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertChannel(Enum):
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"


class AlertDispatcher:
    """
    Dispatches security alerts to subscribers based on their preferences.
    """

    def __init__(self, db: Optional[ContentBrain] = None):
        self.db = db or ContentBrain()
        self._init_services()

    def _init_services(self):
        """Initialize notification service clients."""
        # Resend (Email)
        self.resend_api_key = os.getenv("RESEND_API_KEY")
        self.resend_enabled = bool(self.resend_api_key)

        # Twilio (SMS)
        self.twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.twilio_phone = os.getenv("TWILIO_PHONE_NUMBER")
        self.twilio_enabled = all([self.twilio_sid, self.twilio_token, self.twilio_phone])

        # Web Push (VAPID)
        self.vapid_public = os.getenv("VAPID_PUBLIC_KEY")
        self.vapid_private = os.getenv("VAPID_PRIVATE_KEY")
        self.push_enabled = all([self.vapid_public, self.vapid_private])

        logger.info(f"Alert services: Email={self.resend_enabled}, SMS={self.twilio_enabled}, Push={self.push_enabled}")

    def dispatch_incident(
        self,
        incident_id: str,
        title: str,
        description: str,
        sector: str,
        severity: str,
        source_url: Optional[str] = None
    ) -> Dict:
        """
        Dispatch an incident alert to all relevant subscribers.

        Args:
            incident_id: Unique identifier for the incident
            title: Alert title
            description: Alert description
            sector: Affected sector (e.g., "banking", "healthcare")
            severity: Severity level (low, medium, high, critical)
            source_url: Optional link to more details

        Returns:
            Dict with dispatch statistics
        """
        logger.info(f"Dispatching alert: {title} (sector={sector}, severity={severity})")

        # Get subscribers for this sector and severity
        subscribers = self._get_relevant_subscribers(sector, severity)

        if not subscribers:
            logger.info(f"No subscribers found for sector={sector}, severity={severity}")
            return {"queued": 0, "sent": 0, "failed": 0}

        stats = {"queued": 0, "sent": 0, "failed": 0}

        for subscriber in subscribers:
            # Determine channels based on severity and subscriber preferences
            channels = self._get_channels_for_subscriber(subscriber, severity)

            for channel in channels:
                # Queue the alert
                self._queue_alert(
                    subscriber_id=subscriber["id"],
                    incident_id=incident_id,
                    incident_title=title,
                    incident_sector=sector,
                    incident_severity=severity,
                    channel=channel
                )
                stats["queued"] += 1

        # Process instant alerts immediately
        if severity in ["high", "critical"]:
            sent, failed = self._process_instant_queue()
            stats["sent"] = sent
            stats["failed"] = failed

        return stats

    def _get_relevant_subscribers(self, sector: str, severity: str) -> List[Dict]:
        """Get subscribers who should receive alerts for this sector/severity."""
        cur = self.db.conn.cursor()

        # Map severity to numeric threshold
        severity_map = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        severity_num = severity_map.get(severity, 2)

        cur.execute("""
            SELECT DISTINCT
                s.id, s.email, s.phone, s.frequency, s.channels, s.verified
            FROM alert_subscribers s
            JOIN alert_sector_subscriptions ss ON s.id = ss.subscriber_id
            WHERE ss.sector_slug = ?
            AND s.verified = 1
            AND (
                (ss.severity_threshold = 'low' AND ? >= 1) OR
                (ss.severity_threshold = 'medium' AND ? >= 2) OR
                (ss.severity_threshold = 'high' AND ? >= 3) OR
                (ss.severity_threshold = 'critical' AND ? >= 4)
            )
        """, (sector, severity_num, severity_num, severity_num, severity_num))

        return [dict(row) for row in cur.fetchall()]

    def _get_channels_for_subscriber(self, subscriber: Dict, severity: str) -> List[str]:
        """Determine which channels to use based on subscriber prefs and severity."""
        channels_str = subscriber.get("channels", "email")
        available_channels = channels_str.split(",")

        # For critical alerts, use all available channels
        if severity == "critical":
            return available_channels

        # For high alerts, use email and push
        if severity == "high":
            return [c for c in available_channels if c in ["email", "push"]]

        # For medium/low, email only
        return [c for c in available_channels if c == "email"]

    def _queue_alert(
        self,
        subscriber_id: str,
        incident_id: str,
        incident_title: str,
        incident_sector: str,
        incident_severity: str,
        channel: str
    ):
        """Add an alert to the queue."""
        cur = self.db.conn.cursor()
        cur.execute("""
            INSERT INTO alert_queue (
                subscriber_id, incident_id, incident_title,
                incident_sector, incident_severity, channel, status
            ) VALUES (?, ?, ?, ?, ?, ?, 'pending')
        """, (subscriber_id, incident_id, incident_title, incident_sector, incident_severity, channel))
        self.db.conn.commit()

    def _process_instant_queue(self) -> tuple:
        """Process all pending instant alerts."""
        cur = self.db.conn.cursor()
        cur.execute("""
            SELECT q.*, s.email, s.phone
            FROM alert_queue q
            JOIN alert_subscribers s ON q.subscriber_id = s.id
            WHERE q.status = 'pending'
            AND s.frequency = 'instant'
        """)

        alerts = [dict(row) for row in cur.fetchall()]
        sent = 0
        failed = 0

        for alert in alerts:
            try:
                if alert["channel"] == "email" and self.resend_enabled:
                    self._send_email(alert)
                    sent += 1
                elif alert["channel"] == "sms" and self.twilio_enabled:
                    self._send_sms(alert)
                    sent += 1
                elif alert["channel"] == "push" and self.push_enabled:
                    self._send_push(alert)
                    sent += 1
                else:
                    logger.warning(f"Channel {alert['channel']} not enabled, skipping")
                    failed += 1
                    continue

                # Update queue status
                cur.execute("UPDATE alert_queue SET status = 'sent', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (alert["id"],))

                # Log success
                self._log_alert(alert["subscriber_id"], alert["incident_id"], alert["channel"], "sent")

            except Exception as e:
                logger.error(f"Failed to send alert: {e}")
                cur.execute("UPDATE alert_queue SET status = 'failed', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (alert["id"],))
                self._log_alert(alert["subscriber_id"], alert["incident_id"], alert["channel"], "failed", str(e))
                failed += 1

        self.db.conn.commit()
        return sent, failed

    def _send_email(self, alert: Dict):
        """Send email via Resend."""
        import requests

        email_html = self._render_email_template(alert)

        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {self.resend_api_key}",
                "Content-Type": "application/json"
            },
            json={
                "from": "SPS Security <alerts@sps-security.com>",
                "to": [alert["email"]],
                "subject": f"[{alert['incident_severity'].upper()}] {alert['incident_title']}",
                "html": email_html
            }
        )

        if response.status_code not in [200, 201]:
            raise Exception(f"Resend API error: {response.text}")

        return response.json().get("id")

    def _send_sms(self, alert: Dict):
        """Send SMS via Twilio."""
        from twilio.rest import Client

        client = Client(self.twilio_sid, self.twilio_token)

        message = client.messages.create(
            body=f"[SPS ALERT] {alert['incident_severity'].upper()}: {alert['incident_title'][:100]}",
            from_=self.twilio_phone,
            to=alert["phone"]
        )

        return message.sid

    def _send_push(self, alert: Dict):
        """Send web push notification."""
        # TODO: Implement web push via py-web-push
        logger.info(f"Web push notification queued for subscriber {alert['subscriber_id']}")

    def _render_email_template(self, alert: Dict) -> str:
        """Render email HTML template."""
        severity_colors = {
            "low": "#3B82F6",      # Blue
            "medium": "#F59E0B",   # Amber
            "high": "#EF4444",     # Red
            "critical": "#7C3AED"  # Purple
        }

        color = severity_colors.get(alert["incident_severity"], "#6B7280")

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Courier New', monospace; background: #0A0C10; color: #FAFAFA; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ border-bottom: 4px solid {color}; padding-bottom: 20px; }}
                .severity {{ display: inline-block; padding: 4px 12px; background: {color}; color: #000; font-weight: bold; }}
                .title {{ font-size: 24px; margin-top: 20px; }}
                .sector {{ color: #A3A3A3; font-size: 12px; text-transform: uppercase; }}
                .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #2A2A2A; font-size: 12px; color: #525252; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <img src="https://sps-security.com/sps-logo.png" alt="SPS" width="48" height="48" />
                    <span class="severity">{alert['incident_severity'].upper()} ALERT</span>
                </div>
                <h1 class="title">{alert['incident_title']}</h1>
                <p class="sector">Sector: {alert['incident_sector']}</p>
                <p style="margin-top: 20px;">A new security incident has been detected in your monitored sector.</p>
                <a href="https://sps-security.com/intelligence" style="display: inline-block; margin-top: 20px; padding: 12px 24px; background: #FF4D00; color: #000; text-decoration: none; font-weight: bold;">VIEW DETAILS</a>
                <div class="footer">
                    <p>SPS Security Intelligence Platform</p>
                    <p>You're receiving this because you subscribed to {alert['incident_sector']} alerts.</p>
                    <a href="https://sps-security.com/dashboard/preferences" style="color: #FF4D00;">Manage Preferences</a>
                </div>
            </div>
        </body>
        </html>
        """

    def _log_alert(self, subscriber_id: str, incident_id: str, channel: str, status: str, error: str = None):
        """Log alert delivery attempt."""
        cur = self.db.conn.cursor()
        cur.execute("""
            INSERT INTO alert_log (subscriber_id, incident_id, channel, status, error_message)
            VALUES (?, ?, ?, ?, ?)
        """, (subscriber_id, incident_id, channel, status, error))
        self.db.conn.commit()

    def process_digest_queue(self, frequency: str = "daily"):
        """
        Process digest alerts for subscribers who prefer daily/weekly summaries.

        Called by a scheduled job (e.g., cron, celery beat).
        """
        cur = self.db.conn.cursor()

        # Get pending digest alerts
        cur.execute("""
            SELECT
                s.id as subscriber_id,
                s.email,
                GROUP_CONCAT(q.incident_title, '||') as titles,
                GROUP_CONCAT(q.incident_sector, '||') as sectors,
                COUNT(*) as alert_count
            FROM alert_queue q
            JOIN alert_subscribers s ON q.subscriber_id = s.id
            WHERE q.status = 'pending'
            AND s.frequency = ?
            AND q.channel = 'email'
            GROUP BY s.id
        """, (frequency,))

        digests = [dict(row) for row in cur.fetchall()]

        for digest in digests:
            try:
                self._send_digest_email(digest)
                # Mark alerts as sent
                cur.execute("""
                    UPDATE alert_queue
                    SET status = 'sent', updated_at = CURRENT_TIMESTAMP
                    WHERE subscriber_id = ? AND status = 'pending' AND channel = 'email'
                """, (digest["subscriber_id"],))
                logger.info(f"Sent {frequency} digest to subscriber {digest['subscriber_id']}")
            except Exception as e:
                logger.error(f"Failed to send digest: {e}")

        self.db.conn.commit()

    def _send_digest_email(self, digest: Dict):
        """Send digest summary email."""
        import requests

        titles = digest["titles"].split("||")
        sectors = list(set(digest["sectors"].split("||")))

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Courier New', monospace; background: #0A0C10; color: #FAFAFA; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ border-bottom: 4px solid #FF4D00; padding-bottom: 20px; }}
                .alert-item {{ padding: 12px 0; border-bottom: 1px solid #2A2A2A; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>SPS INTELLIGENCE DIGEST</h1>
                    <p>{digest['alert_count']} alerts in {', '.join(sectors)}</p>
                </div>
                {''.join(f'<div class="alert-item">{t}</div>' for t in titles[:10])}
                <a href="https://sps-security.com/dashboard" style="display: inline-block; margin-top: 20px; padding: 12px 24px; background: #FF4D00; color: #000; text-decoration: none; font-weight: bold;">VIEW ALL</a>
            </div>
        </body>
        </html>
        """

        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {self.resend_api_key}",
                "Content-Type": "application/json"
            },
            json={
                "from": "SPS Security <alerts@sps-security.com>",
                "to": [digest["email"]],
                "subject": f"[SPS] Your Security Intelligence Digest ({digest['alert_count']} alerts)",
                "html": html
            }
        )

        if response.status_code not in [200, 201]:
            raise Exception(f"Resend API error: {response.text}")


# ─────────────────────────────────────────────────────────────────────────────
# Subscription Management
# ─────────────────────────────────────────────────────────────────────────────

def subscribe_to_alerts(
    db: ContentBrain,
    email: str,
    sectors: List[str],
    frequency: str = "instant",
    channels: str = "email",
    phone: str = None,
    user_id: str = None
) -> Dict:
    """
    Subscribe a user to security alerts.

    Args:
        db: ContentBrain instance
        email: Subscriber email
        sectors: List of sector slugs to monitor
        frequency: Alert frequency (instant, daily, weekly)
        channels: Comma-separated channels (email, sms, push)
        phone: Phone number for SMS alerts
        user_id: Optional user ID if authenticated

    Returns:
        Dict with subscription details
    """
    subscriber_id = hashlib.md5(email.lower().strip().encode()).hexdigest()

    cur = db.conn.cursor()

    # Upsert subscriber
    cur.execute("""
        INSERT INTO alert_subscribers (id, user_id, email, phone, frequency, channels, verified)
        VALUES (?, ?, ?, ?, ?, ?, 0)
        ON CONFLICT(id) DO UPDATE SET
            phone = excluded.phone,
            frequency = excluded.frequency,
            channels = excluded.channels,
            updated_at = CURRENT_TIMESTAMP
    """, (subscriber_id, user_id, email, phone, frequency, channels))

    # Add sector subscriptions
    for sector in sectors:
        cur.execute("""
            INSERT INTO alert_sector_subscriptions (subscriber_id, sector_slug)
            VALUES (?, ?)
            ON CONFLICT(subscriber_id, sector_slug) DO NOTHING
        """, (subscriber_id, sector))

    db.conn.commit()

    return {
        "subscriber_id": subscriber_id,
        "email": email,
        "sectors": sectors,
        "frequency": frequency,
        "channels": channels,
        "verified": False
    }


def unsubscribe_from_alerts(db: ContentBrain, email: str) -> bool:
    """Unsubscribe a user from all alerts."""
    subscriber_id = hashlib.md5(email.lower().strip().encode()).hexdigest()

    cur = db.conn.cursor()
    cur.execute("DELETE FROM alert_subscribers WHERE id = ?", (subscriber_id,))
    db.conn.commit()

    return cur.rowcount > 0
