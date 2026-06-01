"""Tests for the APScheduler wrapper (scheduler mocked — no blocking loop)."""

from __future__ import annotations


def test_scheduler_registers_job_and_starts(monkeypatch):
    calls: dict[str, object] = {}

    class FakeScheduler:
        running = False

        def __init__(self, **_kwargs) -> None:
            pass

        def add_job(self, **kwargs) -> None:
            calls["job"] = kwargs

        def start(self) -> None:
            calls["started"] = True

        def shutdown(self, **_kwargs) -> None:
            pass

    monkeypatch.setattr("src.scheduler.job_scheduler.BlockingScheduler", FakeScheduler)
    monkeypatch.setattr("src.scheduler.job_scheduler.signal.signal", lambda *_a, **_k: None)

    from src.scheduler.job_scheduler import AgentScheduler

    sched = AgentScheduler(interval_hours=6)
    assert sched._interval_hours == 6

    sched.start()

    assert calls["job"]["id"] == "qa_intelligence_agent"
    assert calls["job"]["max_instances"] == 1
    assert calls.get("started") is True


def test_scheduler_uses_settings_default_interval(monkeypatch):
    monkeypatch.setattr(
        "src.scheduler.job_scheduler.BlockingScheduler",
        lambda **_k: type("S", (), {"running": False, "shutdown": lambda *a, **k: None})(),
    )
    monkeypatch.setattr("src.scheduler.job_scheduler.signal.signal", lambda *_a, **_k: None)

    from src.config.settings import settings
    from src.scheduler.job_scheduler import AgentScheduler

    sched = AgentScheduler()
    assert sched._interval_hours == settings.schedule_interval_hours
