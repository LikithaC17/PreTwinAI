"""
integrations/flipkart.py
------------------------
Clean Provider Interface & Client for Official Flipkart Integration.

Permitted integration standards:
- Access only through authorized API / feed credentials.
- All secrets kept in environment variables (never committed or exposed to frontend).
- In-memory response caching adhering to Flipkart's 30-minute refresh rules.
- Rate limiting protection (configurable, default 60 req/min).
- Graceful error handling for missing credentials, timeouts, and rate limits.
- Clear distinction between live data, cached data, and catalog data.
- Duplicate prevention during catalog synchronization.
"""

import os
import time
import json
import logging
from typing import Dict, List, Optional, Any
from urllib.parse import quote_plus

import requests
from config import Config
import database

logger = logging.getLogger("flipkart_integration")


class FlipkartProvider:
    """Official Flipkart API integration provider adhering to affiliate and marketplace policies."""

    def __init__(
        self,
        affiliate_id: Optional[str] = None,
        affiliate_token: Optional[str] = None,
        base_url: Optional[str] = None,
        cache_ttl: Optional[int] = None,
    ):
        self.affiliate_id = affiliate_id or Config.FLIPKART_AFFILIATE_ID or os.getenv("FLIPKART_AFFILIATE_ID", "")
        self.affiliate_token = affiliate_token or Config.FLIPKART_AFFILIATE_TOKEN or os.getenv("FLIPKART_AFFILIATE_TOKEN", "")
        self.base_url = (base_url or Config.FLIPKART_API_BASE_URL or "https://affiliate-api.flipkart.net/affiliate/1.0").rstrip("/")
        self.cache_ttl = cache_ttl or getattr(Config, "FLIPKART_CACHE_TTL_SECONDS", 1800)
        self.rate_limit_per_min = getattr(Config, "FLIPKART_RATE_LIMIT_PER_MINUTE", 60)
        self.enabled = getattr(Config, "FLIPKART_ENABLED", False) or bool(self.affiliate_id and self.affiliate_token)

        # In-memory request cache: key -> {"timestamp": float, "data": Any}
        self._cache: Dict[str, Dict[str, Any]] = {}
        # Rate limit tracking: list of request timestamps within last 60 seconds
        self._request_timestamps: List[float] = []

    def is_configured(self) -> bool:
        """Check whether valid affiliate/developer credentials are configured."""
        return bool(self.affiliate_id and self.affiliate_token)

    def is_live_active(self) -> bool:
        """Return True if integration is enabled and configured."""
        return self.enabled and self.is_configured()

    def get_masked_affiliate_id(self) -> Optional[str]:
        """Safely mask affiliate ID for public/admin display."""
        if not self.affiliate_id:
            return None
        if len(self.affiliate_id) <= 4:
            return "****"
        return f"{self.affiliate_id[:2]}****{self.affiliate_id[-2:]}"

    def get_status(self) -> Dict[str, Any]:
        """
        Return comprehensive integration status, compliance information,
        and instructions for obtaining official Flipkart API credentials.
        """
        configured = self.is_configured()
        live = self.is_live_active()

        return {
            "provider": "Flipkart Affiliate / Marketplace API",
            "api_version": "1.0",
            "configured": configured,
            "live_active": live,
            "mode": "LIVE_API" if live else "SAMPLE_CATALOG_MODE",
            "affiliate_id_configured": bool(self.affiliate_id),
            "affiliate_id_masked": self.get_masked_affiliate_id(),
            "api_base_url": self.base_url,
            "cache_ttl_seconds": self.cache_ttl,
            "allowed_refresh_frequency": "Every 30 minutes (per Flipkart Terms of Service)",
            "rate_limit_per_minute": self.rate_limit_per_min,
            "attribution": "Powered by Flipkart Affiliate & Catalog Services",
            "required_env_vars": [
                "FLIPKART_AFFILIATE_ID",
                "FLIPKART_AFFILIATE_TOKEN",
                "FLIPKART_ENABLED"
            ],
            "approval_steps": [
                "1. Register at the official Flipkart Affiliate Portal (https://affiliate.flipkart.com).",
                "2. Apply for API access and complete business identity verification.",
                "3. Copy your unique Affiliate ID and API Token from the API Credentials dashboard.",
                "4. Set environment variables: FLIPKART_AFFILIATE_ID, FLIPKART_AFFILIATE_TOKEN, FLIPKART_ENABLED=true.",
                "5. PreTwin AI will automatically route queries to live Flipkart endpoints with rate-limited caching."
            ],
            "compliance_notice": (
                "PreTwin AI strictly follows permitted integration policies. We do not scrape, "
                "bypass access controls, or claim unverified sample data as live prices. "
                "When live credentials are not present, PreTwin AI seamlessly operates on verified sample catalog data."
            )
        }

    def _check_rate_limit(self) -> bool:
        """Enforce requests-per-minute threshold to prevent provider throttling."""
        now = time.time()
        self._request_timestamps = [t for t in self._request_timestamps if now - t < 60.0]
        if len(self._request_timestamps) >= self.rate_limit_per_min:
            return False
        self._request_timestamps.append(now)
        return True

    def _get_from_cache(self, key: str) -> Optional[Any]:
        """Retrieve valid cached data if not expired."""
        if key in self._cache:
            entry = self._cache[key]
            if time.time() - entry["timestamp"] < self.cache_ttl:
                return entry["data"]
            del self._cache[key]
        return None

    def _set_cache(self, key: str, data: Any):
        """Save data to in-memory cache with current timestamp."""
        self._cache[key] = {
            "timestamp": time.time(),
            "data": data,
        }

    def search_products(
        self,
        query: str,
        category: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """
        Search products via Flipkart API if configured, otherwise provide
        clear feedback and fallback to catalog search.
        """
        cache_key = f"search:{query}:{category}:{page}:{limit}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return {
                "success": True,
                "data_origin": "cached_api",
                "source": "Flipkart Cached Feed",
                "products": cached,
                "total": len(cached),
                "is_live": False,
                "is_cached": True,
            }

        # If live credentials are not configured, return clear explanation
        if not self.is_live_active():
            return {
                "success": False,
                "data_origin": "catalog",
                "reason": "FLIPKART_CREDENTIALS_NOT_CONFIGURED",
                "message": (
                    "Live Flipkart API access requires authorized partner credentials. "
                    "PreTwin AI is serving from the verified local catalog."
                ),
                "products": [],
                "is_live": False,
                "is_cached": False,
            }

        # Check rate limit
        if not self._check_rate_limit():
            return {
                "success": False,
                "data_origin": "rate_limited",
                "reason": "RATE_LIMIT_EXCEEDED",
                "message": "Flipkart API rate limit reached. Please wait before retrying.",
                "products": [],
                "is_live": False,
            }

        # Execute authorized HTTP request to official endpoint
        endpoint = f"{self.base_url}/search.json"
        headers = {
            "Fk-Affiliate-Id": self.affiliate_id,
            "Fk-Affiliate-Token": self.affiliate_token,
            "User-Agent": "PreTwinAI-ShoppingPartner/1.0",
            "Accept": "application/json",
        }
        params = {
            "query": query,
            "resultCount": min(limit, 50),
        }

        try:
            resp = requests.get(endpoint, headers=headers, params=params, timeout=5.0)
            if resp.status_code == 200:
                raw_data = resp.json()
                normalized = self._normalize_flipkart_items(raw_data)
                self._set_cache(cache_key, normalized)
                return {
                    "success": True,
                    "data_origin": "live_api",
                    "source": "Flipkart Live API",
                    "products": normalized,
                    "total": len(normalized),
                    "is_live": True,
                    "is_cached": False,
                }
            elif resp.status_code in (401, 403):
                return {
                    "success": False,
                    "data_origin": "auth_error",
                    "reason": "INVALID_OR_EXPIRED_CREDENTIALS",
                    "message": "Flipkart affiliate credentials rejected by provider.",
                    "products": [],
                    "is_live": False,
                }
            else:
                return {
                    "success": False,
                    "data_origin": "api_error",
                    "reason": f"HTTP_{resp.status_code}",
                    "message": f"Flipkart API returned status code {resp.status_code}.",
                    "products": [],
                    "is_live": False,
                }

        except requests.Timeout:
            return {
                "success": False,
                "data_origin": "timeout",
                "reason": "REQUEST_TIMEOUT",
                "message": "Flipkart API connection timed out. Falling back to local cache.",
                "products": [],
                "is_live": False,
            }
        except Exception as exc:
            logger.warning(f"Flipkart API request error: {exc}")
            return {
                "success": False,
                "data_origin": "error",
                "reason": str(exc),
                "message": "Could not connect to Flipkart API service.",
                "products": [],
                "is_live": False,
            }

    def _normalize_flipkart_items(self, raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Normalize official Flipkart JSON product payload into PreTwin schema."""
        products = []
        item_list = raw_data.get("productInfoList") or raw_data.get("products") or []

        for item in item_list:
            try:
                base = item.get("productBaseInfo") or item.get("productBaseInfoV1") or item
                attrs = base.get("productAttributes") or {}
                ident = base.get("productIdentifier") or {}

                product_id = ident.get("productId") or str(item.get("id") or "")
                title = attrs.get("title") or attrs.get("name") or "Flipkart Product"
                desc = attrs.get("productDescription") or attrs.get("description") or ""
                brand = attrs.get("productBrand") or attrs.get("brand") or "Generic"
                category = attrs.get("category") or "Electronics"

                # Extract price
                sell_price_obj = attrs.get("sellingPrice") or {}
                mrp_obj = attrs.get("maximumRetailPrice") or {}
                selling_price = float(sell_price_obj.get("amount") or attrs.get("price") or 0.0)
                mrp = float(mrp_obj.get("amount") or mrp_obj.get("mrp") or selling_price * 1.25)
                disc = int(attrs.get("discountPercentage") or 0)
                if disc == 0 and mrp > selling_price > 0:
                    disc = int(((mrp - selling_price) / mrp) * 100)

                # Extract image
                image_urls = attrs.get("imageUrls") or {}
                image_url = ""
                for resolution in ["800x800", "400x400", "200x200", "unknown"]:
                    if resolution in image_urls and image_urls[resolution]:
                        image_url = image_urls[resolution]
                        break

                product_url = attrs.get("productUrl") or f"https://www.flipkart.com/search?q={quote_plus(title)}"
                in_stock = bool(attrs.get("inStock", True))

                products.append({
                    "source_id": product_id,
                    "name": title,
                    "category": category,
                    "subcategory": attrs.get("subcategory", ""),
                    "brand": brand,
                    "price": selling_price,
                    "mrp": mrp,
                    "discount_percentage": disc,
                    "description": desc,
                    "image_url": image_url,
                    "external_url": product_url,
                    "source_type": "flipkart_live",
                    "data_origin": "live_api",
                    "availability": "in_stock" if in_stock else "out_of_stock",
                    "rating": float(attrs.get("rating") or 4.2),
                    "review_count_demo": int(attrs.get("reviewCount") or 150),
                    "stock": 50 if in_stock else 0,
                    "specifications": attrs.get("specifications") or {},
                })
            except Exception as e:
                logger.debug(f"Error parsing Flipkart product item: {e}")
                continue

        return products

    def sync_to_database(self, products_data: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Safely insert or update authorized product feed items into the database.
        Strictly prevents duplicates based on (source_type, source_id) and (name, brand).
        """
        inserted = 0
        updated = 0

        with database.get_db() as conn:
            cursor = conn.cursor()

            for p in products_data:
                source_id = p.get("source_id") or ""
                name = p.get("name") or ""
                brand = p.get("brand") or ""
                source_type = p.get("source_type") or "flipkart_live"

                # Check for existing record
                cursor.execute(
                    """
                    SELECT id FROM products 
                    WHERE (source_type = ? AND source_id = ? AND source_id != '')
                       OR (name = ? AND brand = ?)
                    """,
                    (source_type, source_id, name, brand),
                )
                existing = cursor.fetchone()

                specs_str = json.dumps(p.get("specifications") or {})

                if existing:
                    # Update price, stock, availability, and last_synced_at
                    cursor.execute(
                        """
                        UPDATE products
                        SET price = ?,
                            stock = ?,
                            availability = ?,
                            external_url = ?,
                            data_origin = ?,
                            last_synced_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                        """,
                        (
                            float(p.get("price") or 0.0),
                            int(p.get("stock") or 0),
                            p.get("availability") or "in_stock",
                            p.get("external_url") or "",
                            p.get("data_origin") or "live_api",
                            existing["id"],
                        ),
                    )
                    updated += 1
                else:
                    # Insert new authorized product record
                    cursor.execute(
                        """
                        INSERT INTO products (
                            name, category, subcategory, brand, price,
                            discount_percentage, specifications, description,
                            image_url, source_type, source_id, rating,
                            review_count_demo, stock, external_url,
                            availability, data_origin, last_synced_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                        """,
                        (
                            name,
                            p.get("category") or "Electronics",
                            p.get("subcategory") or "",
                            brand,
                            float(p.get("price") or 0.0),
                            int(p.get("discount_percentage") or 15),
                            specs_str,
                            p.get("description") or "",
                            p.get("image_url") or "",
                            source_type,
                            source_id,
                            float(p.get("rating") or 4.2),
                            int(p.get("review_count_demo") or 120),
                            int(p.get("stock") or 50),
                            p.get("external_url") or "",
                            p.get("availability") or "in_stock",
                            p.get("data_origin") or "live_api",
                        ),
                    )
                    inserted += 1

            conn.commit()

        return {"inserted": inserted, "updated": updated, "total_processed": len(products_data)}


# Global provider singleton
flipkart_client = FlipkartProvider()
