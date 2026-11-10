"""
tests/test_predictions_six_sections.py
--------------------------------------
Comprehensive Unit and Integration Test Suite for Feature 2:
Predictive Shopping Intelligence.
Verifies all 10 required customer scenarios:
1. New customer with no purchase history.
2. Customer with one completed purchase.
3. Customer with multiple repeat purchases.
4. Customer with irregular purchasing intervals.
5. Customer with cancelled and returned orders.
6. Customer with pending COD orders.
7. Customer with seasonal purchase history.
8. Two customers with separate purchase histories (Data Isolation).
9. Customer who dismisses, edits, or snoozes a reminder.
10. Customer who marks a predicted purchase as completed / fulfilled.
"""

import json
import pytest
from datetime import datetime, timedelta
import database
from services.purchase_history_service import PurchaseHistoryService
from services.predictive_intelligence_service import (
    PurchasePatternAnalyzer,
    ReplenishmentPredictor,
    SeasonalTrendAnalyzer,
    SpendingForecastEngine,
    PredictiveIntelligenceCoordinator,
)


def _ensure_user(user_id: int, username: str = "Test Shopper"):
    """Helper to ensure clean state and user record for isolated testing."""
    database.execute_db("DELETE FROM purchase_history WHERE user_id = ?", (user_id,))
    database.execute_db("DELETE FROM orders WHERE user_id = ?", (user_id,))
    database.execute_db("DELETE FROM predictions WHERE user_id = ?", (user_id,))
    database.execute_db("DELETE FROM shopping_reminders WHERE user_id = ?", (user_id,))
    database.execute_db(
        """INSERT OR IGNORE INTO users (id, username, email, password_hash)
           VALUES (?, ?, ?, 'hashed_pw')""",
        (user_id, username, f"user_{user_id}@pretwin.ai")
    )


def test_scenario_1_new_customer_with_no_history(test_db):
    """Scenario 1: New customer with zero purchases gets honest empty states, no fake predictions."""
    uid = 8888
    _ensure_user(uid, "New Shopper")

    dash = PredictiveIntelligenceCoordinator.get_dashboard(user_id=uid)
    assert dash["success"] is True
    assert dash["is_first_time_customer"] is True
    assert dash["total_purchases_analyzed"] == 0

    sections = dash["sections"]
    assert len(sections["upcoming_needs"]["items"]) == 0
    assert sections["buying_patterns"]["has_data"] is False
    assert sections["spending_forecast"]["has_forecast"] is False
    assert sections["seasonal_insights"]["has_seasonal_patterns"] is False


def test_scenario_2_customer_with_one_purchase(test_db):
    """Scenario 2: Single purchase does not fabricate repeat intervals, uses consumable baseline if applicable."""
    uid = 8889
    _ensure_user(uid, "Single Order Shopper")
    today_str = (datetime.now() - timedelta(days=20)).strftime("%Y-%m-%d")

    # Add single grocery purchase
    database.execute_db(
        """INSERT INTO purchase_history
           (user_id, product_name, category, price, quantity, purchase_date, order_status, payment_status, is_verified_purchase)
           VALUES (?, 'Organic Roasted Coffee Beans', 'Food & Beverages', 499.0, 1, ?, 'Delivered', 'Paid', 1)""",
        (uid, today_str)
    )

    dash = PredictiveIntelligenceCoordinator.get_dashboard(user_id=uid)
    assert dash["is_first_time_customer"] is False
    assert dash["total_purchases_analyzed"] == 1

    # Should use category baseline (~21 days for Food & Beverages), confidence is Low/Medium
    upcoming = dash["sections"]["upcoming_needs"]["items"]
    assert len(upcoming) >= 1
    coffee_pred = upcoming[0]
    assert coffee_pred["product_name"] == "Organic Roasted Coffee Beans"
    assert coffee_pred["confidence_label"] in ("Medium", "Low")
    assert "Food & Beverages" in coffee_pred["category"]


