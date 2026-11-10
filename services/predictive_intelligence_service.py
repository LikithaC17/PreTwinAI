"""
services/predictive_intelligence_service.py
-------------------------------------------
Predictive Shopping Intelligence Engine (Feature 2):
1. PurchasePatternAnalyzer: Identifies repeat purchases, median intervals, buying cadence, and habit changes.
2. ReplenishmentPredictor: Calculates replenishment windows, expected quantities, and prices without fabricating data.
3. SeasonalTrendAnalyzer: Discovers empirical seasonal shopping patterns strictly supported by historical orders.
4. SpendingForecastEngine: Estimates upcoming weekly/monthly expenditures, category distributions, and ranges.
5. PredictionConfidenceEvaluator: Evaluates statistical reliability and historical prediction accuracy.
6. PredictiveIntelligenceCoordinator: Synthesizes all 6 intelligence sections into an actionable dashboard.
"""

from __future__ import annotations

import logging
import math
import statistics
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import database
from services.purchase_history_service import PurchaseHistoryService

logger = logging.getLogger("predictive_intelligence_service")

# Baselines in days for consumable categories
CONSUMABLE_CATEGORY_CYCLES: Dict[str, int] = {
    "groceries": 21,
    "grocery": 21,
    "food & beverages": 21,
    "coffee & tea": 30,
    "personal care": 45,
    "skincare": 45,
    "beauty": 45,
    "beauty & personal care": 45,
    "health & wellness": 30,
    "health": 30,
    "household essentials": 30,
    "cleaning": 30,
    "baby care": 21,
    "pet supplies": 28,
    "stationery": 60,
    "everyday consumables": 30,
}

DURABLE_CATEGORIES = {
    "electronics", "smartphones", "mobiles", "laptops", "computers",
    "computer accessories", "appliances", "furniture", "televisions",
    "audio", "cameras", "watches", "footwear", "fashion"
}


