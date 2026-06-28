"""
app/services/notification_service.py
Notification service for Pepto marketplace.
Sends transactional emails via SendGrid with styled HTML templates.
All attempts are logged. Failures are non-fatal (best-effort delivery).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from flask import current_app
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content, HtmlContent

from app.models.user import User

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Colour palette used in all HTML emails
# ──────────────────────────────────────────────────────────────────────────────
_PRIMARY = "#4F46E5"
_SECONDARY = "#10B981"
_BG = "#F9FAFB"
_TEXT = "#1F2937"
_MUTED = "#6B7280"
_WHITE = "#FFFFFF"
_DANGER = "#EF4444"
_WARNING = "#F59E0B"


def _base_template(title: str, body_html: str) -> str:
    """Wrap body HTML in a consistent branded email shell."""
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
</head>
<body style="margin:0;padding:0;background:{_BG};font-family:'Segoe UI',Arial,sans-serif;color:{_TEXT};">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:{_BG};padding:40px 20px;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0"
               style="background:{_WHITE};border-radius:12px;overflow:hidden;
                      box-shadow:0 4px 24px rgba(0,0,0,0.08);">
          <!-- Header -->
          <tr>
            <td style="background:{_PRIMARY};padding:32px 40px;text-align:center;">
              <h1 style="margin:0;color:{_WHITE};font-size:28px;font-weight:700;letter-spacing:-0.5px;">
                🐾 Pepto
              </h1>
              <p style="margin:6px 0 0;color:rgba(255,255,255,0.8);font-size:14px;">
                Your trusted pet services marketplace
              </p>
            </td>
          </tr>
          <!-- Body -->
          <tr>
            <td style="padding:40px;">
              {body_html}
            </td>
          </tr>
          <!-- Footer -->
          <tr>
            <td style="background:{_BG};padding:24px 40px;text-align:center;
                        border-top:1px solid #E5E7EB;">
              <p style="margin:0;color:{_MUTED};font-size:12px;">
                © {datetime.utcnow().year} Pepto Pet Services Marketplace. All rights reserved.<br>
                If you have questions, reply to this email or contact
                <a href="mailto:support@pepto.in" style="color:{_PRIMARY};">support@pepto.in</a>
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""


def _cta_button(label: str, url: str, color: str = _PRIMARY) -> str:
    return f"""
<div style="text-align:center;margin:28px 0;">
  <a href="{url}" style="background:{color};color:{_WHITE};text-decoration:none;
     padding:14px 32px;border-radius:8px;font-size:16px;font-weight:600;
     display:inline-block;letter-spacing:0.2px;">{label}</a>
</div>
"""


def _booking_table(booking) -> str:  # type: ignore[valid-type]
    """Render an HTML table summarising a booking."""
    rows = [
        ("Booking ID", booking.id[:8].upper()),
        ("Service", getattr(booking.service, "name", "N/A") if booking.service else "N/A"),
        ("Date", booking.booking_date.strftime("%A, %d %B %Y") if booking.booking_date else "N/A"),
        ("Time", booking.start_time.strftime("%I:%M %p") if booking.start_time else "N/A"),
        ("Duration", f"{getattr(booking.service, 'duration_minutes', 0)} mins"
         if booking.service else "N/A"),
        ("Amount", f"₹{booking.total_amount:.2f}" if booking.total_amount else "N/A"),
        ("Status", (booking.status or "").replace("_", " ").title()),
    ]
    rows_html = "".join(
        f"""<tr>
          <td style="padding:10px 16px;font-weight:600;color:{_MUTED};
                     width:140px;border-bottom:1px solid #F3F4F6;">{k}</td>
          <td style="padding:10px 16px;color:{_TEXT};
                     border-bottom:1px solid #F3F4F6;">{v}</td>
        </tr>"""
        for k, v in rows
    )
    return f"""
