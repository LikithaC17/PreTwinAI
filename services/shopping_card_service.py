"""
services/shopping_card_service.py
==================================
PreTwin AI - Smart Shopping Card Service
Feature: Smart Shopping Card (Feature 6)

Provides comprehensive, accurate, customer-isolated data aggregation
across the seven dedicated sections of the PreTwin AI Smart Shopping Card:
1. My Smart Shopping Identity
2. My Shopping Overview
3. My Rewards and Benefits (5 pts/purchase, 100 pts = ₹1.00)
4. My Budget and Savings Snapshot
5. My Orders and Shopping Activity
6. My Personalised Shopping Insights
7. Quick Actions and Card Management
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import database

logger = logging.getLogger(__name__)


class ShoppingCardService:
    """Service providing data and business logic for the PreTwin AI Smart Shopping Card."""

    POINTS_PER_ORDER = 5
    POINTS_PER_RUPEE = 100.0  # 100 points = ₹1.00

    @classmethod
    def get_full_card_data(cls, user_id: int) -> Dict[str, Any]:
        """Aggregate all seven sections of the Smart Shopping Card for authenticated user."""
        if not user_id or user_id <= 0:
            raise ValueError("Valid authenticated user_id is required")

        identity = cls.get_shopping_identity(user_id)
        overview = cls.get_shopping_overview(user_id)
        rewards = cls.get_rewards_benefits(user_id)
        budget_savings = cls.get_budget_savings_snapshot(user_id)
        orders = cls.get_orders_activity(user_id)
        insights = cls.get_personalised_insights(user_id)
        quick_actions = cls.get_quick_actions(user_id)

        return {
            "success": True,
            "user_id": user_id,
            "generated_at": datetime.utcnow().isoformat(),
            "identity": identity,
            "overview": overview,
            "rewards": rewards,
            "budget_savings": budget_savings,
            "orders": orders,
            "insights": insights,
            "quick_actions": quick_actions
        }

    # =========================================================================
    # SECTION 1: MY SMART SHOPPING IDENTITY
    # =========================================================================
    @classmethod
    def get_shopping_identity(cls, user_id: int) -> Dict[str, Any]:
        """Fetch customer profile, masked identifier, member since date, and shopping persona."""
        user_row = None
        try:
            user_row = database.query_db(
                "SELECT id, username, email, created_at, avatar_url, city, state FROM users WHERE id = ?",
                (user_id,),
                one=True
            )
        except Exception as e:
            logger.debug(f"User profile query exception: {e}")

        username = "PreTwin Shopper"
        email = ""
        avatar_url = None
        created_at_str = ""
        member_since = "Member"
        city = ""
        state = ""

        if user_row:
            username = user_row["username"] or "PreTwin Shopper"
            email = user_row["email"] or ""
            raw_avatar = user_row["avatar_url"]
            if raw_avatar and str(raw_avatar).strip():
                avatar_url = str(raw_avatar).strip()
            else:
                avatar_url = None

            raw_created = user_row["created_at"]
            if raw_created:
                try:
                    dt = datetime.strptime(str(raw_created).split(".")[0], "%Y-%m-%d %H:%M:%S")
                    member_since = dt.strftime("%B %Y")
                    created_at_str = dt.strftime("%d %b %Y")
                except Exception:
                    member_since = str(raw_created)[:10]
                    created_at_str = str(raw_created)[:10]
            city = user_row["city"] or ""
            state = user_row["state"] or ""

        # Safe customer identifier e.g. #PRE-10001
        account_identifier = f"#PRE-{10000 + int(user_id)}"

        # Initial monogram fallback
        name_parts = username.strip().split()
        if len(name_parts) >= 2:
            monogram = f"{name_parts[0][0]}{name_parts[1][0]}".upper()
        elif len(name_parts) == 1 and name_parts[0]:
            monogram = name_parts[0][:2].upper()
        else:
            monogram = "PT"

        # Shopping preferences (categories, brands, styles)
        categories: List[str] = []
        brands: List[str] = []
        styles: List[str] = []
        spending_tier = "Moderate"
        shopping_frequency = "Regular"

        try:
            pref_row = database.query_db(
                """SELECT preferred_categories, preferred_brands, preferred_styles,
                          spending_tier, shopping_frequency, budget_max
                   FROM shopping_preferences WHERE user_id = ?""",
                (user_id,),
                one=True
            )
            if pref_row:
                categories = cls._parse_list_field(pref_row["preferred_categories"])
                brands = cls._parse_list_field(pref_row["preferred_brands"])
                styles = cls._parse_list_field(pref_row["preferred_styles"])
                spending_tier = pref_row["spending_tier"] or "Moderate"
                shopping_frequency = pref_row["shopping_frequency"] or "Regular"
        except Exception as e:
            logger.debug(f"Shopping preferences query exception: {e}")

        # Check twin profile personality if present in household_profiles
        try:
            twin_row = database.query_db(
                "SELECT shopping_personality FROM household_profiles WHERE user_id = ? AND is_active = 1 LIMIT 1",
                (user_id,),
                one=True
            )
            personality = (twin_row["shopping_personality"] if twin_row and twin_row["shopping_personality"]
                           else "Practical Smart Shopper")
        except Exception:
            personality = "Practical Smart Shopper"

        card_status = "Active Verified Member"
        card_tier = "PreTwin Gold" if spending_tier.lower() == "premium" else "PreTwin Classic"

        return {
            "user_id": user_id,
            "display_name": username,
            "masked_account_id": account_identifier,
            "avatar_url": avatar_url,
            "monogram": monogram,
            "member_since": member_since,
            "created_at_formatted": created_at_str,
            "card_status": card_status,
            "card_tier": card_tier,
            "card_branding": "PreTwin AI Smart Shopping Card",
            "tagline": "Your Future. Your Style. Your Twin.",
            "shopping_personality": personality,
            "spending_tier": spending_tier,
            "shopping_frequency": shopping_frequency,
            "preferred_categories": categories,
            "preferred_brands": brands,
            "preferred_styles": styles,
            "city": city,
            "state": state,
            "edit_profile_url": "/twin"
        }

    # =========================================================================
    # SECTION 2: MY SHOPPING OVERVIEW
    # =========================================================================
    @classmethod
    def get_shopping_overview(cls, user_id: int) -> Dict[str, Any]:
        """Calculate counts for eligible completed purchases, active shipments, wishlist, and cart."""
        completed_count = 0
        active_count = 0
        cancelled_count = 0
        total_completed_spent = 0.0

        try:
            order_rows = database.query_db(
                "SELECT status, total_amount FROM orders WHERE user_id = ?",
                (user_id,)
            ) or []
            for row in order_rows:
                st = (row["status"] or "").strip().lower()
                amt = float(row["total_amount"] or 0.0)
                if st in ("delivered", "completed"):
                    completed_count += 1
                    total_completed_spent += amt
                elif st in ("confirmed", "placed", "processing", "shipped", "in_transit", "out_for_delivery"):
                    active_count += 1
                elif st in ("cancelled", "returned", "refunded", "failed"):
                    cancelled_count += 1
        except Exception as e:
            logger.debug(f"Orders overview query exception: {e}")

        # Wishlist count
        wishlist_count = 0
        try:
            wish_row = database.query_db(
                "SELECT COUNT(*) AS c FROM wishlist_items WHERE user_id = ?",
                (user_id,),
                one=True
            )
            wishlist_count = int(wish_row["c"]) if wish_row else 0
        except Exception:
            wishlist_count = 0

        # Cart count
        cart_quantity = 0
        cart_unique_items = 0
        try:
            cart_row = database.query_db(
                "SELECT COALESCE(SUM(quantity), 0) AS q_sum, COUNT(*) AS item_cnt FROM cart_items WHERE user_id = ?",
                (user_id,),
                one=True
            )
            cart_quantity = int(cart_row["q_sum"]) if cart_row and cart_row["q_sum"] else 0
            cart_unique_items = int(cart_row["item_cnt"]) if cart_row else 0
        except Exception:
            cart_quantity = 0
            cart_unique_items = 0

        # Activity summary string
        if completed_count == 0 and active_count == 0:
            summary_text = "No shopping history yet. Start exploring smart product discoveries."
        else:
            summary_text = f"{completed_count} completed orders · {active_count} active orders · {wishlist_count} saved items"

        return {
            "completed_orders_count": completed_count,
            "active_orders_count": active_count,
            "cancelled_orders_count": cancelled_count,
            "total_completed_spent": round(total_completed_spent, 2),
            "total_completed_spent_formatted": f"₹{round(total_completed_spent, 2):,.2f}",
            "wishlist_count": wishlist_count,
            "cart_count": cart_quantity,
            "cart_unique_items": cart_unique_items,
            "summary_text": summary_text,
            "links": {
                "orders": "/orders",
                "wishlist": "/wishlist",
                "cart": "/cart",
                "catalog": "/discovery"
            }
        }

    # =========================================================================
    # SECTION 3: MY REWARDS AND BENEFITS
    # =========================================================================
    @classmethod
    def get_rewards_benefits(cls, user_id: int) -> Dict[str, Any]:
        """Fetch rewards points under PreTwin rules: 5 pts per purchase, 100 pts = ₹1.00."""
        balance_points = 0
        lifetime_earned = 0
        lifetime_redeemed = 0
        transactions = []

        try:
            bal_row = database.query_db(
                "SELECT COALESCE(SUM(points), 0) AS balance FROM reward_ledger WHERE user_id = ?",
                (user_id,),
                one=True
            )
            balance_points = int(bal_row["balance"]) if bal_row else 0

            earned_row = database.query_db(
                "SELECT COALESCE(SUM(points), 0) AS earned FROM reward_ledger WHERE user_id = ? AND points > 0",
                (user_id,),
                one=True
            )
            lifetime_earned = int(earned_row["earned"]) if earned_row else 0

            redeemed_row = database.query_db(
                "SELECT COALESCE(SUM(points), 0) AS redeemed FROM reward_ledger WHERE user_id = ? AND points < 0",
                (user_id,),
                one=True
            )
            lifetime_redeemed = abs(int(redeemed_row["redeemed"])) if redeemed_row else 0

            tx_rows = database.query_db(
                """SELECT id, points, rupee_value, transaction_type, description, created_at
                   FROM reward_ledger WHERE user_id = ?
                   ORDER BY id DESC LIMIT 5""",
                (user_id,)
            ) or []
            for r in tx_rows:
                raw_date = str(r["created_at"])[:16]
                pts = int(r["points"])
                transactions.append({
                    "id": r["id"],
                    "points": pts,
                    "points_formatted": f"+{pts}" if pts > 0 else f"{pts}",
                    "rupee_value": round(float(r["rupee_value"] or (abs(pts) / cls.POINTS_PER_RUPEE)), 2),
                    "transaction_type": r["transaction_type"],
                    "description": r["description"] or "PreTwin Shopping Reward",
                    "date": raw_date
                })
        except Exception as e:
            logger.debug(f"Reward ledger query exception: {e}")

        rupee_value = round(balance_points / cls.POINTS_PER_RUPEE, 2)

        benefits = [
            {"title": "Instant Checkout Credits", "description": "Redeem 100 points for ₹1 discount at cart & checkout"},
            {"title": "Automatic Purchase Rewards", "description": "Earn 5 points automatically on every completed purchase"},
            {"title": "Predictive Deal Access", "description": "Priority price-drop notifications on wishlist and replenishment items"}
        ]

        return {
            "balance_points": balance_points,
            "balance_points_formatted": f"{balance_points:,}",
            "rupee_value": rupee_value,
            "rupee_value_formatted": f"₹{rupee_value:,.2f}",
            "points_ratio": "100 points = ₹1.00",
            "points_per_order": cls.POINTS_PER_ORDER,
            "lifetime_earned": lifetime_earned,
            "lifetime_earned_formatted": f"{lifetime_earned:,}",
            "lifetime_redeemed": lifetime_redeemed,
            "lifetime_redeemed_formatted": f"{lifetime_redeemed:,}",
            "recent_transactions": transactions,
            "benefits": benefits,
            "rewards_page_url": "/rewards"
        }

    # =========================================================================
    # SECTION 4: MY BUDGET AND SAVINGS SNAPSHOT
    # =========================================================================
    @classmethod
    def get_budget_savings_snapshot(cls, user_id: int) -> Dict[str, Any]:
        """Aggregate monthly shopping budget utilization and active savings plans."""
        overall_budget = None
        budget_configured = False
        budget_period = "monthly"

        # 1. Budget record
        try:
            budget_row = database.query_db(
                "SELECT * FROM customer_budgets WHERE user_id = ? ORDER BY id DESC LIMIT 1",
                (user_id,),
                one=True
            )
            if budget_row and budget_row["overall_budget"] is not None and float(budget_row["overall_budget"]) > 0:
                overall_budget = float(budget_row["overall_budget"])
                budget_configured = True
                budget_period = budget_row["budget_period"] or "monthly"
        except Exception:
            budget_row = None

        if not budget_configured:
            try:
                pref_row = database.query_db(
                    "SELECT budget_max FROM shopping_preferences WHERE user_id = ?",
                    (user_id,),
                    one=True
                )
                if pref_row and pref_row["budget_max"] and float(pref_row["budget_max"]) > 0:
                    overall_budget = float(pref_row["budget_max"])
                    budget_configured = True
            except Exception:
                pass

        # Current month spent
        now = datetime.now()
        month_prefix = now.strftime("%Y-%m")
        current_spent = 0.0
        try:
            spent_row = database.query_db(
                """SELECT COALESCE(SUM(total_amount), 0) AS month_spent
                   FROM orders
                   WHERE user_id = ?
                     AND strftime('%Y-%m', created_at) = ?
                     AND LOWER(status) NOT IN ('cancelled', 'returned', 'refunded', 'failed')""",
                (user_id, month_prefix),
                one=True
            )
            current_spent = float(spent_row["month_spent"]) if spent_row else 0.0
        except Exception:
            current_spent = 0.0

        if budget_configured and overall_budget and overall_budget > 0:
            remaining = max(0.0, round(overall_budget - current_spent, 2))
            utilization_pct = min(100.0, round((current_spent / overall_budget) * 100.0, 1))
            if utilization_pct >= 100.0:
                budget_status = "Exceeded Limit"
                status_color = "#EF4444"
            elif utilization_pct >= 80.0:
                budget_status = "Nearing Budget Limit"
                status_color = "#F59E0B"
            else:
                budget_status = "Within Budget"
                status_color = "#10B981"
        else:
            remaining = 0.0
            utilization_pct = 0.0
            budget_status = "Unconfigured"
            status_color = "#81778E"

        # 2. Savings plans
        savings_goals = []
        try:
            plans_rows = database.query_db(
                """SELECT id, goal_title, target_amount, current_saved, target_date, status
                   FROM savings_plans WHERE user_id = ?
                   ORDER BY id DESC LIMIT 5""",
                (user_id,)
            ) or []
            for sp in plans_rows:
                target = float(sp["target_amount"] or 1.0)
                saved = float(sp["current_saved"] or 0.0)
                pct = min(100.0, round((saved / target) * 100.0, 1)) if target > 0 else 0.0
                savings_goals.append({
                    "id": sp["id"],
                    "goal_title": sp["goal_title"] or "Shopping Savings Goal",
                    "target_amount": round(target, 2),
                    "target_amount_formatted": f"₹{round(target, 2):,.2f}",
                    "current_saved": round(saved, 2),
                    "current_saved_formatted": f"₹{round(saved, 2):,.2f}",
                    "progress_pct": pct,
                    "target_date": str(sp["target_date"] or ""),
                    "status": sp["status"] or "active"
                })
        except Exception:
            savings_goals = []

        # Available reward value
        reward_pts = 0
        try:
            bal_row = database.query_db(
                "SELECT COALESCE(SUM(points), 0) AS balance FROM reward_ledger WHERE user_id = ?",
                (user_id,),
                one=True
            )
            reward_pts = int(bal_row["balance"]) if bal_row else 0
        except Exception:
            reward_pts = 0
        reward_rupees = round(reward_pts / cls.POINTS_PER_RUPEE, 2)

        return {
            "budget_configured": budget_configured,
            "overall_budget": round(overall_budget, 2) if overall_budget else 0.0,
            "overall_budget_formatted": f"₹{round(overall_budget, 2):,.2f}" if overall_budget else "Not Set",
            "current_spent": round(current_spent, 2),
            "current_spent_formatted": f"₹{round(current_spent, 2):,.2f}",
            "remaining_budget": remaining,
            "remaining_budget_formatted": f"₹{remaining:,.2f}" if budget_configured else "—",
            "utilization_pct": utilization_pct,
            "budget_status": budget_status,
            "status_color": status_color,
            "budget_period": budget_period,
            "unconfigured_message": "No monthly budget configured yet. Configure one in Budget Intelligence to stay on track." if not budget_configured else "",
            "active_savings_goals": savings_goals,
            "has_savings_goals": len(savings_goals) > 0,
            "available_reward_value": reward_rupees,
            "available_reward_value_formatted": f"₹{reward_rupees:,.2f}",
            "links": {
                "budget": "/budget",
                "savings": "/savings"
            }
        }

    # =========================================================================
    # SECTION 5: MY ORDERS AND SHOPPING ACTIVITY
    # =========================================================================
    @classmethod
    def get_orders_activity(cls, user_id: int) -> Dict[str, Any]:
        """Fetch active orders, recently completed orders, with items summary and tracking links."""
        active_orders = []
        recent_completed = []
        completed_cnt = 0
        active_cnt = 0
        cancelled_cnt = 0

        try:
            active_rows = database.query_db(
                """SELECT id, order_number, total_amount, status, payment_status, payment_method, created_at
                   FROM orders
                   WHERE user_id = ?
                     AND LOWER(status) IN ('confirmed', 'placed', 'processing', 'shipped', 'in_transit', 'out_for_delivery')
                   ORDER BY id DESC LIMIT 5""",
                (user_id,)
            ) or []
            for r in active_rows:
                order_id = r["id"]
                items_summary = cls._get_order_items_summary(order_id)
                pay_st = "Paid"
                try:
                    pay_st = r["payment_status"] or "Paid"
                except Exception:
                    pay_st = "Paid"
                active_orders.append({
                    "id": order_id,
                    "order_number": r["order_number"] or f"#ORD-{order_id}",
                    "total_amount": round(float(r["total_amount"] or 0.0), 2),
                    "total_amount_formatted": f"₹{round(float(r['total_amount'] or 0.0), 2):,.2f}",
                    "status": r["status"],
                    "payment_status": pay_st,
                    "created_at_formatted": str(r["created_at"])[:16],
                    "items_summary": items_summary,
                    "tracking_url": f"/orders#order-{order_id}"
                })

            completed_rows = database.query_db(
                """SELECT id, order_number, total_amount, status, created_at
                   FROM orders
                   WHERE user_id = ?
                     AND LOWER(status) IN ('delivered', 'completed')
                   ORDER BY id DESC LIMIT 5""",
                (user_id,)
            ) or []
            for r in completed_rows:
                order_id = r["id"]
                items_summary = cls._get_order_items_summary(order_id)
                recent_completed.append({
                    "id": order_id,
                    "order_number": r["order_number"] or f"#ORD-{order_id}",
                    "total_amount": round(float(r["total_amount"] or 0.0), 2),
                    "total_amount_formatted": f"₹{round(float(r['total_amount'] or 0.0), 2):,.2f}",
                    "status": r["status"],
                    "created_at_formatted": str(r["created_at"])[:10],
                    "items_summary": items_summary,
                    "view_url": f"/orders#order-{order_id}"
                })

            cnt_row = database.query_db(
                """SELECT
                    COUNT(CASE WHEN LOWER(status) IN ('delivered', 'completed') THEN 1 END) AS completed_cnt,
                    COUNT(CASE WHEN LOWER(status) IN ('confirmed', 'placed', 'processing', 'shipped', 'in_transit', 'out_for_delivery') THEN 1 END) AS active_cnt,
                    COUNT(CASE WHEN LOWER(status) IN ('cancelled', 'returned', 'refunded', 'failed') THEN 1 END) AS cancelled_cnt
                   FROM orders WHERE user_id = ?""",
                (user_id,),
                one=True
            )
            if cnt_row:
                completed_cnt = int(cnt_row["completed_cnt"])
                active_cnt = int(cnt_row["active_cnt"])
                cancelled_cnt = int(cnt_row["cancelled_cnt"])
        except Exception as e:
            logger.debug(f"Orders activity query exception: {e}")

        return {
            "active_orders": active_orders,
            "has_active_orders": len(active_orders) > 0,
            "recently_completed_orders": recent_completed,
            "has_completed_orders": len(recent_completed) > 0,
            "completed_orders_total": completed_cnt,
            "active_orders_total": active_cnt,
            "cancelled_orders_total": cancelled_cnt,
            "orders_url": "/orders"
        }

    @classmethod
    def _get_order_items_summary(cls, order_id: int) -> str:
        """Helper to get a concise text summary of items in an order."""
        try:
            items = database.query_db(
                "SELECT product_name, quantity FROM order_items WHERE order_id = ? LIMIT 3",
                (order_id,)
            ) or []
            if not items:
                return "General Purchase"
            names = [f"{it['product_name']} (x{it['quantity']})" for it in items]
            summary = ", ".join(names)
            if len(items) == 3:
                summary += "..."
            return summary
        except Exception:
            return "General Purchase"

    # =========================================================================
    # SECTION 6: MY PERSONALISED SHOPPING INSIGHTS
    # =========================================================================
    @classmethod
    def get_personalised_insights(cls, user_id: int) -> Dict[str, Any]:
        """Aggregate concise intelligence nuggets from Twin, Predictions, Calendar, and Budget."""
        insights: List[Dict[str, Any]] = []

        # 1. Twin Profile Insight
        try:
            pref_row = database.query_db(
                "SELECT preferred_categories, spending_tier FROM shopping_preferences WHERE user_id = ?",
                (user_id,),
                one=True
            )
            twin_row = database.query_db(
                "SELECT shopping_personality FROM household_profiles WHERE user_id = ? AND is_active = 1 LIMIT 1",
                (user_id,),
                one=True
            )
            personality = (twin_row["shopping_personality"] if twin_row and twin_row["shopping_personality"]
                           else "Practical Smart Shopper")
            cats = cls._parse_list_field(pref_row["preferred_categories"]) if pref_row else []
            cat_str = ", ".join(cats[:2]) if cats else "Curated Essentials"
            insights.append({
                "type": "twin_identity",
                "title": "Digital Twin Shopping Persona",
                "message": f"Your Twin categorizes you as a '{personality}' with primary affinity for {cat_str}.",
                "source": "Feature 1: Personalization and Digital Twin",
                "badge": "Twin Persona",
                "link": "/twin",
                "action_text": "Explore Digital Twin"
            })
        except Exception:
            insights.append({
                "type": "twin_identity",
                "title": "Digital Twin Shopping Persona",
                "message": "Your Shopping Twin identity adapts to your shopping preferences.",
                "source": "Feature 1: Personalization and Digital Twin",
                "badge": "Twin Persona",
                "link": "/twin",
                "action_text": "Explore Digital Twin"
            })

        # 2. Predictive Replenishment Insight
        try:
            reminder_row = database.query_db(
                """SELECT title, category, next_reminder_date
                   FROM shopping_reminders
                   WHERE user_id = ? AND status = 'active'
                   ORDER BY next_reminder_date ASC LIMIT 1""",
                (user_id,),
                one=True
            )
            if reminder_row:
                rem_title = reminder_row["title"]
                rem_date = reminder_row["next_reminder_date"]
                insights.append({
                    "type": "predictive_need",
                    "title": "Upcoming Shopping Prediction",
                    "message": f"Replenishment suggested for '{rem_title}' around {rem_date}.",
                    "source": "Feature 2: Predictive Shopping Intelligence",
                    "badge": "Predicted Need",
                    "link": "/predictions",
                    "action_text": "Review Predictions"
                })
            else:
                insights.append({
                    "type": "predictive_need",
                    "title": "Shopping Rhythm Up to Date",
                    "message": "All predicted replenishment cycles are current. No urgent items forecasted.",
                    "source": "Feature 2: Predictive Shopping Intelligence",
                    "badge": "On Schedule",
                    "link": "/predictions",
                    "action_text": "View Prediction Timeline"
                })
        except Exception:
            insights.append({
                "type": "predictive_need",
                "title": "Shopping Rhythm Up to Date",
                "message": "All predicted replenishment cycles are current. No urgent items forecasted.",
                "source": "Feature 2: Predictive Shopping Intelligence",
                "badge": "On Schedule",
                "link": "/predictions",
                "action_text": "View Prediction Timeline"
            })

        # 3. Calendar Milestone Insight
        try:
            cal_row = database.query_db(
                """SELECT title, event_date, budget
                   FROM shopping_calendar_events
                   WHERE user_id = ? AND event_date >= date('now')
                   ORDER BY event_date ASC LIMIT 1""",
                (user_id,),
                one=True
            )
            if cal_row:
                cal_title = cal_row["title"]
                cal_date = cal_row["event_date"]
                cal_budget = float(cal_row["budget"] or 0.0)
                budget_txt = f" with ₹{cal_budget:,.2f} reserved" if cal_budget > 0 else ""
                insights.append({
                    "type": "calendar_milestone",
                    "title": "Upcoming Calendar Milestone",
                    "message": f"Upcoming event: '{cal_title}' on {cal_date}{budget_txt}.",
                    "source": "Feature 6: Future Predictive Calendar",
                    "badge": "Calendar Event",
                    "link": "/calendar",
                    "action_text": "Open Shopping Calendar"
                })
            else:
                insights.append({
                    "type": "calendar_milestone",
                    "title": "Calendar Ready for Planning",
                    "message": "No scheduled milestones this month. Plan seasonal purchases to lock in price savings.",
                    "source": "Feature 6: Future Predictive Calendar",
                    "badge": "Shopping Planner",
                    "link": "/calendar",
                    "action_text": "Plan Future Occasions"
                })
        except Exception:
            insights.append({
                "type": "calendar_milestone",
                "title": "Calendar Ready for Planning",
                "message": "No scheduled milestones this month. Plan seasonal purchases to lock in price savings.",
                "source": "Feature 6: Future Predictive Calendar",
                "badge": "Shopping Planner",
                "link": "/calendar",
                "action_text": "Plan Future Occasions"
            })

        # 4. Budget & Savings Insight
        try:
            b_row = database.query_db(
                "SELECT overall_budget FROM customer_budgets WHERE user_id = ? ORDER BY id DESC LIMIT 1",
                (user_id,),
                one=True
            )
            if b_row and b_row["overall_budget"] and float(b_row["overall_budget"]) > 0:
                insights.append({
                    "type": "budget_status",
                    "title": "Active Budget Tracking",
                    "message": f"Monthly shopping allocation of ₹{float(b_row['overall_budget']):,.2f} is actively tracked.",
                    "source": "Feature 4: Budget & Price Intelligence",
                    "badge": "Budget Guard",
                    "link": "/budget",
                    "action_text": "Inspect Budget Details"
                })
            else:
                insights.append({
                    "type": "budget_status",
                    "title": "Set a Monthly Spending Budget",
                    "message": "Configure monthly category caps in Budget Intelligence to receive real-time savings alerts.",
                    "source": "Feature 4: Budget & Price Intelligence",
                    "badge": "Smart Advice",
                    "link": "/budget",
                    "action_text": "Configure Budget"
                })
        except Exception:
            insights.append({
                "type": "budget_status",
                "title": "Set a Monthly Spending Budget",
                "message": "Configure monthly category caps in Budget Intelligence to receive real-time savings alerts.",
                "source": "Feature 4: Budget & Price Intelligence",
                "badge": "Smart Advice",
                "link": "/budget",
                "action_text": "Configure Budget"
            })

        return {
            "insights": insights,
            "total_insights": len(insights)
        }

    # =========================================================================
    # SECTION 7: QUICK ACTIONS AND CARD MANAGEMENT
    # =========================================================================
    @classmethod
    def get_quick_actions(cls, user_id: int) -> Dict[str, Any]:
        """Provide verified navigation shortcuts and card management utilities."""
        navigation_shortcuts = [
            {"label": "View My Profile", "icon": "bi-person-circle", "url": "/profile", "description": "Manage account & delivery addresses"},
            {"label": "Browse Products", "icon": "bi-search", "url": "/discovery", "description": "AI-powered product discovery & search"},
            {"label": "Open Wishlist", "icon": "bi-heart", "url": "/wishlist", "description": "Saved products & price drop alerts"},
            {"label": "View Shopping Cart", "icon": "bi-cart3", "url": "/cart", "description": "Current shopping basket & checkout"},
            {"label": "View My Orders", "icon": "bi-box-seam", "url": "/orders", "description": "Order history, status & tracking"},
            {"label": "Check Rewards", "icon": "bi-gem", "url": "/rewards", "description": "PreTwin reward points & discount credits"},
            {"label": "Budget Intelligence", "icon": "bi-pie-chart", "url": "/budget", "description": "Monthly spending ceilings & category caps"},
            {"label": "Shopping Calendar", "icon": "bi-calendar3", "url": "/calendar", "description": "Predictive occasions & future milestones"},
            {"label": "Manage Twin Preferences", "icon": "bi-sliders", "url": "/twin", "description": "Update shopping style, brands & categories"}
        ]

        card_management_actions = [
            {"action": "refresh", "label": "Refresh Card", "icon": "bi-arrow-clockwise", "endpoint": "/api/shopping-card/refresh"},
            {"action": "print", "label": "Print Card", "icon": "bi-printer", "endpoint": "javascript:window.print()"},
            {"action": "download", "label": "Download Card", "icon": "bi-download", "endpoint": "#download-card"},
            {"action": "share", "label": "Privacy-Safe Share", "icon": "bi-share", "endpoint": "#share-card"}
        ]

        # Privacy-safe card export snippet
        display_name = "PreTwin Shopper"
        try:
            user_row = database.query_db("SELECT username FROM users WHERE id = ?", (user_id,), one=True)
            if user_row and user_row["username"]:
                display_name = user_row["username"]
        except Exception:
            pass

        masked_id = f"#PRE-{10000 + int(user_id)}"
        safe_export_text = (
            f"PreTwin AI Smart Shopping Card\n"
            f"Member: {display_name}\n"
            f"Card ID: {masked_id}\n"
            f"Status: Verified Member\n"
            f"Tagline: Your Future. Your Style. Your Twin.\n"
            f"Visit: https://pretwinshop.ai"
        )

        return {
            "navigation_shortcuts": navigation_shortcuts,
            "card_management_actions": card_management_actions,
            "safe_export_text": safe_export_text
        }

    # =========================================================================
    # HELPERS
    # =========================================================================
    @staticmethod
    def _parse_list_field(field_val: Any) -> List[str]:
        """Safely parse comma-separated or JSON string into clean list of strings."""
        if not field_val:
            return []
        if isinstance(field_val, list):
            return [str(x).strip() for x in field_val if str(x).strip()]
        s = str(field_val).strip()
        if not s:
            return []
        if s.startswith("[") and s.endswith("]"):
            try:
                parsed = json.loads(s)
                if isinstance(parsed, list):
                    return [str(x).strip() for x in parsed if str(x).strip()]
            except Exception:
                pass
        return [p.strip() for p in s.split(",") if p.strip()]
