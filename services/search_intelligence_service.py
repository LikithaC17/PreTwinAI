"""
services/search_intelligence_service.py
---------------------------------------
Smart Product Discovery Intelligence Engine (Feature 3):
1. QueryUnderstandingEngine: Parses natural-language queries, price caps, categories, brands, and handles spelling typos.
2. SearchSuggestionEngine: Fast prefix autocomplete, "Did You Mean?" spelling corrections, and zero-result alternatives.
3. DiscoveryCollectionsEngine: Curates real catalogue collections (Popular Products, Budget Finds, Best Discounts, New Arrivals).
4. ProductAlternativesEngine: Finds similar alternatives, budget-friendly options, and premium upgrades with explainable differences.
5. CategoryExplorationEngine: Provides comprehensive data on all 20 catalogue categories with live counts and subcategories.
"""

from __future__ import annotations

import logging
import math
import re
from typing import Any, Dict, List, Optional, Tuple

import database

logger = logging.getLogger(__name__)


# Category emoji mapping for rich visual cues in category exploration
CATEGORY_ICONS = {
    "Fashion": "👗",
    "Mobiles": "📱",
    "Electronics": "🎧",
    "Laptops & Computers": "💻",
    "Home & Kitchen": "🍳",
    "Appliances": "🧊",
    "Beauty, Toys & More": "💄",
    "Toys & Baby Products": "🧸",
    "Food & Grocery": "🛒",
    "Sports & Fitness": "🏋️",
    "Books & Stationery": "📚",
    "Furniture": "🛋️",
    "Footwear": "👟",
    "Watches & Accessories": "⌚",
    "TVs & Home Entertainment": "📺",
    "Personal Care": "🪒",
    "Automotive Accessories": "🚗",
    "Health & Wellness": "🩺",
    "Pet Supplies": "🐾",
    "Travel & Luggage": "🧳",
}


