"""
data/seed_bulk_products.py
--------------------------
Populates exactly 1,040 demo products across all 20 main categories
(52 distinct products per category) for PreTwinShop AI.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.generate_all_20_categories import build_and_seed_catalogue
from scripts.assign_diverse_product_images import assign_diverse_images


def seed_bulk_products():
    count = build_and_seed_catalogue()
    assign_diverse_images()
    return count


if __name__ == "__main__":
    count = seed_bulk_products()
    print(f"[seed_bulk_products] Total seeded in DB: {count}")
