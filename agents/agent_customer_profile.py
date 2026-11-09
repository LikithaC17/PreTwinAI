"""
agents/agent_customer_profile.py
--------------------------------
Customer Profile Agent:
Manages customer shopping identity, clearly distinguishing explicitly selected
preferences from AI-inferred preferences. Calculates profile completeness
and ensures user preferences remain isolated and authenticated.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

import database

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


class CustomerProfileAgent:
    """Agent that builds and governs the customer's Shopping Identity."""

    AGENT_NAME = "CustomerProfileAgent"

    def run(self, user_id: int) -> Dict[str, Any]:
        """Compile the complete shopping identity for the authenticated customer."""
        user_row = database.query_db("SELECT * FROM users WHERE id = ?", (user_id,), one=True)
        user = dict(user_row) if user_row else {}

        pref_row = database.query_db("SELECT * FROM shopping_preferences WHERE user_id = ?", (user_id,), one=True)
        prefs = dict(pref_row) if pref_row else {}

        # 1. Explicit Preferences
        explicit_categories = _safe_json(prefs.get("preferred_categories"), [])
        explicit_brands = _safe_json(prefs.get("preferred_brands"), [])
        preferred_colors = _safe_json(prefs.get("preferred_colors"), [])
        preferred_styles = _safe_json(prefs.get("preferred_styles"), [])
        preferred_sizes = _safe_json(prefs.get("preferred_sizes"), [])
        budget_min = float(prefs.get("budget_min", 0.0) or 0.0)
        budget_max = float(prefs.get("budget_max", 10000.0) or 10000.0)
        shopping_frequency = prefs.get("shopping_frequency", "monthly")
        shopping_goals = prefs.get("shopping_goals", "")
        notes = prefs.get("notes", "")

        # 2. AI-Inferred Preferences (from verified orders & behavior)
        inferred_categories = _safe_json(prefs.get("inferred_categories"), [])
        inferred_brands = _safe_json(prefs.get("inferred_brands"), [])
        inferred_styles = _safe_json(prefs.get("inferred_styles"), [])
        corrected_dislikes = _safe_json(prefs.get("corrected_dislikes"), [])
        is_personalization_enabled = bool(prefs.get("is_personalization_enabled", 1))

        # Filter out anything the user explicitly disliked/corrected
        inferred_categories = [c for c in inferred_categories if c.lower() not in [d.lower() for d in corrected_dislikes]]
        inferred_brands = [b for b in inferred_brands if b.lower() not in [d.lower() for d in corrected_dislikes]]

        # Fallback inferences from purchase history if inferred lists are empty
        if not inferred_categories:
            cat_rows = database.query_db(
                """SELECT category, COUNT(*) as cnt FROM purchase_history
                   WHERE user_id = ? AND is_verified_purchase = 1 AND category IS NOT NULL AND category != ''
                   GROUP BY category ORDER BY cnt DESC LIMIT 5""",
                (user_id,)
            )
            inferred_categories = [
                r["category"] for r in (cat_rows or [])
                if r["category"] not in explicit_categories and r["category"].lower() not in [d.lower() for d in corrected_dislikes]
            ]

        if not inferred_brands:
            brand_rows = database.query_db(
                """SELECT brand, COUNT(*) as cnt FROM purchase_history
                   WHERE user_id = ? AND is_verified_purchase = 1 AND brand IS NOT NULL AND brand != '' AND LOWER(brand) != 'generic'
                   GROUP BY brand ORDER BY cnt DESC LIMIT 5""",
                (user_id,)
            )
            inferred_brands = [
                r["brand"] for r in (brand_rows or [])
                if r["brand"] not in explicit_brands and r["brand"].lower() not in [d.lower() for d in corrected_dislikes]
            ]

        # 3. Profile Completeness Score
        completeness = self._calculate_completeness(
            explicit_categories, explicit_brands, preferred_colors, preferred_sizes, budget_max, shopping_goals
        )

        return {
            "user_id": user_id,
            "username": user.get("username", "Shopper"),
            "email": user.get("email", ""),
            "full_name": user.get("full_name") or user.get("username", "Shopper"),
            "is_personalization_enabled": is_personalization_enabled,
            "explicit": {
                "categories": explicit_categories,
                "brands": explicit_brands,
                "colors": preferred_colors,
                "styles": preferred_styles,
                "sizes": preferred_sizes,
                "budget_min": budget_min,
                "budget_max": budget_max,
                "frequency": shopping_frequency,
                "goals": shopping_goals,
                "notes": notes,
            },
            "inferred": {
                "categories": inferred_categories,
                "brands": inferred_brands,
                "styles": inferred_styles,
                "corrected_dislikes": corrected_dislikes,
            },
            "completeness_score": completeness,
            "has_minimum_data": len(explicit_categories) > 0 or budget_max > 0,
        }

    def _calculate_completeness(self, cats, brands, colors, sizes, budget_max, goals) -> int:
        score = 0
        if cats: score += 25
        if brands: score += 20
        if colors or sizes: score += 15
        if budget_max > 0: score += 20
        if goals: score += 20
        return min(100, score)
