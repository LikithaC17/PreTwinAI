"""
tests/test_purchase_history_and_agents.py
-----------------------------------------
Comprehensive test suite verifying:
1. Purchase history event qualification (COD vs Online, cancelled/returned disqualification)
2. Snapshot preservation of order details and price
3. Privacy controls (opt-in/opt-out) and user data isolation
4. PurchaseHistoryAgent analytics
5. PreferenceLearningAgent spending tier and cadence detection
6. PurchasePredictionAgent statistical intervals and evidence explanations
7. RecommendationCoordinatorAgent integration and recommendation dismissal
8. API endpoints: /api/purchase-history, /api/twin/insights, /api/twin/privacy-controls, /api/twin/dismiss-recommendation
"""

import json
import pytest
from datetime import datetime, timedelta

import database
from services.purchase_history_service import PurchaseHistoryService
from agents.agent_purchase_history import PurchaseHistoryAgent
from agents.agent_preference_learning import PreferenceLearningAgent
from agents.agent_purchase_prediction import PurchasePredictionAgent
from agents.agent_recommendation_coordinator import RecommendationCoordinatorAgent


def _create_user(username="TestUser", email="test@example.com"):
    row_id = database.execute_db(
        "INSERT INTO users (username, email) VALUES (?, ?)",
        (username, email)
    )
    return row_id


def _create_product(name="Test Product", category="Electronics", price=1000.0, brand="TestBrand"):
    row_id = database.execute_db(
        "INSERT INTO products (name, category, brand, price, rating, review_count_demo) VALUES (?, ?, ?, ?, 4.5, 50)",
        (name, category, brand, price)
    )
    return row_id


class TestPurchaseHistoryService:
    """Tests for order verification and purchase history integrity."""

    def test_order_eligibility_online_payment(self):
        """Paid and confirmed online order must be eligible."""
        order = {
            "status": "Confirmed",
            "payment_status": "Paid",
            "payment_method": "Online / Card",
            "gateway_name": "Razorpay",
        }
        assert PurchaseHistoryService.is_order_eligible_for_history(order) is True

    def test_order_eligibility_cod_pending_disqualified(self):
        """COD order placed but not yet delivered must NOT be eligible."""
        order = {
            "status": "Confirmed",
            "payment_status": "Pending (Cash on Delivery)",
            "payment_method": "COD",
            "gateway_name": "COD",
        }
        assert PurchaseHistoryService.is_order_eligible_for_history(order) is False

    def test_order_eligibility_cod_delivered_qualified(self):
        """COD order marked delivered and paid must be eligible."""
        order = {
            "status": "Delivered",
            "payment_status": "Paid (Cash on Delivery)",
            "payment_method": "COD",
            "gateway_name": "COD",
        }
        assert PurchaseHistoryService.is_order_eligible_for_history(order) is True

    def test_order_eligibility_cancelled_and_returned_disqualified(self):
        """Cancelled or returned orders must be disqualified."""
        assert PurchaseHistoryService.is_order_eligible_for_history({
            "status": "Cancelled", "payment_status": "Refunded"
        }) is False

        assert PurchaseHistoryService.is_order_eligible_for_history({
            "status": "Returned", "payment_status": "Refunded"
        }) is False

        assert PurchaseHistoryService.is_order_eligible_for_history({
            "status": "Payment Failed", "payment_status": "Failed"
        }) is False

    def test_record_order_purchase_creates_snapshot(self, app_client):
        """Verify order snapshot is preserved and duplicate events are prevented."""
        u_id = _create_user("SnapshotUser", "snapshot@example.com")
        p_id = _create_product("Wireless Mouse", "Electronics", 1500.0, "Logitech")

        # Create order
        ord_id = database.execute_db(
            """INSERT INTO orders
               (order_number, user_id, total_amount, status, payment_status, payment_method)
               VALUES ('ORD-TEST-101', ?, 1500.0, 'Confirmed', 'Paid', 'Online')""",
            (u_id,)
        )

        # Create order item
        database.execute_db(
            """INSERT INTO order_items
               (order_id, product_id, product_name, category, brand, price, quantity, total_price)
               VALUES (?, ?, 'Wireless Mouse', 'Electronics', 'Logitech', 1500.0, 1, 1500.0)""",
            (ord_id, p_id)
        )

        # Record purchase
        recorded = PurchaseHistoryService.record_order_purchase(ord_id)
        assert recorded == 1

        # Check recorded snapshot
        rows = database.query_db("SELECT * FROM purchase_history WHERE order_id = ?", (ord_id,))
        assert len(rows) == 1
        assert rows[0]["product_name"] == "Wireless Mouse"
        assert rows[0]["price"] == 1500.0
        assert rows[0]["is_verified_purchase"] == 1

        # Second call must not duplicate
        recorded_second = PurchaseHistoryService.record_order_purchase(ord_id)
        assert recorded_second == 0
        cnt_row = database.query_db("SELECT COUNT(*) as cnt FROM purchase_history WHERE order_id = ?", (ord_id,), one=True)
        assert cnt_row["cnt"] == 1

    def test_cancellation_and_return_invalidation(self, app_client):
        """Cancelling or returning an order marks purchase history is_verified_purchase = 0."""
        u_id = _create_user("CancelUser", "cancel@example.com")
        p_id = _create_product("Coffee Beans", "Groceries", 800.0, "Blue Tokai")

        ord_id = database.execute_db(
            """INSERT INTO orders
               (order_number, user_id, total_amount, status, payment_status, payment_method)
               VALUES ('ORD-TEST-102', ?, 800.0, 'Confirmed', 'Paid', 'Online')""",
            (u_id,)
        )
        database.execute_db(
            """INSERT INTO order_items
               (order_id, product_id, product_name, category, brand, price, quantity, total_price)
               VALUES (?, ?, 'Coffee Beans', 'Groceries', 'Blue Tokai', 800.0, 1, 800.0)""",
            (ord_id, p_id)
        )

        PurchaseHistoryService.record_order_purchase(ord_id)

        # Cancel order
        PurchaseHistoryService.handle_order_cancellation(ord_id)
        row = database.query_db("SELECT is_verified_purchase, order_status FROM purchase_history WHERE order_id = ?", (ord_id,), one=True)
        assert row["is_verified_purchase"] == 0
        assert row["order_status"] == "Cancelled"

    def test_privacy_controls_toggle(self, app_client):
        """Verify user opt-in and opt-out toggle."""
        user_id = _create_user("PrivacyUser", "privacy@example.com")
        # Default is True
        assert PurchaseHistoryService.is_twin_history_opted_in(user_id) is True

        # Toggle to False
        PurchaseHistoryService.set_twin_history_opt_in(user_id, False)
        assert PurchaseHistoryService.is_twin_history_opted_in(user_id) is False

        # Toggle back to True
        PurchaseHistoryService.set_twin_history_opt_in(user_id, True)
        assert PurchaseHistoryService.is_twin_history_opted_in(user_id) is True


