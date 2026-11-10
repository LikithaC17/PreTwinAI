"""
services/calendar_service.py
============================
PreTwin AI - Feature: Future Predictive Calendar Service
Modular architecture implementing the Seven Dedicated Sections:
1. My Shopping Calendar (Month, Week, Day views; leap years; activity status colors)
2. Upcoming Shopping Predictions (Median interval calculations, completed orders only, confidence metrics)
3. My Shopping Plans (Active, Completed, Cancelled, Overdue plans; priority; CRUD with ownership checks)
4. Occasions and Events (Customer-managed personal occasions; preparation dates; linked shopping requirements)
5. Future Shopping Budget (Planned vs Estimated vs Actual; category breakdown; Feature 4 budget integration)
6. Reminders and Notifications (In-app notifications; snooze; dismiss; completion; duplicate prevention)
7. Calendar Insights and History (Factual completion rates; on-time metrics; transparent summaries)
"""

import json
import statistics
from datetime import datetime, date, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple

import database
from config import Config


def _parse_json(val, default=None):
    if default is None:
        default = []
    if not val:
        return default
    if isinstance(val, (dict, list)):
        return val
    try:
        return json.loads(val)
    except Exception:
        return default


def _get_utc_today() -> date:
    """Returns today's date in UTC."""
    return datetime.now(timezone.utc).date()


