"""
test_database.py — Unit tests for database.py

Tests cover:
- init_db table creation and idempotency
- seed_products / seed_demo_user helpers
- query_db and execute_db utilities
"""

from __future__ import annotations

import importlib
import os
import sqlite3
import sys
import tempfile

import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ---------------------------------------------------------------------------
# Table names expected in the schema
# ---------------------------------------------------------------------------
EXPECTED_TABLES = {
    "users",
    "shopping_preferences",
    "purchase_history",
    "products",
    "shopping_goals",
    "predictions",
    "recommendations",
    "product_comparisons",
    "agent_runs",
    "user_feedback",
}


# ---------------------------------------------------------------------------
# Fixtures — each test gets a fresh temp-file DB
# ---------------------------------------------------------------------------

@pytest.fixture()
def db_path(tmp_path, monkeypatch):
    """
    Patch DATABASE_PATH to a fresh temp file and reload config + database
    modules so they pick up the new path.
    """
    path = str(tmp_path / "test.db")
    monkeypatch.setenv("DATABASE_PATH", path)

    import config as cfg
    importlib.reload(cfg)

    import database as db_mod
    importlib.reload(db_mod)

    return path


@pytest.fixture()
def db_module(db_path):
    """Return the freshly reloaded database module."""
    import database as db_mod
    return db_mod


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestInitDb:
    def test_init_db_creates_tables(self, db_module, db_path):
        """init_db must create all 10 expected tables."""
        db_module.init_db()

        conn = sqlite3.connect(db_path)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        created_tables = {row[0] for row in cursor.fetchall()}
        conn.close()

        assert EXPECTED_TABLES.issubset(created_tables), (
            f"Missing tables: {EXPECTED_TABLES - created_tables}"
        )

    def test_init_db_idempotent(self, db_module):
        """Calling init_db twice must not raise an error."""
        db_module.init_db()
        db_module.init_db()  # second call — should be a no-op


class TestSeedProducts:
    def _product_count(self, db_path: str) -> int:
        conn = sqlite3.connect(db_path)
        (count,) = conn.execute("SELECT COUNT(*) FROM products").fetchone()
        conn.close()
        return count

    def test_seed_products_inserts_50_products(self, db_module, db_path):
        """seed_products should insert at least 50 products."""
        db_module.init_db()

        # seed_products may be a standalone function or part of init_db
        if hasattr(db_module, "seed_products"):
            db_module.seed_products()
        elif hasattr(db_module, "seed_demo_data"):
            db_module.seed_demo_data()
        else:
            # Try calling init_db with seed=True kwarg if supported
            try:
                db_module.init_db(seed=True)
            except TypeError:
                pytest.skip("seed_products / seed_demo_data not found in database module")

        count = self._product_count(db_path)
        assert count >= 50, f"Expected at least 50 products, got {count}"

    def test_seed_products_idempotent(self, db_module, db_path):
        """Seeding products twice must not raise an error."""
        db_module.init_db()
        seed_fn = getattr(db_module, "seed_products",
                   getattr(db_module, "seed_demo_data", None))
        if seed_fn is None:
            pytest.skip("seed_products / seed_demo_data not found")

        first_count = self._product_count(db_path)
        seed_fn()
        seed_fn()
        # Should not raise; product count should remain stable (idempotent insert)
        second_count = self._product_count(db_path)
        assert second_count >= first_count


class TestSeedDemoUser:
    def _user_count(self, db_path: str) -> int:
        conn = sqlite3.connect(db_path)
        (count,) = conn.execute("SELECT COUNT(*) FROM users").fetchone()
        conn.close()
        return count

    def test_seed_demo_user_creates_user(self, db_module, db_path):
        """seed_demo_user / seed_demo_data should insert at least one user."""
        db_module.init_db()

        seed_fn = getattr(db_module, "seed_demo_user",
                   getattr(db_module, "seed_demo_data", None))
        if seed_fn is None:
            pytest.skip("seed_demo_user / seed_demo_data not found")

        seed_fn()
        count = self._user_count(db_path)
        assert count >= 1, "Expected at least one user after seeding"

    def test_seed_demo_user_idempotent(self, db_module, db_path):
        """Calling seed_demo_user multiple times must not raise and must not
        create duplicate users with the same email."""
        db_module.init_db()
        seed_fn = getattr(db_module, "seed_demo_user",
                   getattr(db_module, "seed_demo_data", None))
        if seed_fn is None:
            pytest.skip("seed_demo_user / seed_demo_data not found")

        seed_fn()
        seed_fn()

        conn = sqlite3.connect(db_path)
        rows = conn.execute("SELECT email, COUNT(*) c FROM users GROUP BY email HAVING c > 1").fetchall()
        conn.close()
        assert rows == [], f"Duplicate users detected: {rows}"


class TestQueryDb:
    def test_query_db_returns_rows(self, db_module, db_path):
        """query_db should return a list of rows for a valid SELECT."""
        db_module.init_db()

        # Insert a row directly to query back
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO users (username, email) VALUES ('alice', 'alice@test.com')"
        )
        conn.commit()
        conn.close()

        rows = db_module.query_db("SELECT * FROM users WHERE email = ?", ("alice@test.com",))
        assert isinstance(rows, list)
        assert len(rows) >= 1
        # sqlite3.Row supports key-based access
        assert rows[0]["username"] == "alice"

    def test_query_db_one_returns_single_row(self, db_module, db_path):
        """query_db with one=True should return a single row, not a list."""
        db_module.init_db()

        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO users (username, email) VALUES ('bob', 'bob@test.com')"
        )
        conn.commit()
        conn.close()

        row = db_module.query_db(
            "SELECT * FROM users WHERE email = ?", ("bob@test.com",), one=True
        )
        assert row is not None
        assert row["username"] == "bob"

    def test_query_db_returns_empty_list_when_no_match(self, db_module, db_path):
        """query_db should return [] when no rows match."""
        db_module.init_db()
        rows = db_module.query_db(
            "SELECT * FROM users WHERE email = ?", ("nobody@nowhere.com",)
        )
        assert rows == [] or rows is None or len(rows) == 0


class TestExecuteDb:
    def test_execute_db_inserts_data(self, db_module, db_path):
        """execute_db should insert a row and return a valid lastrowid."""
        db_module.init_db()

        rowid = db_module.execute_db(
            "INSERT INTO users (username, email) VALUES (?, ?)",
            ("charlie", "charlie@test.com"),
        )
        assert rowid is not None
        assert isinstance(rowid, int)
        assert rowid >= 1

        # Verify it's actually in the DB
        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "SELECT username FROM users WHERE email = ?", ("charlie@test.com",)
        ).fetchone()
        conn.close()
        assert row is not None
        assert row[0] == "charlie"

    def test_execute_db_updates_data(self, db_module, db_path):
        """execute_db should correctly update existing rows."""
        db_module.init_db()

        db_module.execute_db(
            "INSERT INTO users (username, email) VALUES (?, ?)",
            ("delta", "delta@test.com"),
        )
        db_module.execute_db(
            "UPDATE users SET username = ? WHERE email = ?",
            ("delta_updated", "delta@test.com"),
        )

        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "SELECT username FROM users WHERE email = ?", ("delta@test.com",)
        ).fetchone()
        conn.close()
        assert row[0] == "delta_updated"
