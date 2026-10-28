import sqlite3
import os
from contextlib import contextmanager
import config
from config import Config


def init_db():
    """Initialize the database by creating all tables if they don't exist."""
    db_path = config.Config.DATABASE_PATH
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Enable WAL mode for better concurrency
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")

    # --- users ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Safe migration: ensure password_hash, google_id, avatar_url, and profile columns exist on existing users table
    for ucol, utype in [
        ("password_hash", "TEXT DEFAULT ''"),
        ("google_id", "TEXT DEFAULT ''"),
        ("avatar_url", "TEXT DEFAULT ''"),
        ("phone", "TEXT DEFAULT ''"),
        ("address", "TEXT DEFAULT ''"),
        ("city", "TEXT DEFAULT ''"),
        ("state", "TEXT DEFAULT ''"),
        ("pincode", "TEXT DEFAULT ''"),
        ("preferred_payment_mode", "TEXT DEFAULT 'cod'"),
    ]:
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {ucol} {utype}")
        except Exception:
            pass

    # --- shopping_preferences ---
    cursor.execute("""
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
        )
    """)

    # --- purchase_history ---
    cursor.execute("""
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
        )
    """)

    # --- products ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            subcategory TEXT DEFAULT '',
            brand TEXT,
            price REAL NOT NULL,
            discount_percentage INTEGER DEFAULT 20,
            specifications TEXT DEFAULT '{}',
            description TEXT DEFAULT '',
            image_url TEXT DEFAULT '',
            source_type TEXT DEFAULT 'demo',
            rating REAL DEFAULT 4.0,
            review_count_demo INTEGER DEFAULT 120,
            stock INTEGER DEFAULT 100,
            featured INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Ensure optional new columns exist on existing table
    for col, col_type in [
        ("subcategory", "TEXT DEFAULT ''"),
        ("discount_percentage", "INTEGER DEFAULT 20"),
        ("review_count_demo", "INTEGER DEFAULT 120"),
        ("featured", "INTEGER DEFAULT 0"),
        ("source_id", "TEXT DEFAULT ''"),
        ("attributes", "TEXT DEFAULT '{}'"),
        ("external_url", "TEXT DEFAULT ''"),
        ("availability", "TEXT DEFAULT 'in_stock'"),
        ("data_origin", "TEXT DEFAULT 'catalog'"),
        ("last_synced_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
    ]:
        try:
            cursor.execute(f"ALTER TABLE products ADD COLUMN {col} {col_type}")
        except Exception:
            pass

    # Performance indexes for large-scale product catalog
    for idx_sql in [
        "CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);",
        "CREATE INDEX IF NOT EXISTS idx_products_subcategory ON products(subcategory);",
        "CREATE INDEX IF NOT EXISTS idx_products_brand ON products(brand);",
        "CREATE INDEX IF NOT EXISTS idx_products_price ON products(price);",
        "CREATE INDEX IF NOT EXISTS idx_products_rating ON products(rating);",
        "CREATE INDEX IF NOT EXISTS idx_products_source ON products(source_type, source_id);",
        "CREATE INDEX IF NOT EXISTS idx_products_name ON products(name);",
        "CREATE INDEX IF NOT EXISTS idx_products_avail ON products(availability);",
    ]:
        try:
            cursor.execute(idx_sql)
        except Exception:
            pass

    # --- shopping_goals ---
    cursor.execute("""
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
        )
    """)

    # --- predictions ---
    cursor.execute("""
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
        )
    """)

    # --- recommendations ---
    cursor.execute("""
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
        )
    """)

    # --- product_comparisons ---
    cursor.execute("""
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
        )
    """)

    # --- agent_runs ---
    cursor.execute("""
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
        )
    """)

    # --- user_feedback ---
    cursor.execute("""
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
        )
    """)

    # --- orders ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number TEXT NOT NULL UNIQUE,
            user_id INTEGER NOT NULL,
            customer_name TEXT NOT NULL,
            customer_email TEXT NOT NULL,
            customer_phone TEXT DEFAULT '',
            shipping_address TEXT NOT NULL,
            city TEXT NOT NULL,
            state TEXT NOT NULL,
            pincode TEXT NOT NULL,
            subtotal REAL NOT NULL,
            tax REAL DEFAULT 0.0,
            shipping_fee REAL DEFAULT 0.0,
            discount REAL DEFAULT 0.0,
            total_amount REAL NOT NULL,
            status TEXT DEFAULT 'Confirmed',
            payment_status TEXT DEFAULT 'Pending',
            payment_method TEXT DEFAULT 'Razorpay',
            gateway_name TEXT DEFAULT 'Razorpay',
            gateway_order_id TEXT DEFAULT '',
            gateway_payment_id TEXT DEFAULT '',
            gateway_signature TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # --- order_items ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            category TEXT DEFAULT '',
            brand TEXT DEFAULT '',
            price REAL NOT NULL,
            quantity INTEGER DEFAULT 1,
            total_price REAL NOT NULL,
            image_url TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL
        )
    """)

    # --- cart_items ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cart_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
            UNIQUE(user_id, product_id)
        )
    """)

    # Safe migration: ensure new COD and rewards columns exist on existing orders table
    for col, col_type in [
        ("reward_points_redeemed", "INTEGER DEFAULT 0"),
        ("reward_discount_amount", "REAL DEFAULT 0.0"),
        ("reward_points_awarded", "INTEGER DEFAULT 0"),
        ("cod_amount_due", "REAL DEFAULT 0.0"),
    ]:
        try:
            cursor.execute(f"ALTER TABLE orders ADD COLUMN {col} {col_type}")
        except Exception:
            pass

    # --- savings_plans ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS savings_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER,
            goal_title TEXT NOT NULL,
            target_amount REAL NOT NULL,
            current_saved REAL DEFAULT 0.0,
            target_date DATE NOT NULL,
            contribution_cadence TEXT DEFAULT 'daily',
            status TEXT DEFAULT 'active',
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL
        )
    """)

    # --- savings_contributions ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS savings_contributions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            contribution_date DATE NOT NULL,
            note TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (plan_id) REFERENCES savings_plans(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # --- reward_ledger ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reward_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            points INTEGER NOT NULL,
            rupee_value REAL NOT NULL,
            transaction_type TEXT NOT NULL,
            order_id INTEGER,
            description TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE SET NULL
        )
    """)

    # --- chat_messages ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            meta_data TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # --- household_profiles (Feature 1: Multi-Profile Support) ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS household_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            profile_name TEXT NOT NULL,
            relationship TEXT DEFAULT 'Self',
            avatar_initials TEXT DEFAULT 'AJ',
            avatar_color TEXT DEFAULT '#7c3aed',
            lifestyle_type TEXT DEFAULT 'Work & Productivity',
            shopping_personality TEXT DEFAULT 'Value Focused',
            preferred_categories TEXT DEFAULT '["Electronics", "Laptops & Computers"]',
            budget_max REAL DEFAULT 15000.0,
            notes TEXT DEFAULT '',
            is_active INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # --- tracked_products (Feature 4: Price Drop Alerts) ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tracked_products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            target_price REAL NOT NULL,
            alert_active INTEGER DEFAULT 1,
            last_checked_price REAL,
            last_notified_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
        )
    """)

    # --- price_history (Feature 4: Historical Price Tracking) ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            price REAL NOT NULL,
            recorded_date DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
        )
    """)

    # --- shopping_reminders (Feature 2: Smart Replenishment Reminders) ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shopping_reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            estimated_cycle_days INTEGER DEFAULT 30,
            next_reminder_date DATE NOT NULL,
            last_purchased_date DATE,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # --- shopping_calendar_events (Future Predictive Calendar) ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shopping_calendar_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            event_date DATE NOT NULL,
            event_type TEXT DEFAULT 'personal',
            category TEXT DEFAULT 'All',
            budget REAL DEFAULT 5000.0,
            notes TEXT DEFAULT '',
            suggested_products TEXT DEFAULT '[]',
            status TEXT DEFAULT 'upcoming',
            is_ai_predicted INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # Safe migration for calendar table columns
    for ccol, ctype in [
        ("category", "TEXT DEFAULT 'All'"),
        ("notes", "TEXT DEFAULT ''"),
        ("is_ai_predicted", "INTEGER DEFAULT 0"),
    ]:
        try:
            cursor.execute(f"ALTER TABLE shopping_calendar_events ADD COLUMN {ccol} {ctype}")
        except Exception:
            pass

    # --- shopping_tasks (Feature 6: Shopping Task Planner & Autonomous Research) ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shopping_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            task_name TEXT NOT NULL,
            goal_description TEXT,
            budget_limit REAL DEFAULT 0.0,
            status TEXT DEFAULT 'pending',
            steps_json TEXT DEFAULT '[]',
            results_json TEXT DEFAULT '{}',
            requires_approval INTEGER DEFAULT 1,
            approved_by_user INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # --- wishlist_items ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wishlist_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
            UNIQUE(user_id, product_id)
        )
    """)

    conn.commit()
    conn.close()
    print(f"[database] Database initialized at: {os.path.abspath(db_path)}")


@contextmanager
def get_db():
    """Context manager that yields a sqlite3 connection with Row factory."""
    conn = sqlite3.connect(config.Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def query_db(sql: str, args: tuple = (), one: bool = False):
    """
    Execute a SELECT query and return results.

    Args:
        sql:  SQL query string with ? placeholders.
        args: Tuple of parameters to bind.
        one:  If True, return a single row; otherwise return a list of rows.

    Returns:
        A single sqlite3.Row (or None) when one=True, else a list of Rows.
    """
    with get_db() as conn:
        cursor = conn.execute(sql, args)
        rows = cursor.fetchall()
        return (rows[0] if rows else None) if one else rows


def execute_db(sql: str, args: tuple = ()):
    """
    Execute an INSERT / UPDATE / DELETE statement.

    Args:
        sql:  SQL statement with ? placeholders.
        args: Tuple of parameters to bind.

    Returns:
        The lastrowid of the executed statement.
    """
    with get_db() as conn:
        cursor = conn.execute(sql, args)
        conn.commit()
        return cursor.lastrowid


def seed_products():
    from data.seed_products import seed_products as _sp
    return _sp()

def seed_demo_user():
    from data.seed_users import seed_demo_user as _su
    return _su()

def seed_demo_data():
    seed_products()
    seed_demo_user()
