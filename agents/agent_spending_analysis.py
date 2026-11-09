"""
agents/agent_spending_analysis.py
---------------------------------
Spending Analysis Agent:
Audits customer financial transactions strictly on eligible completed purchases.
Excludes cancelled, failed, returned, and refunded orders.
Excludes pending COD orders until delivered and payment collected.
Calculates total spend, AOV, category expenditure, monthly trends, and price range.
"""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

import database
from services.purchase_history_service import PurchaseHistoryService

logger = logging.getLogger(__name__)


class SpendingAnalysisAgent:
    """Agent calculating verified financial metrics and price distributions."""

    AGENT_NAME = "SpendingAnalysisAgent"

    def run(self, user_id: int) -> Dict[str, Any]:
        """Compute verified spending metrics for the authenticated customer."""
        eligible_items = PurchaseHistoryService.get_eligible_purchases_for_user(user_id)

        if not eligible_items:
            return {
                "has_spending_history": False,
                "total_spent": 0.0,
                "total_orders": 0,
                "average_order_value": 0.0,
                "spending_tier": "Smart Value",
                "spend_by_category": [],
                "price_range_distribution": {
                    "under_1000": 0,
                    "between_1000_5000": 0,
                    "above_5000": 0,
                },
                "monthly_spending": [],
                "purchase_frequency_days": 30,
                "purchase_cadence_label": "Monthly",
                "message": "No completed orders recorded yet. Make a purchase or complete a delivery to see spending insights.",
            }

        total_spent = 0.0
        unique_orders: set = set()
        category_spend: Dict[str, float] = defaultdict(float)
        category_items: Counter = Counter()
        monthly_spend: Dict[str, float] = defaultdict(float)
        prices: List[float] = []

        under_1000 = 0
        between_1000_5000 = 0
        above_5000 = 0

        for it in eligible_items:
            qty = max(1, int(it.get("quantity") or 1))
            price = float(it.get("price") or 0.0)
            item_total = price * qty
            total_spent += item_total
            prices.append(price)

            ord_id = it.get("order_id") or it.get("order_number") or it.get("id")
            if ord_id:
                unique_orders.add(str(ord_id))

            cat = (it.get("category") or "General").strip()
            category_spend[cat] += item_total
            category_items[cat] += qty

            pdate = str(it.get("purchase_date") or "")[:7]  # YYYY-MM
            month_key = pdate if len(pdate) == 7 else "Recent"
            monthly_spend[month_key] += item_total

            if price < 1000:
                under_1000 += qty
            elif price <= 5000:
                between_1000_5000 += qty
            else:
                above_5000 += qty

        total_orders = max(len(unique_orders), 1)
        aov = round(total_spent / total_orders, 2)

        # Spending Tier
        if aov > 8000:
            spending_tier = "Premium Luxe"
        elif aov > 3000:
            spending_tier = "Balanced Quality"
        else:
            spending_tier = "Smart Value"

        # Category Breakdown
        spend_by_category = []
        for cat, spend in sorted(category_spend.items(), key=lambda x: x[1], reverse=True):
            pct = round((spend / total_spent) * 100, 1) if total_spent > 0 else 0.0
            spend_by_category.append({
                "category": cat,
                "spend": round(spend, 2),
                "items_count": category_items[cat],
                "percentage": pct,
            })

        # Monthly Trends (sorted chronologically)
        monthly_list = [
            {"month": m, "spend": round(s, 2)}
            for m, s in sorted(monthly_spend.items())
        ]

        # Calculate Purchase Cadence
        purchase_dates = sorted([str(it.get("purchase_date") or "")[:10] for it in eligible_items if it.get("purchase_date")])
        frequency_days = 30
        cadence_label = "Monthly"
        if len(purchase_dates) >= 2:
            try:
                date_objs = [datetime.strptime(d, "%Y-%m-%d") for d in purchase_dates]
                intervals = [(date_objs[i] - date_objs[i - 1]).days for i in range(1, len(date_objs))]
                pos_intervals = [i for i in intervals if i > 0]
                if pos_intervals:
                    frequency_days = max(7, round(sum(pos_intervals) / len(pos_intervals)))
                    if frequency_days <= 10:
                        cadence_label = "Weekly"
                    elif frequency_days <= 20:
                        cadence_label = "Bi-weekly"
                    elif frequency_days <= 45:
                        cadence_label = "Monthly"
                    else:
                        cadence_label = "Seasonal / Quarterly"
            except Exception:
                frequency_days = 30

        return {
            "has_spending_history": True,
            "total_spent": round(total_spent, 2),
            "total_orders": total_orders,
            "average_order_value": aov,
            "spending_tier": spending_tier,
            "spend_by_category": spend_by_category,
            "price_range_distribution": {
                "under_1000": under_1000,
                "between_1000_5000": between_1000_5000,
                "above_5000": above_5000,
            },
            "monthly_spending": monthly_list,
            "purchase_frequency_days": frequency_days,
            "purchase_cadence_label": cadence_label,
            "typical_price_min": round(min(prices), 2) if prices else 0.0,
            "typical_price_max": round(max(prices), 2) if prices else 0.0,
        }
