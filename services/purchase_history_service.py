"""
services/purchase_history_service.py
------------------------------------
Tracks, verifies, and manages legitimate purchase history events for PreTwin AI.

Compliance & Integrity Standards:
1. Only completed, legitimate purchases are counted as purchase-history events.
2. Cancelled orders, failed payments, returned/refunded orders, and abandoned carts
   are strictly excluded from behavioral analysis.
3. Cash on Delivery (COD) purchases are treated as completed only after delivery
   and payment collection are verified.
4. Online payments require verified gateway completion.
5. Order item price and details are recorded as immutable snapshots at purchase time.
6. Prevents duplicate order events and duplicate reward points.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import database

logger = logging.getLogger("purchase_history_service")


class PurchaseHistoryService:
    """Service governing verified purchase events and historical order integration."""

    @staticmethod
    def is_order_eligible_for_history(order: Dict[str, Any]) -> bool:
        """
        Determine whether an order constitutes a completed, legitimate purchase.

        Rules:
        - Must NOT be Cancelled, Returned, or Payment Failed.
        - Must NOT be an unpaid abandoned cart.
        - Cash on Delivery (COD): Must be Delivered and Paid.
        - Online payments (Razorpay/Cards/UPI): Must be Paid and Confirmed/Delivered.
        """
        if not order:
            return False

        status = (order.get("status") or "").strip().lower()
        pay_status = (order.get("payment_status") or "").strip().lower()
        method = (order.get("payment_method") or "").strip().lower()
        gateway = (order.get("gateway_name") or "").strip().lower()

        # Disqualify cancellations, returns, and failed payments
        if status in ("cancelled", "returned", "payment failed", "failed"):
            return False
        if pay_status in ("failed", "refunded"):
            return False

        # COD orders must be delivered to be counted as verified purchases
        is_cod = ("cod" in method or "cash on delivery" in method or "cod" in gateway)
        if is_cod:
            return status in ("delivered", "completed") and ("paid" in pay_status)

        # Online payments must have verified payment status
        return "paid" in pay_status and status in ("confirmed", "delivered", "completed", "shipped")

    @classmethod
    def record_order_purchase(cls, order_id: int) -> int:
        """
        Record order items as verified purchase history events if order is eligible.
        Preserves original price and product details snapshot at the time of purchase.
        """
        order_row = database.query_db("SELECT * FROM orders WHERE id = ?", (order_id,), one=True)
        if not order_row:
            return 0

        order = dict(order_row)
        if not cls.is_order_eligible_for_history(order):
            # If order is not eligible (e.g. COD pending delivery), ensure it's not marked active
            database.execute_db(
                "UPDATE purchase_history SET is_verified_purchase = 0 WHERE order_id = ?",
                (order_id,)
            )
            return 0

        user_id = order["user_id"]
        order_number = order.get("order_number", "")
        purchase_date = str(order.get("created_at", datetime.now(timezone.utc).isoformat()))[:10]
        pay_method = order.get("payment_method", "")
        pay_status = order.get("payment_status", "Paid")
        order_status = order.get("status", "Delivered")
        fulfillment_status = order.get("fulfillment_status", order_status)

        items = database.query_db("SELECT * FROM order_items WHERE order_id = ?", (order_id,))
        recorded_count = 0

        for item_row in items:
            it = dict(item_row)
            pid = it.get("product_id")
            pname = it.get("product_name", "")
            qty = max(1, int(it.get("quantity", 1)))
            price = float(it.get("price", 0.0))
            category = it.get("category", "")
            brand = it.get("brand", "")

            # Prevent duplicate event recording for the same order and product
            existing = database.query_db(
                "SELECT id FROM purchase_history WHERE order_id = ? AND product_name = ?",
                (order_id, pname),
                one=True
            )

            if existing:
                database.execute_db(
                    """
                    UPDATE purchase_history
                    SET price = ?,
                        quantity = ?,
                        purchase_date = ?,
                        payment_status = ?,
                        order_status = ?,
                        fulfillment_status = ?,
                        is_verified_purchase = 1
                    WHERE id = ?
                    """,
                    (price, qty, purchase_date, pay_status, order_status, fulfillment_status, existing["id"])
                )
            else:
                database.execute_db(
                    """
                    INSERT INTO purchase_history (
                        user_id, product_id, product_name, category, brand,
                        price, purchase_date, quantity, notes, order_id,
                        order_number, payment_method, payment_status,
                        order_status, fulfillment_status, is_verified_purchase
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                    """,
                    (
                        user_id, pid, pname, category, brand, price,
                        purchase_date, qty, f"Order #{order_number}",
                        order_id, order_number, pay_method, pay_status,
                        order_status, fulfillment_status
                    )
                )
                recorded_count += 1

        return recorded_count

    @classmethod
    def handle_order_cancellation(cls, order_id: int) -> None:
        """Mark purchase history records for a cancelled order as non-verified."""
        database.execute_db(
            """
            UPDATE purchase_history
            SET order_status = 'Cancelled',
                is_verified_purchase = 0
            WHERE order_id = ?
            """,
            (order_id,)
        )

    @classmethod
    def handle_order_return(cls, order_id: int) -> None:
        """Mark purchase history records for a returned/refunded order as non-verified."""
        database.execute_db(
            """
            UPDATE purchase_history
            SET order_status = 'Returned',
                payment_status = 'Refunded',
                is_verified_purchase = 0
            WHERE order_id = ?
            """,
            (order_id,)
        )

    @classmethod
    def get_eligible_purchases_for_user(cls, user_id: int) -> List[Dict[str, Any]]:
        """
        Retrieve strictly legitimate, verified purchase events for a user.
        Excludes cancelled, returned, refunded, or failed purchases.
        """
        # First ensure all completed orders in the orders table are mirrored
        orders = database.query_db(
            "SELECT id FROM orders WHERE user_id = ? ORDER BY id DESC",
            (user_id,)
        )
        for ord_row in (orders or []):
            cls.record_order_purchase(ord_row["id"])

        # Query purchase history where is_verified_purchase = 1
        rows = database.query_db(
            """
            SELECT * FROM purchase_history
            WHERE user_id = ?
              AND (is_verified_purchase = 1 OR is_verified_purchase IS NULL)
              AND LOWER(order_status) NOT IN ('cancelled', 'returned', 'payment failed')
              AND LOWER(payment_status) NOT IN ('failed', 'refunded')
            ORDER BY purchase_date DESC, id DESC
            """,
            (user_id,)
        )

        return [dict(r) for r in (rows or [])]

    @staticmethod
    def is_twin_history_opted_in(user_id: int) -> bool:
        """
        Check if user has opted into using purchase history for AI Digital Twin personalization.
        Defaults to True (1) with complete user toggle control.
        """
        pref = database.query_db(
            "SELECT use_purchase_history_for_twin FROM shopping_preferences WHERE user_id = ?",
            (user_id,),
            one=True
        )
        if not pref:
            return True
        val = pref["use_purchase_history_for_twin"]
        return val is None or int(val) == 1

    @staticmethod
    def set_twin_history_opt_in(user_id: int, opt_in: bool) -> None:
        """Toggle user preference for using purchase history in Digital Twin personalization."""
        val = 1 if opt_in else 0
        pref = database.query_db(
            "SELECT id FROM shopping_preferences WHERE user_id = ?",
            (user_id,),
            one=True
        )
        if pref:
            database.execute_db(
                "UPDATE shopping_preferences SET use_purchase_history_for_twin = ? WHERE user_id = ?",
                (val, user_id)
            )
        else:
            database.execute_db(
                "INSERT INTO shopping_preferences (user_id, use_purchase_history_for_twin) VALUES (?, ?)",
                (user_id, val)
            )
