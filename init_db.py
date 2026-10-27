"""
init_db.py
----------
Database initialisation script for PreTwinShop AI.

Usage:
    python init_db.py

This script:
    1. Creates all database tables (if not already present)
    2. Seeds 50 demo products across 7 categories
    3. Seeds the demo user (Alex Johnson, ID=1) with preferences,
       purchase history, and shopping goals
"""

import sys
import os

# Ensure the project root is on the path when run directly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import init_db
from data.seed_products import seed_products
from data.seed_users import seed_demo_user


def main() -> None:
    print("=" * 55)
    print("  PreTwinShop AI - Database Initialisation")
    print("=" * 55)

    # Step 1: Create tables
    print("\n[Step 1] Initialising database schema...")
    init_db()

    # Step 2: Seed products
    print("\n[Step 2] Seeding product catalogue...")
    products_inserted = seed_products()
    if products_inserted > 0:
        print(f"          [OK] {products_inserted} products added to catalogue.")
    else:
        print("          [OK] Product catalogue already populated.")

    # Step 3: Seed demo user
    print("\n[Step 3] Seeding demo user data...")
    seed_demo_user()

    print("\n" + "=" * 55)
    print("  [DONE] Database initialisation complete!")
    print("=" * 55)


if __name__ == "__main__":
    main()
