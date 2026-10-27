# -*- coding: utf-8 -*-
"""
scripts/generate_local_placeholders.py
Generates 20 high-quality local vector SVG product placeholder assets,
one for each canonical category, stored locally in static/images/placeholders/.
Ensures that if any remote image is ever slow or offline, a crisp, beautiful,
category-specific vector silhouette is displayed without broken image icons.
"""

import os

PLACEHOLDERS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "images", "placeholders")
os.makedirs(PLACEHOLDERS_DIR, exist_ok=True)

CATEGORIES = [
    ("Fashion", "#7c3aed", "M60 50 L80 30 L100 45 L120 30 L140 50 L125 150 L75 150 Z", "Apparel & Style"),
    ("Mobiles", "#2563eb", "M70 30 C70 24 75 20 81 20 L119 20 C125 20 130 24 130 30 L130 170 C130 176 125 180 119 180 L81 180 C75 180 70 176 70 170 Z", "Smartphones & 5G"),
    ("Electronics", "#0891b2", "M50 110 C50 70 70 50 100 50 C130 50 150 70 150 110 M40 110 L60 110 L60 145 L40 145 Z M140 110 L160 110 L160 145 L140 145 Z", "Audio & Devices"),
    ("Beauty, Toys & More", "#db2777", "M85 70 L115 70 L110 160 L90 160 Z M92 40 L108 40 L108 70 L92 70 Z", "Cosmetics & Care"),
    ("Home & Kitchen", "#ea580c", "M60 90 L140 90 L130 160 L70 160 Z M50 90 L150 90 L100 60 Z", "Kitchen & Dining"),
    ("Appliances", "#0284c7", "M65 30 L135 30 L135 170 L65 170 Z M65 90 L135 90 M95 130 C95 140 105 140 105 130", "Home Appliances"),
    ("Toys & Baby Products", "#eab308", "M80 80 C80 60 120 60 120 80 C120 100 80 100 80 120 L120 120", "Toys & Baby Care"),
    ("Food & Grocery", "#16a34a", "M60 70 L140 70 L130 160 L70 160 Z M85 45 C85 35 115 35 115 45 L115 70 L85 70 Z", "Daily Staples"),
    ("Sports & Fitness", "#dc2626", "M60 100 L80 100 L80 120 L60 120 Z M120 100 L140 100 L140 120 L120 120 Z M80 107 L120 107 L120 113 L80 113 Z", "Fitness & Gym"),
    ("Books & Stationery", "#4f46e5", "M60 50 L100 65 L140 50 L140 150 L100 165 L60 150 Z M100 65 L100 165", "Novels & Study"),
    ("Furniture", "#92400e", "M50 110 L150 110 L150 140 L50 140 Z M60 70 L140 70 L140 110 L60 110 Z M60 140 L60 170 M140 140 L140 170", "Living & Decor"),
    ("Footwear", "#b91c1c", "M50 130 C60 100 100 105 120 120 L160 125 C160 140 150 150 140 150 L50 150 Z", "Shoes & Sneakers"),
    ("Watches & Accessories", "#475569", "M100 70 C80 70 70 85 70 100 C70 115 80 130 100 130 C120 130 130 115 130 100 C130 85 120 70 100 70 Z M85 40 L115 40 L115 70 L85 70 Z M85 130 L115 130 L115 160 L85 160 Z", "Smart & Analog"),
    ("Laptops & Computers", "#0f766e", "M60 60 L140 60 L140 125 L60 125 Z M45 125 L155 125 L150 140 L50 140 Z", "Ultrabooks & PCs"),
    ("TVs & Home Entertainment", "#1e3a8a", "M45 50 L155 50 L155 135 L45 135 Z M90 135 L80 160 L120 160 L110 135 Z", "4K OLED & Smart"),
    ("Personal Care", "#9333ea", "M85 50 L115 50 L110 160 L90 160 Z M95 30 L105 30 L105 50 L95 50 Z", "Grooming & Hygiene"),
    ("Automotive Accessories", "#334155", "M60 120 C70 90 130 90 140 120 L155 125 C155 140 145 150 135 150 L65 150 C55 150 45 140 45 125 Z", "Car & Bike Care"),
    ("Health & Wellness", "#059669", "M90 60 L110 60 L110 90 L140 90 L140 110 L110 110 L110 140 L90 140 L90 110 L60 110 L60 90 L90 90 Z", "Vitamins & Care"),
    ("Pet Supplies", "#d97706", "M85 90 C75 80 75 65 85 65 C95 65 95 80 85 90 Z M115 90 C105 80 105 65 115 65 C125 65 125 80 115 90 Z M100 135 C85 135 75 120 85 105 C95 90 105 90 115 105 C125 120 115 135 100 135 Z", "Pet Food & Toys"),
    ("Travel & Luggage", "#4338ca", "M70 60 L130 60 L130 160 L70 160 Z M88 40 L112 40 L112 60 L88 60 Z M75 160 L75 170 M125 160 L125 170", "Bags & Trolleys")
]

def generate_svgs():
    created = 0
    for cat, color, path_d, sub in CATEGORIES:
        safe_name = cat.lower().replace(" ", "_").replace("&", "and").replace(",", "")
        filename = f"{safe_name}.svg"
        filepath = os.path.join(PLACEHOLDERS_DIR, filename)

        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#f8fafc" />
      <stop offset="100%" stop-color="#eef2f6" />
    </linearGradient>
    <linearGradient id="accentGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{color}" />
      <stop offset="100%" stop-color="{color}cc" />
    </linearGradient>
  </defs>
  <rect width="200" height="200" fill="url(#bgGrad)" rx="8" />
  <circle cx="100" cy="95" r="54" fill="{color}14" />
  <path d="{path_d}" fill="url(#accentGrad)" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
  <text x="100" y="172" font-family="'Inter', -apple-system, sans-serif" font-size="11" font-weight="700" fill="#334155" text-anchor="middle">{cat}</text>
  <text x="100" y="186" font-family="'Inter', -apple-system, sans-serif" font-size="9" font-weight="500" fill="#64748b" text-anchor="middle">PreTwin Verified • {sub}</text>
</svg>"""

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(svg)
        created += 1

    print(f"[generate_local_placeholders] Successfully generated {created} local vector placeholder assets in {PLACEHOLDERS_DIR}")

if __name__ == "__main__":
    generate_svgs()