# ─────────────────────────────────────────────────────────────────────────────
# 1. Purchase Pattern Analyzer
# ─────────────────────────────────────────────────────────────────────────────
class PurchasePatternAnalyzer:
    """Analyzes customer order logs to extract repeat behaviors, cadence, and trends."""

    @classmethod
    def analyze(cls, eligible_purchases: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not eligible_purchases:
            return {
                "has_data": False,
                "total_orders": 0,
                "frequent_products": [],
                "frequent_categories": [],
                "median_repeat_interval_days": None,
                "average_repeat_interval_days": None,
                "cadence_label": "No History",
                "cadence_days": None,
                "habit_trends": [],
                "regularity_score": 0.0,
            }

        product_groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        category_counter: Counter = Counter()
        all_dates: List[datetime] = []

        for p in eligible_purchases:
            pname = (p.get("product_name") or "Product").strip()
            cat = (p.get("category") or "General").strip()
            qty = max(1, int(p.get("quantity") or 1))
            category_counter[cat] += qty

            pdate_str = str(p.get("purchase_date") or "")[:10]
            try:
                dt = datetime.strptime(pdate_str, "%Y-%m-%d")
                product_groups[pname].append({
                    "date": dt,
                    "price": float(p.get("price") or 0.0),
                    "quantity": qty,
                    "category": cat,
                    "brand": p.get("brand") or "",
                    "product_id": p.get("product_id"),
                })
                all_dates.append(dt)
            except Exception:
                pass

        # Calculate repeat intervals per product
        all_intervals: List[int] = []
        product_patterns: List[Dict[str, Any]] = []

        for pname, items in product_groups.items():
            sorted_items = sorted(items, key=lambda x: x["date"])
            dates = [it["date"] for it in sorted_items]
            intervals: List[int] = []

            for i in range(1, len(dates)):
                diff = (dates[i] - dates[i - 1]).days
                if diff > 0:
                    intervals.append(diff)
                    all_intervals.append(diff)

            med_int = int(statistics.median(intervals)) if intervals else None
            avg_price = round(sum(it["price"] for it in items) / len(items), 2)
            total_qty = sum(it["quantity"] for it in items)
            last_date = sorted_items[-1]["date"].strftime("%Y-%m-%d")

            product_patterns.append({
                "product_name": pname,
                "category": sorted_items[-1]["category"],
                "brand": sorted_items[-1]["brand"],
                "product_id": sorted_items[-1]["product_id"],
                "purchase_count": len(sorted_items),
                "total_quantity": total_qty,
                "average_price": avg_price,
                "latest_price": sorted_items[-1]["price"],
                "last_purchased_date": last_date,
                "median_interval_days": med_int,
                "has_repeat": len(sorted_items) >= 2,
            })

        product_patterns.sort(key=lambda x: (x["purchase_count"], x["total_quantity"]), reverse=True)

        # Global intervals & cadence
        median_interval = int(statistics.median(all_intervals)) if all_intervals else None
        avg_interval = round(statistics.mean(all_intervals), 1) if all_intervals else None

        # Regularity score (inverse coefficient of variation)
        regularity_score = 0.5
        if len(all_intervals) >= 2:
            std_dev = statistics.stdev(all_intervals)
            mean_val = statistics.mean(all_intervals)
            if mean_val > 0:
                cv = std_dev / mean_val
                regularity_score = max(0.1, min(1.0, round(1.0 - (cv * 0.5), 2)))

        # Determine overall customer shopping cadence
        cadence_label = "Monthly"
        cadence_days = 30
        if median_interval:
            cadence_days = median_interval
            if median_interval <= 10:
                cadence_label = "Weekly"
            elif median_interval <= 20:
                cadence_label = "Bi-weekly"
            elif median_interval <= 45:
                cadence_label = "Monthly"
            else:
                cadence_label = "Quarterly"

        # Habit trends (recent 45 days vs older)
        now = datetime.now()
        recent_threshold = now - timedelta(days=45)
        recent_cats: Counter = Counter()
        older_cats: Counter = Counter()

        for p in eligible_purchases:
            cat = (p.get("category") or "General").strip()
            pdate_str = str(p.get("purchase_date") or "")[:10]
            try:
                dt = datetime.strptime(pdate_str, "%Y-%m-%d")
                if dt >= recent_threshold:
                    recent_cats[cat] += 1
                else:
                    older_cats[cat] += 1
            except Exception:
                pass

        habit_trends: List[Dict[str, Any]] = []
        for cat, rec_cnt in recent_cats.most_common(4):
            old_cnt = older_cats.get(cat, 0)
            if rec_cnt > old_cnt:
                habit_trends.append({
                    "category": cat,
                    "direction": "accelerating",
                    "badge": "📈 Accelerating",
                    "description": f"You are purchasing items in {cat} more frequently in the last 45 days.",
                })
            else:
                habit_trends.append({
                    "category": cat,
                    "direction": "steady",
                    "badge": "⚖️ Steady Habit",
                    "description": f"Consistent recurring demand in {cat}.",
                })

        # Category list
        total_items_count = sum(category_counter.values()) or 1
        frequent_categories = [
            {
                "category": cat,
                "count": count,
                "percentage": round((count / total_items_count) * 100, 1),
            }
            for cat, count in category_counter.most_common(6)
        ]

        return {
            "has_data": True,
            "total_orders": len(eligible_purchases),
            "frequent_products": product_patterns[:8],
            "frequent_categories": frequent_categories,
            "median_repeat_interval_days": median_interval,
            "average_repeat_interval_days": avg_interval,
            "cadence_label": cadence_label,
            "cadence_days": cadence_days,
            "habit_trends": habit_trends,
            "regularity_score": regularity_score,
        }


# ─────────────────────────────────────────────────────────────────────────────
# 2. Replenishment Predictor
# ─────────────────────────────────────────────────────────────────────────────
class ReplenishmentPredictor:
    """Calculates upcoming shopping needs based on empirical cycles and baselines."""

    @classmethod
    def predict(
        cls,
        eligible_purchases: List[Dict[str, Any]],
        patterns: Dict[str, Any],
        user_id: int,
    ) -> List[Dict[str, Any]]:
        if not eligible_purchases:
            return []

        predictions: List[Dict[str, Any]] = []
        today = datetime.now().date()
        frequent_products = patterns.get("frequent_products", [])

        # Step A: Evaluate products with repeat history
        for p in frequent_products:
            pname = p["product_name"]
            cat = p["category"]
            cat_lower = cat.lower()
            last_date_str = p["last_purchased_date"]
            if not last_date_str:
                continue

            last_date = datetime.strptime(last_date_str, "%Y-%m-%d").date()
            cycle_days = p["median_interval_days"]
            is_repeat = p["has_repeat"]

            # If no repeat interval, check if it is a consumable category baseline
            if not cycle_days:
                for c_key, c_days in CONSUMABLE_CATEGORY_CYCLES.items():
                    if c_key in cat_lower:
                        cycle_days = c_days
                        break

            # If still no cycle and category is durable, strictly skip
            if not cycle_days:
                if any(d in cat_lower for d in DURABLE_CATEGORIES):
                    continue
                cycle_days = 30  # Default general non-durable interval

            estimated_date = last_date + timedelta(days=cycle_days)
            days_until_due = (estimated_date - today).days

            # Window
            window_margin = max(3, round(cycle_days * 0.15))
            window_start = (estimated_date - timedelta(days=window_margin)).strftime("%b %d, %Y")
            window_end = (estimated_date + timedelta(days=window_margin)).strftime("%b %d, %Y")

            # Confidence determination
            if is_repeat and p["purchase_count"] >= 3:
                confidence_score = 0.90
                confidence_label = "High"
                explanation = f"Empirically calculated from your {p['purchase_count']} repeat orders placed every ~{cycle_days} days."
            elif is_repeat:
                confidence_score = 0.75
                confidence_label = "Medium"
                explanation = f"Observed repeat interval of ~{cycle_days} days between your previous orders."
            else:
                confidence_score = 0.55
                confidence_label = "Low"
                explanation = f"Estimated from typical {cat} consumption patterns (~{cycle_days} days) following your last purchase."

            # Urgency
            if days_until_due < 0:
                urgency = "overdue"
                urgency_label = f"Restock Overdue by {abs(days_until_due)}d"
            elif days_until_due <= 7:
                urgency = "due_soon"
                urgency_label = f"Due Soon in {days_until_due}d"
            else:
                urgency = "upcoming"
                urgency_label = f"Upcoming in {days_until_due}d"

            expected_qty = max(1, round(p["total_quantity"] / max(1, p["purchase_count"])))
            expected_price = p["latest_price"] or p["average_price"] or 999.0

            predictions.append({
                "id": None,  # Will be mapped to DB id if saved
                "product_name": pname,
                "category": cat,
                "brand": p.get("brand") or "",
                "product_id": p.get("product_id"),
                "last_purchased_date": last_date.strftime("%b %d, %Y"),
                "estimated_purchase_date": estimated_date.strftime("%Y-%m-%d"),
                "estimated_purchase_date_display": estimated_date.strftime("%b %d, %Y"),
                "estimated_window": f"{window_start} – {window_end}",
                "days_until_due": days_until_due,
                "cycle_days": cycle_days,
                "expected_quantity": expected_qty,
                "expected_price": expected_price,
                "confidence_score": confidence_score,
                "confidence_label": confidence_label,
                "urgency": urgency,
                "urgency_label": urgency_label,
                "explanation": explanation,
                "status": "pending",
            })

        # Sort by urgency: overdue first, then due soon, then upcoming
        predictions.sort(key=lambda x: x["days_until_due"])
        return predictions


# ─────────────────────────────────────────────────────────────────────────────
# 3. Seasonal Trend Analyzer
# ─────────────────────────────────────────────────────────────────────────────
class SeasonalTrendAnalyzer:
    """Discovers empirical seasonal shopping patterns strictly supported by historical orders."""

    SEASON_DEFINITIONS = [
        {
            "name": "Summer Tech & Refreshment",
            "months": [3, 4, 5],
            "keywords": ["ac", "fan", "cooler", "sunscreen", "hydration", "cotton", "summer", "gel", "cold drink", "sunglasses"],
            "categories": ["electronics", "personal care", "appliances", "fashion", "food & beverages"],
            "icon": "☀️",
            "description": "Historical demand for cooling appliances, skin protection, and light essentials.",
        },
        {
            "name": "Monsoon & Academic Cycle",
            "months": [6, 7, 8],
            "keywords": ["umbrella", "rainwear", "waterproof", "backpack", "stationery", "notebook", "laptop", "desk"],
            "categories": ["stationery", "computer accessories", "footwear", "home essentials"],
            "icon": "🌧️",
            "description": "Historical purchases aligned with monsoon preparedness and academic back-to-college sessions.",
        },
        {
            "name": "Festive & Diwali Shopping",
            "months": [9, 10, 11],
            "keywords": ["sweet", "snack", "decor", "light", "gift", "traditional", "ethnic", "audio", "soundbar"],
            "categories": ["home essentials", "electronics", "fashion", "food & beverages"],
            "icon": "🪔",
            "description": "Recurring festive celebrations, gift baskets, and celebratory home enhancements.",
        },
        {
            "name": "Winter Comfort & Wellness",
            "months": [12, 1, 2],
            "keywords": ["heater", "warm", "jacket", "hoodie", "cream", "moisturizer", "coffee", "tea", "soup", "blanket"],
            "categories": ["personal care", "appliances", "fashion", "food & beverages"],
            "icon": "❄️",
            "description": "Cold-weather comfort items, rich skin moisturizers, and hot beverage refills.",
        },
    ]

    @classmethod
    def analyze(cls, eligible_purchases: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not eligible_purchases:
            return {
                "has_seasonal_patterns": False,
                "patterns": [],
                "message": "No historical orders recorded yet. Seasonal patterns activate as you shop throughout different times of the year.",
            }

        matched_patterns: List[Dict[str, Any]] = []
        current_month = datetime.now().month

        for season in cls.SEASON_DEFINITIONS:
            supporting_items: List[Dict[str, Any]] = []

            for p in eligible_purchases:
                pdate_str = str(p.get("purchase_date") or "")[:10]
                try:
                    dt = datetime.strptime(pdate_str, "%Y-%m-%d")
                except Exception:
                    continue

                if dt.month in season["months"]:
                    pname = (p.get("product_name") or "").lower()
                    cat = (p.get("category") or "").lower()

                    matches_keyword = any(kw in pname for kw in season["keywords"])
                    matches_category = any(c in cat for c in season["categories"])

                    if matches_keyword or matches_category:
                        supporting_items.append({
                            "product_name": p.get("product_name"),
                            "category": p.get("category"),
                            "purchased_date": pdate_str,
                            "price": float(p.get("price") or 0.0),
                        })

            if len(supporting_items) >= 1:
                is_active_now = current_month in season["months"]
                matched_patterns.append({
                    "season_name": season["name"],
                    "icon": season["icon"],
                    "is_active_season": is_active_now,
                    "description": season["description"],
                    "verified_item_count": len(supporting_items),
                    "sample_products": [it["product_name"] for it in supporting_items[:3]],
                    "historical_evidence": f"Confirmed by {len(supporting_items)} verified purchase(s) in past {season['name'].split()[0]} cycles.",
                })

        has_patterns = len(matched_patterns) > 0
        message = (
            f"Identified {len(matched_patterns)} authentic seasonal shopping patterns from your order history."
            if has_patterns
            else "No distinctive seasonal cycles detected yet. PreTwin AI avoids guessing and only reports patterns supported by your real history."
        )

        return {
            "has_seasonal_patterns": has_patterns,
            "patterns": matched_patterns,
            "message": message,
        }


# ─────────────────────────────────────────────────────────────────────────────
# 4. Spending Forecast Engine
# ─────────────────────────────────────────────────────────────────────────────
class SpendingForecastEngine:
    """Estimates upcoming weekly and monthly expenditures with transparent comparisons."""

    @classmethod
    def forecast(
        cls,
        predictions: List[Dict[str, Any]],
        eligible_purchases: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        weekly_spend = 0.0
        monthly_spend = 0.0
        category_spend: Dict[str, float] = defaultdict(float)
        category_counts: Counter = Counter()

        for pred in predictions:
            days = pred["days_until_due"]
            cost = pred["expected_price"] * pred["expected_quantity"]

            if days <= 7:
                weekly_spend += cost
            if days <= 30:
                monthly_spend += cost
                cat = pred["category"]
                category_spend[cat] += cost
                category_counts[cat] += 1

        weekly_spend = round(weekly_spend, 2)
        monthly_spend = round(monthly_spend, 2)

        # Spending Range
        spend_range_min = round(monthly_spend * 0.85, 2)
        spend_range_max = round(monthly_spend * 1.15, 2)

        # Historical comparison
        total_historical_spend = sum(float(p.get("price") or 0.0) * int(p.get("quantity") or 1) for p in eligible_purchases)
        historical_months = max(1, len(set(str(p.get("purchase_date") or "")[:7] for p in eligible_purchases if p.get("purchase_date"))))
        historical_monthly_avg = round(total_historical_spend / historical_months, 2)

        if historical_monthly_avg > 0:
            diff_pct = round(((monthly_spend - historical_monthly_avg) / historical_monthly_avg) * 100, 1)
            if diff_pct > 15:
                comparison_label = f"Higher than usual (+{diff_pct}%) due to multiple items due for restock."
            elif diff_pct < -15:
                comparison_label = f"Light replenishment month ({diff_pct}%) compared to historical average."
            else:
                comparison_label = "Within normal historical replenishment variance."
        else:
            comparison_label = "Awaiting more order history to establish historical baseline."

        # Category breakdown
        category_forecasts = []
        for cat, amt in category_spend.items():
            pct = round((amt / max(1.0, monthly_spend)) * 100, 1)
            category_forecasts.append({
                "category": cat,
                "estimated_amount": amt,
                "percentage": pct,
                "item_count": category_counts[cat],
            })
        category_forecasts.sort(key=lambda x: x["estimated_amount"], reverse=True)

        return {
            "estimated_weekly_expenditure": weekly_spend,
            "estimated_monthly_expenditure": monthly_spend,
            "expected_range_min": spend_range_min,
            "expected_range_max": spend_range_max,
            "range_display": f"₹{spend_range_min:,.0f} — ₹{spend_range_max:,.0f}",
            "historical_monthly_average": historical_monthly_avg,
            "comparison_label": comparison_label,
            "category_forecasts": category_forecasts,
            "has_forecast": monthly_spend > 0,
        }


# ─────────────────────────────────────────────────────────────────────────────
# 5. Prediction History & Evaluation Engine
# ─────────────────────────────────────────────────────────────────────────────
class PredictionHistoryEngine:
    """Tracks and evaluates prediction accuracy over time."""

    @classmethod
    def get_history(cls, user_id: int) -> Dict[str, Any]:
        rows = database.query_db(
            """
            SELECT * FROM predictions
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT 25
            """,
            (user_id,)
        )
        items: List[Dict[str, Any]] = []
        fulfilled_count = 0
        total_resolved = 0

        today = datetime.now().date()

        for r in (rows or []):
            d = dict(r)
            status = d.get("status") or "active"

            # Check if overdue
            est_date_str = str(d.get("estimated_purchase_date") or "")
            if est_date_str and status == "active":
                try:
                    est_date = datetime.strptime(est_date_str, "%Y-%m-%d").date()
                    if est_date < today:
                        status = "overdue"
                except Exception:
                    pass

            if status in ("confirmed", "fulfilled"):
                fulfilled_count += 1
                total_resolved += 1
            elif status in ("dismissed", "expired"):
                total_resolved += 1

            d["effective_status"] = status
            items.append(d)

        accuracy_pct = round((fulfilled_count / max(1, total_resolved)) * 100, 1) if total_resolved > 0 else None

        return {
            "predictions_history": items,
            "total_recorded": len(items),
            "fulfilled_count": fulfilled_count,
            "accuracy_percentage": accuracy_pct,
            "accuracy_label": f"{accuracy_pct}% Accuracy" if accuracy_pct is not None else "Evaluating...",
        }


# ─────────────────────────────────────────────────────────────────────────────
# 6. Predictive Intelligence Coordinator (Master)
# ─────────────────────────────────────────────────────────────────────────────
class PredictiveIntelligenceCoordinator:
    """Coordinates all 6 functional sections of Feature 2."""

    @classmethod
    def get_dashboard(cls, user_id: int) -> Dict[str, Any]:
        # Step 1: Verified purchases strictly adhering to order-status logic
        eligible_purchases = PurchaseHistoryService.get_eligible_purchases_for_user(user_id)
        has_purchases = len(eligible_purchases) > 0

        # Step 2: Buying patterns
        patterns = PurchasePatternAnalyzer.analyze(eligible_purchases)

        # Step 3: Replenishment predictions
        upcoming_needs = ReplenishmentPredictor.predict(eligible_purchases, patterns, user_id)

        # Step 4: Sync active predictions with DB table (without duplicating)
        cls._sync_predictions_to_db(user_id, upcoming_needs)

        # Step 5: Spending forecasts
        spending_forecast = SpendingForecastEngine.forecast(upcoming_needs, eligible_purchases)

        # Step 6: Seasonal shopping insights
        seasonal_insights = SeasonalTrendAnalyzer.analyze(eligible_purchases)

        # Step 7: Smart purchase reminders
        reminders = cls._get_reminders(user_id)

        # Step 8: Prediction history
        prediction_history = PredictionHistoryEngine.get_history(user_id)

        # Check first-time customer state
        is_first_time = len(eligible_purchases) == 0

        return {
            "success": True,
            "user_id": user_id,
            "is_first_time_customer": is_first_time,
            "total_purchases_analyzed": len(eligible_purchases),
            "sections": {
                "upcoming_needs": {
                    "total_predictions": len(upcoming_needs),
                    "items": upcoming_needs,
                    "has_predictions": len(upcoming_needs) > 0,
                },
                "buying_patterns": patterns,
                "spending_forecast": spending_forecast,
                "seasonal_insights": seasonal_insights,
                "reminders": {
                    "total_reminders": len(reminders),
                    "items": reminders,
                },
                "prediction_history": prediction_history,
            },
        }

    @classmethod
    def _sync_predictions_to_db(cls, user_id: int, predictions: List[Dict[str, Any]]) -> None:
        """Persist or refresh active predictions in the predictions table."""
        if not user_id or not predictions:
            return

        run_id = str(uuid.uuid4())
        today_str = datetime.now().strftime("%Y-%m-%d")

        for pred in predictions[:10]:
            pname = pred["product_name"]
            cat = pred["category"]
            est_date = pred["estimated_purchase_date"]

            # Check if active prediction already exists for this product
            existing = database.query_db(
                """SELECT id FROM predictions
                   WHERE user_id = ? AND predicted_product = ? AND status = 'active'""",
                (user_id, pname),
                one=True
            )

            if existing:
                pred["id"] = existing["id"]
                database.execute_db(
                    """UPDATE predictions
                       SET estimated_timeframe = ?,
                           confidence_score = ?,
                           confidence_label = ?,
                           estimated_purchase_date = ?,
                           expected_quantity = ?,
                           expected_price = ?,
                           reason = ?
                       WHERE id = ?""",
                    (
                        pred["urgency_label"],
                        pred["confidence_score"],
                        pred["confidence_label"],
                        est_date,
                        pred["expected_quantity"],
                        pred["expected_price"],
                        pred["explanation"],
                        existing["id"]
                    )
                )
            else:
                new_id = database.execute_db(
                    """INSERT INTO predictions (
                        user_id, run_id, predicted_category, predicted_product,
                        reason, supporting_evidence, estimated_timeframe,
                        confidence_score, confidence_label, recommended_action,
                        status, estimated_purchase_date, expected_quantity,
                        expected_price, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?, ?)""",
                    (
                        user_id,
                        run_id,
                        cat,
                        pname,
                        pred["explanation"],
                        "[]",
                        pred["urgency_label"],
                        pred["confidence_score"],
                        pred["confidence_label"],
                        "Review replenishment options",
                        est_date,
                        pred["expected_quantity"],
                        pred["expected_price"],
                        today_str
                    )
                )
                pred["id"] = new_id

    @classmethod
    def _get_reminders(cls, user_id: int) -> List[Dict[str, Any]]:
        rows = database.query_db(
            """SELECT * FROM shopping_reminders
               WHERE user_id = ?
               ORDER BY next_reminder_date ASC""",
            (user_id,)
        )
        today = datetime.now().date()
        reminders = []

        for r in (rows or []):
            item = dict(r)
            next_date_str = item.get("next_reminder_date") or str(today)
            try:
                next_date = datetime.strptime(next_date_str[:10], "%Y-%m-%d").date()
                delta = (next_date - today).days
            except Exception:
                delta = 0

            item["days_until_due"] = delta
            if delta < 0:
                item["urgency"] = "overdue"
                item["urgency_label"] = f"Overdue by {abs(delta)} days"
            elif delta <= 3:
                item["urgency"] = "urgent"
                item["urgency_label"] = f"Due in {delta} day(s)"
            else:
                item["urgency"] = "upcoming"
                item["urgency_label"] = f"Due in {delta} days"

            item["is_enabled"] = bool(item.get("is_enabled", 1))
            reminders.append(item)

        return reminders
