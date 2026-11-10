"""
tests/test_budget_eighteen_scenarios.py
=======================================
Comprehensive Test Suite for Feature 4: Budget and Price Intelligence
Covers all 18 test scenarios specified in Phase 8:
1. First-time customer with no budget
2. Customer creating a monthly budget
3. Customer editing a budget
4. Customer setting category limits
5. Customer with no purchase history
6. Customer with completed purchases
7. Customer with cancelled orders (excluded from spend)
8. Customer with failed payments (excluded from spend)
9. Customer with returned or refunded purchases (excluded/retained)
10. Customer using Cash on Delivery (only counted after delivery & payment)
11. Customer checking cart affordability
12. Customer exceeding their budget
13. Customer comparing catalogue product prices
14. Customer creating and updating a savings goal
15. Customer adding savings contributions
16. Customer checking monthly spending charts
17. Tenant isolation: Customer accessing another customer's budget or savings data
18. Mobile, tablet, and desktop layout rendering (HTTP 200 & DOM structure)
"""

import pytest
import json
import uuid
from datetime import date, datetime, timedelta, timezone

import app as flask_app
import database
import services.budget_intelligence_service as bis


@pytest.fixture
def client():
    flask_app.app.config["TESTING"] = True
    with flask_app.app.test_client() as client:
        yield client


@pytest.fixture
def test_user():
    """Create an isolated test customer for financial tests."""
    email = f"budget_test_{uuid.uuid4().hex[:8]}@example.com"
    user_id = database.execute_db(
        "INSERT INTO users (username, email) VALUES (?, ?)",
        ("Budget Test Customer", email)
    )
    yield user_id
    # Cleanup
    database.execute_db("DELETE FROM customer_budgets WHERE user_id = ?", (user_id,))
    database.execute_db("DELETE FROM category_budget_allocations WHERE user_id = ?", (user_id,))
    database.execute_db("DELETE FROM savings_contributions WHERE user_id = ?", (user_id,))
    database.execute_db("DELETE FROM savings_plans WHERE user_id = ?", (user_id,))
    database.execute_db("DELETE FROM orders WHERE user_id = ?", (user_id,))
    database.execute_db("DELETE FROM shopping_preferences WHERE user_id = ?", (user_id,))
    database.execute_db("DELETE FROM users WHERE id = ?", (user_id,))


# Scenario 1: First-time customer with no budget
def test_scenario_01_first_time_customer_no_budget(client, test_user):
    with client.session_transaction() as sess:
        sess["user_id"] = test_user

    res = client.get("/api/budget/overview")
    assert res.status_code == 200
    data = res.get_json()
    assert data["has_budget"] is False
    assert data["monthly_spent"] == 0.0
    assert data["budget_remaining"] == 0.0


