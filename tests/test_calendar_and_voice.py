import pytest
import json
from datetime import datetime, timedelta, timezone
from agents.chat_assistant import PreTwinChatAssistant
import app


def test_startup_intro_elements_rendered(app_client):
    """Test that startup intro overlay, flying-wing emblem, and skip button are rendered."""
    res = app_client.get("/")
    assert res.status_code == 200
    html = res.data.decode("utf-8")
    assert "pretwinStartupIntro" in html
    assert "pretwin-skip-intro-btn" in html
    assert "pretwin-intro-sky" in html
    assert "Your Future. Your Style. Your Twin." in html


def test_auth_pages_render_with_google_signin(app_client):
    """Test login and register pages render with PreTwin welcome and Continue with Google button."""
    # Login page
    login_res = app_client.get("/login")
    assert login_res.status_code == 200
    login_html = login_res.data.decode("utf-8")
    assert "Welcome to PreTwin" in login_html
    assert "Your personalized shopping experience begins here." in login_html
    assert "Continue with Google" in login_html
    assert "googleConfigModal" in login_html

    # Register page
    reg_res = app_client.get("/register")
    assert reg_res.status_code == 200
    reg_html = reg_res.data.decode("utf-8")
    assert "Welcome to PreTwin" in reg_html
    assert "Continue with Google" in reg_html


def test_google_auth_api_validation(app_client, monkeypatch):
    """Test Google Auth API endpoint validates input, configuration status, and tokens."""
    # Config endpoint
    cfg_res = app_client.get("/api/auth/config")
    assert cfg_res.status_code == 200
    cfg = cfg_res.get_json()
    assert "google_client_id" in cfg
    assert "google_enabled" in cfg

    # Missing credential payload
    bad_res = app_client.post("/api/auth/google", json={})
    assert bad_res.status_code == 400
    assert "credential token is required" in bad_res.get_json()["error"]

    # When client ID is not configured
    monkeypatch.setattr(app.Config, "GOOGLE_CLIENT_ID", "")
    unconfigured_res = app_client.post("/api/auth/google", json={"credential": "sample.token"})
    assert unconfigured_res.status_code == 400
    assert "not configured" in unconfigured_res.get_json()["error"]

    # When client ID is configured, invalid token fails verification with 401
    monkeypatch.setattr(app.Config, "GOOGLE_CLIENT_ID", "mock-client-id.apps.googleusercontent.com")
    invalid_res = app_client.post("/api/auth/google", json={"credential": "invalid.jwt.token"})
    assert invalid_res.status_code == 401
    assert "verification failed" in invalid_res.get_json()["error"].lower()


def test_calendar_page_and_events_api(app_client):
    """Test Future Predictive Calendar page renders and CRUD operations work correctly."""
    # 1. Page render
    cal_res = app_client.get("/calendar")
    assert cal_res.status_code == 200
    html = cal_res.data.decode("utf-8")
    assert "Future Predictive Calendar" in html
    assert "calendarGrid" in html
    assert "calendarModal" in html

    # 2. GET events
    events_res = app_client.get("/api/calendar/events")
    assert events_res.status_code == 200
    ev_data = events_res.get_json()
    assert "events" in ev_data
    assert len(ev_data["events"]) >= 3

    # Check suggested products attached
    first_ev = ev_data["events"][0]
    assert "suggested_products" in first_ev
    assert "category" in first_ev

    # 3. POST create event
    future_date = (datetime.now(timezone.utc) + timedelta(days=20)).strftime("%Y-%m-%d")
    create_res = app_client.post("/api/calendar/events", json={
        "title": "Quarterly Marathon & Running Prep",
        "event_date": future_date,
        "category": "Sports & Fitness",
        "notes": "Need high-performance running shoes and hydration pack",
        "budget": 3500
    })
    assert create_res.status_code == 201
    created_id = create_res.get_json()["id"]
    assert created_id > 0

    # 4. PUT update event
    update_res = app_client.put(f"/api/calendar/events/{created_id}", json={
        "title": "Quarterly Marathon 2026",
        "event_date": future_date,
        "budget": 4500
    })
    assert update_res.status_code == 200
    assert update_res.get_json()["success"] is True

    # 5. POST feedback on event
    fb_res = app_client.post(f"/api/calendar/events/{created_id}/feedback", json={
        "action": "useful"
    })
    assert fb_res.status_code == 200
    assert fb_res.get_json()["success"] is True

    # 6. DELETE event
    del_res = app_client.delete(f"/api/calendar/events/{created_id}")
    assert del_res.status_code == 200
    assert del_res.get_json()["success"] is True


def test_voice_shopping_assistant_queries():
    """Test voice query intent classification and rich responses from PreTwinChatAssistant."""
    assistant = PreTwinChatAssistant()

    # Query 1: College shoes under 1500
    resp1 = assistant.handle_message("Find college shoes under 1500", user_id=1)
    assert resp1["intent"] == "product_search"
    assert len(resp1["products"]) > 0

    # Query 2: Phones under 20000
    resp2 = assistant.handle_message("Show me 5g phones under 20000", user_id=1)
    assert resp2["intent"] == "product_search"
    assert len(resp2["products"]) > 0

    # Query 3: Calendar inquiry
    resp3 = assistant.handle_message("What are my upcoming calendar events?", user_id=1)
    assert resp3["intent"] in ["calendar_inquiry", "calendar_event_prep"]
    assert "milestone" in resp3["reply"].lower() or "calendar" in resp3["reply"].lower()

    # Query 4: Wishlist inquiry
    resp4 = assistant.handle_message("Show me my saved wishlist", user_id=1)
    assert resp4["intent"] in ["wishlist_inquiry", "wishlist_items", "wishlist_empty"]

    # Query 5: Cheaper alternatives
    resp5 = assistant.handle_message("Are there cheaper alternatives for my cart?", user_id=1)
    assert resp5["intent"] == "cheaper_alternatives"

    # Query 6: Budget bundle
    resp6 = assistant.handle_message("Create a budget bundle for me", user_id=1)
    assert resp6["intent"] in ["budget_bundle", "budget_shopping_list"]


def test_navbar_feature_order_and_link(app_client):
    """Verify exact 8 feature categories and Future Predictive Calendar at position 6."""
    res = app_client.get("/")
    assert res.status_code == 200
    html = res.data.decode("utf-8")

    features = [
        ("Personalization and Digital Twin", "/twin"),
        ("Predictive Shopping Intelligence", "/predictions"),
        ("Smart Product Discovery", "/discovery"),
        ("Budget and Price Intelligence", "/budget"),
        ("Product Comparison and Decision Support", "/comparison"),
        ("Future Predictive Calendar", "/calendar"),
        ("Smart Shopping Card", "/smart-cart"),
        ("Advanced Features for Future Development", "/advanced-ai"),
    ]

    last_pos = -1
    for title, link in features:
        pos = html.find(title)
        assert pos != -1, f"Missing navbar feature: {title}"
        assert pos > last_pos, f"Navbar feature out of order: {title}"
        last_pos = pos
        assert link in html, f"Missing navbar link: {link}"
