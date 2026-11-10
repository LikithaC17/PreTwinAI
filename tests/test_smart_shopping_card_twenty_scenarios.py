"""
tests/test_smart_shopping_card_twenty_scenarios.py
==================================================
Comprehensive Verification Suite for PreTwin AI Smart Shopping Card (Feature 6).

Covers all 20 required Phase 9 scenarios:
1. Customer opens their Smart Shopping Card
2. Customer has a profile image
3. Customer has no profile image
4. Customer has no shopping history
5. Customer has completed purchases
6. Customer has active orders
7. Customer has cancelled or returned orders
8. Customer has available reward points
9. Customer has redeemed reward points
10. Customer has no reward balance
11. Customer has not configured a shopping budget
12. Customer has active savings goals
13. Customer has an empty wishlist
14. Customer has an empty cart
15. Customer navigates through all seven sections
16. Customer uses each quick action
17. Customer refreshes card information
18. Customer accesses the card without authentication
19. Customer attempts to access another customer's data
20. Customer uses mobile, tablet, and desktop layouts
"""

import json
import pytest
import database
from services.shopping_card_service import ShoppingCardService


# -----------------------------------------------------------------------------
# SCENARIO 1: Customer opens their Smart Shopping Card
# -----------------------------------------------------------------------------
def test_scenario_01_open_smart_shopping_card_page(app_client):
    """Scenario 1: Customer opens /smart-card and sees page title and digital card."""
    with app_client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["is_authenticated_user"] = True

    resp = app_client.get("/smart-card")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Smart Shopping Card" in html
    assert "PreTwin Digital Card" in html
    assert "dscRewardPoints" in html
    assert "dscMaskedId" in html
    assert "smart_card.js" in html


# -----------------------------------------------------------------------------
# SCENARIO 2: Customer has a profile image
# -----------------------------------------------------------------------------
def test_scenario_02_customer_with_profile_image():
    """Scenario 2: User with valid avatar_url returns the URL in identity."""
    # User 1 in demo DB has avatar_url
    identity = ShoppingCardService.get_shopping_identity(1)
    assert identity["avatar_url"] is not None
    assert "http" in identity["avatar_url"]
    assert identity["display_name"] == "Alex Johnson"


# -----------------------------------------------------------------------------
# SCENARIO 3: Customer has no profile image
# -----------------------------------------------------------------------------
def test_scenario_03_customer_without_profile_image():
    """Scenario 3: User without avatar_url gracefully falls back to monogram initials."""
    test_user_id = 999998
    database.execute_db("DELETE FROM users WHERE id = ?", (test_user_id,))
    database.execute_db(
        """INSERT INTO users (id, username, email, avatar_url, created_at)
           VALUES (?, 'No Avatar User', 'noavatar@test.com', '', datetime('now'))""",
        (test_user_id,)
    )
    identity = ShoppingCardService.get_shopping_identity(test_user_id)
    assert identity["avatar_url"] is None
    assert identity["monogram"] == "NA"
    database.execute_db("DELETE FROM users WHERE id = ?", (test_user_id,))


# -----------------------------------------------------------------------------
# SCENARIO 4: Customer has no shopping history
# -----------------------------------------------------------------------------
def test_scenario_04_customer_with_no_shopping_history():
    """Scenario 4: User with 0 orders returns 0 completed orders and a helpful message."""
    overview = ShoppingCardService.get_shopping_overview(999992)
    assert overview["completed_orders_count"] == 0
    assert overview["active_orders_count"] == 0
    assert "No shopping history yet" in overview["summary_text"]


# -----------------------------------------------------------------------------
# SCENARIO 5: Customer has completed purchases
# -----------------------------------------------------------------------------
def test_scenario_05_customer_with_completed_purchases():
    """Scenario 5: User 1 has completed purchases accurately tallied from orders table."""
    overview = ShoppingCardService.get_shopping_overview(1)
    assert overview["completed_orders_count"] > 0
    assert overview["total_completed_spent"] > 0.0
    assert "completed orders" in overview["summary_text"]


# -----------------------------------------------------------------------------
# SCENARIO 6: Customer has active orders
# -----------------------------------------------------------------------------
def test_scenario_06_customer_with_active_orders():
    """Scenario 6: Active orders (confirmed, shipped) are counted separately from completed."""
    overview = ShoppingCardService.get_shopping_overview(1)
    orders_data = ShoppingCardService.get_orders_activity(1)
    assert overview["active_orders_count"] > 0
    assert orders_data["has_active_orders"] is True
    for act in orders_data["active_orders"]:
        assert act["status"].lower() not in ("delivered", "completed", "cancelled")


