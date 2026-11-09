"""
agents/agent_twin_coordinator.py
--------------------------------
Digital Twin Coordinator:
Synthesizes customer identity, behavior, spending, and future needs into a
unified, explainable Digital Twin profile. Formulates transparent insights
tagged with their empirical source, confidence level, and sample period.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from agents.agent_customer_profile import CustomerProfileAgent
from agents.agent_behaviour_analysis import BehaviourAnalysisAgent
from agents.agent_spending_analysis import SpendingAnalysisAgent
from agents.agent_future_needs import FutureNeedsAgent

logger = logging.getLogger(__name__)


class DigitalTwinCoordinator:
    """Master coordinator assembling the 6 core dimensions of the Personalization Twin."""

    AGENT_NAME = "DigitalTwinCoordinator"

    def __init__(self):
        self.profile_agent = CustomerProfileAgent()
        self.behaviour_agent = BehaviourAnalysisAgent()
        self.spending_agent = SpendingAnalysisAgent()
        self.future_agent = FutureNeedsAgent()

    def get_full_twin_dashboard(self, user_id: int) -> Dict[str, Any]:
        """Produce the comprehensive Digital Twin dashboard payload."""
        identity = self.profile_agent.run(user_id)
        behaviour = self.behaviour_agent.run(user_id)
        spending = self.spending_agent.run(user_id)
        future_needs = self.future_agent.run(user_id)

        insights = self._generate_explainable_insights(identity, behaviour, spending)
        archetype = self._determine_archetype(identity, spending)

        return {
            "success": True,
            "user_id": user_id,
            "archetype": archetype,
            "identity": identity,
            "behaviour": behaviour,
            "spending": spending,
            "insights": insights,
            "future_needs": future_needs,
            "is_personalization_enabled": identity.get("is_personalization_enabled", True),
        }

    def _determine_archetype(self, identity: dict, spending: dict) -> str:
        """Assign an authentic archetype title reflecting customer's real habits."""
        cats = [c.lower() for c in identity.get("explicit", {}).get("categories", [])]
        tier = spending.get("spending_tier", "Smart Value")
        aov = spending.get("average_order_value", 0)

        if "electronics" in cats or "laptops" in cats or "mobiles" in cats:
            return "Precision Tech & Smart Home Enthusiast"
        elif "fashion" in cats or "footwear" in cats:
            return "Curated Style & Contemporary Fashionist"
        elif "home & kitchen" in cats or "appliances" in cats:
            return "Mindful Living & Household Optimizer"
        elif tier == "Premium Luxe" or aov > 6000:
            return "Premium Quality & Discovery Collector"
        else:
            return "Smart Value & Practical Essentials Shopper"

    def _generate_explainable_insights(
        self, identity: dict, behaviour: dict, spending: dict
    ) -> List[Dict[str, Any]]:
        """Formulate 4 to 6 explainable natural-language insights."""
        insights = []

        # 1. Primary Category Preference Insight
        top_engaged = behaviour.get("top_engaged_categories", [])
        explicit_cats = identity.get("explicit", {}).get("categories", [])
        if top_engaged:
            primary_cat = top_engaged[0]["category"]
            is_explicit = any(primary_cat.lower() == c.lower() for c in explicit_cats)
            source = "Explicitly Selected Preference" if is_explicit else "Inferred from Shopping Engagement"
            source_type = "explicit" if is_explicit else "purchase"
            conf = 95 if is_explicit else 82
            insights.append({
                "title": f"Core Interest: {primary_cat}",
                "text": (
                    f"Your most active shopping focus is {primary_cat}, "
                    f"reflecting strong engagement across searches, browsing, and purchase activity."
                ),
                "source": source,
                "source_type": source_type,
                "confidence": f"{conf}%",
                "period": "Last 90 days",
                "explanation": (
                    f"Explicitly declared in your profile settings."
                    if is_explicit else
                    f"Derived from composite engagement score ({top_engaged[0]['score']} activity points)."
                ),
            })

        # 2. Spending Habits & Price Range Insight
        has_spend = spending.get("has_spending_history", False)
        if has_spend:
            total_orders = spending.get("total_orders", 1)
            aov = spending.get("average_order_value", 0)
            p_min = spending.get("typical_price_min", 0)
            p_max = spending.get("typical_price_max", 0)
            insights.append({
                "title": "Observed Price Range & Basket Value",
                "text": (
                    f"You usually select products between ₹{p_min:,.0f} and ₹{p_max:,.0f}, "
                    f"with an average completed order value of ₹{aov:,.2f}."
                ),
                "source": "Verified Purchase History",
                "source_type": "purchase",
                "confidence": "94%",
                "period": f"Over {total_orders} completed order(s)",
                "explanation": "Calculated strictly from delivered and paid transactions. Cancelled and pending COD orders are excluded.",
            })
        else:
            b_min = identity.get("explicit", {}).get("budget_min", 0)
            b_max = identity.get("explicit", {}).get("budget_max", 10000)
            insights.append({
                "title": "Declared Budget Ceiling",
                "text": f"Your current shopping budget ceiling is set between ₹{b_min:,.0f} and ₹{b_max:,.0f}.",
                "source": "Explicitly Selected Preference",
                "source_type": "explicit",
                "confidence": "100%",
                "period": "Active Profile Setting",
                "explanation": "Manually configured in your budget preferences.",
            })

        # 3. Shopping Cadence Insight
        cadence = spending.get("purchase_cadence_label") if has_spend else identity.get("explicit", {}).get("frequency", "Monthly")
        cadence_days = spending.get("purchase_frequency_days", 30) if has_spend else 30
        insights.append({
            "title": f"Shopping Cadence: {cadence}",
            "text": f"Your shopping cycle typically recurs every ~{cadence_days} days for regular basket replenishment.",
            "source": "Verified Order Frequency" if has_spend else "Explicit Profile Preference",
            "source_type": "purchase" if has_spend else "explicit",
            "confidence": "88%" if has_spend else "90%",
            "period": "Seasonal cycle",
            "explanation": "Derived from delivery intervals between completed orders." if has_spend else "Set in shopping cadence preferences.",
        })

        # 4. Brand Affinity Insight
        brands = identity.get("explicit", {}).get("brands", [])
        inferred_brands = identity.get("inferred", {}).get("brands", [])
        if brands:
            insights.append({
                "title": "Brand Affinities",
                "text": f"You show a consistent preference for {', '.join(brands[:3])}.",
                "source": "Explicitly Selected Preference",
                "source_type": "explicit",
                "confidence": "95%",
                "period": "Active Profile Setting",
                "explanation": "Chosen by you in trusted brand preferences.",
            })
        elif inferred_brands:
            insights.append({
                "title": "Inferred Brand Affinities",
                "text": f"Your purchase history indicates repeated selection of {', '.join(inferred_brands[:3])}.",
                "source": "Inferred from Purchase History",
                "source_type": "purchase",
                "confidence": "76%",
                "period": "Recent purchases",
                "explanation": "Identified from brand tags on delivered orders.",
            })

        # 5. Browsing & Wishlist Signal Insight
        wishlist_count = behaviour.get("wishlist_count", 0)
        browsing_count = behaviour.get("browsing_events_count", 0)
        if wishlist_count > 0 or browsing_count > 0:
            insights.append({
                "title": "Exploration & Intent Signals",
                "text": (
                    f"You have saved {wishlist_count} item(s) to your wishlist and actively explored "
                    f"{browsing_count} product(s) recently."
                ),
                "source": "Browsing & Wishlist Activity",
                "source_type": "browsing",
                "confidence": "85%",
                "period": "Current session & history",
                "explanation": "Tracks active intent signals without sharing data with third parties.",
            })

        # 6. Interest Evolution / Drift Insight
        trends = behaviour.get("interest_trends", [])
        if trends:
            top_trend = trends[0]
            insights.append({
                "title": f"Interest Evolution: {top_trend['trend']}",
                "text": top_trend["description"],
                "source": "Behavioral Trend Analysis",
                "source_type": "browsing",
                "confidence": "80%",
                "period": "Last 30 days vs earlier",
                "explanation": "Compares recent category interaction density against historical baselines.",
            })

        return insights
