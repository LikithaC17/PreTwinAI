"""
seed_users.py
-------------
Seeds a demo user (ID=1) with shopping preferences, purchase history,
and shopping goals. All operations are idempotent.
"""

import json
import sys
import os
from datetime import date, timedelta
from werkzeug.security import generate_password_hash

# Allow running as a standalone script from the project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from database import get_db


def _today_minus(days: int) -> str:
    return (date.today() - timedelta(days=days)).isoformat()


def seed_demo_user() -> None:
    """
    Create the demo user and associated data.
    Safe to call multiple times (idempotent).
    """
    default_password_hash = generate_password_hash("password123")
    with get_db() as conn:
        # ------------------------------------------------------------------ #
        #  1. Create demo user
        # ------------------------------------------------------------------ #
        existing = conn.execute(
            "SELECT id, password_hash FROM users WHERE id = 1"
        ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO users (id, username, email, password_hash)
                VALUES (1, 'Alex Johnson', 'alex@demo.pretwinshop.ai', ?)
                """,
                (default_password_hash,)
            )
            print("[seed_users] Created demo user: Alex Johnson (ID=1)")
        else:
            if not existing["password_hash"]:
                conn.execute(
                    "UPDATE users SET password_hash = ? WHERE id = 1",
                    (default_password_hash,)
                )
            print("[seed_users] Demo user already exists. Skipping user creation.")

        # ------------------------------------------------------------------ #
        #  2. Shopping preferences
        # ------------------------------------------------------------------ #
        pref_exists = conn.execute(
            "SELECT id FROM shopping_preferences WHERE user_id = 1"
        ).fetchone()

        if pref_exists is None:
            conn.execute(
                """
                INSERT INTO shopping_preferences
                    (user_id, preferred_categories, budget_min, budget_max,
                     preferred_brands, product_requirements, shopping_frequency,
                     shopping_goals, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    1,
                    json.dumps(["Electronics", "Computer Accessories", "Home Essentials"]),
                    500.0,
                    5000.0,
                    json.dumps(["Sony", "Logitech", "Philips"]),
                    json.dumps({
                        "must_have_warranty": True,
                        "prefer_wireless": True,
                        "energy_efficient": True,
                    }),
                    "monthly",
                    "Build a productive home office setup",
                    "Interested in smart home devices and productivity tools. "
                    "Prefers well-reviewed brands with good after-sales support.",
                ),
            )
            print("[seed_users] Created shopping preferences for user 1.")
        else:
            print("[seed_users] Shopping preferences already exist. Skipping.")

        # ------------------------------------------------------------------ #
        #  3. Purchase history (10 records, last 6 months)
        # ------------------------------------------------------------------ #
        history_count = conn.execute(
            "SELECT COUNT(*) AS cnt FROM purchase_history WHERE user_id = 1"
        ).fetchone()["cnt"]

        if history_count == 0:
            purchases = [
                # id, product_name, category, brand, price, days_ago, qty, notes
                (None, "Logitech MX Master 3S Wireless Mouse",      "Computer Accessories", "Logitech",  99.99, 180, 1, "Great for long work sessions"),
                (None, "Sony WH-1000XM5 Wireless Headphones",       "Electronics",          "Sony",     329.99, 155, 1, "Best noise cancellation I've used"),
                (None, "Keychron K8 Pro Mechanical Keyboard",        "Computer Accessories", "Keychron", 109.00, 130, 1, "Love the tactile feel"),
                (None, "Levoit Core 300 Air Purifier",               "Home Essentials",      "Levoit",    99.99, 110, 1, "Runs quietly at night"),
                (None, "Anker 7-in-1 USB-C Hub",                    "Computer Accessories", "Anker",     39.99,  90, 1, "Essential for my MacBook"),
                (None, "Pilot G2 Retractable Premium Gel Ink Pens", "Stationery",           "Pilot",     19.99,  75, 2, "Bought for office and home"),
                (None, "Leuchtturm1917 Medium A5 Dotted Notebook",  "Stationery",           "Leuchtturm1917", 24.99, 60, 1, "Perfect for bullet journaling"),
                (None, "CeraVe Hydrating Facial Cleanser",          "Personal Care",        "CeraVe",    14.99,  45, 2, "Part of daily skincare routine"),
                (None, "Twinings Green Tea Bags (100 Count)",       "Everyday Consumables", "Twinings",  14.99,  20, 3, "Stock up every few months"),
                (None, "Hydro Flask 32 oz Wide Mouth Water Bottle", "Everyday Consumables", "Hydro Flask", 49.95, 10, 1, "Keeps water cold all day"),
            ]

            for purchase in purchases:
                _, product_name, category, brand, price, days_ago, qty, notes = purchase
                conn.execute(
                    """
                    INSERT INTO purchase_history
                        (user_id, product_name, category, brand, price,
                         purchase_date, quantity, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        1,
                        product_name,
                        category,
                        brand,
                        price,
                        _today_minus(days_ago),
                        qty,
                        notes,
                    ),
                )

            print("[seed_users] Inserted 10 purchase history records for user 1.")
        else:
            print(f"[seed_users] Purchase history already has {history_count} records. Skipping.")

        # ------------------------------------------------------------------ #
        #  4. Shopping goals (2 goals)
        # ------------------------------------------------------------------ #
        goals_count = conn.execute(
            "SELECT COUNT(*) AS cnt FROM shopping_goals WHERE user_id = 1"
        ).fetchone()["cnt"]

        if goals_count == 0:
            goals = [
                {
                    "goal_title": "Complete Home Office Setup",
                    "goal_description": (
                        "Upgrade my home office with a 4K monitor, ergonomic chair, "
                        "better webcam, and cable management solutions."
                    ),
                    "target_date": (date.today() + timedelta(days=60)).isoformat(),
                    "budget": 1500.0,
                    "status": "active",
                },
                {
                    "goal_title": "Smart Home Starter Kit",
                    "goal_description": (
                        "Set up smart lighting (Philips Hue), a smart speaker, "
                        "and a robot vacuum for home automation."
                    ),
                    "target_date": (date.today() + timedelta(days=120)).isoformat(),
                    "budget": 800.0,
                    "status": "active",
                },
            ]

            for goal in goals:
                conn.execute(
                    """
                    INSERT INTO shopping_goals
                        (user_id, goal_title, goal_description, target_date, budget, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        1,
                        goal["goal_title"],
                        goal["goal_description"],
                        goal["target_date"],
                        goal["budget"],
                        goal["status"],
                    ),
                )

            print("[seed_users] Created 2 shopping goals for user 1.")
        else:
            print(f"[seed_users] Shopping goals already has {goals_count} records. Skipping.")

        conn.commit()
        print("[seed_users] Demo user seeding complete.")


if __name__ == "__main__":
    from database import init_db
    init_db()
    seed_demo_user()
