# -*- coding: utf-8 -*-
"""
scripts/seed_database_1040.py
Seeds 52 distinct products for each of the 20 categories (1,040 total).
"""

import sys
import os
import json
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db, init_db

# The 20 categories:
# 1. Fashion
# 2. Mobiles
# 3. Electronics
# 4. Beauty, Toys & More
# 5. Home & Kitchen
# 6. Appliances
# 7. Toys & Baby Products
# 8. Food & Grocery
# 9. Sports & Fitness
# 10. Books & Stationery
# 11. Furniture
# 12. Footwear
# 13. Watches & Accessories
# 14. Laptops & Computers
# 15. TVs & Home Entertainment
# 16. Personal Care
# 17. Automotive Accessories
# 18. Health & Wellness
# 19. Pet Supplies
# 20. Travel & Luggage

print("Compiling full dataset for 20 categories...")
