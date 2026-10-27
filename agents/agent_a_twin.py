"""
Agent A — Shopping Twin Agent
-------------------------------
Reads user data (profile, preferences, purchase history, shopping goals)
and builds a rich "Digital Shopping Twin" profile used by downstream agents.
"""
from __future__ import annotations

import json
import time
import logging
from datetime import datetime, timedelta
from collections import Counter
from typing import Any

from database import query_db, execute_db
from config import Config

logger = logging.getLogger(__name__)


# ───────────────────────────── helpers ────────────────────────────────────────

def _safe_json(value: Any, default=None):
    """Parse a JSON string safely; return *default* on failure."""
    if value is None:
        return default if default is not None else []
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default if default is not None else []


def _row_to_dict(row) -> dict:
    """Convert a sqlite3.Row (or None) to a plain dict."""
    if row is None:
        return {}
    try:
        return dict(row)
    except Exception:
        return {}


def _log_agent_run(run_id: str, agent_name: str, user_id: int,
                   status: str, duration: float, summary: str,
                   error: str = ""):
    """Persist execution metadata to *agent_runs* table."""
    try:
        execute_db(
            """INSERT INTO agent_runs
               (run_id, agent_name, user_id, status, execution_time_ms,
                output_summary, error_message)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (run_id, agent_name, user_id, status,
             int(duration * 1000), summary[:2000], error[:1000]),
        )
    except Exception as exc:
        logger.warning("agent_runs insert failed: %s", exc)


# ───────────────────────────── agent class ────────────────────────────────────

class ShoppingTwinAgent:
    """Agent A — builds a digital shopping-twin profile for a user."""

    AGENT_NAME = "ShoppingTwinAgent"

    # ------------------------------------------------------------------ run --

    def run(self, user_id: int, run_id: str) -> dict:
        """
        Build and return the user's shopping-twin profile.

        Parameters
        ----------
        user_id : int
            Primary key in the *users* table.
        run_id : str
            UUID string shared across the current orchestrator run.

        Returns
        -------
        dict
            Structured profile ready for Agent B.
        """
        t0 = time.time()
        try:
            result = self._build_profile(user_id, run_id)
            duration = time.time() - t0
            _log_agent_run(
                run_id, self.AGENT_NAME, user_id, "success", duration,
                f"Profile built. Categories: {result.get('top_categories')}"
            )
            return result
        except Exception as exc:
            duration = time.time() - t0
            logger.error("ShoppingTwinAgent error: %s", exc, exc_info=True)
            _log_agent_run(
                run_id, self.AGENT_NAME, user_id, "error", duration,
                "Agent A failed", str(exc)
            )
            return self._empty_profile(user_id, str(exc))

    # -------------------------------------------------------- core logic -----

    def _build_profile(self, user_id: int, run_id: str) -> dict:
        # ── 1. User record ──────────────────────────────────────────────────
        user_row = query_db(
            "SELECT * FROM users WHERE id = ?", (user_id,), one=True
        )
        if not user_row:
            return self._empty_profile(
                user_id,
                f"User {user_id} not found in the database."
            )
        user_info = _row_to_dict(user_row)

        # ── 2. Shopping preferences ─────────────────────────────────────────
        pref_row = query_db(
            "SELECT * FROM shopping_preferences WHERE user_id = ?",
            (user_id,), one=True
        )
        prefs = _row_to_dict(pref_row)

        preferred_categories = _safe_json(prefs.get("preferred_categories"), [])
        preferred_brands      = _safe_json(prefs.get("preferred_brands"), [])
        budget_min  = float(prefs.get("budget_min", 0) or 0)
        budget_max  = float(prefs.get("budget_max", Config.DEFAULT_BUDGET_MAX)
                            or Config.DEFAULT_BUDGET_MAX)

        # ── 3. Purchase history (last 20) ───────────────────────────────────
        history_rows = query_db(
            """SELECT * FROM purchase_history
               WHERE user_id = ?
               ORDER BY purchase_date DESC, id DESC
               LIMIT 20""",
            (user_id,)
        )
        purchase_history = [_row_to_dict(r) for r in (history_rows or [])]

        # ── 4. Shopping goals ───────────────────────────────────────────────
        goal_rows = query_db(
            "SELECT * FROM shopping_goals WHERE user_id = ? AND status = 'active'",
            (user_id,)
        )
        shopping_goals = [_row_to_dict(g) for g in (goal_rows or [])]

        # ── 5. Derived insights ─────────────────────────────────────────────
        top_categories = self._top_categories(purchase_history, preferred_categories)
        recent_brands  = self._recent_brands(purchase_history, preferred_brands)
        insights       = self._generate_insights(
            user_info, prefs, purchase_history, shopping_goals,
            preferred_categories, preferred_brands, budget_max
        )

        return {
            "user_id": user_id,
            "user_info": {
                "id": user_info.get("id"),
                "username": user_info.get("username", "Unknown"),
                "email": user_info.get("email", ""),
                "full_name": user_info.get("full_name", ""),
                "created_at": str(user_info.get("created_at", "")),
            },
            "preferences": {
                "preferred_categories": preferred_categories,
                "preferred_brands": preferred_brands,
                "budget_min": budget_min,
                "budget_max": budget_max,
                "shopping_frequency": prefs.get("shopping_frequency", "monthly"),
                "eco_friendly": bool(prefs.get("eco_friendly_preference", 0)),
                "deal_hunter": bool(prefs.get("deal_hunter", 0)),
            },
            "purchase_history": purchase_history,
            "shopping_goals": shopping_goals,
            "profile_insights": insights,
            "budget_range": {"min": budget_min, "max": budget_max},
            "top_categories": top_categories,
            "recent_brands": recent_brands,
            "has_sufficient_data": len(purchase_history) > 0 or len(preferred_categories) > 0,
            "profile_completeness": self._completeness_score(
                user_info, prefs, purchase_history, shopping_goals
            ),
        }

    # -------------------------------------------------------- helpers --------

    def _top_categories(self, history: list, preferred: list) -> list[str]:
        cats: list[str] = []
        for item in history:
            c = item.get("category", "")
            if c:
                cats.append(c.lower().strip())
        counts = Counter(cats)
        # preferred categories that appear in history first, then by frequency
        result = [c for c in preferred if c.lower() in counts]
        for cat, _ in counts.most_common():
            if cat not in [r.lower() for r in result]:
                result.append(cat)
        return result[:8]

    def _recent_brands(self, history: list, preferred: list) -> list[str]:
        brands: list[str] = []
        for item in history:
            b = item.get("brand", "")
            if b:
                brands.append(b)
        combined = list(dict.fromkeys(preferred + brands))  # preserve order, dedup
        return combined[:10]

    def _generate_insights(
        self, user_info, prefs, history, goals,
        preferred_categories, preferred_brands, budget_max
    ) -> list[str]:
        insights: list[str] = []

        # Purchase volume
        n = len(history)
        if n == 0:
            insights.append("No purchase history found — recommendations will rely on stated preferences.")
        elif n < 5:
            insights.append(f"Limited purchase history ({n} items) — predictions may be broad.")
        else:
            insights.append(f"Rich purchase history with {n} recent items enables strong predictions.")

        # Category diversity
        cats = [h.get("category", "") for h in history if h.get("category")]
        unique_cats = set(c.lower() for c in cats)
        if len(unique_cats) >= 4:
            insights.append(f"Diverse shopper across {len(unique_cats)} categories: {', '.join(list(unique_cats)[:4])}.")
        elif len(unique_cats) > 0:
            insights.append(f"Focused shopper primarily in: {', '.join(unique_cats)}.")

        # Budget
        if budget_max > 0:
            insights.append(f"Budget ceiling is ${budget_max:.0f} — recommendations will stay within this range.")

        # Brand loyalty
        if len(preferred_brands) >= 2:
            insights.append(f"Shows brand loyalty toward: {', '.join(preferred_brands[:3])}.")

        # Shopping goals
        if goals:
            goal_titles = [g.get("goal_title") or g.get("goal_description", "") for g in goals]
            insights.append(f"Active shopping goal(s): {'; '.join(t for t in goal_titles if t)[:120]}.")

        # Recency
        if history:
            last_date_str = history[0].get("purchase_date", "")
            if last_date_str:
                try:
                    last_date = datetime.fromisoformat(str(last_date_str).split("T")[0])
                    days_ago = (datetime.now() - last_date).days
                    if days_ago <= 7:
                        insights.append("Very recent purchase activity — high replenishment signal.")
                    elif days_ago <= 30:
                        insights.append(f"Last purchase was {days_ago} days ago — moderate replenishment readiness.")
                    else:
                        insights.append(f"Last purchase was {days_ago} days ago — due for shopping soon.")
                except (ValueError, TypeError):
                    pass

        return insights or ["Profile built from available data. Add more history for richer insights."]

    def _completeness_score(self, user_info, prefs, history, goals) -> int:
        """0-100 score indicating how complete the user's profile is."""
        score = 0
        if user_info:
            score += 20
        if prefs:
            score += 20
        if history:
            score += min(30, len(history) * 3)
        if goals:
            score += 10
        pref_cats = _safe_json(prefs.get("preferred_categories") if prefs else None, [])
        if pref_cats:
            score += 10
        pref_brands = _safe_json(prefs.get("preferred_brands") if prefs else None, [])
        if pref_brands:
            score += 10
        return min(score, 100)

    def _empty_profile(self, user_id: int, explanation: str) -> dict:
        return {
            "user_id": user_id,
            "user_info": {},
            "preferences": {
                "preferred_categories": [],
                "preferred_brands": [],
                "budget_min": Config.DEFAULT_BUDGET_MIN,
                "budget_max": Config.DEFAULT_BUDGET_MAX,
                "shopping_frequency": "monthly",
                "eco_friendly": False,
                "deal_hunter": False,
            },
            "purchase_history": [],
            "shopping_goals": [],
            "profile_insights": [explanation],
            "budget_range": {
                "min": Config.DEFAULT_BUDGET_MIN,
                "max": Config.DEFAULT_BUDGET_MAX,
            },
            "top_categories": [],
            "recent_brands": [],
            "has_sufficient_data": False,
            "profile_completeness": 0,
        }
