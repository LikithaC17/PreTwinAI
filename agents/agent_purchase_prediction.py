"""
agents/agent_purchase_prediction.py
-----------------------------------
Purchase Prediction Agent:
Estimates which products the user might need again and when, with transparent statistical
evidence and confidence metrics. Forecasts replenishment cycles for repeat purchases and
consumable categories, while strictly preventing fabricated predictions for sparse history
or durable goods.
"""

from __future__ import annotations

import logging
import math
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import database
from config import Config
from services.purchase_history_service import PurchaseHistoryService

logger = logging.getLogger(__name__)

# Standard replenishment baselines (in days) for consumable categories
CONSUMABLE_CATEGORY_CYCLES = {
    "groceries": 21,
    "grocery": 21,
    "food & beverages": 21,
    "coffee & tea": 30,
    "beauty & personal care": 45,
    "beauty": 45,
    "personal care": 45,
    "skincare": 45,
    "health & wellness": 30,
    "health": 30,
    "household essentials": 30,
    "cleaning": 30,
    "baby care": 21,
    "pet supplies": 28,
    "stationery": 60,
}

# Categories strictly recognized as durable goods (non-replenishable in short cycles)
DURABLE_CATEGORIES = {
    "electronics", "smartphones", "mobiles", "laptops", "computers",
    "appliances", "home appliances", "furniture", "televisions", "audio",
    "cameras", "watches", "footwear", "fashion"
}