<table width="100%" cellpadding="0" cellspacing="0"
       style="border:1px solid #E5E7EB;border-radius:8px;overflow:hidden;margin:20px 0;">
  {rows_html}
</table>
"""


class NotificationService:
    """
    Sends transactional emails via SendGrid.
    All public methods are best-effort; exceptions are caught and logged
    so that email failures never crash the calling request.
    """

    def __init__(self) -> None:
        self._api_key: Optional[str] = None
        self._from_email: Optional[str] = None
        self._from_name: str = "Pepto Pet Services"
        self._base_url: str = ""
        self._client: Optional[SendGridAPIClient] = None

    def _ensure_configured(self) -> None:
        if self._client is not None:
            return
        self._api_key = current_app.config.get("SENDGRID_API_KEY", "")
        self._from_email = current_app.config.get(
            "SENDGRID_FROM_EMAIL", "noreply@pepto.in"
        )
        self._base_url = current_app.config.get("FRONTEND_URL", "https://pepto.in")
        if self._api_key:
            self._client = SendGridAPIClient(api_key=self._api_key)
        else:
            logger.warning("SENDGRID_API_KEY not configured — emails will be skipped.")

    def _send(self, to_email: str, to_name: str, subject: str, html_body: str) -> bool:
        """
        Core send method. Returns True on success, False on failure.
        """
        self._ensure_configured()
        if not self._client:
            logger.warning(
                "SendGrid not configured. Skipping email to %s | subject: %s",
                to_email, subject,
            )
            return False

        message = Mail(
            from_email=Email(self._from_email, self._from_name),
            to_emails=To(to_email, to_name),
            subject=subject,
            html_content=HtmlContent(html_body),
        )

        try:
            response = self._client.send(message)
            status = response.status_code
            if 200 <= status < 300:
                logger.info(
                    "Email sent [%d] to %s | %s", status, to_email, subject
                )
                return True
            else:
                logger.error(
                    "SendGrid non-2xx [%d] for %s | %s", status, to_email, subject
                )
                return False
        except Exception:
            logger.exception(
                "SendGrid exception sending to %s | subject: %s", to_email, subject
            )
            return False

    # ──────────────────────────────────────────────────────────────────────
    # Auth-related emails
    # ──────────────────────────────────────────────────────────────────────

    def send_verification_email(self, user: User, token: str) -> bool:
        """Send email verification link to newly registered user."""
        self._ensure_configured()
        verify_url = f"{self._base_url}/verify-email?token={token}"
        body = f"""
<h2 style="margin:0 0 16px;color:{_TEXT};font-size:22px;">Welcome to Pepto, {user.first_name}! 🎉</h2>
<p style="color:{_MUTED};line-height:1.6;margin:0 0 20px;">
  Thanks for signing up! Please verify your email address to activate your account
  and start booking amazing pet services.
</p>
{_cta_button("Verify My Email", verify_url)}
<p style="color:{_MUTED};font-size:13px;margin:20px 0 0;text-align:center;">
  This link expires in 24 hours. If you did not create a Pepto account,
  you can safely ignore this email.
</p>
"""
        html = _base_template("Verify Your Pepto Account", body)
        return self._send(
            user.email,
            f"{user.first_name} {user.last_name}",
            "Verify your Pepto account",
            html,
        )

    def send_password_reset(self, user: User, token: str) -> bool:
        """Send password reset link."""
        self._ensure_configured()
        reset_url = f"{self._base_url}/reset-password?token={token}"
        body = f"""
<h2 style="margin:0 0 16px;color:{_TEXT};font-size:22px;">Reset Your Password 🔑</h2>
<p style="color:{_MUTED};line-height:1.6;margin:0 0 20px;">
  We received a request to reset the password for your Pepto account (<strong>{user.email}</strong>).
  Click the button below to choose a new password.
</p>
{_cta_button("Reset My Password", reset_url, _DANGER)}
<p style="color:{_MUTED};font-size:13px;margin:20px 0 0;text-align:center;">
  This link expires in 1 hour. If you did not request a password reset, no action is needed —
  your account is still secure.
