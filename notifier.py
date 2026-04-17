"""
notifier.py
Sends NEW PRODUCT alert emails via Gmail SMTP.

Required GitHub Actions secrets:
  GMAIL_USER   — sender Gmail address
  GMAIL_PASS   — 16-char App Password (NOT your login password)
  NOTIFY_EMAIL — recipient (defaults to GMAIL_USER if not set)
"""
import os
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List

from scrapers.base import ProductEntry

logger = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def _build_email(
    sender: str,
    recipient: str,
    new_by_page: Dict[str, List[ProductEntry]],
) -> MIMEMultipart:
    """Construct a multipart email for new product alerts."""
    total_new = sum(len(items) for items in new_by_page.values())
    subject = f"🆕 New Products Alert: {total_new} item(s) across {len(new_by_page)} page(s)!"

    # ── Plain text body ─────────────────────────────────────────
    text_lines = [
        f"New products detected on {len(new_by_page)} listing page(s):\n",
    ]
    for page_name, items in new_by_page.items():
        text_lines.append(f"  [{page_name}]")
        for item in items:
            price_str = f" — {item.price}" if item.price else ""
            text_lines.append(f"    • {item.name}{price_str}")
            text_lines.append(f"      {item.url}")
        text_lines.append("")
    text_lines.append("— Stock Tracker Bot")
    text_body = "\n".join(text_lines)

    # ── HTML body ───────────────────────────────────────────────
    html_sections = ""
    for page_name, items in new_by_page.items():
        rows = ""
        for item in items:
            price_str = f'<span style="color:#6b7280;font-size:13px;"> — {item.price}</span>' if item.price else ""
            rows += (
                f'<tr>'
                f'  <td style="padding:10px 16px;border-bottom:1px solid #e5e7eb;">'
                f'    <strong>{item.name}</strong>{price_str}<br>'
                f'    <a href="{item.url}" style="color:#4f46e5;font-size:13px;">{item.url}</a>'
                f'  </td>'
                f'</tr>'
            )
        html_sections += f"""
        <div style="margin-bottom:24px;">
          <h3 style="color:#1f2937;margin:0 0 8px;font-size:16px;">📦 {page_name}</h3>
          <table cellpadding="0" cellspacing="0" width="100%"
                 style="border-collapse:collapse;border:1px solid #e5e7eb;border-radius:8px;">
            <tbody>{rows}</tbody>
          </table>
        </div>
        """

    html_body = f"""
    <html><body style="font-family:Arial,sans-serif;background:#f9fafb;padding:24px;">
      <div style="max-width:600px;margin:auto;background:#fff;border-radius:12px;
                  box-shadow:0 2px 8px rgba(0,0,0,.08);overflow:hidden;">
        <div style="background:linear-gradient(135deg,#059669,#10b981);padding:24px;">
          <h1 style="color:#fff;margin:0;font-size:22px;">🆕 New Products Detected</h1>
          <p style="color:#d1fae5;margin:6px 0 0;">{total_new} new item(s) across {len(new_by_page)} page(s)</p>
        </div>
        <div style="padding:24px;">
          {html_sections}
          <p style="color:#6b7280;font-size:13px;margin-top:20px;">
            Don't wait — these are freshly listed!<br>
            <em>— Stock Tracker Bot</em>
          </p>
        </div>
      </div>
    </body></html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))
    return msg


def send_alert(new_by_page: Dict[str, List[ProductEntry]]) -> None:
    """Send a new-product alert email."""
    if not new_by_page:
        logger.info("No new products to notify about.")
        return

    gmail_user = os.environ.get("GMAIL_USER", "").strip()
    gmail_pass = os.environ.get("GMAIL_PASS", "").strip()
    recipient = os.environ.get("NOTIFY_EMAIL", "").strip() or "baidikmustnot@gmail.com"

    if not gmail_user or not gmail_pass:
        raise RuntimeError(
            "Missing GMAIL_USER or GMAIL_PASS environment variables. "
            "Set them as GitHub Actions secrets."
        )

    msg = _build_email(gmail_user, recipient, new_by_page)
    total_new = sum(len(items) for items in new_by_page.values())

    logger.info(f"Sending alert to {recipient} for {total_new} new item(s)…")
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(gmail_user, gmail_pass)
            server.sendmail(gmail_user, recipient, msg.as_string())
        logger.info("✉️  Alert email sent successfully.")
    except smtplib.SMTPAuthenticationError:
        raise RuntimeError(
            "Gmail auth failed. GMAIL_PASS must be an App Password, "
            "NOT your regular Gmail password."
        )
    except Exception as e:
        logger.exception(f"Failed to send email: {e}")
        raise