def _log_agent_run(
    run_id: str,
    agent_name: str,
    user_id: int,
    status: str,
    duration: float,
    summary: str,
    error: str = "",
) -> None:
    try:
        database.execute_db(
            """INSERT INTO agent_runs
               (run_id, agent_name, user_id, status, execution_time_ms,
                output_summary, error_message)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                run_id or "adhoc",
                agent_name,
                user_id or 0,
                status,
                int(duration * 1000),
                summary[:2000],
                error[:1000],
            ),
        )
    except Exception as exc:
        logger.warning("agent_runs insert failed in %s: %s", agent_name, exc)


class PurchasePredictionAgent:
    """Agent that calculates repeat replenishment dates with statistical evidence."""

    AGENT_NAME = "PurchasePredictionAgent"

    def run(
        self,
        user_id: int,
        purchase_summary: Optional[Dict[str, Any]] = None,
        run_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Estimate future replenishment needs based on verified order history.

        Parameters
        ----------
        user_id : int
            The authenticated user's ID.
        purchase_summary : dict, optional
            Pre-computed summary from PurchaseHistoryAgent.
        run_id : str, optional
            UUID for orchestrator tracking.

        Returns
        -------
        dict
            Contains list of predictions with estimated dates, confidence, and evidence.
        """
        t0 = time.time()
        try:
            result = self._predict_replenishments(user_id, purchase_summary)
            duration = time.time() - t0
            _log_agent_run(
                run_id or "",
                self.AGENT_NAME,
                user_id,
                "success",
                duration,
                f"Generated {len(result['predictions'])} replenishment forecasts.",
            )
            return result
        except Exception as exc:
            duration = time.time() - t0
            logger.error("PurchasePredictionAgent failed for user %s: %s", user_id, exc, exc_info=True)
            _log_agent_run(
                run_id or "",
                self.AGENT_NAME,
                user_id,
                "error",
                duration,
                "Purchase Prediction Agent execution failed",
                str(exc),
            )
            return self._empty_predictions(user_id, str(exc))

    def _predict_replenishments(
        self, user_id: int, purchase_summary: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Compute replenishment schedules using empirical intervals and consumable baselines."""
        # 1. Respect user privacy toggle
        if not PurchaseHistoryService.is_twin_history_opted_in(user_id):
            return {
                "user_id": user_id,
                "predictions": [],
                "has_predictions": False,
                "status_message": "Purchase history predictions are paused according to your privacy settings.",
            }

        # 2. Get verified purchases
        purchases = PurchaseHistoryService.get_eligible_purchases_for_user(user_id)
        if not purchases:
            return self._empty_predictions(user_id)

        # 3. Group purchases by product
        product_history: Dict[str, Dict[str, Any]] = {}
        for p in purchases:
            pname = (p.get("product_name") or "").strip()
            if not pname:
                continue

            pdate_str = str(p.get("purchase_date") or "")[:10]
            cat = (p.get("category") or "").strip()
            brand = (p.get("brand") or "").strip()
            price = float(p.get("price") or 0.0)
            pid = p.get("product_id")

            if pname not in product_history:
                product_history[pname] = {
                    "product_name": pname,
                    "product_id": pid,
                    "category": cat,
                    "brand": brand,
                    "price": price,
                    "dates": [],
                }

            if pdate_str:
                try:
                    dt = datetime.strptime(pdate_str, "%Y-%m-%d")
                    product_history[pname]["dates"].append(dt)
                except Exception:
                    pass

        predictions = []
        now = datetime.now()

        for pname, data in product_history.items():
            dates = sorted(list(set(data["dates"])))
            cat_lower = data["category"].lower()

            # Skip durable goods unless they were actually repurchased multiple times
            if len(dates) < 2 and any(d_cat in cat_lower for d_cat in DURABLE_CATEGORIES):
                continue

            # Case A: Repeat Purchases (2 or more distinct purchase dates)
            if len(dates) >= 2:
                intervals = [(dates[i] - dates[i - 1]).days for i in range(1, len(dates))]
                # Filter out same-day duplicates if any
                valid_intervals = [inv for inv in intervals if inv > 0]
                if not valid_intervals:
                    valid_intervals = [CONSUMABLE_CATEGORY_CYCLES.get(cat_lower, 30)]

                mean_interval = sum(valid_intervals) / len(valid_intervals)
                variance = sum((x - mean_interval) ** 2 for x in valid_intervals) / len(valid_intervals)
                std_dev = math.sqrt(variance)

                last_date = dates[-1]
                pred_date = last_date + timedelta(days=int(round(mean_interval)))
                window_start = pred_date - timedelta(days=max(3, int(round(std_dev * 0.5))))
                window_end = pred_date + timedelta(days=max(3, int(round(std_dev * 0.5))))

                # Calculate confidence: more repeat purchases = higher confidence
                rep_count = len(dates)
                if rep_count >= 4 and std_dev < 10:
                    confidence = 0.92
                    confidence_label = "High Confidence"
                elif rep_count >= 3:
                    confidence = 0.82
                    confidence_label = "High Confidence"
                else:
                    confidence = 0.70
                    confidence_label = "Moderate Confidence"

                # Days until replenishment
                days_until = (pred_date - now).days
                is_due_soon = -5 <= days_until <= 10
                is_overdue = days_until < -5

                evidence = (
                    f"Purchased {rep_count} times previously with an average interval of "
                    f"{int(round(mean_interval))} days (last bought on {last_date.strftime('%Y-%m-%d')})."
                )

                predictions.append({
                    "product_name": pname,
                    "product_id": data["product_id"],
                    "category": data["category"],
                    "brand": data["brand"],
                    "price": data["price"],
                    "prediction_type": "repeat_behavior",
                    "purchase_count": rep_count,
                    "average_interval_days": int(round(mean_interval)),
                    "last_purchase_date": last_date.strftime("%Y-%m-%d"),
                    "estimated_replenishment_date": pred_date.strftime("%Y-%m-%d"),
                    "estimated_window_start": window_start.strftime("%Y-%m-%d"),
                    "estimated_window_end": window_end.strftime("%Y-%m-%d"),
                    "days_until_due": days_until,
                    "is_due_soon": is_due_soon,
                    "is_overdue": is_overdue,
                    "confidence": confidence,
                    "confidence_label": confidence_label,
                    "evidence_explanation": evidence,
                })

            # Case B: Consumable single purchase
            elif len(dates) == 1:
                # Check if matches a consumable category cycle
                matched_cycle = None
                for c_name, c_days in CONSUMABLE_CATEGORY_CYCLES.items():
                    if c_name in cat_lower:
                        matched_cycle = c_days
                        break

                if matched_cycle is not None:
                    last_date = dates[0]
                    pred_date = last_date + timedelta(days=matched_cycle)
                    window_start = pred_date - timedelta(days=5)
                    window_end = pred_date + timedelta(days=5)
                    days_until = (pred_date - now).days

                    evidence = (
                        f"Single purchase in consumable category '{data['category']}'. "
                        f"Standard category restocking baseline is ~{matched_cycle} days "
                        f"(purchased on {last_date.strftime('%Y-%m-%d')})."
                    )

                    predictions.append({
                        "product_name": pname,
                        "product_id": data["product_id"],
                        "category": data["category"],
                        "brand": data["brand"],
                        "price": data["price"],
                        "prediction_type": "consumable_baseline",
                        "purchase_count": 1,
                        "average_interval_days": matched_cycle,
                        "last_purchase_date": last_date.strftime("%Y-%m-%d"),
                        "estimated_replenishment_date": pred_date.strftime("%Y-%m-%d"),
                        "estimated_window_start": window_start.strftime("%Y-%m-%d"),
                        "estimated_window_end": window_end.strftime("%Y-%m-%d"),
                        "days_until_due": days_until,
                        "is_due_soon": -5 <= days_until <= 10,
                        "is_overdue": days_until < -5,
                        "confidence": 0.50,
                        "confidence_label": "Baseline Estimate",
                        "evidence_explanation": evidence,
                    })

        # Sort predictions by replenishment urgency (due soonest first)
        predictions.sort(key=lambda x: x["days_until_due"])

        return {
            "user_id": user_id,
            "has_predictions": len(predictions) > 0,
            "predictions_count": len(predictions),
            "predictions": predictions,
            "status_message": (
                f"Generated {len(predictions)} replenishment forecast(s) based on verified purchase cadences."
                if predictions
                else "No repeat replenishment predictions yet. As you make recurring purchases, your Digital Twin will forecast restocking schedules."
            ),
        }

    def _empty_predictions(self, user_id: int, error: str = "") -> Dict[str, Any]:
        """Zero-state representation when no repeat predictions exist."""
        return {
            "user_id": user_id,
            "has_predictions": False,
            "predictions_count": 0,
            "predictions": [],
            "status_message": (
                "No purchase predictions available yet. As you complete repeat orders on PreTwin AI, "
                "your Digital Twin will forecast when you need restocking."
            ),
            "error": error if error else None,
        }
