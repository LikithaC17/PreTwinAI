"""
agents/agent_recommendation_coordinator.py
-----------------------------------------
Recommendation Coordinator Agent:
Synthesizes inputs from the Purchase History Agent, Preference Learning Agent,
Purchase Prediction Agent, Discovery Agent, and Budget Intelligence Agent to deliver
ranked, explainable recommendations. Respects recommendation dismissals and user privacy.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional, Set

import database
from config import Config
from services.purchase_history_service import PurchaseHistoryService
from agents.agent_purchase_history import PurchaseHistoryAgent
from agents.agent_preference_learning import PreferenceLearningAgent
from agents.agent_purchase_prediction import PurchasePredictionAgent

logger = logging.getLogger(__name__)


def _safe_json(val: Any, default=None):
    if val is None:
        return default if default is not None else []
    if isinstance(val, (list, dict)):
        return val
    try:
        return json.loads(val)
    except Exception:
        return default if default is not None else []


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


class RecommendationCoordinatorAgent:
    """Master Coordinator that fuses multi-agent insights into actionable shopping recommendations."""

    AGENT_NAME = "RecommendationCoordinatorAgent"

    def __init__(self):
        self.history_agent = PurchaseHistoryAgent()
        self.learning_agent = PreferenceLearningAgent()
        self.prediction_agent = PurchasePredictionAgent()

    def run(self, user_id: int, run_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute full coordination pipeline for the given user.

        Parameters
        ----------
        user_id : int
            The authenticated user's ID.
        run_id : str, optional
            UUID for trace tracking.

        Returns
        -------
        dict
            Synthesized insights, replenishment alerts, and ranked personalized recommendations.
        """
        t0 = time.time()
        try:
            # 1. Fetch dismissed recommendation IDs
            dismissed_ids = self._get_dismissed_ids(user_id)

            # 2. Run modular sub-agents
            history_summary = self.history_agent.run(user_id, run_id)
            learned_profile = self.learning_agent.run(user_id, history_summary, run_id)
            prediction_summary = self.prediction_agent.run(user_id, history_summary, run_id)

            # 3. Assemble and rank candidates from authorized catalog
            recommendations = self._assemble_recommendations(
                user_id=user_id,
                history_summary=history_summary,
                learned_profile=learned_profile,
                prediction_summary=prediction_summary,
                dismissed_ids=dismissed_ids,
            )

            duration = time.time() - t0
            _log_agent_run(
                run_id or "",
                self.AGENT_NAME,
                user_id,
                "success",
                duration,
                f"Generated {len(recommendations)} coordinated recommendations.",
            )

            return {
                "user_id": user_id,
                "history_summary": history_summary,
                "learned_profile": learned_profile,
                "predictions": prediction_summary.get("predictions", []),
                "recommendations": recommendations,
                "recommendation_count": len(recommendations),
                "dismissed_count": len(dismissed_ids),
                "status": "success",
            }

        except Exception as exc:
            duration = time.time() - t0
            logger.error("RecommendationCoordinatorAgent failed for user %s: %s", user_id, exc, exc_info=True)
            _log_agent_run(
                run_id or "",
                self.AGENT_NAME,
                user_id,
                "error",
                duration,
                "Recommendation Coordinator Agent failed",
                str(exc),
            )
            return {
                "user_id": user_id,
                "history_summary": self.history_agent._empty_summary(user_id),
                "learned_profile": self.learning_agent._fallback_profile(user_id, str(exc)),
                "predictions": [],
                "recommendations": [],
                "recommendation_count": 0,
                "dismissed_count": 0,
                "status": "error",
                "error": str(exc),
            }

    def _assemble_recommendations(
        self,
        user_id: int,
        history_summary: Dict[str, Any],
        learned_profile: Dict[str, Any],
        prediction_summary: Dict[str, Any],
        dismissed_ids: Set[int],
    ) -> List[Dict[str, Any]]:
        """Combine replenishment needs and high-affinity catalog discoveries into ranked recommendations."""
        recommended: List[Dict[str, Any]] = []
        seen_product_ids: Set[int] = set()

        # ── 1. Priority 1: Predicted Replenishment Needs ─────────────────────────
        predictions = prediction_summary.get("predictions", [])
        for pred in predictions:
            pid = pred.get("product_id")
            pname = pred.get("product_name")

            # Look up catalog product
            cat_item = None
            if pid:
                cat_item = database.query_db("SELECT * FROM products WHERE id = ?", (pid,), one=True)
            if not cat_item and pname:
                cat_item = database.query_db(
                    "SELECT * FROM products WHERE LOWER(name) LIKE ? ORDER BY rating DESC",
                    (f"%{pname.lower()}%",),
                    one=True,
                )

            if cat_item:
                p_dict = dict(cat_item)
                p_id = p_dict["id"]
                if p_id in dismissed_ids or p_id in seen_product_ids:
                    continue

                seen_product_ids.add(p_id)
                urgency = "Due Soon" if pred.get("is_due_soon") else ("Overdue" if pred.get("is_overdue") else "Upcoming")
                recommended.append({
                    "id": p_id,
                    "name": p_dict["name"],
                    "category": p_dict.get("category", pred.get("category")),
                    "brand": p_dict.get("brand", pred.get("brand")),
                    "price": float(p_dict.get("price") or 0.0),
                    "original_price": float(p_dict.get("original_price") or p_dict.get("price") or 0.0),
                    "rating": float(p_dict.get("rating") or 4.5),
                    "image_url": p_dict.get("image_url") or "",
                    "badge": f"Restock {urgency}",
                    "recommendation_reason": (
                        f"Replenishment Need: {pred.get('evidence_explanation')} "
                        f"Estimated restock date: {pred.get('estimated_replenishment_date')}."
                    ),
                    "affinity_score": 0.95 if pred.get("is_due_soon") else 0.88,
                    "type": "replenishment",
                })

        # ── 2. Priority 2: High-Affinity Category & Brand Discoveries ────────────
        ranked_categories = learned_profile.get("ranked_categories", [])
        ranked_brands = set(b.lower() for b in learned_profile.get("ranked_brands", []))
        spending_max = float(learned_profile.get("typical_spending_max", 50000.0) or 50000.0)
        spending_min = float(learned_profile.get("typical_spending_min", 0.0) or 0.0)

        # Query top catalog items from user's preferred categories within spending range
        target_categories = ranked_categories[:3] if ranked_categories else []
        if not target_categories:
            # Fallback to general popular categories if no specific affinity
            popular_cats = database.query_db(
                "SELECT category, COUNT(*) as cnt FROM products GROUP BY category ORDER BY cnt DESC LIMIT 3"
            )
            target_categories = [c["category"] for c in (popular_cats or [])]

        for cat in target_categories:
            cat_products = database.query_db(
                """
                SELECT * FROM products
                WHERE category = ?
                  AND price <= ?
                ORDER BY rating DESC, review_count_demo DESC
                LIMIT 8
                """,
                (cat, max(spending_max * 1.5, 5000.0)),
            )

            for prod_row in (cat_products or []):
                prod = dict(prod_row)
                p_id = prod["id"]
                if p_id in dismissed_ids or p_id in seen_product_ids:
                    continue

                seen_product_ids.add(p_id)
                price = float(prod.get("price") or 0.0)
                brand = (prod.get("brand") or "").strip()
                is_fav_brand = brand.lower() in ranked_brands

                # Compute match score
                score = 0.70
                if is_fav_brand:
                    score += 0.15
                if spending_min <= price <= spending_max:
                    score += 0.10

                reason = (
                    f"Recommended based on your top interest in '{cat}'. "
                    f"Matches your '{learned_profile.get('spending_tier', 'Smart Value')}' budget profile "
                    f"at Rs {price:,.0f}."
                )
                if is_fav_brand:
                    reason = f"Matches your preferred brand '{brand}' in '{cat}', rated {prod.get('rating')} stars."

                recommended.append({
                    "id": p_id,
                    "name": prod["name"],
                    "category": prod["category"],
                    "brand": brand,
                    "price": price,
                    "original_price": float(prod.get("original_price") or price),
                    "rating": float(prod.get("rating") or 4.5),
                    "image_url": prod.get("image_url") or "",
                    "badge": "Brand Favorite" if is_fav_brand else "Top Pick",
                    "recommendation_reason": reason,
                    "affinity_score": round(score, 2),
                    "type": "affinity_discovery",
                })

                if len(recommended) >= 12:
                    break

            if len(recommended) >= 12:
                break

        # Sort combined recommendations by affinity score
        recommended.sort(key=lambda x: x["affinity_score"], reverse=True)
        return recommended[:10]

    def _get_dismissed_ids(self, user_id: int) -> Set[int]:
        """Fetch set of product IDs dismissed by the user."""
        pref = database.query_db(
            "SELECT dismissed_recommendation_ids FROM shopping_preferences WHERE user_id = ?",
            (user_id,),
            one=True,
        )
        if not pref:
            return set()
        p_dict = dict(pref)
        ids = _safe_json(p_dict.get("dismissed_recommendation_ids"), [])
        return set(int(x) for x in ids if str(x).isdigit())

    @classmethod
    def dismiss_recommendation(cls, user_id: int, product_id: int) -> bool:
        """Add a product ID to user's dismissed recommendations list."""
        pref = database.query_db(
            "SELECT id, dismissed_recommendation_ids FROM shopping_preferences WHERE user_id = ?",
            (user_id,),
            one=True,
        )
        if pref:
            p_dict = dict(pref)
            current_ids = set(_safe_json(p_dict.get("dismissed_recommendation_ids"), []))
            current_ids.add(int(product_id))
            database.execute_db(
                "UPDATE shopping_preferences SET dismissed_recommendation_ids = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                (json.dumps(list(current_ids)), user_id),
            )
        else:
            database.execute_db(
                "INSERT INTO shopping_preferences (user_id, dismissed_recommendation_ids) VALUES (?, ?)",
                (user_id, json.dumps([int(product_id)])),
            )
        return True
