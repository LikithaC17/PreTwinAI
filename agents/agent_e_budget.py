"""
Agent E — Budget-Aware Recommendation Agent
---------------------------------------------
Enforces the user's hard budget ceiling, scores and ranks all candidate
products, and assembles a final basket with alternatives for over-budget
items.
"""
from __future__ import annotations

import json
import time
import logging
from typing import Any

from database import execute_db
from config import Config

logger = logging.getLogger(__name__)


# ───────────────────────────── helpers ────────────────────────────────────────

def _log_agent_run(run_id, agent_name, user_id, status, duration, summary, error=""):
    try:
        execute_db(
            """INSERT INTO agent_runs
               (run_id, agent_name, user_id, status, execution_time_ms,
                output_summary, error_message)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (run_id, agent_name, user_id or 0, status,
             int(duration * 1000), summary[:2000], error[:1000]),
        )
    except Exception as exc:
        logger.warning("agent_runs insert failed: %s", exc)


def _budget_fit_label(total: float, budget_max: float) -> str:
    if budget_max <= 0:
        return "No budget set"
    pct = total / budget_max
    if pct < 0.60:
        return "Excellent"
    if pct < 0.80:
        return "Good"
    if pct < 0.95:
        return "Tight"
    return "Over Budget"


# ───────────────────────────── agent class ────────────────────────────────────

class BudgetAwareRecommendationAgent:
    """Agent E — budget-conscious product ranking and basket assembly."""

    AGENT_NAME = "BudgetAwareRecommendationAgent"

    def run(self, *args, **kwargs) -> dict:
        """
        Accepts:
          run(discovered_products, comparisons, twin_profile, run_id)
        or
          run(discovered_products, twin_profile, run_id)
        """
        discovered_products = []
        comparisons = {}
        twin_profile = {}
        run_id = ""

        if len(args) == 4:
            discovered_products, comparisons, twin_profile, run_id = args
        elif len(args) == 3:
            discovered_products, twin_profile, run_id = args
            comparisons = {}
        elif len(args) == 2:
            discovered_products, twin_profile = args
            run_id = kwargs.get("run_id", "")
        else:
            discovered_products = kwargs.get("discovered_products") or kwargs.get("recommendations") or []
            comparisons = kwargs.get("comparisons") or {}
            twin_profile = kwargs.get("twin_profile") or kwargs.get("profile") or {}
            run_id = kwargs.get("run_id", "")

        if isinstance(discovered_products, dict) and "discovered_products" in discovered_products:
            discovered_products = discovered_products["discovered_products"]

        t0 = time.time()
        user_id = twin_profile.get("user_id", 0) if isinstance(twin_profile, dict) else 0
        try:
            result = self._recommend(discovered_products, comparisons, twin_profile, run_id)
            duration = time.time() - t0
            _log_agent_run(
                run_id, self.AGENT_NAME, user_id, "success", duration,
                f"Recommended {len(result['recommendations'])} products. "
                f"Total: ${result['total_cost']:.2f}."
            )
            return result
        except Exception as exc:
            duration = time.time() - t0
            logger.error("BudgetAwareRecommendationAgent error: %s", exc, exc_info=True)
            _log_agent_run(
                run_id, self.AGENT_NAME, user_id, "error", duration,
                "Agent E failed", str(exc)
            )
            return {
                "recommendations": [],
                "approved": [],
                "total_cost": 0.0,
                "budget_status": "error",
                "basket_summary": "An error occurred during recommendation.",
                "error": str(exc),
            }

    # -------------------------------------------------------- core logic -----

    def _recommend(
        self, products: list, comparisons: dict,
        profile: dict, run_id: str
    ) -> dict:
        prefs       = profile.get("preferences", {})
        budget_max  = float(prefs.get("budget_max", Config.DEFAULT_BUDGET_MAX) or Config.DEFAULT_BUDGET_MAX)
        pref_brands = [b.lower() for b in prefs.get("preferred_brands", [])]
        user_id     = profile.get("user_id", 0)

        if not products:
            return {
                "recommendations": [],
                "total_cost": 0.0,
                "budget_status": _budget_fit_label(0, budget_max),
                "basket_summary": "No products were discovered to recommend.",
            }

        # ── Score every candidate ────────────────────────────────────────────
        scored = []
        for p in products:
            price     = float(p.get("price") or 0)
            relevance = float(p.get("relevance_score", 0))
            brand     = (p.get("brand") or "").lower()
            pref_match = 1.0 if (brand and brand in pref_brands) else 0.0

            # Guard: skip products already over budget
            if budget_max > 0 and price > budget_max:
                continue

            base_score = (
                relevance * 0.5
                + (1 - price / budget_max if budget_max > 0 else 0.5) * 0.3
                + pref_match * 0.2
            )
            scored.append({**p, "_base_score": round(base_score, 3)})

        # Sort by base_score descending
        scored.sort(key=lambda x: x["_base_score"], reverse=True)

        # ── Greedy basket assembly ───────────────────────────────────────────
        basket:      list[dict] = []
        basket_ids:  set        = set()
        total_cost:  float      = 0.0

        standalone_candidates: list[dict] = []   # expensive but valid items

        for i, p in enumerate(scored):
            price = float(p.get("price") or 0)
            pid   = p.get("id") or p.get("product_name") or f"prod_{i}"

            if pid in basket_ids:
                continue

            # Item that costs more than 50% of budget → standalone candidate (only if multiple items exist)
            if len(scored) > 2 and budget_max > 0 and price > budget_max * 0.5:
                standalone_candidates.append(p)
                continue

            # Check if adding stays within budget
            if budget_max <= 0 or (total_cost + price) <= budget_max:
                basket.append(p)
                basket_ids.add(pid)
                total_cost += price

        # If basket is empty, add standalone candidates one at a time
        if not basket and standalone_candidates:
            for p in standalone_candidates:
                price = float(p.get("price") or 0)
                if budget_max <= 0 or price <= budget_max:
                    basket.append(p)
                    basket_ids.add(p.get("id"))
                    total_cost += price
                    break  # only one expensive standalone

        # ── Build recommendation records ─────────────────────────────────────
        recommendations = []
        for rank, p in enumerate(basket, start=1):
            price     = float(p.get("price") or 0)
            score     = p.get("_base_score", 0.5)
            reason    = self._build_reason(p, pref_brands, budget_max, comparisons)
            fit_label = _budget_fit_label(price, budget_max)
            alts      = self._find_alternatives(p, scored, basket_ids, budget_max)
            prod_name = p.get("name") or p.get("product_name") or "Unknown"

            rec = {
                "product":    p,
                "product_id": p.get("id"),
                "product_name": prod_name,
                "name":       prod_name,
                "category":   p.get("category", ""),
                "price":      price,
                "rank":       rank,
                "score":      score,
                "reason":     reason,
                "budget_fit": fit_label,
                "alternatives": alts,
            }
            recommendations.append(rec)

            # Persist
            try:
                execute_db(
                    """INSERT INTO recommendations
                       (user_id, run_id, product_id, product_name,
                        category, price, rank, score, reason,
                        budget_fit, alternatives)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        user_id, run_id,
                        p.get("id"), prod_name,
                        p.get("category"), price, rank, score,
                        reason, fit_label, json.dumps(alts),
                    ),
                )
            except Exception as exc:
                logger.warning("Failed to save recommendation: %s", exc)

        # ── Summary ──────────────────────────────────────────────────────────
        budget_status = _budget_fit_label(total_cost, budget_max)
        remaining     = budget_max - total_cost if budget_max > 0 else 0
        basket_summary = (
            f"{len(recommendations)} item(s) recommended. "
            f"Total: ${total_cost:.2f} / ${budget_max:.2f} budget "
            f"({budget_status}). Remaining: ${remaining:.2f}."
        )

        return {
            "recommendations": recommendations,
            "approved":        recommendations,
            "total_cost":      round(total_cost, 2),
            "total":           round(total_cost, 2),
            "budget_remaining": round(remaining, 2),
            "budget_status":   budget_status,
            "basket_summary":  basket_summary,
        }

    # -------------------------------------------------------- helpers --------

    def _build_reason(
        self, product: dict, pref_brands: list[str],
        budget_max: float, comparisons: dict
    ) -> str:
        parts = []
        brand = (product.get("brand") or "").lower()
        if brand and brand in pref_brands:
            parts.append(f"it's a preferred brand ({product.get('brand')})")

        price = float(product.get("price") or 0)
        if budget_max > 0 and price <= budget_max * 0.7:
            parts.append(f"excellent value at ${price:.2f}")
        elif budget_max > 0 and price <= budget_max:
            parts.append(f"fits your ${budget_max:.0f} budget at ${price:.2f}")

        # Check if it's a comparison winner
        for comp in (comparisons or {}).get("comparisons", []):
            if product.get("id") == comp.get("winner_id"):
                parts.append(f"top-rated in the {comp['category']} comparison")
                break

        relevance = float(product.get("relevance_score", 0))
        if relevance >= 0.7:
            parts.append("high relevance to your predictions")

        return (
            f"Recommended because "
            + (", and ".join(parts) if parts else "it best matches your profile")
            + "."
        )

    def _find_alternatives(
        self, product: dict, all_scored: list,
        basket_ids: set, budget_max: float
    ) -> list[dict]:
        """Return up to 2 cheaper alternatives in the same category."""
        cat   = (product.get("category") or "").lower()
        price = float(product.get("price") or 0)
        alts  = []

        for p in all_scored:
            if p.get("id") == product.get("id"):
                continue
            if (p.get("category") or "").lower() != cat:
                continue
            alt_price = float(p.get("price") or 0)
            if alt_price >= price:
                continue
            if budget_max > 0 and alt_price > budget_max:
                continue
            alts.append({
                "id":    p.get("id"),
                "name":  p.get("name"),
                "price": alt_price,
                "score": p.get("_base_score", 0),
            })
            if len(alts) >= 2:
                break

        return alts

BudgetAgent = BudgetAwareRecommendationAgent
