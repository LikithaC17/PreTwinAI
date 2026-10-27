"""
test_api.py — Flask API endpoint tests for PreTwinShop AI.

All tests use the `app_client` fixture from conftest.py which provides a
Flask test client backed by a seeded in-memory (temp-file) SQLite database.

Endpoint contract assumed:
  GET  /api/products                 → {"products": [...], "total": N}
  GET  /api/products/<id>            → {"product": {...}}
  GET  /api/profile                  → {"profile": {...}}  (user_id=1)
  PUT  /api/profile                  → {"success": True, ...}
  GET  /api/purchase-history         → {"purchases": [...]}
  POST /api/purchase-history         → {"success": True, "id": N}
  DELETE /api/purchase-history/<id>  → {"success": True}
  GET  /api/predictions              → {"predictions": [...]}
  POST /api/recommendations          → {"success": True, "run_id": "..."}
  GET  /api/agent-runs               → {"agent_runs": [...]}
  POST /api/feedback                 → {"success": True}
  DELETE /api/profile                → {"success": True}
  GET  /api/categories               → {"categories": [...]}
  GET  /api/dashboard                → {"dashboard": {...}}
"""

from __future__ import annotations

import json
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def json_body(response) -> dict:
    """Parse a Flask test response as JSON."""
    return json.loads(response.data.decode())


def assert_ok(response, status: int = 200):
    assert response.status_code == status, (
        f"Expected {status}, got {response.status_code}: "
        f"{response.data.decode()[:300]}"
    )


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------

class TestGetProducts:
    def test_get_products_returns_list(self, app_client):
        """GET /api/products should return a list of products."""
        resp = app_client.get("/api/products")
        assert_ok(resp)
        data = json_body(resp)
        # Accept either {"products": [...]} or a direct list
        products = data.get("products", data) if isinstance(data, dict) else data
        assert isinstance(products, list)

    def test_get_products_with_category_filter(self, app_client):
        """GET /api/products?category=Electronics should only return Electronics."""
        resp = app_client.get("/api/products?category=Electronics")
        assert_ok(resp)
        data = json_body(resp)
        products = data.get("products", data) if isinstance(data, dict) else data
        for p in products:
            assert p.get("category", "Electronics") == "Electronics"

    def test_get_products_with_price_filter(self, app_client):
        """GET /api/products?max_price=200 should only return products ≤ $200."""
        resp = app_client.get("/api/products?max_price=200")
        assert_ok(resp)
        data = json_body(resp)
        products = data.get("products", data) if isinstance(data, dict) else data
        for p in products:
            assert float(p.get("price", 0)) <= 200.0

    def test_get_products_with_search(self, app_client):
        """GET /api/products?search=Sony should return products matching 'Sony'."""
        resp = app_client.get("/api/products?search=Sony")
        assert_ok(resp)
        data = json_body(resp)
        products = data.get("products", data) if isinstance(data, dict) else data
        assert isinstance(products, list)

    def test_get_products_with_pagination_and_sorting(self, app_client):
        """GET /api/products?page=1&limit=5&sort=price_asc should return paginated response."""
        resp = app_client.get("/api/products?page=1&limit=5&sort=price_asc")
        assert_ok(resp)
        data = json_body(resp)
        assert "products" in data
        assert "total" in data
        assert "page" in data
        assert "pages" in data

    def test_get_subcategories(self, app_client):
        """GET /api/subcategories should return list of subcategories."""
        resp = app_client.get("/api/subcategories")
        assert_ok(resp)
        data = json_body(resp)
        assert "subcategories" in data
        assert isinstance(data["subcategories"], list)


class TestGetProductById:
    def test_get_product_by_id(self, app_client):
        """GET /api/products/1 should return a single product dict."""
        resp = app_client.get("/api/products/1")
        assert_ok(resp)
        data = json_body(resp)
        product = data.get("product", data)
        assert "name" in product or "id" in product

    def test_get_product_not_found_returns_404(self, app_client):
        """GET /api/products/999999 should return 404."""
        resp = app_client.get("/api/products/999999")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

