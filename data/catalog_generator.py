"""
data/catalog_generator.py
-------------------------
Large-scale Product Catalog Generator for PreTwin AI.
Generates 2,100+ realistic, high-quality e-commerce products across 13 major categories:
- Mobiles
- Electronics
- Laptops & Computers
- Fashion
- Footwear
- Beauty & Personal Care
- Home & Kitchen
- Appliances
- Books & Stationery
- Toys & Baby Products
- Sports & Fitness
- Food & Grocery
- Furniture

Provides genuine brand names, detailed technical specifications, Unsplash CDN images,
MRP / discount calculations, availability statuses, and official marketplace reference links.
"""

import json
from typing import List, Dict, Any

CATEGORIES_DATA = {
    "Mobiles": {
        "brands": ["Apple", "Samsung", "OnePlus", "Xiaomi", "Realme", "Vivo", "Oppo", "Google", "Motorola", "Nothing"],
        "subcategories": [
            ("Smartphones", ["iPhone 15", "iPhone 15 Pro", "iPhone 14", "Galaxy S24", "Galaxy S23 FE", "Galaxy A55 5G", "OnePlus 12", "OnePlus 12R", "OnePlus Nord CE 4", "Redmi Note 13 Pro+", "Xiaomi 14", "Realme 12 Pro+", "Vivo V30 Pro", "Oppo Reno 11 Pro", "Pixel 8", "Pixel 7a", "Moto Edge 50 Pro", "Nothing Phone (2)", "Nothing Phone (2a)"], (14999, 134999), 18),
            ("Budget 5G Phones", ["Galaxy M15 5G", "Galaxy F15 5G", "Redmi 13C 5G", "Realme Narzo 70x", "Moto G34 5G", "Poco M6 Pro 5G", "Vivo T3x 5G", "Lava Blaze Curve 5G"], (9999, 18999), 15),
            ("Mobile Accessories", ["Fast Charger 65W GaN", "Magnetic Wireless Power Bank 10000mAh", "Braided USB-C Cable 2M", "Shockproof Armor Case", "Tempered Glass 9H Screen Protector", "Car Mount Phone Holder MagSafe", "OTG Adapter Type-C"], (299, 3499), 12),
        ],
        "image": "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=500&q=80",
        "specs_template": {"Display": "6.7-inch AMOLED 120Hz", "Processor": "Octa-core 5G SoC", "Camera": "50MP OIS Triple Camera", "Battery": "5000 mAh with 67W Fast Charging", "RAM": "8GB / 12GB", "Storage": "128GB / 256GB / 512GB", "OS": "Android 14 / iOS 17"}
    },
    "Electronics": {
        "brands": ["Sony", "JBL", "Bose", "boAt", "Noise", "Fire-Boltt", "Apple", "Canon", "Sennheiser", "Marshall"],
        "subcategories": [
            ("Headphones & Earbuds", ["WH-1000XM5 Wireless ANC", "QuietComfort 45", "Airdopes 441 Pro", "Tune 760NC Over-Ear", "AirPods Pro Gen 2", "Momentum 4 Wireless", "Rockerz 550", "ColorFit Buds S1", "Major IV Wireless"], (1299, 32999), 20),
            ("Smart Watches", ["Galaxy Watch 6 Classic", "Apple Watch SE Gen 2", "ColorFit Pro 5 Max", "Ninja Calling Pro", "Wave Elevate AMOLED", "Instinct 2 Solar", "Forerunner 265", "Venu 3 GPS"], (1499, 44999), 16),
            ("Audio & Speakers", ["Flip 6 Waterproof Speaker", "SoundLink Flex Bluetooth", "Stone 1200 14W Speaker", "Stanmore III Bluetooth", "HT-S20R 5.1ch Soundbar", "Cinema SB190 Dolby Atmos", "PartyBox 110 High Power"], (1999, 39999), 15),
            ("Cameras & Accessories", ["EOS R50 Mirrorless Camera", "Alpha 7 IV Full Frame", "Hero 12 Black Action Camera", "Insta360 X3 360 Camera", "Lightweight Tripod 50-inch", "Ring Light 18-inch with Stand"], (999, 199999), 10),
        ],
        "image": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=500&q=80",
        "specs_template": {"Connectivity": "Bluetooth 5.3 / Type-C", "Battery Life": "Up to 36 hours", "Noise Cancellation": "Active Noise Cancellation (ANC)", "Water Resistance": "IPX5 / IP68 Rated", "Warranty": "1 Year Manufacturer"}
    },
    "Laptops & Computers": {
        "brands": ["Apple", "Dell", "HP", "Lenovo", "ASUS", "Acer", "MSI", "Logitech", "SanDisk", "Samsung"],
        "subcategories": [
            ("Laptops", ["MacBook Air M2 13-inch", "MacBook Pro M3 14-inch", "XPS 13 Ultrabook", "Inspiron 15 Thin & Light", "Pavilion x360 2-in-1", "Spectre x360 OLED", "ThinkPad E14 Gen 5", "IdeaPad Slim 3 Core i5", "ROG Zephyrus G14 Gaming", "TUF Gaming F15", "Aspire 5 Slim", "Predator Helios Neo 16"], (34990, 224990), 22),
            ("Monitors & Displays", ["27-inch 4K UHD IPS Monitor", "24-inch Full HD 165Hz Gaming Monitor", "34-inch Curved UltraWide Monitor", "Portable USB-C 15.6-inch Screen", "Smart Monitor M7 with Tizen OS"], (8499, 54999), 14),
            ("PC Accessories & Storage", ["MX Master 3S Wireless Mouse", "MX Keys Advanced Keyboard", "G502 Hero Gaming Mouse", "Mechanical Gaming Keyboard RGB", "Extreme Portable SSD 1TB NVMe", "T7 Shield 2TB Rugged SSD", "Wi-Fi 6 Dual-Band Mesh Router"], (799, 18999), 16),
        ],
        "image": "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?auto=format&fit=crop&w=500&q=80",
        "specs_template": {"Processor": "Intel Core i5/i7 13th Gen / AMD Ryzen 7 / Apple Silicon", "RAM": "16GB DDR5 5200MHz", "Storage": "512GB / 1TB PCIe NVMe SSD", "Display": "15.6-inch Full HD Anti-Glare 300 nits", "Graphics": "Intel Iris Xe / NVIDIA RTX 4060 6GB", "OS": "Windows 11 Home / macOS Sonoma"}
    },
    "Fashion": {
        "brands": ["Levi's", "Zara", "H&M", "Allen Solly", "Peter England", "Biba", "W", "Manyavar", "U.S. Polo Assn", "FabIndia"],
        "subcategories": [
            ("Men's Wear", ["511 Slim Fit Stretchable Jeans", "Regular Fit Cotton Casual Shirt", "Classic Polo Collar T-Shirt", "Formal Slim Fit Trouser", "Single Breasted Blazer Navy", "Linen Kurta with Mandarin Collar", "Puffer Bomber Jacket", "Track Pants Dri-Fit Cotton"], (599, 4999), 24),
            ("Women's Ethnic & Fusion", ["Printed Straight Cotton Kurta", "Anarkali Suit Set with Dupatta", "Chanderi Silk Embroidered Saree", "Palazzo Suit Set Festive Wear", "Ethnic Printed Kaftan", "Handloom Tussar Silk Saree", "Embroidered Kurti with Trouser"], (799, 7999), 22),
            ("Women's Western Wear", ["Floral Wrap Midi Dress", "High-Rise Skinny Fit Denims", "Relaxed Fit Cotton Shirt", "Oversized Graphic Sweatshirt", "Tailored Formal Trousers", "Crop Top Ribbed Knit", "Puffer Winter Trench Coat"], (499, 3999), 20),
            ("Fashion Accessories", ["Genuine Leather Reversible Belt", "Classic Aviator UV Polarized Sunglasses", "Formal Leather Wallet Bi-Fold", "Silk Printed Scarf", "Canvas Messenger Bag"], (349, 2499), 14),
        ],
        "image": "https://images.unsplash.com/photo-1445205170230-053b83016050?auto=format&fit=crop&w=500&q=80",
        "specs_template": {"Fabric": "100% Breathable Combed Cotton / Linen Blend", "Pattern": "Solid / Contemporary Printed", "Fit": "Regular / Tailored Slim Fit", "Care": "Machine Wash Cold, Gentle Cycle", "Occasion": "Casual / Workwear / Festive"}
    },
    "Footwear": {
        "brands": ["Nike", "Adidas", "Puma", "Reebok", "Skechers", "Woodland", "Clarks", "Bata", "Sparx", "Crocs"],
        "subcategories": [
            ("Sports & Running Shoes", ["Air Zoom Pegasus 40", "Revolution 7 Road Running", "Ultraboost Light", "Galaxy 6 Cushioned Shoes", "Nitro Velocity Running", "Smash v2 Classic", "Floatride Energy 5", "Go Run Consistent"], (1499, 14999), 24),
            ("Casual & Sneakers", ["Air Force 1 '07 Classic", "Stan Smith Originals", "Suede Classic XXI Sneaker", "Court Royale 2 Low", "D'Lites Memory Foam Sneaker", "Classic Clog Water Resistant", "Canvas Low-Top Slip-On"], (899, 8999), 22),
            ("Formal & Leather Shoes", ["Derby Leather Formal Shoes", "Oxford Cap-Toe Genuine Leather", "Slip-On Penny Loafers", "Brogue Tan Leather Formal", "Comfort Sole Monk Strap"], (1299, 7999), 16),
            ("Sandals & Floaters", ["Outdoor Trail Leather Sandals", "Hydro Sport Water Sandals", "Daily Comfort Thong Slippers", "Slide Sandals Soft EVA Footbed"], (499, 2999), 14),
        ],
        "image": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=500&q=80",
        "specs_template": {"Outer Material": "Breathable Mesh / Premium Full Grain Leather", "Sole Material": "High-Traction Abrasion Rubber", "Closure": "Lace-Up / Slip-On", "Cushioning": "Responsive Foam Midsole with Arch Support", "Weight": "Approx. 280g per shoe"}
    },
    "Beauty & Personal Care": {
        "brands": ["L'Oreal", "Nivea", "Maybelline", "Mamaearth", "Plum", "The Body Shop", "Forest Essentials", "Philips", "Neutrogena", "Biotique"],
        "subcategories": [
            ("Skincare Essentials", ["Revitalift 1.5% Hyaluronic Acid Serum", "Ultra Sheer Dry-Touch Sunscreen SPF 50+", "Vitamin C Daily Glow Face Serum", "Green Tea Pore Cleansing Face Wash", "Hydro Boost Water Gel Moisturizer", "Rice Water Deep Cleansing Gel", "Night Repair Anti-Aging Cream"], (249, 2199), 24),
            ("Hair Care & Styling", ["Total Repair 5 Hair Mask", "Rosemary Anti-Hair Fall Shampoo", "Argan Oil Hair Treatment Serum", "Keratin Smooth Conditioner", "Scalp Massager Stimulator Brush", "Nourishing Onion Hair Oil 200ml"], (199, 1599), 20),
            ("Grooming & Appliances", ["OneBlade Hybrid Beard Trimmer", "Cordless Multigroom 9-in-1 Groomer", "ThermoProtect 2100W Hair Dryer", "Kerashine Titanium Hair Straightener", "Sonic Electric Toothbrush USB-C"], (899, 4999), 16),
            ("Fragrances & Body Care", ["Aqua Woody Long Lasting EDP 100ml", "Vanilla Mist Body Fragrance 150ml", "Deep Moisture Cocoa Butter Lotion 400ml", "Exfoliating Coffee Body Scrub 250g"], (399, 3499), 16),
        ],
        "image": "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?auto=format&fit=crop&w=500&q=80",
        "specs_template": {"Skin / Hair Type": "All Skin & Hair Types", "Key Ingredients": "Hyaluronic Acid, Vitamin C, Niacinamide, Aloe Vera", "Formulation": "Dermatologically Tested, Paraben-Free, Non-Comedogenic", "Volume / Quantity": "50ml / 100ml / 250ml", "Expiry": "24 Months from Manufacture"}
    },
    "Home & Kitchen": {
        "brands": ["Prestige", "Hawkins", "Milton", "Cello", "Pigeon", "Bombay Dyeing", "Solimo", "Tupperware", "Borosil", "Kaff"],
        "subcategories": [
            ("Cookware & Pressure Cookers", ["Hard Anodized Pressure Cooker 5L", "Granite Non-Stick 3-Piece Cookware Set", "Triply Stainless Steel Kadai with Lid", "Cast Iron Skillet Pre-Seasoned 10-inch", "Induction Bottom Milk Pan 1.5L"], (799, 6499), 22),
            ("Kitchen Storage & Containers", ["Borosilicate Glass Airtight Containers 4-Pack", "Stainless Steel Thermosteel Water Bottle 1L", "Modular Spice Rack Organizer 16 Jars", "Microwave Safe BPA-Free Lunch Box 3-Tier"], (299, 2499), 20),
            ("Bedding & Furnishings", ["100% Pure Cotton King Bed Sheet with 2 Pillow Covers", "Microfiber Ultra Soft Reversible Comforter", "Blackout Room Darkening Eyelet Curtains 7ft", "Memory Foam Orthopedic Pillow with Bamboo Cover"], (599, 3999), 20),
            ("Home Decor & Utility", ["Nordic Minimalist LED Desk Lamp", "Aroma Essential Oil Diffuser Ultrasonic", "Heavy-Duty Wall Hanging Cloth Drying Stand", "Step Dustbin Stainless Steel 12L"], (449, 2999), 16),
        ],
        "image": "https://images.unsplash.com/photo-1556911220-e15b29be8c8f?auto=format&fit=crop&w=500&q=80",
        "specs_template": {"Material": "Food Grade 304 Stainless Steel / 100% Cotton / Borosilicate Glass", "Capacity / Size": "Standard E-Commerce Size Specifications", "Compatibility": "Gas Stove & Induction Compatible", "Dishwasher Safe": "Yes, Top Rack Safe", "Warranty": "2 Years Manufacturer Warranty"}
    },
    "Appliances": {
        "brands": ["LG", "Samsung", "Whirlpool", "IFB", "Godrej", "Philips", "Bajaj", "Havells", "Voltas", "Dyson"],
        "subcategories": [
            ("Kitchen Small Appliances", ["Digital Air Fryer 4.1L Rapid Air", "750W Heavy-Duty Mixer Grinder with 3 Jars", "28L Convection Microwave Oven", "Stainless Steel Electric Kettle 1.8L", "2-Slice Automatic Pop-Up Toaster 800W", "Cold Press Slow Masticating Juicer"], (999, 14999), 22),
            ("Refrigerators & Cooling", ["260L 3-Star Frost Free Double Door Refrigerator", "190L 4-Star Inverter Direct Cool Single Door", "1.5 Ton 5-Star Inverter Split AC with Anti-Bacterial Filter", "Desert Air Cooler with Honeycomb Pads 70L"], (11990, 54990), 16),
            ("Washing Machines", ["7.5 Kg 5-Star Fully Automatic Front Load Washer", "7.0 Kg Smart Inverter Top Load Washer", "Semi-Automatic 8.0 Kg Twin Tub Washer"], (9499, 38999), 14),
            ("Home Cleaning & Climate", ["Cord-Free Powerful Stick Vacuum Cleaner", "HEPA Filter Smart Air Purifier with App Control", "Storage Water Heater Geyser 25L 5-Star"], (2499, 44999), 14),
        ],
        "image": "https://images.unsplash.com/photo-1583863788434-e58a36330cf0?auto=format&fit=crop&w=500&q=80",
        "specs_template": {"Power Consumption": "750W - 1500W / 5-Star BEE Energy Rating", "Capacity": "Large Family Sized", "Control Type": "Digital Touch Screen / Dial Controls", "Motor Warranty": "5 to 10 Years Inverter Motor Warranty", "Voltage": "220-240V AC 50Hz"}
    },
    "Books & Stationery": {
        "brands": ["Penguin", "HarperCollins", "Oxford", "Classmate", "Parker", "Camlin", "Casio", "Faber-Castell", "Rupa", "Bloomsbury"],
        "subcategories": [
            ("Bestselling Non-Fiction", ["Atomic Habits by James Clear", "The Psychology of Money by Morgan Housel", "Thinking, Fast and Slow", "Sapiens: A Brief History of Humankind", "Deep Work by Cal Newport", "Rich Dad Poor Dad", "Start with Why by Simon Sinek"], (249, 999), 24),
            ("Fiction & Literature", ["The Midnight Library by Matt Haig", "To Kill a Mockingbird", "Norwegian Wood by Haruki Murakami", "The Alchemist 25th Anniversary Edition", "A Game of Thrones: A Song of Ice and Fire", "Kite Runner by Khaled Hosseini"], (199, 899), 22),
            ("Office & Fine Stationery", ["Beta Stainless Steel Rollerball Pen", "Vector Chrome Trim Fountain Pen", "Spiral Hardcover Journal Notebook 240 Pages", "Scientific Calculator 417 Functions fx-991CW", "Artist Watercolor Pencils 24 Shades Set", "Desktop Mesh Organizer 6-Tier"], (149, 1999), 22),
        ],
        "image": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?auto=format&fit=crop&w=500&q=80",
        "specs_template": {"Format": "Paperback / Hardcover / Archival Quality", "Language": "English", "Pages / Sheet Count": "280 - 450 Pages / 80 GSM Acid-Free Paper", "Publisher": "Renowned International Publisher", "ISBN": "Standard 13-digit ISBN"}
    },
    "Toys & Baby Products": {
        "brands": ["LEGO", "Hot Wheels", "Barbie", "Fisher-Price", "Funskool", "Nerf", "Chicco", "Pampers", "Mee Mee", "Hamleys"],
        "subcategories": [
            ("Building & STEM Toys", ["Speed Champions Sports Car Set", "City Police Station Building Kit", "Robotics Coding STEM Discovery Kit", "Magnetic Building Tiles 60-Piece Set", "Architectural Landmark 3D Puzzle"], (799, 8999), 22),
            ("Action & Vehicles", ["Monster Truck Die-Cast 1:24 Scale", "Remote Control 4WD Stunt Rock Crawler", "Elite 2.0 Commander Motorized Blaster", "Die-Cast 5-Car Gift Pack High Speed"], (399, 4499), 20),
            ("Games & Dolls", ["Monopoly Deluxe Edition Board Game", "Scrabble Crossword Classic Word Game", "Fashion Doll with Wardrobe & Accessories", "Catan Strategy Board Game"], (499, 3999), 18),
            ("Baby Essentials", ["Foldable Lightweight Baby Stroller", "Multifunction Baby High Chair 3-in-1", "Gentle Baby Feeding Bottle BPA Free 250ml", "Anti-Rash Diapers Pants Monthly Box 128s"], (399, 11999), 16),
        ],
        "image": "https://images.unsplash.com/photo-1566576912321-d58ddd7a6088?auto=format&fit=crop&w=500&q=80",
        "specs_template": {"Age Range": "3+ Years / 6-12 Years / Infants", "Material": "100% Non-Toxic BPA-Free ABS Plastic", "Safety Certification": "EN71 / BIS Quality Certified", "Battery Required": "No / 2x AA Included"}
    },
    "Sports & Fitness": {
        "brands": ["Decathlon", "Cosco", "Yonex", "Nivia", "Cultsport", "Boldfit", "Strauss", "SG", "SS", "Fitbit"],
        "subcategories": [
            ("Home Gym & Fitness", ["Adjustable Hex Dumbbells Set 10kg-20kg", "High-Density Anti-Slip Yoga Mat 6mm", "Resistance Loop Bands Exercise Set of 5", "Ab Roller Wheel with Knee Pad Mat", "Steel Skipping Jump Rope Ball Bearings"], (299, 5999), 24),
            ("Badminton & Rackets", ["Astrox 77 Play Graphite Badminton Racket", "Mavis 350 Nylon Shuttlecocks Pack of 6", "Full Carbon Fiber Lightweight Racket with Cover", "Badminton Kit Bag 3-Racket Compartment"], (349, 7499), 20),
            ("Team Sports & Balls", ["Storm Football Hand Stitched Size 5", "English Willow Full Size Cricket Bat", "High Seam Match Leather Cricket Ball Pack of 2", "Tournament Basketball Rubber Size 7"], (449, 12999), 18),
            ("Sports Accessories", ["Insulated Stainless Steel Gym Shaker 750ml", "Weight Lifting Wrist Support Straps Pair", "Breathable Sports Arm Sleeve UV Protection", "Compression Ankle Support Brace"], (199, 1499), 14),
        ],
        "image": "https://images.unsplash.com/photo-1517838277536-f5f99be501cd?auto=format&fit=crop&w=500&q=80",
        "specs_template": {"Material": "High-Grade Cast Iron / High Density TPE / Carbon Fiber", "Suitability": "Beginner to Professional Athletes", "Features": "Anti-Slip, Sweat Resistant, Ergonomic Grip", "Warranty": "6 Months to 1 Year Manufacturer Warranty"}
    },
    "Food & Grocery": {
        "brands": ["Tata Sampann", "Daawat", "Fortune", "Saffola", "24 Mantra", "Kellogg's", "Nescafe", "Cadbury", "Happilo", "Dabur"],
        "subcategories": [
            ("Staples & Cooking Oils", ["Rozana Super Basmati Rice 5kg", "Cold Pressed Pure Mustard Oil 1L", "Extra Virgin Olive Oil Glass Bottle 1L", "Unpolished Toor Dal High Protein 1kg", "Chakki Fresh 100% Whole Wheat Atta 10kg"], (149, 1899), 24),
            ("Breakfast & Cereals", ["Corn Flakes Real Honey & Almonds 1kg", "Instant Rolled Oats High Fiber 1kg", "Natural Muesli Fruit & Nut 750g", "Peanut Butter Crunchy 100% Roasted 1kg"], (199, 749), 20),
            ("Dry Fruits & Healthy Snacks", ["California Raw Almonds Value Pack 500g", "Premium W240 Jumbo Cashews 500g", "Seedless Black Raisins 500g", "Roasted Salted Pistachios 250g", "Dark Chocolate 70% Cocoa 150g"], (249, 1299), 20),
            ("Beverages & Tea", ["Gold Instant Rich Aroma Coffee 100g", "Premium CTC Leaf Tea Box 1kg", "Pure Himalayan Green Tea 100 Bags", "100% Pure Organic Raw Honey 500g"], (180, 899), 16),
        ],
        "image": "https://images.unsplash.com/photo-1542838132-92c53300491e?auto=format&fit=crop&w=500&q=80",
        "specs_template": {"Dietary Preference": "100% Vegetarian / Gluten-Free / Organic Certified", "Net Quantity": "500g / 1kg / 5kg", "Shelf Life": "12 Months from Packaging", "FSSAI License": "10014047000001 (Certified Food Safety)"}
    },
    "Furniture": {
        "brands": ["IKEA", "Nilkamal", "Sleepwell", "Wakefit", "Godrej Interio", "Green Soul", "Urban Ladder", "Pepperfry", "Wipro", "Durian"],
        "subcategories": [
            ("Chairs & Desks", ["Ergonomic High-Back Mesh Office Chair with Lumbar Support", "Height Adjustable Electric Standing Desk 120x60cm", "Engineered Wood Study Table with Bookshelf", "Gaming Chair with 3D Armrests and Footrest", "Mid-Century Modern Dining Chairs Set of 2"], (2499, 29999), 22),
            ("Living Room Seating", ["L-Shape 6-Seater Sectional Fabric Sofa", "3-Seater Velvet Tufted Sofa Bed", "Solid Sheesham Wood Coffee Table", "Recliner Single Seater Ultra Padded Brown", "Accent Wingback Armchair with Wooden Legs"], (4999, 44999), 18),
            ("Beds & Mattresses", ["Orthopedic Memory Foam Queen Size Mattress 78x60x6", "Solid Teak Wood Queen Size Bed with Hydraulic Storage", "Bunk Bed with Sturdy Metal Ladder for Kids", "Pocket Spring Dual Comfort King Mattress"], (6499, 49999), 16),
            ("Storage & Wardrobes", ["4-Door Engineered Wood Wardrobe with Mirror", "5-Tier Open Bookshelf Display Rack Industrial Style", "Shoe Cabinet with Bench Seating Cushion", "TV Entertainment Unit Wall Mounted Console"], (1999, 24999), 16),
        ],
        "image": "https://images.unsplash.com/photo-1555041469-a586c61ea9bc?auto=format&fit=crop&w=500&q=80",
        "specs_template": {"Material": "Solid Sheesham Wood / High-Density Foam / Powder-Coated Metal", "Dimensions": "Standard Ergonomic Measurements", "Assembly": "Carpenter Assembly Provided / DIY with Guide", "Warranty": "3 Years Comprehensive Warranty"}
    }
}


