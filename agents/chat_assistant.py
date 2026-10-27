# -*- coding: utf-8 -*-
"""
agents/chat_assistant.py
PreTwin AI Shopping Chatbot Engine.
Provides natural language shopping assistance, product discovery, budget recommendations,
twin insights, savings plan guidance, rewards point lookups, COD information, and order tracking.
Uses OpenAI API when Config.USE_LLM and key available; otherwise operates on a robust,
deterministic, SQLite-backed local conversational AI engine.
"""

import os
import re
import json
import sqlite3
from typing import Dict, Any, List
from config import Config
import database

class PreTwinChatAssistant:
    def __init__(self):
        self.use_llm = Config.USE_LLM and bool(Config.OPENAI_API_KEY)
        self.model = Config.OPENAI_MODEL

    def handle_message(self, message: str, user_id: int = 1, session_id: str = "default") -> Dict[str, Any]:
        """Alias for process_message."""
        return self.process_message(message, user_id=user_id, session_id=session_id)

    def process_message(self, message: str, user_id: int = 1, session_id: str = "default") -> Dict[str, Any]:
        """
        Main entry point for processing user chat message.
        Returns a dict with 'reply', 'intent', 'products', 'suggestions', 'meta'.
        """
        msg_clean = message.strip()
        msg_lower = msg_clean.lower()

        # Gather user context
        user_info = None
        user_row = database.query_db("SELECT id, username, email FROM users WHERE id = ?", (user_id,), one=True)
        if user_row:
            user_info = dict(user_row)

        # 1. Check for specific high-value shopping intents
        # Intent: Reward Points
        if any(w in msg_lower for w in ["reward", "points", "point balance", "rewards", "loyalty"]):
            return self._handle_reward_points(user_id)

        # Intent: Cash on Delivery / Payment Methods
        if any(w in msg_lower for w in ["cod", "cash on delivery", "pay on delivery", "payment method", "how to pay"]):
            return self._handle_cod_inquiry()

        # Intent: Wishlist
        if "wishlist" in msg_lower:
            return self._handle_wishlist_inquiry(user_id)

        # Intent: Savings Plan / Goal tracking
        if any(w in msg_lower for w in ["savings plan", "monthly goal", "how much saved", "deposit"]) or (
            any(w in msg_lower for w in ["save", "saving"]) and "wishlist" not in msg_lower
        ):
            return self._handle_savings_inquiry(msg_lower, user_id)

        # Intent: Calendar / Upcoming Event Prep
        if any(w in msg_lower for w in ["calendar", "college event", "upcoming event", "milestone", "semester", "need for my upcoming"]):
            return self._handle_calendar_inquiry(msg_lower, user_id)

        # Intent: Cheaper Alternatives
        if any(w in msg_lower for w in ["cheaper", "alternative", "cheaper alternative", "less expensive"]):
            return self._handle_cheaper_alternatives(msg_lower)

        # Intent: Order Status / Tracking / Cart
        if any(w in msg_lower for w in ["my order", "order status", "track order", "where is my order", "orders"]):
            return self._handle_order_status(user_id)

        if "cart" in msg_lower:
            return self._handle_cart_inquiry(user_id)

        # Intent: Shopping List / Bundle with budget
        if any(w in msg_lower for w in ["shopping list", "curate basket", "bundle"]) or ("budget" in msg_lower and "list" in msg_lower):
            return self._handle_budget_bundle_inquiry(msg_lower)

        # Intent: Gift
        if "gift" in msg_lower or "present" in msg_lower:
            return self._handle_gift_inquiry(msg_lower)

        # Intent: Predictions / Future Needs
        if any(w in msg_lower for w in ["predict", "prediction", "future need", "what should i buy", "next month", "upcoming"]):
            return self._handle_predictions_inquiry(user_id)

        # Intent: Digital Shopping Twin info / Profile
        if any(w in msg_lower for w in ["my twin", "shopping twin", "profile", "my preference", "twin info", "budget limit"]):
            return self._handle_twin_inquiry(user_id)

        # Intent: Comparison
        if "compare" in msg_lower:
            return self._handle_comparison_inquiry(msg_lower)

        # Intent: Recommendation explanation
        if "why" in msg_lower and any(w in msg_lower for w in ["recommend", "suggest", "picked", "chosen"]):
            return self._handle_explanation_inquiry(user_id)

        # Intent: Product Search / Discovery (price limits, categories, keywords)
        product_results = self._search_products_locally(msg_clean, msg_lower)
        if product_results:
            return product_results

        # Fallback / General Conversation
        if self.use_llm:
            try:
                import openai
                client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
                system_prompt = (
                    "You are PreTwin AI, a magical fairytale-inspired yet highly intelligent personal shopping twin. "
                    "You help users discover products from 20 marketplace categories, budget smartly, predict upcoming needs, "
                    "track 30-day Smart Savings Plans, and earn PreTwin Rewards (5 points per purchase; 100 points = ₹1). "
                    "PreTwin supports Cash on Delivery (COD) and fast delivery across India. Keep replies friendly, concise, and helpful."
                )
                resp = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": msg_clean}
                    ],
                    max_tokens=300,
                    temperature=0.7
                )
                reply_text = resp.choices[0].message.content.strip()
                return {
                    "reply": reply_text,
                    "intent": "general_llm",
                    "products": [],
                    "suggestions": ["Find phone under ₹20,000", "My reward points", "Smart Savings Plan", "Can I pay COD?"]
                }
            except Exception as e:
                print(f"[ChatAssistant LLM fallback]: {e}")

        # Intelligent default fallback
        return {
            "reply": (
                "✦ **Welcome to PreTwin AI!** I am your predictive shopping companion.\n\n"
                "I can help you with:\n"
                "• **Product Discovery**: Ask me e.g. *'Find phones under ₹20,000'* or *'Suggest running shoes under ₹1,500'*\n"
                "• **Future Needs Prediction**: Ask *'What should I buy next month?'*\n"
                "• **PreTwin Smart Savings Plan**: Ask *'Help me save ₹5,000 for a laptop'*\n"
                "• **PreTwin Rewards**: Ask *'How many reward points do I have?'* (100 points = ₹1)\n"
                "• **Payment & Orders**: Ask *'Can I pay Cash on Delivery?'* or *'Where is my order?'*"
            ),
            "intent": "welcome_fallback",
            "products": [],
            "suggestions": [
                "Find best phone under ₹20,000",
                "Suggest shoes under ₹1,500",
                "How many reward points do I have?",
                "PreTwin Smart Savings Plan",
                "Can I pay Cash on Delivery?"
            ]
        }

    def _extract_price_limit(self, text: str) -> float:
        """Extracts upper price limit from text like 'under 20000', 'under ₹1,500', 'below 5000'."""
        patterns = [
            r'(?:under|below|less than|within|upto|up to)\s*(?:₹|rs\.?|inr)?\s*([\d,]+)',
            r'(?:₹|rs\.?|inr)\s*([\d,]+)\s*(?:budget|or less)',
        ]
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                clean_num = m.group(1).replace(",", "")
                try:
                    return float(clean_num)
                except ValueError:
                    pass
        return 0.0

    def _search_products_locally(self, raw_msg: str, msg_lower: str) -> Dict[str, Any]:
        """Intelligent local search against 1,040 products table in pretwinshop.db."""
        price_limit = self._extract_price_limit(msg_lower)

        # Detect category or keywords
        categories_map = {
            "phone": "Mobiles", "mobile": "Mobiles", "smartphone": "Mobiles", "iphone": "Mobiles", "android": "Mobiles",
            "shoe": "Footwear", "shoes": "Footwear", "sneaker": "Footwear", "sneakers": "Footwear", "trainer": "Footwear", "heel": "Footwear", "boot": "Footwear",
            "laptop": "Laptops & Computers", "computer": "Laptops & Computers", "macbook": "Laptops & Computers", "monitor": "Laptops & Computers",
            "headphone": "Electronics", "earphone": "Electronics", "earbuds": "Electronics", "speaker": "Electronics", "camera": "Electronics", "mic": "Electronics",
            "tv": "TVs & Home Entertainment", "television": "TVs & Home Entertainment", "oled": "TVs & Home Entertainment",
            "shirt": "Fashion", "t-shirt": "Fashion", "jeans": "Fashion", "saree": "Fashion", "kurta": "Fashion", "dress": "Fashion",
            "watch": "Watches & Accessories", "smartwatch": "Watches & Accessories", "sunglasses": "Watches & Accessories",
            "perfume": "Beauty, Toys & More", "lipstick": "Beauty, Toys & More", "skincare": "Beauty, Toys & More",
            "cookware": "Home & Kitchen", "kettle": "Home & Kitchen", "knife": "Home & Kitchen",
            "refrigerator": "Appliances", "washing machine": "Appliances", "ac": "Appliances", "vacuum": "Appliances",
            "dumbbells": "Sports & Fitness", "yoga": "Sports & Fitness", "protein": "Sports & Fitness",
            "book": "Books & Stationery", "notebook": "Books & Stationery", "pen": "Books & Stationery",
            "chair": "Furniture", "table": "Furniture", "bed": "Furniture",
            "dog": "Pet Supplies", "cat": "Pet Supplies", "pet": "Pet Supplies",
            "luggage": "Travel & Luggage", "suitcase": "Travel & Luggage", "backpack": "Travel & Luggage",
            "bp monitor": "Health & Wellness", "vitamin": "Health & Wellness", "thermometer": "Health & Wellness"
        }

        matched_category = None
        for kw, cat in categories_map.items():
            if kw in msg_lower:
                matched_category = cat
                break

        # Build SQL query
        query_sql = "SELECT id, name, category, subcategory, brand, price, discount_percentage, rating, review_count_demo, image_url, description FROM products WHERE 1=1"
        params = []

        if matched_category:
            query_sql += " AND category = ?"
            params.append(matched_category)

        if price_limit > 0:
            query_sql += " AND price <= ?"
            params.append(price_limit)

        # Keyword filtering if no category matched
        if not matched_category and len(msg_lower.split()) <= 5:
            words = [w for w in msg_lower.split() if len(w) > 3 and w not in ["find", "show", "suggest", "best", "good", "want", "need", "like", "under", "below"]]
            if words:
                word_clause = " OR ".join(["name LIKE ? OR description LIKE ? OR brand LIKE ?" for _ in words])
                query_sql += f" AND ({word_clause})"
                for w in words:
                    params.extend([f"%{w}%", f"%{w}%", f"%{w}%"])

        query_sql += " ORDER BY rating DESC, review_count_demo DESC LIMIT 4"

        rows = database.query_db(query_sql, tuple(params))
        if not rows:
            # If price was too tight, search without price limit to inform user
            if price_limit > 0 and matched_category:
                fallback_rows = database.query_db(
                    "SELECT id, name, category, brand, price, rating, image_url FROM products WHERE category = ? ORDER BY price ASC LIMIT 3",
                    (matched_category,)
                )
                if fallback_rows:
                    products = [dict(r) for r in fallback_rows]
                    return {
                        "reply": f"I couldn't find items in **{matched_category}** strictly under ₹{price_limit:,.0f}. Here are the most affordable top-rated options available:",
                        "intent": "product_search_exceeded",
                        "products": products,
                        "suggestions": [f"View all {matched_category}", "Create Savings Plan for this", "My reward points"]
                    }
            return None

        products = [dict(r) for r in rows]
        price_text = f" under ₹{price_limit:,.0f}" if price_limit > 0 else ""
        cat_text = f" in **{matched_category}**" if matched_category else ""

        reply = f"✦ Here are the top-rated recommendations{cat_text}{price_text} matching your criteria:\n"
        for p in products:
            reply += f"\n• **{p['name']}** by *{p['brand']}* — **₹{p['price']:,.0f}** ({p['rating']}★, {p['discount_percentage']}% off)"

        return {
            "reply": reply,
            "intent": "product_search",
            "products": products,
            "suggestions": [
                "Compare these products",
                "Can I pay with Cash on Delivery?",
                "Create a Smart Savings Plan",
                "Check my reward points"
            ]
        }

    def _handle_reward_points(self, user_id: int) -> Dict[str, Any]:
        """Handles reward balance queries with exact 100 points = ₹1 formula."""
        from database import query_db
        rows = query_db("SELECT points, transaction_type FROM reward_ledger WHERE user_id = ?", (user_id,))
        balance = 0
        lifetime = 0
        for r in rows:
            pts = int(r["points"] or 0)
            balance += pts
            if pts > 0 and r["transaction_type"] == "earned_order":
                lifetime += pts

        balance = max(0, balance)
        rupee_val = round(balance / 100.0, 2)

        reply = (
            f"✨ **PreTwin Rewards Balance**\n\n"
            f"• **Current Points:** `{balance} Points`\n"
            f"• **Equivalent Value:** `₹{rupee_val:.2f}`\n"
            f"• **Lifetime Points Earned:** `{lifetime} Points`\n\n"
            f"**How PreTwin Rewards Work:**\n"
            f"• You earn **5 Points** for every eligible completed purchase (equal to ₹0.05).\n"
            f"• **100 Points = ₹1.00** in store credit.\n"
            f"• You can redeem your points right at checkout to discount your order total!\n"
            f"• *Note:* For Cash on Delivery orders, points are credited once the order is delivered and paid."
        )
        return {
            "reply": reply,
            "intent": "reward_points",
            "meta": {"points_balance": balance, "rupee_value": rupee_val},
            "suggestions": ["Go to Rewards Dashboard", "Can I pay COD?", "Find deals under ₹1,000"]
        }

    def _handle_cod_inquiry(self) -> Dict[str, Any]:
        """Explains Cash on Delivery rules and availability."""
        reply = (
            "💵 **Cash on Delivery (COD) Available on PreTwin!**\n\n"
            "• **Zero Advance Payment Required**: You only pay when your parcel is delivered into your hands.\n"
            "• **Payment Options at Doorstep**: You can pay with physical cash or scan the delivery executive's UPI QR code.\n"
            "• **How to use COD**: Select **'Cash on Delivery'** during checkout in Step 4 (Payment Options).\n"
            "• **Order Confirmation**: Your order is confirmed immediately with initial payment status marked as *Pending*.\n"
            "• **Rewards on Delivery**: Once delivered and payment is collected, your order earns **5 PreTwin Reward Points**!\n"
            "• Free delivery is automatically applied on orders above ₹500."
        )
        return {
            "reply": reply,
            "intent": "cod_info",
            "suggestions": ["Proceed to Checkout", "How do Reward Points work?", "Find phones under ₹20,000"]
        }

    def _handle_savings_inquiry(self, msg_lower: str, user_id: int) -> Dict[str, Any]:
        """Provides information or calculations for PreTwin Smart Savings Plan."""
        from database import query_db
        plans = query_db(
            "SELECT p.*, (SELECT COALESCE(SUM(amount), 0) FROM savings_contributions WHERE plan_id = p.id) AS total_saved FROM savings_plans p WHERE p.user_id = ? AND p.status != 'cancelled' ORDER BY p.id DESC",
            (user_id,)
        )

        if plans:
            reply = "🎯 **Your PreTwin Smart Savings Plans:**\n\n"
            for p in plans:
                target = float(p["target_amount"] or 0)
                saved = float(p["total_saved"] or 0)
                rem = max(0.0, target - saved)
                pct = min(100.0, round((saved / target * 100.0), 1)) if target > 0 else 0
                status_emoji = "🎉" if saved >= target else "⏳"
                reply += f"{status_emoji} **{p['goal_title']}**\n"
                reply += f"   • Target: ₹{target:,.0f} | Saved: ₹{saved:,.0f} ({pct}%)\n"
                reply += f"   • Remaining: ₹{rem:,.0f} | Target Date: {p['target_date']}\n\n"
            reply += "You can record new savings contributions anytime on your [Smart Savings Dashboard](/savings)."
        else:
            reply = (
                "🎯 **PreTwin Smart Savings Plan** helps you save for your dream purchases and buy them after 1 month!\n\n"
                "**How it works:**\n"
                "1. Pick a product from our catalogue (e.g. a ₹15,000 smartphone).\n"
                "2. PreTwin calculates the daily contribution needed (e.g. ₹500/day over 30 days) or weekly savings (₹3,500/week).\n"
                "3. Record your daily or weekly saved amounts as you set money aside.\n"
                "4. When your goal is reached after 1 month, click **'Goal Reached — Ready to Shop'** to add it to your cart and check out (including via Cash on Delivery)!\n\n"
                "*(Note: This is a personal budget tracker and goal planner, not a bank deposit).* \n"
                "Ready to start? Visit [Smart Savings Plan](/savings) to create your first goal!"
            )

        return {
            "reply": reply,
            "intent": "savings_plan",
            "suggestions": ["Open Smart Savings Plan", "Find phones under ₹20,000", "Check Reward Points"]
        }

    def _handle_order_status(self, user_id: int) -> Dict[str, Any]:
        """Retrieves user's recent orders and delivery status."""
        from database import query_db
        orders = query_db(
            "SELECT id, order_number, total_amount, status, payment_status, payment_method, created_at FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT 3",
            (user_id,)
        )
        if not orders:
            return {
                "reply": "📦 You haven't placed any orders yet. Once you complete checkout, you can track delivery status and Cash on Delivery details right here!",
                "intent": "order_status_empty",
                "suggestions": ["Browse 1,000+ Products", "Can I pay COD?", "Smart Savings Plan"]
            }

        reply = "📦 **Your Recent PreTwin Orders:**\n\n"
        for o in orders:
            reply += f"• **Order #{o['order_number']}** — **₹{o['total_amount']:,.0f}**\n"
            reply += f"  Status: `{o['status']}` | Payment: `{o['payment_status']}` ({o['payment_method']})\n"
            reply += f"  Placed: {str(o['created_at'])[:10]}\n\n"
        reply += "You can view complete delivery details on the [My Orders](/orders) page."

        return {
            "reply": reply,
            "intent": "order_status",
            "suggestions": ["View My Orders", "Can I pay COD?", "How many points do I have?"]
        }

    def _handle_cart_inquiry(self, user_id: int) -> Dict[str, Any]:
        return {
            "reply": "🛒 You can review your cart anytime by clicking the **Cart** icon in the top header! We offer **Free Express Delivery** on orders above ₹500 and full **Cash on Delivery (COD)** support.",
            "intent": "cart_inquiry",
            "suggestions": ["Open Cart", "Proceed to Checkout", "Find deals under ₹1,000"]
        }

    def _handle_predictions_inquiry(self, user_id: int) -> Dict[str, Any]:
        """Returns predictions generated by the AI Shopping Twin."""
        from database import query_db
        preds = query_db(
            "SELECT predicted_category, predicted_product, reason, confidence_label, confidence_score, estimated_timeframe FROM predictions WHERE user_id = ? AND status = 'active' ORDER BY confidence_score DESC LIMIT 3",
            (user_id,)
        )
        if not preds:
            return {
                "reply": "🔮 Your AI Shopping Twin is continuously analyzing your purchase habits and preferences. Visit the [Future Needs Prediction](/predictions) dashboard to trigger a new prediction run!",
                "intent": "predictions_empty",
                "suggestions": ["Run AI Analysis", "Go to Shopping Twin", "Browse Products"]
            }

        reply = "🔮 **Your AI Twin's Upcoming Shopping Predictions:**\n\n"
        for p in preds:
            reply += f"• **{p['predicted_product']}** in *{p['predicted_category']}*\n"
            reply += f"  Reason: {p['reason']}\n"
            reply += f"  Confidence: `{p['confidence_label']}` ({int(float(p['confidence_score'] or 0)*100)}%) • Timing: {p['estimated_timeframe']}\n\n"
        reply += "Explore all predictions and accept or dismiss them on the [Future Needs Prediction](/predictions) page."

        return {
            "reply": reply,
            "intent": "predictions",
            "suggestions": ["Open Predictions Dashboard", "View Shopping Twin", "Compare Products"]
        }

    def _handle_twin_inquiry(self, user_id: int) -> Dict[str, Any]:
        """Provides summary of the user's shopping twin profile."""
        from database import query_db
        row = query_db("SELECT * FROM shopping_preferences WHERE user_id = ?", (user_id,), one=True)
        if not row:
            return {
                "reply": "👤 Your Shopping Twin has not been configured yet. Visit [My Shopping Twin](/twin) to set your favorite categories, monthly budget, and preferred brands!",
                "intent": "twin_empty",
                "suggestions": ["Configure Twin", "Browse Products", "Smart Savings Plan"]
            }

        pref = dict(row)
        cats = json.loads(pref.get("preferred_categories") or "[]")
        brands = json.loads(pref.get("preferred_brands") or "[]")
        b_min = pref.get("budget_min", 500)
        b_max = pref.get("budget_max", 10000)

        reply = (
            f"👤 **Your Personalized Digital Shopping Twin:**\n\n"
            f"• **Budget Window:** ₹{b_min:,.0f} – ₹{b_max:,.0f}\n"
            f"• **Preferred Categories:** {', '.join(cats) if cats else 'All 20 Categories'}\n"
            f"• **Favorite Brands:** {', '.join(brands) if brands else 'All Verified Brands'}\n"
            f"• **Shopping Cadence:** {pref.get('shopping_frequency', 'Monthly').capitalize()}\n\n"
            f"You can fine-tune your twin anytime at [My Shopping Twin](/twin)."
        )
        return {
            "reply": reply,
            "intent": "twin_profile",
            "suggestions": ["Open Shopping Twin", "Future Needs Prediction", "Smart Savings Plan"]
        }

    def _handle_comparison_inquiry(self, msg_lower: str) -> Dict[str, Any]:
        reply = (
            "⚖️ **PreTwin AI Product Comparison:**\n\n"
            "You can compare up to **4 products side-by-side** on price, specifications, brand, and AI suitability!\n\n"
            "• Click the **'Compare'** icon on any product card in Discovery or Recommendations.\n"
            "• Or visit the [AI Product Comparison](/comparison) page to search and select products directly.\n"
            "• Our Comparison Agent will evaluate advantages, limitations, and crown an AI 'Best Pick' winner!"
        )
        return {
            "reply": reply,
            "intent": "comparison_info",
            "suggestions": ["Open AI Comparison", "Find phones under ₹20,000", "Compare running shoes"]
        }

    def _handle_explanation_inquiry(self, user_id: int) -> Dict[str, Any]:
        from database import query_db
        recs = query_db(
            "SELECT product_name, category, price, reason, budget_fit FROM recommendations WHERE user_id = ? ORDER BY score DESC LIMIT 2",
            (user_id,)
        )
        if recs:
            reply = "⭐ **Why We Recommended These Products For You:**\n\n"
            for r in recs:
                reply += f"• **{r['product_name']}** (₹{r['price']:,.0f})\n"
                reply += f"  *{r['reason']}*\n"
                reply += f"  Budget Fit: `{r['budget_fit']}`\n\n"
            reply += "See all explanations on the [Personalized Recommendations](/recommendations) page."
        else:
            reply = (
                "⭐ PreTwin's Recommendation Agent generates recommendations by analyzing your purchase history frequency, "
                "active shopping goals, and strict monthly budget constraints. Visit [Smart Recommendations](/recommendations) "
                "to view your latest ranked picks!"
            )

        return {
            "reply": reply,
            "intent": "explanation",
            "suggestions": ["View Recommendations", "Open Shopping Twin", "Smart Savings Plan"]
        }

    def _handle_wishlist_inquiry(self, user_id: int) -> Dict[str, Any]:
        """Fetch items saved in user's wishlist."""
        from database import query_db
        rows = query_db(
            """
            SELECT p.id, p.name, p.category, p.brand, p.price, p.rating, p.image_url
            FROM wishlist_items w
            JOIN products p ON w.product_id = p.id
            WHERE w.user_id = ?
            ORDER BY w.id DESC LIMIT 4
            """,
            (user_id,)
        )
        if not rows:
            return {
                "reply": "❤️ Your Wishlist is currently empty. You can save any product with one click on the heart icon or ask me: *'Find college shoes under 1500'* to explore items!",
                "intent": "wishlist_empty",
                "products": [],
                "suggestions": ["Find shoes under ₹1,500", "Top phones under ₹20,000", "Open Wishlist page"]
            }
        products = [dict(r) for r in rows]
        return {
            "reply": f"❤️ You currently have **{len(products)} item(s)** saved in your PreTwin Wishlist. Here are your saved items:",
            "intent": "wishlist_items",
            "products": products,
            "actions": [{"title": "Open My Wishlist", "url": "/wishlist"}],
            "suggestions": ["Add all to Cart", "Find cheaper alternatives", "Check price drops"]
        }

    def _handle_calendar_inquiry(self, msg_lower: str, user_id: int) -> Dict[str, Any]:
        """Fetch upcoming calendar milestones and gear recommendations."""
        from database import query_db
        events = query_db(
            "SELECT id, title, event_date, event_type, category, budget, notes FROM shopping_calendar_events WHERE user_id = ? ORDER BY event_date ASC LIMIT 3",
            (user_id,)
        )
        if not events:
            return {
                "reply": "📅 You don't have any upcoming shopping milestones in your calendar yet. You can add semester reopenings, birthdays, or household restocking schedules directly on your **Future Predictive Calendar**!",
                "intent": "calendar_empty",
                "actions": [{"title": "Open Predictive Calendar", "url": "/calendar"}],
                "suggestions": ["Add College Milestone", "Add Birthday Milestone", "Open Calendar"]
            }
        ev_list = [dict(e) for e in events]
        first_ev = ev_list[0]
        cat = first_ev.get("category") or "Laptops & Computers"
        prods = query_db(
            "SELECT id, name, category, brand, price, rating, image_url FROM products WHERE category = ? ORDER BY rating DESC LIMIT 3",
            (cat,)
        )
        products = [dict(p) for p in prods] if prods else []
        reply_lines = [f"📅 **Upcoming Milestone**: **{first_ev['title']}** (Target Date: {first_ev['event_date'].split('T')[0]})"]
        if first_ev.get("notes"):
            reply_lines.append(f"• *Needs*: {first_ev['notes']}")
        reply_lines.append(f"• *Budget*: ₹{float(first_ev.get('budget', 5000)):,.0f}")
        reply_lines.append("\nHere are top PreTwin recommended items to prepare for this event:")

        return {
            "reply": "\n".join(reply_lines),
            "intent": "calendar_event_prep",
            "products": products,
            "actions": [{"title": "View Full Predictive Calendar", "url": "/calendar"}],
            "suggestions": ["Add to Cart", "Find cheaper alternatives", "Check other milestones"]
        }

    def _handle_cheaper_alternatives(self, msg_lower: str) -> Dict[str, Any]:
        """Find cheaper alternatives to a product category or item."""
        from database import query_db
        cat = "Electronics"
        if "shoe" in msg_lower: cat = "Footwear"
        elif "phone" in msg_lower: cat = "Mobiles"
        elif "laptop" in msg_lower: cat = "Laptops & Computers"
        elif "shirt" in msg_lower or "jean" in msg_lower: cat = "Fashion"
        elif "watch" in msg_lower: cat = "Watches & Accessories"

        rows = query_db(
            "SELECT id, name, category, brand, price, rating, image_url FROM products WHERE category = ? ORDER BY price ASC LIMIT 4",
            (cat,)
        )
        products = [dict(r) for r in rows] if rows else []
        return {
            "reply": f"🔍 Here are the **best value, budget-friendly alternatives** in **{cat}** with verified high customer satisfaction ratings:",
            "intent": "cheaper_alternatives",
            "products": products,
            "suggestions": ["Compare with top model", "Add to Cart", "Check price history"]
        }

    def _handle_budget_bundle_inquiry(self, msg_lower: str) -> Dict[str, Any]:
        """Create a curated shopping list within a specific budget (e.g. ₹5,000)."""
        limit = self._extract_price_limit(msg_lower)
        if limit <= 0:
            limit = 5000.0

        from database import query_db
        rows = query_db(
            "SELECT id, name, category, brand, price, rating, image_url FROM products WHERE price <= ? ORDER BY rating DESC LIMIT 10",
            (limit * 0.45,)
        )
        products = []
        total = 0.0
        seen_cats = set()
        for r in rows:
            p = dict(r)
            if p["category"] not in seen_cats and (total + p["price"] <= limit):
                products.append(p)
                total += p["price"]
                seen_cats.add(p["category"])
            if len(products) >= 3:
                break

        return {
            "reply": f"🧺 Here is a **Curated Shopping Basket** within your **₹{limit:,.0f} budget** (Total: ₹{total:,.0f}):\n" +
                     "\n".join([f"• **{p['name']}** ({p['category']}) — ₹{p['price']:,.0f}" for p in products]),
            "intent": "budget_shopping_list",
            "products": products,
            "suggestions": ["Add all to Cart", "Adjust budget", "Save to Wishlist"]
        }

    def _handle_gift_inquiry(self, msg_lower: str) -> Dict[str, Any]:
        """Find budget-friendly gift ideas."""
        limit = self._extract_price_limit(msg_lower)
        if limit <= 0:
            limit = 3000.0
        from database import query_db
        rows = query_db(
            "SELECT id, name, category, brand, price, rating, image_url FROM products WHERE (category = 'Watches & Accessories' OR category = 'Electronics' OR category = 'Personal Care') AND price <= ? ORDER BY rating DESC LIMIT 4",
            (limit,)
        )
        products = [dict(r) for r in rows] if rows else []
        return {
            "reply": f"🎁 Here are curated **gift ideas** within your **₹{limit:,.0f} budget** that make wonderful surprises:",
            "intent": "gift_recommendations",
            "products": products,
            "actions": [{"title": "Try Smart Gift Recommender", "url": "/advanced-ai"}],
            "suggestions": ["Add to Cart", "View Watches", "Gift under ₹1,500"]
        }
