"""Slack channel for the Intelligence Agent.

Posts the alert summary to Slack via the Bot API. The logic is unchanged from
the original monolithic Notifier — it was only relocated into this module.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.config.settings import settings
from src.notifications._common import _CATEGORY_META
from src.storage.models import Trend

logger = logging.getLogger(__name__)


class SlackNotifier:
    """Posts the intelligence summary and alert trends to Slack."""

    @staticmethod
    def send_slack(
        alert_trends: list[Trend],
        report_path: Optional[Path],
    ) -> None:
        """Post a Slack notification with alert summary."""
        try:
            from slack_sdk import WebClient
        except ImportError:
            logger.warning("slack_sdk not installed – Slack notifications disabled")
            return

        client = WebClient(token=settings.slack_bot_token)
        blocks = SlackNotifier.build_slack_blocks(alert_trends, report_path)

        try:
            client.chat_postMessage(
                channel=settings.slack_channel,
                blocks=blocks,
                text="Quality Managers in AI World – Intelligence Report",
            )
            logger.info("Slack notification sent to %s", settings.slack_channel)
        except Exception as exc:
            logger.error("Failed to send Slack notification: %s", exc)

    @staticmethod
    def build_slack_blocks(alert_trends: list[Trend], report_path: Optional[Path]) -> list[dict]:
        """Build Slack Block Kit payload."""
        now = datetime.now(timezone.utc).strftime("%d %b %Y %H:%M UTC")
        blocks: list[dict] = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "🎯 Quality Managers in AI World", "emoji": True},
            },
            {
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": f"Intelligence Report | {now}"}],
            },
        ]

        if alert_trends:
            alert_text = "\n".join(
                f"• *{_CATEGORY_META.get(t.category or 'general', _CATEGORY_META['general'])['icon']} {t.name}* "
                f"({t.category}) — momentum: `{t.momentum_score:.1f}` | articles: `{t.article_count}`"
                for t in alert_trends
            )
            blocks.append({"type": "divider"})
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"🚨 *Critical Insights – Action Recommended:*\n{alert_text}"},
            })
        else:
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": "✅ *All Systems Normal — No Critical Insights*"},
            })

        if report_path:
            blocks.append({"type": "divider"})
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"📄 *Report file:* `{report_path.name}`"},
            })

        return blocks
