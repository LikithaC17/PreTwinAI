"""
Agent F — Recommendation Explanation Agent
-------------------------------------------
Produces human-readable, evidence-backed explanations for every
recommended product and an overall session summary.
Falls back gracefully to template-based generation when no LLM key is
available.
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


# ───────────────────────────── agent class ────────────────────────────────────

class RecommendationExplanationAgent:
    """Agent F — generates explanations for recommendations."""

    AGENT_NAME = "RecommendationExplanationAgent"

    def run(self, *args, **kwargs) -> dict:
        """
        Accepts:
          run(twin_profile, predictions, discovered_products, recommendations, comparisons, run_id)
        or
          run(recommendations, profile, run_id)
        or
          run(profile, recommendations, run_id)
        """
        twin_profile = {}
        predictions = []
        discovered_products = []
        recommendations = {}
        comparisons = {}
        run_id = ""

        if len(args) == 6:
            twin_profile, predictions, discovered_products, recommendations, comparisons, run_id = args
        elif len(args) == 3:
            a0, a1, a2 = args
            run_id = str(a2)
            # detect which is profile and which is recommendations
            if isinstance(a0, dict) and ("user_id" in a0 or "profile_insights" in a0 or "budget_range" in a0) and not ("recommendations" in a0 and isinstance(a0.get("recommendations"), list)):
                twin_profile = a0
                recommendations = a1
            elif isinstance(a1, dict) and ("user_id" in a1 or "profile_insights" in a1 or "budget_range" in a1):
                twin_profile = a1
                recommendations = a0
            else:
                recommendations = a0
                twin_profile = a1
        else:
            twin_profile = kwargs.get("twin_profile") or kwargs.get("profile") or {}
            predictions = kwargs.get("predictions") or []
            discovered_products = kwargs.get("discovered_products") or []
            recommendations = kwargs.get("recommendations") or {}
            comparisons = kwargs.get("comparisons") or {}
            run_id = kwargs.get("run_id", "")

        # Normalize recommendations if it's a list
        if isinstance(recommendations, list):
            recommendations = {"recommendations": recommendations, "total_cost": sum(float(r.get("price", 0)) for r in recommendations)}

        t0 = time.time()
        user_id = twin_profile.get("user_id", 0) if isinstance(twin_profile, dict) else 0
        try:
            result = self._explain(
                twin_profile, predictions, discovered_products,
                recommendations, comparisons, run_id
            )
            duration = time.time() - t0
            _log_agent_run(
                run_id, self.AGENT_NAME, user_id, "success", duration,
                f"Explained {len(result.get('explanations', []))} recommendations."
            )
            return result
        except Exception as exc:
            duration = time.time() - t0
            logger.error("RecommendationExplanationAgent error: %s", exc, exc_info=True)
            _log_agent_run(
                run_id, self.AGENT_NAME, user_id, "error", duration,
                "Agent F failed", str(exc)
            )
            return {
                "explanations":                  [],
                "recommendations":               [],
                "overall_summary":               {},
                "what_would_improve_predictions": [],
                "error":                          str(exc),
            }

    # -------------------------------------------------------- core logic -----

    def _explain(
        self,
        profile:     dict,
        predictions: list | dict,
        discovered:  list,
        recs_output: dict,
        comparisons: dict,
        run_id:      str,
    ) -> dict:
        user_id  = profile.get("user_id", 0)
        prefs    = profile.get("preferences", {})
        budget_max = float(prefs.get("budget_max", Config.DEFAULT_BUDGET_MAX) or Config.DEFAULT_BUDGET_MAX)

        recs          = recs_output.get("recommendations", [])
        total_cost    = recs_output.get("total_cost", 0.0)
        budget_status = recs_output.get("budget_status", "Unknown")

        pred_list = predictions if isinstance(predictions, list) else []

        # Build a quick lookup: category → prediction
        pred_by_cat: dict[str, dict] = {}
        for p in pred_list:
            cat = p.get("predicted_category", "")
            if cat:
                pred_by_cat[cat] = p

        # Build comparison winner lookup: product_id → winner_reason
        winner_reasons: dict[int, str] = {}
        for comp in (comparisons or {}).get("comparisons", []):
            wid = comp.get("winner_id")
            if wid:
                winner_reasons[wid] = comp.get("winner_reason", "")

        # ── Per-recommendation explanations ──────────────────────────────────
        explanations = []

        for rec in recs:
            product    = rec.get("product", rec)
            pid        = rec.get("product_id") or product.get("id")
            prod_name  = rec.get("product_name") or product.get("name", "Unknown Product")
            cat        = (rec.get("category") or product.get("category") or "").lower()
            price      = float(rec.get("price") or product.get("price") or 0)
            budget_fit = rec.get("budget_fit", "Unknown")

            # Trace back the prediction that triggered this
            pred = pred_by_cat.get(cat, {})
            evidence_used = []

            # Assemble human-readable explanation from template
            user_actions = self._user_actions_phrase(pred, profile, cat)
            budget_reasoning = self._budget_phrase(price, budget_max, budget_fit)
            confidence_note  = self._confidence_phrase(pred)

            explanation = (
                f"{prod_name} is recommended because {user_actions}. "
                f"{budget_reasoning}. "
                f"{confidence_note}."
            )

            # Evidence chain
            evidence_used.append(f"Prediction rule: {pred.get('rule_used', 'profile-based')}")
            if pred.get("supporting_evidence"):
                evidence_used.extend(pred["supporting_evidence"])
            if pid in winner_reasons:
                evidence_used.append(f"Comparison winner: {winner_reasons[pid]}")
            relevance = product.get("relevance_score", rec.get("relevance_score", 0))
            evidence_used.append(f"Relevance score: {relevance}")

            # Limitations
            limitations = self._derive_limitations(rec, pred, profile, budget_max)

            explanations.append({
                "product_id":    pid,
                "product_name":  prod_name,
                "explanation":   explanation,
                "evidence_used": evidence_used,
                "limitations":   limitations,
            })

        # ── Optionally use LLM to polish explanations ────────────────────────
        if Config.USE_LLM and Config.OPENAI_API_KEY:
            explanations = self._llm_enhance(explanations, profile)

        # ── Overall summary ───────────────────────────────────────────────────
        top_pick = recs[0]["product_name"] if recs else "None"
        key_insights = self._key_insights(profile, pred_list, recs, budget_max, total_cost)

        overall_summary = {
            "total_recommendations": len(recs),
            "budget_used":           round(total_cost, 2),
            "budget_remaining":      round(budget_max - total_cost, 2),
            "budget_status":         budget_status,
            "top_pick":              top_pick,
            "key_insights":          key_insights,
        }

        # ── What would improve predictions ───────────────────────────────────
        improvements = self._improvement_suggestions(profile, pred_list, recs)

        # Attach explanations to recommendation items
        recs_with_explanations = []
        for i, rec in enumerate(recs):
            expl_text = explanations[i]["explanation"] if i < len(explanations) else "Matches your shopping preferences."
            r_copy = dict(rec)
            r_copy["explanation"] = expl_text
            r_copy["reason"] = expl_text
            r_copy["rationale"] = expl_text
            recs_with_explanations.append(r_copy)

        return {
            "explanations":                  explanations,
            "recommendations":               recs_with_explanations,
            "overall_summary":               overall_summary,
            "what_would_improve_predictions": improvements,
        }

    # -------------------------------------------------------- template helpers

    def _user_actions_phrase(self, pred: dict, profile: dict, cat: str) -> str:
        rule = pred.get("rule_used", "")
        history = profile.get("purchase_history", [])
        prefs   = profile.get("preferences", {})

        if rule == "Rule 1":
            count = sum(
                1 for h in history
                if (h.get("category") or "").lower() == cat
            )
            return (
                f"you've purchased from the '{cat}' category {count} time(s), "
                f"showing a strong repeat-buying pattern"
            )
        if rule == "Rule 2":
            return (
                f"you regularly buy from '{cat}' and it's been over 25 days since "
                f"your last purchase — replenishment time"
            )
        if rule == "Rule 3":
            return (
                f"'{cat}' is listed as a preferred category in your profile "
                f"but you haven't purchased from it yet"
            )
        if rule == "Rule 4":
            goals = profile.get("shopping_goals", [])
            goal_label = goals[0].get("goal_title") if goals else "your active shopping goal"
            return f"it aligns with {goal_label}"

        # Fallback
        pref_cats = prefs.get("preferred_categories", [])
        if cat in [p.lower() for p in pref_cats]:
            return f"'{cat}' is one of your stated preferred categories"
        return "it matches your shopping profile"

    def _budget_phrase(self, price: float, budget_max: float, fit: str) -> str:
        if budget_max <= 0:
            return f"Priced at ${price:.2f}"
        pct = (price / budget_max) * 100
        if fit == "Excellent":
            return f"At ${price:.2f}, it uses only {pct:.0f}% of your ${budget_max:.0f} budget — excellent value"
        if fit == "Good":
            return f"At ${price:.2f}, it fits comfortably within your ${budget_max:.0f} budget ({pct:.0f}% used)"
        if fit == "Tight":
            return f"At ${price:.2f}, it's close to your ${budget_max:.0f} budget limit — consider carefully"
        return f"At ${price:.2f}, it stretches your ${budget_max:.0f} budget"

    def _confidence_phrase(self, pred: dict) -> str:
        label = pred.get("confidence_label", "")
        score = pred.get("confidence_score", 0)
        if not label:
            return "Based on your available profile data"
        return (
            f"Prediction confidence is {label} ({score:.0%}) based on "
            f"your purchase history and stated preferences"
        )

    def _derive_limitations(
        self, rec: dict, pred: dict, profile: dict, budget_max: float
    ) -> list[str]:
        lims = []
        history_count = len(profile.get("purchase_history", []))
        if history_count < 3:
            lims.append("Limited purchase history may reduce prediction accuracy")
        conf = pred.get("confidence_score", 0)
        if conf < 0.5:
            lims.append("Low confidence prediction — treat as exploratory suggestion")
        price = float(rec.get("price") or 0)
        if budget_max > 0 and price > budget_max * 0.8:
            lims.append("Price is near your budget ceiling")
        if not lims:
            lims.append("No significant limitations identified")
        return lims

    def _key_insights(
        self, profile: dict, predictions: list,
        recs: list, budget_max: float, total_cost: float
    ) -> list[str]:
        insights = []
        completeness = profile.get("profile_completeness", 0)
        insights.append(
            f"Your shopping profile is {completeness}% complete — "
            + ("strong data foundation." if completeness >= 70 else "adding more data will improve predictions.")
        )
        if predictions:
            rules = [p.get("rule_used", "unknown") for p in predictions]
            unique_rules = list(dict.fromkeys(rules))
            insights.append(
                f"{len(predictions)} prediction(s) generated using: "
                f"{', '.join(unique_rules)}."
            )
        if recs:
            top = recs[0]["product_name"]
            insights.append(f"Top recommendation: {top}.")
        if budget_max > 0:
            pct = (total_cost / budget_max) * 100
            insights.append(
                f"Total basket cost ${total_cost:.2f} uses {pct:.0f}% of your ${budget_max:.0f} budget."
            )
        for ins in profile.get("profile_insights", [])[:2]:
            if ins not in insights:
                insights.append(ins)
        return insights[:5]

    def _improvement_suggestions(
        self, profile: dict, predictions: list, recs: list
    ) -> list[str]:
        suggestions = []
        history_count = len(profile.get("purchase_history", []))
        if history_count == 0:
            suggestions.append(
                "Add purchase history — even 3-5 past purchases dramatically improve predictions."
            )
        elif history_count < 10:
            suggestions.append(
                f"More purchase history ({history_count}/10+ recommended) would sharpen predictions."
            )
        prefs = profile.get("preferences", {})
        if not prefs.get("preferred_brands"):
            suggestions.append("Add preferred brands to enable brand-affinity matching.")
        if not prefs.get("preferred_categories"):
            suggestions.append("Add preferred categories to unlock Rule 3 (Preferred Category) predictions.")
        if not profile.get("shopping_goals"):
            suggestions.append("Set a shopping goal to enable Rule 4 (Goal-Aligned) predictions.")
        budget_max = float(prefs.get("budget_max") or 0)
        if budget_max == 0:
            suggestions.append("Set a budget maximum to enable budget-aware filtering and ranking.")
        return suggestions or ["Profile looks good! Keep shopping to improve future predictions."]

    # ── Optional LLM enhancement ──────────────────────────────────────────────

    def _llm_enhance(self, explanations: list, profile: dict) -> list:
        """Replace template explanations with LLM-generated ones if key available."""
        try:
            import openai  # type: ignore
            client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
            username = profile.get("user_info", {}).get("username", "the user")
            enhanced = []
            for expl in explanations:
                prompt = (
                    f"You are a helpful shopping assistant. Explain in 2-3 friendly "
                    f"sentences why {expl['product_name']} is recommended for {username}. "
                    f"Evidence: {'; '.join(expl['evidence_used'][:3])}. "
                    f"Keep it conversational, positive, and concise."
                )
                try:
                    response = client.chat.completions.create(
                        model=Config.OPENAI_MODEL,
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=150,
                        temperature=0.7,
                    )
                    expl["explanation"] = response.choices[0].message.content.strip()
                except Exception as llm_exc:
                    logger.warning("LLM explanation failed for %s: %s",
                                   expl["product_name"], llm_exc)
                enhanced.append(expl)
            return enhanced
        except ImportError:
            logger.info("openai package not installed; using template explanations.")
            return explanations
        except Exception as exc:
            logger.warning("LLM enhancement failed: %s", exc)
            return explanations

ExplanationAgent = RecommendationExplanationAgent
