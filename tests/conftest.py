"""Shared fixtures: every test runs against an empty schema "nutrition" in a throwaway
database, at a fixed 'now' (Tuesday 2026-10-13, 08:15 in Vienna).

The database comes from TEST_DATABASE_URL (default: the local test container, see README);
tests are skipped when it is not reachable. Never point it at the real database - every test
drops the schema.
"""
import datetime as dt
import os

import psycopg
import pytest

import config
import days
import db

TEST_URL = os.getenv("TEST_DATABASE_URL", "postgresql://postgres:test@127.0.0.1:55432/test")
NOW = dt.datetime(2026, 10, 13, 8, 15, tzinfo=config.TIMEZONE)


@pytest.fixture(autouse=True)
def fresh_schema(monkeypatch):
    """Point the server at the test database, recreate the schema and freeze 'now'."""
    try:
        with psycopg.connect(TEST_URL, connect_timeout=3):
            pass
    except psycopg.OperationalError:
        pytest.skip(f"test database not reachable: {TEST_URL}")
    monkeypatch.setattr(config, "DATABASE_URL", TEST_URL)
    monkeypatch.setattr(days, "now", lambda: NOW)
    db.conn().execute("drop schema if exists nutrition cascade")
    db.init_schema()
    yield
    db.conn().close()
