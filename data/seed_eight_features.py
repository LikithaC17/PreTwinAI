"""
data/seed_eight_features.py
Seeds realistic data for the 8 Intelligent AI Shopping Features.
"""

import os
import sys
import json

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import database

def seed_eight_features():
    user_id = 1

    # 1. Household Profiles
    count_hp = database.query_db('SELECT COUNT(*) as c FROM household_profiles', one=True)['c']
    if count_hp == 0:
        database.execute_db("""
            INSERT INTO household_profiles 
                (user_id, profile_name, relationship, avatar_initials, avatar_color, lifestyle_type, shopping_personality, preferred_categories, budget_max, notes, is_active)
            VALUES 
                (?, 'Alex Johnson (Primary)', 'Self', 'AJ', '#7c3aed', 'Work & Productivity', 'Value Focused', ?, 25000.0, 'Prefers reliable tech, gadgets, and everyday productivity essentials', 1)
        """, (user_id, json.dumps(["Electronics", "Laptops & Computers", "Fashion"])))

        database.execute_db("""
            INSERT INTO household_profiles 
                (user_id, profile_name, relationship, avatar_initials, avatar_color, lifestyle_type, shopping_personality, preferred_categories, budget_max, notes, is_active)
            VALUES 
                (?, 'Home & Living Twin', 'Household', 'HL', '#059669', 'Home & Living', 'Quality Focused', ?, 12000.0, 'Curates sustainable kitchen essentials and living room upgrades', 0)
        """, (user_id, json.dumps(["Home & Kitchen", "Appliances"])))

        database.execute_db("""
            INSERT INTO household_profiles 
                (user_id, profile_name, relationship, avatar_initials, avatar_color, lifestyle_type, shopping_personality, preferred_categories, budget_max, notes, is_active)
            VALUES 
                (?, 'Active & Fitness Twin', 'Sports', 'AF', '#d97706', 'Fitness & Active', 'Performance Focused', ?, 8000.0, 'Running shoes, workout apparel, and fitness accessories', 0)
        """, (user_id, json.dumps(["Sports & Fitness", "Footwear"])))
        print("✓ Household Profiles seeded")

    # 2. Tracked Products
    count_tp = database.query_db('SELECT COUNT(*) as c FROM tracked_products', one=True)['c']
    if count_tp == 0:
        prods = database.query_db('SELECT id, price FROM products LIMIT 3')
        if prods:
            for p in prods:
                target = round(float(p['price']) * 0.9, 2)
                database.execute_db(
                    'INSERT INTO tracked_products (user_id, product_id, target_price, last_checked_price) VALUES (?, ?, ?, ?)',
                    (user_id, p['id'], target, float(p['price']))
                )
        print("✓ Tracked products seeded")

    # 3. Price History
    count_ph = database.query_db('SELECT COUNT(*) as c FROM price_history', one=True)['c']
    if count_ph == 0:
        top_prods = database.query_db('SELECT id, price FROM products LIMIT 25')
        for p in top_prods:
            base_p = float(p['price'])
            database.execute_db('INSERT INTO price_history (product_id, price, recorded_date) VALUES (?, ?, ?)', (p['id'], round(base_p * 1.15, 2), '2026-08-15'))
            database.execute_db('INSERT INTO price_history (product_id, price, recorded_date) VALUES (?, ?, ?)', (p['id'], round(base_p * 1.08, 2), '2026-09-10'))
            database.execute_db('INSERT INTO price_history (product_id, price, recorded_date) VALUES (?, ?, ?)', (p['id'], round(base_p * 1.03, 2), '2026-10-01'))
            database.execute_db('INSERT INTO price_history (product_id, price, recorded_date) VALUES (?, ?, ?)', (p['id'], base_p, '2026-10-26'))
        print("✓ Price history seeded")

    # 4. Shopping Reminders
    count_rem = database.query_db('SELECT COUNT(*) as c FROM shopping_reminders', one=True)['c']
    if count_rem == 0:
        database.execute_db(
            'INSERT INTO shopping_reminders (user_id, title, category, estimated_cycle_days, next_reminder_date, status) VALUES (?, ?, ?, ?, ?, ?)',
            (user_id, "Coffee Beans & Morning Brew Supplies", "Food & Grocery", 30, "2026-11-05", "active")
        )
        database.execute_db(
            'INSERT INTO shopping_reminders (user_id, title, category, estimated_cycle_days, next_reminder_date, status) VALUES (?, ?, ?, ?, ?, ?)',
            (user_id, "Electric Toothbrush Heads & Floss", "Personal Care", 60, "2026-11-18", "active")
        )
        database.execute_db(
            'INSERT INTO shopping_reminders (user_id, title, category, estimated_cycle_days, next_reminder_date, status) VALUES (?, ?, ?, ?, ?, ?)',
            (user_id, "Printer Ink Cartridge & Paper", "Books & Stationery", 90, "2026-12-01", "active")
        )
        print("✓ Shopping reminders seeded")

    # 5. Shopping Calendar Events
    count_cal = database.query_db('SELECT COUNT(*) as c FROM shopping_calendar_events', one=True)['c']
    if count_cal == 0:
        database.execute_db(
            'INSERT INTO shopping_calendar_events (user_id, title, event_date, event_type, budget) VALUES (?, ?, ?, ?, ?)',
            (user_id, "College Tech Fest & Hackathon Project", "2026-11-15", "college", 6000.0)
        )
        database.execute_db(
            'INSERT INTO shopping_calendar_events (user_id, title, event_date, event_type, budget) VALUES (?, ?, ?, ?, ?)',
            (user_id, "Winter Vacation & Travel Prep", "2026-12-20", "trip", 15000.0)
        )
        database.execute_db(
            'INSERT INTO shopping_calendar_events (user_id, title, event_date, event_type, budget) VALUES (?, ?, ?, ?, ?)',
            (user_id, "Diwali Festival Celebrations & Gifts", "2026-11-01", "festival", 8500.0)
        )
        print("✓ Shopping calendar events seeded")

    # 6. Shopping Tasks
    count_task = database.query_db('SELECT COUNT(*) as c FROM shopping_tasks', one=True)['c']
    if count_task == 0:
        steps = [
            {"agent": "Preference Agent", "status": "done", "summary": "Identified budget limit ₹5,000 for college work essentials"},
            {"agent": "Discovery Agent", "status": "done", "summary": "Found ergonomic wireless mouse, keyboard, and aluminum stand"},
            {"agent": "Comparison Agent", "status": "done", "summary": "Selected top value combination with 4.5+ star ratings"},
            {"agent": "Budget Agent", "status": "done", "summary": "Total estimated bundle ₹4,299 (Saved ₹701 under ceiling)"}
        ]
        database.execute_db("""
            INSERT INTO shopping_tasks 
                (user_id, task_name, goal_description, budget_limit, status, steps_json, requires_approval, approved_by_user)
            VALUES (?, ?, ?, ?, 'ready_for_approval', ?, 1, 0)
        """, (user_id, "Ergonomic Workstation Setup", "College project workstation essentials under ₹5,000", 5000.0, json.dumps(steps)))
        print("✓ Shopping task seeded")

if __name__ == "__main__":
    seed_eight_features()
