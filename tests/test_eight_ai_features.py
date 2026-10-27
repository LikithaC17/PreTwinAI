"""
test_eight_ai_features.py
=========================
Comprehensive automated tests for PreTwin's 8 Intelligent Shopping Features:
1. Personalization and Digital Twin (/twin & /api/profiles/household)
2. Predictive Shopping Intelligence (/predictions & /api/predictions/reminders)
3. Smart Product Discovery (/discovery & /api/discovery/nl-search, visual-search)
4. Budget and Price Intelligence (/budget & /api/budget/*, price-history)
5. Product Comparison and Decision Support (/comparison & /api/comparison/weighted)
6. Agentic AI Shopping Workflow (/agents & /api/agents/plan-task, approve-task)
7. Smart Cart and Shopping Automation (/smart-cart & /api/smart-cart/analyze)
8. Advanced Features for Future Development (/advanced-ai & /api/advanced/*)
"""

import json
import pytest
from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_eight_feature_pages_render_successfully(client):
    """Verify that all 8 intelligent shopping feature pages return 200 OK."""
    pages = [
        "/twin",
        "/predictions",
        "/discovery",
        "/budget",
        "/comparison",
        "/agents",
        "/smart-cart",
        "/advanced-ai",
    ]
    for url in pages:
        response = client.get(url)
        assert response.status_code == 200, f"Page {url} failed with status {response.status_code}"
        assert b"PreTwin" in response.data or b"Shopping" in response.data


def test_household_profiles_api(client):
    """Feature 1: Multi-Profile Twin management and switching."""
    # 1. Fetch household profiles
    res = client.get("/api/profiles/household")
    assert res.status_code == 200
    data = res.get_json()
    assert "profiles" in data
    assert len(data["profiles"]) >= 1

    # 2. Create new profile
    new_prof = {
        "profile_name": "Test Teen Twin",
        "relationship": "Child",
        "lifestyle_type": "Student",
        "shopping_personality": "Tech Trendsetter",
        "preferred_categories": ["Electronics", "Fashion"],
        "budget_max": 5000.0,
        "notes": "Testing household twin."
    }
    create_res = client.post("/api/profiles/household", json=new_prof)
    assert create_res.status_code == 201
    created_data = create_res.get_json()
    new_id = created_data["profile_id"]

    # 3. Switch active profile
    switch_res = client.post(f"/api/profiles/household/{new_id}/switch")
    assert switch_res.status_code == 200
    switch_data = switch_res.get_json()
    assert switch_data["success"] is True
    assert switch_data["active_profile"]["profile_name"] == "Test Teen Twin"


def test_predictive_reminders_and_feedback(client):
    """Feature 2: Replenishment reminders and prediction feedback loop."""
    # 1. Get reminders
    res = client.get("/api/predictions/reminders")
    assert res.status_code == 200
    data = res.get_json()
    assert "reminders" in data

    # 2. Add reminder
    rem_payload = {
        "title": "Protein Shake Powder",
        "category": "Sports & Fitness",
        "estimated_cycle_days": 20
    }
    add_res = client.post("/api/predictions/reminders", json=rem_payload)
    assert add_res.status_code == 201

    # 3. Submit prediction feedback
    fb_res = client.post("/api/predictions/1/feedback", json={"action": "confirm", "reason": "Accurate cycle"})
    assert fb_res.status_code == 200
    assert fb_res.get_json()["success"] is True


def test_smart_discovery_nlp_and_visual(client):
    """Feature 3: Natural language product search and visual similarity."""
    # 1. NL Search with price ceiling and keyword
    nl_res = client.post("/api/discovery/nl-search", json={"query": "shoes under 3000 for running"})
    assert nl_res.status_code == 200
    nl_data = nl_res.get_json()
    assert "products" in nl_data
    assert nl_data["parsed_intent"]["max_price"] == 3000.0
    assert nl_data["parsed_intent"]["category"] == "Fashion"

    # 2. Visual Search
    vis_res = client.post("/api/discovery/visual-search", json={"category_hint": "Footwear"})
    assert vis_res.status_code == 200
    vis_data = vis_res.get_json()
    assert "products" in vis_data
    assert vis_data["success"] is True