def generate_large_catalog() -> List[Dict[str, Any]]:
    """
    Generate 2,100+ realistic, unique e-commerce product records
    covering all 13 major categories with clean metadata.
    """
    generated_products = []
    item_counter = 100

    for cat_name, cat_info in CATEGORIES_DATA.items():
        brands = cat_info["brands"]
        subcats = cat_info["subcategories"]
        default_img = cat_info["image"]
        specs_base = cat_info["specs_template"]

        for subcat_name, models, price_range, base_target in subcats:
            min_p, max_p = price_range
            target_count = base_target * 3  # Generates ~2,500+ diverse products across 13 categories
            price_step = (max_p - min_p) / max(target_count, 1)

            for i in range(target_count):
                item_counter += 1
                brand = brands[i % len(brands)]
                model_base = models[i % len(models)]
                color_variants = ["Midnight Black", "Starlight Silver", "Deep Blue", "Emerald Green", "Rose Gold", "Titanium Grey", "Obsidian", "Pure White"]
                color = color_variants[i % len(color_variants)]
                edition = f"Edition {chr(65 + (i % 8))}" if i >= len(models) else ""
                
                # Product title
                if edition:
                    name = f"{brand} {model_base} ({edition}, {color})"
                else:
                    name = f"{brand} {model_base} ({color})"

                # Calculate realistic price
                price = round(min_p + (i * price_step) + ((i * 17) % 50), 2)
                discount = 10 + ((i * 7) % 45)  # 10% to 55%
                mrp = round(price / (1 - discount / 100.0), 2)
                rating = round(3.8 + ((i * 13) % 12) / 10.0, 1)  # 3.8 to 4.9
                review_count = 120 + ((i * 243) % 9800)
                stock = 15 + ((i * 37) % 200)

                # Unique SKU/source ID
                cat_code = cat_name[:3].upper()
                source_id = f"PT-{cat_code}-{item_counter}"
                external_url = f"https://www.flipkart.com/search?q={name.replace(' ', '+')}"

                # Specifications customization
                specs = dict(specs_base)
                specs["Brand"] = brand
                specs["Model Name"] = model_base
                specs["Category"] = cat_name
                specs["Subcategory"] = subcat_name

                description = (
                    f"Authentic {brand} {model_base} offering premier performance, exceptional durability, "
                    f"and verified quality in the {cat_name} category. Designed for everyday lifestyle comfort."
                )

                generated_products.append({
                    "source_id": source_id,
                    "name": name,
                    "category": cat_name,
                    "subcategory": subcat_name,
                    "brand": brand,
                    "price": price,
                    "discount_percentage": discount,
                    "mrp": mrp,
                    "description": description,
                    "specifications": specs,
                    "image_url": default_img,
                    "source_type": "pretwin_catalog",
                    "data_origin": "catalog",
                    "availability": "in_stock" if stock > 20 else "limited_stock",
                    "rating": rating,
                    "review_count_demo": review_count,
                    "stock": stock,
                    "featured": 1 if i % 15 == 0 else 0,
                    "external_url": external_url,
                })

    return generated_products


if __name__ == "__main__":
    products = generate_large_catalog()
    print(f"Total products generated: {len(products)}")
    from collections import Counter
    cats = Counter(p["category"] for p in products)
    for c, cnt in cats.items():
        print(f"  - {c}: {cnt} items")