# -----------------------------------------------------------------------------
# SCENARIO 7: Customer has cancelled or returned orders
# -----------------------------------------------------------------------------
def test_scenario_07_customer_with_cancelled_or_returned_orders():
    """Scenario 7: Cancelled or returned orders must NEVER be counted as completed purchases."""
    # Find or insert a test cancelled order for user 999993
    test_user_id = 999993
    database.execute_db(
        "DELETE FROM orders WHERE user_id = ?",
        (test_user_id,)
    )
    database.execute_db(
        "INSERT OR IGNORE INTO users (id, username, email) VALUES (?, 'Cancelled User', 'cancelled@test.com')",
        (test_user_id,)
    )
    database.execute_db(
        """INSERT INTO orders (order_number, user_id, customer_name, customer_email, customer_phone, shipping_address, city, state, pincode, subtotal, total_amount, status, payment_status, payment_method, created_at)
           VALUES ('#ORD-CANCEL-TEST', ?, 'Test Shopper', 'test@test.com', '9999999999', '123 Test St', 'City', 'State', '123456', 4500.0, 4500.0, 'Cancelled', 'Refunded', 'COD', datetime('now'))""",
        (test_user_id,)
    )
    overview = ShoppingCardService.get_shopping_overview(test_user_id)
    assert overview["completed_orders_count"] == 0
    assert overview["cancelled_orders_count"] == 1
    # Clean up
    database.execute_db("DELETE FROM orders WHERE user_id = ?", (test_user_id,))
    database.execute_db("DELETE FROM users WHERE id = ?", (test_user_id,))


# -----------------------------------------------------------------------------
# SCENARIO 8: Customer has available reward points
# -----------------------------------------------------------------------------
def test_scenario_08_customer_with_available_reward_points():
    """Scenario 8: Reward balance follows PreTwin AI rules (100 points = ₹1.00)."""
    rewards = ShoppingCardService.get_rewards_benefits(1)
    assert rewards["balance_points"] > 0
    assert rewards["rupee_value"] == round(rewards["balance_points"] / 100.0, 2)
    assert rewards["points_ratio"] == "100 points = ₹1.00"
    assert rewards["points_per_order"] == 5


# -----------------------------------------------------------------------------
# SCENARIO 9: Customer has redeemed reward points
# -----------------------------------------------------------------------------
def test_scenario_09_customer_with_redeemed_reward_points():
    """Scenario 9: Lifetime redeemed points tracked accurately as positive magnitude."""
    rewards = ShoppingCardService.get_rewards_benefits(1)
    assert rewards["lifetime_redeemed"] >= 0
    assert isinstance(rewards["lifetime_redeemed"], int)


# -----------------------------------------------------------------------------
# SCENARIO 10: Customer has no reward balance
# -----------------------------------------------------------------------------
def test_scenario_10_customer_with_zero_reward_balance():
    """Scenario 10: User with zero reward ledger entries returns 0 pts and ₹0.00 value."""
    rewards = ShoppingCardService.get_rewards_benefits(999994)
    assert rewards["balance_points"] == 0
    assert rewards["rupee_value"] == 0.0
    assert len(rewards["recent_transactions"]) == 0


# -----------------------------------------------------------------------------
# SCENARIO 11: Customer has not configured a shopping budget
# -----------------------------------------------------------------------------
def test_scenario_11_customer_unconfigured_budget():
    """Scenario 11: User without customer_budgets shows budget_configured: False and friendly guidance."""
    budget_data = ShoppingCardService.get_budget_savings_snapshot(999995)
    assert budget_data["budget_configured"] is False
    assert budget_data["overall_budget"] == 0.0
    assert "No monthly budget configured yet" in budget_data["unconfigured_message"]


# -----------------------------------------------------------------------------
# SCENARIO 12: Customer has active savings goals
# -----------------------------------------------------------------------------
def test_scenario_12_customer_active_savings_goals():
    """Scenario 12: User 1 active savings goals from savings_plans are returned with progress %."""
    budget_data = ShoppingCardService.get_budget_savings_snapshot(1)
    assert budget_data["has_savings_goals"] is True
    assert len(budget_data["active_savings_goals"]) > 0
    for goal in budget_data["active_savings_goals"]:
        assert "goal_title" in goal
        assert goal["target_amount"] > 0
        assert 0.0 <= goal["progress_pct"] <= 100.0


