"""
Notification Services - Multi-Channel Alert Delivery

Provides unified interface for sending notifications via:
- Email (Resend)
- SMS (Twilio)
- Web Push (py-web-push / VAPID)
"""

import os
import json
import base64
from typing import Dict, Optional, List
from dataclasses import dataclass
from abc import ABC, abstractmethod

from shared.logger import get_logger

logger = get_logger("NotificationServices")


@dataclass
class NotificationResult:
    """Result of a notification send attempt."""
    success: bool
    channel: str
    external_id: Optional[str] = None
    error: Optional[str] = None


class NotificationService(ABC):
    """Base class for notification services."""

    @abstractmethod
    def send(self, to: str, subject: str, body: str, **kwargs) -> NotificationResult:
        """Send a notification."""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if the service is properly configured."""
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Email Service (Resend)
# ─────────────────────────────────────────────────────────────────────────────

class ResendEmailService(NotificationService):
    """
    Email notification via Resend API.

    https://resend.com/docs/api-reference/emails/send-email
    """

    def __init__(self):
        self.api_key = os.getenv("RESEND_API_KEY")
        self.from_email = os.getenv("RESEND_FROM_EMAIL", "SPS Security <alerts@sps-security.com>")
        self.api_url = "https://api.resend.com/emails"

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def send(
        self,
        to: str,
        subject: str,
        body: str,
        html: Optional[str] = None,
        **kwargs
    ) -> NotificationResult:
        """
        Send an email via Resend.

        Args:
            to: Recipient email address
            subject: Email subject line
            body: Plain text body
            html: Optional HTML body (preferred for rich emails)
        """
        if not self.is_configured():
            return NotificationResult(
                success=False,
                channel="email",
                error="Resend API key not configured"
            )

        import requests

        try:
            payload = {
                "from": self.from_email,
                "to": [to] if isinstance(to, str) else to,
                "subject": subject,
            }

            if html:
                payload["html"] = html
            else:
                payload["text"] = body

            response = requests.post(
                self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=30
            )

            if response.status_code in [200, 201]:
                data = response.json()
                logger.info(f"Email sent to {to}: {data.get('id')}")
                return NotificationResult(
                    success=True,
                    channel="email",
                    external_id=data.get("id")
                )
            else:
                error_msg = response.text
                logger.error(f"Resend API error: {error_msg}")
                return NotificationResult(
                    success=False,
                    channel="email",
                    error=f"API error: {response.status_code}"
                )

        except Exception as e:
            logger.error(f"Email send failed: {e}")
            return NotificationResult(
                success=False,
                channel="email",
                error=str(e)
            )


# ─────────────────────────────────────────────────────────────────────────────
# SMS Service (Twilio)
# ─────────────────────────────────────────────────────────────────────────────

class TwilioSMSService(NotificationService):
    """
    SMS notification via Twilio.

    https://www.twilio.com/docs/sms/api/message-resource
    """

    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.from_number = os.getenv("TWILIO_PHONE_NUMBER")

    def is_configured(self) -> bool:
        return all([self.account_sid, self.auth_token, self.from_number])

    def send(
        self,
        to: str,
        subject: str,
        body: str,
        **kwargs
    ) -> NotificationResult:
        """
        Send an SMS via Twilio.

        Args:
            to: Recipient phone number (E.164 format: +91XXXXXXXXXX)
            subject: Not used for SMS, but included in body
            body: SMS message body (max 160 chars for single SMS)
        """
        if not self.is_configured():
            return NotificationResult(
                success=False,
                channel="sms",
                error="Twilio credentials not configured"
            )

        try:
            from twilio.rest import Client
            from twilio.base.exceptions import TwilioRestException

            client = Client(self.account_sid, self.auth_token)

            # Combine subject and body for SMS
            message_body = f"[SPS] {subject}: {body}"

            # Truncate to SMS limit if needed
            if len(message_body) > 160:
                message_body = message_body[:157] + "..."

            message = client.messages.create(
                body=message_body,
                from_=self.from_number,
                to=to
            )

            logger.info(f"SMS sent to {to}: {message.sid}")
            return NotificationResult(
                success=True,
                channel="sms",
                external_id=message.sid
            )

        except TwilioRestException as e:
            logger.error(f"Twilio error: {e}")
            return NotificationResult(
                success=False,
                channel="sms",
                error=str(e)
            )
        except ImportError:
            logger.error("Twilio library not installed")
            return NotificationResult(
                success=False,
                channel="sms",
                error="Twilio library not installed"
            )
        except Exception as e:
            logger.error(f"SMS send failed: {e}")
            return NotificationResult(
                success=False,
                channel="sms",
                error=str(e)
            )


# ─────────────────────────────────────────────────────────────────────────────
# Web Push Service (VAPID)
# ─────────────────────────────────────────────────────────────────────────────

class WebPushService(NotificationService):
    """
    Web Push notification via VAPID protocol.

    Uses py-web-push library for sending push notifications.
    """

    def __init__(self):
        self.vapid_public = os.getenv("VAPID_PUBLIC_KEY")
        self.vapid_private = os.getenv("VAPID_PRIVATE_KEY")
        self.vapid_claims = {
            "sub": "mailto:alerts@sps-security.com"
        }

    def is_configured(self) -> bool:
        return all([self.vapid_public, self.vapid_private])

    def send(
        self,
        to: str,
        subject: str,
        body: str,
        subscription_info: Optional[Dict] = None,
        **kwargs
    ) -> NotificationResult:
        """
        Send a web push notification.

        Args:
            to: Not used directly - subscription_info contains endpoint
            subject: Notification title
            body: Notification body
            subscription_info: Browser push subscription object containing:
                - endpoint: Push service URL
                - keys.p256dh: User public key
                - keys.auth: User auth secret
        """
        if not self.is_configured():
            return NotificationResult(
                success=False,
                channel="push",
                error="VAPID keys not configured"
            )

        if not subscription_info:
            return NotificationResult(
                success=False,
                channel="push",
                error="No subscription info provided"
            )

        try:
            from pywebpush import webpush, WebPushException

            # Prepare notification payload
            payload = json.dumps({
                "title": subject,
                "body": body,
                "icon": "/sps-logo.png",
                "badge": "/sps-badge.png",
                "tag": "sps-alert",
                "data": {
                    "url": "/dashboard"
                }
            })

            webpush(
                subscription_info=subscription_info,
                data=payload,
                vapid_private_key=self.vapid_private,
                vapid_claims=self.vapid_claims
            )

            logger.info(f"Web push sent to endpoint: {subscription_info.get('endpoint', 'unknown')[:50]}...")
            return NotificationResult(
                success=True,
                channel="push"
            )

        except WebPushException as e:
            logger.error(f"Web push error: {e}")
            return NotificationResult(
                success=False,
                channel="push",
                error=str(e)
            )
        except ImportError:
            logger.error("pywebpush library not installed")
            return NotificationResult(
                success=False,
                channel="push",
                error="pywebpush library not installed"
            )
        except Exception as e:
            logger.error(f"Push send failed: {e}")
            return NotificationResult(
                success=False,
                channel="push",
                error=str(e)
            )


# ─────────────────────────────────────────────────────────────────────────────
# Unified Notification Manager
# ─────────────────────────────────────────────────────────────────────────────

class NotificationManager:
    """
    Unified manager for all notification channels.

    Usage:
        manager = NotificationManager()
        result = manager.send(
            channel="email",
            to="user@example.com",
            subject="Security Alert",
            body="A new threat has been detected..."
        )
    """

    def __init__(self):
        self.services = {
            "email": ResendEmailService(),
            "sms": TwilioSMSService(),
            "push": WebPushService()
        }

    def get_available_channels(self) -> List[str]:
        """Get list of properly configured channels."""
        return [name for name, service in self.services.items() if service.is_configured()]

    def send(
        self,
        channel: str,
        to: str,
        subject: str,
        body: str,
        **kwargs
    ) -> NotificationResult:
        """
        Send a notification via specified channel.

        Args:
            channel: Channel to use (email, sms, push)
            to: Recipient (email, phone, or subscription endpoint)
            subject: Notification title/subject
            body: Notification body
            **kwargs: Additional channel-specific options
        """
        if channel not in self.services:
            return NotificationResult(
                success=False,
                channel=channel,
                error=f"Unknown channel: {channel}"
            )

        service = self.services[channel]

        if not service.is_configured():
            return NotificationResult(
                success=False,
                channel=channel,
                error=f"{channel} service not configured"
            )

        return service.send(to, subject, body, **kwargs)

    def send_multi(
        self,
        channels: List[str],
        to_map: Dict[str, str],
        subject: str,
        body: str,
        **kwargs
    ) -> List[NotificationResult]:
        """
        Send notification via multiple channels.

        Args:
            channels: List of channels to use
            to_map: Dict mapping channel to recipient (e.g., {"email": "a@b.com", "sms": "+91..."})
            subject: Notification title
            body: Notification body

        Returns:
            List of NotificationResult for each channel
        """
        results = []
        for channel in channels:
            if channel not in to_map:
                results.append(NotificationResult(
                    success=False,
                    channel=channel,
                    error=f"No recipient for {channel}"
                ))
                continue

            result = self.send(
                channel=channel,
                to=to_map[channel],
                subject=subject,
                body=body,
                **kwargs
            )
            results.append(result)

        return results


# ─────────────────────────────────────────────────────────────────────────────
# Email Templates
# ─────────────────────────────────────────────────────────────────────────────

def render_alert_email(
    title: str,
    sector: str,
    severity: str,
    description: str,
    action_url: str = "https://sps-security.com/intelligence"
) -> str:
    """Render an HTML email template for security alerts."""
    from pathlib import Path

    severity_colors = {
        "low": "#3B82F6",
        "medium": "#F59E0B",
        "high": "#EF4444",
        "critical": "#7C3AED"
    }
    color = severity_colors.get(severity, "#6B7280")

    template_path = Path(__file__).parent / "templates" / "alert_email.html"
    template = template_path.read_text()

    return template.format(
        title=title,
        sector=sector,
        severity_upper=severity.upper(),
        description=description,
        action_url=action_url,
        color=color
    )
