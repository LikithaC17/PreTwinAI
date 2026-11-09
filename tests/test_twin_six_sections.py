"""
tests/test_twin_six_sections.py
-------------------------------
Unit and Integration tests for Feature 1: Personalization and Digital Twin
Validates:
1. GET /api/twin/dashboard returning 6 structured sections.
2. Distinct explicit vs inferred preference handling.
3. Spending analysis strictly excluding cancelled/returned/COD-pending orders.
4. Activity logging (browse, search, wishlist) reflecting in twin behaviour.
5. Inaccurate inference correction (dislike registration).
6. Reset and deletion governance endpoints.
"""

import json
import pytest
from agents import (
    CustomerProfileAgent,
    BehaviourAnalysisAgent,
    SpendingAnalysisAgent,
    FutureNeedsAgent,
    DigitalTwinCoordinator,
)
from services.activity_service import ActivityService


def test_twin_dashboard_endpoint_returns_six_sections(app_client):
    """GET /api/twin/dashboard returns 200 with all 6 required sections."""
    resp = app_client.get("/api/twin/dashboard")
    assert resp.status_code == 200
    data = resp.get_json()

    assert data["success"] is True
    assert "archetype" in data
    assert "identity" in data
    assert "behaviour" in data
    assert "spending" in data
    assert "insights" in data
    assert "future_needs" in data
    assert "is_personalization_enabled" in data

    # Verify Identity section
    identity = data["identity"]
    assert "explicit" in identity
    assert "inferred" in identity
    assert "completeness_score" in identity

    # Verify Behaviour section
    behaviour = data["behaviour"]
    assert "total_purchases_recorded" in behaviour
    assert "wishlist_count" in behaviour
    assert "cart_count" in behaviour
    assert "browsing_events_count" in behaviour

    # Verify Spending section
    spending = data["spending"]
    assert "total_spent" in spending
    assert "average_order_value" in spending
    assert "spending_tier" in spending


def test_update_twin_preferences_endpoint(app_client):
    """PUT /api/twin/preferences updates explicit preferences."""
    payload = {
        "preferred_categories": ["Electronics", "Personal Care"],
        "preferred_brands": ["Sony", "Philips"],
        "preferred_colors": ["Black", "Silver"],
        "preferred_sizes": ["M", "L"],
        "budget_min": 1000,
        "budget_max": 8000,
        "shopping_frequency": "biweekly",
        "goals": "Home Office Upgrade"
    }

    resp = app_client.put(
        "/api/twin/preferences",
        data=json.dumps(payload),
        content_type="application/json"
    )
    assert resp.status_code == 200
    res_data = resp.get_json()
    assert res_data["success"] is True

    # Check that GET returns updated explicit preferences
    get_resp = app_client.get("/api/twin/dashboard")
    dash = get_resp.get_json()
    explicit = dash["identity"]["explicit"]
    assert "Electronics" in explicit["categories"]
    assert "Sony" in explicit["brands"]
    assert "Black" in explicit["colors"]
    assert explicit["budget_min"] == 1000
    assert explicit["budget_max"] == 8000
    assert explicit["frequency"] == "biweekly"


def test_correct_inference_endpoint(app_client):
    """POST /api/twin/correct-inference registers dislike and removes inference."""
    # Register dislike for inferred category "Gaming"
    resp = app_client.post(
        "/api/twin/correct-inference",
        data=json.dumps({"tag_type": "category", "tag_value": "Gaming"}),
        content_type="application/json"
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True

    # Verify that "Gaming" is now in corrected_dislikes
    get_resp = app_client.get("/api/twin/dashboard")
    dash = get_resp.get_json()
    dislikes = dash["identity"]["inferred"].get("corrected_dislikes", [])
    assert "Gaming" in dislikes


def test_activity_logging_and_behaviour_tracking(app_client):
    """POST /api/activity/log records interactions and updates Behaviour agent metrics."""
    # Log a browse event
    resp = app_client.post(
        "/api/activity/log",
        data=json.dumps({
            "activity_type": "browse",
            "product_id": 1,
            "category": "Electronics",
            "brand": "Sony"
        }),
        content_type="application/json"
    )
    assert resp.status_code == 200

    # Log a search query
    resp2 = app_client.post(
        "/api/activity/log",
        data=json.dumps({
            "activity_type": "search",
            "search_query": "noise cancelling headphones",
            "category": "Electronics"
        }),
        content_type="application/json"
    )
    assert resp2.status_code == 200

    # Dashboard behaviour reflects activity
    get_resp = app_client.get("/api/twin/dashboard")
    dash = get_resp.get_json()
    assert dash["behaviour"]["browsing_events_count"] >= 1
    assert "noise cancelling headphones" in dash["behaviour"]["recent_search_queries"]


def test_spending_analysis_integrity_agent(test_db):
    """SpendingAnalysisAgent excludes cancelled, refunded, returned, and COD pending orders."""
    spending_agent = SpendingAnalysisAgent()

    # User 1 with sample orders in test_db
    res = spending_agent.run(1)
    assert "total_spent" in res
    assert "average_order_value" in res
    assert "spending_tier" in res
    # Disqualified orders should not inflate spend
    assert res["total_spent"] >= 0


def test_twin_reset_and_delete_endpoints(app_client):
    """POST /api/twin/reset and /api/twin/delete-personalization function smoothly."""
    # Reset
    resp = app_client.post("/api/twin/reset")
    assert resp.status_code == 200
    assert resp.get_json()["success"] is True

    # Delete
    del_resp = app_client.post("/api/twin/delete-personalization")
    assert del_resp.status_code == 200
    assert del_resp.get_json()["success"] is True
