"""Shared pytest fixtures."""

import pytest


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    """Point every test at a fresh SQLite file via `FINALLY_DB_PATH`."""
    path = tmp_path / "finally.db"
    monkeypatch.setenv("FINALLY_DB_PATH", str(path))
    return path


@pytest.fixture
def conn(temp_db):
    """An open connection to the temp database, closed after the test."""
    from db.database import get_connection

    connection = get_connection()
    yield connection
    connection.close()
