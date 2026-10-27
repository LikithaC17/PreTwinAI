"""
Agent C — Product Discovery Agent
------------------------------------
For each prediction from Agent B, searches the products catalogue and
returns the most relevant matches with detailed scoring.
"""
from __future__ import annotations

import json
import time
import logging
from typing import Any

from database import query_db, execute_db
from config import Config

logger = logging.getLogger(__name__)


# ───────────────────────────── helpers ────────────────────────────────────────

def _safe_json(value: Any, default=None):
    if value is None:
        return default if default is not None else {}
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default if default is not None else {}


def _row_to_dict(row) -> dict:
    if row is None:
        return {}
    try:
        return dict(row)
    except Exception:
        return {}


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


# ───────────────────────────── agent class ────────────────────────────────────

class ProductDiscoveryAgent:
    """Agent C — discovers products matching each prediction."""

    AGENT_NAME = "ProductDiscoveryAgent"
    MAX_PER_PREDICTION = Config.MAX_PRODUCTS_PER_PREDICTION

    def run(self, *args, **kwargs) -> dict:
        """
        Accepts either:
          run(predictions, twin_profile, run_id)
        or
          run(twin_profile, predictions, run_id)
        """
        predictions = None
        twin_profile = None
        run_id = kwargs.get("run_id", "")

        # Detect argument positions
        for a in args:
            if isinstance(a, str) and not run_id:
                run_id = a
            elif isinstance(a, dict) and ("user_id" in a or "preferences" in a or "budget_range" in a):
                twin_profile = a
            elif isinstance(a, (list, dict)):
                predictions = a

        if twin_profile is None:
            twin_profile = kwargs.get("twin_profile") or kwargs.get("profile") or {}
        if predictions is None:
            predictions = kwargs.get("predictions") or []
        if not run_id:
            run_id = kwargs.get("run_id", "")

        t0 = time.time()
        user_id = twin_profile.get("user_id", 0) if isinstance(twin_profile, dict) else 0
        try:
            result = self._discover(predictions, twin_profile)
            duration = time.time() - t0
            _log_agent_run(
                run_id, self.AGENT_NAME, user_id, "success", duration,
                f"Discovered {len(result['discovered_products'])} products."
            )
            return result
        except Exception as exc:
            duration = time.time() - t0
            logger.error("ProductDiscoveryAgent error: %s", exc, exc_info=True)
            _log_agent_run(
                run_id, self.AGENT_NAME, user_id, "error", duration,
                "Agent C failed", str(exc)
            )
            return {"discovered_products": [], "products": [], "error": str(exc)}

    # -------------------------------------------------------- core logic -----

    def _discover(self, predictions: list | dict, profile: dict) -> dict:
        # If Agent B returned insufficient_data, check if we have profile fallback
        if isinstance(predictions, dict) and predictions.get("insufficient_data"):
            predictions = []

        prefs         = profile.get("preferences", {}) if isinstance(profile, dict) else {}
        budget_max    = float(
            prefs.get("budget_max")
            or profile.get("budget_range", {}).get("max")
            or Config.DEFAULT_BUDGET_MAX
        )
        pref_brands   = [b.lower() for b in prefs.get("preferred_brands", [])]

        seen_ids:     set        = set()
        all_products: list[dict] = []

        # If predictions are empty, fall back to profile categories
        pred_list = predictions if isinstance(predictions, list) else []
        if not pred_list:
            fallback_cats = profile.get("top_categories", []) or prefs.get("preferred_categories", [])
            pred_list = [{"predicted_category": c, "reason": "Based on preferred profile categories", "confidence_score": 0.5} for c in fallback_cats]

        for pred in pred_list:
            cat = pred.get("predicted_category", "")
            if not cat:
                continue

            products = self._search_products(cat, budget_max)

            for p_row in products:
                p = _row_to_dict(p_row)
                pid = p.get("id")
                if pid in seen_ids:
                    continue
                seen_ids.add(pid)

                score, reasons = self._score_product(p, cat, pred, pref_brands, budget_max)

                # Parse specs safely
                specs_raw = p.get("specifications") or p.get("specs") or "{}"
                p["specs_parsed"] = _safe_json(specs_raw, {})

                p["relevance_score"]  = round(score, 3)
                p["discovery_reason"] = "; ".join(reasons)
                p["matched_prediction"] = {
                    "category": pred.get("predicted_category"),
                    "reason": pred.get("reason", ""),
                    "confidence": pred.get("confidence_score", 0),
                }
                all_products.append(p)

        # Sort all products by relevance_score descending
        all_products.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

        return {
            "discovered_products": all_products,
            "products": all_products,
            "total_discovered": len(all_products),
        }

    # -------------------------------------------------------- helpers --------

    def _search_products(self, category: str, budget_max: float) -> list:
        """Fetch products from DB matching category (case-insensitive) within budget."""
        try:
            rows = query_db(
                """SELECT * FROM products
                   WHERE LOWER(category) = LOWER(?)
                     AND price <= ?
                     AND (stock IS NULL OR stock > 0)
                   ORDER BY rating DESC, price ASC
                   LIMIT ?""",
                (category, budget_max, self.MAX_PER_PREDICTION * 3),
            )
            if rows:
                return rows

            # Fuzzy fallback: LIKE match on category
            rows = query_db(
                """SELECT * FROM products
                   WHERE LOWER(category) LIKE ?
                     AND price <= ?
                     AND (stock IS NULL OR stock > 0)
                   ORDER BY rating DESC, price ASC
                   LIMIT ?""",
                (f"%{category.lower()}%", budget_max, self.MAX_PER_PREDICTION * 3),
            )
            return rows or []
        except Exception as exc:
            logger.warning("Product search failed for '%s': %s", category, exc)
            return []

    def _score_product(
        self, product: dict, category: str, prediction: dict,
        pref_brands: list[str], budget_max: float
    ) -> tuple[float, list[str]]:
        score   = 0.0
        reasons = []

        # +0.4 exact category match
        prod_cat = (product.get("category") or "").lower()
        if prod_cat == category.lower():
            score += 0.4
            reasons.append(f"Exact category match: {category}")
        elif category.lower() in prod_cat:
            score += 0.2
            reasons.append(f"Partial category match: {category}")

        # +0.2 preferred brand
        prod_brand = (product.get("brand") or "").lower()
        if prod_brand and prod_brand in pref_brands:
            score += 0.2
            reasons.append(f"Preferred brand: {product.get('brand')}")

        # +0.2 price well within budget
        price = float(product.get("price") or 0)
        if budget_max > 0 and price <= budget_max * 0.8:
            score += 0.2
            reasons.append(f"Price (${price:.2f}) well within budget")
        elif budget_max > 0 and price <= budget_max:
            score += 0.1
            reasons.append(f"Price (${price:.2f}) within budget")

        # +0.2 name/desc keyword match
        pred_name = (prediction.get("predicted_product") or "").lower()
        prod_name = (product.get("name") or "").lower()
        prod_desc = (product.get("description") or "").lower()
        shared = set(pred_name.split()) & set(prod_name.split() + prod_desc.split())
        if shared:
            score += min(0.2, len(shared) * 0.05)
            reasons.append(f"Name/description match on: {', '.join(list(shared)[:3])}")

        # Rating boost (small)
        rating = float(product.get("rating") or 0)
        if rating >= 4.0:
            score += 0.05
            reasons.append(f"High rating: {rating}")

        return min(score, 1.0), reasons

DiscoveryAgent = ProductDiscoveryAgent
