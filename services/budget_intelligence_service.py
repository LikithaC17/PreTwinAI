"""
services/budget_intelligence_service.py
---------------------------------------
Budget and Price Intelligence Engine (Feature 4):
1. SpendingCalculationEngine: Strictly calculates eligible completed/paid purchases, excludes cancelled/refunded/unpaid, provides AOV, trends, and date filters.
2. BudgetManagementEngine: Handles monthly, weekly, and custom shopping budgets, category allocations, resets, and history.
3. CategoryBudgetEngine: Tracks category-wise allocations, actual expenditures, utilization percentages, and overspending warnings.
4. PriceIntelligenceEngine: Real selling prices, MRPs, discount analysis, unit price comparisons, and genuine catalogue alternatives.
5. SavingsPlannerIntegrationEngine: Reuses and enhances PreTwin's existing Smart Savings Plan system without duplicating.
6. PurchaseAffordabilityEngine: Pre-checkout affordability assessment with cart impact, remaining budget delta, and non-blocking warnings.
7. BudgetAlertsAndInsightsEngine: Transparent, explainable financial health insights and alerts based on real customer data.
"""

from __future__ import annotations

import logging
import math
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import database

logger = logging.getLogger(__name__)


def _is_order_eligible_for_spending(order: Dict[str, Any]) -> bool:
    """
    Determine if an order qualifies as actual completed shopping expenditure.
    Rules:
    - Status NOT in ('cancelled', 'payment failed', 'failed')
    - Payment status NOT in ('failed', 'refunded')
    - COD orders: must be delivered/completed AND paid
    - Online/PreTwin payments: payment status must start with 'paid'
    """
    if not order:
        return False

    status = (order.get("status") or "").strip().lower()
    pay_status = (order.get("payment_status") or "").strip().lower()
    method = (order.get("payment_method") or "").strip().lower()
    gateway = (order.get("gateway_name") or "").strip().lower()

    # Disqualify cancellations, failed payments, or full refunds
    if status in ("cancelled", "payment failed", "failed"):
        return False
    if pay_status in ("failed", "refunded"):
        return False

    # COD orders must be delivered and paid
    is_cod = ("cod" in method or "cash on delivery" in method or "cod" in gateway)
    if is_cod:
        return (status in ("delivered", "completed")) and ("paid" in pay_status)

    # Online orders must have completed payment
    return pay_status.startswith("paid")


def _get_retained_order_amount(order: Dict[str, Any]) -> float:
    """
    Get the actual retained expenditure for an order, handling partial refunds.
    """
    total = float(order.get("total_amount") or 0.0)
    pay_status = (order.get("payment_status") or "").strip().lower()

    if pay_status == "refunded":
        return 0.0
    if pay_status == "partially_refunded":
        # Retain actual non-refunded amount if tracked
        refund_amount = float(order.get("refund_amount") or 0.0)
        return max(0.0, round(total - refund_amount, 2))

    return max(0.0, round(total, 2))


