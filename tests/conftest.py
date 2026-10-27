"""
conftest.py — Pytest configuration for PreTwinShop AI test suite.

Fixtures
--------
app_client   : Flask test client using an in-memory SQLite database
test_db      : Raw sqlite3 connection to the in-memory test database
demo_user_id : Returns 1 (the seeded demo user's primary key)

Helper functions
----------------
create_test_product(db, **kwargs)  : Insert a product row; returns its id
create_test_purchase(db, **kwargs) : Insert a purchase_history row; returns id
"""

from __future__ import annotations

import json
import sqlite3
import sys
import os
import tempfile
from typing import Generator

import pytest

# ---------------------------------------------------------------------------
# Make the project root importable from tests/
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ---------------------------------------------------------------------------
# Helper: build an in-memory database schema
# ---------------------------------------------------------------------------

_DDL = """
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT DEFAULT '',
    google_id TEXT DEFAULT '',
    avatar_url TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS shopping_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    preferred_categories TEXT DEFAULT '[]',
    budget_min REAL DEFAULT 0.0,
    budget_max REAL DEFAULT 10000.0,
    preferred_brands TEXT DEFAULT '[]',
    product_requirements TEXT DEFAULT '{}',
    shopping_frequency TEXT DEFAULT 'monthly',
    shopping_goals TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS purchase_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    product_id INTEGER,
    product_name TEXT NOT NULL,
    category TEXT,
    brand TEXT,
    price REAL,
    purchase_date DATE,
    quantity INTEGER DEFAULT 1,
    notes TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    subcategory TEXT DEFAULT '',
    brand TEXT,
    price REAL NOT NULL,
    discount_percentage INTEGER DEFAULT 10,
    review_count_demo INTEGER DEFAULT 120,
    featured INTEGER DEFAULT 0,
    specifications TEXT DEFAULT '{}',
    description TEXT DEFAULT '',
    image_url TEXT DEFAULT '',
    source_type TEXT DEFAULT 'demo',
    rating REAL DEFAULT 4.0,
    stock INTEGER DEFAULT 100,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS shopping_goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    goal_title TEXT NOT NULL,
    goal_description TEXT DEFAULT '',
    target_date DATE,
    budget REAL DEFAULT 0.0,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    run_id TEXT,
    predicted_category TEXT,
    predicted_product TEXT,
    reason TEXT DEFAULT '',
    supporting_evidence TEXT DEFAULT '[]',
    estimated_timeframe TEXT DEFAULT '',
    confidence_score REAL DEFAULT 0.0,
    confidence_label TEXT DEFAULT '',
    recommended_action TEXT DEFAULT '',
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    run_id TEXT,
    product_id INTEGER,
    product_name TEXT,
    category TEXT,
    price REAL,
    rank INTEGER DEFAULT 1,
    score REAL DEFAULT 0.0,
    reason TEXT DEFAULT '',
    budget_fit TEXT DEFAULT '',
    alternatives TEXT DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS product_comparisons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    run_id TEXT,
    product_ids TEXT DEFAULT '[]',
    comparison_data TEXT DEFAULT '{}',
    winner_id INTEGER,
    winner_reason TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS agent_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    run_id TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    task TEXT DEFAULT '',
    status TEXT DEFAULT 'pending',
    input_summary TEXT DEFAULT '',
    output_summary TEXT DEFAULT '',
    execution_time_ms INTEGER DEFAULT 0,
    error_message TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS user_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    item_type TEXT NOT NULL,
    item_id INTEGER,
    feedback_type TEXT NOT NULL,
    rating INTEGER,
    comment TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    order_number TEXT NOT NULL UNIQUE,
    total_amount REAL NOT NULL,
    discount_amount REAL DEFAULT 0.0,
    shipping_amount REAL DEFAULT 0.0,
    reward_points_redeemed INTEGER DEFAULT 0,
    payment_method TEXT DEFAULT 'ONLINE',
    payment_status TEXT DEFAULT 'pending',
    shipping_address TEXT DEFAULT '',
    status TEXT DEFAULT 'placed',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    product_id INTEGER,
    product_name TEXT,
    price REAL NOT NULL,
    quantity INTEGER DEFAULT 1,
    image_url TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cart_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS savings_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    plan_name TEXT NOT NULL,
    target_amount REAL NOT NULL,
    current_amount REAL DEFAULT 0.0,
    duration_days INTEGER DEFAULT 30,
    start_date DATE,
    target_date DATE,
    daily_target REAL DEFAULT 0.0,
    weekly_target REAL DEFAULT 0.0,
    status TEXT DEFAULT 'active',
    category TEXT DEFAULT 'General',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS savings_contributions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    contribution_date DATE,
    notes TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reward_ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    points INTEGER NOT NULL,
    reason TEXT DEFAULT '',
    source_type TEXT DEFAULT 'earned',
    order_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    meta_data TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS household_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    profile_name TEXT NOT NULL,
    relationship TEXT DEFAULT 'Self',
    avatar_initials TEXT DEFAULT 'AJ',
    avatar_color TEXT DEFAULT '#8b5cf6',
    lifestyle_type TEXT DEFAULT 'Standard',
    shopping_personality TEXT DEFAULT 'Value Seeker',
    preferred_categories TEXT DEFAULT '[]',
    budget_max REAL DEFAULT 15000.0,
    notes TEXT DEFAULT '',
    is_active INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tracked_products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    target_price REAL NOT NULL,
    alert_active INTEGER DEFAULT 1,
    last_checked_price REAL DEFAULT 0.0,
    last_notified_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    price REAL NOT NULL,
    recorded_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS shopping_reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    category TEXT DEFAULT 'Everyday Consumables',
    estimated_cycle_days INTEGER DEFAULT 30,
    next_reminder_date DATE NOT NULL,
    last_purchased_date DATE,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS shopping_calendar_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    event_date DATE NOT NULL,
    event_type TEXT DEFAULT 'Birthday',
    category TEXT DEFAULT 'All',
    budget REAL DEFAULT 2000.0,
    notes TEXT DEFAULT '',
    suggested_products TEXT DEFAULT '[]',
    status TEXT DEFAULT 'upcoming',
    is_ai_predicted INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS shopping_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    task_name TEXT NOT NULL,
    goal_description TEXT DEFAULT '',
    budget_limit REAL DEFAULT 0.0,
    status TEXT DEFAULT 'awaiting_approval',
    steps_json TEXT DEFAULT '[]',
    results_json TEXT DEFAULT '[]',
    requires_approval INTEGER DEFAULT 1,
    approved_by_user INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS wishlist_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    UNIQUE(user_id, product_id)
);
"""

