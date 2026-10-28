# -*- coding: utf-8 -*-
"""
scripts/generate_all_20_categories.py
Generates 52+ distinct realistic products for EACH of the 20 categories (1,040+ products total)
and directly seeds them into pretwinshop.db.
"""

import sys
import os
import json
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db, init_db

# 20 Categories Master Specification
CATEGORY_METADATA = [
    {
        "category": "Fashion",
        "brands": ["Levi's", "Allen Solly", "FabIndia", "Biba", "W for Woman", "Peter England", "Van Heusen", "Zara", "Raymond", "Manyavar", "U.S. Polo Assn.", "Wrangler"],
        "subcats": ["T-Shirts", "Shirts", "Jeans", "Trousers", "Dresses", "Sarees", "Kurtas", "Ethnic Wear", "Western Wear", "Innerwear", "Handbags", "Wallets", "Belts", "Sunglasses"],
        "img": "https://images.unsplash.com/photo-1489987707025-afc232f7ea0f?w=400&q=80",
        "prefixes": [
            "Slim Fit Casual", "Classic Straight Fit", "Pure Cotton Printed", "Traditional Embroidered", "Formal Pleated",
            "Stretchable Denim", "Vintage Washed", "Festive Designer", "Breathable Linen", "Comfort Fit",
            "Tailored Fit", "Woven Jacquard", "Graphic Printed", "Solid Polo Neck", "Double Pocket",
            "Relaxed Streetwear", "Premium Rayon", "Mandarin Collar", "Anarkali Flared", "Silk Blend"
        ],
        "nouns": [
            ("Shirt", 1299, "Shirts", "Premium breathable combed cotton fabric with curved hem and spread collar"),
            ("Denim Jeans", 1999, "Jeans", "Heavy duty stretch denim with 5-pocket styling and antique brass rivets"),
            ("Chino Trousers", 1499, "Trousers", "Wrinkle-resistant twill cotton casual trousers with coin pocket"),
            ("Cotton T-Shirt", 699, "T-Shirts", "Bio-washed 100% cotton with anti-pilling and fade-resistant dye"),
            ("Silk Saree with Blouse Piece", 2999, "Sarees", "Authentic rich zari woven borders with traditional Indian motifs"),
            ("Long Kurta Set", 1799, "Kurtas", "Calf-length ethnic kurta with matching trousers and dupatta"),
            ("A-Line Midi Dress", 1399, "Dresses", "Flowy georgette fabric with waist tie-up belt and elegant flare"),
            ("Nehru Jacket", 1999, "Ethnic Wear", "Structured woven textured ethnic jacket with pocket square"),
            ("Leather Formal Belt", 899, "Belts", "Reversible dual-tone genuine grain leather with metal swivel buckle"),
            ("Bifold Leather Wallet", 799, "Wallets", "RFID blocking technology with 8 credit card slots and currency divider"),
            ("Structured Handbag", 1899, "Handbags", "Triple zip compartments with gold hardware and detachable shoulder strap"),
            ("UV Polarized Sunglasses", 1199, "Sunglasses", "Anti-glare scratch-resistant lenses with lightweight stainless steel frame"),
            ("Cotton Boxer Shorts Pack of 3", 699, "Innerwear", "100% woven cotton poplin with elasticated waistband and button fly"),
            ("Winter Fleece Hoodie", 1499, "Western Wear", "Warm brushed fleece interior with front kangaroo pocket and drawstring hood")
        ]
    },
    {
        "category": "Mobiles",
        "brands": ["Samsung", "Apple", "OnePlus", "Xiaomi", "Realme", "Motorola", "Google", "Vivo", "iQOO", "Nothing", "Boat", "Anker"],
        "subcats": ["Smartphones", "5G Android Phones", "iOS Phones", "Feature Phones", "Mobile Covers & Cases", "Screen Guards", "Chargers & Cables", "Power Banks", "Wireless Earbuds", "Mobile Stands"],
        "img": "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=400&q=80",
        "prefixes": [
            "Pro 5G Flagship", "Ultra Slim 5G", "Neo Gaming Edition", "Plus SuperAMOLED", "Prime Edition",
            "Max Pro 5G", "Lite Compact", "Turbo Speed 5G", "Explorer Edition", "Master Edition",
            "Speed Fast", "Military Grade Shockproof", "Edge-to-Edge 9H", "Braided Heavy Duty", "GaN Super Fast"
        ],
        "nouns": [
            ("Smartphone (8GB RAM, 128GB)", 21999, "Smartphones", "High refresh rate AMOLED display, 5000mAh battery, 64MP OIS camera"),
            ("5G Smartphone (12GB RAM, 256GB)", 34999, "5G Android Phones", "Flagship processor, 120W super-fast charge, Quad camera system"),
            ("Demo iPhone Flagship (128GB)", 69900, "iOS Phones", "Super Retina XDR display, A-series bionic neural engine, Cinematic mode"),
            ("Dual SIM 4G Feature Phone", 1799, "Feature Phones", "Long lasting 7-day battery standby, UPI payment support, wireless FM radio"),
            ("Shockproof Magnetic Ring Case", 449, "Mobile Covers & Cases", "Drop test certified with 360 rotating kickstand and air cushions"),
            ("9H Tempered Glass Screen Guard", 299, "Screen Guards", "High transparency oleophobic coating, smudge-proof bubble free install"),
            ("65W GaN Dual Port Fast Wall Charger", 1699, "Chargers & Cables", "Gallium Nitride tech, Type-C PD 3.0 & USB-A fast charging"),
            ("Braided Fast Charging Cable (1.5m)", 349, "Chargers & Cables", "Nylon braided cable tested for 20,000 bends, supports 65W fast charge"),
            ("20000mAh 22.5W Fast Power Bank", 1599, "Power Banks", "Triple output ports, two-way fast charging, LED battery level indicator"),
            ("True Wireless ANC Earbuds", 2499, "Wireless Earbuds", "Active noise cancellation with 40h playtime and low latency gaming mode"),
            ("Aluminium Desktop Mobile Stand", 349, "Mobile Stands", "Multi-angle adjustable viewing angles with non-slip silicone pads"),
            ("Wireless Magnetic Car Charger Mount", 1299, "Mobile Stands", "15W fast inductive charging with automatic air vent lock grip"),
            ("Liquid Silicone Soft Touch Cover", 399, "Mobile Covers & Cases", "Microfiber interior lining, camera lens raised lip protection"),
            ("Privacy Anti-Spy Tempered Glass", 399, "Screen Guards", "28 degree side privacy angle keeps screen private in public")
        ]
    },
    {
        "category": "Electronics",
        "brands": ["Sony", "JBL", "Bose", "Canon", "Nikon", "Logitech", "SanDisk", "Seagate", "TP-Link", "Marshall", "Sennheiser", "GoPro"],
        "subcats": ["Headphones", "Bluetooth Speakers", "Soundbars", "Cameras", "Webcams", "Microphones", "Smartwatches", "Storage Devices", "Computer Accessories"],
        "img": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&q=80",
        "prefixes": [
            "Wireless Active Noise Cancelling", "Hi-Res Audio Studio", "Portable Waterproof Rugged", "Dual-Band Gigabit", "Extreme Speed NVMe",
            "Precision Optical", "Mechanical RGB Backlit", "Full HD 1080p Ultra", "Compact Mirrorless 4K", "Cardioid Condenser",
            "Professional Studio Monitor", "Multi-Port Aluminum", "Smart Health & Fitness", "Heavy Duty Anti-Surge", "Long Range Bluetooth"
        ],
        "nouns": [
            ("Over-Ear Wireless Headphones", 7999, "Headphones", "40mm dynamic drivers, active noise cancelling, 35 hours battery life"),
            ("Portable Waterproof Bluetooth Speaker", 4499, "Bluetooth Speakers", "IPX7 waterproof, deep punchy bass, dual passive radiators, 12h playtime"),
            ("2.1 Channel Dolby Soundbar with Subwoofer", 9999, "Soundbars", "200W peak power, wireless subwoofer, optical and HDMI ARC connectivity"),
            ("4K Mirrorless Digital Camera Kit", 49999, "Cameras", "24.2 MP APS-C CMOS sensor, 4K video recording, fast hybrid autofocus"),
            ("Full HD 1080p Streaming Webcam", 3499, "Webcams", "Stereo dual noise cancelling microphones, auto light correction, privacy cover"),
            ("USB Condenser Microphone for Podcasting", 4999, "Microphones", "Zero latency headphone monitoring, gain control knob, built-in pop filter"),
            ("AMOLED Bluetooth Calling Smartwatch", 4299, "Smartwatches", "1.43 inch AMOLED display, heart rate, SpO2 sensor, 100+ sport modes"),
            ("1TB Extreme Portable SSD USB 3.2", 7999, "Storage Devices", "Up to 1050MB/s read speeds, shock resistant aluminum unibody, Type-C"),
            ("2TB External Backup Hard Drive", 5499, "Storage Devices", "USB 3.0 plug and play, automatic backup software, Windows and Mac"),
            ("Wireless Ergonomic Laser Mouse", 1999, "Computer Accessories", "Contoured shape with thumb rest, dual Bluetooth and 2.4GHz USB receiver"),
            ("RGB Mechanical Gaming Keyboard", 4299, "Computer Accessories", "Hot swappable mechanical switches, anti-ghosting keys, volume roller"),
            ("Wi-Fi 6 Dual Band Router 1800Mbps", 3299, "Storage Devices", "4 high gain external antennas, OFDMA technology, WPA3 security"),
            ("Active Stylus Pen for Touchscreens", 1499, "Computer Accessories", "Palm rejection technology, high precision 4096 pressure sensitivity"),
            ("USB-C 8-in-1 Multifunction Hub Adapter", 2199, "Computer Accessories", "4K HDMI output, 100W PD pass-through charging, SD/TF card reader")
        ]
    },
    {
        "category": "Beauty, Toys & More",
        "brands": ["L'Oreal Paris", "The Ordinary", "Mamaearth", "Maybelline", "LEGO", "Hot Wheels", "Barbie", "Nerf", "Hasbro", "Biotique", "Nivea", "Cetaphil"],
        "subcats": ["Skincare", "Face Wash", "Moisturizers", "Sunscreen", "Makeup & Lipstick", "Haircare", "Perfumes & Deodorants", "Educational Toys", "Board Games", "Action Figures"],
        "img": "https://images.unsplash.com/photo-1596462502278-27bfdc403348?w=400&q=80",
        "prefixes": [
            "Hydrating 24H", "Natural Herbal Organic", "Ultra Matte Long Stay", "Brightening Vitamin C", "Deep Cleansing Foaming",
            "Pure Cold-Pressed", "Restorative Damage Repair", "Broad Spectrum SPF 50", "Classic Interlocking", "Die-Cast Metal 1:64",
            "Strategy Deduction", "Sensory Developmental", "Botanical Enriched", "Anti-Aging Collagen", "Luxury Long-Lasting"
        ],
        "nouns": [
            ("Face Serum for Dark Spots & Blemishes (30ml)", 699, "Skincare", "10% Niacinamide + Zinc formula balances sebum and minimizes enlarged pores"),
            ("Gentle Hydrating Cleanser Face Wash (200ml)", 449, "Face Wash", "Soap-free, fragrance-free formula preserves skin barrier moisture"),
            ("Ultra Lightweight Gel Moisturizer (100g)", 549, "Moisturizers", "Oil-free gel enriched with hyaluronic acid for 72-hour deep hydration"),
            ("Matte Finish Sunscreen Gel SPF 50 PA+++ (50g)", 499, "Sunscreen", "Zero white cast, water resistant, broad spectrum UVA and UVB shielding"),
            ("Liquid Matte Transfer-Proof Lipstick (5ml)", 499, "Makeup & Lipstick", "Intense pigment payoff with weightless 16-hour smudge-proof formula"),
            ("Damage Repair Moroccan Argan Hair Mask (200g)", 649, "Haircare", "Deep conditioning treatment restores dry damaged split ends with shine"),
            ("Luxury Eau De Parfum for Men & Women (100ml)", 1499, "Perfumes & Deodorants", "Exquisite top notes of citrus bergamot with lingering cedarwood and amber"),
            ("Building Blocks Rescue Vehicle Toy Set", 1299, "Educational Toys", "Includes 240 interlocking plastic pieces with rotating crane and wheels"),
            ("Die-Cast Racing Cars Pack of 5", 899, "Action Figures", "Authentic 1:64 scale metal die-cast cars with custom aerodynamic decors"),
            ("Fashion Doll with Wardrobe Accessories", 1199, "Action Figures", "Posable articulated fashion doll with 3 dresses, handbag and vanity set"),
            ("Foam Dart Target Blaster Toy", 1299, "Action Figures", "Pump-action firing mechanism with 12 soft tip safe suction darts"),
            ("Classic Family Strategy Board Game", 799, "Board Games", "High-engagement property trading and decision-making board game for all ages"),
            ("1000-Piece Landscape Jigsaw Puzzle", 599, "Educational Toys", "Precision cut recycled cardboard with anti-glare finish and full poster"),
            ("Organic Under-Eye Depuffing Cream (20g)", 499, "Skincare", "Infused with caffeine and peptide complex to lighten dark circles")
        ]
    },
    {
        "category": "Home & Kitchen",
        "brands": ["Prestige", "Hawkins", "Milton", "Cello", "Wonderchef", "Bombay Dyeing", "Spaces", "Philips", "Solimo", "Borosil", "Tupperware", "Godrej"],
        "subcats": ["Cookware", "Kitchen Tools", "Storage Containers", "Bedsheets", "Bath Accessories", "Home Decor", "Cleaning Supplies", "Dinnerware"],
        "img": "https://images.unsplash.com/photo-1583847268964-b28dc8f51f92?w=400&q=80",
        "prefixes": [
            "Hard Anodised Heavy", "Induction Base Non-Stick", "Airtight Leak-Proof", "100% Pure Combed Cotton", "Double Wall Vacuum Insulated",
            "Stainless Steel Mirror Finish", "Ergonomic Chef Grade", "High Absorption 500 GSM", "Thermal Insulated Blackout", "Modular Space-Saving",
            "Chip Resistant Opalware", "Microfiber Spin & Clean", "Borosilicate Thermal Glass", "Distressed Antique Wooden", "Handcrafted Bohemian"
        ],
        "nouns": [
            ("Pressure Cooker with Induction Base 3L", 1899, "Cookware", "Hard anodized corrosion-resistant body with pressure safety indicator valve"),
            ("Non-Stick Dosa Tawa & Frying Pan Combo", 1699, "Cookware", "5-layer scratch resistant granite coating with cool-touch bakelite handles"),
            ("Kitchen Chef Knife Set with Block (6 Pcs)", 1299, "Kitchen Tools", "Razor sharp German high-carbon stainless steel with solid pine wooden block"),
            ("Airtight Glass Food Storage Containers (Set of 4)", 1199, "Storage Containers", "Thermal shock resistant borosilicate glass with airtight silicone snap lids"),
            ("Insulated Thermosteel Water Bottle 1000ml", 799, "Kitchen Tools", "Double wall vacuum insulation keeps beverages hot or cold for 24 hours"),
            ("Cotton King Size Bedsheet with 2 Pillow Covers", 1199, "Bedsheets", "250 thread count combed pure cotton with color-lock fade resistant dye"),
            ("Microfiber Reversible AC Comforter Blanket", 1799, "Bedsheets", "Hypoallergenic hollow siliconized fiber filling for all-season lightweight warmth"),
            ("Room Darkening Window Curtains Set of 2 (7 Ft)", 999, "Bedsheets", "Triple weave heavy polyester fabric blocks 90% sunlight and outdoor noise"),
            ("Plush Cotton Bath Towels Set of 4", 1299, "Bath Accessories", "550 GSM ultra-soft ring-spun cotton towels with high water absorption"),
            ("Floating Wall Mount Display Shelves Set of 3", 899, "Home Decor", "Sturdy engineered wood with concealed metal brackets for modern living rooms"),
            ("Floor Cleaning Microfiber Spin Mop System", 1399, "Cleaning Supplies", "Stainless steel fast wringer basket with 360 rotating mop head and 2 refills"),
            ("Chip-Resistant Dinner Set 32-Pieces", 2999, "Dinnerware", "Lightweight bone ash-free opalware dinner set, microwave and dishwasher safe"),
            ("Revolving Spice Rack with 16 Glass Jars", 999, "Storage Containers", "360 degree rotating tower carousel with dual-opening flip shaker lids"),
            ("Memory Foam Ergonomic Cervical Sleeping Pillow", 1299, "Bedsheets", "Therapeutic contour butterfly shape promotes spinal alignment and relieves pain")
        ]
    },
    {
        "category": "Appliances",
        "brands": ["LG", "Samsung", "Whirlpool", "Haier", "Bosch", "IFB", "Voltas", "Daikin", "Havells", "Bajaj", "Philips", "Eureka Forbes"],
        "subcats": ["Refrigerators", "Washing Machines", "Air Conditioners", "Fans & Coolers", "Microwave Ovens", "Mixers & Grinders", "Induction Cooktops", "Vacuum Cleaners", "Water Purifiers", "Electric Irons"],
        "img": "https://images.unsplash.com/photo-1585338107529-13afc5f02586?w=400&q=80",
        "prefixes": [
            "Frost Free Double Door", "Fully Automatic Front Load", "Inverter Split 5-Star", "BLDC Energy Saver", "Convection Digital Touch",
            "Heavy Duty 750W", "Crystal Glass Touch Panel", "Robotic Lidar Laser", "RO + UV + Mineralizer", "Non-Stick Ceramic Soleplate",
            "Direct Cool 4-Star", "Smart Inverter Top Load", "Convertible 4-in-1", "Silent Aerodynamic", "Rapid Air Circulation"
        ],
        "nouns": [
            ("Double Door Frost Free Refrigerator 260L", 24990, "Refrigerators", "Smart Inverter compressor, multi-air flow cooling, toughened glass shelves"),
            ("Fully Automatic Front Load Washing Machine 7kg", 28990, "Washing Machines", "Steam allergen removal wash, 1200 RPM high spin speed, stainless steel drum"),
            ("1.5 Ton 5-Star Inverter Split Air Conditioner", 36990, "Air Conditioners", "100% copper condenser, PM 2.5 air filtration, 4-in-1 convertible cooling modes"),
            ("High Speed Silent BLDC Ceiling Fan 1200mm", 3190, "Fans & Coolers", "Consumes only 28W electricity, saves up to 65% power, comes with RF remote"),
            ("Convection Microwave Oven 28L with Tandoor Mode", 11990, "Microwave Ovens", "Auto-cook Indian menu recipes, motorized rotisserie for barbecue roasting"),
            ("Mixer Grinder 750W with 4 Stainless Steel Jars", 3290, "Mixers & Grinders", "Heavy duty copper wound motor, overload safety protection, flow breaker jars"),
            ("Push Button Induction Cooktop 2100W", 2490, "Induction Cooktops", "Pre-programmed Indian cooking presets, digital display, auto shut-off safety"),
            ("Robotic Wet and Dry Vacuum Cleaner with Mopping", 21990, "Vacuum Cleaners", "Lidar room navigation mapping, 3000Pa strong suction, auto dock recharge"),
            ("RO + UV + Copper Mineral Water Purifier 8L", 12990, "Water Purifiers", "Multi-stage filtration adds essential copper and mineral ions to drinking water"),
            ("Heavyweight Dry Iron with Non-Stick Soleplate 1000W", 799, "Electric Irons", "Traditional heavy pressing weight for crisp cotton shirt creases, thermal fuse"),
            ("Air Fryer 4.5L with Rapid 360 Heat Circulation", 3990, "Microwave Ovens", "Fries with up to 90% less oil, non-stick dishwasher-safe basket, timer dial"),
            ("Personal Desert Air Cooler 45L with Honeycomb Pads", 6490, "Fans & Coolers", "30-feet powerful air throw, ice chamber for rapid cooling, motorized louvers"),
            ("Handheld Cordless Stick Vacuum Cleaner 150W", 7490, "Vacuum Cleaners", "Bagless cyclonic filtration, 40-minute battery runtime, LED motorized floor brush"),
            ("Instant Water Geyser 3L 3000W Fast Heating", 2890, "Water Purifiers", "Rust-proof thermoplastic outer casing with high pressure safety valve")
        ]
    },
    {
        "category": "Toys & Baby Products",
        "brands": ["LEGO", "Fisher-Price", "Hot Wheels", "Barbie", "Chicco", "Pampers", "Huggies", "MamyPoko", "Funskool", "Mee Mee", "LuvLap", "BeyBlade"],
        "subcats": ["Educational Toys", "Building Blocks", "Puzzles", "Dolls & Action Figures", "Board Games", "Baby Clothing", "Diapers & Baby Care", "Strollers & Feeding"],
        "img": "https://images.unsplash.com/photo-1515488042361-ee00e0ddd4e4?w=400&q=80",
        "prefixes": [
            "Montessori Educational", "Interlocking Creative", "Die-Cast Licensed 1:64", "Posable Articulated", "Ergonomic Multi-Position",
            "12-Hour Dry Absorption", "99% Pure Water Soft", "Organic Combed Cotton", "Steam Sterilization", "Anti-Colic Venting",
            "STEM accredited Science", "Tactile Sensory", "Hypoallergenic Velvet", "Rechargeable Electric", "Washable Reusable Eco"
        ],
        "nouns": [
            ("Rescue Vehicles Building Blocks Construction Set", 1999, "Building Blocks", "Includes 350+ pieces with moving ladder, siren and mini construction worker figures"),
            ("Wooden Alphabet & Numbers Peg Puzzle Board", 499, "Puzzles", "Non-toxic eco water-based paints, smooth chunky wooden pieces easy for toddler grip"),
            ("Die-Cast Supercar Track Set with Double Loop", 1799, "Dolls & Action Figures", "Includes 2 high-speed launcher cars with motorized double loop jump ramp"),
            ("Fashion Doll with Glamour Wardrobe & Accessories", 1499, "Dolls & Action Figures", "Posable doll with interchangeable dresses, high heels, jewelry and vanity mirror"),
            ("Lightweight Foldable Baby Stroller Pram", 4799, "Strollers & Feeding", "5-point safety harness, sun canopy with peekaboo window, multi-recline backrest"),
            ("Baby Diaper Pants Ultra Soft (Pack of 64)", 999, "Diapers & Baby Care", "12-hour leak lock gel core with wetness indicator line and breathable waistband"),
            ("Sensitive Baby Water Wipes (Pack of 3 x 72 wipes)", 349, "Diapers & Baby Care", "Enriched with aloe vera and vitamin E, 0% alcohol, paraben-free and hypoallergenic"),
            ("Pure Cotton Baby Romper Sleepsuits (Pack of 3)", 799, "Baby Clothing", "Nickel-free snap buttons for easy diaper changing, soft breathable rib knit cotton"),
            ("Electric Steam Baby Bottle Sterilizer & Dryer", 2499, "Strollers & Feeding", "Sterilizes and dries up to 6 feeding bottles and pacifiers in 30 minutes"),
            ("Anti-Colic Feeding Bottle 250ml (Pack of 2)", 649, "Strollers & Feeding", "BPA-free polypropylene bottle with soft natural silicone nipple and air vent"),
            ("Interactive Musical Baby Walker with Activity Center", 1899, "Educational Toys", "Includes detachable piano, telephone handset, spinning gears and shape sorter"),
            ("Magnetic 3D Geometry Building Tiles Set (64 Pcs)", 1699, "Building Blocks", "Translucent rainbow geometric shapes foster 3D architectural thinking and STEM logic"),
            ("100-Piece Illustrated World Map Floor Puzzle", 599, "Puzzles", "Large sturdy pieces featuring famous landmarks, native animals and country flags"),
            ("Ergonomic 4-in-1 Baby Kangaroo Carrier", 1699, "Strollers & Feeding", "Padded shoulder straps with lumbar waist belt support, forward and rear facing modes")
        ]
    },
    {
        "category": "Food & Grocery",
        "brands": ["Tata", "Aashirvaad", "Fortune", "India Gate", "Saffola", "Dabur", "Nestle", "Cadbury", "Britannia", "Parle", "Maggi", "Catch"],
        "subcats": ["Rice & Atta", "Dals & Pulses", "Cooking Oils & Ghee", "Spices & Masalas", "Dry Fruits & Nuts", "Biscuits & Snacks", "Chocolates & Sweets", "Tea & Coffee", "Breakfast Cereals", "Noodles & Pasta"],
        "img": "https://images.unsplash.com/photo-1542838132-92c53300491e?w=400&q=80",
        "prefixes": [
            "Whole Wheat Chakki", "Traditional Aged Basmati", "Refined Heart-Friendly", "Pure Desi Danedar", "Unpolished Organic High-Protein",
            "Raw Crunchy Jumbo", "Antioxidant Rich Green", "Aromatic Roasted Arabica", "Instant 2-Minute Masala", "100% Durum Wheat Semolina",
            "Artisan Dark Cocoa", "Crunchy Butter Baked", "Roasted Multigrain Healthy", "100% Rolled Wholegrain", "Pure NMR-Tested Wild"
        ],
        "nouns": [
            ("Whole Wheat Atta (10kg Bag)", 449, "Rice & Atta", "100% MP Sharbati wheat stone ground chakki atta with natural bran and fiber"),
            ("Aged Basmati Rice 5kg Pack", 699, "Rice & Atta", "Extra-long slender pearl white grains with authentic aroma, aged for 2 years"),
            ("Refined Sunflower Cooking Oil 5L Can", 699, "Cooking Oils & Ghee", "Light and easy to digest, fortified with vitamins A and D, high smoking point"),
            ("Pure Cow Ghee 1L Tin", 649, "Cooking Oils & Ghee", "Traditional bilona curd churning method, golden granule texture with divine aroma"),
            ("Unpolished Toor Dal Arhar 1kg", 189, "Dals & Pulses", "Naturally rich in plant protein, dietary fiber and iron with zero artificial polish"),
            ("California Raw Almonds Badam 500g", 499, "Dry Fruits & Nuts", "Jumbo crispy whole almonds packed with natural vitamin E and healthy fats"),
            ("Premium Green Tea Bags (Pack of 100)", 399, "Tea & Coffee", "Rich in natural catechins and antioxidants, helps detox and boosts metabolism"),
            ("Roasted Instant Coffee 200g Jar", 449, "Tea & Coffee", "Master blend of select Arabica and Robusta beans delivering rich dark crema"),
            ("Instant Masala Noodles (Pack of 12)", 168, "Noodles & Pasta", "Classic signature 20-spice mix, quick and comforting evening family snack"),
            ("Durum Wheat Penne Pasta 500g", 129, "Noodles & Pasta", "High protein Italian durum semolina pasta, holds thick creamy sauces al dente"),
            ("Rich Dark Chocolate Gift Box 250g", 349, "Chocolates & Sweets", "70% cocoa with roasted almonds and sea salt caramel filling"),
            ("Oatmeal Chocolate Chip Cookies (400g)", 199, "Biscuits & Snacks", "Baked with wholegrain oats, real dark chocolate chips and creamy farm butter"),
            ("Rolled Breakfast Oats 1kg Pouch", 199, "Breakfast Cereals", "Rich in soluble beta-glucan fiber, helps reduce cholesterol and manage weight"),
            ("Pure Natural Forest Honey 500g Squeeze Bottle", 229, "Chocolates & Sweets", "100% pure raw honey, zero added sugar, tested with advanced NMR analysis")
        ]
    },
    {
        "category": "Sports & Fitness",
        "brands": ["Cosco", "Nivia", "Yonex", "Decathlon", "Puma", "Boldfit", "Strauss", "Reebok", "Kobo", "Hero", "Cultsport", "Nike"],
        "subcats": ["Cricket", "Badminton", "Football & Basketball", "Yoga Mats", "Dumbbells & Weights", "Resistance Bands", "Gym Accessories", "Fitness Trackers", "Running Shoes & Sportswear", "Cycles & Gear"],
        "img": "https://images.unsplash.com/photo-1517838277536-f5f99be501cd?w=400&q=80",
        "prefixes": [
            "Professional Tournament", "High-Tension Graphite", "FIFA Approved Match", "Eco-Friendly TPE Anti-Tear", "Hexagonal Rubber Encased",
            "Multi-Resistance Latex Loop", "Dual-Layer Leakproof Shaker", "Smart Heart-Rate Fitness", "Lightweight Breathable Mesh", "Multi-Speed Geared City",
            "Reinforced Kashmir Willow", "Shock Absorption Cushioned", "Non-Slip Textured Grip", "Heavy Duty Cast Iron", "Adjustable Ergonomic"
        ],
        "nouns": [
            ("Kashmir Willow Cricket Bat (Short Handle)", 1899, "Cricket", "Handcrafted premium grade willow with thick power edges and rubber grip"),
            ("Graphite Badminton Racket with Full Cover", 1699, "Badminton", "Lightweight 82g isometric frame with 24-lbs factory stringing tension"),
            ("PU Hand Stitched Size 5 Football", 999, "Football & Basketball", "32-panel durable PU construction with high air retention butyl bladder"),
            ("TPE Eco-Friendly Yoga Mat 6mm Thick", 999, "Yoga Mats", "Dual-sided anti-slip texture with carrying strap, lightweight and odor-free"),
            ("Hexagonal Rubber Coated Dumbbells Pair (5kg x 2)", 1899, "Dumbbells & Weights", "Solid cast iron core with heavy rubber coating prevents rolling and floor dents"),
            ("Resistance Exercise Bands Set of 5 with Handles", 799, "Resistance Bands", "Natural latex tubes ranging from 10 lbs to 50 lbs with door anchor and ankle straps"),
            ("Gym Shaker Protein Bottle 700ml with Whisk Ball", 349, "Gym Accessories", "100% leakproof BPA-free bottle with stainless steel wire blending ball"),
            ("Smart Fitness Band with SpO2 and Heart Rate", 2199, "Fitness Trackers", "Vibrant AMOLED screen, 14-day battery life, 5ATM swim-proof water resistance"),
            ("Men Lightweight Cushion Running Shoes", 1999, "Running Shoes & Sportswear", "Breathable knit upper with high rebound EVA foam midsole shock absorption"),
            ("21-Speed Mountain Bicycle with Dual Disc Brakes", 8999, "Cycles & Gear", "Sturdy carbon steel frame, front suspension fork, Shimano shifting gears"),
            ("Feather Badminton Shuttlecocks (Pack of 10)", 799, "Badminton", "Goose feather shuttlecocks with natural cork base for steady parabolic flight"),
            ("Leather Cricket Leather Ball Pack of 2 (Alum Tanned)", 599, "Cricket", "Four-piece alum tanned leather ball with pronounced seam for swing"),
            ("Adjustable Heavy Hand Grip Strengthener (10-60kg)", 299, "Gym Accessories", "Stainless steel spring with non-slip rubberized handles and counter"),
            ("Thermal Compression Dry-Fit Gym Tights", 799, "Running Shoes & Sportswear", "4-way stretch moisture wicking fabric reduces muscle soreness and fatigue")
        ]
    },
    {
        "category": "Books & Stationery",
        "brands": ["Classmate", "Reynolds", "Parker", "Camlin", "Casio", "Doms", "Penguin", "HarperCollins", "Rupa", "Oxford", "Faber-Castell", "Kangaro"],
        "subcats": ["Fiction & Literature", "Non-Fiction & Biographies", "Self-Help", "Business & Finance", "Children's Books", "Academic & Exams", "Notebooks & Diaries", "Pens & Art Supplies", "Desk Organizers"],
        "img": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=400&q=80",
        "prefixes": [
            "Bestselling Motivational", "Hardcover Collector's", "Official Entrance Exam Guide", "Acid-Free Archival Paper", "Precision Tip Fluid",
            "Stainless Steel Nib Executive", "Scientific 417-Function", "Artist Quality Heavyweight", "Multipurpose Mesh Metal", "Comprehensive Illustrated",
            "Inspirational Biography", "Spiral Bound Perforated", "Vibrant Non-Toxic Gouache", "Ergonomic Retractable", "Soft Touch Premium Leather"
        ],
        "nouns": [
            ("International Bestselling Self-Help Book", 399, "Self-Help", "Transformative practical strategies for building positive habits and mental focus"),
            ("Compelling Mystery & Thriller Crime Novel", 349, "Fiction & Literature", "Gripping page-turning plot filled with suspense, twists and memorable characters"),
            ("Comprehensive General Knowledge & Current Affairs Guide", 499, "Academic & Exams", "Up to date yearbook coverage for civil services, banking and competitive tests"),
            ("Spiral Bound Ruled Long Notebooks (Pack of 6)", 360, "Notebooks & Diaries", "Smooth 70 GSM elemental chlorine-free paper with durable coated covers"),
            ("Executive Retractable Rollerball Pens (Pack of 5)", 249, "Pens & Art Supplies", "0.7mm tungsten carbide ball tip for ultra smooth fluid dark writing"),
            ("Luxury Stainless Steel Fountain Pen with Ink Converter", 899, "Pens & Art Supplies", "Handcrafted fine nib, brushed metal finish with engraved chrome accents"),
            ("Scientific Calculator with 417 Functions", 1299, "Desk Organizers", "Natural textbook display, dual solar and battery power, matrix and vector math"),
            ("Acrylic Artist Paint Colors 12-Tubes Set (20ml)", 399, "Pens & Art Supplies", "High pigment density, buttery smooth consistency, dries to a satin finish"),
            ("Metal Mesh 4-Tier Desktop Document Tray Organizer", 799, "Desk Organizers", "Pull-out sliding letter trays organize files, folders, stationery and magazines"),
            ("Undated Daily Productivity Planner Journal", 599, "Notebooks & Diaries", "Hardcover faux leather diary with habit trackers, monthly goals and ribbon marker"),
            ("Illustrated Children's Bedtime Fairytale Storybook", 299, "Children's Books", "Glossy colorful illustrations with moral life lessons for young readers"),
            ("Heavy Duty Desktop Paper Stapler with 1000 Pins", 249, "Desk Organizers", "Steel mechanism staples up to 30 sheets with built-in staple remover"),
            ("Fine Tip Fineliner Sketching Pens (Set of 10)", 349, "Pens & Art Supplies", "Waterproof archival pigment ink, zero bleeding on paper, 0.4mm needle tip"),
            ("Financial Independence & Wealth Mindset Book", 399, "Business & Finance", "Timeless lessons on money management, investing, risk and compound growth")
        ]
    },
    {
        "category": "Furniture",
        "brands": ["Wakefit", "Sleepwell", "Godrej Interio", "Nilkamal", "Urban Ladder", "Pepperfry", "Green Soul", "Kurlon", "Durian", "Spacewood", "Wipro", "IKEA"],
        "subcats": ["Beds & Mattresses", "Wardrobes", "Sofas & Sectionals", "Recliners", "Coffee Tables & TV Units", "Dining Tables & Chairs", "Office Chairs & Desks", "Bookshelves & Shoe Racks"],
        "img": "https://images.unsplash.com/photo-1555041469-a586c61ea9bc?w=400&q=80",
        "prefixes": [
            "Ergonomic High Back Mesh", "Sheesham Solid Wood", "High-Density Orthopedic Foam", "L-Shaped Sectional Fabric", "Single Motorized Power",
            "Engineered Wood Modern", "4-Seater Compact Dining", "Multipurpose 5-Tier", "Foldable Heavy-Duty Plastic", "Pocket Spring Orthopedic",
            "Queen Size Hydraulic Storage", "Minimalist Scandinavian", "Cushioned Padded Lounge", "Modular 3-Door Sliding", "Waterproof Rust-Proof"
        ],
        "nouns": [
            ("Ergonomic High Back Office Mesh Chair", 6499, "Office Chairs & Desks", "Adjustable lumbar support, 2D armrests, pneumatic height tilt recline lock"),
            ("Solid Sheesham Wood Queen Bed with Storage", 18999, "Beds & Mattresses", "Rich honey finish solid rosewood bed with spacious box storage compartments"),
            ("Orthopedic Memory Foam Mattress (Queen 78x60x6)", 9999, "Beds & Mattresses", "High resilience foam base with body conforming cooling memory foam layer"),
            ("L-Shaped 6-Seater Sectional Fabric Sofa", 24999, "Sofas & Sectionals", "High density foam cushioning, solid sal wood frame with stain-resistant fabric"),
            ("Manual Leatherette Recliner Chair with Cup Holder", 14999, "Recliners", "Multi-angle reclining backrest with extendable footrest and plush arm cushioning"),
            ("Modern Engineered Wood TV Unit Entertainment Console", 4499, "Coffee Tables & TV Units", "Accommodates up to 55-inch TVs with open storage shelves for set-top boxes"),
            ("4-Seater Dining Table Set with Cushioned Chairs", 13999, "Dining Tables & Chairs", "Solid wooden table top with 4 matching comfortable upholstered dining chairs"),
            ("Solid Wood Minimalist Coffee Center Table", 3499, "Coffee Tables & TV Units", "Clean Scandinavian lines with lower open shelf for books and remote controls"),
            ("3-Door Engineered Wood Wardrobe with Mirror", 12999, "Wardrobes", "Hanging rod with deep shelves and internal locking safety drawer"),
            ("5-Tier Wooden Ladder Bookshelf & Display Rack", 2999, "Bookshelves & Shoe Racks", "Open display shelves for books, indoor plants and decorative photo frames"),
            ("Closed 4-Door Shoe Rack with Seat Cushion", 3999, "Bookshelves & Shoe Racks", "Stores up to 16 pairs of footwear with comfortable top bench cushion for wearing shoes"),
            ("Ergonomic Height Adjustable Computer Study Desk", 5499, "Office Chairs & Desks", "Wide desktop with headphone hook, cable management tray and cup holder"),
            ("Plastic Armless Dining Chairs Set of 4", 2499, "Dining Tables & Chairs", "Heavy duty weather-resistant molded plastic, stackable space saving design"),
            ("Bean Bag Chair with Footstool (Pre-Filled XXL)", 2199, "Sofas & Sectionals", "Durable leatherette material with double stitching and child-safe zipper")
        ]
    },
    {
        "category": "Footwear",
        "brands": ["Nike", "Adidas", "Puma", "Bata", "Woodland", "Red Tape", "Sparx", "Skechers", "Metro", "Campus", "Crocs", "Asian"],
        "subcats": ["Men's Casual Shoes", "Men's Formal Shoes", "Sports & Running Shoes", "Sneakers", "Women's Flats", "Heels & Wedges", "Slippers & Flip Flops", "Kids' Footwear", "Shoe Care & Socks"],
        "img": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&q=80",
        "prefixes": [
            "Lightweight Air Mesh Running", "Classic Leather Oxford", "Streetwear Chunky Sole", "Memory Foam Slip-On", "Genuine Nubuck Leather Rugged",
            "Cushioned Waterproof Lightweight", "Orthopedic Arch Support Soft", "Pointed Toe Block Heel", "Braided Strap Ethnic Slip-On", "Breathable Knit Walking",
            "High Top Retro Basketball", "Flexible EVA Cushion", "Water-Resistant Outdoor Trail", "Non-Slip Anti-Skid Grip", "Handmade Italian Style"
        ],
        "nouns": [
            ("Men Running Sports Shoes with Air Cushion", 1999, "Sports & Running Shoes", "Breathable mesh upper, shock absorbing Phylon midsole, durable rubber outsole"),
            ("Classic Leather Formal Derby Shoes", 2199, "Men's Formal Shoes", "Genuine polished leather with cushioned insole and non-slip TPR sole"),
            ("Retro Chunky Casual Sneakers", 1799, "Sneakers", "Vintage two-tone street design with padded ankle collar and traction outsole"),
            ("Rugged Outdoor Leather Trekking Boots", 3499, "Men's Casual Shoes", "Durable nubuck leather with grooved rubber lug sole for tough rocky terrains"),
            ("Memory Foam Walk Comfort Shoes", 2499, "Sports & Running Shoes", "Ultra-cushioned memory foam insole relieves heel stress during long walks"),
            ("Women Pointed Toe Block Heel Pumps", 1599, "Heels & Wedges", "2.5 inch comfortable block heel with padded footbed for party and office wear"),
            ("Women Ethnic Embroidered Mojari Flats", 799, "Women's Flats", "Traditional handcrafted jutti with foam padded sole and zari embroidery"),
            ("Cushioned Waterproof Clogs with Heel Strap", 999, "Slippers & Flip Flops", "Lightweight Croslite foam material with ventilation ports and pivot heel strap"),
            ("Men Soft Cushion Flip Flop Slippers", 499, "Slippers & Flip Flops", "Soft textured footbed with durable synthetic leather straps and grooved sole"),
            ("Kids Light-Up LED Sports Sneakers", 899, "Kids' Footwear", "Flashing LED lights inside transparent sole, Velcro strap for easy wear"),
            ("Men Penny Loafers Slip-On Driving Shoes", 1699, "Men's Casual Shoes", "Moccasin toe stitch with flexible rubber pebble sole for driving comfort"),
            ("Women Wedge Heel Casual Sandals", 1299, "Heels & Wedges", "Ankle buckle strap with lightweight cork patterned wedge platform sole"),
            ("Bamboo Cotton Ankle Length Socks (Pack of 5)", 399, "Shoe Care & Socks", "Naturally anti-bacterial and odor-resistant with reinforced heel and toe"),
            ("Waterproof Instant Shoe Cleaning Foam Spray Kit", 349, "Shoe Care & Socks", "Cleans dirt, stains and grime from sneakers, canvas, suede and mesh without water")
        ]
    },
    {
        "category": "Watches & Accessories",
        "brands": ["Titan", "Fastrack", "Casio", "Fossil", "Timex", "Tommy Hilfiger", "Daniel Wellington", "Ray-Ban", "Police", "Hidesign", "Wildhorn", "Noise"],
        "subcats": ["Men's Analog Watches", "Chronograph Watches", "Women's Designer Watches", "Smartwatches & Bands", "Sunglasses", "Wallets & Belts", "Fashion Jewellery", "Ties & Cufflinks"],
        "img": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=400&q=80",
        "prefixes": [
            "Analog Quartz Classic", "Multi-Dial Chronograph", "Rose Gold Swarovski Studded", "Stainless Steel Mesh", "Polarized UV400 Aviator",
            "Genuine Full Grain Leather", "Tough Shock Resistant", "Automatic Mechanical Skeleton", "Minimalist Slim Line", "Zirconia Crystal Plated",
            "Matte Black Stealth", "Designer Silk Jacquard", "Ceramic Dial Hybrid", "Vintage Retro Digital", "Heavy Brass Rhodium Plated"
        ],
        "nouns": [
            ("Men Classic Quartz Analog Watch with Leather Strap", 2495, "Men's Analog Watches", "Clean sunray dial with date display, mineral glass and water resistant to 30m"),
            ("Men Multi-Function Chronograph Stainless Steel Watch", 4995, "Chronograph Watches", "Stopwatch sub-dials, tachymeter bezel, fold-over safety clasp with push buttons"),
            ("Women Rose Gold Watch with Mother of Pearl Dial", 3995, "Women's Designer Watches", "Jewelry clasp with embedded crystal hour markers and rose gold plating"),
            ("Tough Shock-Resistant Digital Sports Watch", 3495, "Smartwatches & Bands", "200m water resistance, countdown timer, auto LED backlight, world time 48 cities"),
            ("Automatic Skeleton Mechanical Movement Watch", 8995, "Men's Analog Watches", "Exhibition see-through dial shows oscillating balance wheel, no battery required"),
            ("Polarized UV400 Metal Aviator Sunglasses", 1799, "Sunglasses", "Glare reduction polarized lenses with spring hinges and silicon nose pads"),
            ("Wayfarer Matte Black Sunglasses with UV Protection", 1299, "Sunglasses", "Classic durable acetate frame with green tint scratch-resistant lenses"),
            ("Genuine Full Grain Leather Wallet & Keychain Combo", 1199, "Wallets & Belts", "Gift boxed handcrafted cowhide leather with 10 card slots and coin pocket"),
            ("Reversible Italian Formal Leather Belt", 999, "Wallets & Belts", "Dual-tone black and brown finish with automatic micro-adjust sliding ratchet buckle"),
            ("18K Gold Plated Austrian Crystal Pendant & Earrings Set", 1299, "Fashion Jewellery", "Skin friendly hypoallergenic rhodium coating with high-sparkle solitaire crystal"),
            ("Luxury Silk Necktie, Pocket Square & Cufflinks Box Set", 999, "Ties & Cufflinks", "Hand-stitched jacquard woven silk tie with matching floral brass cufflinks"),
            ("Men Stainless Steel Cuban Link Curb Chain Necklace", 699, "Fashion Jewellery", "Heavy 8mm diamond cut curb links with secure lobster claw clasp"),
            ("Retro Digital Gold Metallic Vintage Watch", 2295, "Men's Analog Watches", "Iconic 80s retro digital watch with alarm, hourly chime and 1/100s stopwatch"),
            ("Hard Travel Watch Storage Organizer Case for 3 Watches", 899, "Wallets & Belts", "Shockproof EVA hard shell with individual velvet cushions and divider walls")
        ]
    },
    {
        "category": "Laptops & Computers",
        "brands": ["HP", "Dell", "Lenovo", "Asus", "Acer", "Apple", "MSI", "Logitech", "Intel", "AMD", "Crucial", "BenQ"],
        "subcats": ["Gaming Laptops", "Thin & Light Laptops", "Desktop PCs", "Monitors", "Keyboards & Mice", "External Storage", "Laptop Bags", "Laptop Stands"],
        "img": "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=400&q=80",
        "prefixes": [
            "Core i5 13th Gen Powerful", "Ryzen 7 Octa-Core High-Speed", "GeForce RTX 4060 Dedicated", "Ultra-Thin Lightweight Metallic", "IPS 144Hz Gaming",
            "M3 Chip Flagship", "Wireless Silent Ergonomic", "Mechanical RGB Hot-Swap", "Fast NVMe Gen4 1TB", "Water-Repellent Padded",
            "All-in-One Core i7", "27-inch 4K UHD Frameless", "Adjustable Aluminium Ergonomic", "High Speed 10Gbps Dock", "Multi-Device Bluetooth"
        ],
        "nouns": [
            ("Thin & Light Laptop (16GB RAM, 512GB SSD, 15.6 FHD)", 46990, "Thin & Light Laptops", "Intel Core i5 13th Gen, anti-glare IPS display, backlit keyboard, 1.6kg"),
            ("Dedicated RTX Gaming Laptop (16GB RAM, 1TB SSD)", 74990, "Gaming Laptops", "AMD Ryzen 7, NVIDIA RTX 4060 8GB graphics, 165Hz high refresh display"),
            ("Demo MacBook Air 13-inch (M2 Chip, 8GB, 256GB)", 89900, "Thin & Light Laptops", "Liquid Retina display, fanless silent design, MagSafe charging, 18h battery"),
            ("All-in-One Desktop PC (23.8 FHD, 16GB, 512GB)", 52990, "Desktop PCs", "Sleek frameless design with wireless keyboard, mouse and pop-up privacy camera"),
            ("27-Inch IPS QHD 144Hz Gaming Monitor", 17990, "Monitors", "1ms response time, AMD FreeSync Premium, HDR10, height adjustable stand"),
            ("24-Inch Full HD Ultra-Slim Borderless Monitor", 8990, "Monitors", "Eye-care low blue light mode, flicker-free panel, HDMI and VGA ports"),
            ("Wireless Multi-Device Keyboard and Mouse Combo", 2499, "Keyboards & Mice", "Connects to 3 devices simultaneously, quiet whisper keys, 24-month battery life"),
            ("Mechanical Gaming Keyboard with RGB Backlighting", 3499, "Keyboards & Mice", "Custom mechanical blue clicky switches, durable aluminum top plate"),
            ("Water-Resistant Laptop Backpack (Up to 15.6-inch)", 1499, "Laptop Bags", "Padded laptop sleeve with anti-theft hidden pocket and external USB charge port"),
            ("Foldable Aluminum Ergonomic Laptop Riser Stand", 899, "Laptop Stands", "6 adjustable angle height settings, ventilated open design prevents overheating"),
            ("1TB NVMe PCIe 4.0 Internal High Speed SSD", 6499, "External Storage", "Read speeds up to 7300 MB/s, ideal for PS5 console and fast PC gaming rigs"),
            ("Dual Fan USB Powered Laptop Cooling Pad", 1199, "Laptop Stands", "Silent 140mm fans with blue LED lights, pass-through USB port, 2 height pegs"),
            ("USB-C Triple Display Docking Station with 100W PD", 4999, "Keyboards & Mice", "Dual HDMI 4K, DisplayPort, Gigabit Ethernet, 4 USB 3.0 ports for laptops"),
            ("Protective Padded Neoprene Laptop Sleeve with Handle", 699, "Laptop Bags", "3-layer shockproof sponge padding with soft fleece interior lining")
        ]
    },
    {
        "category": "TVs & Home Entertainment",
        "brands": ["Sony", "Samsung", "LG", "TCL", "Xiaomi", "OnePlus", "Vu", "JBL", "Zebronics", "Amazon Fire", "ViewSonic", "Hisense"],
        "subcats": ["4K Ultra HD TVs", "OLED & QLED TVs", "Smart TVs", "Soundbars & Subwoofers", "Home Theatre Systems", "Streaming Devices", "Projectors & Screens", "TV Wall Mounts"],
        "img": "https://images.unsplash.com/photo-1593359677879-a4bb92f829d1?w=400&q=80",
        "prefixes": [
            "4K Ultra HD Smart LED", "Quantum Dot QLED 120Hz", "Self-Lit OLED Infinite Contrast", "Dolby Atmos Cinema", "Full HD Smart Google",
            "5.1 Surround Channel Wireless", "4K HDR Streaming Stick", "Portable Smart Android Projector", "Heavy Duty Universal Swivel", "High Speed eARC HDMI",
            "Bezel-Less Metallic Frame", "Game Mode VRR ALLM", "Acoustic Multi-Audio", "Bravia XR Cognitive", "Subwoofer Built-In Powerful"
        ],
        "nouns": [
            ("55-Inch 4K Ultra HD Smart Google TV", 36990, "4K Ultra HD TVs", "Dolby Vision, HDR10+, hands-free voice control, 24W speakers with Dolby Audio"),
            ("65-Inch QLED 4K Smart TV with 120Hz VRR", 59990, "OLED & QLED TVs", "Quantum Dot color gamut, AMD FreeSync for gaming, slim air design with solar remote"),
            ("43-Inch Full HD Smart LED TV with Android 11", 19990, "Smart TVs", "Vivid Picture Engine, built-in Chromecast, dual band Wi-Fi, stereo 20W sound"),
            ("5.1 Channel Soundbar with Wireless Subwoofer & Rear Satellites", 14990, "Soundbars & Subwoofers", "400W powerful output, Dolby Digital surround sound, HDMI ARC and Bluetooth 5.3"),
            ("Dolby Atmos 2.1 Channel Compact Soundbar", 7990, "Soundbars & Subwoofers", "Built-in dual subwoofers, punchy bass, dialogue enhancement voice mode"),
            ("4K Streaming Device with Voice Remote", 3999, "Streaming Devices", "Streams in 4K Ultra HD, Dolby Vision, HDR10+, TV control power and volume buttons"),
            ("Portable Smart Full HD Projector with Android", 11990, "Projectors & Screens", "Auto keystone focus correction, 400 ANSI lumens, built-in Wi-Fi and Bluetooth"),
            ("Universal Full-Motion Swivel & Tilt TV Wall Mount Bracket", 1299, "TV Wall Mounts", "Fits 32 to 65 inch TVs, cold-rolled steel holds up to 45kg, extends 15 inches"),
            ("Fixed Slim Low Profile TV Wall Mount Bracket", 499, "TV Wall Mounts", "Sits just 1 inch from wall, built-in bubble level, fits 24 to 55 inch LED TVs"),
            ("High Speed 8K HDMI 2.1 Braided Cable (2m)", 699, "Soundbars & Subwoofers", "48Gbps bandwidth supports 4K 120Hz and 8K 60Hz with eARC audio return"),
            ("65-Inch OLED 4K Ultra HD Cinema Smart TV", 129990, "OLED & QLED TVs", "Self-lit OLED pixels, alpha AI processor, infinite contrast with G-Sync support"),
            ("32-Inch HD Ready Smart LED TV", 11490, "Smart TVs", "Vibrant colors, 2 HDMI ports, 2 USB ports, access to Netflix, Prime and YouTube"),
            ("Foldable 100-Inch Projector Anti-Crease Screen with Hooks", 999, "Projectors & Screens", "High density thick polyester material supports double sided front and rear projection"),
            ("Backlit Universal TV Learning Remote Control", 399, "Streaming Devices", "Learns infrared commands from existing TV, soundbar and set-top box remotes")
        ]
    },
    {
        "category": "Personal Care",
        "brands": ["Philips", "Braun", "Havells", "Beardo", "Bombay Shaving Company", "Gillette", "Oral-B", "Syska", "Vega", "Nova", "Colgate", "Dyson"],
        "subcats": ["Electric Toothbrushes", "Trimmers & Shavers", "Hair Dryers & Stylers", "Facial Cleansers & Scrubs", "Beard Oils & Kits", "Body Washes & Lotions", "Oral Care & Floss"],
        "img": "https://images.unsplash.com/photo-1556228720-195a672e8a03?w=400&q=80",
        "prefixes": [
            "Cordless Rechargeable Fast", "Skin-Friendly Titanium Coated", "Ionic Conditioning 1800W", "Deep Cleansing Charcoal", "Sonic High Frequency Pulse",
            "Multi-Grooming All-in-1", "Ceramic Coated Straightening", "Waterproof Wet & Dry", "Ayurvedic Growth Enriched", "Anti-Bacterial Moisturizing",
            "Precision Close Foil", "Rechargeable Water Flosser", "Keratin Infused Salon", "Triple Action Whitening", "Cooling Menthol Refresh"
        ],
        "nouns": [
            ("All-in-One Multi Grooming Beard Trimmer (9 Attachments)", 1899, "Trimmers & Shavers", "Self-sharpening stainless steel blades, 60 minutes cordless use, washable heads"),
            ("Electric Rotary Wet & Dry Men's Shaver", 2499, "Trimmers & Shavers", "3D floating rotary heads adjust to facial curves for a clean cut without nicks"),
            ("Rechargeable Sonic Electric Toothbrush with Timer", 1499, "Electric Toothbrushes", "40,000 micro-vibrations per minute, 3 brushing modes with 2-minute smart timer"),
            ("Cordless Portable Dental Water Flosser", 1999, "Oral Care & Floss", "300ml water tank, 3 pressure modes, effectively removes plaque between tight teeth"),
            ("Professional Salon Hair Dryer 2000W with Cool Shot", 1699, "Hair Dryers & Stylers", "Ionic technology reduces frizz, 2 speed and 3 heat settings with concentrator nozzle"),
            ("Ceramic Keratin Hair Straightener Flat Iron", 1799, "Hair Dryers & Stylers", "Extra wide ceramic plates with rapid 30-second heat up up to 210C"),
            ("Activated Charcoal Deep Cleansing Face Wash (150ml)", 349, "Facial Cleansers & Scrubs", "Pollution defense formula draws out stubborn toxins and unclogs congested pores"),
            ("Beard Growth Oil with Redensyl & Almond Oil (50ml)", 399, "Beard Oils & Kits", "Conditions facial hair, prevents itchiness and encourages thicker healthy beard growth"),
            ("Complete 6-Piece Wooden Beard Grooming Kit", 999, "Beard Oils & Kits", "Includes double-sided sandalwood comb, boar bristle brush, scissors and beard balm"),
            ("Refreshing Menthol Body Wash Shower Gel (400ml)", 349, "Body Washes & Lotions", "Crisp cooling sensation with tea tree extract washes away gym sweat and body odor"),
            ("Nose, Ear & Eyebrow Detail Hair Trimmer", 699, "Trimmers & Shavers", "Dual-edge spinning blades with protective cone shield, 100% water washable"),
            ("Automatic 2-in-1 Hair Curler & Waver Barrel", 2199, "Hair Dryers & Stylers", "Tangle-free ceramic tourmaline barrel creates bouncy loose beach waves automatically"),
            ("Sonic Silicone Facial Cleansing Brush Waterproof", 899, "Facial Cleansers & Scrubs", "Soft hygienic silicone bristles with 8 vibration speeds for pore exfoliation"),
            ("Activated Coconut Charcoal Teeth Whitening Powder (50g)", 299, "Oral Care & Floss", "Removes stubborn tea, coffee and tobacco stains naturally without harsh bleach")
        ]
    },
    {
        "category": "Automotive Accessories",
        "brands": ["Bosch", "70mai", "Qubo", "Wuerth", "Godrej aer", "Ambi Pur", "Vega", "Steelbird", "Studds", "Tusa", "Bergmann", "Ceat"],
        "subcats": ["Car Fresheners", "Car Mobile Holders", "Dash Cameras", "Tyre Inflators", "Car Covers", "Seat Covers & Mats", "Helmets & Riding Gear", "Bike Covers"],
        "img": "https://images.unsplash.com/photo-1558981403-c5f9899a28bc?w=400&q=80",
        "prefixes": [
            "Digital Auto Cut-Off", "Full HD 1080p Night Vision", "Heavy Duty Waterproof All-Weather", "Magnetic Automatic Clamp", "DOT & ISI Certified Safety",
            "High Pressure Cyclone 12V", "Organic Spill-Proof Gel", "Dual Layer Anti-Theft", "Universal 7D Custom Fit", "Anti-Scratch Microfiber",
            "Quick Release Double D-Ring", "Smart Tire Pressure Monitoring", "Emergency Window Glass Breaker", "Aerodynamic Glossy Finish", "Multi-Pocket Backseat Organizer"
        ],
        "nouns": [
            ("Portable 12V Car Tyre Inflator with Digital Gauge", 1999, "Tyre Inflators", "Auto shut-off when preset pressure is reached, built-in bright LED emergency light"),
            ("Full HD 1080p Car Dash Camera with Night Vision", 3999, "Dash Cameras", "Sony Starvis image sensor, 140 wide angle lens, loop recording with G-sensor"),
            ("Smart Automatic Clamping Qi Wireless Car Phone Charger", 1499, "Car Mobile Holders", "Infrared motion sensor opens and closes arms automatically with 15W fast charging"),
            ("Spill-Proof Car Gel Air Freshener Canister", 299, "Car Fresheners", "Rich essential oil fragrance lasts up to 60 days, fits neatly in car cup holder"),
            ("All-Weather Waterproof Car Body Cover with Mirror Pockets", 1499, "Car Covers", "UV reflective silver fabric shields from bird droppings, dust, rain and scorching sun"),
            ("7D Custom Fitted Car Floor Mats Set", 3499, "Seat Covers & Mats", "Waterproof PU leather with detachable curly foot pads, anti-skid bottom spikes"),
            ("Full Face Motorcycle Helmet with Double Visor (ISI Certified)", 1999, "Helmets & Riding Gear", "Aerodynamic ventilation, scratch resistant outer visor with drop-down inner sun shield"),
            ("Waterproof Heavy Duty Motorcycle Two-Wheeler Cover", 599, "Bike Covers", "Elastic hem with buckle clip, heat resistant fabric protects against exhaust pipes"),
            ("High Power 12V Wet and Dry Portable Car Vacuum Cleaner", 1299, "Tyre Inflators", "120W motor with washable stainless steel HEPA filter and 16ft long 12V power cord"),
            ("Solar Powered Tire Pressure Monitoring System (TPMS)", 2499, "Tyre Inflators", "4 external waterproof valve sensors transmit real-time tyre pressure and temperature"),
            ("Leatherette Car Backseat Hanging Organizer with Tablet Holder", 799, "Seat Covers & Mats", "9 utility pockets hold bottles, umbrellas, snacks and transparent touchscreen tablet slot"),
            ("Leather Riding Gloves with Carbon Fiber Knuckle Armor", 999, "Helmets & Riding Gear", "Touchscreen fingertips on thumb and index finger with breathable air vents"),
            ("Jumper Cables Heavy Duty Booster Clamp Set (1000A)", 899, "Tyre Inflators", "Tangle-free copper coated aluminum core cables for dead car battery jumpstarts"),
            ("Car Windshield Sunshade Umbrella Foldable (Universal)", 499, "Car Covers", "Blocks 99% UV rays and reduces dashboard interior heat by up to 25 degrees")
        ]
    },
    {
        "category": "Health & Wellness",
        "brands": ["MuscleBlaze", "Optimum Nutrition", "Himalaya", "Omron", "Dr. Morepen", "Accu-Chek", "Fast&Up", "Kapiva", "HealthKart", "Moov", "Volini", "Dettol"],
        "subcats": ["Whey Protein", "Mass Gainers", "Multivitamins", "Fish Oil", "BP Monitors", "Glucometers", "Weighing Scales", "Pain Relief"],
        "img": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=400&q=80",
        "prefixes": [
            "100% Pure Whey Protein Isolate", "Fully Automatic Digital Upper Arm", "High Potency Triple Strength Omega 3", "Daily One-A-Day Comprehensive",
            "High Precision Digital Body Fat", "Pain Relieving Fast Acting Gel", "Sugar-Free Effervescent Electrolyte", "Clinically Proven Blood Glucose",
            "Ayurvedic Herbal Organic Pure", "High Calorie Muscle Mass Gainer", "Natural Collagen Peptides Powder", "Non-Contact Infrared Forehead",
            "Cold Pressed Virgin Evening Primrose", "Orthopedic Lumbar Support Posture", "Warm Heating Orthopedic Electric"
        ],
        "nouns": [
            ("100% Whey Protein Powder 1kg (Chocolate Fudge)", 2199, "Whey Protein", "25g protein and 5.5g BCAAs per serving, lab tested with fast digestive enzymes"),
            ("Triple Strength Deep Sea Fish Oil 1000mg (60 Softgels)", 699, "Fish Oil", "840mg Omega-3 (EPA 500mg + DHA 300mg) molecularly distilled, zero fishy burps"),
            ("Daily Multivitamin Tablets for Men & Women (60 Tabs)", 499, "Multivitamins", "Packed with 25 essential vitamins, minerals, ginseng and amino acids for energy"),
            ("Digital Upper Arm Blood Pressure Monitor (Fully Automatic)", 1799, "BP Monitors", "Intellisense technology, irregular heartbeat detection, 60 readings memory with date"),
            ("Accurate Blood Glucose Monitoring Glucometer Kit", 999, "Glucometers", "Includes meter, lancing device and 25 test strips, requires only tiny 0.6ul blood drop"),
            ("Smart Bluetooth Body Composition Weighing Scale", 1499, "Weighing Scales", "Measures 13 body metrics: weight, BMI, body fat %, muscle mass and visceral fat"),
            ("Ayurvedic Pain Relief Spray for Muscle & Joint Pain (100g)", 249, "Pain Relief", "Deep penetrating micro-particles for fast soothing relief from backache and sprains"),
            ("High Calorie Weight Mass Gainer 1kg with Complex Carbs", 1299, "Mass Gainers", "Over 1000 calories and 60g protein per day with added digestive enzymes"),
            ("Effervescent Vitamin C 1000mg + Zinc (Pack of 20 Tabs)", 299, "Multivitamins", "Tangy orange fizzy drink tablets boost daily immunity and skin radiance"),
            ("Pure Himalayan Shilajit Resin Form 20g with Gold Test", 999, "Whey Protein", "Rich in 75% fulvic acid and 84+ trace minerals for stamina, endurance and vitality"),
            ("Electric Orthopedic Heating Belt Pad for Back Pain", 799, "Pain Relief", "3 thermostat heat settings with soft washable cotton cover and auto cut-off"),
            ("Ergonomic Back Support Memory Foam Lumbar Cushion", 899, "Pain Relief", "Relieves lower back pressure for office chairs, car seats and work from home"),
            ("Organic Apple Cider Vinegar with Mother 500ml", 399, "Multivitamins", "Raw, unfiltered, unpasteurized natural probiotic tonic assists healthy digestion"),
            ("Non-Contact Infrared Digital Forehead Thermometer", 899, "BP Monitors", "1-second instant fever detection with colored fever alert LCD backlight")
        ]
    },
    {
        "category": "Pet Supplies",
        "brands": ["Pedigree", "Whiskas", "Royal Canin", "Drools", "Farmina", "Himalaya Pets", "Lozalo", "Meat Up", "Purepet", "Catfest", "KONG", "Wahl"],
        "subcats": ["Dog Food", "Cat Food", "Collars & Leashes", "Pet Grooming", "Pet Beds", "Scratching Posts", "Interactive Pet Toys", "Feeding Bowls"],
        "img": "https://images.unsplash.com/photo-1583511655857-d19b40a7a54e?w=400&q=80",
        "prefixes": [
            "Complete & Balanced Adult", "Kitten Growth Wet Pouch", "Heavy Duty Reflective Nylon", "Anti-Tick & Flea Natural Herbal", "Ultra-Plush Washable Orthopedic",
            "Multi-Level Sisal Rope Cat", "Indestructible Natural Rubber Tough", "Stainless Steel Anti-Skid Rubber", "Grain-Free High Protein Real",
            "Odor Control Clumping Bentonite", "Self-Cleaning Deshedding Slicker", "Interactive Laser Pointer Chasing", "Waterproof Car Rear Seat", "Gentle Tearless Puppy"
        ],
        "nouns": [
            ("Adult Dry Dog Food Chicken & Vegetables (3kg)", 849, "Dog Food", "Complete balanced nutrition with omega-6 and zinc for healthy skin and shiny coat"),
            ("Wet Cat Food Pouches Tuna in Jelly (Pack of 12 x 85g)", 540, "Cat Food", "Tempting fish aroma packed with taurine, vitamin A and essential fatty acids"),
            ("Reflective Retractable Dog Leash with Anti-Slip Handle (5m)", 799, "Collars & Leashes", "Tangle-free 360 tape movement with one-button brake and lock system"),
            ("Anti-Tick and Flea Dog Shampoo (500ml)", 399, "Pet Grooming", "Infused with natural neem oil and eucalyptus to soothe itchy irritated skin"),
            ("Round Calming Donut Fluffy Pet Bed (Diameter 60cm)", 1299, "Pet Beds", "Raised rim creates a sense of security and provides head and neck orthopedic relief"),
            ("Multi-Level Cat Scratching Post Tree with Perch & Toy", 1899, "Scratching Posts", "Durable natural sisal rope scratching posts protect furniture from cat claws"),
            ("Durable Natural Rubber Chew Ball Toy for Dogs", 349, "Interactive Pet Toys", "Teeth cleaning textured nubs, can be stuffed with peanut butter or treats"),
            ("Stainless Steel Double Pet Food and Water Bowls with Stand", 699, "Feeding Bowls", "Rust-resistant removable stainless steel bowls with non-skid rubber base holder"),
            ("Bentonite Clumping Cat Litter Lavender Scented (10kg)", 799, "Cat Food", "Fast clumping formula traps ammonia odors instantly, 99% dust free"),
            ("Self-Cleaning Slicker Brush for Dogs and Cats", 399, "Pet Grooming", "Retractable bristle design releases trapped fur and hairballs with one click"),
            ("Waterproof Dog Car Seat Cover with Mesh Window", 1499, "Collars & Leashes", "Heavy duty 600D oxford hammock protects back car seats from mud, fur and claw marks"),
            ("Interactive Moving Laser Cat Toy with Auto Timer", 699, "Interactive Pet Toys", "Random 360 circular red laser patterns keep indoor cats actively exercising"),
            ("Crunchy Dental Dog Treats Pack of 3 (Oral Care)", 499, "Dog Food", "Helps reduce tartar and plaque buildup, freshens breath with mint flavor"),
            ("Nail Clipper and Trimmer with Safety Guard for Pets", 299, "Pet Grooming", "Sharp stainless steel blades with safety guard prevent cutting sensitive quicks")
        ]
    },
    {
        "category": "Travel & Luggage",
        "brands": ["American Tourister", "Skybags", "Safari", "VIP", "Aristocrat", "Wildcraft", "Samsonite", "Mokobara", "Delsey", "Tommy Hilfiger", "Traveler's Choice", "Swiss Military"],
        "subcats": ["Hard Luggage", "Soft Luggage", "Cabin Luggage", "Large Luggage", "Backpacks", "Laptop Backpacks", "Duffel Bags", "Travel Accessories"],
        "img": "https://images.unsplash.com/photo-1565026057447-bc90a3dceb87?w=400&q=80",
        "prefixes": [
            "Scratch-Resistant Polycarbonate Hard", "Ultra-Lightweight 8-Wheel Spinner", "TSA Approved Lock Expandable", "Water-Repellent Ripstop Fabric",
            "Ergonomic Padded Lumbar Support", "Convertible Foldable Weekender", "Memory Foam Micro-Velvet Ergonomic", "Tear-Proof Ballistic Nylon",
            "Combination Number Padlock Secure", "Cabin Approved 55cm Trolley", "Large Check-in 75cm Suitcase", "Anti-Theft Hidden Zipper", "Multipurpose Packing Compression"
        ],
        "nouns": [
            ("Hard Sided Polycarbonate Cabin Trolley Bag 55cm", 2999, "Cabin Luggage", "360-degree silent 8-spinner wheels, integrated 3-digit combination lock, 38L"),
            ("Large Check-In Hard Suitcase Trolley 75cm (105L)", 4999, "Large Luggage", "Lightweight polypropylene shell with scratch-resistant texture and expandable zip"),
            ("Soft Sided 4-Wheel Medium Travel Suitcase 68cm", 3499, "Soft Luggage", "Tough polyester fabric with two front quick-access zipper pockets and corner guards"),
            ("Outdoor Adventure Rucksack Hiking Backpack 55L", 2199, "Backpacks", "Ergonomic internal metal stay frame, waterproof rain cover and sleeping bag straps"),
            ("Executive Anti-Theft Laptop Backpack (15.6-Inch)", 1799, "Laptop Backpacks", "Hidden rear security zipper, external USB power pass-through, waterproof fabric"),
            ("Foldable Gym & Travel Duffel Bag with Shoe Compartment", 899, "Duffel Bags", "Separate ventilated shoe compartment with wet towel pocket and shoulder strap"),
            ("Memory Foam Neck Travel Pillow with Eye Mask & Earplugs", 699, "Travel Accessories", "360-degree ergonomic chin support with breathable washable cooling cover"),
            ("Compression Travel Packing Cubes Set of 6", 899, "Travel Accessories", "Double zipper compression saves 60% luggage space, organizes shirts, underwear and shoes"),
            ("Universal TSA Approved Luggage Cable Padlocks (Pack of 2)", 599, "Travel Accessories", "Flexible braided steel cable allows TSA airport security officers to inspect without damage"),
            ("Waterproof Hanging Travel Toiletry Kit Organizer Bag", 649, "Travel Accessories", "Multiple transparent mesh compartments with durable 360 rotating hanging hook"),
            ("Wheeled Travel Duffel Bag with Telescopic Handle 65cm", 1999, "Duffel Bags", "Smooth corner roller blade wheels with heavy duty grip handles and 60L capacity"),
            ("Underseat Compact Rolling Cabin Luggage Suitcase", 2499, "Cabin Luggage", "Fits underneath airline seats, padded interior fits 14-inch laptop and 2-day clothing"),
            ("RFID Blocking Family Passport Holder Wallet with Pen", 499, "Travel Accessories", "Holds up to 4 passports, boarding passes, credit cards and foreign currencies safely"),
            ("Digital Portable Luggage Scale with Backlit LCD Screen", 449, "Travel Accessories", "Precision strain gauge avoids overweight airport baggage fees, measures up to 50kg")
        ]
    }
]

