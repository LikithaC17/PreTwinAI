"""
agents/agent_purchase_history.py
--------------------------------
Purchase History Agent:
Retrieves, audits, and summarizes the authenticated user's eligible order and
purchase history. Strictly excludes cancelled, returned, refunded, or failed
purchases, preserving verified order integrity.
"""

from __future__ import annotations

import logging
import time
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

import database
from config import Config
from services.purchase_history_service import PurchaseHistoryService

logger = logging.getLogger(__name__)


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


class PurchaseHistoryAgent:
    """Agent that analyzes verified, eligible purchase history for an isolated user."""

    AGENT_NAME = "PurchaseHistoryAgent"

    def run(self, user_id: int, run_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute purchase history audit and analytical aggregation.

        Parameters
        ----------
        user_id : int
            The authenticated user's ID.
        run_id : str, optional
            UUID for orchestrator tracking.

        Returns
        -------
        dict
            Comprehensive summary containing orders count, item counts, total spend,
            average order value, frequently purchased items, category/brand breakdowns,
            and recent purchase timeline.
        """
        t0 = time.time()
        try:
            summary = self._summarize_history(user_id)
            duration = time.time() - t0
            _log_agent_run(
                run_id or "",
                self.AGENT_NAME,
                user_id,
                "success",
                duration,
                f"Parsed {summary['total_orders']} orders, {summary['total_items_count']} items. Spend: Rs {summary['total_spent']:.2f}",
            )
            return summary
        except Exception as exc:
            duration = time.time() - t0
            logger.error("PurchaseHistoryAgent failed for user %s: %s", user_id, exc, exc_info=True)
            _log_agent_run(
                run_id or "",
                self.AGENT_NAME,
                user_id,
                "error",
                duration,
                "Purchase History Agent execution failed",
                str(exc),
            )
            return self._empty_summary(user_id, str(exc))

    def _summarize_history(self, user_id: int) -> Dict[str, Any]:
        """Process verified purchase records into statistical aggregates."""
        # 1. Fetch strictly eligible, verified purchases
        raw_items = PurchaseHistoryService.get_eligible_purchases_for_user(user_id)

        if not raw_items:
            return self._empty_summary(user_id)

        # 2. Basic counters & aggregates
        total_items_count = 0
        total_spent = 0.0
        unique_orders: set = set()
        product_counter: Dict[str, Dict[str, Any]] = {}
        category_counts: Counter = Counter()
        category_spend: Dict[str, float] = defaultdict(float)
        brand_counts: Counter = Counter()
        brand_spend: Dict[str, float] = defaultdict(float)
        monthly_spend: Dict[str, float] = defaultdict(float)
        monthly_orders: Dict[str, set] = defaultdict(set)

        for item in raw_items:
            qty = max(1, int(item.get("quantity") or 1))
            price = float(item.get("price") or 0.0)
            item_total = price * qty
            total_items_count += qty
            total_spent += item_total

            ord_id = item.get("order_id") or item.get("order_number") or item.get("id")
            if ord_id:
                unique_orders.add(str(ord_id))

            pname = (item.get("product_name") or "Unknown Product").strip()
            cat = (item.get("category") or "General").strip()
            brand = (item.get("brand") or "Generic").strip()
            pdate = str(item.get("purchase_date") or "")[:10]

            # Category & Brand aggregations
            category_counts[cat] += qty
            category_spend[cat] += item_total
            if brand and brand.lower() != "generic":
                brand_counts[brand] += qty
                brand_spend[brand] += item_total

            # Monthly trends
            month_key = pdate[:7] if len(pdate) >= 7 else "Recent"
            monthly_spend[month_key] += item_total
            if ord_id:
                monthly_orders[month_key].add(str(ord_id))

            # Frequently purchased tracking
            if pname not in product_counter:
                product_counter[pname] = {
                    "product_name": pname,
                    "product_id": item.get("product_id"),
                    "category": cat,
                    "brand": brand,
                    "total_quantity": 0,
                    "order_appearances": 0,
                    "total_spent": 0.0,
                    "avg_price": price,
                    "purchase_dates": [],
                    "latest_purchase_date": pdate,
                }
            product_counter[pname]["total_quantity"] += qty
            product_counter[pname]["order_appearances"] += 1
            product_counter[pname]["total_spent"] += item_total
            if pdate:
                product_counter[pname]["purchase_dates"].append(pdate)
                if not product_counter[pname]["latest_purchase_date"] or pdate > product_counter[pname]["latest_purchase_date"]:
                    product_counter[pname]["latest_purchase_date"] = pdate

        # 3. Calculate averages
        total_orders_count = len(unique_orders) if unique_orders else (1 if raw_items else 0)
        aov = round(total_spent / total_orders_count, 2) if total_orders_count > 0 else 0.0
        avg_item_price = round(total_spent / total_items_count, 2) if total_items_count > 0 else 0.0

        # 4. Format Frequently Purchased
        frequently_purchased = []
        for p in product_counter.values():
            if p["total_quantity"] > 0:
                p["avg_price"] = round(p["total_spent"] / p["total_quantity"], 2)
                frequently_purchased.append(p)
        # Sort by total quantity and repeat purchase frequency
        frequently_purchased.sort(key=lambda x: (x["order_appearances"], x["total_quantity"]), reverse=True)

        # 5. Format Category Breakdown
        category_breakdown = []
        for cat, count in category_counts.most_common():
            spend = category_spend[cat]
            pct = round((spend / total_spent) * 100, 1) if total_spent > 0 else 0.0
            category_breakdown.append({
                "category": cat,
                "item_count": count,
                "spend": round(spend, 2),
                "spend_percentage": pct,
            })

        # 6. Format Brand Breakdown
        brand_breakdown = []
        for br, count in brand_counts.most_common(10):
            spend = brand_spend[br]
            brand_breakdown.append({
                "brand": br,
                "item_count": count,
                "spend": round(spend, 2),
            })

        # 7. Format Monthly Trends
        spending_trends = []
        for m_key in sorted(monthly_spend.keys(), reverse=True):
            spending_trends.append({
                "month": m_key,
                "spend": round(monthly_spend[m_key], 2),
                "orders_count": len(monthly_orders[m_key]),
            })

        # 8. Recent Items (last 15 items)
        recent_purchases = []
        for item in raw_items[:15]:
            recent_purchases.append({
                "id": item.get("id"),
                "order_id": item.get("order_id"),
                "order_number": item.get("order_number"),
                "product_id": item.get("product_id"),
                "product_name": item.get("product_name"),
                "category": item.get("category"),
                "brand": item.get("brand"),
                "price": float(item.get("price") or 0.0),
                "quantity": int(item.get("quantity") or 1),
                "purchase_date": str(item.get("purchase_date") or ""),
                "payment_method": item.get("payment_method"),
                "payment_status": item.get("payment_status"),
                "fulfillment_status": item.get("fulfillment_status") or item.get("order_status"),
            })

        return {
            "user_id": user_id,
            "has_purchase_history": True,
            "total_orders": total_orders_count,
            "total_items_count": total_items_count,
            "total_spent": round(total_spent, 2),
            "average_order_value": aov,
            "average_item_price": avg_item_price,
            "top_category": category_breakdown[0]["category"] if category_breakdown else "General",
            "category_breakdown": category_breakdown,
            "brand_breakdown": brand_breakdown,
            "frequently_purchased": frequently_purchased,
            "spending_trends": spending_trends,
            "recent_purchases": recent_purchases,
            "summary_text": (
                f"{total_orders_count} verified orders ({total_items_count} items) totaling "
                f"Rs {total_spent:,.2f} with average basket of Rs {aov:,.2f}."
            ),
        }

    def _empty_summary(self, user_id: int, error: str = "") -> Dict[str, Any]:
        """Zero-state representation when user has no verified purchase history."""
        return {
            "user_id": user_id,
            "has_purchase_history": False,
            "total_orders": 0,
            "total_items_count": 0,
            "total_spent": 0.0,
            "average_order_value": 0.0,
            "average_item_price": 0.0,
            "top_category": None,
            "category_breakdown": [],
            "brand_breakdown": [],
            "frequently_purchased": [],
            "spending_trends": [],
            "recent_purchases": [],
            "summary_text": "No completed purchase history yet. Start shopping to train your Digital Twin!",
            "error": error if error else None,
        }
