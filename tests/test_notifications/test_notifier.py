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

from types import SimpleNamespace

from src.config.settings import settings as _settings
from src.notifications._common import _CATEGORY_META
from src.notifications.email_renderer import EmailRenderer
from src.notifications.notifier import Notifier
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

    html = EmailRenderer.build_email_html(
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

    html = EmailRenderer.build_email_html(
        alert_trends=trends,
        report_html="<div>full report</div>",
        date_str="2026-06-01",
    )

    assert "Mystery topic" in html
    assert _CATEGORY_META["general"]["icon"] in html


def test_build_email_html_without_alerts_still_renders() -> None:
    """The no-alerts path returns wrapper HTML without error."""
    html = EmailRenderer.build_email_html(
        alert_trends=[],
        report_html="<div>full report</div>",
        date_str="2026-06-01",
    )

    assert isinstance(html, str)
    assert len(html) > 0


def _disable_email_and_slack(monkeypatch) -> None:
    for attr in ("smtp_user", "smtp_password", "notify_email", "slack_bot_token"):
        monkeypatch.setattr(_settings, attr, None, raising=False)


def test_notifier_send_console_only_does_not_raise(monkeypatch) -> None:
    """With email/slack unconfigured, send() runs the console path and returns."""
    _disable_email_and_slack(monkeypatch)
    Notifier().send(
        alert_trends=[_trend("Flaky CI surge", "qa_testing")],
        all_trends=[],
        articles=[],
        report_path=None,
    )


def test_notifier_send_digest_console_only_does_not_raise(monkeypatch) -> None:
    """With email unconfigured, send_digest() runs the console path and returns."""
    _disable_email_and_slack(monkeypatch)
    stats = SimpleNamespace(
        date_str="01 May 2026",
        total_articles=3,
        avg_relevance=55.0,
        alert_count=1,
        category_counts={"qa_testing": 2},
    )
    Notifier().send_digest(
        digest_articles=[],
        stats=stats,
        alert_trends=[_trend("Flaky CI surge", "qa_testing")],
        report_path=None,
    )


def test_send_email_builds_body_and_attempts_send(monkeypatch) -> None:
    """EmailRenderer.send_email builds the email and hands it to SMTP.sendmail."""
    monkeypatch.setattr(_settings, "smtp_user", "from@example.com", raising=False)
    monkeypatch.setattr(_settings, "smtp_password", "app-password", raising=False)
    monkeypatch.setattr(_settings, "notify_email", "to@example.com", raising=False)
    monkeypatch.setattr(_settings, "smtp_host", "smtp.example.com", raising=False)
    monkeypatch.setattr(_settings, "smtp_port", 587, raising=False)

    captured: dict[str, str] = {}

    class FakeSMTP:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args) -> bool:
            return False

        def ehlo(self) -> None:
            pass

        def starttls(self) -> None:
            pass

        def login(self, *args) -> None:
            pass

        def sendmail(self, from_addr, to_addr, body) -> None:
            captured["body"] = body

    monkeypatch.setattr("src.notifications.email_renderer.smtplib.SMTP", FakeSMTP)

    EmailRenderer.send_email(
        alert_trends=[_trend("Flaky CI surge", "qa_testing")],
        all_trends=[],
        articles=[],
        report_path=None,
    )

    assert "body" in captured
    assert "Quality Managers in AI World" in captured["body"]


def _digest_article(i: int):
    return SimpleNamespace(
        title=f"Digest Article {i}",
        url=f"https://example.com/d-{i}",
        category="qa_testing",
        keywords=["kw1", "kw2", "kw3"],
        relevance_score=70 - i,
        published_date="01 May 2026",
        collected_date="02 May 2026",
    )


def _digest_stats():
    return SimpleNamespace(
        date_str="01 May 2026",
        total_articles=2,
        avg_relevance=60.0,
        alert_count=1,
        category_counts={"qa_testing": 2},
        top_keywords=[("testing", 5), ("genai", 3)],
    )


def test_send_digest_email_builds_and_sends(monkeypatch) -> None:
    monkeypatch.setattr(_settings, "smtp_user", "from@example.com", raising=False)
    monkeypatch.setattr(_settings, "smtp_password", "pw", raising=False)
    monkeypatch.setattr(_settings, "notify_email", "to@example.com", raising=False)
    monkeypatch.setattr(_settings, "smtp_host", "smtp.example.com", raising=False)
    monkeypatch.setattr(_settings, "smtp_port", 587, raising=False)

    captured: dict[str, str] = {}

    class FakeSMTP:
        def __init__(self, *a, **k) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a) -> bool:
            return False

        def ehlo(self) -> None:
            pass

        def starttls(self) -> None:
            pass

        def login(self, *a) -> None:
            pass

        def sendmail(self, frm, to, body) -> None:
            captured["body"] = body

    monkeypatch.setattr("src.notifications.email_renderer.smtplib.SMTP", FakeSMTP)

    EmailRenderer.send_digest_email(
        [_digest_article(1), _digest_article(2)],
        _digest_stats(),
        [_trend("Flaky CI surge", "qa_testing")],
        None,
    )

    # The HTML body is base64-encoded inside the MIME message; assert on the
    # plaintext headers and that a non-trivial message was handed to sendmail.
    assert "body" in captured
    assert "Quality Managers in AI World" in captured["body"]  # plaintext From header
    assert len(captured["body"]) > 500


def test_send_slack_posts_message(monkeypatch) -> None:
    import slack_sdk

    monkeypatch.setattr(_settings, "slack_bot_token", "xoxb-test", raising=False)
    monkeypatch.setattr(_settings, "slack_channel", "#qa", raising=False)

    posted: dict[str, object] = {}

    class FakeWebClient:
        def __init__(self, token=None) -> None:
            posted["token"] = token

        def chat_postMessage(self, channel, blocks, text):
            posted["channel"] = channel
            posted["blocks"] = blocks

    monkeypatch.setattr(slack_sdk, "WebClient", FakeWebClient)

    from src.notifications.slack_notifier import SlackNotifier

    SlackNotifier.send_slack([_trend("Flaky CI surge", "qa_testing")], None)

    assert posted["channel"] == "#qa"
    assert isinstance(posted["blocks"], list) and posted["blocks"]
