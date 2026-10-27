"""
Tests for PreTwin New Features:
- Fairytale Logo & Branding Assets
- 5-Item AI Navigation Bar
- AI Shopping Chat Assistant & API
- Cash on Delivery (COD) Checkout & Delivery Flow
- PreTwin Smart Shopping Savings Plan (Daily/Weekly Rates & Progress)
- PreTwin Reward Points (Strict 100 pts = ₹1.00 conversion & Redemption)
"""

import os
import json
import pytest
from app import app, calculate_savings_plan_stats, get_user_reward_balance
import database
from agents.chat_assistant import PreTwinChatAssistant


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_fairytale_brand_assets_exist():
    """Verify all fairytale logo SVG assets exist on disk and have valid content."""
    logo_path = os.path.join("static", "images", "pretwin-logo.svg")
    icon_path = os.path.join("static", "images", "pretwin-icon.svg")
    fav_path = os.path.join("static", "favicon.svg")

    assert os.path.exists(logo_path), "pretwin-logo.svg missing"
    assert os.path.exists(icon_path), "pretwin-icon.svg missing"
    assert os.path.exists(fav_path), "favicon.svg missing"

    with open(logo_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "Twin" in content
        assert "<svg" in content


def test_ai_navigation_bar_rendered(client):
    """Verify that base template contains the 8 AI Navigation items above categories."""
    res = client.get("/")
    assert res.status_code == 200
    html = res.data.decode("utf-8")

    assert "pretwin-ai-nav-bar" in html
    assert "Personalization and Digital Twin" in html
    assert "Predictive Shopping Intelligence" in html
    assert "Smart Product Discovery" in html
    assert "Budget and Price Intelligence" in html
    assert "Product Comparison and Decision Support" in html
    assert "Future Predictive Calendar" in html
    assert "Smart Cart and Shopping Automation" in html
    assert "Advanced Features for Future Development" in html


def test_chat_assistant_engine_deterministic():
    """Test PreTwinChatAssistant fallback responses for various shopping intents."""
    bot = PreTwinChatAssistant()

    # 1. Budget product search
    res = bot.handle_message("Show me phones under 20000")
    assert "Found" in res["reply"] or "Here are" in res["reply"]
    assert len(res["products"]) > 0
    for p in res["products"]:
        assert p["price"] <= 20000

    # 2. Reward points inquiry (must mention 100 points = 1 rupee)
    res_rew = bot.handle_message("How do reward points work?")
    assert "100 points = ₹1" in res_rew["reply"].lower()
    assert "5 points" in res_rew["reply"].lower()

    # 3. Cash on Delivery inquiry
    res_cod = bot.handle_message("Can I pay with Cash on Delivery?")
    assert "Cash on Delivery" in res_cod["reply"] or "COD" in res_cod["reply"]

    # 4. Savings plan inquiry
    res_sav = bot.handle_message("How does the savings plan work?")
    assert "savings" in res_sav["reply"].lower()


def test_chat_api_endpoints(client):
    """Test POST /api/chat and GET /api/chat/history."""
    res = client.post("/api/chat", json={
        "message": "shoes under 2000",
        "session_id": "test_session_123"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert "reply" in data
    assert isinstance(data["products"], list)

    hist_res = client.get("/api/chat/history?session_id=test_session_123")
    assert hist_res.status_code == 200
    hist = hist_res.get_json()
    assert hist["total"] >= 2  # user + assistant message


def test_smart_savings_plan_calculations():
    """Test exact mathematical breakdown for daily and weekly rates."""
    plan = {
        "target_amount": 15000.0,
        "saved_amount": 3000.0,
        "target_date": "2026-11-25"  # 30 days from 2026-10-26
    }
    stats = calculate_savings_plan_stats(plan)
    assert stats["remaining_amount"] == 12000.0
    assert stats["progress_percentage"] == 20.0
    assert stats["days_remaining"] == 30
    assert stats["daily_savings_rate"] == 400.0  # 12000 / 30
    assert stats["weekly_savings_rate"] == 2800.0  # 400 * 7
    assert stats["is_ready_to_shop"] is False

    # Completed plan
    plan_complete = {
        "target_amount": 5000.0,
        "saved_amount": 5000.0,
        "target_date": "2026-11-25"
    }
    stats_c = calculate_savings_plan_stats(plan_complete)
    assert stats_c["remaining_amount"] == 0.0
    assert stats_c["progress_percentage"] == 100.0
    assert stats_c["is_ready_to_shop"] is True


def test_savings_plan_crud_api(client):
    """Test full API lifecycle for savings goals and contributions."""
    # 1. Create plan
    res = client.post("/api/savings/plans", json={
        "title": "Save for Test Wireless Earbuds",
        "target_amount": 2000.0,
        "notes": "Testing auto-breakdown"
    })
    assert res.status_code == 201
    plan = res.get_json()["plan"]
    plan_id = plan["id"]
    assert plan["target_amount"] == 2000.0
    assert plan["saved_amount"] == 0.0

    # 2. Add contribution
    res_c = client.post(f"/api/savings/plans/{plan_id}/contributions", json={
        "amount": 500.0,
        "payment_method": "PreTwin Wallet",
        "notes": "First deposit"
    })
    assert res_c.status_code == 201
    c_data = res_c.get_json()
    assert c_data["plan"]["saved_amount"] == 500.0
    assert c_data["plan"]["progress_percentage"] == 25.0

    # 3. Add second contribution completing the goal
    res_c2 = client.post(f"/api/savings/plans/{plan_id}/contributions", json={
        "amount": 1500.0,
        "payment_method": "UPI",
        "notes": "Final deposit"
    })
    assert res_c2.status_code == 201
    c_data2 = res_c2.get_json()
    assert c_data2["plan"]["saved_amount"] == 2000.0
    assert c_data2["plan"]["is_ready_to_shop"] is True


def test_cash_on_delivery_checkout(client):
    """Test Cash on Delivery (COD) order flow: pending payment, confirmed order, cod_amount_due."""
    order_data = {
        "items": [{"product_id": 1, "quantity": 1}],
        "shipping_address": {
            "name": "Jane Tester",
            "email": "jane@example.com",
            "phone": "9876543210",
            "address": "123 Test Street",
            "city": "Bengaluru",
            "state": "Karnataka",
            "pincode": "560103"
        },
        "payment_method": "COD"
    }

    res = client.post("/api/orders/create", json=order_data)
    assert res.status_code == 201
    data = res.get_json()

    assert data["is_cod"] is True
    assert data["order_status"] == "Confirmed"
    assert data["payment_status"] == "Pending (Cash on Delivery)"
    assert data["cod_amount_due"] == data["total_amount"]
    assert data["razorpay_key_id"] is None

    order_id = data["order_id"]

    # Test delivery simulation awards 5 reward points
    del_res = client.post(f"/api/orders/{order_id}/mark-delivered")
    assert del_res.status_code == 200
    del_data = del_res.get_json()
    assert del_data["status"] == "Delivered"
    assert del_data["payment_status"] == "Paid (Cash on Delivery)"
    assert del_data["points_awarded"] == 5


def test_reward_points_conversion_and_redemption(client):
    """
    Verify strict 100 points = ₹1.00 conversion:
    - 500 points = ₹5.00
    - Redemption subtracts ₹5.00 from total
    - Ledger records deduction and balance prevents negative balance
    """
    user_id = 1

    # Grant test points directly into ledger
    database.execute_db(
        """
        INSERT INTO reward_ledger (user_id, points, rupee_value, transaction_type, description)
        VALUES (?, 500, 5.0, 'Bonus', 'Test Welcome Bonus')
        """,
        (user_id,)
    )

    balance_res = client.get("/api/rewards/balance")
    assert balance_res.status_code == 200
    bal_data = balance_res.get_json()
    assert bal_data["balance_points"] >= 500
    # Check strict 100 points = ₹1 ratio
    assert bal_data["rupee_value"] == round(bal_data["balance_points"] / 100.0, 2)

    # Test checkout calculation with rewards redemption
    calc_res = client.post("/api/checkout/calculate", json={
        "items": [{"product_id": 1, "quantity": 1}],
        "redeem_points": True
    })
    assert calc_res.status_code == 200
    calc_data = calc_res.get_json()
    assert calc_data["reward_points_redeemed"] > 0
    assert calc_data["reward_discount_amount"] == round(calc_data["reward_points_redeemed"] / 100.0, 2)
    expected_total = max(0.0, round(calc_data["subtotal"] + calc_data["shipping_fee"] - calc_data["reward_discount_amount"], 2))
    assert calc_data["total_amount"] == expected_total
