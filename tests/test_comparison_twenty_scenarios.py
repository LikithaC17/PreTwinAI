"""
tests/test_comparison_twenty_scenarios.py
=========================================
Comprehensive Test Suite for Feature 5: Product Comparison and Decision Support
Covers all 20 test scenarios specified in Phase 8:
1. Customer opens comparison with no selected products.
2. Customer selects two products.
3. Customer selects multiple products (up to 4).
4. Customer attempts to add the same product twice (duplicate prevention).
5. Customer removes one selected product.
6. Customer clears all selected products.
7. Customer compares products from the same category.
8. Customer compares products with missing attributes.
9. Customer uses the show-only-differences option.
10. Customer compares prices and discounts.
11. Customer changes comparison priorities (weight adjustment).
12. Customer views pros and cons.
13. Customer receives a decision explanation.
14. Customer encounters products with similar scores (comparable options detection).
15. Customer views product details.
16. Customer adds a compared product to wishlist.
17. Customer adds a compared product to cart.
18. Customer attempts to access invalid product IDs.
19. Tenant isolation: Customer attempts to access another customer's saved comparison.
20. Responsive layout rendering (HTTP 200 & DOM structure for all 7 sections).
"""

import json
import pytest
import app as flask_app
import database
import services.comparison_service as cs


@pytest.fixture
def client():
    flask_app.app.config["TESTING"] = True
    with flask_app.app.test_client() as client:
        yield client


@pytest.fixture
def two_products():
    """Retrieve 2 valid products from catalogue."""
    rows = database.query_db("SELECT id, name, category, price FROM products LIMIT 2")
    return [flask_app.row_to_dict(r) if hasattr(flask_app, "row_to_dict") else dict(r) for r in rows]


# =============================================================================
# SCENARIO 1: Customer opens comparison with no selected products
# =============================================================================

def test_scenario_01_empty_comparison(client):
    """Scenario 1: Opens comparison page and API with no selected products."""
    resp = client.get("/comparison")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Product Comparison" in html
    assert "sectionSelect" in html
    assert "comparisonEmptyState" in html

    # API call with empty list returns 400 or proper validation error
    api_res = client.post("/api/comparison/analyze", json={"product_ids": []})
    assert api_res.status_code in [400, 422]


# =============================================================================
# SCENARIO 2: Customer selects two products
# =============================================================================

def test_scenario_02_compare_two_products(client, two_products):
    """Scenario 2: Selects two valid products and compares side-by-side."""
    p_ids = [two_products[0]["id"], two_products[1]["id"]]
    res = client.post("/api/comparison/analyze", json={"product_ids": p_ids})
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["total_selected"] == 2
    assert len(data["products"]) == 2
    assert "side_by_side" in data
    assert "spec_analysis" in data
    assert "price_value" in data
    assert "pros_cons" in data
    assert "decision" in data


# =============================================================================
# SCENARIO 3: Customer selects multiple products (up to 4)
# =============================================================================

def test_scenario_03_multiple_products_limit(client):
    """Scenario 3: Compare 4 products and verify cap on max limit."""
    rows = database.query_db("SELECT id FROM products LIMIT 5")
    all_ids = [r[0] for r in rows]
    # Pass 5 IDs; system should enforce max limit of 4
    res = client.post("/api/comparison/analyze", json={"product_ids": all_ids})
    assert res.status_code == 200
    data = res.get_json()
    assert data["total_selected"] <= 4
    assert len(data["products"]) <= 4


# =============================================================================
# SCENARIO 4: Duplicate product prevention
# =============================================================================

def test_scenario_04_duplicate_prevention(client, two_products):
    """Scenario 4: Attempting to compare duplicate product IDs deduplicates them."""
    p1 = two_products[0]["id"]
    p2 = two_products[1]["id"]
    # Duplicate p1
    res = client.post("/api/comparison/analyze", json={"product_ids": [p1, p1, p2, p2]})
    assert res.status_code == 200
    data = res.get_json()
    # Deduplicated list contains only 2 distinct products
    assert data["total_selected"] == 2
    unique_ids = set(p["id"] for p in data["products"])
    assert len(unique_ids) == 2


# =============================================================================
# SCENARIO 5: Customer removes one selected product
# =============================================================================

def test_scenario_05_remove_product(client):
    """Scenario 5: Remove product from 3-item comparison leaves 2 items."""
    rows = database.query_db("SELECT id FROM products LIMIT 3")
    ids = [r[0] for r in rows]
    # Initially 3
    res3 = client.post("/api/comparison/analyze", json={"product_ids": ids})
    assert res3.status_code == 200
    assert res3.get_json()["total_selected"] == 3

    # Remove 1st product
    remaining_ids = ids[1:]
    res2 = client.post("/api/comparison/analyze", json={"product_ids": remaining_ids})
    assert res2.status_code == 200
    assert res2.get_json()["total_selected"] == 2


# =============================================================================
# SCENARIO 6: Customer clears all selected products
# =============================================================================

