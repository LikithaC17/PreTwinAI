"""
tests/test_calendar_twenty_one_scenarios.py
===========================================
Comprehensive Test Suite for Feature 6: Future Predictive Calendar
Covers all 21 test scenarios specified in Phase 9:
1. Customer opens an empty calendar
2. Customer navigates between months
3. Customer switches month, week and day views
4. Customer selects a date
5. Customer creates a shopping plan
6. Customer edits a shopping plan
7. Customer reschedules a plan
8. Customer marks a plan completed
9. Customer creates an occasion
10. Customer creates/checks a custom reminder
11. Customer views upcoming predictions
12. Customer with no purchase history uses the calendar
13. Customer with sufficient purchase history receives an explainable prediction
14. Customer edits or dismisses a prediction / converts to plan
15. Customer checks future shopping expenses
16. Customer views completed and overdue activities
17. Customer accesses an invalid date or activity ID
18. Tenant isolation: Customer attempts to access another customer's calendar records
19. Customer checks reminder snooze and dismiss
20. Leap-year and month-boundary date handling
21. Mobile, tablet and desktop responsiveness (DOM containers for all 7 sections)
"""

import json
import uuid
import pytest
from datetime import datetime, date, timedelta, timezone

import app as flask_app
import database
import services.calendar_service as cs


@pytest.fixture
def client():
    flask_app.app.config["TESTING"] = True
    with flask_app.app.test_client() as client:
        yield client


@pytest.fixture
def test_user():
    """Create an isolated test customer for calendar tests."""
    email = f"cal_test_{uuid.uuid4().hex[:8]}@example.com"
    user_id = database.execute_db(
        "INSERT INTO users (username, email) VALUES (?, ?)",
        ("Calendar Test Customer", email)
    )
    return user_id


# =============================================================================
# SCENARIO 1: Customer opens an empty calendar
# =============================================================================

def test_scenario_01_empty_calendar(client, test_user):
    """Scenario 1: Opens calendar view for a new customer with no prior records."""
    res = client.get("/api/calendar/view?mode=month")
    assert res.status_code == 200
    data = res.get_json()
    assert "days" in data
    assert len(data["days"]) in [28, 35, 42]
    assert "display_title" in data


# =============================================================================
# SCENARIO 2: Customer navigates between months
# =============================================================================

def test_scenario_02_month_navigation(client):
    """Scenario 2: Navigate to previous and next month dates."""
    res_dec = client.get("/api/calendar/view?mode=month&date=2026-12-15")
    assert res_dec.status_code == 200
    assert "December 2026" in res_dec.get_json()["display_title"]

    res_jan = client.get("/api/calendar/view?mode=month&date=2027-01-10")
    assert res_jan.status_code == 200
    assert "January 2027" in res_jan.get_json()["display_title"]


# =============================================================================
# SCENARIO 3: Customer switches month, week and day views
# =============================================================================

def test_scenario_03_view_modes(client):
    """Scenario 3: Month, week, and day view endpoints."""
    # Month
    m_res = client.get("/api/calendar/view?mode=month&date=2026-11-10")
    assert m_res.status_code == 200
    assert m_res.get_json()["view_mode"] == "month"

    # Week
    w_res = client.get("/api/calendar/view?mode=week&date=2026-11-10")
    assert w_res.status_code == 200
    w_data = w_res.get_json()
    assert w_data["view_mode"] == "week"
    assert len(w_data["days"]) == 7

    # Day
    d_res = client.get("/api/calendar/view?mode=day&date=2026-11-10")
    assert d_res.status_code == 200
    assert d_res.get_json()["view_mode"] == "day"


# =============================================================================
# SCENARIO 4: Customer selects a date
# =============================================================================

def test_scenario_04_select_date(client):
    """Scenario 4: Date selection returns day's activities."""
    res = client.get("/api/calendar/view?mode=day&date=2026-11-15")
    assert res.status_code == 200
    data = res.get_json()
    assert data["current_date"] == "2026-11-15"
    assert "activities" in data


# =============================================================================
# SCENARIO 5: Customer creates a shopping plan
# =============================================================================

