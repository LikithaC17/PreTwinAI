"""
Agent B — Predictive Shopping Agent
--------------------------------------
Analyses the shopping-twin profile produced by Agent A and generates
data-driven purchase predictions using four documented rules.
"""
from __future__ import annotations

import json
import time
import logging
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from typing import Any

from database import execute_db
from config import Config

logger = logging.getLogger(__name__)


# ───────────────────────────── helpers ────────────────────────────────────────

def _safe_json(value: Any, default=None):
    if value is None:
        return default if default is not None else []
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default if default is not None else []


def _confidence_label(score: float) -> str:
    if score >= 0.75:
        return "High"
    if score >= 0.50:
        return "Medium"
    return "Low"


def _timeframe_from_days(days: int) -> str:
    if days <= 7:
        return "Within the week"
    if days <= 14:
        return "Within 2 weeks"
    if days <= 30:
        return "Within the month"
    return "Within the next few months"


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

class PredictiveShoppingAgent:
    """Agent B — generates purchase predictions from a twin profile."""

    AGENT_NAME = "PredictiveShoppingAgent"
    MAX_PREDICTIONS = Config.MAX_PREDICTIONS

    def run(self, twin_profile: dict, run_id: str) -> list | dict:
        """
        Parameters
        ----------
        twin_profile : dict   Output from Agent A.
        run_id       : str    Shared run UUID.

        Returns
        -------
        list of prediction dicts, sorted by confidence descending.
        Returns a dict with *insufficient_data=True* if no data to work with.
        """
        t0 = time.time()
        user_id = twin_profile.get("user_id", 0)
        try:
            result = self._predict(twin_profile, run_id)
            duration = time.time() - t0
            count = len(result) if isinstance(result, list) else 0
            _log_agent_run(
                run_id, self.AGENT_NAME, user_id, "success", duration,
                f"Generated {count} predictions."
            )
            return result
        except Exception as exc:
            duration = time.time() - t0
            logger.error("PredictiveShoppingAgent error: %s", exc, exc_info=True)
            _log_agent_run(
                run_id, self.AGENT_NAME, user_id, "error", duration,
                "Agent B failed", str(exc)
            )
            return {"insufficient_data": True, "reason": str(exc)}

    # -------------------------------------------------------- core logic -----

    def _predict(self, profile: dict, run_id: str) -> list | dict:
        user_id            = profile.get("user_id", 0)
        history            = profile.get("purchase_history", [])
        preferences        = profile.get("preferences", {})
        shopping_goals     = profile.get("shopping_goals", [])
        preferred_cats     = preferences.get("preferred_categories", [])
        budget_max         = preferences.get("budget_max", Config.DEFAULT_BUDGET_MAX)

        has_data = len(history) > 0 or len(preferred_cats) > 0
        if not has_data:
            return {
                "insufficient_data": True,
                "reason": (
                    "No purchase history and no preferred categories on file. "
                    "Add preferences or make a purchase to unlock predictions."
                ),
            }

        # ── Analyse history ──────────────────────────────────────────────────
        category_counts:   Counter   = Counter()
        last_purchase_by_cat: dict   = {}          # cat -> datetime
        brand_by_cat:         dict   = defaultdict(list)

        for item in history:
            cat = (item.get("category") or "").lower().strip()
            if not cat:
                continue
            category_counts[cat] += 1

            # track last purchase date per category
            date_str = item.get("purchase_date") or item.get("created_at") or ""
            if date_str:
                try:
                    d = datetime.fromisoformat(str(date_str).split("T")[0].split(" ")[0])
                    if cat not in last_purchase_by_cat or d > last_purchase_by_cat[cat]:
                        last_purchase_by_cat[cat] = d
                except (ValueError, TypeError):
                    pass

            brand = (item.get("brand") or "").strip()
            if brand:
                brand_by_cat[cat].append(brand)

        # ── Generate predictions ─────────────────────────────────────────────
        predictions: list[dict] = []

        # — Rule 1: Recurring Category —
        for cat, count in category_counts.items():
            if count >= 2:
                confidence = min(0.9, 0.4 + 0.1 * count)
                days_since = self._days_since(last_purchase_by_cat.get(cat))
                top_brand  = Counter(brand_by_cat[cat]).most_common(1)
                brand_hint = f" (often {top_brand[0][0]})" if top_brand else ""
                predictions.append({
                    "predicted_category": cat,
                    "predicted_product": f"Popular {cat.title()} item{brand_hint}",
                    "reason": f"Rule 1 — Recurring Category: You've purchased from '{cat}' {count} times.",
                    "supporting_evidence": [
                        f"Purchased {count} -  -  in this category",
                        f"Last purchase {days_since} days ago" if days_since else "Recent purchase detected",
                    ],
                    "estimated_timeframe": _timeframe_from_days(max(7, 30 - (days_since or 30))),
                    "confidence_score": round(confidence, 2),
                    "confidence_label": _confidence_label(confidence),
                    "recommended_action": f"Browse {cat.title()} section — you're a repeat buyer.",
                    "rule_used": "Rule 1",
                })

        # — Rule 2: Time-based Replenishment —
        for cat, last_dt in last_purchase_by_cat.items():
            days_since = (datetime.now() - last_dt).days
            if days_since >= 25 and cat in [p.lower() for p in preferred_cats]:
                # avoid duplicate (may already be in Rule 1)
                already = any(
                    p["predicted_category"] == cat and p["rule_used"] == "Rule 2"
                    for p in predictions
                )
                if not already:
                    confidence = 0.6
                    predictions.append({
                        "predicted_category": cat,
                        "predicted_product": f"Replenishment of {cat.title()} item",
                        "reason": (
                            f"Rule 2 — Time-based Replenishment: "
                            f"It's been {days_since} days since you bought from '{cat}' and it's a preferred category."
                        ),
                        "supporting_evidence": [
                            f"Last {cat} purchase was {days_since} days ago",
                            "Category is in your stated preferences",
                        ],
                        "estimated_timeframe": "Within the week" if days_since >= 45 else "Within 2 weeks",
                        "confidence_score": confidence,
                        "confidence_label": _confidence_label(confidence),
                        "recommended_action": f"Time to restock {cat.title()} — consider reordering soon.",
                        "rule_used": "Rule 2",
                    })

        # — Rule 3: Preferred Category Never Purchased —
        purchased_cats_lower = {c.lower() for c in category_counts.keys()}
        for pref_cat in preferred_cats:
            pc = pref_cat.lower().strip()
            if pc and pc not in purchased_cats_lower:
                confidence = 0.5
                predictions.append({
                    "predicted_category": pc,
                    "predicted_product": f"First {pc.title()} purchase based on your preferences",
                    "reason": (
                        f"Rule 3 — Preferred Category Not Purchased: "
                        f"'{pref_cat}' is in your preferences but you haven't bought from it yet."
                    ),
                    "supporting_evidence": [
                        f"'{pref_cat}' is listed as a preferred category",
                        "No prior purchases detected in this category",
                    ],
                    "estimated_timeframe": "When ready",
                    "confidence_score": confidence,
                    "confidence_label": _confidence_label(confidence),
                    "recommended_action": f"Explore {pref_cat.title()} — you indicated interest but haven't bought yet.",
                    "rule_used": "Rule 3",
                })

        # — Rule 4: Shopping Goal Aligned —
        for goal in shopping_goals:
            target_cat = (
                goal.get("target_category")
                or self._extract_category_from_goal(goal)
            )
            if not target_cat:
                continue
            tc = target_cat.lower().strip()
            confidence = 0.7
            goal_label = goal.get("goal_title") or goal.get("goal_description", "your goal")
            predictions.append({
                "predicted_category": tc,
                "predicted_product": f"{tc.title()} item aligned with your goal",
                "reason": (
                    f"Rule 4 — Shopping Goal Aligned: "
                    f"Your goal '{goal_label}' calls for items in '{tc}'."
                ),
                "supporting_evidence": [
                    f"Active shopping goal: '{goal_label}'",
                    f"Goal target category: {target_cat}",
                ],
                "estimated_timeframe": self._goal_timeframe(goal),
                "confidence_score": confidence,
                "confidence_label": _confidence_label(confidence),
                "recommended_action": f"Purchase {tc.title()} to progress toward your goal.",
                "rule_used": "Rule 4",
            })

        # ── Deduplicate by category (keep highest confidence) ───────────────
        deduped: dict[str, dict] = {}
        for pred in predictions:
            cat = pred["predicted_category"]
            if cat not in deduped or pred["confidence_score"] > deduped[cat]["confidence_score"]:
                deduped[cat] = pred

        final = sorted(deduped.values(), key=lambda x: x["confidence_score"], reverse=True)
        final = final[: self.MAX_PREDICTIONS]

        # ── Persist to DB ────────────────────────────────────────────────────
        for pred in final:
            try:
                execute_db(
                    """INSERT INTO predictions
                       (user_id, run_id, predicted_category, predicted_product,
                        reason, supporting_evidence, estimated_timeframe,
                        confidence_score, confidence_label, recommended_action)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        user_id, run_id,
                        pred["predicted_category"],
                        pred["predicted_product"],
                        pred["reason"],
                        json.dumps(pred["supporting_evidence"]),
                        pred["estimated_timeframe"],
                        pred["confidence_score"],
                        pred["confidence_label"],
                        pred["recommended_action"],
                    ),
                )
            except Exception as exc:
                logger.warning("Failed to save prediction: %s", exc)

        return final

    # -------------------------------------------------------- helpers --------

    @staticmethod
    def _days_since(dt: datetime | None) -> int | None:
        if dt is None:
            return None
        return (datetime.now() - dt).days

    @staticmethod
    def _extract_category_from_goal(goal: dict) -> str:
        """Heuristic: extract a category keyword from goal text."""
        text = " ".join([
            str(goal.get("goal_title", "")),
            str(goal.get("goal_description", "")),
        ]).lower()
        keywords = [
            "electronics", "clothing", "furniture", "food", "books",
            "sports", "beauty", "health", "toys", "tools", "kitchen",
            "garden", "automotive", "travel", "fitness",
        ]
        for kw in keywords:
            if kw in text:
                return kw
        return ""

    @staticmethod
    def _goal_timeframe(goal: dict) -> str:
        target_date = goal.get("target_date")
        if not target_date:
            return "When ready"
        try:
            td = datetime.fromisoformat(str(target_date).split("T")[0])
            days = (td - datetime.now()).days
            return _timeframe_from_days(max(0, days))
        except (ValueError, TypeError):
            return "When ready"

PredictiveAgent = PredictiveShoppingAgent