_SEED_USER = """
INSERT INTO users (id, username, email, password_hash) VALUES (1, 'demo_user', 'demo@pretwinshop.ai', 'scrypt:32768:8:1$f9g8$13e2f5b49b29cb11b151');
"""

_SEED_PREFS = """
INSERT INTO shopping_preferences
    (user_id, preferred_categories, budget_min, budget_max, preferred_brands,
     shopping_frequency)
VALUES
    (1, '["Electronics","Clothing"]', 50.0, 2000.0, '["Sony","Nike"]', 'monthly');
"""

_SEED_PRODUCTS = [
    ("Sony WH-1000XM5 Headphones", "Electronics", "Sony", 349.99, 4.8),
    ("Nike Air Max 270", "Clothing", "Nike", 129.99, 4.5),
    ("Apple AirPods Pro", "Electronics", "Apple", 249.99, 4.7),
    ("Adidas Ultraboost 22", "Clothing", "Adidas", 189.99, 4.6),
    ("Samsung Galaxy Watch 5", "Electronics", "Samsung", 279.99, 4.4),
]


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_DDL)
    # Check if user already exists
    cur = conn.execute("SELECT id FROM users WHERE id = 1")
    if not cur.fetchone():
        conn.execute(_SEED_USER)
    cur = conn.execute("SELECT id FROM shopping_preferences WHERE user_id = 1")
    if not cur.fetchone():
        conn.execute(_SEED_PREFS)
    try:
        conn.execute("INSERT OR IGNORE INTO user_reward_points (user_id, total_points, lifetime_earned, lifetime_redeemed) VALUES (1, 100, 100, 0)")
    except Exception:
        pass
    cur = conn.execute("SELECT COUNT(*) FROM products")
    if cur.fetchone()[0] == 0:
        for name, cat, brand, price, rating in _SEED_PRODUCTS:
            conn.execute(
                "INSERT INTO products (name, category, brand, price, rating) VALUES (?,?,?,?,?)",
                (name, cat, brand, price, rating),
            )
    conn.commit()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def test_db() -> Generator[sqlite3.Connection, None, None]:
    """
    Yields a fresh in-memory sqlite3 connection with schema + seed data.
    The connection uses Row factory for dict-like access.
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    _create_schema(conn)
    yield conn
    conn.close()


@pytest.fixture(scope="function")
def app_client(tmp_path, monkeypatch):
    """
    Flask test client backed by a temporary file-based SQLite database
    so that Flask's request-scoped DB helpers (which re-open connections)
    all point to the same seeded file.
    """
    db_file = str(tmp_path / "test_pretwinshop.db")

    # Patch environment BEFORE importing app / config so the DB path is correct
    monkeypatch.setenv("DATABASE_PATH", db_file)
    monkeypatch.setenv("OPENAI_API_KEY", "")     # disable LLM calls in tests
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")

    # Reload config so Config.DATABASE_PATH picks up the env var
    import importlib
    import config as cfg_module
    importlib.reload(cfg_module)

    # Build schema in the temp file
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    _create_schema(conn)
    conn.close()

    # Now import and create the Flask app
    try:
        import app as app_module
        importlib.reload(app_module)
        flask_app = app_module.app
    except ImportError:
        # app.py not yet created — create a minimal stub so tests can import
        pytest.skip("app.py not yet available")
        return

    flask_app.config["TESTING"] = True
    flask_app.config["SECRET_KEY"] = "test-secret-key"

    with flask_app.test_client() as client:
        yield client


@pytest.fixture
def demo_user_id() -> int:
    """Return the primary key of the seeded demo user."""
    return 1


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def create_test_product(
    db: sqlite3.Connection,
    name: str = "Test Product",
    category: str = "Electronics",
    brand: str = "TestBrand",
    price: float = 99.99,
    rating: float = 4.0,
    stock: int = 100,
    description: str = "A test product",
    specifications: dict | None = None,
) -> int:
    """Insert a product row into *db* and return its lastrowid."""
    specs = json.dumps(specifications or {})
    cur = db.execute(
        """INSERT INTO products
               (name, category, brand, price, rating, stock, description, specifications)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (name, category, brand, price, rating, stock, description, specs),
    )
    db.commit()
    return cur.lastrowid


def create_test_purchase(
    db: sqlite3.Connection,
    user_id: int = 1,
    product_name: str = "Test Purchase",
    category: str = "Electronics",
    brand: str = "TestBrand",
    price: float = 99.99,
    purchase_date: str = "2024-01-15",
    quantity: int = 1,
    product_id: int | None = None,
) -> int:
    """Insert a purchase_history row and return its lastrowid."""
    cur = db.execute(
        """INSERT INTO purchase_history
               (user_id, product_id, product_name, category, brand,
                price, purchase_date, quantity)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, product_id, product_name, category, brand,
         price, purchase_date, quantity),
    )
    db.commit()
    return cur.lastrowid
