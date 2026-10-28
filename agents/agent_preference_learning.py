"""
agents/agent_preference_learning.py
-----------------------------------
Preference Learning Agent:
Updates and synthesizes the user's shopping profile from observed eligible purchases
and explicitly declared preferences. Respects user privacy controls (opt-in/opt-out)
and detects spending tiers, brand affinities, category weights, and preference drift over time.
"""

from __future__ import annotations

import json
import logging
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import database
from config import Config
from services.purchase_history_service import PurchaseHistoryService

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


class PreferenceLearningAgent:
    """Agent that learns and refines the user's digital shopping profile."""

    AGENT_NAME = "PreferenceLearningAgent"

    def run(
        self,
        user_id: int,
        purchase_summary: Optional[Dict[str, Any]] = None,
        run_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Synthesize user's explicit preferences with behavioral purchase patterns.

        Parameters
        ----------
        user_id : int
            The authenticated user's ID.
        purchase_summary : dict, optional
            Output from PurchaseHistoryAgent (if already computed).
        run_id : str, optional
            UUID for orchestrator tracking.

        Returns
        -------
        dict
            Learned profile including weighted categories, brands, price boundaries,
            spending tier, purchase cadence, and preference evolution.
        """
        t0 = time.time()
        try:
            learned = self._learn_preferences(user_id, purchase_summary)
            duration = time.time() - t0
            _log_agent_run(
                run_id or "",
                self.AGENT_NAME,
                user_id,
                "success",
                duration,
                f"Learned profile for user {user_id}. Tier: {learned.get('spending_tier')}, Top categories: {learned.get('ranked_categories')[:3]}",
            )
            return learned
        except Exception as exc:
            duration = time.time() - t0
            logger.error("PreferenceLearningAgent failed for user %s: %s", user_id, exc, exc_info=True)
            _log_agent_run(
                run_id or "",
                self.AGENT_NAME,
                user_id,
                "error",
                duration,
                "Preference Learning Agent execution failed",
                str(exc),
            )
            return self._fallback_profile(user_id, str(exc))

    def _learn_preferences(
        self, user_id: int, purchase_summary: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Learn multi-dimensional preferences from explicit + implicit signals."""
        # 1. Check user privacy opt-in
        opted_in = PurchaseHistoryService.is_twin_history_opted_in(user_id)

        # 2. Fetch explicit preferences from database
        pref_row = database.query_db(
            "SELECT * FROM shopping_preferences WHERE user_id = ?",
            (user_id,),
            one=True,
        )
        explicit_prefs = dict(pref_row) if pref_row else {}

        explicit_categories = _safe_json(explicit_prefs.get("preferred_categories"), [])
        explicit_brands = _safe_json(explicit_prefs.get("preferred_brands"), [])
        budget_min = float(explicit_prefs.get("budget_min", 0.0) or 0.0)
        budget_max = float(explicit_prefs.get("budget_max", Config.DEFAULT_BUDGET_MAX) or Config.DEFAULT_BUDGET_MAX)
        declared_frequency = explicit_prefs.get("shopping_frequency", "monthly")

        # 3. If opted out of purchase history, rely strictly on explicit declarations
        if not opted_in:
            return {
                "user_id": user_id,
                "privacy_opted_in": False,
                "purchase_history_utilized": False,
                "spending_tier": "Value (Self-Declared)",
                "typical_spending_min": budget_min,
                "typical_spending_max": budget_max,
                "ranked_categories": explicit_categories,
                "ranked_brands": explicit_brands,
                "observed_frequency": declared_frequency,
                "preference_evolution": {
                    "is_evolving": False,
                    "insight": "Purchase history learning is paused as per privacy settings.",
                },
                "explanation": (
                    "Personalization is based exclusively on your manually declared preferences "
                    "because purchase history learning is turned off in your privacy settings."
                ),
            }

        # 4. Fetch purchase history if not passed in
        if purchase_summary is None:
            raw_purchases = PurchaseHistoryService.get_eligible_purchases_for_user(user_id)
        else:
            raw_purchases = purchase_summary.get("recent_purchases", [])
            # Also get all eligible records for full statistical calculations
            raw_purchases = PurchaseHistoryService.get_eligible_purchases_for_user(user_id)

        if not raw_purchases:
            # User has no purchase history yet — use explicit preferences with transparent notice
            return {
                "user_id": user_id,
                "privacy_opted_in": True,
                "purchase_history_utilized": False,
                "spending_tier": "Standard Explorer",
                "typical_spending_min": budget_min,
                "typical_spending_max": budget_max,
                "ranked_categories": explicit_categories,
                "ranked_brands": explicit_brands,
                "observed_frequency": declared_frequency,
                "preference_evolution": {
                    "is_evolving": False,
                    "insight": "No purchase history available yet to evaluate pattern evolution.",
                },
                "explanation": (
                    "You haven't completed any orders yet. As you make purchases on PreTwin AI, "
                    "your Digital Twin will automatically learn your spending habits, preferred brands, "
                    "and favorite categories."
                ),
            }

        # 5. Extract price distributions and spending metrics
        prices = [float(p.get("price") or 0.0) for p in raw_purchases if float(p.get("price") or 0.0) > 0]
        if not prices:
            prices = [budget_min or 500.0]

        prices.sort()
        p_min = min(prices)
        p_max = max(prices)
        p_avg = sum(prices) / len(prices)
        # 80th percentile for typical ceiling
        idx_80 = int(len(prices) * 0.8)
        p_80 = prices[min(idx_80, len(prices) - 1)]

        # Determine spending tier based on actual purchase prices and budget
        spending_tier = self._classify_spending_tier(p_avg, p_80, budget_max)
        typical_spending_min = round(max(0.0, p_avg * 0.4), 2)
        typical_spending_max = round(max(p_80 * 1.25, p_avg * 1.5), 2)

        # 6. Rank Categories (Weighted: 60% actual purchase frequency + 40% explicit preference)
        cat_counts: Counter = Counter()
        for p in raw_purchases:
            cat = (p.get("category") or "").strip()
            if cat:
                cat_counts[cat] += int(p.get("quantity") or 1)

        category_scores: Dict[str, float] = defaultdict(float)
        total_p_qty = sum(cat_counts.values()) or 1
        for cat, cnt in cat_counts.items():
            category_scores[cat] += (cnt / total_p_qty) * 0.60

        for idx, cat in enumerate(explicit_categories):
            weight = max(0.1, 0.40 - (idx * 0.05))
            category_scores[cat] += weight

        ranked_categories = [
            cat for cat, _ in sorted(category_scores.items(), key=lambda x: x[1], reverse=True)
        ]

        # 7. Rank Brands (Weighted: purchase history + explicit brands)
        brand_counts: Counter = Counter()
        for p in raw_purchases:
            br = (p.get("brand") or "").strip()
            if br and br.lower() not in ("generic", "unknown", "n/a"):
                brand_counts[br] += int(p.get("quantity") or 1)

        brand_scores: Dict[str, float] = defaultdict(float)
        total_b_qty = sum(brand_counts.values()) or 1
        for br, cnt in brand_counts.items():
            brand_scores[br] += (cnt / total_b_qty) * 0.60

        for idx, br in enumerate(explicit_brands):
            weight = max(0.1, 0.40 - (idx * 0.05))
            brand_scores[br] += weight

        ranked_brands = [
            br for br, _ in sorted(brand_scores.items(), key=lambda x: x[1], reverse=True)
        ]

        # 8. Shopping Cadence / Frequency analysis
        observed_frequency, cadence_days = self._calculate_shopping_cadence(raw_purchases)

        # 9. Preference Evolution over time (Recent 45 days vs Earlier)
        evolution_info = self._analyze_preference_evolution(raw_purchases)

        # 10. Persist learned attributes into shopping_preferences table
        self._persist_learned_preferences(user_id, spending_tier, typical_spending_min, typical_spending_max)

        return {
            "user_id": user_id,
            "privacy_opted_in": True,
            "purchase_history_utilized": True,
            "spending_tier": spending_tier,
            "typical_spending_min": typical_spending_min,
            "typical_spending_max": typical_spending_max,
            "average_item_spend": round(p_avg, 2),
            "max_item_spend": round(p_max, 2),
            "ranked_categories": ranked_categories,
            "ranked_brands": ranked_brands,
            "observed_frequency": observed_frequency,
            "cadence_days": cadence_days,
            "preference_evolution": evolution_info,
            "explanation": (
                f"Your Digital Twin has observed {len(raw_purchases)} verified purchases. "
                f"Your typical spending tier is '{spending_tier}' (avg Rs {p_avg:,.0f}/item), "
                f"shopping approximately every {cadence_days} days."
            ),
        }

    def _classify_spending_tier(self, avg_price: float, p80_price: float, budget_max: float) -> str:
        """Categorize customer spending into clear, meaningful purchasing tiers."""
        effective_metric = (avg_price * 0.6) + (p80_price * 0.4)
        if effective_metric < 750:
            return "Budget Saver"
        elif effective_metric < 2500:
            return "Smart Value"
        elif effective_metric < 8000:
            return "Mid-Range Quality"
        elif effective_metric < 25000:
            return "Premium Explorer"
        else:
            return "Luxury & High-End"

    def _calculate_shopping_cadence(self, purchases: List[Dict[str, Any]]) -> Tuple[str, int]:
        """Estimate shopping frequency and average interval in days."""
        dates = []
        for p in purchases:
            p_date_str = str(p.get("purchase_date") or "")[:10]
            if p_date_str:
                try:
                    dates.append(datetime.strptime(p_date_str, "%Y-%m-%d"))
                except Exception:
                    pass

        dates = sorted(list(set(dates)))
        if len(dates) < 2:
            return ("Monthly", 30)

        intervals = [(dates[i] - dates[i - 1]).days for i in range(1, len(dates))]
        avg_days = sum(intervals) / len(intervals)
        cadence_days = max(1, int(round(avg_days)))

        if cadence_days <= 7:
            freq = "Weekly"
        elif cadence_days <= 18:
            freq = "Bi-weekly"
        elif cadence_days <= 45:
            freq = "Monthly"
        else:
            freq = "Occasional / Seasonal"

        return (freq, cadence_days)

    def _analyze_preference_evolution(self, purchases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compare recent orders (last 45 days) against historical baseline to detect interest drift."""
        now = datetime.now()
        recent_threshold = now - timedelta(days=45)

        recent_cats: Counter = Counter()
        older_cats: Counter = Counter()

        for p in purchases:
            p_date_str = str(p.get("purchase_date") or "")[:10]
            cat = (p.get("category") or "").strip()
            if not cat:
                continue

            is_recent = False
            if p_date_str:
                try:
                    dt = datetime.strptime(p_date_str, "%Y-%m-%d")
                    if dt >= recent_threshold:
                        is_recent = True
                except Exception:
                    pass

            if is_recent:
                recent_cats[cat] += 1
            else:
                older_cats[cat] += 1

        emerging = []
        for cat, cnt in recent_cats.most_common():
            if older_cats[cat] == 0:
                emerging.append(cat)

        if emerging:
            insight_text = f"Emerging interest detected in {', '.join(emerging[:2])} over the last 45 days."
            is_evolving = True
        elif recent_cats and older_cats:
            top_recent = recent_cats.most_common(1)[0][0]
            top_older = older_cats.most_common(1)[0][0]
            if top_recent != top_older:
                insight_text = f"Shift in primary focus: recently purchasing more '{top_recent}' compared to earlier focus on '{top_older}'."
                is_evolving = True
            else:
                insight_text = f"Stable shopping profile consistently focused on '{top_recent}'."
                is_evolving = False
        else:
            insight_text = "Shopping profile is developing as more transactions are recorded."
            is_evolving = False

        return {
            "is_evolving": is_evolving,
            "emerging_categories": emerging[:3],
            "insight": insight_text,
        }

    def _persist_learned_preferences(
        self, user_id: int, tier: str, min_spend: float, max_spend: float
    ) -> None:
        """Safely save derived statistical attributes to shopping_preferences."""
        try:
            pref = database.query_db(
                "SELECT id FROM shopping_preferences WHERE user_id = ?",
                (user_id,),
                one=True,
            )
            if pref:
                database.execute_db(
                    """
                    UPDATE shopping_preferences
                    SET spending_tier = ?,
                        typical_spending_min = ?,
                        typical_spending_max = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                    """,
                    (tier, min_spend, max_spend, user_id),
                )
            else:
                database.execute_db(
                    """
                    INSERT INTO shopping_preferences
                    (user_id, spending_tier, typical_spending_min, typical_spending_max)
                    VALUES (?, ?, ?, ?)
                    """,
                    (user_id, tier, min_spend, max_spend),
                )
        except Exception as exc:
            logger.warning("Failed to persist learned preferences for user %s: %s", user_id, exc)

    def _fallback_profile(self, user_id: int, error: str) -> Dict[str, Any]:
        """Safe fallback on execution exception."""
        return {
            "user_id": user_id,
            "privacy_opted_in": True,
            "purchase_history_utilized": False,
            "spending_tier": "Value",
            "typical_spending_min": 200.0,
            "typical_spending_max": 5000.0,
            "ranked_categories": [],
            "ranked_brands": [],
            "observed_frequency": "monthly",
            "cadence_days": 30,
            "preference_evolution": {"is_evolving": False, "insight": "Statistical analysis unavailable."},
            "explanation": "Default preference profile applied.",
            "error": error,
        }