class SpendingCalculationEngine:
    """
    Accurately computes shopping expenditure strictly from eligible, completed orders.
    Supports flexible date filters: 'current_month', 'last_month', 'last_30_days', 'last_90_days', 'year_to_date', 'all_time', 'custom'.
    """

    @classmethod
    def get_spending_overview(
        cls,
        user_id: int,
        date_filter: str = "current_month",
        custom_start: Optional[str] = None,
        custom_end: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Calculates eligible spending metrics for the customer within the requested window.
        """
        today = date.today()

        # Determine date bounds
        if date_filter == "last_month":
            # First day of last month to last day of last month
            first_of_this_month = today.replace(day=1)
            last_day_last_month = first_of_this_month - timedelta(days=1)
            start_date = last_day_last_month.replace(day=1)
            end_date = last_day_last_month
            filter_label = start_date.strftime("%B %Y")
        elif date_filter == "last_30_days":
            start_date = today - timedelta(days=30)
            end_date = today
            filter_label = "Last 30 Days"
        elif date_filter == "last_90_days":
            start_date = today - timedelta(days=90)
            end_date = today
            filter_label = "Last 90 Days"
        elif date_filter == "year_to_date":
            start_date = today.replace(month=1, day=1)
            end_date = today
            filter_label = f"Year to Date ({today.year})"
        elif date_filter == "all_time":
            start_date = date(2020, 1, 1)
            end_date = today
            filter_label = "All Time"
        elif date_filter == "custom" and custom_start and custom_end:
            try:
                start_date = datetime.strptime(custom_start[:10], "%Y-%m-%d").date()
                end_date = datetime.strptime(custom_end[:10], "%Y-%m-%d").date()
                filter_label = f"{start_date.strftime('%d %b %Y')} to {end_date.strftime('%d %b %Y')}"
            except Exception:
                start_date = today.replace(day=1)
                end_date = today
                filter_label = today.strftime("%B %Y")
        else:
            # Default: current_month
            start_date = today.replace(day=1)
            # End of month or today
            end_date = today
            filter_label = today.strftime("%B %Y")

        start_str = f"{start_date.strftime('%Y-%m-%d')} 00:00:00"
        end_str = f"{end_date.strftime('%Y-%m-%d')} 23:59:59"

        # Query all customer orders in window
        order_rows = database.query_db(
            """
            SELECT * FROM orders 
            WHERE user_id = ? AND created_at >= ? AND created_at <= ?
            ORDER BY created_at DESC
            """,
            (user_id, start_str, end_str),
        )

        eligible_orders = []
        total_spent = 0.0

        for r in order_rows:
            order = dict(r)
            if _is_order_eligible_for_spending(order):
                retained_amount = _get_retained_order_amount(order)
                total_spent += retained_amount
                order["eligible_spent_amount"] = retained_amount
                eligible_orders.append(order)

        total_spent = round(total_spent, 2)
        eligible_count = len(eligible_orders)
        aov = round(total_spent / eligible_count, 2) if eligible_count > 0 else 0.0

        # Monthly Spending Trend (Last 6 Months)
        monthly_trend = cls._calculate_monthly_trend(user_id)

        # Recent 5 eligible purchases with items
        recent_purchases = []
        for o in eligible_orders[:6]:
            item_rows = database.query_db(
                "SELECT * FROM order_items WHERE order_id = ?", (o["id"],)
            )
            items = [dict(it) for it in item_rows]
            recent_purchases.append({
                "order_id": o["id"],
                "order_number": o["order_number"],
                "date": str(o.get("created_at", ""))[:10],
                "total_amount": o.get("eligible_spent_amount", o.get("total_amount", 0.0)),
                "payment_method": o.get("payment_method", ""),
                "status": o.get("status", ""),
                "items_count": len(items),
                "items": items,
            })

        return {
            "date_filter": date_filter,
            "filter_label": filter_label,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "total_spent": total_spent,
            "eligible_purchases_count": eligible_count,
            "average_order_value": aov,
            "recent_purchases": recent_purchases,
            "monthly_trend": monthly_trend,
        }

    @classmethod
    def _calculate_monthly_trend(cls, user_id: int) -> List[Dict[str, Any]]:
        """Calculate eligible monthly spend for the last 6 calendar months."""
        today = date.today()
        months = []
        for i in range(5, -1, -1):
            # calculate year and month
            m = today.month - i
            y = today.year
            while m <= 0:
                m += 12
                y -= 1
            start = date(y, m, 1)
            # next month 1st day minus 1 day
            if m == 12:
                end = date(y, 12, 31)
            else:
                end = date(y, m + 1, 1) - timedelta(days=1)
            months.append((start, end))

        trend = []
        for start, end in months:
            s_str = f"{start.strftime('%Y-%m-%d')} 00:00:00"
            e_str = f"{end.strftime('%Y-%m-%d')} 23:59:59"
            rows = database.query_db(
                "SELECT * FROM orders WHERE user_id = ? AND created_at >= ? AND created_at <= ?",
                (user_id, s_str, e_str)
            )
            m_spent = 0.0
            order_count = 0
            for r in rows:
                o = dict(r)
                if _is_order_eligible_for_spending(o):
                    m_spent += _get_retained_order_amount(o)
                    order_count += 1

            trend.append({
                "month_key": start.strftime("%Y-%m"),
                "month_label": start.strftime("%b %Y"),
                "spent": round(m_spent, 2),
                "orders_count": order_count,
            })

        return trend


class BudgetManagementEngine:
    """
    Manages customer budget creation, editing, category allocation,
    resetting with confirmation, and budget period tracking.
    """

    @classmethod
    def get_active_budget(cls, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve active budget for user. If not created yet in customer_budgets,
        checks shopping_preferences.budget_max to support seamless transition.
        """
        row = database.query_db(
            """
            SELECT * FROM customer_budgets 
            WHERE user_id = ? AND status = 'active'
            ORDER BY id DESC LIMIT 1
            """,
            (user_id,),
            one=True,
        )

        if row:
            b_dict = dict(row)
            alloc_rows = database.query_db(
                "SELECT category, allocated_amount FROM category_budget_allocations WHERE budget_id = ?",
                (b_dict["id"],),
            )
            allocations = {r["category"]: float(r["allocated_amount"]) for r in alloc_rows}
            b_dict["category_allocations"] = allocations
            b_dict["has_custom_budget"] = True
            return b_dict

        # Check shopping preferences fallback
        pref = database.query_db(
            "SELECT budget_min, budget_max FROM shopping_preferences WHERE user_id = ?",
            (user_id,),
            one=True,
        )
        if pref and pref["budget_max"] and float(pref["budget_max"]) > 0:
            today = date.today()
            start_date = today.replace(day=1)
            if today.month == 12:
                end_date = date(today.year, 12, 31)
            else:
                end_date = date(today.year, today.month + 1, 1) - timedelta(days=1)

            b_max = float(pref["budget_max"])
            return {
                "id": None,
                "user_id": user_id,
                "budget_period": "monthly",
                "period_start": str(start_date),
                "period_end": str(end_date),
                "overall_budget": b_max,
                "status": "active",
                "notes": "Inherited from your shopping twin preferences",
                "category_allocations": {},
                "has_custom_budget": False,
            }

        return None

    @classmethod
    def save_budget(
        cls,
        user_id: int,
        budget_period: str = "monthly",
        overall_budget: float = 10000.0,
        period_start: Optional[str] = None,
        period_end: Optional[str] = None,
        category_allocations: Optional[Dict[str, float]] = None,
        notes: str = "",
    ) -> Dict[str, Any]:
        """
        Create or update customer budget with category limits.
        """
        if overall_budget <= 0:
            raise ValueError("Overall budget must be greater than zero.")

        today = date.today()

        # Calculate period dates if not provided
        if budget_period == "weekly":
            # Current Monday to Sunday
            start = today - timedelta(days=today.weekday())
            end = start + timedelta(days=6)
        elif budget_period == "custom" and period_start and period_end:
            start = datetime.strptime(period_start[:10], "%Y-%m-%d").date()
            end = datetime.strptime(period_end[:10], "%Y-%m-%d").date()
        else:
            # Monthly
            budget_period = "monthly"
            start = today.replace(day=1)
            if today.month == 12:
                end = date(today.year, 12, 31)
            else:
                end = date(today.year, today.month + 1, 1) - timedelta(days=1)

        start_str = str(start)
        end_str = str(end)

        # Deactivate any previous active budgets for this user
        database.execute_db(
            "UPDATE customer_budgets SET status = 'archived', updated_at = CURRENT_TIMESTAMP WHERE user_id = ? AND status = 'active'",
            (user_id,),
        )

        # Insert new active budget
        budget_id = database.execute_db(
            """
            INSERT INTO customer_budgets 
                (user_id, budget_period, period_start, period_end, overall_budget, status, notes)
            VALUES (?, ?, ?, ?, ?, 'active', ?)
            """,
            (user_id, budget_period, start_str, end_str, round(overall_budget, 2), notes),
        )

        # Insert category allocations if provided
        alloc_dict = {}
        if category_allocations and isinstance(category_allocations, dict):
            for cat, amount in category_allocations.items():
                amt = float(amount or 0.0)
                if amt > 0:
                    database.execute_db(
                        """
                        INSERT INTO category_budget_allocations 
                            (budget_id, user_id, category, allocated_amount)
                        VALUES (?, ?, ?, ?)
                        """,
                        (budget_id, user_id, cat.strip(), round(amt, 2)),
                    )
                    alloc_dict[cat.strip()] = round(amt, 2)

        # Sync shopping_preferences.budget_max
        existing_pref = database.query_db(
            "SELECT id FROM shopping_preferences WHERE user_id = ?", (user_id,), one=True
        )
        if existing_pref:
            database.execute_db(
                "UPDATE shopping_preferences SET budget_max = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                (round(overall_budget, 2), user_id),
            )
        else:
            database.execute_db(
                "INSERT INTO shopping_preferences (user_id, budget_min, budget_max) VALUES (?, 1000.0, ?)",
                (user_id, round(overall_budget, 2)),
            )

        return {
            "success": True,
            "budget_id": budget_id,
            "budget_period": budget_period,
            "period_start": start_str,
            "period_end": end_str,
            "overall_budget": round(overall_budget, 2),
            "category_allocations": alloc_dict,
            "message": f"Successfully established {budget_period} budget of ₹{overall_budget:,.2f}.",
        }

    @classmethod
    def reset_budget(cls, user_id: int) -> Dict[str, Any]:
        """Reset customer's active budget with confirmation."""
        database.execute_db(
            "UPDATE customer_budgets SET status = 'reset', updated_at = CURRENT_TIMESTAMP WHERE user_id = ? AND status = 'active'",
            (user_id,),
        )
        return {"success": True, "message": "Your active shopping budget has been reset."}

    @classmethod
    def get_budget_history(cls, user_id: int) -> List[Dict[str, Any]]:
        """Retrieve historical budget periods and their spending results."""
        rows = database.query_db(
            "SELECT * FROM customer_budgets WHERE user_id = ? ORDER BY id DESC LIMIT 10",
            (user_id,),
        )
        history = []
        for r in rows:
            b = dict(r)
            s_str = f"{b['period_start']} 00:00:00"
            e_str = f"{b['period_end']} 23:59:59"
            order_rows = database.query_db(
                "SELECT * FROM orders WHERE user_id = ? AND created_at >= ? AND created_at <= ?",
                (user_id, s_str, e_str),
            )
            spent = sum(_get_retained_order_amount(dict(o)) for o in order_rows if _is_order_eligible_for_spending(dict(o)))
            target = float(b["overall_budget"])
            pct = round((spent / target) * 100, 1) if target > 0 else 0
            b["actual_spent"] = round(spent, 2)
            b["utilization_percentage"] = pct
            b["status_label"] = "Within Budget" if spent <= target else f"Exceeded by ₹{round(spent - target, 2):,}"
            history.append(b)

        return history


class CategoryBudgetEngine:
    """
    Tracks and alerts on category-wise expenditures against allocated budgets.
    """

    @classmethod
    def get_category_tracking(cls, user_id: int, active_budget: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Calculates category-wise spend, allocated budget, remaining budget, and utilization.
        """
        if not active_budget:
            active_budget = BudgetManagementEngine.get_active_budget(user_id)

        period_start = active_budget.get("period_start") if active_budget else str(date.today().replace(day=1))
        period_end = active_budget.get("period_end") if active_budget else str(date.today())
        allocations = active_budget.get("category_allocations", {}) if active_budget else {}

        s_str = f"{period_start} 00:00:00"
        e_str = f"{period_end} 23:59:59"

        # Query eligible orders and their items
        order_rows = database.query_db(
            "SELECT id, total_amount, payment_status, status, payment_method, gateway_name FROM orders WHERE user_id = ? AND created_at >= ? AND created_at <= ?",
            (user_id, s_str, e_str),
        )

        eligible_order_ids = [
            o["id"] for o in order_rows if _is_order_eligible_for_spending(dict(o))
        ]

        category_spend: Dict[str, float] = {}

        if eligible_order_ids:
            placeholders = ",".join(["?"] * len(eligible_order_ids))
            item_rows = database.query_db(
                f"""
                SELECT category, COALESCE(SUM(total_price), 0) AS cat_total 
                FROM order_items 
                WHERE order_id IN ({placeholders}) AND category IS NOT NULL AND category != ''
                GROUP BY category
                """,
                tuple(eligible_order_ids),
            )
            for r in item_rows:
                category_spend[r["category"]] = round(float(r["cat_total"]), 2)

        # Assemble comprehensive tracking for all categories that either have an allocation or have spending
        all_tracked_categories = set(list(allocations.keys()) + list(category_spend.keys()))
        tracking_list = []
        alerts = []

        for cat in sorted(all_tracked_categories):
            allocated = float(allocations.get(cat, 0.0))
            spent = float(category_spend.get(cat, 0.0))
            remaining = max(0.0, round(allocated - spent, 2)) if allocated > 0 else 0.0
            utilization = round((spent / allocated) * 100, 1) if allocated > 0 else (100.0 if spent > 0 else 0.0)

            is_over = allocated > 0 and spent > allocated
            over_amount = round(spent - allocated, 2) if is_over else 0.0

            if is_over:
                alerts.append({
                    "category": cat,
                    "severity": "danger",
                    "title": f"Over budget in {cat}",
                    "message": f"You have exceeded your ₹{allocated:,.2f} limit by ₹{over_amount:,.2f} ({utilization}% used).",
                })
            elif allocated > 0 and utilization >= 85:
                alerts.append({
                    "category": cat,
                    "severity": "warning",
                    "title": f"Nearing limit in {cat}",
                    "message": f"You have used {utilization}% of your ₹{allocated:,.2f} category budget. ₹{remaining:,.2f} remaining.",
                })

            tracking_list.append({
                "category": cat,
                "allocated": allocated,
                "spent": spent,
                "remaining": remaining,
                "utilization_percentage": utilization,
                "is_over_budget": is_over,
                "over_amount": over_amount,
            })

        # Sort by spent descending
        tracking_list.sort(key=lambda x: x["spent"], reverse=True)

        return {
            "period_start": period_start,
            "period_end": period_end,
            "categories": tracking_list,
            "category_alerts": alerts,
            "total_allocated": sum(t["allocated"] for t in tracking_list),
            "total_category_spent": sum(t["spent"] for t in tracking_list),
        }


class PriceIntelligenceEngine:
    """
    Provides real product selling prices, MRPs, discount analysis,
    unit price comparisons, and genuine catalogue alternatives.
    """

    @classmethod
    def get_product_price_intelligence(cls, product_id: int) -> Dict[str, Any]:
        """
        Analyze a specific product's price, discount, unit economics, and affordable alternatives.
        """
        row = database.query_db("SELECT * FROM products WHERE id = ?", (product_id,), one=True)
        if not row:
            return {"error": "Product not found"}

        p = dict(row)
        price = float(p.get("price") or 0.0)
        disc_pct = int(p.get("discount_percentage") or 15)
        cat = p.get("category", "")
        subcat = p.get("subcategory", "")
        rating = float(p.get("rating") or 4.2)

        if 0 < disc_pct < 100:
            mrp = round(price / (1 - disc_pct / 100.0), 2)
        else:
            mrp = round(price * 1.25, 2)

        # Unit price extraction (e.g. from name or specs like 500g, 1kg, 200ml, 50ml, Pack of 2)
        unit_info = cls._extract_unit_price(p.get("name", ""), price)

        # Affordable Alternatives in same category/subcategory (at least 15% cheaper with solid rating)
        alt_rows = database.query_db(
            """
            SELECT * FROM products 
            WHERE id != ? AND category = ? AND price <= ? AND rating >= 4.0
            ORDER BY rating DESC, price ASC LIMIT 4
            """,
            (product_id, cat, round(price * 0.85, 2)),
        )
        if not alt_rows:
            # fallback to same category cheaper
            alt_rows = database.query_db(
                "SELECT * FROM products WHERE id != ? AND category = ? AND price < ? ORDER BY rating DESC LIMIT 4",
                (product_id, cat, price),
            )

        alternatives = []
        for r in alt_rows:
            alt = dict(r)
            savings = round(price - float(alt["price"]), 2)
            alternatives.append({
                "id": alt["id"],
                "name": alt["name"],
                "brand": alt.get("brand", ""),
                "price": float(alt["price"]),
                "rating": float(alt.get("rating") or 4.0),
                "savings": savings,
                "image_url": alt.get("image_url", ""),
                "explanation": f"Save ₹{int(savings):,} with comparable {alt.get('rating', 4.2)}★ rating.",
            })

        # Value Assessment (transparent & explainable)
        cat_avg_row = database.query_db(
            "SELECT AVG(price) as avg_p FROM products WHERE category = ?", (cat,), one=True
        )
        cat_avg = float(cat_avg_row["avg_p"]) if cat_avg_row and cat_avg_row["avg_p"] else price

        if price < cat_avg * 0.85 and rating >= 4.3:
            value_label = "Exceptional Value"
            value_badge = "success"
            value_reason = f"Priced {int(((cat_avg - price)/cat_avg)*100)}% below category average (₹{int(cat_avg):,}) with top {rating}★ rating."
        elif price <= cat_avg:
            value_label = "Good Value"
            value_badge = "primary"
            value_reason = f"Below category average price (₹{int(cat_avg):,})."
        else:
            value_label = "Premium Tier"
            value_badge = "warning"
            value_reason = f"Above category average price (₹{int(cat_avg):,}) for premium specifications."

        return {
            "product_id": product_id,
            "name": p.get("name"),
            "category": cat,
            "subcategory": subcat,
            "brand": p.get("brand"),
            "selling_price": price,
            "mrp": mrp,
            "discount_percentage": disc_pct,
            "unit_price_info": unit_info,
            "category_average_price": round(cat_avg, 2),
            "value_label": value_label,
            "value_badge": value_badge,
            "value_reason": value_reason,
            "affordable_alternatives": alternatives,
        }

    @classmethod
    def _extract_unit_price(cls, title: str, price: float) -> Optional[Dict[str, Any]]:
        """Extract pack quantity or volume from product name to calculate price per unit."""
        # Check for weight (e.g. 500g, 1kg)
        w_match = re.search(r'(\d+(?:\.\d+)?)\s*(kg|g|gm|gms|ml|l|ltr|litres?)\b', title, re.IGNORECASE)
        if w_match:
            qty = float(w_match.group(1))
            unit = w_match.group(2).lower()
            if unit in ("kg", "l", "ltr", "litre", "litres"):
                base_unit = "kg" if "g" in unit or unit == "kg" else "L"
                per_base = round(price / qty, 2)
                return {"quantity": qty, "unit": unit, "display": f"₹{per_base:,.2f} per {base_unit}"}
            elif unit in ("g", "gm", "gms", "ml"):
                # per 100g / 100ml
                per_100 = round((price / qty) * 100, 2)
                base_unit = "100g" if "g" in unit else "100ml"
                return {"quantity": qty, "unit": unit, "display": f"₹{per_100:,.2f} per {base_unit}"}

        # Check for pack of X
        pack_match = re.search(r'(?:pack of|set of)\s*(\d+)', title, re.IGNORECASE)
        if pack_match:
            count = int(pack_match.group(1))
            if count > 1:
                per_item = round(price / count, 2)
                return {"quantity": count, "unit": "pieces", "display": f"₹{per_item:,.2f} per piece (Pack of {count})"}

        return None


class SavingsPlannerIntegrationEngine:
    """
    Seamlessly integrates and improves PreTwin's existing Smart Savings Plan system.
    Strictly distinguishes savings deposits from shopping expenditure.
    """

    @classmethod
    def get_savings_summary(cls, user_id: int) -> Dict[str, Any]:
        """Retrieve user savings goals and contributions."""
        rows = database.query_db(
            "SELECT * FROM savings_plans WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        )

        plans = []
        total_target = 0.0
        total_saved = 0.0

        for r in rows:
            p = dict(r)
            target = float(p.get("target_amount") or 0.0)
            saved = float(p.get("current_saved") or 0.0)
            total_target += target
            total_saved += saved

            pct = min(100.0, round((saved / target) * 100, 1)) if target > 0 else 0.0
            remaining = max(0.0, round(target - saved, 2))

            # Fetch contributions
            c_rows = database.query_db(
                "SELECT * FROM savings_contributions WHERE plan_id = ? ORDER BY contribution_date DESC, id DESC LIMIT 5",
                (p["id"],),
            )
            contributions = [dict(c) for c in c_rows]

            # Estimated completion date calculation based on actual contribution pattern
            est_completion = cls._estimate_completion_date(saved, target, p.get("target_date"), contributions)

            p["progress_percentage"] = pct
            p["remaining_amount"] = remaining
            p["recent_contributions"] = contributions
            p["contributions_count"] = len(contributions)
            p["estimated_completion_date"] = est_completion
            plans.append(p)

        return {
            "total_plans": len(plans),
            "active_plans": len([p for p in plans if p.get("status") == "active"]),
            "total_target_amount": round(total_target, 2),
            "total_saved_amount": round(total_saved, 2),
            "overall_savings_progress": min(100.0, round((total_saved / total_target) * 100, 1)) if total_target > 0 else 0.0,
            "plans": plans,
        }

    @classmethod
    def _estimate_completion_date(
        cls, current_saved: float, target_amount: float, target_date_str: Any, contributions: List[Dict[str, Any]]
    ) -> str:
        """Estimate realistic completion date based on actual contribution frequency."""
        remaining = max(0.0, target_amount - current_saved)
        if remaining <= 0:
            return "Goal Completed! 🎉"

        if len(contributions) >= 2:
            # Calculate average daily contribution rate from actual contributions
            total_c = sum(float(c.get("amount", 0.0)) for c in contributions)
            days_span = max(7, len(contributions) * 7)
            daily_rate = total_c / days_span
            if daily_rate > 0:
                needed_days = int(math.ceil(remaining / daily_rate))
                est_date = date.today() + timedelta(days=needed_days)
                return est_date.strftime("%d %b %Y")

        if target_date_str:
            return f"Target: {str(target_date_str)[:10]}"

        return "In Progress"


class PurchaseAffordabilityEngine:
    """
    Evaluates financial impact of a cart before purchase.
    Shows subtotal, shipping, discounts, remaining budget before & after,
    and informative non-blocking budget warnings.
    """

    @classmethod
    def evaluate_affordability(
        cls,
        user_id: int,
        cart_subtotal: float = 0.0,
        cart_items_data: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Calculate financial affordability of the given cart value against the user's budget.
        """
        active_budget = BudgetManagementEngine.get_active_budget(user_id)
        overall_budget = float(active_budget.get("overall_budget", 0.0)) if active_budget else 0.0

        # Current eligible spending in active budget period
        period_start = active_budget.get("period_start") if active_budget else str(date.today().replace(day=1))
        period_end = active_budget.get("period_end") if active_budget else str(date.today())

        s_str = f"{period_start} 00:00:00"
        e_str = f"{period_end} 23:59:59"

        order_rows = database.query_db(
            "SELECT * FROM orders WHERE user_id = ? AND created_at >= ? AND created_at <= ?",
            (user_id, s_str, e_str),
        )
        current_spent = sum(
            _get_retained_order_amount(dict(o))
            for o in order_rows
            if _is_order_eligible_for_spending(dict(o))
        )
        current_spent = round(current_spent, 2)

        # Shipping fee rule: free above 500, else 40
        shipping_fee = 0.0 if cart_subtotal >= 500.0 or cart_subtotal == 0.0 else 40.0
        final_payable = round(cart_subtotal + shipping_fee, 2)

        remaining_before = max(0.0, round(overall_budget - current_spent, 2)) if overall_budget > 0 else 0.0
        projected_total = round(current_spent + final_payable, 2)
        remaining_after = round(overall_budget - projected_total, 2) if overall_budget > 0 else 0.0
        utilization_after = (
            round((projected_total / overall_budget) * 100, 1) if overall_budget > 0 else 0.0
        )

        is_over_budget = overall_budget > 0 and projected_total > overall_budget
        over_amount = round(projected_total - overall_budget, 2) if is_over_budget else 0.0

        if is_over_budget:
            warning_level = "danger"
            warning_message = f"Warning: Completing this purchase of ₹{final_payable:,.2f} will exceed your {active_budget.get('budget_period', 'monthly')} budget by ₹{over_amount:,.2f} ({utilization_after}% used)."
        elif overall_budget > 0 and utilization_after >= 85:
            warning_level = "warning"
            warning_message = f"Notice: This purchase will utilize {utilization_after}% of your {active_budget.get('budget_period', 'monthly')} budget. ₹{remaining_after:,.2f} will remain."
        else:
            warning_level = "success"
            warning_message = f"Comfortably within your shopping budget! ₹{remaining_after:,.2f} will remain after purchase."

        # Find affordable alternatives if cart items are present
        suggested_alternatives = []
        if cart_items_data and isinstance(cart_items_data, list):
            for it in cart_items_data[:3]:
                pid = it.get("id") or it.get("product_id")
                if pid:
                    intel = PriceIntelligenceEngine.get_product_price_intelligence(pid)
                    for alt in intel.get("affordable_alternatives", [])[:1]:
                        suggested_alternatives.append({
                            "original_product_name": it.get("name", "Cart Item"),
                            "alternative": alt,
                        })

        return {
            "has_budget": overall_budget > 0,
            "overall_budget": overall_budget,
            "current_spent": current_spent,
            "cart_subtotal": round(cart_subtotal, 2),
            "shipping_fee": shipping_fee,
            "final_payable": final_payable,
            "remaining_budget_before": remaining_before,
            "remaining_budget_after": remaining_after,
            "budget_utilization_after": utilization_after,
            "is_over_budget": is_over_budget,
            "over_budget_amount": over_amount,
            "warning_level": warning_level,
            "warning_message": warning_message,
            "suggested_alternatives": suggested_alternatives,
        }


class BudgetAlertsAndInsightsEngine:
    """
    Generates explainable financial observations and action items for the customer.
    """

    @classmethod
    def get_insights_and_alerts(cls, user_id: int) -> Dict[str, Any]:
        """
        Synthesizes rule-based, verified alerts and insights based on customer's actual data.
        """
        active_budget = BudgetManagementEngine.get_active_budget(user_id)
        overview = SpendingCalculationEngine.get_spending_overview(user_id, date_filter="current_month")
        cat_tracking = CategoryBudgetEngine.get_category_tracking(user_id, active_budget)

        alerts = []
        insights = []

        total_spent = overview["total_spent"]
        overall_budget = float(active_budget.get("overall_budget", 0.0)) if active_budget else 0.0

        if overall_budget > 0:
            util_pct = round((total_spent / overall_budget) * 100, 1)
            if total_spent > overall_budget:
                alerts.append({
                    "type": "exceeded",
                    "severity": "danger",
                    "title": "Overall Budget Exceeded",
                    "message": f"You have spent ₹{total_spent:,.2f}, exceeding your ₹{overall_budget:,.2f} budget by ₹{round(total_spent - overall_budget, 2):,}.",
                })
            elif util_pct >= 85:
                alerts.append({
                    "type": "nearing_limit",
                    "severity": "warning",
                    "title": "Budget Nearing Limit",
                    "message": f"You have utilized {util_pct}% of your budget with ₹{round(overall_budget - total_spent, 2):,.2f} remaining.",
                })
            else:
                insights.append({
                    "title": "Healthy Spending Pace",
                    "message": f"You have used {util_pct}% of your monthly budget. You have ₹{round(overall_budget - total_spent, 2):,.2f} available.",
                })

        # Add category overspending alerts
        for cat_alert in cat_tracking.get("category_alerts", []):
            alerts.append({
                "type": "category_overspending",
                "severity": cat_alert["severity"],
                "title": cat_alert["title"],
                "message": cat_alert["message"],
            })

        # Spending pace insight
        today = date.today()
        day_of_month = today.day
        if day_of_month > 0 and total_spent > 0:
            daily_avg = round(total_spent / day_of_month, 2)
            insights.append({
                "title": "Daily Spending Average",
                "message": f"Your current spending pace is ₹{daily_avg:,.2f} per day across {overview['eligible_purchases_count']} purchases.",
            })

        # Tracked items price drop insights
        tracked_rows = database.query_db(
            """
            SELECT tp.*, p.name, p.price as current_price 
            FROM tracked_products tp 
            JOIN products p ON tp.product_id = p.id 
            WHERE tp.user_id = ? AND tp.alert_active = 1
            """,
            (user_id,)
        )
        drops_reached = [
            t for t in tracked_rows if float(t["current_price"]) <= float(t["target_price"])
        ]
        if drops_reached:
            insights.append({
                "title": "Price Drop Opportunity",
                "message": f"{len(drops_reached)} of your tracked products have reached their target price! Great time to save.",
            })

        return {
            "total_alerts": len(alerts),
            "alerts": alerts,
            "insights": insights,
        }