class CalendarService:
    """Master service for PreTwin Future Predictive Calendar."""

    # Activity color palette matching PreTwin Soft Lavender + Champagne Gold design
    ACTIVITY_COLORS = {
        "predicted": {"label": "AI Predicted Need", "color": "#7C3AED", "bg": "#F5EEFF", "border": "#C4A6F5"},
        "plan": {"label": "Customer Shopping Plan", "color": "#2563EB", "bg": "#EFF6FF", "border": "#93C5FD"},
        "occasion": {"label": "Special Occasion", "color": "#D97706", "bg": "#FFFBEB", "border": "#FCD34D"},
        "milestone": {"label": "Shopping Milestone", "color": "#059669", "bg": "#ECFDF5", "border": "#6EE7B7"},
        "completed": {"label": "Completed Purchase", "color": "#475569", "bg": "#F1F5F9", "border": "#CBD5E1"},
        "cancelled": {"label": "Cancelled / Dismissed", "color": "#DC2626", "bg": "#FEF2F2", "border": "#FCA5A5"},
        "overdue": {"label": "Overdue Plan", "color": "#B91C1C", "bg": "#FEF2F2", "border": "#EF4444"}
    }

    # =========================================================================
    # 1. MY SHOPPING CALENDAR (View Generation: Month, Week, Day)
    # =========================================================================

    @classmethod
    def get_calendar_view(cls, user_id: int, mode: str = "month", target_date_str: Optional[str] = None, event_type: str = "ALL") -> Dict[str, Any]:
        """
        Generates structured calendar view data:
        - Correct day alignment
        - Month length and leap-year calculations (e.g. Feb 29)
        - Day/Week/Month slicing
        - Activities mapped to dates
        """
        today = _get_utc_today()

        if target_date_str:
            try:
                curr_date = datetime.strptime(target_date_str.split("T")[0], "%Y-%m-%d").date()
            except Exception:
                curr_date = today
        else:
            curr_date = today

        year = curr_date.year
        month = curr_date.month

        # Fetch all activities for user
        all_activities = cls.get_all_unified_activities(user_id, event_type=event_type)

        if mode == "week":
            # Start of week (Sunday)
            start_offset = curr_date.weekday() + 1
            if start_offset == 7:
                start_offset = 0
            start_date = curr_date - timedelta(days=start_offset)
            days = []
            for i in range(7):
                d = start_date + timedelta(days=i)
                d_str = d.strftime("%Y-%m-%d")
                d_acts = [a for a in all_activities if a["date"] == d_str]
                days.append({
                    "date": d_str,
                    "day_number": d.day,
                    "day_name": d.strftime("%a"),
                    "is_today": d == today,
                    "is_current_month": d.month == month,
                    "activities": d_acts
                })
            return {
                "view_mode": "week",
                "current_date": curr_date.strftime("%Y-%m-%d"),
                "display_title": f"Week of {start_date.strftime('%b %d, %Y')}",
                "days": days,
                "total_activities": sum(len(d["activities"]) for d in days),
                "colors_legend": cls.ACTIVITY_COLORS
            }

        elif mode == "day":
            d_str = curr_date.strftime("%Y-%m-%d")
            d_acts = [a for a in all_activities if a["date"] == d_str]
            return {
                "view_mode": "day",
                "current_date": d_str,
                "display_title": curr_date.strftime("%A, %B %d, %Y"),
                "is_today": curr_date == today,
                "activities": d_acts,
                "total_activities": len(d_acts),
                "colors_legend": cls.ACTIVITY_COLORS
            }

        else: # month view
            # First day of month and weekday (0=Mon .. 6=Sun)
            first_day = date(year, month, 1)
            # Python weekday(): Monday is 0, Sunday is 6. We want Sunday as 0.
            first_day_col = (first_day.weekday() + 1) % 7

            # Days in current month (handling leap years via next month minus 1 day)
            if month == 12:
                next_month_first = date(year + 1, 1, 1)
            else:
                next_month_first = date(year, month + 1, 1)
            last_day = next_month_first - timedelta(days=1)
            total_days = last_day.day

            # Days in previous month for padding
            prev_month_last = first_day - timedelta(days=1)
            prev_total_days = prev_month_last.day

            days = []
            # 1. Leading padding days
            for i in range(first_day_col - 1, -1, -1):
                p_day = prev_total_days - i
                p_date = date(prev_month_last.year, prev_month_last.month, p_day)
                p_str = p_date.strftime("%Y-%m-%d")
                days.append({
                    "date": p_str,
                    "day_number": p_day,
                    "is_today": p_date == today,
                    "is_current_month": False,
                    "activities": [a for a in all_activities if a["date"] == p_str]
                })

            # 2. Current month days
            for d in range(1, total_days + 1):
                c_date = date(year, month, d)
                c_str = c_date.strftime("%Y-%m-%d")
                c_acts = [a for a in all_activities if a["date"] == c_str]
                days.append({
                    "date": c_str,
                    "day_number": d,
                    "is_today": c_date == today,
                    "is_current_month": True,
                    "activities": c_acts
                })

            # 3. Trailing padding days to fill 35 or 42 grid cells
            rem_cells = (7 - (len(days) % 7)) % 7
            for i in range(1, rem_cells + 1):
                n_date = last_day + timedelta(days=i)
                n_str = n_date.strftime("%Y-%m-%d")
                days.append({
                    "date": n_str,
                    "day_number": i,
                    "is_today": n_date == today,
                    "is_current_month": False,
                    "activities": [a for a in all_activities if a["date"] == n_str]
                })

            month_name = first_day.strftime("%B")
            return {
                "view_mode": "month",
                "year": year,
                "month": month,
                "current_date": curr_date.strftime("%Y-%m-%d"),
                "display_title": f"{month_name} {year}",
                "days": days,
                "total_activities": len(all_activities),
                "colors_legend": cls.ACTIVITY_COLORS
            }

    @classmethod
    def get_all_unified_activities(cls, user_id: int, event_type: str = "ALL") -> List[Dict[str, Any]]:
        """
        Unifies events, plans, occasions, and replenish predictions into a single timeline.
        """
        today = _get_utc_today()
        activities = []

        # 1. Shopping Calendar Events table
        cal_rows = database.query_db(
            "SELECT * FROM shopping_calendar_events WHERE user_id = ? ORDER BY event_date ASC",
            (user_id,)
        ) or []

        for r in cal_rows:
            d = database.row_to_dict(r) if hasattr(database, "row_to_dict") else dict(r)
            ev_date_str = (d.get("event_date") or "").split("T")[0]
            if not ev_date_str:
                continue
            is_pred = bool(d.get("is_ai_predicted"))
            status = d.get("status", "upcoming")

            # Check if overdue
            try:
                ev_d = datetime.strptime(ev_date_str, "%Y-%m-%d").date()
                if ev_d < today and status == "upcoming":
                    display_status = "overdue"
                else:
                    display_status = status
            except Exception:
                display_status = status

            act_type = "predicted" if is_pred else (d.get("event_type") or "milestone").lower()
            if act_type not in cls.ACTIVITY_COLORS:
                act_type = "milestone"

            color_info = cls.ACTIVITY_COLORS.get(display_status, cls.ACTIVITY_COLORS.get(act_type, cls.ACTIVITY_COLORS["milestone"]))

            activities.append({
                "id": f"event_{d['id']}",
                "raw_id": d["id"],
                "source_type": "event",
                "title": d.get("title", "Milestone"),
                "date": ev_date_str,
                "category": d.get("category", "All"),
                "budget": float(d.get("budget") or 0.0),
                "notes": d.get("notes", ""),
                "status": display_status,
                "activity_type": act_type,
                "color_info": color_info,
                "suggested_products": _parse_json(d.get("suggested_products"), [])
            })

        # 2. Customer Shopping Plans table
        plan_rows = database.query_db(
            "SELECT * FROM customer_shopping_plans WHERE user_id = ? ORDER BY target_date ASC",
            (user_id,)
        ) or []

        for r in plan_rows:
            d = database.row_to_dict(r) if hasattr(database, "row_to_dict") else dict(r)
            t_date_str = (d.get("target_date") or "").split("T")[0]
            if not t_date_str:
                continue

            status = d.get("status", "active")
            try:
                t_d = datetime.strptime(t_date_str, "%Y-%m-%d").date()
                if t_d < today and status == "active":
                    display_status = "overdue"
                else:
                    display_status = status
            except Exception:
                display_status = status

            color_info = cls.ACTIVITY_COLORS.get(display_status, cls.ACTIVITY_COLORS["plan"])

            activities.append({
                "id": f"plan_{d['id']}",
                "raw_id": d["id"],
                "source_type": "plan",
                "title": f"📋 {d.get('title', 'Shopping Plan')}",
                "date": t_date_str,
                "category": d.get("category", "All"),
                "budget": float(d.get("estimated_budget") or 0.0),
                "priority": d.get("priority", "Medium"),
                "notes": d.get("notes", ""),
                "status": display_status,
                "activity_type": "plan",
                "color_info": color_info,
                "suggested_products": []
            })

        # 3. Customer Shopping Occasions table
        occ_rows = database.query_db(
            "SELECT * FROM customer_shopping_occasions WHERE user_id = ? ORDER BY event_date ASC",
            (user_id,)
        ) or []

        for r in occ_rows:
            d = database.row_to_dict(r) if hasattr(database, "row_to_dict") else dict(r)
            o_date_str = (d.get("event_date") or "").split("T")[0]
            if not o_date_str:
                continue

            status = d.get("status", "active")
            color_info = cls.ACTIVITY_COLORS.get(status, cls.ACTIVITY_COLORS["occasion"])

            activities.append({
                "id": f"occ_{d['id']}",
                "raw_id": d["id"],
                "source_type": "occasion",
                "title": f"🎉 {d.get('event_name', 'Occasion')}",
                "date": o_date_str,
                "category": "All",
                "budget": float(d.get("estimated_budget") or 0.0),
                "notes": d.get("notes", ""),
                "status": status,
                "activity_type": "occasion",
                "color_info": color_info,
                "suggested_products": []
            })

        # Filter if requested
        if event_type and event_type != "ALL":
            activities = [a for a in activities if a["activity_type"].lower() == event_type.lower() or a["category"].lower() == event_type.lower()]

        # Sort chronologically
        activities.sort(key=lambda x: x["date"])
        return activities

    # =========================================================================
    # 2. UPCOMING SHOPPING PREDICTIONS (Factual Replenishment Calculations)
    # =========================================================================

    @classmethod
    def get_upcoming_predictions(cls, user_id: int) -> Dict[str, Any]:
        """
        Calculates recurring purchase estimates:
        - Only uses eligible completed / delivered purchases (never cancelled/failed/returned)
        - Computes median purchase intervals to reduce outlier impact
        - Assigns explainable confidence score
        - Handles insufficient data honestly
        """
        today = _get_utc_today()

        # Fetch eligible purchases for user
        purchases = database.query_db(
            """SELECT id, product_name, category, brand, price, purchase_date, quantity
               FROM purchase_history
               WHERE user_id = ?
               ORDER BY purchase_date ASC""",
            (user_id,)
        ) or []

        if not purchases or len(purchases) < 2:
            return {
                "has_sufficient_data": False,
                "message": "More shopping history is needed to calculate statistically reliable replenishment dates.",
                "predictions": []
            }

        # Group purchases by product_name or category
        grouped_items: Dict[str, List[Dict[str, Any]]] = {}
        for r in purchases:
            p = database.row_to_dict(r) if hasattr(database, "row_to_dict") else dict(r)
            key = p["product_name"].strip()
            if key not in grouped_items:
                grouped_items[key] = []
            grouped_items[key].append(p)

        predictions = []

        for p_name, p_list in grouped_items.items():
            if len(p_list) < 2:
                continue

            # Parse dates
            dates = []
            for item in p_list:
                dt_str = item.get("purchase_date")
                if dt_str:
                    try:
                        dates.append(datetime.strptime(dt_str.split("T")[0], "%Y-%m-%d").date())
                    except Exception:
                        pass
            dates.sort()

            if len(dates) < 2:
                continue

            # Calculate intervals in days
            intervals = [(dates[i] - dates[i-1]).days for i in range(1, len(dates))]
            positive_intervals = [i for i in intervals if i > 0]

            if not positive_intervals:
                continue

            median_interval = int(statistics.median(positive_intervals))
            last_date = dates[-1]

            # Projected next date
            projected_date = last_date + timedelta(days=median_interval)

            # If projected date is in the past, roll forward by intervals until future
            while projected_date < today:
                projected_date += timedelta(days=median_interval)

            days_until = (projected_date - today).days

            # Determine confidence level
            count = len(dates)
            variance = statistics.stdev(positive_intervals) if len(positive_intervals) > 1 else 0
            if count >= 3 and variance <= 15:
                confidence = "High"
                conf_score = 0.90
            elif count >= 2:
                confidence = "Moderate"
                conf_score = 0.75
            else:
                confidence = "Low"
                conf_score = 0.50

            latest_item = p_list[-1]
            cat = latest_item.get("category", "General")
            price = float(latest_item.get("price") or 0.0)

            predictions.append({
                "product_name": p_name,
                "category": cat,
                "last_purchased_date": last_date.strftime("%Y-%m-%d"),
                "estimated_interval_days": median_interval,
                "historical_purchase_count": count,
                "predicted_next_date": projected_date.strftime("%Y-%m-%d"),
                "days_until_next_purchase": days_until,
                "estimated_budget": price,
                "confidence_level": confidence,
                "confidence_score": conf_score,
                "source": "Recorded Purchase Interval Analysis",
                "explanation": f"Based on {count} verified previous purchases with a typical {median_interval}-day replenishment cycle."
            })

        # Sort by closest upcoming date
        predictions.sort(key=lambda x: x["predicted_next_date"])

        return {
            "has_sufficient_data": len(predictions) > 0,
            "message": f"Identified {len(predictions)} recurring replenishment predictions." if predictions else "More repeat purchases needed to establish clear intervals.",
            "predictions": predictions
        }

    # =========================================================================
    # 3. MY SHOPPING PLANS (CRUD + Filters)
    # =========================================================================

    @classmethod
    def create_shopping_plan(cls, user_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Creates a manual shopping plan with ownership validation."""
        title = (data.get("title") or "").strip()
        target_date = data.get("target_date")
        category = data.get("category", "All")
        product_id = data.get("product_id")
        budget = float(data.get("estimated_budget") or data.get("budget") or 0.0)
        quantity = max(1, int(data.get("quantity") or 1))
        priority = data.get("priority", "Medium")
        notes = (data.get("notes") or "").strip()

        if not title:
            raise ValueError("Plan title is required.")
        if not target_date:
            raise ValueError("Target purchase date is required.")

        # Check date format
        try:
            p_date = datetime.strptime(target_date.split("T")[0], "%Y-%m-%d").date()
        except Exception:
            raise ValueError("Target date must be in YYYY-MM-DD format.")

        new_id = database.execute_db(
            """INSERT INTO customer_shopping_plans
               (user_id, title, category, product_id, target_date, estimated_budget, quantity, priority, notes, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'active')""",
            (user_id, title, category, product_id, target_date, budget, quantity, priority, notes)
        )

        return {
            "success": True,
            "id": new_id,
            "message": "Shopping plan created successfully."
        }

    @classmethod
    def get_shopping_plans(cls, user_id: int, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns customer shopping plans grouped by status."""
        today = _get_utc_today()
        sql = "SELECT * FROM customer_shopping_plans WHERE user_id = ?"
        params = [user_id]

        if status_filter and status_filter.lower() != "all":
            if status_filter.lower() == "overdue":
                sql += " AND status = 'active' AND target_date < ?"
                params.append(today.strftime("%Y-%m-%d"))
            else:
                sql += " AND status = ?"
                params.append(status_filter.lower())

        sql += " ORDER BY target_date ASC"

        rows = database.query_db(sql, tuple(params)) or []
        plans = []
        for r in rows:
            p = database.row_to_dict(r) if hasattr(database, "row_to_dict") else dict(r)
            t_str = p.get("target_date", "")
            is_overdue = False
            if t_str and p.get("status") == "active":
                try:
                    if datetime.strptime(t_str, "%Y-%m-%d").date() < today:
                        is_overdue = True
                except Exception:
                    pass

            p["is_overdue"] = is_overdue
            p["display_status"] = "overdue" if is_overdue else p.get("status", "active")
            plans.append(p)
        return plans

    @classmethod
    def update_shopping_plan(cls, user_id: int, plan_id: int, data: Dict[str, Any]) -> bool:
        """Updates plan with strict ownership check."""
        existing = database.query_db(
            "SELECT id FROM customer_shopping_plans WHERE id = ? AND user_id = ?",
            (plan_id, user_id),
            one=True
        )
        if not existing:
            return False

        fields = []
        values = []
        for key in ["title", "category", "product_id", "target_date", "estimated_budget", "quantity", "priority", "notes", "status"]:
            if key in data:
                fields.append(f"{key} = ?")
                values.append(data[key])

        if "status" in data and data["status"] == "completed":
            fields.append("completed_at = CURRENT_TIMESTAMP")

        if not fields:
            return True

        fields.append("updated_at = CURRENT_TIMESTAMP")
        values.extend([plan_id, user_id])

        database.execute_db(
            f"UPDATE customer_shopping_plans SET {', '.join(fields)} WHERE id = ? AND user_id = ?",
            tuple(values)
        )
        return True

    @classmethod
    def delete_shopping_plan(cls, user_id: int, plan_id: int) -> bool:
        """Deletes plan with strict ownership check."""
        existing = database.query_db(
            "SELECT id FROM customer_shopping_plans WHERE id = ? AND user_id = ?",
            (plan_id, user_id),
            one=True
        )
        if not existing:
            return False

        database.execute_db(
            "DELETE FROM customer_shopping_plans WHERE id = ? AND user_id = ?",
            (plan_id, user_id)
        )
        return True

    # =========================================================================
    # 4. OCCASIONS AND EVENTS (Customer Managed Occasions)
    # =========================================================================

    @classmethod
    def create_occasion(cls, user_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Creates an occasion record managed by the customer."""
        event_name = (data.get("event_name") or data.get("title") or "").strip()
        event_date = data.get("event_date")
        prep_date = data.get("prep_start_date")
        occ_type = data.get("occasion_type") or data.get("event_type") or "Custom"
        reqs = (data.get("shopping_requirements") or data.get("notes") or "").strip()
        budget = float(data.get("estimated_budget") or data.get("budget") or 0.0)
        rem_days = int(data.get("reminder_days_before") or 7)

        if not event_name:
            raise ValueError("Event name is required.")
        if not event_date:
            raise ValueError("Event date is required.")

        new_id = database.execute_db(
            """INSERT INTO customer_shopping_occasions
               (user_id, event_name, event_date, prep_start_date, occasion_type, shopping_requirements, estimated_budget, notes, reminder_days_before)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, event_name, event_date, prep_date, occ_type, reqs, budget, reqs, rem_days)
        )

        return {"success": True, "id": new_id, "message": "Occasion saved successfully."}

    @classmethod
    def get_occasions(cls, user_id: int) -> List[Dict[str, Any]]:
        """Fetch occasions strictly for the authenticated customer."""
        rows = database.query_db(
            "SELECT * FROM customer_shopping_occasions WHERE user_id = ? ORDER BY event_date ASC",
            (user_id,)
        ) or []
        return [database.row_to_dict(r) if hasattr(database, "row_to_dict") else dict(r) for r in rows]

    @classmethod
    def delete_occasion(cls, user_id: int, occasion_id: int) -> bool:
        """Deletes occasion with ownership verification."""
        existing = database.query_db(
            "SELECT id FROM customer_shopping_occasions WHERE id = ? AND user_id = ?",
            (occasion_id, user_id),
            one=True
        )
        if not existing:
            return False
        database.execute_db(
            "DELETE FROM customer_shopping_occasions WHERE id = ? AND user_id = ?",
            (occasion_id, user_id)
        )
        return True

    # =========================================================================
    # 5. FUTURE SHOPPING BUDGET (Integration with Feature 4)
    # =========================================================================

    @classmethod
    def get_future_budget_summary(cls, user_id: int) -> Dict[str, Any]:
        """
        Calculates upcoming shopping expenses from active plans, occasions, and milestones.
        Integrates with Feature 4 customer_budgets table for affordability context.
        """
        today = _get_utc_today()

        # 1. Planned shopping from plans
        plans = cls.get_shopping_plans(user_id, status_filter="active")
        # 2. Planned shopping from occasions
        occasions = [o for o in cls.get_occasions(user_id) if o.get("status") == "active"]
        # 3. Calendar events
        cal_events = database.query_db(
            "SELECT * FROM shopping_calendar_events WHERE user_id = ? AND status = 'upcoming'",
            (user_id,)
        ) or []

        monthly_expenses: Dict[str, float] = {}
        category_expenses: Dict[str, float] = {}
        total_planned = 0.0

        for p in plans:
            b = float(p.get("estimated_budget") or 0.0)
            total_planned += b
            d_str = p.get("target_date", "")[:7] or "Unscheduled"
            cat = p.get("category") or "All"
            monthly_expenses[d_str] = round(monthly_expenses.get(d_str, 0.0) + b, 2)
            category_expenses[cat] = round(category_expenses.get(cat, 0.0) + b, 2)

        for o in occasions:
            b = float(o.get("estimated_budget") or 0.0)
            total_planned += b
            d_str = o.get("event_date", "")[:7] or "Unscheduled"
            monthly_expenses[d_str] = round(monthly_expenses.get(d_str, 0.0) + b, 2)
            category_expenses["Occasions"] = round(category_expenses.get("Occasions", 0.0) + b, 2)

        for r in cal_events:
            d = database.row_to_dict(r) if hasattr(database, "row_to_dict") else dict(r)
            b = float(d.get("budget") or 0.0)
            total_planned += b
            d_str = (d.get("event_date") or "")[:7] or "Unscheduled"
            cat = d.get("category") or "General"
            monthly_expenses[d_str] = round(monthly_expenses.get(d_str, 0.0) + b, 2)
            category_expenses[cat] = round(category_expenses.get(cat, 0.0) + b, 2)

        # Feature 4 Active Budget Context
        active_monthly_budget = 0.0
        try:
            b_row = database.query_db(
                "SELECT monthly_budget FROM customer_budgets WHERE user_id = ?",
                (user_id,),
                one=True
            )
            if b_row:
                b_dict = database.row_to_dict(b_row) if hasattr(database, "row_to_dict") else dict(b_row)
                active_monthly_budget = float(b_dict.get("monthly_budget") or 0.0)
        except Exception:
            pass

        current_month_key = today.strftime("%Y-%m")
        current_month_planned = monthly_expenses.get(current_month_key, 0.0)
        within_budget = (current_month_planned <= active_monthly_budget) if active_monthly_budget > 0 else True

        return {
            "total_estimated_future_expenses": round(total_planned, 2),
            "current_month_key": current_month_key,
            "current_month_planned": round(current_month_planned, 2),
            "active_monthly_budget": round(active_monthly_budget, 2),
            "is_within_monthly_budget": within_budget,
            "monthly_planned_breakdown": monthly_expenses,
            "category_planned_breakdown": category_expenses,
            "total_active_items_tracked": len(plans) + len(occasions) + len(cal_events)
        }

    # =========================================================================
    # 6. REMINDERS AND NOTIFICATIONS (In-App Reminder Management)
    # =========================================================================

    @classmethod
    def get_in_app_reminders(cls, user_id: int) -> List[Dict[str, Any]]:
        """Fetch active in-app reminders with due-soon and snooze awareness."""
        today = _get_utc_today()
        rows = database.query_db(
            """SELECT * FROM shopping_reminders
               WHERE user_id = ? AND is_enabled = 1 AND status != 'dismissed' AND status != 'completed'
               ORDER BY next_reminder_date ASC""",
            (user_id,)
        ) or []

        reminders = []
        for r in rows:
            item = database.row_to_dict(r) if hasattr(database, "row_to_dict") else dict(r)
            snooze_until = item.get("snooze_until")
            if snooze_until:
                try:
                    s_date = datetime.strptime(snooze_until, "%Y-%m-%d").date()
                    if s_date > today:
                        item["is_currently_snoozed"] = True
                        item["snooze_days_remaining"] = (s_date - today).days
                    else:
                        item["is_currently_snoozed"] = False
                except Exception:
                    item["is_currently_snoozed"] = False
            else:
                item["is_currently_snoozed"] = False

            reminders.append(item)
        return reminders

    @classmethod
    def snooze_reminder(cls, user_id: int, reminder_id: int, snooze_days: int = 3) -> bool:
        """Snooze reminder by given number of days with ownership check."""
        today = _get_utc_today()
        snooze_target = today + timedelta(days=max(1, snooze_days))

        existing = database.query_db(
            "SELECT id FROM shopping_reminders WHERE id = ? AND user_id = ?",
            (reminder_id, user_id),
            one=True
        )
        if not existing:
            return False

        database.execute_db(
            "UPDATE shopping_reminders SET snooze_until = ?, status = 'snoozed' WHERE id = ? AND user_id = ?",
            (snooze_target.strftime("%Y-%m-%d"), reminder_id, user_id)
        )
        return True

    @classmethod
    def dismiss_reminder(cls, user_id: int, reminder_id: int) -> bool:
        """Dismisses an in-app reminder."""
        existing = database.query_db(
            "SELECT id FROM shopping_reminders WHERE id = ? AND user_id = ?",
            (reminder_id, user_id),
            one=True
        )
        if not existing:
            return False

        database.execute_db(
            "UPDATE shopping_reminders SET status = 'dismissed' WHERE id = ? AND user_id = ?",
            (reminder_id, user_id)
        )
        return True

    # =========================================================================
    # 7. CALENDAR INSIGHTS AND HISTORY (Factual Planning Analytics)
    # =========================================================================

    @classmethod
    def get_calendar_analytics(cls, user_id: int) -> Dict[str, Any]:
        """
        Computes factual completion and on-time planning metrics.
        No fabricated accuracy percentages.
        """
        today = _get_utc_today()

        plans = database.query_db(
            "SELECT * FROM customer_shopping_plans WHERE user_id = ?",
            (user_id,)
        ) or []

        total_plans = len(plans)
        completed = 0
        overdue = 0
        active = 0
        cancelled = 0

        for r in plans:
            p = database.row_to_dict(r) if hasattr(database, "row_to_dict") else dict(r)
            st = p.get("status", "active")
            if st == "completed":
                completed += 1
            elif st == "cancelled":
                cancelled += 1
            elif st == "active":
                t_str = p.get("target_date")
                if t_str:
                    try:
                        if datetime.strptime(t_str, "%Y-%m-%d").date() < today:
                            overdue += 1
                        else:
                            active += 1
                    except Exception:
                        active += 1
                else:
                    active += 1

        completion_rate = round((completed / total_plans * 100.0), 1) if total_plans > 0 else 0.0

        return {
            "total_plans": total_plans,
            "completed_plans": completed,
            "active_plans": active,
            "overdue_plans": overdue,
            "cancelled_plans": cancelled,
            "completion_rate_percentage": completion_rate,
            "has_data": total_plans > 0
        }