def build_and_seed_catalogue():
    print(f"Beginning generation of 20 categories...")
    init_db()

    with get_db() as conn:
        cursor = conn.cursor()

        # Wipe existing products so clean 1,040+ products are inserted with unique IDs
        cursor.execute("PRAGMA foreign_keys = OFF")
        cursor.execute("DELETE FROM products")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='products'")
        conn.commit()

        insert_sql = """
            INSERT INTO products (
                id, name, category, subcategory, brand, price,
                discount_percentage, specifications, description,
                image_url, source_type, rating, stock, review_count_demo, featured
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        prod_id = 1
        total_inserted = 0

        for cat_info in CATEGORY_METADATA:
            cat_name = cat_info["category"]
            brands = cat_info["brands"]
            prefixes = cat_info["prefixes"]
            nouns = cat_info["nouns"]
            cat_img = cat_info["img"]

            # Generate at least 52 products per category
            # We take each noun (14 items) and combine with prefixes/brands to reach 52 items
            category_products = []
            
            # Step 1: Add the 14 base items
            for noun_tuple in nouns:
                name, price, subcat, desc = noun_tuple
                category_products.append({
                    "name": name,
                    "price": price,
                    "subcat": subcat,
                    "desc": desc
                })

            # Step 2: Generate variations until we reach at least 52 products
            var_idx = 0
            while len(category_products) < 52:
                base_noun = nouns[var_idx % len(nouns)]
                prefix = prefixes[var_idx % len(prefixes)]
                var_brand = brands[var_idx % len(brands)]

                # Build varied product
                base_name = base_noun[0]
                base_price = base_noun[1]
                subcat = base_noun[2]
                base_desc = base_noun[3]

                # Tweak price realistically
                price_multiplier = 0.85 + ((var_idx * 7) % 35) * 0.01
                new_price = round(base_price * price_multiplier, 0)
                if new_price < 99: new_price = 149
                # Round to nice endings like 99, 49, 90
                new_price = int(new_price // 10 * 10 + 9)

                new_name = f"{var_brand} {prefix} {base_name}"
                new_desc = f"{prefix} {base_name}. {base_desc}"

                category_products.append({
                    "name": new_name,
                    "price": new_price,
                    "subcat": subcat,
                    "desc": new_desc
                })
                var_idx += 1

            # Insert all products for this category
            for idx, p in enumerate(category_products):
                brand = brands[idx % len(brands)]
                rating = round(3.9 + ((idx * 3 + len(p['name'])) % 11) * 0.1, 1)
                if rating > 5.0: rating = 4.8
                stock = 15 + ((idx * 19) % 320)
                reviews = 65 + ((idx * 347) % 24500)
                disc = ((idx * 8 + 15) % 45) + 15
                featured = 1 if (idx < 6) else 0

                specs = {
                    "Brand": brand,
                    "Category": cat_name,
                    "Subcategory": p["subcat"],
                    "Warranty": "1 Year Brand Warranty" if "Electronics" in cat_name or "Mobiles" in cat_name or "Appliances" in cat_name or "Laptops" in cat_name else "100% Genuine Assured Quality",
                    "Return Policy": "7 Days Replacement or Refund Guarantee",
                    "Stock Status": "In Stock" if stock > 0 else "Limited Stock Available"
                }

                cursor.execute(insert_sql, (
                    prod_id,
                    p["name"],
                    cat_name,
                    p["subcat"],
                    brand,
                    p["price"],
                    disc,
                    json.dumps(specs),
                    p["desc"],
                    cat_img,
                    "demo",
                    rating,
                    stock,
                    reviews,
                    featured
                ))

                prod_id += 1
                total_inserted += 1

            print(f"  [OK] Category '{cat_name}': Inserted {len(category_products)} products.")

        cursor.execute("PRAGMA foreign_keys = ON")
        conn.commit()
        print(f"\n[DONE] Successfully seeded {total_inserted} products across {len(CATEGORY_METADATA)} categories.")
        return total_inserted

if __name__ == "__main__":
    count = build_and_seed_catalogue()
    print(f"Total verified in DB: {count}")
