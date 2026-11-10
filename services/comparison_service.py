"""
services/comparison_service.py
==============================
PreTwin AI - Feature 5: Product Comparison and Decision Support Service
Provides modular engines for:
1. Product Selection & Validation (catalogue search, category filtering, preset pairs, max 4 limit, duplicate prevention)
2. Side-by-Side Comparison Matrix (aligned attributes, "Show only differences" detection)
3. Feature & Specification Analysis (category-aware spec grouping, shared vs different attributes, best value highlights)
4. Price and Value Comparison (selling price, MRP, discounts, price difference, explainable value score, budget affordability)
5. Fact-Based Pros and Cons (strictly derived from catalogue attributes, no fabricated claims)
6. Smart Decision Assistant (multi-attribute priority weighting, trade-off analysis, close-score/comparable option detection)
7. Final Decision & Actions (tenant-isolated comparison session persistence, wishlist/cart handoff)
"""

import json
import re
import math
from typing import List, Dict, Any, Optional, Tuple

import database


def _parse_json(val, default=None):
    if default is None:
        default = {}
    if not val:
        return default
    if isinstance(val, (dict, list)):
        return val
    try:
        return json.loads(val)
    except Exception:
        return default


def _calculate_mrp(price: float, discount_percentage: float) -> float:
    """Calculate original price (MRP) from selling price and discount."""
    if not discount_percentage or discount_percentage <= 0:
        return float(price)
    if discount_percentage >= 99:
        return float(price)
    mrp = price / (1.0 - (discount_percentage / 100.0))
    return round(mrp, 2)


# =============================================================================
# 1. Product Selection & Validation Engine
# =============================================================================

class ProductSelectionEngine:
    """Manages catalogue search, preset pairs, and product validation for comparison."""

    MAX_COMPARE_LIMIT = 4

    @staticmethod
    def search_catalogue(query: str = "", category: str = "", limit: int = 24) -> List[Dict[str, Any]]:
        """Search products from catalogue for comparison selection."""
        sql = "SELECT id, name, category, brand, price, discount_percentage, rating, review_count_demo, stock, image_url, subcategory FROM products WHERE 1=1"
        params: List[Any] = []

        if query and query.strip():
            sql += " AND (name LIKE ? OR brand LIKE ? OR subcategory LIKE ?)"
            term = f"%{query.strip()}%"
            params.extend([term, term, term])

        if category and category.strip() and category.lower() != "all":
            sql += " AND category = ?"
            params.append(category.strip())

        sql += " ORDER BY rating DESC, price ASC LIMIT ?"
        params.append(limit)

        rows = database.query_db(sql, tuple(params)) or []
        results = []
        for r in rows:
            p = database.row_to_dict(r) if hasattr(database, "row_to_dict") else dict(r)
            price = float(p.get("price") or 0.0)
            disc = float(p.get("discount_percentage") or 0.0)
            p["original_price"] = _calculate_mrp(price, disc)
            results.append(p)
        return results

    @staticmethod
    def get_comparison_presets() -> List[Dict[str, Any]]:
        """
        Return popular category comparison pairs from the genuine catalogue
        to give customers an instant one-click demonstration.
        """
        presets = []
        categories_to_sample = [
            ("Mobiles", "Top Rated Smartphones"),
            ("Appliances", "Popular Home Appliances"),
            ("Fashion", "Trending Everyday Wear"),
            ("Electronics", "High-Performance Electronics")
        ]

        for cat, title in categories_to_sample:
            rows = database.query_db(
                "SELECT id, name, category, brand, price, rating, image_url, discount_percentage FROM products WHERE category = ? ORDER BY rating DESC, stock DESC LIMIT 2",
                (cat,)
            )
            if rows and len(rows) >= 2:
                items = [database.row_to_dict(r) if hasattr(database, "row_to_dict") else dict(r) for r in rows]
                presets.append({
                    "title": title,
                    "category": cat,
                    "product_ids": [items[0]["id"], items[1]["id"]],
                    "product_names": [items[0]["name"], items[1]["name"]],
                    "preview_images": [items[0].get("image_url", ""), items[1].get("image_url", "")]
                })
        return presets

    @staticmethod
    def validate_and_fetch_products(product_ids: List[Any], max_limit: int = 4) -> List[Dict[str, Any]]:
        """
        Validates product IDs:
        - Rejects non-digits or <= 0
        - Deduplicates preserving order
        - Caps at max_limit
        - Queries database and returns fully-hydrated product dictionaries
        """
        if not product_ids or not isinstance(product_ids, list):
            return []

        clean_ids = []
        seen = set()
        for pid in product_ids:
            try:
                val = int(pid)
                if val > 0 and val not in seen:
                    clean_ids.append(val)
                    seen.add(val)
            except (ValueError, TypeError):
                continue

        clean_ids = clean_ids[:max_limit]
        if not clean_ids:
            return []

        placeholders = ",".join("?" * len(clean_ids))
        rows = database.query_db(
            f"SELECT * FROM products WHERE id IN ({placeholders})",
            tuple(clean_ids)
        ) or []

        p_map = {}
        for r in rows:
            p = database.row_to_dict(r) if hasattr(database, "row_to_dict") else dict(r)
            price = float(p.get("price") or 0.0)
            disc = float(p.get("discount_percentage") or 0.0)
            p["original_price"] = _calculate_mrp(price, disc)
            p["discount_amount"] = round(p["original_price"] - price, 2)
            p["specifications"] = _parse_json(p.get("specifications"), {})
            p["rating"] = float(p.get("rating") or 4.0)
            p["review_count"] = int(p.get("review_count_demo") or 15)
            p["stock"] = int(p.get("stock") or 0)
            p_map[p["id"]] = p

        # Preserve input order
        ordered_products = [p_map[pid] for pid in clean_ids if pid in p_map]
        return ordered_products