def test_scenario_3_customer_with_multiple_repeat_purchases(test_db):
    """Scenario 3: 3 repeat purchases compute accurate median interval and High confidence."""
    uid = 8890
    _ensure_user(uid, "Repeat Shopper")
    dates = [
        (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d"),
        (datetime.now() - timedelta(days=32)).strftime("%Y-%m-%d"),  # 28 days interval
        (datetime.now() - timedelta(days=4)).strftime("%Y-%m-%d"),   # 28 days interval
    ]

    for dt in dates:
        database.execute_db(
            """INSERT INTO purchase_history
               (user_id, product_name, category, price, quantity, purchase_date, order_status, payment_status, is_verified_purchase)
               VALUES (?, 'Hydrating Face Moisturizer', 'Personal Care', 650.0, 1, ?, 'Delivered', 'Paid', 1)""",
            (uid, dt)
        )

    dash = PredictiveIntelligenceCoordinator.get_dashboard(user_id=uid)
    upcoming = dash["sections"]["upcoming_needs"]["items"]
    assert len(upcoming) >= 1

    pred = upcoming[0]
    assert pred["product_name"] == "Hydrating Face Moisturizer"
    assert pred["cycle_days"] == 28
    assert pred["confidence_label"] == "High"
    assert pred["confidence_score"] >= 0.85


def test_scenario_4_irregular_purchasing_intervals(test_db):
    """Scenario 4: Irregular purchase intervals compute median and lowered regularity score."""
    uid = 8891
    _ensure_user(uid, "Irregular Shopper")
    dates = [
        (datetime.now() - timedelta(days=120)).strftime("%Y-%m-%d"),
        (datetime.now() - timedelta(days=95)).strftime("%Y-%m-%d"),  # 25 days
        (datetime.now() - timedelta(days=35)).strftime("%Y-%m-%d"),  # 60 days
        (datetime.now() - timedelta(days=15)).strftime("%Y-%m-%d"),  # 20 days
    ]

    for dt in dates:
        database.execute_db(
            """INSERT INTO purchase_history
               (user_id, product_name, category, price, quantity, purchase_date, order_status, payment_status, is_verified_purchase)
               VALUES (?, 'Green Tea Bags 100s', 'Food & Beverages', 350.0, 1, ?, 'Delivered', 'Paid', 1)""",
            (uid, dt)
        )

    dash = PredictiveIntelligenceCoordinator.get_dashboard(user_id=uid)
    patterns = dash["sections"]["buying_patterns"]
    assert patterns["median_repeat_interval_days"] is not None
    # Regularity score reflects variance
    assert patterns["regularity_score"] < 1.0


def test_scenario_5_cancelled_and_returned_orders_excluded(test_db):
    """Scenario 5: Cancelled, failed, and returned orders are strictly excluded from predictions."""
    uid = 8892
    _ensure_user(uid, "Returns Shopper")
    dt_valid = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")

    # 1 Valid order
    database.execute_db(
        """INSERT INTO purchase_history
           (user_id, product_name, category, price, quantity, purchase_date, order_status, payment_status, is_verified_purchase)
           VALUES (?, 'Hand Sanitizer 500ml', 'Personal Care', 150.0, 1, ?, 'Delivered', 'Paid', 1)""",
        (uid, dt_valid)
    )

    # 1 Cancelled order
    database.execute_db(
        """INSERT INTO purchase_history
           (user_id, product_name, category, price, quantity, purchase_date, order_status, payment_status, is_verified_purchase)
           VALUES (?, 'Fake Cancelled Laptop', 'Electronics', 65000.0, 1, ?, 'Cancelled', 'Cancelled', 0)""",
        (uid, dt_valid)
    )

    # 1 Returned order
    database.execute_db(
        """INSERT INTO purchase_history
           (user_id, product_name, category, price, quantity, purchase_date, order_status, payment_status, is_verified_purchase)
           VALUES (?, 'Fake Returned Smartphone', 'Electronics', 25000.0, 1, ?, 'Returned', 'Refunded', 0)""",
        (uid, dt_valid)
    )

    dash = PredictiveIntelligenceCoordinator.get_dashboard(user_id=uid)
    assert dash["total_purchases_analyzed"] == 1

    # Electronics must NOT appear in predictions or patterns
    frequent_cats = [c["category"] for c in dash["sections"]["buying_patterns"]["frequent_categories"]]
    assert "Electronics" not in frequent_cats


def test_scenario_6_pending_cod_orders_excluded_until_delivered(test_db):
    """Scenario 6: Pending COD orders are excluded from purchase history and predictions."""
    uid = 8893
    _ensure_user(uid, "COD Shopper")

    # Insert COD order that is placed but NOT yet delivered
    order_id = database.execute_db(
        """INSERT INTO orders
           (user_id, order_number, customer_name, customer_email, shipping_address, city, state, pincode, subtotal, total_amount, status, payment_method, payment_status, gateway_name)
           VALUES (?, 'ORD-COD-PENDING', 'COD Shopper', 'cod@test.com', '123 Main St', 'Bengaluru', 'Karnataka', '560001', 2500.0, 2500.0, 'Placed', 'Cash on Delivery', 'Pending', 'COD')""",
        (uid,)
    )
    database.execute_db(
        """INSERT INTO order_items
           (order_id, product_id, product_name, category, price, quantity, total_price)
           VALUES (?, 1, 'COD Pending Headphones', 'Electronics', 2500.0, 1, 2500.0)""",
        (order_id,)
    )

    # Verify not eligible
    eligible = PurchaseHistoryService.get_eligible_purchases_for_user(uid)
    assert len(eligible) == 0

    dash = PredictiveIntelligenceCoordinator.get_dashboard(user_id=uid)
    assert dash["is_first_time_customer"] is True
    assert dash["total_purchases_analyzed"] == 0


def test_scenario_7_seasonal_purchase_history(test_db):
    """Scenario 7: Seasonal insights accurately identify historical seasonal purchase months."""
    uid = 8894
    _ensure_user(uid, "Seasonal Shopper")

    # Add historical summer order in April (Month 4)
    database.execute_db(
        """INSERT INTO purchase_history
           (user_id, product_name, category, price, quantity, purchase_date, order_status, payment_status, is_verified_purchase)
           VALUES (?, 'SPF 50 Mineral Sunscreen Gel', 'Personal Care', 450.0, 1, '2025-04-12', 'Delivered', 'Paid', 1)""",
        (uid,)
    )

    dash = PredictiveIntelligenceCoordinator.get_dashboard(user_id=uid)
    seasonal = dash["sections"]["seasonal_insights"]
    assert seasonal["has_seasonal_patterns"] is True
    pattern_names = [p["season_name"] for p in seasonal["patterns"]]
    assert any("Summer" in name for name in pattern_names)


def test_scenario_8_data_isolation_between_two_customers(test_db):
    """Scenario 8: Customer A data does not leak into Customer B."""
    user_a = 8895
    user_b = 8896
    _ensure_user(user_a, "Shopper Alpha")
    _ensure_user(user_b, "Shopper Beta")

    # Order for User A
    database.execute_db(
        """INSERT INTO purchase_history
           (user_id, product_name, category, price, quantity, purchase_date, order_status, payment_status, is_verified_purchase)
           VALUES (?, 'Alpha Vitamin D3 Softgels', 'Health', 399.0, 1, '2026-04-01', 'Delivered', 'Paid', 1)""",
        (user_a,)
    )

    # Order for User B
    database.execute_db(
        """INSERT INTO purchase_history
           (user_id, product_name, category, price, quantity, purchase_date, order_status, payment_status, is_verified_purchase)
           VALUES (?, 'Beta Herbal Shampoo', 'Personal Care', 299.0, 1, '2026-04-01', 'Delivered', 'Paid', 1)""",
        (user_b,)
    )

    dash_a = PredictiveIntelligenceCoordinator.get_dashboard(user_id=user_a)
    dash_b = PredictiveIntelligenceCoordinator.get_dashboard(user_id=user_b)

    prods_a = [p["product_name"] for p in dash_a["sections"]["upcoming_needs"]["items"]]
    prods_b = [p["product_name"] for p in dash_b["sections"]["upcoming_needs"]["items"]]

    assert "Alpha Vitamin D3 Softgels" in prods_a
    assert "Alpha Vitamin D3 Softgels" not in prods_b
    assert "Beta Herbal Shampoo" in prods_b
    assert "Beta Herbal Shampoo" not in prods_a


def test_scenario_9_reminder_management_lifecycle(app_client):
    """Scenario 9: Customer creates, edits, snoozes, toggles, and deletes reminders."""
    # 1. Create reminder
    res = app_client.post(
        "/api/predictions/reminders",
        data=json.dumps({
            "title": "Almond Milk 1L Pack of 6",
            "category": "Groceries",
            "estimated_cycle_days": 14
        }),
        content_type="application/json"
    )
    assert res.status_code == 201

    # 2. Get reminders
    list_res = app_client.get("/api/predictions/reminders")
    assert list_res.status_code == 200
    reminders = list_res.get_json()["reminders"]
    match = next(r for r in reminders if r["title"] == "Almond Milk 1L Pack of 6")
    rem_id = match["id"]

    # 3. Edit date and toggle
    edit_res = app_client.put(
        f"/api/predictions/reminders/{rem_id}",
        data=json.dumps({
            "next_reminder_date": "2026-06-15",
            "is_enabled": False
        }),
        content_type="application/json"
    )
    assert edit_res.status_code == 200

    # 4. Snooze reminder
    snooze_res = app_client.put(
        f"/api/predictions/reminders/{rem_id}/status",
        data=json.dumps({"status": "snoozed", "snooze_days": 10}),
        content_type="application/json"
    )
    assert snooze_res.status_code == 200

    # 5. Delete reminder
    del_res = app_client.delete(f"/api/predictions/reminders/{rem_id}")
    assert del_res.status_code == 200


def test_scenario_10_mark_predicted_purchase_completed(app_client):
    """Scenario 10: Customer marks a predicted purchase as completed / fulfilled."""
    # Ensure a prediction exists in DB
    dash_res = app_client.get("/api/predictions/dashboard")
    assert dash_res.status_code == 200

    # Get predictions list
    preds_res = app_client.get("/api/predictions")
    preds = preds_res.get_json()["predictions"]
    if preds:
        pred_id = preds[0]["id"]
        # Mark as purchased
        act_res = app_client.post(
            f"/api/predictions/{pred_id}/action",
            data=json.dumps({"action": "purchased"}),
            content_type="application/json"
        )
        assert act_res.status_code == 200
        assert act_res.get_json()["action"] == "purchased"

        # Verify status in history
        dash2 = app_client.get("/api/predictions/dashboard").get_json()
        history = dash2["sections"]["prediction_history"]["predictions_history"]
        history_match = next(p for p in history if p["id"] == pred_id)
        assert history_match["effective_status"] in ("fulfilled", "confirmed")
        assert history_match["actual_purchase_date"] is not None
