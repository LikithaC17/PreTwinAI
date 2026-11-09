"""
agents/agent_future_needs.py
----------------------------
Future Needs Analysis Agent:
Estimates realistic replenishment needs and intervals for consumable products.
Provides empirical explanations, estimated time windows, and confidence ratings.
Transparently communicates insufficient data when purchase history is sparse.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import database
from services.purchase_history_service import PurchaseHistoryService

logger = logging.getLogger(__name__)

# Standard replenishment baselines (in days) for consumable categories
CONSUMABLE_CYCLES = {
    "grocery": 21,
    "groceries": 21,
    "food & grocery": 21,
    "food": 21,
    "beauty": 45,
    "personal care": 45,
    "skincare": 45,
    "health": 30,
    "health & wellness": 30,
    "household essentials": 30,
    "coffee & tea": 30,
    "cleaning supplies": 30,
    "baby care": 21,
    "stationery": 60,
}

DURABLE_CATEGORIES = {
    "electronics", "smartphones", "mobiles", "laptops", "computers",
    "appliances", "furniture", "televisions", "audio", "cameras",
    "watches", "footwear", "two wheelers"
}


class FutureNeedsAgent:
    """Agent predicting future consumable restocking needs without fabrication."""

    AGENT_NAME = "FutureNeedsAgent"

    def run(self, user_id: int) -> Dict[str, Any]:
        """Generate explainable future shopping forecasts."""
        eligible_items = PurchaseHistoryService.get_eligible_purchases_for_user(user_id)

        if not eligible_items:
            return {
                "has_forecasts": False,
                "needs": [],
                "status": "insufficient_data",
                "message": (
                    "No repeat consumable purchases recorded yet. "
                    "As you order everyday consumables like skincare, groceries, or wellness items, "
                    "your twin will automatically project restocking cycles."
                ),
            }

        # Group purchases by product name and category
        product_history: Dict[str, List[dict]] = defaultdict(list)
        for it in eligible_items:
            pname = (it.get("product_name") or "").strip()
            cat = (it.get("category") or "").strip().lower()

            # Skip durable products from recurring consumable forecasts
            if any(d in cat for d in DURABLE_CATEGORIES):
                continue

            product_history[pname].append(it)

        forecasts: List[Dict[str, Any]] = []
        today = datetime.now(timezone.utc).date()

        for pname, items in product_history.items():
            cat = items[0].get("category") or "Consumables"
            cat_lower = cat.lower()

            # Sort items by purchase date
            dates = []
            for item in items:
                d_str = str(item.get("purchase_date") or "")[:10]
                try:
                    dates.append(datetime.strptime(d_str, "%Y-%m-%d").date())
                except Exception:
                    pass
            dates.sort()

            if not dates:
                continue

            last_date = dates[-1]

            # Case A: User has bought this exact consumable 2 or more times
            if len(dates) >= 2:
                intervals = [(dates[i] - dates[i - 1]).days for i in range(1, len(dates))]
                pos_intervals = [i for i in intervals if i > 0]
                avg_interval = round(sum(pos_intervals) / len(pos_intervals)) if pos_intervals else 30
                confidence = min(95, 65 + (len(dates) * 8))
                confidence_label = "High Confidence" if confidence >= 80 else "Moderate Confidence"
                source = "Verified Repeat Purchase Cadence"
                explanation = (
                    f"You have purchased this item {len(dates)} times with an average repeat interval "
                    f"of ~{avg_interval} days."
                )
            else:
                # Case B: Single purchase in known consumable category
                matched_cycle = None
                for key, cycle_days in CONSUMABLE_CYCLES.items():
                    if key in cat_lower or key in pname.lower():
                        matched_cycle = cycle_days
                        break
                if not matched_cycle:
                    continue  # Do not invent forecasts for unclassified one-offs

                avg_interval = matched_cycle
                confidence = 65
                confidence_label = "Standard Category Cadence"
                source = f"Industry Baseline for {cat}"
                explanation = (
                    f"Based on typical consumption intervals for {cat} (~{avg_interval} days) "
                    f"following your purchase on {last_date.strftime('%d %b %Y')}."
                )

            # Estimated replenishment window
            est_target = last_date + timedelta(days=avg_interval)
            window_start = est_target - timedelta(days=5)
            window_end = est_target + timedelta(days=5)

            days_remaining = (est_target - today).days

            if days_remaining < 0:
                timing_desc = f"May need review (approx. {abs(days_remaining)} days past usual interval)"
                urgency = "Due for Review"
            elif days_remaining <= 7:
                timing_desc = f"Likely within the next {days_remaining}–{days_remaining + 5} days"
                urgency = "Soon"
            else:
                timing_desc = f"Estimated in ~{days_remaining} days ({window_start.strftime('%b %d')} – {window_end.strftime('%b %d')})"
                urgency = "Upcoming"

            forecasts.append({
                "product_name": pname,
                "category": cat,
                "product_id": items[0].get("product_id"),
                "estimated_window": f"{window_start.strftime('%d %b')} – {window_end.strftime('%d %b %Y')}",
                "timing_description": timing_desc,
                "urgency": urgency,
                "average_interval_days": avg_interval,
                "confidence_score": confidence,
                "confidence_label": confidence_label,
                "source": source,
                "explanation": explanation,
                "last_purchased": last_date.strftime("%d %b %Y"),
            })

        forecasts.sort(key=lambda x: (x["urgency"] != "Due for Review", x["urgency"] != "Soon"))

        return {
            "has_forecasts": len(forecasts) > 0,
            "needs": forecasts[:6],
            "status": "active" if forecasts else "insufficient_data",
            "message": (
                f"Identified {len(forecasts)} upcoming consumable replenishment requirements."
                if forecasts else
                "No active consumable replenishment needs detected. Predictions activate automatically as consumables are ordered."
            ),
        }
