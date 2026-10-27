"""
test_comparison_and_card.py
Verifies:
1. Product Comparison API & UI elements
2. Digital Shopping Card in Smart Cart (/smart-cart)
3. Personalization & Digital Twin (/twin)
4. Predictive Shopping Intelligence (/predictions)
5. Fairy-Tale Startup Intro & Login transition elements
"""

import json
import pytest

def test_api_comparison_two_products(app_client):
    """Test POST /api/comparisons with two products."""
    payload = {"product_ids": [1, 2]}
    resp = app_client.post(
        "/api/comparisons",
        data=json.dumps(payload),
        content_type="application/json"
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert "comparison_table" in data or "products" in data
    products = data.get("products", [])
    assert len(products) >= 2
    # Ensure critical comparison fields exist
    for p in products:
        assert "name" in p or "product_name" in p
        assert "price" in p
        assert "category" in p


def test_api_comparison_cross_category(app_client):
    """Test POST /api/comparisons with products from different categories without dropping."""
    payload = {"product_ids": [1, 4]}  # Headphones (Electronics) and Shoes (Fashion)
    resp = app_client.post(
        "/api/comparisons",
        data=json.dumps(payload),
        content_type="application/json"
    )
    assert resp.status_code == 200
    data = resp.get_json()
    products = data.get("products", [])
    assert len(products) == 2


def test_comparison_page_rendered(app_client):
    """Test GET /comparison renders comparison dashboard."""
    resp = app_client.get("/comparison")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Compare Products" in html or "Product Comparison" in html
    assert "comparison.js" in html


def test_smart_cart_digital_shopping_card(app_client):
    """Test GET /smart-cart contains PreTwin Digital Shopping Card and metrics."""
    resp = app_client.get("/smart-cart")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "PreTwin Digital Card" in html
    assert "dscRewardPoints" in html
    assert "dscSavedAmount" in html
    assert "dscMaskedId" in html
    assert "No shopping credits available (₹0)" in html
    assert "smart_cart.js" in html


def test_rewards_balance_api(app_client):
    """Test GET /api/rewards/balance returns 100 points = ₹1 ratio."""
    resp = app_client.get("/api/rewards/balance")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "balance_points" in data
    assert "rupee_value" in data
    assert data.get("points_ratio") == "100 points = ₹1.00"


def test_savings_plans_api(app_client):
    """Test GET /api/savings/plans returns calculated savings stats."""
    resp = app_client.get("/api/savings/plans")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "plans" in data or isinstance(data, list)


def test_twin_page_tabs_and_overview(app_client):
    """Test GET /twin renders upgraded overview, tabs, and recommendation grid."""
    resp = app_client.get("/twin")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "twinArchetype" in html
    assert "twinPreferenceTabs" in html
    assert "twinRecsGrid" in html
    assert "twin.js" in html


def test_predictions_page_timeline_and_seasonal(app_client):
    """Test GET /predictions renders upcoming needs timeline and seasonal picks."""
    resp = app_client.get("/predictions")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "upcomingNeedsTimeline" in html
    assert "remindersContainer" in html
    assert "seasonalSuggestionsGrid" in html
    assert "predictions.js" in html


def test_login_page_renders_cleanly(app_client):
    """Test GET /login renders Welcome to PreTwin sign-in experience."""
    resp = app_client.get("/login")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Welcome to PreTwin" in html
    assert "Sign In" in html


def test_startup_intro_overlay_present(app_client):
    """Test GET / includes fairy startup animation markup."""
    resp = app_client.get("/")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "pretwinStartupIntro" in html
    assert "PreTwin" in html
    assert "Your Future. Your Style. Your Twin." in html
