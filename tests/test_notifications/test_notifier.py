"""
Unit tests for the email Notifier's HTML builder.

Regression coverage for the alert-card rendering path in
``Notifier._build_email_html``. That path previously raised
``NameError: name '_CATEGORY_ICONS' is not defined`` because it looked up a
symbol that does not exist, instead of the module-level ``_CATEGORY_META``
table used everywhere else in the file. The bug was latent because it only
triggers when ``alert_trends`` is non-empty (i.e. exactly when an alert email
needs to be sent) and there was no test exercising it.
"""

from __future__ import annotations

from src.notifications.notifier import Notifier, _CATEGORY_META
from src.storage.models import Trend


def _trend(
    name: str,
    category: str,
    description: str | None = None,
    momentum_score: float = 82.5,
    article_count: int = 7,
) -> Trend:
    """Build a transient Trend (no DB session needed) for rendering tests.

    Numeric fields are populated with realistic values because alert trends
    reaching the email path always come from the DB (where column defaults
    such as ``momentum_score=0.0`` and ``article_count=1`` are applied).
    """
    return Trend(
        name=name,
        category=category,
        description=description,
        momentum_score=momentum_score,
        article_count=article_count,
        is_alert=True,
    )


def test_build_email_html_with_alert_trends_renders_without_error() -> None:
    """A non-empty alert_trends list must render, not raise.

    Before the fix this raised ``NameError: _CATEGORY_ICONS``.
    """
    trends = [_trend("Flaky CI surge", "qa_testing", "Many flaky tests reported")]

    html = Notifier._build_email_html(
        alert_trends=trends,
        report_html="<div>full report</div>",
        date_str="2026-06-01",
    )

    assert isinstance(html, str)
    assert "Flaky CI surge" in html
    # The icon must come from _CATEGORY_META (the real table), not a missing _CATEGORY_ICONS.
    assert _CATEGORY_META["qa_testing"]["icon"] in html


def test_build_email_html_unknown_category_falls_back_to_general_icon() -> None:
    """An unmapped category falls back to the 'general' icon instead of crashing."""
    trends = [_trend("Mystery topic", "totally_unknown_category")]

    html = Notifier._build_email_html(
        alert_trends=trends,
        report_html="<div>full report</div>",
        date_str="2026-06-01",
    )

    assert "Mystery topic" in html
    assert _CATEGORY_META["general"]["icon"] in html


def test_build_email_html_without_alerts_still_renders() -> None:
    """The no-alerts path returns wrapper HTML without error."""
    html = Notifier._build_email_html(
        alert_trends=[],
        report_html="<div>full report</div>",
        date_str="2026-06-01",
    )

    assert isinstance(html, str)
    assert len(html) > 0
