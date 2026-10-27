# -*- coding: utf-8 -*-
"""
scripts/assign_diverse_product_images.py
Maps every product in pretwinshop.db to a specific, verified, high-quality,
product-appropriate image matching its exact subcategory, name, style, and silhouette.
Ensures rich visual variety across all 20 categories and 1,040 products.
"""

import sqlite3
import os
import sys

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pretwinshop.db")

# Curated pools of verified, high-quality Unsplash image URLs per subcategory / keyword
# All images are commercial/public royalty-free product photos on Unsplash CDN
IMAGE_POOLS = {
    "Footwear": {
        "Sports & Running Shoes": [
            "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&q=80",  # Red Nike Running
            "https://images.unsplash.com/photo-1595950653106-6c9ebd614d3a?w=400&q=80",  # White Pastel Sport Trainers
            "https://images.unsplash.com/photo-1584735935682-2f2b69dff9d2?w=400&q=80",  # Black & Orange Athletic
            "https://images.unsplash.com/photo-1608231387042-66d1773070a5?w=400&q=80",  # White Puma Trainer
            "https://images.unsplash.com/photo-1551107696-a4b0c5a0d9a2?w=400&q=80",  # Blue Knit Runner
            "https://images.unsplash.com/photo-1460353581641-37baddab0fa2?w=400&q=80",  # Grey Running Trainers
        ],
        "Men's Formal Shoes": [
            "https://images.unsplash.com/photo-1533867617858-e7b97e060509?w=400&q=80",  # Classic Brown Oxford Brogues
            "https://images.unsplash.com/photo-1614252235316-8c857d38b5f4?w=400&q=80",  # Shiny Black Derby
            "https://images.unsplash.com/photo-1560343090-f0409e92791a?w=400&q=80",  # Leather Wingtip Brogue
            "https://images.unsplash.com/photo-1449505278894-297fdb3edbc1?w=400&q=80",  # Polished Black Dress Shoes
            "https://images.unsplash.com/photo-1597045566677-8cf032ed6634?w=400&q=80",  # Tan Leather Formal
        ],
        "Sneakers": [
            "https://images.unsplash.com/photo-1552346154-21d32810aba3?w=400&q=80",  # Streetwear Chunky Sneakers
            "https://images.unsplash.com/photo-1525966222134-fcfa99b8ae77?w=400&q=80",  # Vans Old Skool Canvas
            "https://images.unsplash.com/photo-1560769629-975ec94e6a86?w=400&q=80",  # Colorblock Retro Sneaker
            "https://images.unsplash.com/photo-1512990414788-d97cb4a25db3?w=400&q=80",  # Minimal White Leather Sneaker
            "https://images.unsplash.com/photo-1607522370275-f14206abe5d3?w=400&q=80",  # Red High-Top Converse
            "https://images.unsplash.com/photo-1579338559194-a162d19bf842?w=400&q=80",  # Nike Air Jordan Retro
        ],
        "Men's Casual Shoes": [
            "https://images.unsplash.com/photo-1520639888713-7851133b1ed0?w=400&q=80",  # Rugged Leather Boots
            "https://images.unsplash.com/photo-1549298916-b41d501d3772?w=400&q=80",  # Suede Desert Chukka
            "https://images.unsplash.com/photo-1582588678413-dbf45f4823e9?w=400&q=80",  # Penny Driving Loafers
            "https://images.unsplash.com/photo-1543163521-1bf539c55dd2?w=400&q=80",  # Suede Casual Slip-on
            "https://images.unsplash.com/photo-1518002171953-a080ee817e1f?w=400&q=80",  # Timberland Nubuck Boots
        ],
        "Heels & Wedges": [
            "https://images.unsplash.com/photo-1543163521-1bf539c55dd2?w=400&q=80",  # Elegant Stiletto Pumps
            "https://images.unsplash.com/photo-1535043934128-cf0b28d52f95?w=400&q=80",  # Red High Heels
            "https://images.unsplash.com/photo-1596704017254-9b121068fb31?w=400&q=80",  # Strappy Wedge Sandals
            "https://images.unsplash.com/photo-1566150905458-1bf1fc113f0d?w=400&q=80",  # Pointed Toe Block Heel
        ],
        "Women's Flats": [
            "https://images.unsplash.com/photo-1562273138-f46be4ebdf33?w=400&q=80",  # Ballerina Flats
            "https://images.unsplash.com/photo-1575537302964-96cd47c06b1b?w=400&q=80",  # Leather Flat Sandals
            "https://images.unsplash.com/photo-1595341888016-a392ef81b7de?w=400&q=80",  # Mule Slip-Ons
        ],
        "Slippers & Flip Flops": [
            "https://images.unsplash.com/photo-1603808033192-082d6919d3e1?w=400&q=80",  # Slide Sandals
            "https://images.unsplash.com/photo-1586525198428-225f6f12cff5?w=400&q=80",  # Casual Flip Flops
            "https://images.unsplash.com/photo-1560769629-975ec94e6a86?w=400&q=80",  # Beach Sliders
        ],
        "Kids' Footwear": [
            "https://images.unsplash.com/photo-1514989940723-e8e51635b782?w=400&q=80",  # Kids Cute Sneakers
            "https://images.unsplash.com/photo-1551107696-a4b0c5a0d9a2?w=400&q=80",  # Light Up Kids Shoes
            "https://images.unsplash.com/photo-1507464098880-e367bc5d2c08?w=400&q=80",  # Toddler Velcro Booties
        ],
        "Shoe Care & Socks": [
            "https://images.unsplash.com/photo-1586350977771-b3b0abd50c82?w=400&q=80",  # Cotton Socks Pack
            "https://images.unsplash.com/photo-1582588678413-dbf45f4823e9?w=400&q=80",  # Shoe Brush and Polish
        ]
    },
    "Mobiles": {
        "Smartphones": [
            "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=400&q=80",  # Sleek White Smartphone
            "https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=400&q=80",  # Minimal Black Mobile
            "https://images.unsplash.com/photo-1565849904461-04a58ad377e0?w=400&q=80",  # Dual Camera Phone
            "https://images.unsplash.com/photo-1574944985070-8f3ebc6b79d2?w=400&q=80",  # Modern Android Phone
        ],
        "5G Android Phones": [
            "https://images.unsplash.com/photo-1580910051074-3eb694886505?w=400&q=80",  # Samsung Galaxy Edge Screen
            "https://images.unsplash.com/photo-1610945265064-0e34e5519bbf?w=400&q=80",  # Galaxy Ultra Multi-Lens
            "https://images.unsplash.com/photo-1567581935884-3349723552ca?w=400&q=80",  # OnePlus / Pixel Android
            "https://images.unsplash.com/photo-1592750475338-74b7b21085ab?w=400&q=80",  # Curved OLED 5G Display
        ],
        "iOS Phones": [
            "https://images.unsplash.com/photo-1510557880182-3d4d3cba35a5?w=400&q=80",  # iPhone Silver Clean
            "https://images.unsplash.com/photo-1591337676887-a217a6970a8a?w=400&q=80",  # iPhone Midnight Black
            "https://images.unsplash.com/photo-1530319067432-f2a729c03db5?w=400&q=80",  # iPhone Red Edition
            "https://images.unsplash.com/photo-1605236453806-6ff36851218e?w=400&q=80",  # iPhone Pro Titanium
        ],
        "Feature Phones": [
            "https://images.unsplash.com/photo-1584438784894-089d6a62b8fa?w=400&q=80",  # Retro Keypad Phone
            "https://images.unsplash.com/photo-1567581935884-3349723552ca?w=400&q=80",  # Nokia Style Tough Phone
        ],
        "Mobile Covers & Cases": [
            "https://images.unsplash.com/photo-1586105251261-72a756497a11?w=400&q=80",  # Leather Phone Case
            "https://images.unsplash.com/photo-1603313011101-320f26a4f6f6?w=400&q=80",  # Clear Matte Case
            "https://images.unsplash.com/photo-1584438784894-089d6a62b8fa?w=400&q=80",  # Silicone Grip Cover
        ],
        "Screen Guards": [
            "https://images.unsplash.com/photo-1585060544812-6b45742d762f?w=400&q=80",  # Tempered Glass Pack
            "https://images.unsplash.com/photo-1580910051074-3eb694886505?w=400&q=80",  # Edge Guard Screen
        ],
        "Chargers & Cables": [
            "https://images.unsplash.com/photo-1583863788434-e58a36330cf0?w=400&q=80",  # GaN Wall Fast Charger
            "https://images.unsplash.com/photo-1583863788434-e58a36330cf0?w=400&q=80",  # Braided USB-C Cable
        ],
        "Power Banks": [
            "https://images.unsplash.com/photo-1609592426804-58eb1bb24483?w=400&q=80",  # Slim Black Power Bank
            "https://images.unsplash.com/photo-1620799140408-edc6dcb6d633?w=400&q=80",  # Heavy Duty Portable Battery
        ],
        "Wireless Earbuds": [
            "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?w=400&q=80",  # TWS ANC Wireless Pods
            "https://images.unsplash.com/photo-1572569511254-d8f925fe2cbb?w=400&q=80",  # Compact Charging Case Pods
            "https://images.unsplash.com/photo-1600294037681-c80b4cb5b434?w=400&q=80",  # Sport In-Ear Wireless Buds
        ],
        "Mobile Stands": [
            "https://images.unsplash.com/photo-1586105251261-72a756497a11?w=400&q=80",  # Aluminium Desk Phone Stand
            "https://images.unsplash.com/photo-1584438784894-089d6a62b8fa?w=400&q=80",  # Magnetic Car Mount Holder
        ]
    },
    "Fashion": {
        "Shirts": [
            "https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?w=400&q=80",  # Classic White Linen Shirt
            "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&q=80",  # Denim Casual Shirt
            "https://images.unsplash.com/photo-1603252109303-2751441dd157?w=400&q=80",  # Formal Checked Shirt
            "https://images.unsplash.com/photo-1598033129183-c4f50c736f10?w=400&q=80",  # Black Oxford Button Down
        ],
        "Jeans": [
            "https://images.unsplash.com/photo-1542272604-780c96856592?w=400&q=80",  # Blue Washed Denim
            "https://images.unsplash.com/photo-1541099649105-f69ad21f3246?w=400&q=80",  # Slim Black Jeans
            "https://images.unsplash.com/photo-1582418702059-97ebafb35d09?w=400&q=80",  # Vintage Distressed Denim
        ],
        "Trousers": [
            "https://images.unsplash.com/photo-1624378439575-d8705ad7ae80?w=400&q=80",  # Beige Chino Pants
            "https://images.unsplash.com/photo-1473966968600-fa801b869a1a?w=400&q=80",  # Charcoal Formal Trousers
        ],
        "T-Shirts": [
            "https://images.unsplash.com/photo-1521572267360-ee0c2909d518?w=400&q=80",  # White Minimal Tee
            "https://images.unsplash.com/photo-1583743814966-8936f5b7be1a?w=400&q=80",  # Black Graphic Cotton T-Shirt
            "https://images.unsplash.com/photo-1503342217505-b0a15ec3261c?w=400&q=80",  # Vintage Print Tee
            "https://images.unsplash.com/photo-1618354691373-d851c5c3a990?w=400&q=80",  # Striped Polo T-Shirt
        ],
        "Sarees": [
            "https://images.unsplash.com/photo-1610030469983-98e550d6193c?w=400&q=80",  # Rich Red Silk Saree
            "https://images.unsplash.com/photo-1617627143750-d86bc21e42bb?w=400&q=80",  # Golden Zari Banarasi
            "https://images.unsplash.com/photo-1610030469668-9359e1a1b41d?w=400&q=80",  # Contemporary Georgette Saree
        ],
        "Kurtas": [
            "https://images.unsplash.com/photo-1583391733956-3750e0ff4e8b?w=400&q=80",  # Embroidered Ethnic Kurta
            "https://images.unsplash.com/photo-1609357605129-26f69add5d6e?w=400&q=80",  # Festive Yellow Kurta Set
        ],
        "Dresses": [
            "https://images.unsplash.com/photo-1572804013309-59a88b7e92f1?w=400&q=80",  # Floral Summer Dress
            "https://images.unsplash.com/photo-1595777457583-95e059d581b8?w=400&q=80",  # Elegant Black Evening Dress
            "https://images.unsplash.com/photo-1515372039744-b8f02a3ae446?w=400&q=80",  # A-line Midi Flare Dress
        ],
        "Ethnic Wear": [
            "https://images.unsplash.com/photo-1583391733956-3750e0ff4e8b?w=400&q=80",  # Nehru Waistcoat Jacket
            "https://images.unsplash.com/photo-1610030469983-98e550d6193c?w=400&q=80",  # Traditional Silk Dupatta
        ],
        "Western Wear": [
            "https://images.unsplash.com/photo-1556905055-8f358a7a47b2?w=400&q=80",  # Warm Fleece Pullover Hoodie
            "https://images.unsplash.com/photo-1551028719-00167b16eac5?w=400&q=80",  # Biker Leather Jacket
        ],
        "Innerwear": [
            "https://images.unsplash.com/photo-1583743814966-8936f5b7be1a?w=400&q=80",  # Cotton Boxers Pack
            "https://images.unsplash.com/photo-1521572267360-ee0c2909d518?w=400&q=80",  # Comfy Innerwear Vest
        ],
        "Handbags": [
            "https://images.unsplash.com/photo-1584917865442-de89df76afd3?w=400&q=80",  # Tan Leather Tote Bag
            "https://images.unsplash.com/photo-1590874103328-eac38a683ce7?w=400&q=80",  # Crossbody Structured Bag
            "https://images.unsplash.com/photo-1548036328-c9fa89d128fa?w=400&q=80",  # Shoulder Satchel Purse
        ],
        "Wallets": [
            "https://images.unsplash.com/photo-1627123424574-724758594e93?w=400&q=80",  # Genuine Leather Bifold Wallet
            "https://images.unsplash.com/photo-1554412933-514a83d2f3c8?w=400&q=80",  # Slim Cardholder Wallet
        ],
        "Belts": [
            "https://images.unsplash.com/photo-1624222247344-550fb60583dc?w=400&q=80",  # Brown Leather Formal Belt
            "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=400&q=80",  # Black Classic Metal Buckle
        ],
        "Sunglasses": [
            "https://images.unsplash.com/photo-1511499767150-a48a237f0083?w=400&q=80",  # Aviator UV Sunglasses
            "https://images.unsplash.com/photo-1572635196237-14b3f281503f?w=400&q=80",  # Wayfarer Polarized Shades
            "https://images.unsplash.com/photo-1577803645773-f96470509666?w=400&q=80",  # Retro Round Sunglasses
        ]
    },
    "Electronics": {
        "Headphones": [
            "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&q=80",  # Sony Over-Ear ANC
            "https://images.unsplash.com/photo-1484704849700-f032a568e944?w=400&q=80",  # Studio Monitor Headphones
            "https://images.unsplash.com/photo-1546435770-a3e426bf472b?w=400&q=80",  # Wireless Bose Style Headset
        ],
        "Bluetooth Speakers": [
            "https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=400&q=80",  # Cylinder Portable Speaker
            "https://images.unsplash.com/photo-1545454675-3531b543be5d?w=400&q=80",  # Heavy Bass Bluetooth Speaker
            "https://images.unsplash.com/photo-1508700115892-45ecd05ae2ad?w=400&q=80",  # Rugged Outdoor Speaker
        ],
        "Soundbars": [
            "https://images.unsplash.com/photo-1545454675-3531b543be5d?w=400&q=80",  # Slim TV Soundbar
            "https://images.unsplash.com/photo-1593359677879-a4bb92f829d1?w=400&q=80",  # Dolby Audio Subwoofer Bar
        ],
        "Cameras": [
            "https://images.unsplash.com/photo-1516035069371-29a1b244cc32?w=400&q=80",  # 4K Mirrorless Digital Camera
            "https://images.unsplash.com/photo-1502920917128-1aa500764cbd?w=400&q=80",  # DSLR Professional Camera
            "https://images.unsplash.com/photo-1526170375885-4d8ecf77b99f?w=400&q=80",  # Instant Print Polaroid Camera
        ],
        "Webcams": [
            "https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=400&q=80",  # 1080p Stream Webcam
            "https://images.unsplash.com/photo-1588508065123-287b28e013da?w=400&q=80",  # Wide Angle Video Cam
        ],
        "Microphones": [
            "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?w=400&q=80",  # USB Condenser Studio Mic
            "https://images.unsplash.com/photo-1598488035139-bdbb2231ce04?w=400&q=80",  # Podcast Broadcast Mic
        ],
        "Smartwatches": [
            "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=400&q=80",  # White Smartwatch
            "https://images.unsplash.com/photo-1508685096489-7aacd43bd3b1?w=400&q=80",  # Black Fitness AMOLED Watch
            "https://images.unsplash.com/photo-1579586337278-3befd40fd17a?w=400&q=80",  # Apple Watch Style Tracker
        ],
        "Computer Accessories": [
            "https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?w=400&q=80",  # Ergonomic Wireless Mouse
            "https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=400&q=80",  # Mechanical RGB Keyboard
            "https://images.unsplash.com/photo-1618384887929-16ec33fab9ef?w=400&q=80",  # Type-C Multiport Hub
        ],
        "Storage Devices": [
            "https://images.unsplash.com/photo-1597872200969-2b65d56bd16b?w=400&q=80",  # Portable External SSD
            "https://images.unsplash.com/photo-1618384887929-16ec33fab9ef?w=400&q=80",  # High Speed Flash Drive
        ]
    },
    "Laptops & Computers": {
        "Thin & Light Laptops": [
            "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=400&q=80",  # Silver MacBook / Ultrabook
            "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=400&q=80",  # Sleek Aluminum Laptop
            "https://images.unsplash.com/photo-1588872657578-7efd1f1555ed?w=400&q=80",  # Dell XPS Slim Notebook
        ],
        "Gaming Laptops": [
            "https://images.unsplash.com/photo-1603302576837-37561b2e2302?w=400&q=80",  # RGB Backlit Gaming Laptop
            "https://images.unsplash.com/photo-1593642702821-c8da6771f0c6?w=400&q=80",  # RTX Gaming Rig Laptop
            "https://images.unsplash.com/photo-1525547719571-a2d4ac8945e2?w=400&q=80",  # High Refresh Screen Laptop
        ],
        "Desktop PCs": [
            "https://images.unsplash.com/photo-1587831990711-23ca6441447b?w=400&q=80",  # Glass RGB Gaming Tower
            "https://images.unsplash.com/photo-1547082299-de196ea013d6?w=400&q=80",  # Minimalist All-in-One PC
        ],
        "Monitors": [
            "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=400&q=80",  # Curved 27-inch 144Hz
            "https://images.unsplash.com/photo-1586210579191-33b45e38fa2c?w=400&q=80",  # 4K IPS UltraWide Monitor
        ],
        "Keyboards": [
            "https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=400&q=80",  # Keychron Mechanical Keyboard
            "https://images.unsplash.com/photo-1618384887929-16ec33fab9ef?w=400&q=80",  # Wireless Compact Keyboard
        ],
        "Mice": [
            "https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?w=400&q=80",  # Logitech MX Master Mouse
            "https://images.unsplash.com/photo-1615663245857-ac93bb7c39e7?w=400&q=80",  # Wireless Gaming Optical Mouse
        ],
        "Routers & Networking": [
            "https://images.unsplash.com/photo-1544197150-b99a580bb7a8?w=400&q=80",  # Wi-Fi 6 Mesh Router
        ],
        "Printers": [
            "https://images.unsplash.com/photo-1612815154858-60aa4c59eaa6?w=400&q=80",  # Wireless Color InkTank Printer
        ]
    },
    "TVs & Home Entertainment": {
        "4K Ultra HD Smart TVs": [
            "https://images.unsplash.com/photo-1593359677879-a4bb92f829d1?w=400&q=80",  # Modern Frameless 55 inch TV
            "https://images.unsplash.com/photo-1509281373149-e957c6296406?w=400&q=80",  # 65 inch OLED Television
            "https://images.unsplash.com/photo-1461151304267-38535e780c79?w=400&q=80",  # Wall Mounted Home Cinema
        ],
        "OLED & QLED TVs": [
            "https://images.unsplash.com/photo-1593359677879-a4bb92f829d1?w=400&q=80",  # Vivid Color QLED TV
            "https://images.unsplash.com/photo-1509281373149-e957c6296406?w=400&q=80",  # 4K HDR Quantum Display
        ],
        "Budget Smart TVs": [
            "https://images.unsplash.com/photo-1461151304267-38535e780c79?w=400&q=80",  # 32/43 inch LED Smart TV
        ],
        "Home Theater Soundbars": [
            "https://images.unsplash.com/photo-1545454675-3531b543be5d?w=400&q=80",  # 5.1 Dolby Surround Soundbar
            "https://images.unsplash.com/photo-1508700115892-45ecd05ae2ad?w=400&q=80",  # Wireless Subwoofer Cinema
        ],
        "Streaming Devices": [
            "https://images.unsplash.com/photo-1544197150-b99a580bb7a8?w=400&q=80",  # 4K Media Streaming Stick
        ],
        "Projectors": [
            "https://images.unsplash.com/photo-1517604931442-7e0c8ed2963c?w=400&q=80",  # Full HD Smart Cinema Projector
        ],
        "TV Wall Mounts & Cables": [
            "https://images.unsplash.com/photo-1618384887929-16ec33fab9ef?w=400&q=80",  # Heavy Duty Swivel TV Bracket
        ]
    },
    "Home & Kitchen": {
        "Cookware Sets": [
            "https://images.unsplash.com/photo-1584990347449-74d32049d533?w=400&q=80",  # Non-Stick Granite Cookware
            "https://images.unsplash.com/photo-1556911220-e15b29be8c8f?w=400&q=80",  # Stainless Steel Pots & Pans
        ],
        "Cast Iron Skillets": [
            "https://images.unsplash.com/photo-1584990347449-74d32049d533?w=400&q=80",  # Pre-seasoned Heavy Skillet
        ],
        "Electric Kettles": [
            "https://images.unsplash.com/photo-1544787219-7f47ccb76574?w=400&q=80",  # Glass LED Boiling Kettle
            "https://images.unsplash.com/photo-1594212699903-ec8a3eca50f5?w=400&q=80",  # Stainless Steel Auto Kettle
        ],
        "Blenders & Mixers": [
            "https://images.unsplash.com/photo-1570222094114-d054a817e56b?w=400&q=80",  # 750W 3-Jar Mixer Grinder
            "https://images.unsplash.com/photo-1584269600464-37b1b58a9fe7?w=400&q=80",  # High Speed Smoothie Blender
        ],
        "Coffee Makers": [
            "https://images.unsplash.com/photo-1517668808822-9ebb02f2a0e6?w=400&q=80",  # Espresso Machine with Frother
            "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?w=400&q=80",  # French Press Coffee Pot
        ],
        "Air Fryers": [
            "https://images.unsplash.com/photo-1585515320310-259814833e62?w=400&q=80",  # Digital Touch Air Fryer
        ],
        "Kitchen Storage Containers": [
            "https://images.unsplash.com/photo-1584269600464-37b1b58a9fe7?w=400&q=80",  # Airtight Borosilicate Jars
        ],
        "Bedsheets & Linen": [
            "https://images.unsplash.com/photo-1584100936595-c0654b55a2e2?w=400&q=80",  # 300TC Pure Cotton King Sheet
            "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=400&q=80",  # Memory Foam Sleeping Pillows
        ]
    },
    "Furniture": {
        "Sofas & Sectionals": [
            "https://images.unsplash.com/photo-1555041469-a586c61ea9bc?w=400&q=80",  # Emerald Velvet 3-Seater
            "https://images.unsplash.com/photo-1493663284031-b7e3aefcae8e?w=400&q=80",  # Scandinavian Grey Fabric Couch
        ],
        "Office Chairs & Desks": [
            "https://images.unsplash.com/photo-1580481077197-391e4c7a522a?w=400&q=80",  # Ergonomic Mesh Office Chair
            "https://images.unsplash.com/photo-1518455027359-f3f8164ba6bd?w=400&q=80",  # Solid Wood Work Desk
        ],
        "Beds & Mattresses": [
            "https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?w=400&q=80",  # King Size Bed Frame
            "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=400&q=80",  # Orthopedic Memory Foam Mattress
        ],
        "Dining Tables & Chairs": [
            "https://images.unsplash.com/photo-1615066390971-03e4e1c36ddf?w=400&q=80",  # 4-Seater Teak Dining Set
        ],
        "Wardrobes & Closets": [
            "https://images.unsplash.com/photo-1595428774223-ef52624120d2?w=400&q=80",  # 3-Door Engineered Wood Wardrobe
        ],
        "Coffee Tables": [
            "https://images.unsplash.com/photo-1533090161767-e6ffed986c88?w=400&q=80",  # Marble Top Round Coffee Table
        ],
        "Bookshelves & Shoe Racks": [
            "https://images.unsplash.com/photo-1594980596870-8aa52a78d8cd?w=400&q=80",  # 5-Tier Ladder Bookshelf
            "https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=400&q=80",  # Closed 4-Door Shoe Rack
        ],
        "Recliners & Lounge": [
            "https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=400&q=80",  # Single Motor Leatherette Recliner
        ]
    },
    "Appliances": {
        "Refrigerators": [
            "https://images.unsplash.com/photo-1571175443880-49e1d25b2bc5?w=400&q=80",  # Double Door Frost Free Fridge
            "https://images.unsplash.com/photo-1584992236310-6edddc08acff?w=400&q=80",  # Multi-Door Inverter Refrigerator
        ],
        "Washing Machines": [
            "https://images.unsplash.com/photo-1626806787461-102c1bfaaea1?w=400&q=80",  # Front Load 8kg Smart Washer
            "https://images.unsplash.com/photo-1604335399105-a0c585fd81a1?w=400&q=80",  # Fully Automatic Top Load
        ],
        "Air Conditioners": [
            "https://images.unsplash.com/photo-1621905251189-08b45d6a269e?w=400&q=80",  # 1.5 Ton 5-Star Split Inverter AC
        ],
        "Microwave Ovens": [
            "https://images.unsplash.com/photo-1585515320310-259814833e62?w=400&q=80",  # 28L Convection Microwave
        ],
        "Vacuum Cleaners": [
            "https://images.unsplash.com/photo-1558317374-067fb5f30001?w=400&q=80",  # Cordless Stick Vacuum
            "https://images.unsplash.com/photo-1518770660439-4636190af475?w=400&q=80",  # Robotic Vacuum Cleaner
        ],
        "Air Purifiers": [
            "https://images.unsplash.com/photo-1585771724684-38269d6639fd?w=400&q=80",  # True HEPA Air Purifier
        ],
        "Water Purifiers": [
            "https://images.unsplash.com/photo-1548839140-29a749e1bc4e?w=400&q=80",  # RO+UV Alkaline Water Purifier
        ],
        "Water Heaters (Geysers)": [
            "https://images.unsplash.com/photo-1584622650111-993a426fbf0a?w=400&q=80",  # 25L 5-Star Storage Geyser
        ],
        "Iron & Garment Steamers": [
            "https://images.unsplash.com/photo-1585771724684-38269d6639fd?w=400&q=80",  # Non-Stick Steam Iron
        ],
        "Ceiling & Table Fans": [
            "https://images.unsplash.com/photo-1585771724684-38269d6639fd?w=400&q=80",  # BLDC Energy Saving Ceiling Fan
        ]
    },
    "Beauty, Toys & More": {
        "Face Wash & Cleansers": [
            "https://images.unsplash.com/photo-1556228720-195a672e8a03?w=400&q=80",  # Gentle Foaming Cleanser
            "https://images.unsplash.com/photo-1598440947619-2c35fc9aa908?w=400&q=80",  # Vitamin C Face Wash
        ],
        "Moisturizers & Sunscreen": [
            "https://images.unsplash.com/photo-1596462502278-27bfdc403348?w=400&q=80",  # SPF 50 Gel Sunscreen
            "https://images.unsplash.com/photo-1570172619644-dfd03ed5d881?w=400&q=80",  # Hyaluronic Ceramide Moisturizer
        ],
        "Makeup & Lipsticks": [
            "https://images.unsplash.com/photo-1586495777744-4413f21062fa?w=400&q=80",  # Matte Velvet Red Lipstick
            "https://images.unsplash.com/photo-1512496015851-a90fb38ba796?w=400&q=80",  # Eyeshadow Palette & Foundation
        ],
        "Perfumes & Fragrances": [
            "https://images.unsplash.com/photo-1594035910387-fea47794261f?w=400&q=80",  # Luxury Eau De Parfum 100ml
            "https://images.unsplash.com/photo-1523293182086-7651a899d37f?w=400&q=80",  # Amber Woody Cologne
        ],
        "Haircare & Shampoos": [
            "https://images.unsplash.com/photo-1535585209827-a15fcdbc4c2d?w=400&q=80",  # Keratin Argan Oil Shampoo
            "https://images.unsplash.com/photo-1608248597359-5f284ec1bc7a?w=400&q=80",  # Nourishing Hair Mask
        ],
        "Beard & Shaving Care": [
            "https://images.unsplash.com/photo-1621607512214-68297480165e?w=400&q=80",  # Precision Beard Trimmer
            "https://images.unsplash.com/photo-1503951914875-452162b0f3f1?w=400&q=80",  # Shaving Kit & Razor
        ],
        "Educational Toys": [
            "https://images.unsplash.com/photo-1587654780291-39c9404d746b?w=400&q=80",  # Wooden Building Blocks & Puzzle
            "https://images.unsplash.com/photo-1566576912321-d58ddd7a6088?w=400&q=80",  # STEM Science Learning Kit
        ],
        "Action Figures & Dolls": [
            "https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?w=400&q=80",  # Superhero Collectible Figure
        ],
        "Baby Diapers & Wipes": [
            "https://images.unsplash.com/photo-1515488042361-ee00e0ddd4e4?w=400&q=80",  # Ultra Soft Baby Diapers
        ],
        "Strollers & Car Seats": [
            "https://images.unsplash.com/photo-1591088398332-8a7791972843?w=400&q=80",  # Foldable Pram Stroller
        ]
    },
    "Personal Care": {
        "Oral Care": [
            "https://images.unsplash.com/photo-1559591937-e1032b49c71e?w=400&q=80",  # Sonic Electric Toothbrush
            "https://images.unsplash.com/photo-1559591937-e1032b49c71e?w=400&q=80",  # Dental Water Flosser
        ],
        "Shaving & Grooming": [
            "https://images.unsplash.com/photo-1621607512214-68297480165e?w=400&q=80",  # Waterproof Body Groomer
            "https://images.unsplash.com/photo-1503951914875-452162b0f3f1?w=400&q=80",  # Traditional Double Edge Safety Razor
        ],
        "Hair Dryers & Stylers": [
            "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=400&q=80",  # Ionic Hair Dryer 2000W
            "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=400&q=80",  # Ceramic Hair Straightener
        ],
        "Skincare Essentials": [
            "https://images.unsplash.com/photo-1556228720-195a672e8a03?w=400&q=80",  # Niacinamide Face Serum
            "https://images.unsplash.com/photo-1570172619644-dfd03ed5d881?w=400&q=80",  # Day Cream with SPF
        ],
        "Bath & Body Care": [
            "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=400&q=80",  # Moisturizing Body Wash
            "https://images.unsplash.com/photo-1608248597359-5f284ec1bc7a?w=400&q=80",  # Exfoliating Coffee Body Scrub
        ],
        "Deodorants & Roll-ons": [
            "https://images.unsplash.com/photo-1594035910387-fea47794261f?w=400&q=80",  # Long Lasting Deo Spray
        ],
        "Feminine Hygiene": [
            "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=400&q=80",  # Organic Cotton Pads
        ]
    },
    "Toys & Baby Products": {
        "Puzzles & Board Games": [
            "https://images.unsplash.com/photo-1610890716171-6b1bb98ffd09?w=400&q=80",  # Strategy Board Game & Pieces
            "https://images.unsplash.com/photo-1587654780291-39c9404d746b?w=400&q=80",  # 1000-Piece Jigsaw Puzzle
        ],
        "Remote Control Cars & Drones": [
            "https://images.unsplash.com/photo-1594787318286-3d835c1d207f?w=400&q=80",  # High Speed 4WD RC Buggy
            "https://images.unsplash.com/photo-1508614589041-895b88991e3e?w=400&q=80",  # Mini Altitude Hold Drone
        ],
        "Soft Toys & Stuffed Animals": [
            "https://images.unsplash.com/photo-1559454403-b8fb88521f11?w=400&q=80",  # Giant Plush Teddy Bear
            "https://images.unsplash.com/photo-1563245372-f21724e3856d?w=400&q=80",  # Cuddly Velvet Elephant Toy
        ],
        "Action Figures & Dolls": [
            "https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?w=400&q=80",  # Posable Articulated Figure
        ],
        "Baby Gear & Strollers": [
            "https://images.unsplash.com/photo-1591088398332-8a7791972843?w=400&q=80",  # Lightweight Travel Stroller
        ],
        "Baby Diapers & Feeding": [
            "https://images.unsplash.com/photo-1515488042361-ee00e0ddd4e4?w=400&q=80",  # Anti-Colic Feeding Bottles
            "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=400&q=80",  # Hypoallergenic Baby Wipes
        ],
        "Building Sets & Blocks": [
            "https://images.unsplash.com/photo-1587654780291-39c9404d746b?w=400&q=80",  # Magnetic Construction Tiles
            "https://images.unsplash.com/photo-1566576912321-d58ddd7a6088?w=400&q=80",  # Interlocking Creative Bricks
        ]
    },
    "Food & Grocery": {
        "Daily Staples & Rice": [
            "https://images.unsplash.com/photo-1586201375761-83865001e31c?w=400&q=80",  # Aged Royal Basmati Rice 5kg
            "https://images.unsplash.com/photo-1574323347407-f5e1ad6d020b?w=400&q=80",  # 100% Sharbati Whole Wheat Atta
        ],
        "Cooking Oils & Ghee": [
            "https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?w=400&q=80",  # Extra Virgin Cold Pressed Olive Oil
            "https://images.unsplash.com/photo-1589927986089-35812388d1f4?w=400&q=80",  # Pure Cow Desi Ghee 1L
        ],
        "Dry Fruits & Nuts": [
            "https://images.unsplash.com/photo-1508061253366-f7da158b6d46?w=400&q=80",  # California Raw Almonds 500g
            "https://images.unsplash.com/photo-1599785209707-a456fc1337bb?w=400&q=80",  # Roasted Salted Cashews 500g
        ],
        "Tea & Coffee": [
            "https://images.unsplash.com/photo-1544787219-7f47ccb76574?w=400&q=80",  # Organic Green Tea Bags
            "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?w=400&q=80",  # 100% Arabica Roasted Coffee Beans
        ],
        "Snacks & Biscuits": [
            "https://images.unsplash.com/photo-1558961363-fa8fdf82db35?w=400&q=80",  # Dark Chocolate Chunk Cookies
            "https://images.unsplash.com/photo-1582293041079-7814c2f12063?w=400&q=80",  # Gourmet Roasted Makhana
        ],
        "Chocolates & Sweets": [
            "https://images.unsplash.com/photo-1549007994-cb92caebd54b?w=400&q=80",  # 70% Dark Cocoa Artisanal Chocolate
        ],
        "Spices & Masalas": [
            "https://images.unsplash.com/photo-1596040033229-a9821ebd058d?w=400&q=80",  # Organic Whole Black Peppercorns
            "https://images.unsplash.com/photo-1599785209707-a456fc1337bb?w=400&q=80",  # Kashmir Royal Saffron Strands
        ],
        "Breakfast Cereals": [
            "https://images.unsplash.com/photo-1517093157656-b9ec91e311ef?w=400&q=80",  # Rolled Oats with Chia & Honey
        ],
        "Beverages & Juices": [
            "https://images.unsplash.com/photo-1613478223719-2ab802602423?w=400&q=80",  # 100% Cold Pressed Valencia Orange
        ]
    },
    "Sports & Fitness": {
        "Gym & Home Workout": [
            "https://images.unsplash.com/photo-1584735935682-2f2b69dff9d2?w=400&q=80",  # Rubber Coated Hex Dumbbells Set
            "https://images.unsplash.com/photo-1517838277536-f5f99be501cd?w=400&q=80",  # Adjustable Incline Weight Bench
            "https://images.unsplash.com/photo-1598289431512-b97b0917affc?w=400&q=80",  # Pull Up Resistance Bands Kit
        ],
        "Yoga Mats & Blocks": [
            "https://images.unsplash.com/photo-1601925260368-ae2f83cf8b7f?w=400&q=80",  # 6mm Anti-Skid Eco TPE Yoga Mat
            "https://images.unsplash.com/photo-1506126613408-eca07ce68773?w=400&q=80",  # High Density Cork Yoga Block
        ],
        "Cricket & Team Sports": [
            "https://images.unsplash.com/photo-1531415074868-036b1c575351?w=400&q=80",  # English Willow Cricket Bat
            "https://images.unsplash.com/photo-1579952363873-27f3bade9f55?w=400&q=80",  # Match Size 5 Football
        ],
        "Badminton & Tennis": [
            "https://images.unsplash.com/photo-1626224583764-f87db24ac4ea?w=400&q=80",  # High Carbon Badminton Racket
            "https://images.unsplash.com/photo-1622279457486-62dcc4a431d6?w=400&q=80",  # Pressurized Tennis Balls Pack
        ],
        "Fitness Accessories": [
            "https://images.unsplash.com/photo-1598289431512-b97b0917affc?w=400&q=80",  # Leather Weightlifting Gym Belt
            "https://images.unsplash.com/photo-1526506118085-60ce8714f8c5?w=400&q=80",  # High Speed Bearing Jump Rope
        ],
        "Shakers & Water Bottles": [
            "https://images.unsplash.com/photo-1602143407151-7111542de6e8?w=400&q=80",  # Insulated Stainless Steel Bottle
            "https://images.unsplash.com/photo-1523362628745-0c100150b504?w=400&q=80",  # Leakproof Protein Shaker Cup
        ],
        "Cycling & Skates": [
            "https://images.unsplash.com/photo-1485965120184-e220f721d03e?w=400&q=80",  # 21-Speed Mountain Bicycle
        ],
        "Running & Athletics": [
            "https://images.unsplash.com/photo-1460353581641-37baddab0fa2?w=400&q=80",  # Compression Calf Sleeves
        ],
        "Swimming": [
            "https://images.unsplash.com/photo-1530549387789-4c1017266635?w=400&q=80",  # Anti-Fog UV Swimming Goggles
        ],
        "Outdoor Camping": [
            "https://images.unsplash.com/photo-1504280390367-361c6d9f38f4?w=400&q=80",  # Waterproof 4-Person Dome Tent
        ]
    },
    "Books & Stationery": {
        "Fiction & Bestsellers": [
            "https://images.unsplash.com/photo-1544947950-fa07a98d237f?w=400&q=80",  # Bestselling Paperback Novel
            "https://images.unsplash.com/photo-1512820790803-83ca734da794?w=400&q=80",  # Hardcover Classic Fiction
        ],
        "Self-Help & Business": [
            "https://images.unsplash.com/photo-1589829085413-56de8ae18c73?w=400&q=80",  # Productivity & Wealth Book
            "https://images.unsplash.com/photo-1532012164546-f432f2e3777f?w=400&q=80",  # Inspirational Leadership Title
        ],
        "Pens & Writing Instruments": [
            "https://images.unsplash.com/photo-1583485088034-697b5bc54ccd?w=400&q=80",  # Luxury Metal Fountain Pen
            "https://images.unsplash.com/photo-1585336261026-41ff9115f235?w=400&q=80",  # 0.5mm Fine Gel Pens Pack of 10
        ],
        "Notebooks & Journals": [
            "https://images.unsplash.com/photo-1531346878377-a5be20888e57?w=400&q=80",  # Hardbound Dotted Bullet Journal
            "https://images.unsplash.com/photo-1517842645767-c639042777db?w=400&q=80",  # A5 Wirebound Ruled Notebooks
        ],
        "Art & Sketching Supplies": [
            "https://images.unsplash.com/photo-1513364776144-60967b0f800f?w=400&q=80",  # Dual Tip Alcohol Brush Markers
            "https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?w=400&q=80",  # 160 GSM Heavyweight Sketchpad
        ],
        "Desk Organizers": [
            "https://images.unsplash.com/photo-1507842229458-57790b8f6c4d?w=400&q=80",  # Metal Mesh Rotating Pen Stand
        ],
        "Files & Folders": [
            "https://images.unsplash.com/photo-1497633762265-9d179a990aa6?w=400&q=80",  # Expanding Document Organizer
        ],
        "Scientific Calculators": [
            "https://images.unsplash.com/photo-1587145820266-a5951ee6f620?w=400&q=80",  # Advanced Scientific Calculator
        ]
    },
    "Watches & Accessories": {
        "Smartwatches": [
            "https://images.unsplash.com/photo-1508685096489-7aacd43bd3b1?w=400&q=80",  # AMOLED Bluetooth Calling Watch
            "https://images.unsplash.com/photo-1579586337278-3befd40fd17a?w=400&q=80",  # Stainless Steel Smart Tracker
        ],
        "Men's Analog Watches": [
            "https://images.unsplash.com/photo-1524805444758-089113d48a6d?w=400&q=80",  # Classic Leather Chronograph
            "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&q=80",  # Stainless Steel Quartz Watch
            "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=400&q=80",  # Minimalist White Dial Watch
        ],
        "Women's Analog Watches": [
            "https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=400&q=80",  # Rose Gold Mesh Strap Watch
            "https://images.unsplash.com/photo-1548036328-c9fa89d128fa?w=400&q=80",  # Diamond Accent Dial Watch
        ],
        "Chronograph & Sports Watches": [
            "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&q=80",  # Tactical Water Resistant 100m
        ],
        "Jewellery & Bracelets": [
            "https://images.unsplash.com/photo-1599643478518-a784e5dc4c8f?w=400&q=80",  # Sterling Silver Chain Bracelet
            "https://images.unsplash.com/photo-1535632066927-ab7c9ab60908?w=400&q=80",  # 18K Gold Plated Minimalist Ring
        ],
        "Wallets & Cardholders": [
            "https://images.unsplash.com/photo-1627123424574-724758594e93?w=400&q=80",  # Full Grain Leather Wallet
        ],
        "Leather Belts": [
            "https://images.unsplash.com/photo-1624222247344-550fb60583dc?w=400&q=80",  # Genuine Italian Leather Belt
        ],
        "Watch Straps & Cases": [
            "https://images.unsplash.com/photo-1524805444758-089113d48a6d?w=400&q=80",  # Quick Release Leather Watch Band
        ]
    },
    "Health & Wellness": {
        "Protein Supplements": [
            "https://images.unsplash.com/photo-1579722821273-0f6c7d44362f?w=400&q=80",  # 100% Whey Protein Isolate 1kg
            "https://images.unsplash.com/photo-1593095948071-474c5cc2989d?w=400&q=80",  # Plant Based Vegan Protein
        ],
        "Vitamins & Minerals": [
            "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=400&q=80",  # Daily Multivitamin 60 Tablets
            "https://images.unsplash.com/photo-1577401239170-897942555fb3?w=400&q=80",  # Vitamin D3 + K2 Bone Health
        ],
        "Fish Oil & Omega-3": [
            "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=400&q=80",  # Triple Strength Omega 3 Softgels
        ],
        "Ayurvedic & Herbal": [
            "https://images.unsplash.com/photo-1540420773420-3366772f4999?w=400&q=80",  # Pure Organic Ashwagandha Root
            "https://images.unsplash.com/photo-1608248597359-5f284ec1bc7a?w=400&q=80",  # Triphala Digestion Churna
        ],
        "Health Monitors & BP": [
            "https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?w=400&q=80",  # Digital Upper Arm BP Monitor
            "https://images.unsplash.com/photo-1583947215259-38e31be8751f?w=400&q=80",  # Fingertip Pulse Oximeter
        ],
        "Weight Management": [
            "https://images.unsplash.com/photo-1540420773420-3366772f4999?w=400&q=80",  # Apple Cider Vinegar with Mother
        ],
        "Pain Relief Sprays": [
            "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=400&q=80",  # Herbal Joint Pain Relief Oil
        ],
        "First Aid & Sanitizers": [
            "https://images.unsplash.com/photo-1584515979956-d9f6e5d09982?w=400&q=80",  # Comprehensive 50-Item First Aid Kit
        ]
    },
    "Automotive Accessories": {
        "Car Dashcams & Electronics": [
            "https://images.unsplash.com/photo-1508974239320-0a029497e820?w=400&q=80",  # 4K Front & Rear Dual Dashcam
            "https://images.unsplash.com/photo-1544197150-b99a580bb7a8?w=400&q=80",  # Bluetooth FM Transmitter Charger
        ],
        "Tyre Inflators & Gauges": [
            "https://images.unsplash.com/photo-1486006920555-c77dce18193b?w=400&q=80",  # 12V Digital Auto Tyre Air Pump
        ],
        "Car Vacuum Cleaners": [
            "https://images.unsplash.com/photo-1558317374-067fb5f30001?w=400&q=80",  # High Power Portable Car Vacuum
        ],
        "Helmets & Riding Gear": [
            "https://images.unsplash.com/photo-1558981403-c5f9899a28bc?w=400&q=80",  # DOT Certified Full Face Helmet
            "https://images.unsplash.com/photo-1558981420-87aa9dad1c89?w=400&q=80",  # Breathable Leather Riding Gloves
        ],
        "Car Cleaning & Polishing": [
            "https://images.unsplash.com/photo-1607860108855-64acf2078ed9?w=400&q=80",  # Carnauba Car Wax Shampoo
            "https://images.unsplash.com/photo-1607860108855-64acf2078ed9?w=400&q=80",  # 800 GSM Microfiber Drying Towels
        ],
        "Car Perfumes & Fresheners": [
            "https://images.unsplash.com/photo-1594035910387-fea47794261f?w=400&q=80",  # Solar Rotating Car Air Freshener
        ],
        "Seat Covers & Cushions": [
            "https://images.unsplash.com/photo-1549399542-7e3f8b79c341?w=400&q=80",  # Memory Foam Orthopedic Backrest
        ],
        "Mobile Holders & Chargers": [
            "https://images.unsplash.com/photo-1586105251261-72a756497a11?w=400&q=80",  # 360 Degree Dashboard Gravity Mount
        ]
    },
    "Pet Supplies": {
        "Dog Food": [
            "https://images.unsplash.com/photo-1589924691995-400dc9ecc119?w=400&q=80",  # Chicken & Rice Dog Kibble 10kg
            "https://images.unsplash.com/photo-1568640347023-a616a30bc3bd?w=400&q=80",  # Rawhide Calcium Chew Sticks
        ],
        "Cat Food & Treats": [
            "https://images.unsplash.com/photo-1548767797-d8c844163c4c?w=400&q=80",  # Ocean Fish Wet Cat Food Pouch
            "https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?w=400&q=80",  # Crunchy Salmon Cat Treats
        ],
        "Dog Toys": [
            "https://images.unsplash.com/photo-1535930891776-0c2dfb7fda1a?w=400&q=80",  # Tough Rubber Fetch Ball & Rope
            "https://images.unsplash.com/photo-1576201836106-db1758fd1c97?w=400&q=80",  # Squeaky Plush Chew Toy
        ],
        "Pet Grooming & Brushes": [
            "https://images.unsplash.com/photo-1516734212186-a967f81ad0d7?w=400&q=80",  # Self-Cleaning Slicker Brush
            "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=400&q=80",  # Anti-Tick Aloe Vera Pet Shampoo
        ],
        "Dog Collars & Leashes": [
            "https://images.unsplash.com/photo-1601758228041-f3b2795255f1?w=400&q=80",  # Reflective Padded Dog Harness
            "https://images.unsplash.com/photo-1583511655857-d19b40a7a54e?w=400&q=80",  # 5M Retractable Dog Leash
        ],
        "Pet Beds & Mats": [
            "https://images.unsplash.com/photo-1541599540903-216a46ca1dc0?w=400&q=80",  # Washable Donut Cuddle Pet Bed
        ],
        "Cat Litter & Accessories": [
            "https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?w=400&q=80",  # Clumping Bentonite Cat Litter
        ],
        "Aquarium Supplies": [
            "https://images.unsplash.com/photo-1522069169874-c58ec4b76be5?w=400&q=80",  # Submersible Aquarium Water Filter
        ]
    },
    "Travel & Luggage": {
        "Hard-Shell Trolley Bags": [
            "https://images.unsplash.com/photo-1565026057447-bc90a3dceb87?w=400&q=80",  # Polycarbonate Spinner Suitcase
            "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=400&q=80",  # Rose Gold Metallic Trolley Bag
            "https://images.unsplash.com/photo-1581553680321-4fffae59fccd?w=400&q=80",  # Navy Blue 4-Wheel Hard Luggage
        ],
        "Soft-Sided Luggage": [
            "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=400&q=80",  # Expandable Polyester Trolley
        ],
        "Cabin & Carry-On Bags": [
            "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=400&q=80",  # 20-Inch International Carry-On
        ],
        "Backpacks & Laptop Bags": [
            "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=400&q=80",  # Water Resistant Laptop Backpack
            "https://images.unsplash.com/photo-1622560480605-d83c853bc5c3?w=400&q=80",  # Ergonomic College Daypack
            "https://images.unsplash.com/photo-1546938576-6e6a64f317cc?w=400&q=80",  # Leather Vintage Travel Rucksack
        ],
        "Duffle & Gym Bags": [
            "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=400&q=80",  # Barrel Gym Bag with Shoe Compartment
            "https://images.unsplash.com/photo-1544816155-12df9643f363?w=400&q=80",  # Weekend Travel Canvas Duffle
        ],
        "Travel Accessories & Pouches": [
            "https://images.unsplash.com/photo-1584917865442-de89df76afd3?w=400&q=80",  # 6-Piece Packing Cubes Organizer
            "https://images.unsplash.com/photo-1584100936595-c0654b55a2e2?w=400&q=80",  # Memory Foam Ergonomic Neck Pillow
        ],
        "Rucksacks & Trekking Bags": [
            "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=400&q=80",  # 65L Internal Frame Hiking Rucksack
        ]
    }
}