class TestShoppingAgents:
    """Tests for the specialized AI shopping agents."""

    def test_purchase_history_agent_zero_state(self, app_client):
        """User with no purchases should cleanly return zero-state without errors."""
        agent = PurchaseHistoryAgent()
        res = agent.run(user_id=777)
        assert res["total_orders"] == 0
        assert res["total_items_count"] == 0
        assert res["total_spent"] == 0.0
        assert res["has_purchase_history"] is False
        assert res["frequently_purchased"] == []

    def test_purchase_history_agent_with_purchases(self, app_client):
        """Verify analytics calculations on verified purchases."""
        u_id = _create_user("AnalyticsUser", "analytics@example.com")
        database.execute_db(
            """INSERT INTO purchase_history
               (user_id, product_name, category, brand, price, quantity, purchase_date, order_number, is_verified_purchase)
               VALUES
               (?, 'Running Shoes', 'Footwear', 'Puma', 2000.0, 1, '2026-03-01', 'ORD-1', 1)""",
            (u_id,)
        )
        database.execute_db(
            """INSERT INTO purchase_history
               (user_id, product_name, category, brand, price, quantity, purchase_date, order_number, is_verified_purchase)
               VALUES
               (?, 'Running Shoes', 'Footwear', 'Puma', 2000.0, 1, '2026-03-25', 'ORD-2', 1)""",
            (u_id,)
        )
        database.execute_db(
            """INSERT INTO purchase_history
               (user_id, product_name, category, brand, price, quantity, purchase_date, order_number, is_verified_purchase)
               VALUES
               (?, 'Cotton T-Shirt', 'Fashion', 'Levis', 500.0, 2, '2026-03-25', 'ORD-2', 1)""",
            (u_id,)
        )

        agent = PurchaseHistoryAgent()
        res = agent.run(user_id=u_id)
        assert res["has_purchase_history"] is True
        assert res["total_items_count"] == 4
        assert res["total_spent"] == 5000.0
        assert res["total_orders"] == 2
        assert len(res["frequently_purchased"]) >= 1
        assert res["frequently_purchased"][0]["product_name"] == "Running Shoes"
        assert res["frequently_purchased"][0]["order_appearances"] == 2

    def test_preference_learning_agent_privacy_respect(self, app_client):
        """When user opts out of purchase history, learning agent must ignore purchase data."""
        u_id = _create_user("OptOutUser", "optout@example.com")
        database.execute_db(
            """INSERT INTO shopping_preferences
               (user_id, preferred_categories, preferred_brands, budget_min, budget_max, use_purchase_history_for_twin)
               VALUES (?, '["Books"]', '["Penguin"]', 200.0, 1000.0, 0)""",
            (u_id,)
        )
        database.execute_db(
            """INSERT INTO purchase_history
               (user_id, product_name, category, brand, price, is_verified_purchase)
               VALUES (?, 'Smartphone', 'Electronics', 'Samsung', 35000.0, 1)""",
            (u_id,)
        )

        agent = PreferenceLearningAgent()
        learned = agent.run(user_id=u_id)
        assert learned["purchase_history_utilized"] is False
        assert "Electronics" not in learned["ranked_categories"]
        assert "Books" in learned["ranked_categories"]

    def test_preference_learning_agent_tier_classification(self, app_client):
        """Check spending tier classification from purchases."""
        u_id = _create_user("TierUser", "tier@example.com")
        database.execute_db(
            """INSERT INTO purchase_history
               (user_id, product_name, category, brand, price, quantity, purchase_date, is_verified_purchase)
               VALUES
               (?, 'Mechanical Keyboard', 'Electronics', 'Logitech', 6500.0, 1, '2026-02-10', 1)""",
            (u_id,)
        )
        database.execute_db(
            """INSERT INTO purchase_history
               (user_id, product_name, category, brand, price, quantity, purchase_date, is_verified_purchase)
               VALUES
               (?, 'Gaming Mouse', 'Electronics', 'Razer', 4500.0, 1, '2026-03-10', 1)""",
            (u_id,)
        )

        agent = PreferenceLearningAgent()
        learned = agent.run(user_id=u_id)
        assert learned["purchase_history_utilized"] is True
        assert "Mid-Range Quality" in learned["spending_tier"] or "Value" in learned["spending_tier"]

    def test_purchase_prediction_agent_repeat_interval(self, app_client):
        """Calculate repeat interval and forecast date with transparent evidence."""
        u_id = _create_user("PredUser", "pred@example.com")
        database.execute_db(
            """INSERT INTO purchase_history
               (user_id, product_name, category, brand, price, quantity, purchase_date, is_verified_purchase)
               VALUES
               (?, 'Arabica Coffee Beans', 'Groceries', 'Blue Tokai', 600.0, 1, '2026-01-01', 1)""",
            (u_id,)
        )
        database.execute_db(
            """INSERT INTO purchase_history
               (user_id, product_name, category, brand, price, quantity, purchase_date, is_verified_purchase)
               VALUES
               (?, 'Arabica Coffee Beans', 'Groceries', 'Blue Tokai', 600.0, 1, '2026-01-31', 1)""",
            (u_id,)
        )

        agent = PurchasePredictionAgent()
        result = agent.run(user_id=u_id)
        assert result["has_predictions"] is True
        pred = result["predictions"][0]
        assert pred["product_name"] == "Arabica Coffee Beans"
        assert pred["average_interval_days"] == 30
        assert pred["prediction_type"] == "repeat_behavior"
        assert "Purchased 2 times" in pred["evidence_explanation"]

    def test_purchase_prediction_agent_durable_goods_not_predicted(self, app_client):
        """Single purchase of durable good (Laptop) must NOT generate recurring replenishment."""
        u_id = _create_user("DurableUser", "durable@example.com")
        database.execute_db(
            """INSERT INTO purchase_history
               (user_id, product_name, category, brand, price, quantity, purchase_date, is_verified_purchase)
               VALUES
               (?, 'MacBook Air M2', 'Laptops', 'Apple', 89000.0, 1, '2026-01-01', 1)""",
            (u_id,)
        )

        agent = PurchasePredictionAgent()
        result = agent.run(user_id=u_id)
        assert len(result["predictions"]) == 0

    def test_recommendation_coordinator_and_dismissal(self, app_client):
        """Coordinator assembles candidates and excludes dismissed products."""
        u_id = _create_user("CoordUser", "coord@example.com")
        p1 = _create_product("Test Product Alpha", "Electronics", 2500.0, "Sony")
        p2 = _create_product("Test Product Beta", "Electronics", 2800.0, "Sony")

        # Dismiss p1
        RecommendationCoordinatorAgent.dismiss_recommendation(user_id=u_id, product_id=p1)

        coordinator = RecommendationCoordinatorAgent()
        res = coordinator.run(user_id=u_id)
        recs = res["recommendations"]
        rec_ids = [r["id"] for r in recs]
        assert p1 not in rec_ids


class TestTwinApiEndpoints:
    """Tests for the HTTP endpoints."""

    def test_get_purchase_history_api(self, app_client):
        """GET /api/purchase-history returns 200 and history list."""
        resp = app_client.get("/api/purchase-history")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "history" in data
        assert "user_id" in data

    def test_twin_insights_api(self, app_client):
        """GET /api/twin/insights returns coordinated agent insights."""
        resp = app_client.get("/api/twin/insights")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "history_summary" in data
        assert "learned_profile" in data
        assert "recommendations" in data

    def test_privacy_controls_api(self, app_client):
        """GET & POST /api/twin/privacy-controls works smoothly."""
        resp = app_client.get("/api/twin/privacy-controls")
        assert resp.status_code == 200

        resp = app_client.post(
            "/api/twin/privacy-controls",
            data=json.dumps({"use_purchase_history_for_twin": False}),
            content_type="application/json"
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["use_purchase_history_for_twin"] is False

    def test_dismiss_recommendation_api(self, app_client):
        """POST /api/twin/dismiss-recommendation registers product dismissal."""
        resp = app_client.post(
            "/api/twin/dismiss-recommendation",
            data=json.dumps({"product_id": 42}),
            content_type="application/json"
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["product_id"] == 42
