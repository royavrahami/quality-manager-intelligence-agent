"""
Notifier – Quality Managers in AI World Intelligence Agent.
Sends the Intelligence Report via configured channels:
  - Email  : full, professional HTML newsletter rendered directly in the email body
  - Slack  : summary + alert trends via Bot API
  - Console: rich formatted summary (always active)

This module is a thin multi-channel dispatcher. The per-channel rendering and
sending logic lives in dedicated modules:
  - email_renderer.EmailRenderer   (email subjects/bodies + SMTP send)
  - slack_notifier.SlackNotifier   (Slack Block Kit + Bot API)
  - console_notifier.ConsoleNotifier (rich terminal output)
  - _common                        (shared category metadata + score colour)

Gmail App Password setup:
  1. Enable 2-Step Verification: https://myaccount.google.com/security
  2. Create App Password: https://myaccount.google.com/apppasswords
  3. Use the 16-char password as SMTP_PASSWORD in .env
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from src.config.settings import settings
from src.notifications.console_notifier import ConsoleNotifier
from src.notifications.email_renderer import EmailRenderer
from src.notifications.slack_notifier import SlackNotifier
from src.storage.models import Trend

logger = logging.getLogger(__name__)


class Notifier:
    """
    Multi-channel notification dispatcher.

    Activated channels (auto-detected from settings):
      - Email : SMTP_USER + SMTP_PASSWORD + NOTIFY_EMAIL all set
      - Slack : SLACK_BOT_TOKEN set
    """

    def send_digest(
        self,
        digest_articles: list,
        stats,
        alert_trends: list[Trend],
        report_path: Optional[Path] = None,
    ) -> None:
        """
        Send the daily digest report via all configured channels.

        Args:
            digest_articles: List of DigestArticle objects.
            stats:           DigestStats summary object.
            alert_trends:    Alert-level trends.
            report_path:     Path to the generated HTML digest file.
        """
        ConsoleNotifier.console_digest_output(stats, alert_trends, report_path)

        if settings.smtp_user and settings.smtp_password and settings.notify_email:
            EmailRenderer.send_digest_email(digest_articles, stats, alert_trends, report_path)
        else:
            logger.info("Email not configured – digest email skipped")

    def send(
        self,
        alert_trends: list[Trend],
        all_trends: Optional[list[Trend]] = None,
        articles: Optional[list] = None,
        report_path: Optional[Path] = None,
    ) -> None:
        """
        Dispatch notifications to all configured channels.

        Args:
            alert_trends: High-momentum trends requiring immediate attention.
            all_trends:   All detected trends for the full trend landscape section.
            articles:     Scored articles to display in the email body.
            report_path:  Path to the generated HTML report file.
        """
        ConsoleNotifier.console_output(alert_trends, report_path)

        if settings.smtp_user and settings.smtp_password and settings.notify_email:
            EmailRenderer.send_email(
                alert_trends=alert_trends,
                all_trends=all_trends or [],
                articles=articles or [],
                report_path=report_path,
            )
        else:
            logger.info(
                "Email not configured – set SMTP_USER, SMTP_PASSWORD, NOTIFY_EMAIL to enable"
            )

        if settings.slack_bot_token:
            SlackNotifier.send_slack(alert_trends, report_path)
