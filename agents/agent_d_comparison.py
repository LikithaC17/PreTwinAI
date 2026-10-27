"""
Agent D — Product Comparison Agent
--------------------------------------
Groups discovered products by category and, for each group, builds a
structured comparison table with a data-driven "best pick" winner.
"""
from __future__ import annotations

import json
import time
import logging
from collections import defaultdict
from typing import Any

from database import execute_db
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

class ProductComparisonAgent:
    """Agent D — compares products within each predicted category."""

    AGENT_NAME = "ProductComparisonAgent"
    MAX_PER_GROUP = Config.MAX_COMPARISON_PRODUCTS_PER_GROUP

    def run(self, discovered_products: list, twin_profile: dict, run_id: str) -> dict:
        """
        Parameters
        ----------
        discovered_products : list  Agent C output (discovered_products list).
        twin_profile        : dict  Agent A output.
        run_id              : str   Shared UUID.

        Returns
        -------
        dict with key *comparisons* — one entry per category group.
        """
        t0 = time.time()
        user_id = twin_profile.get("user_id", 0)
        try:
            result = self._compare(discovered_products, twin_profile, run_id)
            duration = time.time() - t0
            _log_agent_run(
                run_id, self.AGENT_NAME, user_id, "success", duration,
                f"Compared {len(result['comparisons'])} category groups."
            )
            return result
        except Exception as exc:
            duration = time.time() - t0
            logger.error("ProductComparisonAgent error: %s", exc, exc_info=True)
            _log_agent_run(
                run_id, self.AGENT_NAME, user_id, "error", duration,
                "Agent D failed", str(exc)
            )
            return {"comparisons": [], "error": str(exc)}

    # -------------------------------------------------------- core logic -----

    def _compare(self, products: list, profile: dict, run_id: str) -> dict:
        if not products:
            return {"comparisons": [], "note": "No products to compare."}

        prefs       = profile.get("preferences", {})
        pref_brands = [b.lower() for b in prefs.get("preferred_brands", [])]
        budget_max  = float(prefs.get("budget_max", Config.DEFAULT_BUDGET_MAX) or Config.DEFAULT_BUDGET_MAX)
        user_id     = profile.get("user_id", 0)

        # Group by category (if custom selection <= 10 products, compare all together in one group)
        by_category: dict[str, list] = defaultdict(list)
        if len(products) <= 10:
            cats = list(set((p.get("category") or "All").capitalize() for p in products))
            group_label = " & ".join(cats) if len(cats) <= 2 else "Selected Products"
            by_category[group_label] = products
        else:
            for p in products:
                cat = (p.get("category") or "uncategorised").lower()
                by_category[cat].append(p)

        comparisons = []
        all_comp_rows = []
        overall_winner_id = None
        overall_winner_reason = ""
        overall_best_score = -1.0

        for category, group in by_category.items():
            # Limit to top N by relevance_score
            group_sorted = sorted(
                group, key=lambda x: x.get("relevance_score", 0), reverse=True
            )[: self.MAX_PER_GROUP]

            if len(group_sorted) < 1:
                continue

            # Build comparison rows
            max_price  = max(float(p.get("price") or 0) for p in group_sorted) or 1.0
            comp_rows  = []
            best_score = -1.0
            winner_id  = None
            winner_row = None

            for p in group_sorted:
                specs   = p.get("specs_parsed") or _safe_json(
                    p.get("specifications") or p.get("specs"), {}
                )
                price   = float(p.get("price") or 0)
                brand   = (p.get("brand") or "").lower()
                rating  = float(p.get("rating") or 0)

                advantages  = self._derive_advantages(p, specs, pref_brands, budget_max)
                limitations = self._derive_limitations(p, specs, budget_max)

                # Scoring
                price_score  = (1 - price / max_price) * 0.4
                spec_score   = min(len(specs) / 5, 1.0) * 0.3
                brand_score  = 0.3 if brand and brand in pref_brands else 0.0
                rating_bonus = min(rating / 5, 1.0) * 0.1
                total_score  = price_score + spec_score + brand_score + rating_bonus

                comp_row = {
                    "product_id":       p.get("id"),
                    "id":               p.get("id"),
                    "name":             p.get("name", "Unknown Product"),
                    "product_name":     p.get("name", "Unknown Product"),
                    "brand":            p.get("brand", ""),
                    "category":         p.get("category", category),
                    "price":            price,
                    "rating":           rating,
                    "stock":            p.get("stock", 20),
                    "image_url":        p.get("image_url", ""),
                    "specs":            specs,
                    "specifications":   specs,
                    "advantages":       advantages,
                    "limitations":      limitations,
                    "comparison_score": round(total_score, 3),
                }
                comp_rows.append(comp_row)
                all_comp_rows.append(comp_row)

                if total_score > best_score:
                    best_score = total_score
                    winner_id  = p.get("id")
                    winner_row = comp_row

                if total_score > overall_best_score:
                    overall_best_score = total_score
                    overall_winner_id  = p.get("id")

            winner_reason = self._build_winner_reason(winner_row, pref_brands, budget_max)
            if not overall_winner_reason:
                overall_winner_reason = winner_reason

            # Persist to DB
            try:
                execute_db(
                    """INSERT INTO product_comparisons
                       (run_id, user_id, product_ids, comparison_data,
                        winner_id, winner_reason)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        run_id, user_id,
                        json.dumps([r["product_id"] for r in comp_rows]),
                        json.dumps(comp_rows),
                        winner_id,
                        winner_reason,
                    ),
                )
            except Exception as exc:
                logger.warning("Failed to save comparison: %s", exc)

            comparisons.append({
                "category":         category,
                "products":         comp_rows,
                "winner_id":        winner_id,
                "winner_reason":    winner_reason,
                "comparison_table": comp_rows,   # alias kept for compatibility
            })

        return {
            "comparisons":      comparisons,
            "winner_id":        overall_winner_id,
            "winner_reason":    overall_winner_reason,
            "products":         all_comp_rows,
            "comparison_table": all_comp_rows,
        }

    # -------------------------------------------------------- helpers --------

    def _derive_advantages(
        self, product: dict, specs: dict,
        pref_brands: list[str], budget_max: float
    ) -> list[str]:
        adv = []
        price  = float(product.get("price") or 0)
        brand  = (product.get("brand") or "").lower()
        rating = float(product.get("rating") or 0)

        if brand and brand in pref_brands:
            adv.append(f"Preferred brand ({product.get('brand')})")
        if budget_max > 0 and price <= budget_max * 0.7:
            adv.append(f"Great value at ${price:.2f}")
        if rating >= 4.5:
            adv.append(f"Excellent rating ({rating}/5)")
        elif rating >= 4.0:
            adv.append(f"Good rating ({rating}/5)")
        if len(specs) >= 5:
            adv.append("Detailed specifications available")
        # Surface a few interesting spec keys
        for key in ("warranty", "material", "capacity", "power", "speed"):
            if key in {k.lower() for k in specs.keys()}:
                adv.append(f"Spec available: {key}")
                break

        return adv or ["Available within budget"]

    def _derive_limitations(
        self, product: dict, specs: dict, budget_max: float
    ) -> list[str]:
        lim = []
        price  = float(product.get("price") or 0)
        rating = float(product.get("rating") or 0)

        if budget_max > 0 and price > budget_max * 0.85:
            lim.append(f"Price (${price:.2f}) near budget ceiling")
        if rating > 0 and rating < 3.5:
            lim.append(f"Below-average rating ({rating}/5)")
        if not specs:
            lim.append("Limited specification details")
        desc = product.get("description", "") or ""
        if len(desc) < 20:
            lim.append("Minimal product description")
        return lim or ["No notable limitations identified"]

    def _build_winner_reason(
        self, winner: dict | None, pref_brands: list[str], budget_max: float
    ) -> str:
        if not winner:
            return "No clear winner identified."
        parts = []
        brand = (winner.get("brand") or "").lower()
        price = winner.get("price", 0)
        if brand and brand in pref_brands:
            parts.append(f"it's a preferred brand ({winner.get('brand')})")
        if budget_max > 0 and float(price) <= budget_max * 0.7:
            parts.append(f"it's excellent value at ${float(price):.2f}")
        rating = winner.get("rating", 0)
        if float(rating) >= 4.0:
            parts.append(f"it has a strong rating of {rating}/5")
        if winner.get("specs"):
            parts.append("it has rich specification data")
        reason = (
            f"'{winner.get('name')}' is the best pick because "
            + (", and ".join(parts) if parts else "it scored highest overall")
            + "."
        )
        return reason

ComparisonAgent = ProductComparisonAgent