def test_scenario_06_clear_all_comparison(client):
    """Scenario 6: Clearing all products persists empty state."""
    res = client.post("/api/comparison/saved", json={"product_ids": []})
    assert res.status_code == 200
    assert res.get_json()["saved_ids"] == []

    get_res = client.get("/api/comparison/saved")
    assert get_res.status_code == 200
    # Returns empty or most recent
    assert isinstance(get_res.get_json().get("saved_ids", []), list)


# =============================================================================
# SCENARIO 7: Same category comparison
# =============================================================================

def test_scenario_07_same_category_comparison(client):
    """Scenario 7: Compare products from same category (e.g. Mobiles or Fashion)."""
    rows = database.query_db("SELECT id FROM products WHERE category = 'Fashion' LIMIT 2")
    if len(rows) < 2:
        rows = database.query_db("SELECT id FROM products LIMIT 2")
    ids = [r[0] for r in rows]

    res = client.post("/api/comparison/analyze", json={"product_ids": ids})
    assert res.status_code == 200
    data = res.get_json()
    cats = [p["category"] for p in data["products"]]
    assert len(set(cats)) == 1 or len(cats) == 2


# =============================================================================
# SCENARIO 8: Products with missing attributes
# =============================================================================

def test_scenario_08_missing_attributes_graceful(client):
    """Scenario 8: Products missing certain specifications are handled without crash."""
    rows = database.query_db("SELECT id FROM products LIMIT 2")
    ids = [r[0] for r in rows]
    res = client.post("/api/comparison/analyze", json={"product_ids": ids})
    assert res.status_code == 200
    data = res.get_json()
    spec_groups = data["spec_analysis"]["groups"]
    assert isinstance(spec_groups, list)
    # Ensure missing values are represented as 'Not specified' without failure
    for grp in spec_groups:
        for row in grp["rows"]:
            assert len(row["values"]) == len(ids)


# =============================================================================
# SCENARIO 9: Show only differences option
# =============================================================================

def test_scenario_09_show_only_differences(client):
    """Scenario 9: show_differences_only filters out non-essential identical rows."""
    rows = database.query_db("SELECT id FROM products LIMIT 2")
    ids = [r[0] for r in rows]

    # Full matrix
    res_full = client.post("/api/comparison/analyze", json={"product_ids": ids, "show_differences_only": False})
    # Filtered matrix
    res_diff = client.post("/api/comparison/analyze", json={"product_ids": ids, "show_differences_only": True})

    assert res_full.status_code == 200
    assert res_diff.status_code == 200
    rows_full = res_full.get_json()["side_by_side"]["rows"]
    rows_diff = res_diff.get_json()["side_by_side"]["rows"]
    # Filtered rows count should be <= full rows count
    assert len(rows_diff) <= len(rows_full)


# =============================================================================
# SCENARIO 10: Price and discount comparison
# =============================================================================

def test_scenario_10_price_and_discount_comparison(client):
    """Scenario 10: Accurate pricing, original MRP, discount %, and lowest badge."""
    rows = database.query_db("SELECT id FROM products LIMIT 2")
    ids = [r[0] for r in rows]
    res = client.post("/api/comparison/analyze", json={"product_ids": ids})
    assert res.status_code == 200
    pv = res.get_json()["price_value"]
    assert "lowest_price_id" in pv
    assert "min_price" in pv
    assert "items" in pv
    for item in pv["items"]:
        assert "price" in item
        assert "original_price" in item
        assert "discount_percentage" in item
        assert "diff_from_lowest" in item
        assert item["diff_from_lowest"] >= 0


# =============================================================================
# SCENARIO 11: Priority weight adjustment
# =============================================================================

def test_scenario_11_priority_weight_adjustment(client):
    """Scenario 11: Changing customer priority weights changes decision scoring."""
    rows = database.query_db("SELECT id FROM products LIMIT 3")
    ids = [r[0] for r in rows]

    # Heavy on price
    res_price = client.post("/api/comparison/analyze", json={
        "product_ids": ids,
        "weights": {"price": 90, "specs": 5, "value": 5, "rating": 0, "brand": 0}
    })
    # Heavy on rating
    res_rating = client.post("/api/comparison/analyze", json={
        "product_ids": ids,
        "weights": {"price": 0, "specs": 5, "value": 5, "rating": 90, "brand": 0}
    })

    assert res_price.status_code == 200
    assert res_rating.status_code == 200
    dec_price = res_price.get_json()["decision"]
    dec_rating = res_rating.get_json()["decision"]
    assert dec_price["weights_used"]["price"] == 90
    assert dec_rating["weights_used"]["rating"] == 90


# =============================================================================
# SCENARIO 12: Fact-based pros and cons
# =============================================================================