</p>
"""
        html = _base_template("Pepto Password Reset", body)
        return self._send(
            user.email,
            f"{user.first_name} {user.last_name}",
            "Reset your Pepto password",
            html,
        )

    # ──────────────────────────────────────────────────────────────────────
    # Booking-related emails
    # ──────────────────────────────────────────────────────────────────────

    def send_booking_confirmation(self, booking) -> bool:  # type: ignore[valid-type]
        """Email sent to customer confirming their booking was placed."""
        customer = booking.customer
        dashboard_url = f"{self._base_url}/bookings/{booking.id}"
        body = f"""
<h2 style="margin:0 0 16px;color:{_TEXT};font-size:22px;">
  Booking Confirmed! ✅
</h2>
<p style="color:{_MUTED};line-height:1.6;margin:0 0 4px;">
  Hi <strong>{customer.first_name}</strong>, your booking has been placed successfully.
  Here are your booking details:
</p>
{_booking_table(booking)}
<p style="color:{_MUTED};line-height:1.6;margin:0 0 20px;font-size:14px;">
  The service provider will confirm your booking shortly. You'll receive another notification
  when they do.
</p>
{_cta_button("View Booking", dashboard_url)}
"""
        html = _base_template("Your Pepto Booking is Confirmed", body)
        return self._send(
            customer.email,
            f"{customer.first_name} {customer.last_name}",
            f"Booking Confirmed – {getattr(booking.service, 'name', 'Service')}",
            html,
        )

    def send_booking_request_to_provider(self, booking) -> bool:  # type: ignore[valid-type]
        """Email sent to provider about a new booking request."""
        provider_user = booking.provider.user if booking.provider else None
        if not provider_user:
            logger.warning("Cannot notify provider — user not found for booking %s", booking.id)
            return False

        customer = booking.customer
        dashboard_url = f"{self._base_url}/provider/bookings/{booking.id}"
        body = f"""
<h2 style="margin:0 0 16px;color:{_TEXT};font-size:22px;">
  New Booking Request 🐾
</h2>
<p style="color:{_MUTED};line-height:1.6;margin:0 0 4px;">
  Hi <strong>{provider_user.first_name}</strong>, you have a new booking request from
  <strong>{customer.first_name} {customer.last_name}</strong>.
</p>
{_booking_table(booking)}
<p style="color:{_MUTED};line-height:1.6;margin:0 0 20px;font-size:14px;">
  Please confirm or decline this booking within 24 hours. After that, it will be
  automatically cancelled.
</p>
{_cta_button("Review Booking Request", dashboard_url, _SECONDARY)}
"""
        html = _base_template("New Booking Request on Pepto", body)
        return self._send(
            provider_user.email,
            f"{provider_user.first_name} {provider_user.last_name}",
            f"New Booking Request – {getattr(booking.service, 'name', 'Service')}",
            html,
        )

    def send_status_update(self, booking, old_status: str, new_status: str) -> bool:  # type: ignore[valid-type]
        """Email sent to customer when booking status changes."""
        customer = booking.customer
        dashboard_url = f"{self._base_url}/bookings/{booking.id}"

        status_messages = {
            "confirmed": (
                "Great news! 🎉",
                f"Your booking has been <strong>confirmed</strong> by {booking.provider.business_name if booking.provider else 'the provider'}.",
                _SECONDARY,
            ),
            "cancelled": (
                "Booking Cancelled ❌",
                "Unfortunately, your booking has been cancelled."
                + (f" Reason: {booking.cancellation_reason}" if booking.cancellation_reason else ""),
                _DANGER,
            ),
            "in_progress": (
                "Service in Progress 🏃",
                f"Your {getattr(booking.service, 'name', 'service')} is now in progress.",
                _WARNING,
            ),
            "completed": (
                "Service Completed! ⭐",
                "Your service has been completed. We hope you had a great experience!",
                _SECONDARY,
            ),
            "refunded": (
                "Refund Processed 💰",
                "Your refund has been processed and will appear in your account within 5-7 business days.",
                _PRIMARY,
            ),
        }

        title_text, message, color = status_messages.get(
            new_status,
            ("Booking Update", f"Your booking status has changed from {old_status} to {new_status}.", _PRIMARY),
        )

        body = f"""