def test_budget_and_price_history(client):
    """Feature 4: Budget overview, price drop tracking, and 60-day price history."""
    prods = client.get("/api/products").get_json().get("products", [])
    prod_id = prods[0]["id"] if prods else 1

    # 1. Budget overview
    b_res = client.get("/api/budget/overview")
    assert b_res.status_code == 200
    b_data = b_res.get_json()
    assert "budget_max" in b_data
    assert "monthly_spent" in b_data

    # 2. Track product price
    t_res = client.post("/api/budget/track", json={"product_id": prod_id, "target_price": 2800})
    assert t_res.status_code == 200
    assert t_res.get_json()["success"] is True

    # 3. 60-Day price history
    h_res = client.get(f"/api/products/{prod_id}/price-history")
    assert h_res.status_code == 200
    h_data = h_res.get_json()
    assert "history" in h_data
    assert len(h_data["history"]) >= 5
    assert h_data["decision"] in ["BUY NOW", "FAIR DEAL", "WAIT FOR DROP"]


def test_weighted_product_comparison(client):
    """Feature 5: Multi-attribute comparison with custom weight sliders."""
    prods = client.get("/api/products").get_json().get("products", [])
    ids = [p["id"] for p in prods[:2]] if len(prods) >= 2 else [1, 2]

    comp_res = client.post("/api/comparison/weighted", json={
        "product_ids": ids,
        "weights": {"price": 40, "rating": 30, "specs": 20, "brand": 10}
    })
    assert comp_res.status_code == 200
    comp_data = comp_res.get_json()
    assert "products" in comp_data
    assert "winner" in comp_data
    assert "decision_reason" in comp_data["winner"]


def test_agentic_task_planning_and_approval(client):
    """Feature 6: Goal decomposition, autonomous candidate basket, and human checkpoint."""
    # 1. Plan task
    task_res = client.post("/api/agents/plan-task", json={
        "goal": "Setup ergonomic study desk under 15000",
        "budget": 15000
    })
    assert task_res.status_code == 200
    t_data = task_res.get_json()
    task_id = t_data["task_id"]
    assert len(t_data["steps"]) >= 4
    assert t_data["steps"][-1]["status"] == "pending_approval"

    # 2. Approve task
    appr_res = client.post(f"/api/agents/approve-task/{task_id}")
    assert appr_res.status_code == 200
    assert appr_res.get_json()["success"] is True


def test_smart_cart_duplicate_and_bundle_analysis(client):
    """Feature 7: Duplicate detection, accessory companion, combo bundle discounts, budget ceilings."""
    cart_items = [
        {"id": 1, "name": "Wireless Over-Ear ANC Headphones", "price": 3499, "quantity": 1, "category": "Electronics"},
        {"id": 2, "name": "Men's Breathable Running Shoes", "price": 2199, "quantity": 1, "category": "Fashion"}
    ]
    cart_res = client.post("/api/smart-cart/analyze", json={"cart_items": cart_items})
    assert cart_res.status_code == 200
    c_data = cart_res.get_json()
    assert c_data["subtotal"] == 5698
    assert len(c_data["eligible_bundles"]) >= 1
    assert "missing_essentials" in c_data


def test_advanced_ai_features_and_simulators(client):
    """Feature 8: Strategic roadmap features, gift finder, voice, and try-on simulators."""
    # 1. Roadmap features
    feat_res = client.get("/api/advanced/features")
    assert feat_res.status_code == 200
    assert len(feat_res.get_json()["features"]) >= 6

    # 2. Gift Finder
    gift_res = client.post("/api/advanced/gift-finder", json={
        "recipient": "Father",
        "occasion": "Birthday",
        "budget": 4000
    })
    assert gift_res.status_code == 200
    assert "results" in gift_res.get_json()

    # 3. Voice Simulator
    voice_res = client.post("/api/advanced/voice-simulator", json={"transcript": "Add running shoes to cart"})
    assert voice_res.status_code == 200
    assert voice_res.get_json()["detected_action"] == "add_to_cart"

    # 4. Try-on Simulator
    try_res = client.post("/api/advanced/try-on-simulator", json={"category": "Footwear", "size": "UK 9"})
    assert try_res.status_code == 200
    assert "fit_confidence" in try_res.get_json()