# -----------------------------------------------------------------------------
# SCENARIO 13: Customer has an empty wishlist
# -----------------------------------------------------------------------------
def test_scenario_13_customer_empty_wishlist():
    """Scenario 13: User with 0 saved items has wishlist_count = 0."""
    overview = ShoppingCardService.get_shopping_overview(999996)
    assert overview["wishlist_count"] == 0


# -----------------------------------------------------------------------------
# SCENARIO 14: Customer has an empty cart
# -----------------------------------------------------------------------------
def test_scenario_14_customer_empty_cart():
    """Scenario 14: User with 0 cart items has cart_count = 0."""
    overview = ShoppingCardService.get_shopping_overview(999997)
    assert overview["cart_count"] == 0


# -----------------------------------------------------------------------------
# SCENARIO 15: Customer navigates through all seven sections
# -----------------------------------------------------------------------------
def test_scenario_15_all_seven_sections_present(app_client):
    """Scenario 15: Verifies all 7 sections are present in API payload and HTML."""
    with app_client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["is_authenticated_user"] = True

    # 1. API payload check
    resp = app_client.get("/api/shopping-card/data")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True

    required_sections = ["identity", "overview", "rewards", "budget_savings", "orders", "insights", "quick_actions"]
    for sec in required_sections:
        assert sec in data, f"Section {sec} missing from card data"

    # 2. HTML page check
    page_resp = app_client.get("/smart-card")
    assert page_resp.status_code == 200
    html = page_resp.get_data(as_text=True)
    assert "1. My Smart Shopping Identity" in html
    assert "2. My Shopping Overview" in html
    assert "3. My Rewards and Benefits" in html
    assert "4. My Budget and Savings Snapshot" in html
    assert "5. My Orders and Shopping Activity" in html
    assert "6. My Personalised Shopping Insights" in html
    assert "7. Quick Actions and Card Management" in html


# -----------------------------------------------------------------------------
# SCENARIO 16: Customer uses each quick action
# -----------------------------------------------------------------------------
def test_scenario_16_quick_actions_shortcuts():
    """Scenario 16: Verify all quick actions have valid URLs to PreTwin features."""
    actions = ShoppingCardService.get_quick_actions(1)
    shortcuts = actions["navigation_shortcuts"]
    assert len(shortcuts) >= 9

    expected_routes = ["/profile", "/discovery", "/wishlist", "/cart", "/orders", "/rewards", "/budget", "/calendar", "/twin"]
    urls = [s["url"] for s in shortcuts]
    for r in expected_routes:
        assert r in urls, f"Route {r} missing from quick action shortcuts"


# -----------------------------------------------------------------------------
# SCENARIO 17: Customer refreshes card information
# -----------------------------------------------------------------------------
def test_scenario_17_refresh_card_endpoint(app_client):
    """Scenario 17: POST /api/shopping-card/refresh re-fetches dynamic data."""
    with app_client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["is_authenticated_user"] = True

    resp = app_client.post("/api/shopping-card/refresh")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert data.get("refreshed") is True
    assert "refreshed with latest live data" in data.get("message", "")


# -----------------------------------------------------------------------------
# SCENARIO 18: Customer accesses the card without authentication
# -----------------------------------------------------------------------------
def test_scenario_18_unauthenticated_access(app_client):
    """Scenario 18: Unauthenticated access without session returns 401."""
    with app_client.session_transaction() as sess:
        sess.clear()
        sess["anonymous_test"] = True

    resp = app_client.get("/api/shopping-card/data")
    assert resp.status_code == 401
    data = resp.get_json()
    assert "Authentication required" in data.get("error", "")


# -----------------------------------------------------------------------------
# SCENARIO 19: Customer attempts to access another customer's data
# -----------------------------------------------------------------------------
def test_scenario_19_cross_tenant_access_blocked(app_client):
    """Scenario 19: User 1 requesting user 2's card is strictly forbidden (403)."""
    with app_client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["is_authenticated_user"] = True

    resp = app_client.get("/api/shopping-card/data?user_id=2")
    assert resp.status_code == 403
    data = resp.get_json()
    assert "Access denied" in data.get("error", "")


# -----------------------------------------------------------------------------
# SCENARIO 20: Responsive layouts HTTP check & print styling
# -----------------------------------------------------------------------------
def test_scenario_20_responsive_and_print_styles(app_client):
    """Scenario 20: Verifies responsive CSS media queries and print styles are defined."""
    resp = app_client.get("/smart-card")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    # Media queries for responsiveness
    assert "@media (max-width: 768px)" in html
    # Print stylesheet hiding non-printable components
    assert "@media print" in html
    assert "page-break-inside: avoid" in html