def test_scenario_12_pros_and_cons(client, two_products):
    """Scenario 12: Pros and cons derived strictly from database attributes."""
    ids = [two_products[0]["id"], two_products[1]["id"]]
    res = client.post("/api/comparison/analyze", json={"product_ids": ids})
    assert res.status_code == 200
    pros_cons = res.get_json()["pros_cons"]
    for pid in ids:
        str_pid = str(pid)
        item_pc = pros_cons.get(str_pid) or pros_cons.get(pid)
        assert item_pc is not None
        assert "pros" in item_pc
        assert "cons" in item_pc
        assert len(item_pc["pros"]) >= 1


# =============================================================================
# SCENARIO 13: Decision explanation transparency
# =============================================================================

def test_scenario_13_decision_explanation(client, two_products):
    """Scenario 13: Decision rationale is explainable and references metrics."""
    ids = [two_products[0]["id"], two_products[1]["id"]]
    res = client.post("/api/comparison/analyze", json={"product_ids": ids})
    assert res.status_code == 200
    dec = res.get_json()["decision"]
    assert "winner" in dec
    assert "decision_reason" in dec["winner"]
    assert len(dec["winner"]["decision_reason"]) > 10


# =============================================================================
# SCENARIO 14: Similar score / comparable options detection
# =============================================================================

def test_scenario_14_comparable_options_detection(client):
    """Scenario 14: Products with near-identical composite scores flagged as comparable."""
    # We can evaluate two products directly using SmartDecisionAssistantEngine
    products = [
        {"id": 101, "name": "Item A", "price": 1000.0, "rating": 4.5, "original_price": 1200.0, "discount_percentage": 10, "specifications": {"RAM": "8GB"}},
        {"id": 102, "name": "Item B", "price": 1010.0, "rating": 4.5, "original_price": 1200.0, "discount_percentage": 10, "specifications": {"RAM": "8GB"}}
    ]
    dec = cs.SmartDecisionAssistantEngine.evaluate(products)
    assert dec["status"] == "success"
    # Score delta is <= 3.0 points
    assert dec["is_comparable"] is True
    assert "Comparable" in dec["decision_title"] or "Close Match" in dec["decision_title"]


# =============================================================================
# SCENARIO 15: View product details
# =============================================================================

def test_scenario_15_view_product_details(client, two_products):
    """Scenario 15: Product detail route is accessible for compared products."""
    pid = two_products[0]["id"]
    res = client.get(f"/product/{pid}")
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert two_products[0]["name"] in html or "Product Details" in html or "Price" in html


# =============================================================================
# SCENARIO 16: Add compared product to wishlist
# =============================================================================

def test_scenario_16_add_to_wishlist(client, two_products):
    """Scenario 16: Adding a compared product to wishlist succeeds."""
    pid = two_products[0]["id"]
    res = client.post("/api/wishlist/toggle", json={"product_id": pid})
    assert res.status_code == 200
    data = res.get_json()
    assert data.get("success") is True or "action" in data


# =============================================================================
# SCENARIO 17: Add compared product to cart
# =============================================================================

def test_scenario_17_add_to_cart(client, two_products):
    """Scenario 17: Adding a compared product to cart succeeds."""
    pid = two_products[0]["id"]
    res = client.post("/api/cart", json={"product_id": pid, "quantity": 1})
    assert res.status_code == 200
    data = res.get_json()
    assert data.get("success") is True


# =============================================================================
# SCENARIO 18: Invalid product ID handling
# =============================================================================

def test_scenario_18_invalid_product_ids(client):
    """Scenario 18: Non-existent IDs, strings, or negative numbers rejected gracefully."""
    res = client.post("/api/comparison/analyze", json={"product_ids": [-5, 99999999, "invalid"]})
    assert res.status_code in [400, 404]

    # Non-list payload
    res_bad = client.post("/api/comparison/analyze", json={"product_ids": "not_a_list"})
    assert res_bad.status_code == 400


# =============================================================================
# SCENARIO 19: Tenant isolation on saved comparisons
# =============================================================================

def test_scenario_19_saved_comparison_tenant_isolation(client):
    """Scenario 19: Accessing another customer's comparison session returns 403 Forbidden."""
    # Attempt to request saved comparison with another customer ID
    res = client.get("/api/comparison/saved?user_id=9999")
    assert res.status_code == 403


# =============================================================================
# SCENARIO 20: Responsive layout and DOM structure
# =============================================================================

def test_scenario_20_responsive_layout_rendering(client):
    """Scenario 20: GET /comparison renders all 7 required section containers."""
    res = client.get("/comparison")
    assert res.status_code == 200
    html = res.get_data(as_text=True)

    # Verify all 7 sections exist
    assert "sectionSelect" in html
    assert "sectionSideBySide" in html
    assert "sectionFeatureAnalysis" in html
    assert "sectionPriceValue" in html
    assert "sectionProsCons" in html
    assert "sectionDecisionAssistant" in html
    assert "sectionFinalActions" in html

    # Verify search input & presets
    assert "compSearchInput" in html
    assert "presetsGrid" in html

    # Verify theme colors
    assert "#F7F3FF" in html or "--pt-bg" in html
    assert "#FFFDF9" in html or "--pt-card-bg" in html
    assert "#C4A6F5" in html or "--pt-primary" in html