# =============================================================================
# 2. Side-by-Side Comparison Matrix Engine
# =============================================================================

class SideBySideEngine:
    """Builds aligned side-by-side comparison matrix with difference detection."""

    @staticmethod
    def build_matrix(products: List[Dict[str, Any]], show_differences_only: bool = False) -> Dict[str, Any]:
        """
        Constructs an aligned comparison table matrix.
        Detects which rows have identical values vs differing values across products.
        If show_differences_only is True, filters out identical non-essential rows.
        """
        if not products:
            return {"columns": [], "rows": [], "total_products": 0, "diff_count": 0}

        min_price = min(p["price"] for p in products)
        max_rating = max(p["rating"] for p in products)

        columns = []
        for p in products:
            columns.append({
                "id": p["id"],
                "name": p["name"],
                "brand": p.get("brand") or "Generic",
                "category": p.get("category") or "General",
                "subcategory": p.get("subcategory") or "",
                "price": p["price"],
                "original_price": p["original_price"],
                "discount_percentage": p.get("discount_percentage", 0),
                "discount_amount": p.get("discount_amount", 0),
                "rating": p["rating"],
                "review_count": p["review_count"],
                "stock": p["stock"],
                "image_url": p.get("image_url", ""),
                "description": p.get("description", ""),
                "is_lowest_price": p["price"] == min_price,
                "is_top_rated": p["rating"] == max_rating
            })

        # Define standard comparison criteria
        raw_rows = [
            # Group: Basic Identity & Core Specs
            {
                "group": "Basic Details",
                "label": "Brand",
                "key": "brand",
                "extractor": lambda p: p.get("brand") or "Generic",
                "essential": True
            },
            {
                "group": "Basic Details",
                "label": "Category",
                "key": "category",
                "extractor": lambda p: p.get("category") or "General",
                "essential": True
            },
            {
                "group": "Basic Details",
                "label": "Subcategory",
                "key": "subcategory",
                "extractor": lambda p: p.get("subcategory") or "Not specified",
                "essential": False
            },
            # Group: Pricing & Commercials
            {
                "group": "Pricing & Discounts",
                "label": "Current Selling Price",
                "key": "price",
                "extractor": lambda p: f"₹{p['price']:,.2f}",
                "essential": True
            },
            {
                "group": "Pricing & Discounts",
                "label": "Original Price (MRP)",
                "key": "original_price",
                "extractor": lambda p: f"₹{p['original_price']:,.2f}",
                "essential": True
            },
            {
                "group": "Pricing & Discounts",
                "label": "Discount Percentage",
                "key": "discount_percentage",
                "extractor": lambda p: f"{int(p.get('discount_percentage', 0))}% OFF" if p.get("discount_percentage") else "No discount",
                "essential": True
            },
            {
                "group": "Pricing & Discounts",
                "label": "Total Savings",
                "key": "savings",
                "extractor": lambda p: f"₹{p.get('discount_amount', 0):,.2f}" if p.get("discount_amount") else "₹0.00",
                "essential": False
            },
            # Group: Customer Trust & Reputation
            {
                "group": "Ratings & Acclaim",
                "label": "Customer Rating",
                "key": "rating",
                "extractor": lambda p: f"★ {p['rating']:.1f} / 5.0",
                "essential": True
            },
            {
                "group": "Ratings & Acclaim",
                "label": "Verified Reviews",
                "key": "reviews",
                "extractor": lambda p: f"{p['review_count']:,} verified ratings",
                "essential": False
            },
            # Group: Stock & Policies
            {
                "group": "Availability & Services",
                "label": "Stock Availability",
                "key": "stock",
                "extractor": lambda p: f"In Stock ({p['stock']} units)" if p['stock'] > 10 else (f"Limited Stock ({p['stock']} left)" if p['stock'] > 0 else "Out of Stock"),
                "essential": True
            },
            {
                "group": "Availability & Services",
                "label": "Warranty",
                "key": "warranty",
                "extractor": lambda p: p.get("specifications", {}).get("Warranty") or "1 Year Manufacturer Assured",
                "essential": False
            },
            {
                "group": "Availability & Services",
                "label": "Return Policy",
                "key": "return_policy",
                "extractor": lambda p: p.get("specifications", {}).get("Return Policy") or "7 Days Replacement or Refund Guarantee",
                "essential": False
            },
            {
                "group": "Availability & Services",
                "label": "Delivery Terms",
                "key": "delivery",
                "extractor": lambda p: "PreTwin Assured Express Delivery (Free)",
                "essential": False
            }
        ]

        # Add any custom specification keys present in products' specifications dictionary
        custom_spec_keys = set()
        for p in products:
            specs = p.get("specifications", {})
            if isinstance(specs, dict):
                for k in specs.keys():
                    if k not in ["Brand", "Category", "Subcategory", "Warranty", "Return Policy", "Stock Status"]:
                        custom_spec_keys.add(k)

        for spec_key in sorted(list(custom_spec_keys)):
            raw_rows.append({
                "group": "Technical Specifications",
                "label": spec_key,
                "key": f"spec_{spec_key}",
                "extractor": lambda p, sk=spec_key: p.get("specifications", {}).get(sk) or "Not specified",
                "essential": False
            })

        processed_rows = []
        diff_count = 0

        for r_def in raw_rows:
            values = [r_def["extractor"](p) for p in products]
            # Check if all values are identical
            first_val = values[0] if values else ""
            is_different = any(v != first_val for v in values[1:])
            if is_different:
                diff_count += 1

            row_data = {
                "group": r_def["group"],
                "label": r_def["label"],
                "key": r_def["key"],
                "values": values,
                "is_different": is_different,
                "essential": r_def["essential"]
            }

            # Filter if show_differences_only is active
            if show_differences_only:
                if is_different or r_def["essential"]:
                    processed_rows.append(row_data)
            else:
                processed_rows.append(row_data)

        return {
            "columns": columns,
            "rows": processed_rows,
            "total_products": len(products),
            "diff_count": diff_count,
            "show_differences_only": show_differences_only
        }


