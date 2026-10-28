"""
seed_products.py
----------------
Seeds the products table with 56 realistic demo products across 8 categories:
- Electronics
- Computer Accessories
- Fashion
- Home Essentials
- Kitchen Products
- Personal Care
- Stationery
- Everyday Consumables

Each product includes:
- Real e-commerce product image URLs (Unsplash CDN)
- Genuine specifications
- MRP (original price for discount calculation)
- Review counts and ratings
"""

import json
import sys
import os

# Allow running as a standalone script from the project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from database import get_db

PRODUCTS = [
    # ------------------------------------------------------------------ #
    #  ELECTRONICS (10 products)
    # ------------------------------------------------------------------ #
    {
        "name": "Sony WH-1000XM5 Wireless Headphones",
        "category": "Electronics",
        "brand": "Sony",
        "price": 329.99,
        "specifications": {
            "mrp": 399.99,
            "discount_percent": 18,
            "review_count": 4280,
            "type": "Over-ear",
            "connectivity": "Bluetooth 5.2",
            "battery_life": "30 hours",
            "noise_cancellation": "Industry-leading ANC",
            "weight": "250g",
            "microphone": "8-mic array",
            "foldable": True,
        },
        "description": "Premium noise-cancelling wireless headphones with exceptional sound quality, 30-hour battery life, and multipoint connection.",
        "image_url": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=600&q=80",
        "rating": 4.8,
        "stock": 85,
    },
    {
        "name": "Samsung Galaxy S24 Ultra",
        "category": "Electronics",
        "brand": "Samsung",
        "price": 1299.99,
        "specifications": {
            "mrp": 1419.99,
            "discount_percent": 8,
            "review_count": 3150,
            "display": "6.8-inch QHD+ Dynamic AMOLED 2X",
            "processor": "Snapdragon 8 Gen 3",
            "ram": "12 GB",
            "storage": "256 GB",
            "camera": "200 MP main + 12 MP ultra-wide",
            "battery": "5000 mAh",
            "5g": True,
        },
        "description": "Flagship Android smartphone with titanium frame, built-in S Pen, and Galaxy AI photo intelligence.",
        "image_url": "https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?auto=format&fit=crop&w=600&q=80",
        "rating": 4.7,
        "stock": 60,
    },
    {
        "name": "Apple AirPods Pro (2nd Gen)",
        "category": "Electronics",
        "brand": "Apple",
        "price": 249.00,
        "specifications": {
            "mrp": 279.00,
            "discount_percent": 11,
            "review_count": 8900,
            "chip": "H2 Apple silicon",
            "battery_life": "6 hours (30 with case)",
            "water_resistance": "IP54",
            "audio": "Spatial Audio with dynamic head tracking",
        },
        "description": "Active Noise Cancellation up to 2x more effective, Adaptive Audio, and Personalized Spatial Audio.",
        "image_url": "https://images.unsplash.com/photo-1600294037681-c80b4cb5b434?auto=format&fit=crop&w=600&q=80",
        "rating": 4.9,
        "stock": 120,
    },
    {
        "name": "Apple Watch Series 9 GPS 45mm",
        "category": "Electronics",
        "brand": "Apple",
        "price": 399.00,
        "specifications": {
            "mrp": 429.00,
            "discount_percent": 7,
            "review_count": 2400,
            "case_size": "45mm Aluminum",
            "chip": "S9 SiP with 64-bit dual-core",
            "brightness": "2000 nits edge-to-edge",
            "sensors": "ECG, Blood Oxygen, Temperature",
        },
        "description": "Smarter, brighter, and mightier with Double Tap gesture and on-device Siri health metrics.",
        "image_url": "https://images.unsplash.com/photo-1579586337278-3befd40fd17a?auto=format&fit=crop&w=600&q=80",
        "rating": 4.8,
        "stock": 70,
    },
    {
        "name": "iPad Air M2 11-inch",
        "category": "Electronics",
        "brand": "Apple",
        "price": 599.00,
        "specifications": {
            "mrp": 649.00,
            "discount_percent": 8,
            "review_count": 1820,
            "chip": "Apple M2 8-core CPU",
            "display": "Liquid Retina 11-inch True Tone",
            "storage": "128 GB",
            "support": "Apple Pencil Pro & Magic Keyboard",
        },
        "description": "Turbocharged by the M2 chip with stunning Liquid Retina display and all-day battery life.",
        "image_url": "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?auto=format&fit=crop&w=600&q=80",
        "rating": 4.8,
        "stock": 45,
    },
    {
        "name": "Anker 733 Power Bank GaNPrime 65W",
        "category": "Electronics",
        "brand": "Anker",
        "price": 99.99,
        "specifications": {
            "mrp": 129.99,
            "discount_percent": 23,
            "review_count": 3120,
            "capacity": "10000 mAh",
            "output": "65W max via USB-C",
            "ports": "2x USB-C, 1x USB-A",
            "form": "2-in-1 hybrid charger",
        },
        "description": "High-speed 2-in-1 wall charger and portable battery power bank powered by GaNPrime technology.",
        "image_url": "https://images.unsplash.com/photo-1609592424856-06fb76359f1f?auto=format&fit=crop&w=600&q=80",
        "rating": 4.7,
        "stock": 95,
    },
    {
        "name": "Sony WF-1000XM5 True Wireless Earbuds",
        "category": "Electronics",
        "brand": "Sony",
        "price": 279.99,
        "specifications": {
            "mrp": 299.99,
            "discount_percent": 7,
            "review_count": 2180,
            "drivers": "Dynamic Driver X",
            "anc": "Dual feedback microphones",
            "battery": "8 hours (24 with case)",
            "codec": "LDAC Hi-Res Wireless",
        },
        "description": "Astonishing sound quality and cutting-edge noise cancelling with bone conduction sensors.",
        "image_url": "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?auto=format&fit=crop&w=600&q=80",
        "rating": 4.6,
        "stock": 50,
    },
    {
        "name": "Kindle Paperwhite Signature Edition",
        "category": "Electronics",
        "brand": "Amazon",
        "price": 139.99,
        "specifications": {
            "mrp": 179.99,
            "discount_percent": 22,
            "review_count": 6400,
            "display": "6.8-inch 300 ppi glare-free",
            "lighting": "Auto-adjusting warm light",
            "storage": "32 GB",
            "waterproof": "IPX8",
        },
        "description": "Purpose-built for reading with flush-front design, adjustable warm light, and weeks of battery life.",
        "image_url": "https://images.unsplash.com/photo-1592496431122-2349e0fbc666?auto=format&fit=crop&w=600&q=80",
        "rating": 4.8,
        "stock": 110,
    },
    {
        "name": "Xiaomi Redmi Note 13 Pro+ 5G",
        "category": "Electronics",
        "brand": "Xiaomi",
        "price": 449.99,
        "specifications": {
            "mrp": 499.99,
            "discount_percent": 10,
            "review_count": 1490,
            "camera": "200 MP OIS main sensor",
            "charging": "120W HyperCharge",
            "screen": "1.5K 120Hz curved AMOLED",
            "ip_rating": "IP68 water resistant",
        },
        "description": "Super-clear 200MP camera with OIS, 120W HyperCharge, and flagship curved AMOLED display.",
        "image_url": "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=600&q=80",
        "rating": 4.5,
        "stock": 75,
    },
    {
        "name": "JBL Flip 6 Portable Bluetooth Speaker",
        "category": "Electronics",
        "brand": "JBL",
        "price": 129.95,
        "specifications": {
            "mrp": 149.95,
            "discount_percent": 13,
            "review_count": 5200,
            "sound": "2-way speaker system with deep bass",
            "waterproof": "IP67 waterproof and dustproof",
            "battery": "12 hours playtime",
            "partyboost": True,
        },
        "description": "Bold JBL Original Pro Sound with 2-way speaker system, racetrack-shaped woofer, and separate tweeter.",
        "image_url": "https://images.unsplash.com/photo-1545454675-3531b543be5d?auto=format&fit=crop&w=600&q=80",
        "rating": 4.7,
        "stock": 130,
    },

    # ------------------------------------------------------------------ #
    #  COMPUTER ACCESSORIES (8 products)
    # ------------------------------------------------------------------ #
    {
        "name": "Logitech MX Master 3S Wireless Mouse",
        "category": "Computer Accessories",
        "brand": "Logitech",
        "price": 99.99,
        "specifications": {
            "mrp": 119.99,
            "discount_percent": 17,
            "review_count": 6800,
            "sensor": "8000 DPI Darkfield tracking on glass",
            "clicks": "Quiet Clicks (90% noise reduction)",
            "scroll": "MagSpeed electromagnetic scroll wheel",
            "connectivity": "Bluetooth + Logi Bolt USB",
            "battery": "70 days on full charge",
        },
        "description": "An iconic ergonomic wireless performance mouse reimagined with Quiet Clicks and 8,000 DPI track-on-glass sensor.",
        "image_url": "https://images.unsplash.com/photo-1615663245857-ac93bb7c39e7?auto=format&fit=crop&w=600&q=80",
        "rating": 4.9,
        "stock": 90,
    },
    {
        "name": "Keychron K8 Pro QMK Wireless Mechanical Keyboard",
        "category": "Computer Accessories",
        "brand": "Keychron",
        "price": 109.00,
        "specifications": {
            "mrp": 129.00,
            "discount_percent": 16,
            "review_count": 2400,
            "switches": "Gateron G Pro Brown tactile",
            "layout": "Tenkeyless (87 keys)",
            "connectivity": "Bluetooth 5.1 + Type-C wired",
            "qmk_via": "Fully programmable with VIA",
            "hotswap": True,
        },
        "description": "Wireless mechanical keyboard allowing anyone to master any keyboard keys or macro commands through VIA.",
        "image_url": "https://images.unsplash.com/photo-1587829741301-dc798b83add3?auto=format&fit=crop&w=600&q=80",
        "rating": 4.8,
        "stock": 65,
    },
    {
        "name": "Anker 7-in-1 USB-C Hub Adapter",
        "category": "Computer Accessories",
        "brand": "Anker",
        "price": 39.99,
        "specifications": {
            "mrp": 49.99,
            "discount_percent": 20,
            "review_count": 9200,
            "ports": "4K HDMI, 100W Power Delivery, SD/TF, 2x USB-A, 1x USB-C",
            "hdmi": "4K@30Hz or 1080p@60Hz",
            "pass_through": "85W continuous charging",
        },
        "description": "Massive expansion with 4K HDMI, SD card reader, 100W PD pass-through charging, and ultra-high-speed data transfer.",
        "image_url": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?auto=format&fit=crop&w=600&q=80",
        "rating": 4.7,
        "stock": 140,
    },
    {
        "name": "Logitech C920s HD Pro Webcam with Privacy Shutter",
        "category": "Computer Accessories",
        "brand": "Logitech",
        "price": 79.99,
        "specifications": {
            "mrp": 89.99,
            "discount_percent": 11,
            "review_count": 5100,
            "resolution": "Full HD 1080p/30fps",
            "autofocus": "HD auto light correction",
            "audio": "Dual stereo microphones",
            "fov": "78 degrees field of view",
        },
        "description": "Remarkably crisp and detailed Full HD video with a glass lens and stereo audio for remote professional meetings.",
        "image_url": "https://images.unsplash.com/photo-1585338107529-13afc5f02586?auto=format&fit=crop&w=600&q=80",
        "rating": 4.7,
        "stock": 100,
    },
    {
        "name": "Dell UltraSharp U2724D 27-inch 120Hz Monitor",
        "category": "Computer Accessories",
        "brand": "Dell",
        "price": 479.99,
        "specifications": {
            "mrp": 549.99,
            "discount_percent": 13,
            "review_count": 890,
            "panel": "IPS Black with 2000:1 contrast",
            "resolution": "QHD 2560x1440 at 120Hz",
            "color": "98% DCI-P3, ComfortView Plus",
            "ports": "DisplayPort 1.4, HDMI, USB-C 90W PD",
        },
        "description": "Experience deeper blacks and improved color accuracy with IPS Black technology and silky 120Hz refresh rates.",
        "image_url": "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?auto=format&fit=crop&w=600&q=80",
        "rating": 4.9,
        "stock": 30,
    },
    {
        "name": "SteelSeries Arctis Nova 7 Wireless Headset",
        "category": "Computer Accessories",
        "brand": "SteelSeries",
        "price": 179.99,
        "specifications": {
            "mrp": 199.99,
            "discount_percent": 10,
            "review_count": 1650,
            "audio": "Nova Acoustic System with Hi-Fi Drivers",
            "wireless": "Simultaneous 2.4GHz and Bluetooth",
            "battery": "38 hours with fast charging",
            "mic": "ClearCast Gen 2 AI-powered noise-cancelling",
        },
        "description": "Almighty Audio meets multi-platform wireless for PC, Mac, PlayStation, and mobile work sessions.",
        "image_url": "https://images.unsplash.com/photo-1546435770-a3e426bf472b?auto=format&fit=crop&w=600&q=80",
        "rating": 4.6,
        "stock": 55,
    },
    {
        "name": "Corsair MM300 PRO Extended Gaming Mousepad",
        "category": "Computer Accessories",
        "brand": "Corsair",
        "price": 29.99,
        "specifications": {
            "mrp": 39.99,
            "discount_percent": 25,
            "review_count": 4200,
            "dimensions": "930mm x 300mm x 3mm",
            "coating": "Spill-proof and stain-resistant",
            "stitching": "360-degree precision anti-fray",
            "base": "Textured anti-skid rubber base",
        },
        "description": "Spill-proof cloth mouse pad providing an ultra-fast glide surface for low-friction optical mice.",
        "image_url": "https://images.unsplash.com/photo-1618384887929-16ec33fab9ef?auto=format&fit=crop&w=600&q=80",
        "rating": 4.8,
        "stock": 180,
    },
    {
        "name": "Nulaxy Ergonomic Aluminum Laptop Stand",
        "category": "Computer Accessories",
        "brand": "Nulaxy",
        "price": 27.99,
        "specifications": {
            "mrp": 34.99,
            "discount_percent": 20,
            "review_count": 8300,
            "material": "CNC machined aviation aluminum",
            "compatibility": "Laptops 10 to 17.3 inches",
            "elevation": "Raises screen by 6 inches for neck ergonomics",
            "cooling": "Open ventilation airflow design",
        },
        "description": "Universal laptop riser with ergonomic eye-level elevation, heat-dissipating aluminum, and anti-slip silicone pads.",
        "image_url": "https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?auto=format&fit=crop&w=600&q=80",
        "rating": 4.7,
        "stock": 160,
    },

    # ------------------------------------------------------------------ #
    #  FASHION & APPAREL (6 products)
    # ------------------------------------------------------------------ #
    {
        "name": "Nike Air Max 270 Lifestyle Sneakers",
        "category": "Fashion",
        "brand": "Nike",
        "price": 159.99,
        "specifications": {
            "mrp": 179.99,
            "discount_percent": 11,
            "review_count": 3890,
            "cushioning": "Max Air 270 unit in heel",
            "material": "Breathable knit mesh upper",
            "sole": "Dual-density foam with rubber waffle tread",
            "closure": "Asymmetrical lacing for secure fit",
        },
        "description": "Legendary street style footwear engineered with Nike's largest heel Air unit for unbelievable all-day bounce and cloud comfort.",
        "image_url": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=600&q=80",
        "rating": 4.8,
        "stock": 70,
    },
    {
        "name": "Levi's The Trucker Classic Denim Jacket",
        "category": "Fashion",
        "brand": "Levi's",
        "price": 89.50,
        "specifications": {
            "mrp": 108.00,
            "discount_percent": 17,
            "review_count": 2100,
            "fabric": "100% non-stretch cotton denim",
            "fit": "Standard fit hits at waist",
            "pockets": "Button-flap chest pockets + side welts",
            "origin": "Original 1967 Trucker blueprint",
        },
        "description": "The quintessential denim jacket worn and loved for generations. Made with durable cotton denim that only gets better with age.",
        "image_url": "https://images.unsplash.com/photo-1576995853123-5a10305d93c0?auto=format&fit=crop&w=600&q=80",
        "rating": 4.7,
        "stock": 45,
    },
    {
        "name": "Fossil Minimalist Chronograph Leather Watch",
        "category": "Fashion",
        "brand": "Fossil",
        "price": 129.00,
        "specifications": {
            "mrp": 160.00,
            "discount_percent": 19,
            "review_count": 1420,
            "case": "44mm slim stainless steel",
            "strap": "22mm genuine brown leather interchangeable",
            "movement": "Quartz chronograph movement",
            "water_resistance": "5 ATM / 50 meters",
        },
        "description": "A clean, understated timepiece combining classic brown leather craftsmanship with contemporary satin-finish dial aesthetics.",
        "image_url": "https://images.unsplash.com/photo-1524805444758-089113d48a6d?auto=format&fit=crop&w=600&q=80",
        "rating": 4.6,
        "stock": 55,
    },
    {
        "name": "Ray-Ban Classic Aviator Polarized Sunglasses",
        "category": "Fashion",
        "brand": "Ray-Ban",
        "price": 174.00,
        "specifications": {
            "mrp": 213.00,
            "discount_percent": 18,
            "review_count": 4800,
            "lens": "G-15 Polarized green crystal lenses",
            "frame": "Classic polished gold metal frame",
            "uv_protection": "100% UV400 protective coating",
            "bridge": "14mm double bridge with adjustable nose pads",
        },
        "description": "Timeless pilot sunglasses originally created for U.S. aviators in 1937. Combines legendary style with exceptional eye protection.",
        "image_url": "https://images.unsplash.com/photo-1511499767150-a48a237f0083?auto=format&fit=crop&w=600&q=80",
        "rating": 4.9,
        "stock": 60,
    },
    {
        "name": "Puma Evercat Contender Training Duffel Bag",
        "category": "Fashion",
        "brand": "Puma",
        "price": 38.00,
        "specifications": {
            "mrp": 48.00,
            "discount_percent": 21,
            "review_count": 1850,
            "capacity": "38 Liters",
            "compartments": "Side shoe pocket + interior organizer",
            "material": "Heavy-duty 100% polyester weave",
            "strap": "Padded adjustable shoulder strap",
        },
        "description": "Versatile weekend gym duffel featuring dedicated ventilated footwear compartment and durable water-resistant base.",
        "image_url": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?auto=format&fit=crop&w=600&q=80",
        "rating": 4.5,
        "stock": 85,
    },
    {
        "name": "Tommy Hilfiger Classic Crewneck Cotton Sweatshirt",
        "category": "Fashion",
        "brand": "Tommy Hilfiger",
        "price": 69.50,
        "specifications": {
            "mrp": 89.50,
            "discount_percent": 22,
            "review_count": 920,
            "fabric": "100% organic French terry cotton",
            "details": "Ribbed collar, cuffs, and hem with signature flag",
            "care": "Machine washable colorfast",
        },
        "description": "Relaxed collegiate comfort featuring premium breathable cotton fleece and iconic embroidered chest emblem.",
        "image_url": "https://images.unsplash.com/photo-1556905055-8f358a7a47b2?auto=format&fit=crop&w=600&q=80",
        "rating": 4.6,
        "stock": 90,
    },

    # ------------------------------------------------------------------ #
    #  HOME ESSENTIALS / LIVING (8 products)
    # ------------------------------------------------------------------ #
    {
        "name": "Philips LED Smart Bulb Hue White & Color Ambiance",
        "category": "Home Essentials",
        "brand": "Philips",
        "price": 49.99,
        "specifications": {
            "mrp": 59.99,
            "discount_percent": 17,
            "review_count": 5200,
            "lumens": "800 Lumens (60W equivalent)",
            "colors": "16 million colors + warm-to-cool whites",
            "smart": "Alexa, Google Assistant, Apple HomeKit",
            "base": "Standard E26 / E27 socket",
        },
        "description": "Transform your room atmosphere with 16 million colors and instant Bluetooth control in any room.",
        "image_url": "https://images.unsplash.com/photo-1550985543-f47f38aeee65?auto=format&fit=crop&w=600&q=80",
        "rating": 4.7,
        "stock": 150,
    },
    {
        "name": "Levoit Core 300 True HEPA Air Purifier",
        "category": "Home Essentials",
        "brand": "Levoit",
        "price": 99.99,
        "specifications": {
            "mrp": 129.99,
            "discount_percent": 23,
            "review_count": 12400,
            "filtration": "H13 True HEPA with activated carbon",
            "coverage": "Purifies 1095 sq ft in 1 hour",
            "noise": "24dB ultra-quiet Sleep Mode",
            "timer": "2, 4, 6, 8-hour auto shut-off",
        },
        "description": "Breathe fresh air with 3-stage filtration capturing 99.97% of airborne particles down to 0.3 microns.",
        "image_url": "https://images.unsplash.com/photo-1585771724684-38269d6639fd?auto=format&fit=crop&w=600&q=80",
        "rating": 4.8,
        "stock": 75,
    },
    {
        "name": "Anker 12-Outlet Heavy-Duty Surge Protector Strip",
        "category": "Home Essentials",
        "brand": "Anker",
        "price": 29.99,
        "specifications": {
            "mrp": 39.99,
            "discount_percent": 25,
            "review_count": 4800,
            "outlets": "12 AC outlets + 2 USB-A + 1 USB-C PD",
            "joules": "4000 Joules surge protection rating",
            "cord": "6ft heavy-duty braided power cable",
            "safety": "Dual 15A circuit breakers",
        },
        "description": "All-in-one power station safeguarding high-end home office workstations from dangerous electrical spikes.",
        "image_url": "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?auto=format&fit=crop&w=600&q=80",
        "rating": 4.8,
        "stock": 190,
    },
    {
        "name": "Dyson Cool Tower Fan AM07",
        "category": "Home Essentials",
        "brand": "Dyson",
        "price": 369.99,
        "specifications": {
            "mrp": 429.99,
            "discount_percent": 14,
            "review_count": 920,
            "tech": "Air Multiplier bladeless airflow technology",
            "settings": "10 precise airflow speeds with sleep timer",
            "remote": "Curved magnetized remote docks on machine",
            "sound": "60% quieter than previous AM02 model",
        },
        "description": "Smooth, powerful cooling with no fast-spinning blades, making it safe for kids and pets and effortlessly easy to clean.",
        "image_url": "https://images.unsplash.com/photo-1618944847828-82e943c3bdb7?auto=format&fit=crop&w=600&q=80",
        "rating": 4.6,
        "stock": 35,
    },
    {
        "name": "Pure Enrichment MistAire Ultrasonic Cool Mist Humidifier",
        "category": "Home Essentials",
        "brand": "Pure Enrichment",
        "price": 39.99,
        "specifications": {
            "mrp": 49.99,
            "discount_percent": 20,
            "review_count": 7100,
            "tank": "1.5-Liter transparent water tank",
            "runtime": "Up to 25 hours continuous operation",
            "feature": "Optional soothing night light glow",
            "auto_off": "Shuts off safely when water level is low",
        },
        "description": "Safely moisturizes the dry indoor air for up to 25 hours to soothe congestion, sinus issues, and dry skin.",
        "image_url": "https://images.unsplash.com/photo-1542013936693-884638332954?auto=format&fit=crop&w=600&q=80",
        "rating": 4.7,
        "stock": 90,
    },
    {
        "name": "Hatch Restore 2 Sunrise Alarm & Sound Machine",
        "category": "Home Essentials",
        "brand": "Hatch",
        "price": 199.99,
        "specifications": {
            "mrp": 229.99,
            "discount_percent": 13,
            "review_count": 1850,
            "light": "Gentle custom sunrise light alarm",
            "sound": "White noise, pink noise, ocean soundscapes",
            "design": "Soft linen fabric cover in neutral aesthetics",
            "controls": "Top phone-free resting buttons",
        },
        "description": "Wake up gently to a gradual sunrise and wind down with soothing sleep sounds tailored for restorative circadian rest.",
        "image_url": "https://images.unsplash.com/photo-1507652313519-d4e9174996dd?auto=format&fit=crop&w=600&q=80",
        "rating": 4.8,
        "stock": 40,
    },
    {
        "name": "OXO Good Grips Pop Storage Container 5-Piece Set",
        "category": "Home Essentials",
        "brand": "OXO",
        "price": 54.99,
        "specifications": {
            "mrp": 64.99,
            "discount_percent": 15,
            "review_count": 3400,
            "seal": "Airtight push-button silicone pop seal",
            "material": "BPA-free crystal-clear durable plastic",
            "stackable": "Modular nesting design for neat pantries",
            "dishwasher": "Top-rack dishwasher safe",
        },
        "description": "Keep dry kitchen staples and snacks fresh with the push of a button. Modular stacking system saves cabinet space.",
        "image_url": "https://images.unsplash.com/photo-1584269600464-37b1b58a9fe7?auto=format&fit=crop&w=600&q=80",
        "rating": 4.9,
        "stock": 115,
    },
    {
        "name": "Zwilling Henckels Premium Microfiber Cleaning Cloth 8-Pack",
        "category": "Home Essentials",
        "brand": "Zwilling",
        "price": 19.99,
        "specifications": {
            "mrp": 25.99,
            "discount_percent": 23,
            "review_count": 2800,
            "count": "8 high-density dual-sided cloths",
            "absorption": "Absorbs up to 8x its weight in water",
            "safe": "Scratch-free on glass, displays, and lacquer",
            "reusable": "Machine washable over 300 cycles",
        },
        "description": "Ultra-soft non-abrasive microfiber wipes away grease, dust, and smudges without streaks or harsh chemical sprays.",
        "image_url": "https://images.unsplash.com/photo-1581578731548-c64695cc6952?auto=format&fit=crop&w=600&q=80",
        "rating": 4.7,
        "stock": 200,
    },

    # ------------------------------------------------------------------ #
    #  KITCHEN PRODUCTS (8 products)
    # ------------------------------------------------------------------ #
    {
        "name": "Fellow Stagg EKG Electric Pour-Over Gooseneck Kettle",
        "category": "Kitchen Products",
        "brand": "Fellow",
        "price": 165.00,
        "specifications": {
            "mrp": 195.00,
            "discount_percent": 15,
            "review_count": 2900,
            "capacity": "0.9 Liter",
            "control": "To-the-degree variable temperature dial",
            "spout": "Precision gooseneck pour control",
            "screen": "Discreet real-time LCD display screen",
            "hold": "60-minute temperature hold mode",
        },
        "description": "The pour-over kettle beloved by world barista champions, featuring precision pour spout and LCD temperature feedback.",
        "image_url": "https://images.unsplash.com/photo-1544787219-7f47ccb76574?auto=format&fit=crop&w=600&q=80",
        "rating": 4.9,
        "stock": 45,
    },
    {
        "name": "Nespresso VertuoPlus Deluxe Coffee and Espresso Machine",
        "category": "Kitchen Products",
        "brand": "Nespresso",
        "price": 169.00,
        "specifications": {
            "mrp": 199.00,
            "discount_percent": 15,
            "review_count": 4800,
            "tech": "Centrifusion barcode extraction technology",
            "sizes": "5 cup sizes from Espresso to Alto 14oz",
            "tank": "60oz multi-position movable water reservoir",
            "heat_up": "Ready in 20-25 seconds",
        },
        "description": "Brew freshly brewed coffee with rich crema at the touch of a button using barcode-reading precision extraction.",
        "image_url": "https://images.unsplash.com/photo-1517668808822-9ebb02f2a0e6?auto=format&fit=crop&w=600&q=80",
        "rating": 4.8,
        "stock": 60,
    },
    {
        "name": "Ninja Professional Plus Blender with Auto-iQ",
        "category": "Kitchen Products",
        "brand": "Ninja",
        "price": 99.99,
        "specifications": {
            "mrp": 119.99,
            "discount_percent": 17,
            "review_count": 8100,
            "power": "1400 Peak Watts heavy motor",
            "pitcher": "72oz Total Crushing Pitcher",
            "blades": "Stacked 6-blade stainless steel assembly",
            "programs": "3 Auto-iQ timed pulsing presets",
        },
        "description": "Crush whole fruits, vegetables, and ice in seconds with 1400 peak watts and intelligent one-touch automated programs.",
        "image_url": "https://images.unsplash.com/photo-1570222094114-d054a817e56b?auto=format&fit=crop&w=600&q=80",
        "rating": 4.7,
        "stock": 80,
    },
    {
        "name": "Cuisinart 14-Cup Custom Food Processor",
        "category": "Kitchen Products",
        "brand": "Cuisinart",
        "price": 249.95,
        "specifications": {
            "mrp": 299.95,
            "discount_percent": 17,
            "review_count": 2100,
            "motor": "720-Watt heavy-duty motor",
            "bowl": "14-Cup Lexan work bowl with handle",
            "discs": "Standard slicing disc, shredding disc, chopping blade",
            "feed_tube": "Extra-large feed tube holds whole potatoes",
        },
        "description": "An enduring kitchen workhorse ready to slice, shred, chop, and puree through meal prep in minutes.",
        "image_url": "https://images.unsplash.com/photo-1588854337236-6889d631faa8?auto=format&fit=crop&w=600&q=80",
        "rating": 4.8,
        "stock": 35,
    },
    {
        "name": "Wusthof Classic 8-Inch Chef Knife",
        "category": "Kitchen Products",
        "brand": "Wusthof",
        "price": 170.00,
        "specifications": {
            "mrp": 195.00,
            "discount_percent": 13,
            "review_count": 3100,
            "steel": "High-carbon stainless steel 58 HRC",
            "origin": "Precision forged in Solingen, Germany",
            "edge": "Precision Edge Technology (PEtec) 20% sharper",
            "handle": "Triple-riveted POM handle",
        },
        "description": "The quintessential all-rounder kitchen knife forged from high-carbon German steel with laser-tested sharpness.",
        "image_url": "https://images.unsplash.com/photo-1593618998160-e34014e67546?auto=format&fit=crop&w=600&q=80",
        "rating": 4.9,
        "stock": 40,
    },
    {
        "name": "John Boos Block Maple Wood Reversible Cutting Board",
        "category": "Kitchen Products",
        "brand": "John Boos",
        "price": 109.95,
        "specifications": {
            "mrp": 135.00,
            "discount_percent": 19,
            "review_count": 1400,
            "wood": "Sustainably harvested Northern Hard Rock Maple",
            "dimensions": "20 x 15 x 1.25 inches",
            "reversible": "Both sides flat for chopping versatility",
            "finish": "Natural Boos Block cream food-safe beeswax finish",
        },
        "description": "Handcrafted American maple heirloom butcher block designed to protect fine cutlery edges while prepping gourmet meals.",
        "image_url": "https://images.unsplash.com/photo-1590794056226-79ef3a8147e1?auto=format&fit=crop&w=600&q=80",
        "rating": 4.8,
        "stock": 50,
    },
    {
        "name": "Greater Goods Digital Food Kitchen Scale",
        "category": "Kitchen Products",
        "brand": "Greater Goods",
        "price": 14.99,
        "specifications": {
            "mrp": 19.99,
            "discount_percent": 25,
            "review_count": 9800,
            "accuracy": "Precise down to 1 gram (0.1 oz)",
            "capacity": "11 lbs (5 kg) maximum load",
            "features": "One-touch Tare auto-zero button",
            "display": "High-contrast backlit LCD screen",
        },
        "description": "Slim, high-precision digital food scale with smooth glass surface and intuitive zero-out tare function for calorie and baking balance.",
        "image_url": "https://images.unsplash.com/photo-1589782182703-2aaa69037b5b?auto=format&fit=crop&w=600&q=80",
        "rating": 4.7,
        "stock": 190,
    },
    {
        "name": "Instant Pot Duo 7-in-1 Electric Pressure Cooker 6-Qt",
        "category": "Kitchen Products",
        "brand": "Instant Pot",
        "price": 99.95,
        "specifications": {
            "mrp": 119.95,
            "discount_percent": 17,
            "review_count": 15400,
            "capacity": "6 Quarts (serves up to 6 people)",
            "functions": "Pressure cook, slow cook, rice, yogurt, steam, sauté, warm",
            "pot": "Food-grade 304 stainless steel inner pot",
            "safety": "Over 10 proven safety mechanisms",
        },
        "description": "Cook delicious one-pot meals up to 70% faster with 13 customizable Smart Programs for soup, beans, poultry, and desserts.",
        "image_url": "https://images.unsplash.com/photo-1544233726-9f1d2b27be8b?auto=format&fit=crop&w=600&q=80",
        "rating": 4.8,
        "stock": 110,
    },

    # ------------------------------------------------------------------ #
    #  PERSONAL CARE / BEAUTY (6 products)
    # ------------------------------------------------------------------ #
    {
        "name": "Philips Sonicare ProtectiveClean 6100 Electric Toothbrush",
        "category": "Personal Care",
        "brand": "Philips",
        "price": 129.96,
        "specifications": {
            "mrp": 149.96,
            "discount_percent": 13,
            "review_count": 4100,
            "motions": "Up to 62,000 brush movements/min",
            "modes": "Clean, White, Gum Care with 3 intensities",
            "sensor": "Pressure sensor alerts if pressing too hard",
            "battery": "2 weeks battery on single charge",
        },
        "description": "Removes up to 10x more plaque than a manual toothbrush while whitening teeth in just one week.",
        "image_url": "https://images.unsplash.com/photo-1559591937-e1032338fec3?auto=format&fit=crop&w=600&q=80",
        "rating": 4.8,
        "stock": 95,
    },
    {
        "name": "Braun Series 9 Pro Electric Foil Shaver",
        "category": "Personal Care",
        "brand": "Braun",
        "price": 299.99,
        "specifications": {
            "mrp": 349.99,
            "discount_percent": 14,
            "review_count": 1890,
            "head": "ProHead with 5 synchronized shaving elements",
            "sonic": "10,000 Sonic vibrations glide across skin",
            "case": "Includes SmartCare 5-in-1 cleaning center",
            "wet_dry": "100% waterproof for shower use",
        },
        "description": "Braun's most efficient electric razor engineered to tackle tough 1, 3, or 7-day beards with gentle precision.",
        "image_url": "https://images.unsplash.com/photo-1621607512214-68297480165e?auto=format&fit=crop&w=600&q=80",
        "rating": 4.7,
        "stock": 40,
    },
    {
        "name": "Dyson Supersonic Hair Dryer",
        "category": "Personal Care",
        "brand": "Dyson",
        "price": 429.99,
        "specifications": {
            "mrp": 469.99,
            "discount_percent": 9,
            "review_count": 3600,
            "motor": "Dyson digital motor V9 up to 110,000rpm",
            "heat": "Intelligent heat control prevents thermal damage",
            "attachments": "5 magnetic styling attachments including Flyaway tool",
            "weight": "Balanced in handle, not top-heavy",
        },
        "description": "Fast drying with no extreme heat. Engineered for different hair types to protect natural shine and eliminate frizz.",
        "image_url": "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?auto=format&fit=crop&w=600&q=80",
        "rating": 4.9,
        "stock": 30,
    },
    {
        "name": "CeraVe Hydrating Facial Cleanser 16 oz",
        "category": "Personal Care",
        "brand": "CeraVe",
        "price": 14.99,
        "specifications": {
            "mrp": 18.99,
            "discount_percent": 21,
            "review_count": 18900,
            "skin_type": "Normal to dry skin",
            "ceramides": "Formulated with 3 essential ceramides (1, 3, 6-II)",
            "hydration": "MVE Delivery Technology continuous moisture",
            "certification": "National Eczema Association accepted",
        },
        "description": "Non-foaming lotion cleanser that washes away dirt and oil while increasing skin hydration after just one use.",
        "image_url": "https://images.unsplash.com/photo-1556228720-195a672e8a03?auto=format&fit=crop&w=600&q=80",
        "rating": 4.8,
        "stock": 250,
    },
    {
        "name": "La Roche-Posay Anthelios Melt-in Milk Sunscreen SPF 60",
        "category": "Personal Care",
        "brand": "La Roche-Posay",
        "price": 27.99,
        "specifications": {
            "mrp": 32.99,
            "discount_percent": 15,
            "review_count": 6200,
            "spf": "Broad spectrum UVA/UVB SPF 60",
            "texture": "Fast-absorbing, non-greasy, velvety finish",
            "waterproof": "Water resistant for 80 minutes",
            "safe": "Oxybenzone-free, dermatologist tested",
        },
        "description": "Multi-award-winning sunscreen formulated with Cell-Ox Shield technology and powerful antioxidant protection.",
        "image_url": "https://images.unsplash.com/photo-1598440947619-2c35fc9aa908?auto=format&fit=crop&w=600&q=80",
        "rating": 4.8,
        "stock": 140,
    },
    {
        "name": "Neutrogena Hydro Boost Water Gel Moisturizer",
        "category": "Personal Care",
        "brand": "Neutrogena",
        "price": 19.97,
        "specifications": {
            "mrp": 24.99,
            "discount_percent": 20,
            "review_count": 11300,
            "ingredient": "Purified Hyaluronic Acid",
            "texture": "Ultra-lightweight oil-free water gel",
            "action": "Instantly quenches dry skin and keeps it smooth",
            "absorption": "Absorbs immediately without pore clogging",
        },
        "description": "Oil-free gel moisturizer that instantly absorbs like a gel with the long-lasting moisturizing power of a cream.",
        "image_url": "https://images.unsplash.com/photo-1571781926291-c477ebfd024b?auto=format&fit=crop&w=600&q=80",
        "rating": 4.7,
        "stock": 180,
    },

    # ------------------------------------------------------------------ #
    #  STATIONERY & BOOKS (5 products)
    # ------------------------------------------------------------------ #
    {
        "name": "Leuchtturm1917 Medium A5 Dotted Hardcover Notebook",
        "category": "Stationery",
        "brand": "Leuchtturm1917",
        "price": 24.99,
        "specifications": {
            "mrp": 29.99,
            "discount_percent": 17,
            "review_count": 3200,
            "pages": "251 numbered fountain-pen friendly pages",
            "paper": "80 gsm ink-proof acid-free paper",
            "features": "Table of contents, 2 bookmarks, expandable pocket",
            "binding": "Thread-bound opens completely flat 180 degrees",
        },
        "description": "The gold-standard journal for bullet journalers and thinkers, with numbered dot-grid pages and archival durability.",
        "image_url": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?auto=format&fit=crop&w=600&q=80",
        "rating": 4.9,
        "stock": 120,
    },
    {
        "name": "Pilot G2 Retractable Premium Gel Pens 12-Pack",
        "category": "Stationery",
        "brand": "Pilot",
        "price": 16.99,
        "specifications": {
            "mrp": 21.99,
            "discount_percent": 23,
            "review_count": 14200,
            "point": "0.7mm Fine Point roller ball",
            "ink": "Smooth-writing, smear-proof vibrant black gel ink",
            "grip": "Contoured rubber grip for writing comfort",
            "refillable": True,
        },
        "description": "America's go-to gel ink pen providing ultra-smooth skip-free writing and longest-writing ink formula.",
        "image_url": "https://images.unsplash.com/photo-1583485088034-697b5bc54ccd?auto=format&fit=crop&w=600&q=80",
        "rating": 4.8,
        "stock": 250,
    },
    {
        "name": "Maruman Mnemosyne A4 Executive Grid Desk Pad",
        "category": "Stationery",
        "brand": "Maruman",
        "price": 21.50,
        "specifications": {
            "mrp": 26.50,
            "discount_percent": 19,
            "review_count": 1150,
            "paper": "Japanese silky 80 gsm fountain pen paper",
            "layout": "5mm subtle light gray grid",
            "microperforated": True,
            "sheets": "70 sheets per spiral pad",
        },
        "description": "Manufactured in Japan for executive note-taking and wireframing, with zero feathering or bleed-through.",
        "image_url": "https://images.unsplash.com/photo-1517842645767-c639042777db?auto=format&fit=crop&w=600&q=80",
        "rating": 4.9,
        "stock": 70,
    },
    {
        "name": "Midori Brass Fountain Pen with Clip",
        "category": "Stationery",
        "brand": "Midori",
        "price": 58.00,
        "specifications": {
            "mrp": 68.00,
            "discount_percent": 15,
            "review_count": 820,
            "material": "Solid untreated brass develops unique patina",
            "nib": "Fine steel German nib",
            "cartridge": "Standard international short cartridges",
            "portability": "Pocket pen cap screws onto barrel to extend",
        },
        "description": "Compact brass pocket fountain pen from Japan that ages with a magnificent vintage brass patina with every journey.",
        "image_url": "https://images.unsplash.com/photo-1585336261026-77cc7c458e0a?auto=format&fit=crop&w=600&q=80",
        "rating": 4.8,
        "stock": 45,
    },
    {
        "name": "Mindspace Mesh Desktop Organizer with 6 Compartments",
        "category": "Stationery",
        "brand": "Mindspace",
        "price": 23.99,
        "specifications": {
            "mrp": 29.99,
            "discount_percent": 20,
            "review_count": 3600,
            "compartments": "6 divided sorting slots + pull-out drawer",
            "material": "Sturdy steel mesh with powder-coat finish",
            "feet": "Non-skid rubber feet protect desk finish",
        },
        "description": "Streamline office supplies, pens, notebooks, and sticky notes in one modern wire-mesh space-saving caddy.",
        "image_url": "https://images.unsplash.com/photo-1544717305-2782549b5136?auto=format&fit=crop&w=600&q=80",
        "rating": 4.7,
        "stock": 130,
    },

    # ------------------------------------------------------------------ #
    #  EVERYDAY CONSUMABLES / LIFESTYLE (5 products)
    # ------------------------------------------------------------------ #
    {
        "name": "Twinings Pure Green Tea Bags 100 Count",
        "category": "Everyday Consumables",
        "brand": "Twinings",
        "price": 14.99,
        "specifications": {
            "mrp": 19.99,
            "discount_percent": 25,
            "review_count": 8700,
            "count": "100 individually foil-sealed tea bags",
            "origin": "Steamed Chinese green tea leaves",
            "caffeine": "Naturally caffeinated mild uplift",
            "antioxidants": "High natural polyphenol content",
        },
        "description": "Smooth, refreshing taste with a golden hue made from gently steamed tea leaves for morning calm and clarity.",
        "image_url": "https://images.unsplash.com/photo-1576092768241-dec231879fc3?auto=format&fit=crop&w=600&q=80",
        "rating": 4.8,
        "stock": 300,
    },
    {
        "name": "Hydro Flask 32 oz Wide Mouth Insulated Water Bottle",
        "category": "Everyday Consumables",
        "brand": "Hydro Flask",
        "price": 49.95,
        "specifications": {
            "mrp": 54.95,
            "discount_percent": 9,
            "review_count": 9200,
            "insulation": "TempShield double-wall vacuum insulation",
            "cold_hot": "Cold for 24 hours, piping hot for 12 hours",
            "steel": "18/8 pro-grade stainless steel purity",
            "cap": "Leakproof Flex Cap with flexible strap",
        },
        "description": "Keeps beverages ice-cold all day with condensation-free powder coating and pure taste with zero flavor transfer.",
        "image_url": "https://images.unsplash.com/photo-1602143407151-7111542de6e8?auto=format&fit=crop&w=600&q=80",
        "rating": 4.9,
        "stock": 140,
    },
    {
        "name": "Larabar Gluten-Free Fruit & Nut Bars 16-Pack",
        "category": "Everyday Consumables",
        "brand": "Larabar",
        "price": 18.99,
        "specifications": {
            "mrp": 23.99,
            "discount_percent": 21,
            "review_count": 4200,
            "ingredients": "Only 3-6 whole food ingredients per bar",
            "diet": "Non-GMO, vegan, gluten-free, dairy-free",
            "flavor": "Peanut Butter Chocolate Chip & Cashew",
        },
        "description": "Wholesome real-food snack bars made with simple ingredients like dates, peanuts, and fair-trade chocolate.",
        "image_url": "https://images.unsplash.com/photo-1590080875515-8a3a8dc5735e?auto=format&fit=crop&w=600&q=80",
        "rating": 4.7,
        "stock": 190,
    },
    {
        "name": "Aesop Resurrection Aromatique Hand Wash 500ml",
        "category": "Everyday Consumables",
        "brand": "Aesop",
        "price": 43.00,
        "specifications": {
            "mrp": 48.00,
            "discount_percent": 10,
            "review_count": 2100,
            "botanicals": "Mandarin Rind, Rosemary Leaf, Cedar Atlas",
            "texture": "Clear gel with skin-softening gentle cleanse",
            "aroma": "Citrus, woody, herbaceous aroma",
        },
        "description": "Iconic gentle botanical hand wash with purifying extracts of orange, rosemary, and lavender to soften hands.",
        "image_url": "https://images.unsplash.com/photo-1608248597359-20ff9a6ef2f7?auto=format&fit=crop&w=600&q=80",
        "rating": 4.9,
        "stock": 80,
    },
    {
        "name": "Nature Made Vitamin C 1000mg with Rose Hips 100 Count",
        "category": "Everyday Consumables",
        "brand": "Nature Made",
        "price": 12.99,
        "specifications": {
            "mrp": 16.99,
            "discount_percent": 24,
            "review_count": 6400,
            "dosage": "1000mg Ascorbic Acid + Rose Hips",
            "count": "100 caplets (100 day supply)",
            "verification": "USP Verified dietary supplement",
            "benefit": "Immune defense and collagen synthesis support",
        },
        "description": "Supports immune health with pure Vitamin C and bioflavonoid rose hips. USP tested and verified for potency.",
        "image_url": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?auto=format&fit=crop&w=600&q=80",
        "rating": 4.8,
        "stock": 220,
    },
]