def _levenshtein_distance(s1: str, s2: str) -> int:
    """Compute Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return _levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def _format_product(row: Any) -> Dict[str, Any]:
    """Format database product row with full calculated fields."""
    d = dict(row)
    price = float(d.get("price") or 0.0)
    disc = int(d.get("discount_percentage") or 15)
    d["price"] = price
    d["discount_percentage"] = disc
    d["rating"] = float(d.get("rating") or 4.2)
    d["review_count_demo"] = int(d.get("review_count_demo") or 120)

    if 0 < disc < 100:
        d["mrp"] = round(price / (1 - disc / 100.0), 2)
    else:
        d["mrp"] = round(price * 1.25, 2)

    return d


class QueryUnderstandingEngine:
    """
    Parses conversational and keyword queries to extract:
    - Min / Max price limits (e.g. 'under 3000', 'between 1000 and 5000', '< 1500')
    - Category intent (matching catalogue categories and aliases)
    - Brand intent
    - Cleaned search keywords
    - Spelling typo corrections ('Did You Mean?')
    """

    CATEGORY_KEYWORDS = {
        "Fashion": ["shoe", "shoes", "shirt", "tshirt", "t-shirt", "jeans", "dress", "saree", "jacket", "hoodie", "sneaker", "kurti", "top", "trousers", "clothing"],
        "Mobiles": ["phone", "smartphone", "iphone", "samsung", "oneplus", "redmi", "mobile", "android", "5g", "pixel"],
        "Electronics": ["earbuds", "headphone", "audio", "speaker", "bluetooth", "power bank", "smartwatch", "charger", "cable", "tws"],
        "Laptops & Computers": ["laptop", "keyboard", "mouse", "monitor", "pc", "macbook", "ram", "ssd", "printer", "computer"],
        "Home & Kitchen": ["kettle", "blender", "coffee", "lamp", "cookware", "pan", "bottle", "bedsheet", "mixer", "air fryer", "curtain", "kitchen"],
        "Personal Care": ["trimmer", "shaver", "toothbrush", "skincare", "serum", "perfume", "cream", "face wash", "lotion", "grooming"],
        "Sports & Fitness": ["yoga", "dumbbell", "gym", "treadmill", "cycle", "protein", "fitness", "badminton", "cricket", "workout"],
        "Food & Grocery": ["tea", "coffee", "snack", "nuts", "chocolate", "oil", "organic", "dry fruits", "spices", "grocery"],
        "Watches & Accessories": ["watch", "belt", "wallet", "sunglasses", "handbag", "backpack", "accessories"],
        "Appliances": ["refrigerator", "washing machine", "microwave", "ac", "air conditioner", "heater", "vacuum", "appliance"],
        "Beauty, Toys & More": ["makeup", "lipstick", "mascara", "cosmetics", "beauty"],
        "Toys & Baby Products": ["toy", "puzzle", "doll", "action figure", "baby", "diaper", "stroller", "walker", "rattle", "soft toy"],
        "Books & Stationery": ["book", "novel", "diary", "notebook", "pen", "stationery", "textbook"],
        "Furniture": ["sofa", "bed", "chair", "table", "dining table", "bookshelf", "wardrobe", "desk", "mattress"],
        "Footwear": ["footwear", "sandals", "flip flops", "boots", "loafers", "formal shoes", "slippers", "heels", "sneakers"],
        "TVs & Home Entertainment": ["tv", "television", "home theatre", "projector", "soundbar", "smart tv", "led tv"],
        "Automotive Accessories": ["car cover", "bike cover", "car dash cam", "helmet", "car charger", "tyre", "automotive"],
        "Health & Wellness": ["bp monitor", "thermometer", "weighing scale", "pulse oximeter", "vitamins", "health", "wellness"],
        "Pet Supplies": ["dog food", "cat food", "pet collar", "pet leash", "aquarium", "pet shampoo", "pet"],
        "Travel & Luggage": ["suitcase", "trolley", "duffel bag", "travel bag", "rucksack", "luggage", "travel"],
    }

    TYPO_CORRECTIONS = {
        "samung": "samsung",
        "samsng": "samsung",
        "sumsung": "samsung",
        "adida": "adidas",
        "adiddas": "adidas",
        "nik": "nike",
        "neke": "nike",
        "aple": "apple",
        "appel": "apple",
        "snoy": "sony",
        "xiomi": "xiaomi",
        "redmy": "redmi",
        "oneplus": "oneplus",
        "lenvo": "lenovo",
        "pma": "puma",
        "bote": "boat",
        "boAt": "boat",
        "shoos": "shoes",
        "shoo": "shoes",
        "phne": "phone",
        "fone": "phone",
        "lapttop": "laptop",
        "labtop": "laptop",
        "earfone": "earbuds",
        "earfones": "earbuds",
        "airpod": "earbuds",
        "airpods": "earbuds",
        "wacth": "watch",
        "wtch": "watch",
        "shrt": "shirt",
        "t-shrt": "tshirt",
        "pant": "pants",
        "hedphone": "headphone",
        "traker": "tracker",
        "snikers": "sneakers",
        "blutooth": "bluetooth",
    }

    @classmethod
    def parse_query(cls, raw_query: str) -> Dict[str, Any]:
        """
        Analyze the search query and extract structured intent:
        - max_price, min_price
        - category
        - brand
        - clean_keywords
        - did_you_mean / corrected_query
        """
        query = (raw_query or "").strip().lower()
        if not query:
            return {
                "original_query": "",
                "clean_keywords": [],
                "max_price": None,
                "min_price": None,
                "category": None,
                "brand": None,
                "did_you_mean": None,
                "extracted_filters": {},
            }

        # 1. Spelling normalization & "Did You Mean"
        words = query.split()
        corrected_words = []
        has_typo = False
        for w in words:
            # check exact dictionary
            clean_w = re.sub(r'[^a-z0-9]', '', w)
            if clean_w in cls.TYPO_CORRECTIONS:
                corrected_words.append(cls.TYPO_CORRECTIONS[clean_w])
                has_typo = True
            else:
                # Fuzzy check against known brand or category keywords if length > 4
                closest_match = None
                if len(clean_w) >= 4:
                    for target in ["samsung", "adidas", "nike", "apple", "shoes", "laptop", "phone", "watch", "headphones"]:
                        if _levenshtein_distance(clean_w, target) == 1:
                            closest_match = target
                            break
                if closest_match:
                    corrected_words.append(closest_match)
                    has_typo = True
                else:
                    corrected_words.append(w)

        corrected_query = " ".join(corrected_words)
        did_you_mean = corrected_query if (has_typo and corrected_query.lower() != query.lower()) else None
        effective_query = corrected_query.lower()

        # 2. Price extraction
        max_price = None
        min_price = None

        # Pattern: between X and Y
        between_match = re.search(r'between\s*(?:rs\.?|inr|₹)?\s*([0-9,]+)\s*(?:and|to|-)\s*(?:rs\.?|inr|₹)?\s*([0-9,]+)', effective_query)
        if between_match:
            try:
                min_price = float(between_match.group(1).replace(",", ""))
                max_price = float(between_match.group(2).replace(",", ""))
            except Exception:
                pass

        if max_price is None:
            # Pattern: under / below / less than / < / budget of
            max_match = re.search(r'(?:under|below|less than|<|budget of|max(?:imum)? of)\s*(?:rs\.?|inr|₹)?\s*([0-9,]+)', effective_query)
            if max_match:
                try:
                    max_price = float(max_match.group(1).replace(",", ""))
                except Exception:
                    max_price = None

        if min_price is None:
            # Pattern: above / more than / > / min of
            min_match = re.search(r'(?:above|more than|>|min(?:imum)? of)\s*(?:rs\.?|inr|₹)?\s*([0-9,]+)', effective_query)
            if min_match:
                try:
                    min_price = float(min_match.group(1).replace(",", ""))
                except Exception:
                    min_price = None

        # 3. Category detection
        detected_category = None
        for cat, kw_list in cls.CATEGORY_KEYWORDS.items():
            if any(re.search(rf'\b{re.escape(kw)}\b', effective_query) for kw in kw_list):
                detected_category = cat
                break

        # 4. Brand detection
        detected_brand = None
        # Common catalog brands
        known_brands = [
            "Apple", "Samsung", "Nike", "Adidas", "Puma", "Boat", "Sony", "Dell", "HP", "Acer", "Asus",
            "Lenovo", "OnePlus", "Redmi", "Xiaomi", "Bata", "Allen Solly", "Biba", "Philips", "Bajaj",
            "Prestige", "Whirlpool", "LG", "Voltas", "Fastrack", "Titan", "Casio", "Noise", "Fire-Boltt",
            "Beardo", "Biotique", "Nivea", "L'Oreal", "Maybelline", "Wildcraft", "American Tourister",
            "Safari", "Skybags", "Pigeon", "Hawkins", "Milton", "Cello", "Dettol", "Himalaya"
        ]
        for b in known_brands:
            if re.search(rf'\b{re.escape(b.lower())}\b', effective_query):
                detected_brand = b
                break

        # 5. Clean query keywords
        # Remove price phrases and filler words
        clean_q = re.sub(r'(?:under|below|less than|above|more than|<|>|budget of|between|and|to|find|show|me|best|cheap|good|inr|rs\.?|₹|\d+)', ' ', effective_query)
        clean_words = [w for w in clean_q.split() if len(w) > 2]

        return {
            "original_query": raw_query,
            "corrected_query": corrected_query,
            "did_you_mean": did_you_mean,
            "max_price": max_price,
            "min_price": min_price,
            "category": detected_category,
            "brand": detected_brand,
            "extracted_keywords": clean_words,
            "clean_keywords": clean_words,
        }


class SearchSuggestionEngine:
    """
    Supplies fast autocomplete suggestions, category/brand hints,
    and fallback alternatives when zero products match.
    """

    POPULAR_SEARCHES = [
        "Running Shoes",
        "Wireless Earbuds",
        "Smart Watch",
        "Cotton Casual Shirt",
        "5G Smartphone",
        "Gaming Laptop",
        "Bluetooth Speaker",
        "Stainless Steel Water Bottle",
        "Trimmer for Men",
        "Yoga Mat",
    ]

    @classmethod
    def get_suggestions(cls, prefix: str, limit: int = 8) -> Dict[str, Any]:
        """
        Generate autocomplete suggestions partitioned into brands, categories, and products.
        """
        p = (prefix or "").strip().lower()
        if not p:
            return {
                "suggestions": [
                    {"text": term, "type": "popular", "query": term}
                    for term in cls.POPULAR_SEARCHES[:limit]
                ],
                "did_you_mean": None
            }

        # Check typo
        parsed = QueryUnderstandingEngine.parse_query(p)
        did_you_mean = parsed.get("did_you_mean")
        search_target = parsed.get("corrected_query", p).lower()

        suggestions = []

        # 1. Category matches
        cat_rows = database.query_db(
            "SELECT DISTINCT category FROM products WHERE LOWER(category) LIKE ? LIMIT 3",
            (f"%{search_target}%",)
        )
        for r in cat_rows:
            suggestions.append({
                "text": f"in {r['category']}",
                "type": "category",
                "category": r["category"],
                "query": r["category"],
            })

        # 2. Brand matches
        brand_rows = database.query_db(
            "SELECT DISTINCT brand FROM products WHERE LOWER(brand) LIKE ? AND brand IS NOT NULL AND brand != '' LIMIT 3",
            (f"{search_target}%",)
        )
        for r in brand_rows:
            suggestions.append({
                "text": f"{r['brand']} (Brand)",
                "type": "brand",
                "brand": r["brand"],
                "query": r["brand"],
            })

        # 3. Product title matches
        prod_rows = database.query_db(
            "SELECT name, category FROM products WHERE LOWER(name) LIKE ? LIMIT ?",
            (f"%{search_target}%", limit)
        )
        for r in prod_rows:
            if len(suggestions) < limit:
                suggestions.append({
                    "text": r["name"],
                    "type": "product",
                    "category": r["category"],
                    "query": r["name"],
                })

        # Fallback to popular searches if sparse
        if len(suggestions) < limit:
            for term in cls.POPULAR_SEARCHES:
                if term.lower() not in [s["text"].lower() for s in suggestions] and len(suggestions) < limit:
                    suggestions.append({
                        "text": term,
                        "type": "popular",
                        "query": term
                    })

        return {
            "suggestions": suggestions[:limit],
            "did_you_mean": did_you_mean,
            "query": prefix,
        }

    @classmethod
    def get_zero_result_fallback(cls, query: str = "") -> Dict[str, Any]:
        """Provide zero-result fallback recommendations and tips to loosen filters."""
        # Top 4 popular categories
        cat_rows = database.query_db(
            "SELECT category, count(*) as count FROM products GROUP BY category ORDER BY count DESC LIMIT 6"
        )
        categories = [r["category"] for r in cat_rows]

        # Top 4 trending products
        trend_rows = database.query_db(
            "SELECT * FROM products WHERE rating >= 4.5 ORDER BY review_count_demo DESC LIMIT 4"
        )
        trending = [_format_product(r) for r in trend_rows]

        return {
            "message": "No exact products matched your search.",
            "suggestions": [
                "Check for spelling mistakes in your search query.",
                "Try broader keywords or remove specific price filters.",
                "Browse through our popular catalogue categories below.",
            ],
            "popular_categories": categories,
            "trending_products": trending,
        }


class DiscoveryCollectionsEngine:
    """
    Curates genuine catalogue collections strictly from pretwinshop.db:
    1. Popular Products (rating >= 4.3 with high reviews)
    2. Budget Finds (price <= 999 and rating >= 4.0)
    3. Best Discounts (highest discount percentages 30%+)
    4. New Arrivals (latest items in catalogue)
    """

    @classmethod
    def get_collection(cls, collection_type: str = "popular", limit: int = 12) -> Dict[str, Any]:
        """Fetch curated collection products."""
        ctype = (collection_type or "popular").lower().strip()

        if ctype in ("budget", "budget_finds", "under_999"):
            title = "Budget Finds (Under ₹999)"
            description = "High-quality customer favorites priced under ₹999 with 4★+ ratings."
            sql = "SELECT * FROM products WHERE price <= 999 AND rating >= 4.0 ORDER BY rating DESC, price ASC LIMIT ?"
            params = [limit]

        elif ctype in ("discount", "best_discounts", "offers"):
            title = "Best Discounts (30% - 70% Off)"
            description = "Maximum savings on authentic brands verified by PreTwin."
            sql = "SELECT * FROM products WHERE discount_percentage >= 30 ORDER BY discount_percentage DESC, rating DESC LIMIT ?"
            params = [limit]

        elif ctype in ("new", "new_arrivals", "latest"):
            title = "New Arrivals"
            description = "Recently introduced products across all 20 categories."
            sql = "SELECT * FROM products ORDER BY id DESC LIMIT ?"
            params = [limit]

        else:  # default 'popular'
            ctype = "popular"
            title = "Popular Products"
            description = "Top-rated customer bestsellers with genuine 4.3★+ reviews."
            sql = "SELECT * FROM products WHERE rating >= 4.3 ORDER BY rating DESC, review_count_demo DESC LIMIT ?"
            params = [limit]

        rows = database.query_db(sql, tuple(params))
        products = [_format_product(r) for r in rows]

        return {
            "collection_type": ctype,
            "title": title,
            "description": description,
            "total": len(products),
            "products": products,
        }


class ProductAlternativesEngine:
    """
    Identifies related products and alternatives for any given product:
    - Similar Alternatives (within ±30% price range, same category/subcategory)
    - Budget-Friendly Alternative (lower price by 15-50%, high rating)
    - Premium Upgrade (higher rating or premium tier in same category)
    Includes explainable differences for each alternative.
    """

    @classmethod
    def get_alternatives(cls, product_id: int, limit: int = 4) -> Dict[str, Any]:
        """
        Find comparable products with transparent, explainable differences.
        """
        source_row = database.query_db("SELECT * FROM products WHERE id = ?", (product_id,), one=True)
        if not source_row:
            return {"error": "Product not found", "alternatives": []}

        source = _format_product(source_row)
        cat = source["category"]
        subcat = source.get("subcategory")
        price = source["price"]
        rating = source["rating"]

        # 1. Fetch candidates from same category or subcategory
        where_clauses = ["id != ?"]
        params = [product_id]

        if subcat:
            where_clauses.append("(subcategory = ? OR category = ?)")
            params.extend([subcat, cat])
        else:
            where_clauses.append("category = ?")
            params.append(cat)

        where_sql = " AND ".join(where_clauses)
        cand_rows = database.query_db(f"SELECT * FROM products WHERE {where_sql} LIMIT 50", tuple(params))
        candidates = [_format_product(r) for r in cand_rows]

        if not candidates:
            # Fallback to general category
            cand_rows = database.query_db("SELECT * FROM products WHERE id != ? AND category = ? LIMIT 20", (product_id, cat))
            candidates = [_format_product(r) for r in cand_rows]

        # Categorize alternatives
        budget_options = []
        similar_options = []
        upgrade_options = []

        for cand in candidates:
            c_price = cand["price"]
            c_rating = cand["rating"]
            price_ratio = c_price / max(price, 1.0)

            if price_ratio <= 0.85 and c_rating >= 3.8:
                # Budget alternative
                savings = price - c_price
                cand["alternative_type"] = "budget"
                cand["alternative_badge"] = "Budget-Friendly Choice"
                cand["explanation"] = f"Save ₹{int(savings):,} ({int((savings/max(price,1))*100)}% less) with solid {c_rating:.1f}★ rating."
                budget_options.append(cand)

            elif 0.70 <= price_ratio <= 1.30:
                # Similar alternative
                cand["alternative_type"] = "similar"
                cand["alternative_badge"] = "Similar Alternative"
                price_diff = abs(c_price - price)
                diff_str = f"Within ₹{int(price_diff):,} of target" if price_diff > 0 else "Same price tier"
                cand["explanation"] = f"Comparable {c_rating:.1f}★ rating in {cand.get('brand', 'same brand')}. {diff_str}."
                similar_options.append(cand)

            elif price_ratio > 1.15 and c_rating >= rating:
                # Premium upgrade
                cand["alternative_type"] = "premium"
                cand["alternative_badge"] = "Premium Upgrade"
                cand["explanation"] = f"Higher {c_rating:.1f}★ rating with enhanced brand prestige."
                upgrade_options.append(cand)

        # Sort each tier
        budget_options.sort(key=lambda x: (x["price"], -x["rating"]))
        similar_options.sort(key=lambda x: -x["rating"])
        upgrade_options.sort(key=lambda x: -x["rating"])

        alternatives = []
        # Add 1 budget option if present
        if budget_options:
            alternatives.append(budget_options[0])
        # Add 1 premium upgrade if present
        if upgrade_options:
            alternatives.append(upgrade_options[0])
        # Add similar options to fill up to limit
        for opt in similar_options:
            if len(alternatives) < limit and opt["id"] not in [a["id"] for a in alternatives]:
                alternatives.append(opt)
        # If still space, add remaining budget or upgrades
        for opt in budget_options[1:] + upgrade_options[1:]:
            if len(alternatives) < limit and opt["id"] not in [a["id"] for a in alternatives]:
                alternatives.append(opt)

        return {
            "source_product": source,
            "total_alternatives": len(alternatives),
            "alternatives": alternatives[:limit],
        }


class CategoryExplorationEngine:
    """
    Supplies all 20 catalogue categories with real-time product counts,
    subcategories, price brackets, and icons.
    """

    @classmethod
    def get_all_categories_summary(cls) -> List[Dict[str, Any]]:
        """Retrieve structured catalogue summary for all 20 categories."""
        rows = database.query_db("""
            SELECT 
                category, 
                COUNT(*) as product_count,
                MIN(price) as min_price,
                MAX(price) as max_price,
                AVG(rating) as avg_rating
            FROM products 
            GROUP BY category 
            ORDER BY category ASC
        """)

        categories = []
        for r in rows:
            cat_name = r["category"]
            subcat_rows = database.query_db(
                "SELECT DISTINCT subcategory FROM products WHERE category = ? AND subcategory IS NOT NULL AND subcategory != '' ORDER BY subcategory",
                (cat_name,)
            )
            subcats = [s["subcategory"] for s in subcat_rows]

            categories.append({
                "name": cat_name,
                "icon": CATEGORY_ICONS.get(cat_name, "🛍️"),
                "product_count": r["product_count"],
                "min_price": round(float(r["min_price"] or 0), 2),
                "max_price": round(float(r["max_price"] or 0), 2),
                "avg_rating": round(float(r["avg_rating"] or 4.0), 1),
                "subcategories": subcats,
                "subcategory_count": len(subcats),
            })

        return categories
