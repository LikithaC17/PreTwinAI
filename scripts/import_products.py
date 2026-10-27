# -*- coding: utf-8 -*-
"""
scripts/import_products.py
Reusable, production-grade Product Ingestion & Synchronization Pipeline for PreTwin.
Supports importing catalogue data from JSON or CSV feeds.
Validates fields, ranges, and types, and performs safe upserts that preserve existing
product IDs (1-1040), foreign keys (cart, wishlist, orders, recommendations, purchase history).
"""

import os
import sys
import json
import csv
import argparse
import sqlite3
from typing import Dict, Any, List, Tuple

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB = os.path.join(PROJECT_ROOT, "pretwinshop.db")

VALID_CATEGORIES = {
    "Fashion", "Mobiles", "Electronics", "Beauty, Toys & More", "Home & Kitchen",
    "Appliances", "Toys & Baby Products", "Food & Grocery", "Sports & Fitness",
    "Books & Stationery", "Furniture", "Footwear", "Watches & Accessories",
    "Laptops & Computers", "TVs & Home Entertainment", "Personal Care",
    "Automotive Accessories", "Health & Wellness", "Pet Supplies", "Travel & Luggage"
}

def validate_product(record: Dict[str, Any], idx: int) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Validates a product record.
    Returns (is_valid, error_reason, sanitized_record).
    """
    name = str(record.get("name") or "").strip()
    if not name or len(name) < 2:
        return False, f"Row {idx}: Missing or invalid 'name' (must be >= 2 characters)", record

    category = str(record.get("category") or "").strip()
    if not category:
        return False, f"Row {idx}: Missing 'category'", record

    try:
        price = float(record.get("price") or 0)
        if price <= 0:
            return False, f"Row {idx}: 'price' must be greater than 0 (got {price})", record
    except (ValueError, TypeError):
        return False, f"Row {idx}: 'price' must be a numeric value", record

    image_url = str(record.get("image_url") or "").strip()
    if not image_url:
        return False, f"Row {idx}: Missing 'image_url'", record

    # Validate or default optional fields
    subcategory = str(record.get("subcategory") or "").strip() or category
    brand = str(record.get("brand") or "").strip() or "PreTwin Assured"

    try:
        rating = float(record.get("rating", 4.2))
        rating = max(1.0, min(5.0, round(rating, 1)))
    except (ValueError, TypeError):
        rating = 4.2

    try:
        stock = int(record.get("stock", 50))
        if stock < 0: stock = 0
    except (ValueError, TypeError):
        stock = 50

    try:
        discount = float(record.get("discount_percentage", 15))
        discount = max(0.0, min(90.0, round(discount, 1)))
    except (ValueError, TypeError):
        discount = 15.0

    try:
        reviews = int(record.get("review_count_demo", 120))
        if reviews < 0: reviews = 0
    except (ValueError, TypeError):
        reviews = 120

    featured = 1 if record.get("featured") in (1, True, "1", "true", "True") else 0
    source_type = str(record.get("source_type") or "curated_feed").strip()
    source_id = str(record.get("source_id") or "").strip()
    description = str(record.get("description") or f"High quality {name} crafted for premium performance and durability.").strip()

    # Specifications handling
    specs = record.get("specifications")
    if isinstance(specs, dict):
        specs_json = json.dumps(specs)
    elif isinstance(specs, str) and specs.strip().startswith("{"):
        specs_json = specs.strip()
    else:
        specs_json = json.dumps({
            "Brand": brand,
            "Category": category,
            "Subcategory": subcategory,
            "Warranty": "1 Year Manufacturer Warranty",
            "Return Policy": "7 Days Return / Exchange Policy",
            "Stock Status": "In Stock" if stock > 0 else "Out of Stock"
        })

    # Attributes handling
    attrs = record.get("attributes")
    if isinstance(attrs, dict):
        attrs_json = json.dumps(attrs)
    elif isinstance(attrs, str) and attrs.strip().startswith("{"):
        attrs_json = attrs.strip()
    else:
        attrs_json = json.dumps({
            "color": record.get("color", "Standard"),
            "material": record.get("material", "Premium"),
            "origin": "India",
            "package_contents": f"1 x {name}"
        })

    prod_id = None
    if "id" in record and record["id"] is not None and str(record["id"]).strip().isdigit():
        prod_id = int(record["id"])

    sanitized = {
        "id": prod_id,
        "name": name,
        "category": category,
        "subcategory": subcategory,
        "brand": brand,
        "price": price,
        "discount_percentage": discount,
        "specifications": specs_json,
        "description": description,
        "image_url": image_url,
        "source_type": source_type,
        "source_id": source_id,
        "rating": rating,
        "stock": stock,
        "review_count_demo": reviews,
        "featured": featured,
        "attributes": attrs_json
    }

    return True, "", sanitized

def import_products_from_file(
    file_path: str,
    db_path: str = DEFAULT_DB,
    dry_run: bool = False,
    file_format: str = None
) -> Dict[str, Any]:
    """
    Imports products from JSON or CSV into pretwinshop.db.
    Preserves existing product IDs and foreign key integrity.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Input file not found: {file_path}")

    # Determine format
    if not file_format:
        ext = os.path.splitext(file_path)[1].lower()
        file_format = "json" if ext == ".json" else "csv"

    records = []
    if file_format == "json":
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                records = data
            elif isinstance(data, dict) and "products" in data:
                records = data["products"]
            else:
                raise ValueError("JSON file must be a list of products or contain a 'products' key")
    elif file_format == "csv":
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            records = list(reader)
    else:
        raise ValueError(f"Unsupported format: {file_format}")

    total_records = len(records)
    print(f"[{'DRY RUN' if dry_run else 'IMPORT'}] Ingesting {total_records} products from '{file_path}' (format: {file_format})...")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Pre-load existing products map: id -> id, source_id -> id
    cursor.execute("SELECT id, source_id FROM products")
    existing_ids = set()
    source_id_to_id = {}
    for r in cursor.fetchall():
        pid = r["id"]
        sid = r["source_id"]
        existing_ids.add(pid)
        if sid:
            source_id_to_id[str(sid).strip()] = pid

    added_count = 0
    updated_count = 0
    skipped_count = 0
    rejected_count = 0
    rejection_reasons = []

    for idx, rec in enumerate(records, 1):
        is_valid, err_msg, p = validate_product(rec, idx)
        if not is_valid:
            rejected_count += 1
            rejection_reasons.append(err_msg)
            continue

        target_id = None
        # Check matching by explicit id
        if p["id"] and p["id"] in existing_ids:
            target_id = p["id"]
        # Check matching by source_id
        elif p["source_id"] and p["source_id"] in source_id_to_id:
            target_id = source_id_to_id[p["source_id"]]

        if target_id is not None:
            # UPDATE existing product (preserves foreign keys!)
            if not dry_run:
                cursor.execute("""
                    UPDATE products SET
                        name = ?,
                        category = ?,
                        subcategory = ?,
                        brand = ?,
                        price = ?,
                        discount_percentage = ?,
                        specifications = ?,
                        description = ?,
                        image_url = ?,
                        source_type = ?,
                        source_id = ?,
                        rating = ?,
                        stock = ?,
                        review_count_demo = ?,
                        featured = ?,
                        attributes = ?
                    WHERE id = ?
                """, (
                    p["name"], p["category"], p["subcategory"], p["brand"],
                    p["price"], p["discount_percentage"], p["specifications"],
                    p["description"], p["image_url"], p["source_type"],
                    p["source_id"], p["rating"], p["stock"],
                    p["review_count_demo"], p["featured"], p["attributes"],
                    target_id
                ))
            updated_count += 1
        else:
            # INSERT new product
            if not dry_run:
                if p["id"]:
                    cursor.execute("""
                        INSERT INTO products (
                            id, name, category, subcategory, brand, price,
                            discount_percentage, specifications, description,
                            image_url, source_type, source_id, rating, stock,
                            review_count_demo, featured, attributes
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        p["id"], p["name"], p["category"], p["subcategory"], p["brand"],
                        p["price"], p["discount_percentage"], p["specifications"],
                        p["description"], p["image_url"], p["source_type"],
                        p["source_id"], p["rating"], p["stock"],
                        p["review_count_demo"], p["featured"], p["attributes"]
                    ))
                    existing_ids.add(p["id"])
                    if p["source_id"]: source_id_to_id[p["source_id"]] = p["id"]
                else:
                    cursor.execute("""
                        INSERT INTO products (
                            name, category, subcategory, brand, price,
                            discount_percentage, specifications, description,
                            image_url, source_type, source_id, rating, stock,
                            review_count_demo, featured, attributes
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        p["name"], p["category"], p["subcategory"], p["brand"],
                        p["price"], p["discount_percentage"], p["specifications"],
                        p["description"], p["image_url"], p["source_type"],
                        p["source_id"], p["rating"], p["stock"],
                        p["review_count_demo"], p["featured"], p["attributes"]
                    ))
                    new_id = cursor.lastrowid
                    existing_ids.add(new_id)
                    if p["source_id"]: source_id_to_id[p["source_id"]] = new_id
            added_count += 1

    if not dry_run:
        conn.commit()

    conn.close()

    summary = {
        "total_processed": total_records,
        "added": added_count,
        "updated": updated_count,
        "skipped": skipped_count,
        "rejected": rejected_count,
        "rejection_reasons": rejection_reasons[:10],
        "dry_run": dry_run
    }

    print("\n" + "=" * 50)
    print("      PRETWIN INGESTION SUMMARY REPORT")
    print("=" * 50)
    print(f"Total Products Ingested : {total_records}")
    print(f"Products Added (New)    : {added_count}")
    print(f"Products Updated        : {updated_count}")
    print(f"Products Skipped        : {skipped_count}")
    print(f"Products Rejected       : {rejected_count}")
    if dry_run:
        print("[!] DRY RUN ONLY: Database was not modified.")
    if rejection_reasons:
        print("\nTop Rejection Reasons:")
        for r in rejection_reasons[:5]:
            print(f"  - {r}")
    print("=" * 50 + "\n")

    return summary

def main():
    parser = argparse.ArgumentParser(description="PreTwin Product Ingestion & Synchronization Pipeline")
    parser.add_argument("--file", "-f", required=True, help="Path to JSON or CSV product feed file")
    parser.add_argument("--format", choices=["json", "csv"], default=None, help="Explicit file format")
    parser.add_argument("--db-path", default=DEFAULT_DB, help="Target SQLite database path")
    parser.add_argument("--dry-run", action="store_true", help="Validate feed without writing to database")

    args = parser.parse_args()
    try:
        import_products_from_file(
            file_path=args.file,
            db_path=args.db_path,
            dry_run=args.dry_run,
            file_format=args.format
        )
    except Exception as e:
        print(f"[ERROR] Import failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