from data.catalog_generator import generate_large_catalog

def seed_products(clear_existing: bool = True) -> int:
    """
    Insert product catalog into database.
    Seeds the original 56 demo products (preserving IDs 1..56 for tests)
    plus 2,100+ generated products across 13 categories.
    Guarantees duplicate prevention and idempotency.
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Temporarily disable foreign keys during reseeding to preserve existing order history
        cursor.execute("PRAGMA foreign_keys = OFF")

        if clear_existing:
            cursor.execute("DELETE FROM products")
            try:
                cursor.execute("DELETE FROM sqlite_sequence WHERE name = 'products'")
            except Exception:
                pass

        # Existing keys for duplicate prevention
        cursor.execute("SELECT name, brand, source_id FROM products")
        existing_names = set()
        existing_source_ids = set()
        for row in cursor.fetchall():
            n = (row[0] or "").strip().lower()
            b = (row[1] or "").strip().lower()
            sid = (row[2] or "").strip()
            existing_names.add((n, b))
            if sid:
                existing_source_ids.add(sid)

        inserted = 0
        curr_id = 0

        # Step 1: Insert original 56 products with fixed IDs 1..56 if not present
        for idx, p in enumerate(PRODUCTS, start=1):
            key = (p["name"].strip().lower(), p["brand"].strip().lower())
            sid = f"PT-DEMO-{idx:04d}"
            if key in existing_names or sid in existing_source_ids:
                continue

            specs = p.get("specifications", {})
            mrp = float(specs.get("mrp", p["price"] * 1.2))
            disc = int(specs.get("discount_percent", round(((mrp - p["price"]) / mrp) * 100)))
            revs = int(specs.get("review_count", 120))
            specs_json = json.dumps(specs)
            ext_url = f"https://www.flipkart.com/search?q={p['name'].replace(' ', '+')}"

            cursor.execute(
                """
                INSERT INTO products (
                    id, name, category, subcategory, brand, price,
                    discount_percentage, specifications, description, image_url,
                    source_type, rating, review_count_demo, stock, featured,
                    source_id, external_url, availability, data_origin
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    idx,
                    p["name"],
                    p["category"],
                    p.get("subcategory", p["category"]),
                    p["brand"],
                    float(p["price"]),
                    disc,
                    specs_json,
                    p["description"],
                    p.get("image_url", ""),
                    "demo",
                    float(p.get("rating", 4.5)),
                    revs,
                    int(p.get("stock", 50)),
                    1 if idx % 5 == 0 else 0,
                    sid,
                    ext_url,
                    "in_stock",
                    "catalog"
                ),
            )
            existing_names.add(key)
            existing_source_ids.add(sid)
            inserted += 1
            curr_id = max(curr_id, idx)

        # Step 2: Insert generated 2,100+ products across all 13 categories
        catalog_items = generate_large_catalog()
        for p in catalog_items:
            key = (p["name"].strip().lower(), p["brand"].strip().lower())
            sid = p.get("source_id", "").strip()
            if key in existing_names or (sid and sid in existing_source_ids):
                # Duplicate prevention: skip duplicate product
                continue

            curr_id += 1
            specs_json = json.dumps(p.get("specifications", {}))

            cursor.execute(
                """
                INSERT INTO products (
                    id, name, category, subcategory, brand, price,
                    discount_percentage, specifications, description, image_url,
                    source_type, rating, review_count_demo, stock, featured,
                    source_id, external_url, availability, data_origin
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    curr_id,
                    p["name"],
                    p["category"],
                    p.get("subcategory", ""),
                    p["brand"],
                    float(p["price"]),
                    int(p.get("discount_percentage", 20)),
                    specs_json,
                    p.get("description", ""),
                    p.get("image_url", ""),
                    p.get("source_type", "pretwin_catalog"),
                    float(p.get("rating", 4.2)),
                    int(p.get("review_count_demo", 150)),
                    int(p.get("stock", 50)),
                    int(p.get("featured", 0)),
                    sid,
                    p.get("external_url", ""),
                    p.get("availability", "in_stock"),
                    p.get("data_origin", "catalog")
                ),
            )
            existing_names.add(key)
            if sid:
                existing_source_ids.add(sid)
            inserted += 1

        cursor.execute("PRAGMA foreign_keys = ON")
        conn.commit()
        print(f"[seed_products] Successfully populated {inserted} products (total in DB).")
        return inserted


if __name__ == "__main__":
    count = seed_products()
    print(f"Total seeded products: {count}")
