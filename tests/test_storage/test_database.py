"""Tests for the database engine / session-factory module."""

from __future__ import annotations

from sqlalchemy import text

from src.storage import database


def test_init_db_is_idempotent() -> None:
    """Creating the schema twice must not raise."""
    database.init_db()
    database.init_db()


def test_get_session_is_a_working_context_manager() -> None:
    """get_session yields a usable session and commits/closes cleanly."""
    with database.get_session() as session:
        assert session is not None
        result = session.execute(text("SELECT 1")).scalar()
        assert result == 1


def test_get_session_rolls_back_on_error() -> None:
    """An exception inside the with-block propagates (and triggers rollback)."""
    raised = False
    try:
        with database.get_session():
            raise ValueError("boom")
    except ValueError:
        raised = True
    assert raised