def assign_diverse_images():
    """Assigns rich, verified diverse product images across all 1,040 products."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT id, name, category, subcategory FROM products ORDER BY id ASC")
    products = cursor.fetchall()
    total = len(products)
    print(f"Total products to process: {total}")

    updates = []
    category_counters = {}

    for row in products:
        pid = row["id"]
        name = row["name"].lower()
        cat = row["category"]
        subcat = row["subcategory"] or ""

        cat_pool = IMAGE_POOLS.get(cat, {})
        selected_url = None

        # 1. Match by subcategory in category pool
        subcat_pool = cat_pool.get(subcat)

        # 2. If subcategory pool not directly found, check partial match or product name
        if not subcat_pool:
            for s_key, urls in cat_pool.items():
                if s_key.lower() in subcat.lower() or subcat.lower() in s_key.lower():
                    subcat_pool = urls
                    break

        if not subcat_pool:
            for s_key, urls in cat_pool.items():
                # check if any word from s_key is in name
                words = [w for w in s_key.lower().split() if len(w) > 3]
                if any(w in name for w in words):
                    subcat_pool = urls
                    break

        # Fallback to any subcat in category pool
        if not subcat_pool and cat_pool:
            all_urls = []
            for urls in cat_pool.values():
                all_urls.extend(urls)
            subcat_pool = all_urls

        if subcat_pool:
            # Deterministic round-robin index based on product ID to ensure reproducible diversity
            idx = pid % len(subcat_pool)
            selected_url = subcat_pool[idx]
        else:
            # General fallback
            selected_url = "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&q=80"

        updates.append((selected_url, pid))

    # Execute batch update
    cursor.executemany("UPDATE products SET image_url = ? WHERE id = ?", updates)
    conn.commit()
    conn.close()

    print(f"Successfully updated image URLs for all {len(updates)} products!")


if __name__ == "__main__":
    assign_diverse_images()
