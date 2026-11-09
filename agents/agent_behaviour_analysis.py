"""
agents/agent_behaviour_analysis.py
----------------------------------
Behaviour Analysis Agent:
Analyzes real customer activity across 5 key dimensions:
1. Completed purchases
2. Frequently purchased categories
3. Product browsing activity
4. Wishlist engagement
5. Cart activity & search queries
Computes meaningful behavioral summaries and tracks changes in interests over time.
"""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import database
from services.purchase_history_service import PurchaseHistoryService

logger = logging.getLogger(__name__)


class BehaviourAnalysisAgent:
    """Agent that analyzes customer interactions and interest trends."""

    AGENT_NAME = "BehaviourAnalysisAgent"

    def run(self, user_id: int) -> Dict[str, Any]:
        """Aggregate and evaluate customer shopping behavior."""
        # 1. Verified completed purchases
        eligible_items = PurchaseHistoryService.get_eligible_purchases_for_user(user_id)
        purchased_categories = Counter()
        repeat_products = Counter()

        for item in eligible_items:
            cat = (item.get("category") or "General").strip()
            qty = max(1, int(item.get("quantity") or 1))
            purchased_categories[cat] += qty
            pname = (item.get("product_name") or "Product").strip()
            repeat_products[pname] += qty

        # 2. Wishlist activity
        wishlist_rows = database.query_db(
            """SELECT w.*, p.name, p.category, p.price, p.image_url
               FROM wishlist_items w
               LEFT JOIN products p ON w.product_id = p.id
               WHERE w.user_id = ?
               ORDER BY w.id DESC""",
            (user_id,)
        )
        wishlist_items = [dict(r) for r in (wishlist_rows or [])]
        wishlist_categories = Counter(item.get("category") for item in wishlist_items if item.get("category"))

        # 3. Cart activity
        cart_rows = database.query_db(
            """SELECT c.*, p.name, p.category, p.price
               FROM cart_items c
               LEFT JOIN products p ON c.product_id = p.id
               WHERE c.user_id = ?""",
            (user_id,)
        )
        cart_items = [dict(r) for r in (cart_rows or [])]
        cart_categories = Counter(item.get("category") for item in cart_items if item.get("category"))

        # 4. Browsing and Search activity
        activity_rows = database.query_db(
            """SELECT * FROM user_activity
               WHERE user_id = ?
               ORDER BY id DESC LIMIT 100""",
            (user_id,)
        )
        activities = [dict(r) for r in (activity_rows or [])]

        browsed_categories = Counter()
        total_browsed_count = 0
        search_queries = []
        recent_cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        recent_categories = Counter()
        older_categories = Counter()

        for act in activities:
            atype = act.get("activity_type", "").lower()
            q_or_c = act.get("query_or_category", "")
            created = str(act.get("created_at") or "")

            if atype == "browse":
                total_browsed_count += 1
                cat = q_or_c or "General"
                browsed_categories[cat] += 1
                if created >= recent_cutoff:
                    recent_categories[cat] += 1
                else:
                    older_categories[cat] += 1
            elif atype == "search":
                if q_or_c and q_or_c not in search_queries:
                    search_queries.append(q_or_c)

        # 5. Composite Category Interest Ranking
        composite_interest = Counter()
        for cat, cnt in purchased_categories.items():
            composite_interest[cat] += cnt * 4  # Purchases carry high weight
        for cat, cnt in wishlist_categories.items():
            composite_interest[cat] += cnt * 2  # Wishlist carries medium weight
        for cat, cnt in cart_categories.items():
            composite_interest[cat] += cnt * 2.5
        for cat, cnt in browsed_categories.items():
            composite_interest[cat] += cnt * 1

        top_engaged_categories = [
            {"category": cat, "score": round(score, 1)}
            for cat, score in composite_interest.most_common(6)
        ]

        # 6. Interest Drift / Changes Over Time
        interest_trends = []
        for cat, recent_cnt in recent_categories.most_common(3):
            old_cnt = older_categories.get(cat, 0)
            if recent_cnt > old_cnt:
                interest_trends.append({
                    "category": cat,
                    "trend": "Rising Interest",
                    "description": f"Exploring {cat} significantly more in the past 30 days."
                })
        if not interest_trends and top_engaged_categories:
            top_cat = top_engaged_categories[0]["category"]
            interest_trends.append({
                "category": top_cat,
                "trend": "Consistent Focus",
                "description": f"Consistently your most engaged shopping category."
            })

        has_activity = (
            len(eligible_items) > 0 or
            len(wishlist_items) > 0 or
            len(cart_items) > 0 or
            len(activities) > 0
        )

        return {
            "has_activity": has_activity,
            "total_purchases_recorded": len(eligible_items),
            "wishlist_count": len(wishlist_items),
            "cart_count": len(cart_items),
            "browsing_events_count": total_browsed_count,
            "recent_search_queries": search_queries[:8],
            "top_purchased_categories": [
                {"category": cat, "count": cnt} for cat, cnt in purchased_categories.most_common(5)
            ],
            "top_engaged_categories": top_engaged_categories,
            "frequently_repurchased": [
                {"product_name": p, "count": c} for p, c in repeat_products.most_common(5) if c > 1
            ],
            "interest_trends": interest_trends,
        }