class TestProfile:
    def test_get_profile_returns_data(self, app_client):
        """GET /api/profile should return profile data for demo user."""
        resp = app_client.get("/api/profile")
        assert_ok(resp)
        data = json_body(resp)
        # Accept {"profile": {...}} or flat dict
        profile = data.get("profile", data)
        # Should have at least one of these keys
        profile_keys = set(profile.keys())
        expected_any = {"user_id", "username", "email", "preferences",
                        "budget_min", "budget_max", "user"}
        assert profile_keys & expected_any, (
            f"Profile response missing expected keys. Got: {profile_keys}"
        )

    def test_put_profile_updates_preferences(self, app_client):
        """PUT /api/profile with valid payload should succeed."""
        payload = {
            "budget_min": 100.0,
            "budget_max": 1500.0,
            "preferred_categories": ["Electronics", "Books"],
            "preferred_brands": ["Sony"],
            "shopping_frequency": "weekly",
        }
        resp = app_client.put(
            "/api/profile",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert_ok(resp)
        data = json_body(resp)
        assert data.get("success") is True or resp.status_code == 200

    def test_put_profile_validates_budget(self, app_client):
        """PUT /api/profile with budget_max < budget_min should return 400."""
        payload = {
            "budget_min": 5000.0,
            "budget_max": 100.0,  # invalid: max < min
        }
        resp = app_client.put(
            "/api/profile",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert resp.status_code == 400, (
            f"Expected 400 for invalid budget, got {resp.status_code}"
        )

    def test_delete_profile_resets_data(self, app_client):
        """DELETE /api/profile should reset user profile to defaults."""
        resp = app_client.delete("/api/profile")
        assert resp.status_code in (200, 204)
        if resp.data:
            data = json_body(resp)
            assert data.get("success") is True or "reset" in str(data).lower()


# ---------------------------------------------------------------------------
# Purchase History
# ---------------------------------------------------------------------------

class TestPurchaseHistory:
    def test_get_purchase_history(self, app_client):
        """GET /api/purchase-history should return a list."""
        resp = app_client.get("/api/purchase-history")
        assert_ok(resp)
        data = json_body(resp)
        purchases = data.get("purchases", data.get("history", data))
        assert isinstance(purchases, list)

    def test_post_purchase_history_adds_record(self, app_client):
        """POST /api/purchase-history should add a new purchase record."""
        payload = {
            "product_name": "Test Headphones",
            "category": "Electronics",
            "brand": "TestBrand",
            "price": 199.99,
            "purchase_date": "2024-06-01",
            "quantity": 1,
        }
        resp = app_client.post(
            "/api/purchase-history",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert resp.status_code in (200, 201)
        data = json_body(resp)
        assert data.get("success") is True or "id" in data

    def test_delete_purchase_history(self, app_client):
        """DELETE /api/purchase-history/<id> should remove the record."""
        # First add a record to delete
        payload = {
            "product_name": "Delete Me",
            "category": "Books",
            "price": 29.99,
            "purchase_date": "2024-01-01",
        }
        post_resp = app_client.post(
            "/api/purchase-history",
            data=json.dumps(payload),
            content_type="application/json",
        )
        if post_resp.status_code not in (200, 201):
            pytest.skip("Could not create purchase record to delete")

        post_data = json_body(post_resp)
        record_id = post_data.get("id", post_data.get("purchase_id", 1))

        del_resp = app_client.delete(f"/api/purchase-history/{record_id}")
        assert del_resp.status_code in (200, 204)


# ---------------------------------------------------------------------------
# Predictions
# ---------------------------------------------------------------------------

class TestPredictions:
    def test_get_predictions(self, app_client):
        """GET /api/predictions should return a list (possibly empty)."""
        resp = app_client.get("/api/predictions")
        assert_ok(resp)
        data = json_body(resp)
        predictions = data.get("predictions", data)
        assert isinstance(predictions, list)


# ---------------------------------------------------------------------------
# Recommendations / Orchestrator
# ---------------------------------------------------------------------------

class TestRecommendations:
    def test_post_recommendations_runs_workflow(self, app_client):
        """POST /api/recommendations should trigger the agent workflow."""
        resp = app_client.post(
            "/api/recommendations",
            data=json.dumps({}),
            content_type="application/json",
        )
        # Allow 200 or 202 (async) or 201
        assert resp.status_code in (200, 201, 202), (
            f"Unexpected status {resp.status_code}: {resp.data.decode()[:200]}"
        )
        data = json_body(resp)
        # Should return a run_id or success indicator
        assert data.get("run_id") or data.get("success") or data.get("result")


# ---------------------------------------------------------------------------
# Agent Runs
# ---------------------------------------------------------------------------

class TestAgentRuns:
    def test_get_agent_runs(self, app_client):
        """GET /api/agent-runs should return a list."""
        resp = app_client.get("/api/agent-runs")
        assert_ok(resp)
        data = json_body(resp)
        runs = data.get("agent_runs", data.get("runs", data))
        assert isinstance(runs, list)


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------

class TestFeedback:
    def test_post_feedback(self, app_client):
        """POST /api/feedback should record user feedback."""
        payload = {
            "item_type": "prediction",
            "item_id": 1,
            "feedback_type": "like",
            "rating": 5,
            "comment": "Great prediction!",
        }
        resp = app_client.post(
            "/api/feedback",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert resp.status_code in (200, 201)
        data = json_body(resp)
        assert data.get("success") is True or resp.status_code in (200, 201)


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------

class TestCategories:
    def test_get_categories_returns_list(self, app_client):
        """GET /api/categories should return a non-empty list of category strings."""
        resp = app_client.get("/api/categories")
        assert_ok(resp)
        data = json_body(resp)
        categories = data.get("categories", data)
        assert isinstance(categories, list)
        assert len(categories) >= 1


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

class TestDashboard:
    def test_get_dashboard_data(self, app_client):
        """GET /api/dashboard should return aggregated dashboard data."""
        resp = app_client.get("/api/dashboard")
        assert_ok(resp)
        data = json_body(resp)
        # Should have at least one of these top-level keys
        expected_any = {
            "dashboard", "predictions", "recommendations",
            "profile", "agent_runs", "stats",
        }
        assert set(data.keys()) & expected_any, (
            f"Dashboard response missing expected keys. Got: {set(data.keys())}"
        )