# Scenario 2: Customer creating a monthly budget
def test_scenario_02_create_monthly_budget(client, test_user):
    with client.session_transaction() as sess:
        sess["user_id"] = test_user

    payload = {
        "budget_period": "monthly",
        "overall_budget": 15000.0,
        "notes": "November shopping limit"
    }
    res = client.post("/api/budget/manage", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["overall_budget"] == 15000.0
    assert data["budget_period"] == "monthly"

    # Verify overview reflects the new budget
    ov_res = client.get("/api/budget/overview")
    ov_data = ov_res.get_json()
    assert ov_data["has_budget"] is True
    assert ov_data["budget_max"] == 15000.0


# Scenario 3: Customer editing a budget
def test_scenario_03_edit_budget(client, test_user):
    with client.session_transaction() as sess:
        sess["user_id"] = test_user

    # Create initial budget
    client.post("/api/budget/manage", json={"budget_period": "monthly", "overall_budget": 12000.0})
    # Edit to higher amount
    res = client.post("/api/budget/manage", json={"budget_period": "monthly", "overall_budget": 20000.0})
    assert res.status_code == 200
    assert res.get_json()["overall_budget"] == 20000.0

    ov = client.get("/api/budget/overview").get_json()
    assert ov["budget_max"] == 20000.0


# Scenario 4: Customer setting category limits
def test_scenario_04_category_limits(client, test_user):
    with client.session_transaction() as sess:
        sess["user_id"] = test_user

    payload = {
        "budget_period": "monthly",
        "overall_budget": 25000.0,
        "category_allocations": {
            "Fashion": 5000.0,
            "Electronics": 10000.0,
            "Home & Kitchen": 4000.0
        }
    }
    res = client.post("/api/budget/manage", json=payload)
    assert res.status_code == 200

    cat_res = client.get("/api/budget/categories")
    assert cat_res.status_code == 200
    cat_data = cat_res.get_json()
    categories = {c["category"]: c["allocated"] for c in cat_data["categories"]}
    assert categories.get("Fashion") == 5000.0
    assert categories.get("Electronics") == 10000.0
    assert categories.get("Home & Kitchen") == 4000.0


# Scenario 5: Customer with no purchase history
def test_scenario_05_no_purchase_history(client, test_user):
    with client.session_transaction() as sess:
        sess["user_id"] = test_user

    res = client.get("/api/budget/spending-overview?date_filter=current_month")
    assert res.status_code == 200
    data = res.get_json()
    assert data["total_spent"] == 0.0
    assert data["eligible_purchases_count"] == 0
    assert data["average_order_value"] == 0.0
    assert len(data["recent_purchases"]) == 0


# Scenario 6: Customer with completed purchases
def test_scenario_06_completed_purchases(client, test_user):
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    # Insert completed order
    database.execute_db(
        """
        INSERT INTO orders 
            (order_number, user_id, customer_name, customer_email, customer_phone,
             shipping_address, city, state, pincode, subtotal, tax, shipping_fee,
             total_amount, status, payment_status, payment_method, created_at)
        VALUES (?, ?, 'Test User', 'test@example.com', '9999999999',
                '123 MG Road', 'Bengaluru', 'Karnataka', '560001',
                2000.0, 100.0, 0.0, 2100.0, 'Confirmed', 'Paid (Sandbox Verified)', 'PreTwin Sandbox', ?)
        """,
        (f"PT-{uuid.uuid4().hex[:6].upper()}", test_user, now_str)
    )

    overview = bis.SpendingCalculationEngine.get_spending_overview(test_user, date_filter="current_month")
    assert overview["total_spent"] == 2100.0
    assert overview["eligible_purchases_count"] == 1
    assert overview["average_order_value"] == 2100.0


# Scenario 7: Customer with cancelled orders (excluded from spend)
def test_scenario_07_cancelled_orders_excluded(client, test_user):
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    database.execute_db(
        """
        INSERT INTO orders 
            (order_number, user_id, customer_name, customer_email, customer_phone,
             shipping_address, city, state, pincode, subtotal, tax, shipping_fee,
             total_amount, status, payment_status, payment_method, created_at)
        VALUES (?, ?, 'Test User', 'test@example.com', '9999999999',
                '123 MG Road', 'Bengaluru', 'Karnataka', '560001',
                4000.0, 200.0, 0.0, 4200.0, 'Cancelled', 'Pending', 'PreTwin Sandbox', ?)
        """,
        (f"PT-CAN-{uuid.uuid4().hex[:6].upper()}", test_user, now_str)
    )

    overview = bis.SpendingCalculationEngine.get_spending_overview(test_user, date_filter="current_month")
    assert overview["total_spent"] == 0.0
    assert overview["eligible_purchases_count"] == 0


# Scenario 8: Customer with failed payments (excluded from spend)
def test_scenario_08_failed_payments_excluded(client, test_user):
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    database.execute_db(
        """
        INSERT INTO orders 
            (order_number, user_id, customer_name, customer_email, customer_phone,
             shipping_address, city, state, pincode, subtotal, tax, shipping_fee,
             total_amount, status, payment_status, payment_method, created_at)
        VALUES (?, ?, 'Test User', 'test@example.com', '9999999999',
                '123 MG Road', 'Bengaluru', 'Karnataka', '560001',
                3000.0, 150.0, 0.0, 3150.0, 'Payment Failed', 'failed', 'Razorpay', ?)
        """,
        (f"PT-FAIL-{uuid.uuid4().hex[:6].upper()}", test_user, now_str)
    )

    overview = bis.SpendingCalculationEngine.get_spending_overview(test_user, date_filter="current_month")
    assert overview["total_spent"] == 0.0
    assert overview["eligible_purchases_count"] == 0


# Scenario 9: Customer with returned or refunded purchases
def test_scenario_09_refunded_orders_excluded(client, test_user):
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    database.execute_db(
        """
        INSERT INTO orders 
            (order_number, user_id, customer_name, customer_email, customer_phone,
             shipping_address, city, state, pincode, subtotal, tax, shipping_fee,
             total_amount, status, payment_status, payment_method, created_at)
        VALUES (?, ?, 'Test User', 'test@example.com', '9999999999',
                '123 MG Road', 'Bengaluru', 'Karnataka', '560001',
                5000.0, 250.0, 0.0, 5250.0, 'Returned', 'refunded', 'COD', ?)
        """,
        (f"PT-REF-{uuid.uuid4().hex[:6].upper()}", test_user, now_str)
    )

    overview = bis.SpendingCalculationEngine.get_spending_overview(test_user, date_filter="current_month")
    assert overview["total_spent"] == 0.0
    assert overview["eligible_purchases_count"] == 0


# Scenario 10: Customer using Cash on Delivery (COD)
def test_scenario_10_cash_on_delivery_status(client, test_user):
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    # 1. Undelivered / Pending COD order -> NOT counted as spend
    database.execute_db(
        """
        INSERT INTO orders 
            (order_number, user_id, customer_name, customer_email, customer_phone,
             shipping_address, city, state, pincode, subtotal, tax, shipping_fee,
             total_amount, status, payment_status, payment_method, created_at)
        VALUES (?, ?, 'Test User', 'test@example.com', '9999999999',
                '123 MG Road', 'Bengaluru', 'Karnataka', '560001',
                1200.0, 60.0, 40.0, 1300.0, 'Confirmed', 'Pending (Cash on Delivery)', 'COD', ?)
        """,
        (f"PT-COD-PEND-{uuid.uuid4().hex[:6].upper()}", test_user, now_str)
    )

    ov1 = bis.SpendingCalculationEngine.get_spending_overview(test_user, date_filter="current_month")
    assert ov1["total_spent"] == 0.0

    # 2. Delivered & Paid COD order -> COUNTED as spend
    database.execute_db(
        """
        INSERT INTO orders 
            (order_number, user_id, customer_name, customer_email, customer_phone,
             shipping_address, city, state, pincode, subtotal, tax, shipping_fee,
             total_amount, status, payment_status, payment_method, created_at)
        VALUES (?, ?, 'Test User', 'test@example.com', '9999999999',
                '123 MG Road', 'Bengaluru', 'Karnataka', '560001',
                1800.0, 90.0, 0.0, 1890.0, 'Delivered', 'Paid (Cash on Delivery)', 'COD', ?)
        """,
        (f"PT-COD-PAID-{uuid.uuid4().hex[:6].upper()}", test_user, now_str)
    )

    ov2 = bis.SpendingCalculationEngine.get_spending_overview(test_user, date_filter="current_month")
    assert ov2["total_spent"] == 1890.0
    assert ov2["eligible_purchases_count"] == 1


# Scenario 11: Customer checking cart affordability
def test_scenario_11_cart_affordability(client, test_user):
    with client.session_transaction() as sess:
        sess["user_id"] = test_user

    # Set budget = 10,000
    client.post("/api/budget/manage", json={"budget_period": "monthly", "overall_budget": 10000.0})

    # Proposed cart = 2500
    res = client.post("/api/budget/affordability", json={"cart_subtotal": 2500.0})
    assert res.status_code == 200
    data = res.get_json()
    assert data["has_budget"] is True
    assert data["overall_budget"] == 10000.0
    assert data["cart_subtotal"] == 2500.0
    # Free shipping on 2500
    assert data["shipping_fee"] == 0.0
    assert data["final_payable"] == 2500.0
    assert data["remaining_budget_after"] == 7500.0
    assert data["is_over_budget"] is False
    assert data["warning_level"] == "success"


# Scenario 12: Customer exceeding their budget
def test_scenario_12_customer_exceeding_budget(client, test_user):
    with client.session_transaction() as sess:
        sess["user_id"] = test_user

    # Set budget = 5,000
    client.post("/api/budget/manage", json={"budget_period": "monthly", "overall_budget": 5000.0})

    # Proposed cart = 6500 (exceeds 5000 by 1500)
    res = client.post("/api/budget/affordability", json={"cart_subtotal": 6500.0})
    assert res.status_code == 200
    data = res.get_json()
    assert data["is_over_budget"] is True
    assert data["over_budget_amount"] == 1500.0
    assert data["warning_level"] == "danger"
    assert "exceed your monthly budget" in data["warning_message"]


# Scenario 13: Customer comparing catalogue product prices
def test_scenario_13_catalogue_price_comparison(client):
    res = client.get("/api/budget/price-intelligence?product_id=1")
    assert res.status_code == 200
    data = res.get_json()
    assert "selling_price" in data
    assert "mrp" in data
    assert "discount_percentage" in data
    assert "value_label" in data
    assert "affordable_alternatives" in data
    assert isinstance(data["affordable_alternatives"], list)


# Scenario 14: Customer creating and updating a savings goal
def test_scenario_14_create_and_update_savings_goal(client, test_user):
    with client.session_transaction() as sess:
        sess["user_id"] = test_user

    target_date = (date.today() + timedelta(days=90)).strftime("%Y-%m-%d")
    create_res = client.post("/api/savings/plans", json={
        "goal_title": "Sony Noise Cancelling Headphones",
        "target_amount": 15000.0,
        "target_date": target_date,
        "initial_deposit": 2000.0
    })
    assert create_res.status_code in [200, 201]
    plan_data = create_res.get_json()
    plan_id = plan_data["plan"]["id"]

    # Verify savings summary endpoint captures it
    summary = client.get("/api/budget/savings-summary").get_json()
    assert summary["total_plans"] >= 1
    found = any(p["id"] == plan_id for p in summary["plans"])
    assert found is True


# Scenario 15: Customer adding savings contributions
def test_scenario_15_add_savings_contribution(client, test_user):
    with client.session_transaction() as sess:
        sess["user_id"] = test_user

    target_date = (date.today() + timedelta(days=60)).strftime("%Y-%m-%d")
    create_res = client.post("/api/savings/plans", json={
        "goal_title": "Emergency Fund",
        "target_amount": 10000.0,
        "target_date": target_date
    })
    plan_id = create_res.get_json()["plan"]["id"]

    # Deposit contribution
    contrib_res = client.post(f"/api/savings/plans/{plan_id}/contributions", json={
        "amount": 2500.0,
        "note": "Bonus allocation"
    })
    assert contrib_res.status_code in [200, 201]

    # Verify savings summary reflects new saved amount
    summary = client.get("/api/budget/savings-summary").get_json()
    plan = next(p for p in summary["plans"] if p["id"] == plan_id)
    assert plan["current_saved"] == 2500.0
    assert plan["progress_percentage"] == 25.0


# Scenario 16: Customer checking monthly spending charts
def test_scenario_16_monthly_spending_charts(client, test_user):
    with client.session_transaction() as sess:
        sess["user_id"] = test_user

    res = client.get("/api/budget/spending-overview?date_filter=last_90_days")
    assert res.status_code == 200
    data = res.get_json()
    assert "monthly_trend" in data
    assert len(data["monthly_trend"]) == 6
    for m in data["monthly_trend"]:
        assert "month_label" in m
        assert "spent" in m
        assert "orders_count" in m


# Scenario 17: Tenant isolation: Customer accessing another customer's data
def test_scenario_17_tenant_isolation(client, test_user):
    # Create User B
    user_b = database.execute_db(
        "INSERT INTO users (username, email) VALUES (?, ?)",
        ("User B", f"user_b_{uuid.uuid4().hex[:6]}@example.com")
    )
    # Give User B a budget of 50,000
    database.execute_db(
        "INSERT INTO customer_budgets (user_id, period_start, period_end, overall_budget, status) VALUES (?, '2026-11-01', '2026-11-30', 50000.0, 'active')",
        (user_b,)
    )

    # Login as test_user (User A)
    with client.session_transaction() as sess:
        sess["user_id"] = test_user

    # User A requests overview -> must NOT see User B's 50,000 budget
    res = client.get("/api/budget/overview")
    data = res.get_json()
    assert data["budget_max"] != 50000.0

    # Cleanup user B
    database.execute_db("DELETE FROM customer_budgets WHERE user_id = ?", (user_b,))
    database.execute_db("DELETE FROM users WHERE id = ?", (user_b,))


# Scenario 18: Mobile, tablet, and desktop layout rendering
def test_scenario_18_responsive_layout_rendering(client):
    res = client.get("/budget")
    assert res.status_code == 200
    html = res.data.decode("utf-8")

    # Check that all 7 sections / navigation links are present in DOM
    assert "budget-section-setup" in html
    assert "budget-section-spending" in html
    assert "budget-section-categories" in html
    assert "budget-section-pricing" in html
    assert "budget-section-savings" in html
    assert "budget-section-affordability" in html
    assert "budget-section-insights" in html

    # Check that backward compatible IDs exist
    assert 'id="monthlySpent"' in html
    assert 'id="budgetMax"' in html
    assert 'id="budgetRemaining"' in html
    assert 'id="budgetSpentPercent"' in html
    assert 'id="budgetProgressBar"' in html
    assert 'id="budgetHealthBadge"' in html
    assert 'id="totalTrackedCount"' in html
    assert 'id="activeDropsCount"' in html
    assert 'id="unlockedSavings"' in html
    assert 'id="priceHistoryProductSelect"' in html
    assert 'id="priceHistoryChart"' in html
    assert 'id="trackedTableBody"' in html

    # Verify Soft Lavender color palette elements
    assert "#F7F3FF" in html
    assert "#FFFDF9" in html
    assert "#C4A6F5" in html