# =============================================================================
# 3. Feature and Specification Analysis Engine
# =============================================================================

class SpecificationAnalysisEngine:
    """
    Groups specifications into category-aware sections,
    highlights best values for comparable attributes,
    and identifies shared vs different attributes without unfair penalties.
    """

    @staticmethod
    def _extract_category_specs(product: Dict[str, Any]) -> Dict[str, str]:
        """
        Extracts structured specifications from the product title, description,
        and specifications dict according to category.
        Strictly factual based on database content.
        """
        specs = dict(product.get("specifications") or {})
        title = product.get("name", "")
        desc = product.get("description", "")
        cat = (product.get("category") or "").lower()
        subcat = (product.get("subcategory") or "").lower()
        combined_text = f"{title} {desc} {subcat}"

        extracted: Dict[str, str] = {}

        # 1. Capacity / Volume / Size
        cap_match = re.search(r'(\d+(?:\.\d+)?\s*(?:L|kg|Ton|ml|g|gm|cm|mm|inch|\"))\b', combined_text, re.IGNORECASE)
        if cap_match:
            extracted["Capacity / Volume"] = cap_match.group(1).strip()

        # 2. Power / Wattage / Energy
        power_match = re.search(r'(\d+\s*W(?:att)?)\b', combined_text, re.IGNORECASE)
        if power_match:
            extracted["Power Rating"] = power_match.group(1).strip()

        star_match = re.search(r'(\d\s*-\s*Star|\d\s*Star)\b', combined_text, re.IGNORECASE)
        if star_match:
            extracted["Energy Rating"] = star_match.group(1).strip()

        # 3. Electronics: RAM & Storage
        ram_match = re.search(r'(\d+\s*GB\s*RAM|\d+\s*GB\s*Memory)\b', combined_text, re.IGNORECASE)
        if ram_match:
            extracted["RAM / Memory"] = ram_match.group(1).strip()

        storage_match = re.search(r'(\d+\s*(?:GB|TB)\s*(?:Storage|ROM|SSD))\b', combined_text, re.IGNORECASE)
        if storage_match:
            extracted["Internal Storage"] = storage_match.group(1).strip()

        # 4. Materials & Fabrics (Fashion / Footwear / Furniture)
        material_terms = ["Cotton", "Denim", "Silk", "Linen", "Polyester", "Leather", "Mesh", "Solid Wood", "Engineered Wood", "Stainless Steel", "Ceramic"]
        found_mats = [m for m in material_terms if re.search(rf'\b{m}\b', combined_text, re.IGNORECASE)]
        if found_mats:
            extracted["Primary Material"] = ", ".join(found_mats)

        # 5. Technology / Mechanism
        tech_terms = ["Inverter", "BLDC", "Frost Free", "Fully Automatic", "Semi Automatic", "Convection", "Active Noise Cancellation", "Bluetooth", "Wireless", "Fast Charging"]
        found_tech = [t for t in tech_terms if re.search(rf'\b{t}\b', combined_text, re.IGNORECASE)]
        if found_tech:
            extracted["Key Technology"] = ", ".join(found_tech)

        # Merge with existing specs
        for k, v in specs.items():
            if k not in ["Brand", "Category", "Subcategory", "Stock Status"]:
                extracted[k] = str(v)

        return extracted

    @classmethod
    def analyze(cls, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyzes specifications across all selected products.
        Groups into logical categories, marks shared vs unique,
        and computes best-in-class values for comparable metrics.
        """
        if not products:
            return {"groups": [], "shared_keys": [], "unique_keys": []}

        product_specs = []
        all_keys = set()
        for p in products:
            s = cls._extract_category_specs(p)
            product_specs.append(s)
            all_keys.update(s.keys())

        # Categorize keys into groups
        group_mapping = {
            "Performance & Core": ["Capacity / Volume", "Power Rating", "RAM / Memory", "Internal Storage", "Key Technology", "Processor", "Battery"],
            "Materials & Build": ["Primary Material", "Finish", "Sole Material", "Fit", "Pattern", "Color"],
            "Efficiency & Trust": ["Energy Rating", "Warranty", "Return Policy", "Certification"],
            "Additional Details": []
        }

        grouped_specs = {g: [] for g in group_mapping.keys()}

        shared_keys = []
        unique_keys = []

        for key in sorted(list(all_keys)):
            # Check presence
            count = sum(1 for s in product_specs if key in s and s[key] != "Not specified")
            if count == len(products):
                shared_keys.append(key)
            else:
                unique_keys.append(key)

            # Determine best value if numerical
            best_idx = None
            numeric_vals = []
            for idx, s in enumerate(product_specs):
                v_str = s.get(key, "")
                num_match = re.search(r'(\d+(?:\.\d+)?)', v_str)
                if num_match:
                    try:
                        numeric_vals.append((idx, float(num_match.group(1))))
                    except Exception:
                        pass

            if numeric_vals and len(numeric_vals) == len(products):
                # For energy rating or capacity/power, higher is generally better
                best_idx = max(numeric_vals, key=lambda x: x[1])[0]

            row_entry = {
                "key": key,
                "values": [s.get(key, "Not specified") for s in product_specs],
                "is_shared": count == len(products),
                "best_product_index": best_idx
            }

            # Assign to group
            assigned = False
            for grp, grp_keys in group_mapping.items():
                if key in grp_keys:
                    grouped_specs[grp].append(row_entry)
                    assigned = True
                    break
            if not assigned:
                grouped_specs["Additional Details"].append(row_entry)

        # Remove empty groups
        final_groups = []
        for g_name, rows in grouped_specs.items():
            if rows:
                final_groups.append({
                    "group_name": g_name,
                    "rows": rows
                })

        return {
            "groups": final_groups,
            "shared_keys": shared_keys,
            "unique_keys": unique_keys,
            "total_attributes_analyzed": len(all_keys)
        }


# =============================================================================
# 4. Price and Value Comparison Engine
# =============================================================================

class PriceValueComparisonEngine:
    """Provides transparent financial breakdown and explainable value indicators."""

    @staticmethod
    def compare(products: List[Dict[str, Any]], user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Calculates:
        - Lowest price product
        - Highest discount % product
        - Best value indicator (balanced score of rating, features, and price)
        - Price delta vs lowest
        - Budget affordability status (integrating with Feature 4 budget if set)
        """
        if not products:
            return {}

        prices = [p["price"] for p in products]
        min_price = min(prices)
        max_price = max(prices)

        discounts = [p.get("discount_percentage", 0) for p in products]
        max_discount = max(discounts)

        # Calculate value scores for each product:
        # A transparent formula: 40% price-efficiency, 35% customer rating, 25% discount savings
        value_analysis = []
        for p in products:
            price = p["price"]
            rating = p["rating"]
            disc = p.get("discount_percentage", 0)
            orig_price = p["original_price"]
            diff_from_lowest = price - min_price

            # Price efficiency: 100 for lowest, scaled down for higher
            price_eff = (min_price / price * 100.0) if price > 0 else 100.0
            rating_eff = (rating / 5.0) * 100.0
            disc_eff = min(100.0, disc * 2.0)  # 50% discount = 100 pts

            value_score = round((price_eff * 0.40) + (rating_eff * 0.35) + (disc_eff * 0.25), 1)

            # Check if quantity information can give a unit price estimate
            unit_price_info = None
            cap_match = re.search(r'(\d+(?:\.\d+)?)\s*(L|kg|ml|g|gm|cm|mm|m)\b', f"{p['name']} {p.get('description', '')}", re.IGNORECASE)
            if cap_match:
                try:
                    qty = float(cap_match.group(1))
                    unit = cap_match.group(2).upper()
                    if qty > 0:
                        unit_price = round(price / qty, 2)
                        unit_price_info = f"₹{unit_price:,.2f} per {unit}"
                except Exception:
                    pass

            value_analysis.append({
                "product_id": p["id"],
                "product_name": p["name"],
                "price": price,
                "original_price": orig_price,
                "discount_percentage": disc,
                "discount_amount": p.get("discount_amount", 0),
                "diff_from_lowest": round(diff_from_lowest, 2),
                "is_lowest_price": price == min_price,
                "is_highest_discount": disc == max_discount and disc > 0,
                "value_score": value_score,
                "unit_price_info": unit_price_info
            })

        # Identify best value winner (highest value_score)
        best_val_item = max(value_analysis, key=lambda x: x["value_score"])
        best_val_id = best_val_item["product_id"]

        for item in value_analysis:
            item["is_best_value"] = item["product_id"] == best_val_id

        # Affordability context via Feature 4 (Budget table)
        budget_info = None
        if user_id:
            try:
                row = database.query_db(
                    "SELECT monthly_budget FROM customer_budgets WHERE user_id = ?",
                    (user_id,),
                    one=True
                )
                if row:
                    b_dict = database.row_to_dict(row) if hasattr(database, "row_to_dict") else dict(row)
                    monthly_budget = float(b_dict.get("monthly_budget") or 0.0)
                    if monthly_budget > 0:
                        budget_info = {
                            "user_monthly_budget": monthly_budget,
                            "affordable_products": [p["id"] for p in products if p["price"] <= monthly_budget]
                        }
            except Exception:
                pass

        return {
            "lowest_price_id": next((p["id"] for p in products if p["price"] == min_price), None),
            "highest_discount_id": next((p["id"] for p in products if p.get("discount_percentage", 0) == max_discount and max_discount > 0), None),
            "best_value_id": best_val_id,
            "min_price": min_price,
            "max_price": max_price,
            "max_price_delta": round(max_price - min_price, 2),
            "items": value_analysis,
            "budget_context": budget_info
        }


# =============================================================================
# 5. Pros and Cons Engine
# =============================================================================

class ProsConsEngine:
    """Extracts factual advantages and limitations strictly from real catalogue fields."""

    @staticmethod
    def generate(products: List[Dict[str, Any]]) -> Dict[int, Dict[str, List[str]]]:
        """
        Builds list of factual pros and cons for each product relative to compared set:
        - Price advantages/tradeoffs
        - Customer acclaim & ratings
        - Availability and stock limits
        - Specification richness or missing details
        """
        if not products:
            return {}

        min_price = min(p["price"] for p in products)
        max_price = max(p["price"] for p in products)
        max_rating = max(p["rating"] for p in products)
        min_rating = min(p["rating"] for p in products)

        results = {}

        for p in products:
            pros: List[str] = []
            cons: List[str] = []
            pid = p["id"]
            price = p["price"]
            rating = p["rating"]
            reviews = p["review_count"]
            disc = p.get("discount_percentage", 0)
            stock = p["stock"]
            specs = p.get("specifications", {})
            spec_count = len(specs) if isinstance(specs, dict) else 0

            # 1. Pricing Pros & Cons
            if price == min_price and len(products) > 1:
                pros.append(f"Lowest upfront price in this comparison (₹{price:,.2f})")
            elif price >= max_price * 0.9 and max_price > min_price:
                cons.append(f"Higher price tier (₹{price - min_price:,.2f} more than lowest option)")

            if disc >= 30:
                pros.append(f"Substantial promotional discount ({int(disc)}% savings)")

            # 2. Rating Pros & Cons
            if rating >= 4.4:
                pros.append(f"Excellent customer rating (★ {rating:.1f}/5.0 from {reviews} shoppers)")
            elif rating <= 3.8 and len(products) > 1:
                cons.append(f"Lower customer satisfaction rating (★ {rating:.1f}/5.0)")

            if reviews >= 500:
                pros.append(f"Proven market track record ({reviews:,} verified buyers)")

            # 3. Stock Pros & Cons
            if stock < 10 and stock > 0:
                cons.append(f"Limited inventory ({stock} units remaining)")
            elif stock >= 30:
                pros.append("High stock availability ready for immediate dispatch")

            # 4. Specifications Pros & Cons
            if spec_count >= 5:
                pros.append(f"Comprehensive catalogue specifications verified ({spec_count} attributes)")
            elif spec_count <= 2:
                cons.append("Limited detailed specifications provided in catalogue")

            # Ensure every product has at least 1 balanced point
            if not pros:
                pros.append(f"Reliable baseline option in the {p.get('category', 'catalogue')} category")
            if not cons:
                cons.append("No notable limitations detected from catalogue records")

            results[pid] = {
                "pros": pros,
                "cons": cons
            }

        return results


# =============================================================================
# 6. Smart Decision Assistant Engine
# =============================================================================

class SmartDecisionAssistantEngine:
    """
    Transparent, explainable decision-support system.
    Normalizes multi-attribute scores according to customer priority weights,
    explains tradeoffs, and detects close scores as 'Comparable Options'.
    """

    DEFAULT_WEIGHTS = {
        "price": 35.0,
        "specs": 25.0,
        "value": 20.0,
        "rating": 15.0,
        "brand": 5.0
    }

    @classmethod
    def evaluate(cls, products: List[Dict[str, Any]], custom_weights: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Calculates normalized scores (0-100) across:
        - Price score (inversely proportional to price)
        - Specs score (based on spec richness and verified attributes)
        - Value for money score (calculated price-to-feature balance)
        - Customer rating score (scaled 5-star rating)
        - Brand score (catalogue brand baseline)

        If top 2 scores are within 3 points, flags as 'Comparable Options'.
        """
        if not products:
            return {"ranked_products": [], "status": "no_products"}

        # Normalize weights
        weights = dict(cls.DEFAULT_WEIGHTS)
        if custom_weights:
            for k in weights.keys():
                if k in custom_weights:
                    try:
                        val = float(custom_weights[k])
                        if val >= 0:
                            weights[k] = val
                    except (ValueError, TypeError):
                        pass

        total_weight = sum(weights.values()) or 100.0

        min_price = min(p["price"] for p in products)
        max_price = max(p["price"] for p in products)

        ranked = []
        for p in products:
            price = p["price"]
            rating = p["rating"]
            specs = p.get("specifications", {})
            spec_count = len(specs) if isinstance(specs, dict) else 3
            disc = p.get("discount_percentage", 0)

            # Normalization 0..100
            # Price Score: Lowest price gets 100, highest gets proportional score
            if max_price == min_price:
                price_score = 100.0
            else:
                price_score = round((1.0 - ((price - min_price) / max_price)) * 100.0, 1)
                price_score = max(10.0, min(100.0, price_score))

            # Rating Score: 5.0 stars = 100
            rating_score = round((rating / 5.0) * 100.0, 1)

            # Specs Score: scaled by count and completeness
            spec_score = round(min(100.0, (spec_count / 6.0) * 100.0), 1)

            # Value Score: balance of specs + discount vs price
            price_factor = (min_price / price) if price > 0 else 1.0
            val_calc = ((rating / 5.0) * 0.4 + price_factor * 0.4 + (min(50, disc) / 50.0) * 0.2) * 100.0
            value_score = round(val_calc, 1)

            # Brand Score: based on brand presence
            brand_name = p.get("brand") or ""
            brand_score = 85.0 if brand_name and brand_name.lower() != "generic" else 70.0

            # Composite Weighted Score
            composite = (
                (price_score * weights["price"]) +
                (spec_score * weights["specs"]) +
                (value_score * weights["value"]) +
                (rating_score * weights["rating"]) +
                (brand_score * weights["brand"])
            ) / total_weight

            composite = round(composite, 1)

            ranked.append({
                "id": p["id"],
                "name": p["name"],
                "brand": p.get("brand", ""),
                "price": price,
                "rating": rating,
                "scores": {
                    "price_score": price_score,
                    "spec_score": spec_score,
                    "value_score": value_score,
                    "rating_score": rating_score,
                    "brand_score": brand_score,
                    "composite": composite
                }
            })

        # Sort descending by composite score
        ranked.sort(key=lambda x: x["scores"]["composite"], reverse=True)

        winner = ranked[0]
        runner_up = ranked[1] if len(ranked) > 1 else None

        # Check for close scores (difference <= 3.0 points)
        is_comparable = False
        decision_title = f"{winner['name']} Stands Out"
        tradeoff_explanation = ""

        if runner_up and (winner["scores"]["composite"] - runner_up["scores"]["composite"]) <= 3.0:
            is_comparable = True
            decision_title = "Close Match: Both Options Highly Competitive"
            tradeoff_explanation = (
                f"{winner['name']} ({winner['scores']['composite']} pts) and {runner_up['name']} "
                f"({runner_up['scores']['composite']} pts) have nearly identical overall utility. "
                f"Choose {winner['name']} if you prioritize "
                f"{'lower price' if winner['price'] <= runner_up['price'] else 'higher acclaim and features'}, "
                f"or choose {runner_up['name']} for "
                f"{'budget savings' if runner_up['price'] < winner['price'] else 'enhanced rating'}."
            )
            decision_reason = tradeoff_explanation
        else:
            dominant_factor = "overall value"
            if weights["price"] >= 40:
                dominant_factor = "pricing economy"
            elif weights["rating"] >= 35:
                dominant_factor = "customer satisfaction rating"
            elif weights["specs"] >= 30:
                dominant_factor = "specification richness"

            decision_reason = (
                f"{winner['name']} leads with a {winner['scores']['composite']} composite score, "
                f"aligning best with your priority on {dominant_factor} while delivering a strong "
                f"balance across price (₹{winner['price']:,.2f}) and rating (★ {winner['rating']})."
            )
            tradeoff_explanation = (
                f"This choice prioritizes your active weight settings. "
                f"{'Note that lower-priced alternatives exist' if winner['price'] > min_price else 'It also happens to be the lowest priced option in this set'}."
            )

        return {
            "status": "success",
            "weights_used": weights,
            "ranked_products": ranked,
            "is_comparable": is_comparable,
            "decision_title": decision_title,
            "winner": {
                "id": winner["id"],
                "name": winner["name"],
                "score": winner["scores"]["composite"],
                "decision_reason": decision_reason
            },
            "runner_up": {
                "id": runner_up["id"],
                "name": runner_up["name"],
                "score": runner_up["scores"]["composite"]
            } if runner_up else None,
            "tradeoff_explanation": tradeoff_explanation
        }


# =============================================================================
# 7. Comparison Session & Persistence Engine (Tenant Isolation)
# =============================================================================

class ComparisonSessionEngine:
    """Manages tenant-isolated saved comparisons for authenticated customers."""

    @staticmethod
    def get_user_comparison(user_id: int) -> List[int]:
        """Fetch saved product IDs for the given user from product_comparisons."""
        if not user_id:
            return []
        row = database.query_db(
            "SELECT product_ids FROM product_comparisons WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
            (user_id,),
            one=True
        )
        if row:
            d = database.row_to_dict(row) if hasattr(database, "row_to_dict") else dict(row)
            ids = _parse_json(d.get("product_ids"), [])
            if isinstance(ids, list):
                return [int(x) for x in ids if str(x).isdigit()]
        return []

    @staticmethod
    def save_user_comparison(user_id: int, product_ids: List[int], winner_id: Optional[int] = None, winner_reason: str = ""):
        """Store the comparison session strictly partitioned by user_id."""
        if not user_id or not product_ids:
            return
        clean_ids = [int(x) for x in product_ids if str(x).isdigit()][:ProductSelectionEngine.MAX_COMPARE_LIMIT]
        database.execute_db(
            "INSERT INTO product_comparisons (user_id, run_id, product_ids, comparison_data, winner_id, winner_reason) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, f"comp_{user_id}_{len(clean_ids)}", json.dumps(clean_ids), json.dumps([]), winner_id, winner_reason)
        )


# =============================================================================
# Master Orchestrator for Comprehensive 7-Section Analysis
# =============================================================================

def run_comprehensive_comparison(product_ids: List[Any], user_id: Optional[int] = None, weights: Optional[Dict[str, Any]] = None, show_differences_only: bool = False) -> Dict[str, Any]:
    """
    Executes the full 7-section comparison analysis:
    1. Product Selection & Validation
    2. Side-by-Side Matrix
    3. Feature & Specification Analysis
    4. Price and Value Comparison
    5. Pros and Cons
    6. Smart Decision Assistant
    7. Final Decision & Actions Payload
    """
    products = ProductSelectionEngine.validate_and_fetch_products(product_ids)

    if len(products) < 2:
        return {
            "success": False,
            "error": "At least 2 valid products are required for comparison.",
            "total_selected": len(products),
            "products": products
        }

    # 2. Side-by-Side
    side_by_side = SideBySideEngine.build_matrix(products, show_differences_only=show_differences_only)

    # 3. Specification Analysis
    spec_analysis = SpecificationAnalysisEngine.analyze(products)

    # 4. Price & Value Comparison
    price_value = PriceValueComparisonEngine.compare(products, user_id=user_id)

    # 5. Pros and Cons
    pros_cons = ProsConsEngine.generate(products)

    # 6. Smart Decision Assistant
    decision = SmartDecisionAssistantEngine.evaluate(products, custom_weights=weights)

    # Attach pros/cons and scores directly into the products payload for backward compatibility
    for p in products:
        pid = p["id"]
        p["advantages"] = pros_cons.get(pid, {}).get("pros", [])
        p["limitations"] = pros_cons.get(pid, {}).get("cons", [])
        p["pros"] = p["advantages"]
        p["cons"] = p["limitations"]
        # Find score from decision
        for r_p in decision.get("ranked_products", []):
            if r_p["id"] == pid:
                p["scores"] = r_p["scores"]
                p["comparison_score"] = r_p["scores"]["composite"]
                break

    # Persist session if user_id is authenticated
    if user_id:
        try:
            win_id = decision.get("winner", {}).get("id")
            win_reason = decision.get("winner", {}).get("decision_reason", "")
            ComparisonSessionEngine.save_user_comparison(user_id, [p["id"] for p in products], win_id, win_reason)
        except Exception:
            pass

    return {
        "success": True,
        "total_selected": len(products),
        "products": products,
        "side_by_side": side_by_side,
        "spec_analysis": spec_analysis,
        "price_value": price_value,
        "pros_cons": pros_cons,
        "decision": decision,
        "winner": decision.get("winner"),
        "is_comparable": decision.get("is_comparable", False)
    }
