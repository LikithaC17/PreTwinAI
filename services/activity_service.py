"""
services/activity_service.py
----------------------------
Records authenticated customer interactions (browsing, search, wishlist, cart)
to enable authentic, explainable behavioral learning for the Personalization Twin.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

import database

logger = logging.getLogger("activity_service")


class ActivityService:
    @staticmethod
    def log_activity(
        user_id: int,
        activity_type: str,
        product_id: Optional[int] = None,
        query_or_category: str = "",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Safely record a customer activity event."""
        if not user_id:
            return
        try:
            details_str = json.dumps(details or {})
            database.execute_db(
                """INSERT INTO user_activity
                   (user_id, activity_type, product_id, query_or_category, details_json)
                   VALUES (?, ?, ?, ?, ?)""",
                (user_id, activity_type, product_id, query_or_category[:120], details_str),
            )
        except Exception as exc:
            logger.debug("Activity log skipped: %s", exc)

    @staticmethod
    def get_recent_activities(user_id: int, limit: int = 50) -> list[dict]:
        """Fetch recent activity timeline for the authenticated user."""
        if not user_id:
            return []
        rows = database.query_db(
            """SELECT * FROM user_activity
               WHERE user_id = ?
               ORDER BY id DESC LIMIT ?""",
            (user_id, limit),
        )
        return [dict(r) for r in (rows or [])]