<h2 style="margin:0 0 16px;color:{color};font-size:22px;">{title_text}</h2>
<p style="color:{_MUTED};line-height:1.6;margin:0 0 4px;">
  Hi <strong>{customer.first_name}</strong>, {message}
</p>
{_booking_table(booking)}
{_cta_button("View Booking", dashboard_url, color)}
"""
        html = _base_template(f"Booking {new_status.replace('_', ' ').title()} – Pepto", body)
        return self._send(
            customer.email,
            f"{customer.first_name} {customer.last_name}",
            f"Booking Update: {new_status.replace('_', ' ').title()}",
            html,
        )

    def send_review_request(self, booking) -> bool:  # type: ignore[valid-type]
        """Email sent to customer after service completion asking for a review."""
        customer = booking.customer
        review_url = f"{self._base_url}/bookings/{booking.id}/review"
        provider_name = booking.provider.business_name if booking.provider else "your provider"
        body = f"""
<h2 style="margin:0 0 16px;color:{_TEXT};font-size:22px;">
  How was your experience? ⭐
</h2>
<p style="color:{_MUTED};line-height:1.6;margin:0 0 20px;">
  Hi <strong>{customer.first_name}</strong>, we hope <strong>{provider_name}</strong>
  did an amazing job! Your feedback helps other pet owners in the community find the best
  care for their furry friends.
</p>
<div style="background:{_BG};border-radius:8px;padding:20px;margin:0 0 20px;text-align:center;">
  <p style="margin:0 0 8px;font-weight:600;color:{_TEXT};">Rate your experience:</p>
  <span style="font-size:32px;">⭐⭐⭐⭐⭐</span>
</div>
{_cta_button("Write a Review", review_url, _WARNING)}
<p style="color:{_MUTED};font-size:13px;margin:20px 0 0;text-align:center;">
  It only takes 30 seconds and makes a huge difference to providers like {provider_name}!
</p>
"""
        html = _base_template("Share Your Pepto Experience", body)
        return self._send(
            customer.email,
            f"{customer.first_name} {customer.last_name}",
            f"How was your experience with {provider_name}?",
            html,
        )

    def send_booking_reminder(self, booking) -> bool:  # type: ignore[valid-type]
        """Reminder sent to customer 24 hours before their booking."""
        customer = booking.customer
        dashboard_url = f"{self._base_url}/bookings/{booking.id}"
        provider_name = booking.provider.business_name if booking.provider else "Your provider"
        body = f"""
<h2 style="margin:0 0 16px;color:{_TEXT};font-size:22px;">
  Reminder: Your appointment is tomorrow! 🗓️
</h2>
<p style="color:{_MUTED};line-height:1.6;margin:0 0 4px;">
  Hi <strong>{customer.first_name}</strong>, just a friendly reminder about your
  upcoming appointment with <strong>{provider_name}</strong>.
</p>
{_booking_table(booking)}
{_cta_button("View Booking Details", dashboard_url)}
<p style="color:{_MUTED};font-size:13px;margin:20px 0 0;text-align:center;">
  Need to cancel or reschedule? Please do so at least 24 hours in advance to avoid cancellation fees.
</p>
"""
        html = _base_template("Appointment Reminder – Pepto", body)
        return self._send(
            customer.email,
            f"{customer.first_name} {customer.last_name}",
            f"Reminder: Your {getattr(booking.service, 'name', 'appointment')} is tomorrow",
            html,
        )
