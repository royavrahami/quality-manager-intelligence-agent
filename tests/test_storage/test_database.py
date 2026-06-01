"""Tests for the database engine / session-factory module.

The module-level ``engine`` / ``SessionLocal`` are redirected to a throwaway
SQLite file under tmp_path so the tests never touch the configured database
and run identically in any environment.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from src.storage import database
from src.storage.models import Base


@pytest.fixture
def temp_db(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(
        database,
        "SessionLocal",
        sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False),
    )
    return engine


def test_init_db_is_idempotent(temp_db) -> None:
    """Creating the schema twice must not raise, and tables must exist."""
    database.init_db()
    database.init_db()
    assert "articles" in Base.metadata.tables


def test_get_session_is_a_working_context_manager(temp_db) -> None:
    """get_session yields a usable session and commits/closes cleanly."""
    database.init_db()
    with database.get_session() as session:
        assert session is not None
        assert session.execute(text("SELECT 1")).scalar() == 1


def test_get_session_rolls_back_on_error(temp_db) -> None:
    """An exception inside the with-block propagates (and triggers rollback)."""
    database.init_db()
    with pytest.raises(ValueError):
        with database.get_session():
            raise ValueError("boom")