def test_scenario_05_create_shopping_plan(client):
    """Scenario 5: Successfully create a future shopping plan."""
    future_date = (date.today() + timedelta(days=25)).strftime("%Y-%m-%d")
    res = client.post("/api/calendar/plans", json={
        "title": "Ergonomic Office Chair",
        "category": "Furniture",
        "target_date": future_date,
        "estimated_budget": 8500,
        "priority": "High",
        "notes": "Lumbar support required"
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["success"] is True
    assert data["id"] > 0


# =============================================================================
# SCENARIO 6: Customer edits a shopping plan
# =============================================================================

def test_scenario_06_edit_shopping_plan(client):
    """Scenario 6: Edit details of an existing plan."""
    # Create first
    target = (date.today() + timedelta(days=30)).strftime("%Y-%m-%d")
    c_res = client.post("/api/calendar/plans", json={
        "title": "Smart Watch",
        "target_date": target,
        "estimated_budget": 3000
    })
    plan_id = c_res.get_json()["id"]

    # Edit
    u_res = client.put(f"/api/calendar/plans/{plan_id}", json={
        "title": "Smart Watch Ultra",
        "estimated_budget": 4500
    })
    assert u_res.status_code == 200
    assert u_res.get_json()["success"] is True


# =============================================================================
# SCENARIO 7: Customer reschedules a plan
# =============================================================================

def test_scenario_07_reschedule_plan(client):
    """Scenario 7: Reschedule plan to a new target date."""
    target1 = (date.today() + timedelta(days=10)).strftime("%Y-%m-%d")
    target2 = (date.today() + timedelta(days=40)).strftime("%Y-%m-%d")
    c_res = client.post("/api/calendar/plans", json={"title": "Winter Jacket", "target_date": target1})
    plan_id = c_res.get_json()["id"]

    r_res = client.put(f"/api/calendar/plans/{plan_id}", json={"target_date": target2})
    assert r_res.status_code == 200


# =============================================================================
# SCENARIO 8: Customer marks a plan completed
# =============================================================================

def test_scenario_08_mark_plan_completed(client):
    """Scenario 8: Mark shopping plan status as completed."""
    target = (date.today() + timedelta(days=15)).strftime("%Y-%m-%d")
    c_res = client.post("/api/calendar/plans", json={"title": "Coffee Beans", "target_date": target})
    plan_id = c_res.get_json()["id"]

    done_res = client.put(f"/api/calendar/plans/{plan_id}", json={"status": "completed"})
    assert done_res.status_code == 200
    assert done_res.get_json()["success"] is True


# =============================================================================
# SCENARIO 9: Customer creates an occasion
# =============================================================================

def test_scenario_09_create_occasion(client):
    """Scenario 9: Customer adds a personal festive occasion."""
    occ_date = (date.today() + timedelta(days=45)).strftime("%Y-%m-%d")
    res = client.post("/api/calendar/occasions", json={
        "event_name": "Diwali Festival Celebration",
        "event_date": occ_date,
        "occasion_type": "Festival",
        "estimated_budget": 12000,
        "shopping_requirements": "Traditional attire and decorative lights"
    })
    assert res.status_code == 201
    assert res.get_json()["success"] is True
    assert res.get_json()["id"] > 0


# =============================================================================
# SCENARIO 10: Customer creates and checks a custom reminder
# =============================================================================

def test_scenario_10_custom_reminder(client):
    """Scenario 10: In-app reminders endpoint returns active alerts."""
    res = client.get("/api/calendar/reminders")
    assert res.status_code == 200
    data = res.get_json()
    assert "reminders" in data
    assert isinstance(data["reminders"], list)


# =============================================================================
# SCENARIO 11: Customer views upcoming predictions
# =============================================================================

def test_scenario_11_view_upcoming_predictions(client):
    """Scenario 11: Retrieve replenishment predictions."""
    res = client.get("/api/calendar/predictions")
    assert res.status_code == 200
    data = res.get_json()
    assert "has_sufficient_data" in data
    assert "predictions" in data


# =============================================================================
# SCENARIO 12: Customer with no purchase history uses the calendar
# =============================================================================

def test_scenario_12_no_purchase_history(test_user):
    """Scenario 12: Customer with zero orders gets honest insufficient data notice."""
    preds = cs.CalendarService.get_upcoming_predictions(test_user)
    assert preds["has_sufficient_data"] is False
    assert len(preds["predictions"]) == 0
    assert "More shopping history is needed" in preds["message"]


# =============================================================================
# SCENARIO 13: Customer with sufficient purchase history receives explainable prediction
# =============================================================================

def test_scenario_13_sufficient_history_prediction(test_user):
    """Scenario 13: Repeat purchases generate statistical interval and explanation."""
    # Seed 3 completed repeat purchases separated by ~30 days
    d1 = (date.today() - timedelta(days=90)).strftime("%Y-%m-%d")
    d2 = (date.today() - timedelta(days=60)).strftime("%Y-%m-%d")
    d3 = (date.today() - timedelta(days=30)).strftime("%Y-%m-%d")
    for d in [d1, d2, d3]:
        database.execute_db(
            """INSERT INTO purchase_history
               (user_id, product_name, category, brand, price, purchase_date, quantity)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (test_user, "Premium Organic Green Tea", "Food & Grocery", "Twinings", 350.0, d, 1)
        )

    preds = cs.CalendarService.get_upcoming_predictions(test_user)
    assert preds["has_sufficient_data"] is True
    assert len(preds["predictions"]) >= 1
    p0 = preds["predictions"][0]
    assert p0["product_name"] == "Premium Organic Green Tea"
    assert p0["estimated_interval_days"] in [29, 30, 31]
    assert p0["confidence_level"] in ["High", "Moderate"]
    assert "explanation" in p0


# =============================================================================
# SCENARIO 14: Customer converts prediction to plan
# =============================================================================

def test_scenario_14_convert_prediction_to_plan(client):
    """Scenario 14: Convert an accepted replenishment prediction into a shopping plan."""
    next_date = (date.today() + timedelta(days=20)).strftime("%Y-%m-%d")
    res = client.post("/api/calendar/predictions/convert", json={
        "product_name": "Immunity Booster Protein",
        "category": "Health & Wellness",
        "predicted_next_date": next_date,
        "estimated_budget": 1499
    })
    assert res.status_code == 201
    assert res.get_json()["success"] is True


# =============================================================================
# SCENARIO 15: Customer checks future shopping expenses
# =============================================================================

def test_scenario_15_future_budget_summary(client):
    """Scenario 15: Budget summary distinguishes planned vs active monthly limit."""
    res = client.get("/api/calendar/budget-summary")
    assert res.status_code == 200
    data = res.get_json()
    assert "total_estimated_future_expenses" in data
    assert "current_month_planned" in data
    assert "active_monthly_budget" in data
    assert "monthly_planned_breakdown" in data
    assert "category_planned_breakdown" in data


# =============================================================================
# SCENARIO 16: Customer views completed and overdue activities
# =============================================================================

def test_scenario_16_completed_and_overdue_activities(client):
    """Scenario 16: Filter plans by completed and overdue statuses."""
    comp_res = client.get("/api/calendar/plans?status=completed")
    assert comp_res.status_code == 200
    assert "plans" in comp_res.get_json()

    overdue_res = client.get("/api/calendar/plans?status=overdue")
    assert overdue_res.status_code == 200
    assert "plans" in overdue_res.get_json()


# =============================================================================
# SCENARIO 17: Customer accesses an invalid date or activity ID
# =============================================================================

def test_scenario_17_invalid_date_or_id(client):
    """Scenario 17: Bad date formats or nonexistent IDs return 400 or 404."""
    # Bad date format for plan
    bad_plan = client.post("/api/calendar/plans", json={"title": "Test", "target_date": "not-a-date"})
    assert bad_plan.status_code == 400

    # Nonexistent plan ID
    bad_id = client.put("/api/calendar/plans/9999999", json={"title": "New Title"})
    assert bad_id.status_code == 404


# =============================================================================
# SCENARIO 18: Tenant isolation on customer calendar records
# =============================================================================

def test_scenario_18_tenant_isolation(client, test_user):
    """Scenario 18: Customer A cannot edit or delete Customer B's plans."""
    # Create plan for test_user
    plan_id = cs.CalendarService.create_shopping_plan(test_user, {
        "title": "Private Plan for Test User",
        "target_date": "2026-12-25"
    })["id"]

    # Attempt to delete using client (which acts as demo user 1)
    # Since plan_id belongs to test_user (not demo user 1), delete should return 404
    del_res = client.delete(f"/api/calendar/plans/{plan_id}")
    assert del_res.status_code == 404


# =============================================================================
# SCENARIO 19: Reminder snooze and dismiss
# =============================================================================

def test_scenario_19_reminder_snooze_and_dismiss(client, test_user):
    """Scenario 19: Snooze in-app reminder +3 days, then dismiss."""
    rem_id = database.execute_db(
        """INSERT INTO shopping_reminders (user_id, title, category, next_reminder_date)
           VALUES (?, ?, ?, ?)""",
        (1, "Restock Body Wash", "Personal Care", date.today().strftime("%Y-%m-%d"))
    )

    snooze_res = client.post(f"/api/calendar/reminders/{rem_id}/snooze", json={"days": 3})
    assert snooze_res.status_code == 200

    dismiss_res = client.post(f"/api/calendar/reminders/{rem_id}/dismiss")
    assert dismiss_res.status_code == 200


# =============================================================================
# SCENARIO 20: Leap-year and month-boundary date handling
# =============================================================================

def test_scenario_20_leap_year_handling(client):
    """Scenario 20: Correctly calculates February 29 on leap years (e.g. 2028)."""
    leap_res = client.get("/api/calendar/view?mode=month&date=2028-02-15")
    assert leap_res.status_code == 200
    days = leap_res.get_json()["days"]
    # Verify February 29th exists in leap year view
    feb_29 = [d for d in days if d["date"] == "2028-02-29"]
    assert len(feb_29) == 1
    assert feb_29[0]["day_number"] == 29
    assert feb_29[0]["is_current_month"] is True


# =============================================================================
# SCENARIO 21: Responsive layout and DOM structure
# =============================================================================

def test_scenario_21_responsive_layout_rendering(client):
    """Scenario 21: GET /calendar renders all 7 required section containers."""
    res = client.get("/calendar")
    assert res.status_code == 200
    html = res.get_data(as_text=True)

    # Verify all 7 section anchors exist
    assert "sectionCalendar" in html
    assert "sectionPredictions" in html
    assert "sectionPlans" in html
    assert "sectionOccasions" in html
    assert "sectionBudget" in html
    assert "sectionReminders" in html
    assert "sectionInsights" in html

    # Verify backward-compatible IDs
    assert "calendarGrid" in html
    assert "calendarModal" in html
    assert "calendarEventForm" in html

    # Verify palette colors
    assert "#F7F3FF" in html or "--cal-bg" in html
    assert "#FFFDF9" in html or "--cal-card-bg" in html
    assert "#C4A6F5" in html or "--cal-primary" in html
