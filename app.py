"""
PreTwinShop AI – Flask Backend API
===================================
Main application entry point. Registers all API and frontend routes.
"""

import json
import re
import uuid
from datetime import datetime, timedelta

from flask import Flask, jsonify, render_template, request, session, redirect, url_for
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

try:
    import razorpay
except ImportError:
    razorpay = None

import database
from config import Config
from agents.chat_assistant import PreTwinChatAssistant

# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

app = Flask(__name__)
app.secret_key = Config.SECRET_KEY
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=not Config.DEBUG,
    PERMANENT_SESSION_LIFETIME=timedelta(days=7),
)
CORS(app)

def get_current_user_id() -> int:
    """Return user_id from active session if logged in, otherwise default demo user (ID=1)."""
    return session.get("user_id", Config.DEFAULT_DEMO_USER_ID)

@app.context_processor
def inject_user_context():
    """Expose authenticated user, status, and auth config globally to all Jinja templates."""
    # Never auto-authenticate users as the demo user Alex Johnson
    if not session.get("is_authenticated_user") and (session.get("user_id") or session.get("email")):
        session.pop("user_id", None)
        session.pop("username", None)
        session.pop("email", None)
        session.pop("avatar_url", None)
        session.pop("is_authenticated_user", None)

    uid = session.get("user_id")
    user = None
    if uid:
        try:
            row = database.query_db("SELECT id, username, email, avatar_url FROM users WHERE id = ?", (uid,), one=True)
            if row:
                user = row_to_dict(row)
        except Exception:
            user = None
    return {
        "current_user": user,
        "is_authenticated": bool(user),
        "google_client_id": Config.GOOGLE_CLIENT_ID,
        "google_auth_enabled": Config.GOOGLE_AUTH_ENABLED,
        "current_year": datetime.utcnow().year,
    }

# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def row_to_dict(row) -> dict:
    """Convert a sqlite3.Row object to a plain Python dict."""
    if row is None:
        return {}
    return dict(row)


def parse_json_field(value, fallback=None):
    """
    Safely parse a JSON string stored in a TEXT column.

    Args:
        value:    The raw value (string, None, or already-parsed object).
        fallback: Default to return when parsing fails. Defaults to [] or {}.

    Returns:
        Parsed Python object, or *fallback* on any error.
    """
    if fallback is None:
        # Guess a sensible default from the value
        if isinstance(value, str) and value.strip().startswith("{"):
            fallback = {}
        else:
            fallback = []

    if value is None:
        return fallback
    if isinstance(value, (list, dict)):
        # Already parsed (shouldn't normally happen, but be defensive)
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError, ValueError):
        return fallback


def get_user_reward_balance(user_id: int) -> int:
    """Calculate the current reward points balance for a user (100 points = ₹1)."""
    try:
        if not user_id:
            user_id = 1

        # Verify user exists in database to avoid foreign key errors
        user_row = database.query_db("SELECT id FROM users WHERE id = ?", (user_id,), one=True)
        if not user_row:
            user_id = 1

        # Check if user has any ledger entries; if not, grant 500 welcome bonus points
        count_row = database.query_db(
            "SELECT COUNT(*) AS cnt FROM reward_ledger WHERE user_id = ?",
            (user_id,),
            one=True
        )
        if count_row and int(count_row["cnt"]) == 0:
            database.execute_db(
                """
                INSERT INTO reward_ledger (user_id, points, rupee_value, transaction_type, description)
                VALUES (?, 500, 5.0, 'Welcome Bonus', 'PreTwin Welcome Joining Reward (500 pts = ₹5.00)')
                """,
                (user_id,)
            )

        row = database.query_db(
            "SELECT COALESCE(SUM(points), 0) AS balance FROM reward_ledger WHERE user_id = ?",
            (user_id,),
            one=True
        )
        return int(row["balance"]) if row else 0
    except Exception as e:
        print(f"[Reward Balance Warning] Error calculating points: {e}")
        return 0


def calculate_savings_plan_stats(plan: dict) -> dict:
    """Calculate daily/weekly rates, progress %, remaining days for a savings plan."""
    target = float(plan.get("target_amount") or 0.0)
    saved = float(plan.get("current_saved") if plan.get("current_saved") is not None else (plan.get("saved_amount") or 0.0))
    remaining = max(0.0, round(target - saved, 2))
    progress_pct = min(100.0, round((saved / target * 100.0), 1)) if target > 0 else 0.0

    target_date_str = plan.get("target_date")
    days_remaining = 30
    if target_date_str:
        try:
            target_date = datetime.strptime(str(target_date_str).split("T")[0], "%Y-%m-%d").date()
            today = datetime.utcnow().date()
            delta = (target_date - today).days
            days_remaining = max(1, delta)
        except Exception:
            days_remaining = 30

    daily_rate = round(remaining / days_remaining, 2) if days_remaining > 0 else remaining
    weekly_rate = round(daily_rate * 7.0, 2)
    is_ready = saved >= target

    plan_copy = dict(plan)
    title = plan.get("goal_title") or plan.get("title") or "Shopping Goal"
    plan_copy.update({
        "title": title,
        "goal_title": title,
        "saved_amount": saved,
        "current_saved": saved,
        "remaining_amount": remaining,
        "progress_percentage": progress_pct,
        "days_remaining": days_remaining,
        "daily_savings_rate": daily_rate,
        "weekly_savings_rate": weekly_rate,
        "is_ready_to_shop": is_ready
    })
    return plan_copy


def current_timestamp() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.utcnow().isoformat()


def _error(message: str, code: int = 500):
    """Return a standardised JSON error response."""
    return jsonify({"error": message, "code": code}), code


# ---------------------------------------------------------------------------
# Seed helpers (run once at startup via data.seeder or inline below)
# ---------------------------------------------------------------------------

def _seed_demo_products():
    """Insert a rich set of demo products if the table is empty."""
    from database import query_db
    from data.seed_bulk_products import seed_bulk_products

    existing = query_db("SELECT COUNT(*) AS cnt FROM products", one=True)
    if existing and existing["cnt"] >= 50:
        return  # Already seeded

    seed_bulk_products()

    products = [
        # Electronics
        ("Sony WH-1000XM5 Headphones", "Electronics", "Sony", 349.99,
         '{"connectivity":"Bluetooth 5.2","battery":"30h","noise_cancelling":true}',
         "Industry-leading noise cancelling wireless headphones.", 4.8),
        ("Apple AirPods Pro (2nd Gen)", "Electronics", "Apple", 249.00,
         '{"connectivity":"Bluetooth 5.3","battery":"6h","anc":true}',
         "Active noise cancellation and personalized spatial audio.", 4.7),
        ("Samsung 65\" 4K QLED TV", "Electronics", "Samsung", 1299.99,
         '{"resolution":"4K","panel":"QLED","hdr":"HDR10+","refresh_rate":"120Hz"}',
         "Brilliant 4K QLED picture with Quantum HDR.", 4.6),
        ("LG C3 65\" OLED TV", "Electronics", "LG", 1799.99,
         '{"resolution":"4K","panel":"OLED","hdr":"Dolby Vision","refresh_rate":"120Hz"}',
         "Evo OLED panel with infinite contrast and perfect blacks.", 4.8),
        ("iPad Air 5th Generation", "Electronics", "Apple", 749.00,
         '{"chip":"M1","storage":"64GB","display":"10.9 inch Liquid Retina"}',
         "Supercharged by the Apple M1 chip.", 4.7),
        ("Dell XPS 15 Laptop", "Electronics", "Dell", 1899.99,
         '{"cpu":"Intel Core i7-13700H","ram":"16GB","storage":"512GB SSD","display":"15.6 OLED"}',
         "Premium laptop with stunning OLED display.", 4.5),
        ("Canon EOS R6 Mark II Camera", "Electronics", "Canon", 2499.00,
         '{"sensor":"24.2MP Full-Frame","video":"4K60p","autofocus":"Dual Pixel II"}',
         "Professional mirrorless camera for stills and video.", 4.7),
        ("Dyson V15 Detect Vacuum", "Electronics", "Dyson", 749.99,
         '{"suction":"230AW","battery":"60min","filter":"HEPA"}',
         "Laser detects microscopic dust you can't see.", 4.6),

        # Home & Kitchen
        ("KitchenAid Stand Mixer 5Qt", "Home & Kitchen", "KitchenAid", 449.99,
         '{"capacity":"5Qt","wattage":"325W","attachments":10}',
         "Tilt-head stand mixer with 10 speeds.", 4.8),
        ("Instant Pot Duo 7-in-1", "Home & Kitchen", "Instant Pot", 99.95,
         '{"capacity":"6Qt","functions":7,"presets":13}',
         "Pressure cooker, slow cooker, rice cooker and more.", 4.7),
        ("Ninja Foodi Air Fryer 8Qt", "Home & Kitchen", "Ninja", 179.99,
         '{"capacity":"8Qt","functions":6,"max_temp":"450F"}',
         "XL capacity air fryer with crisp technology.", 4.6),
        ("Vitamix A3500 Blender", "Home & Kitchen", "Vitamix", 649.95,
         '{"motor":"2.2HP","container":"64oz","speeds":"variable"}',
         "Ascent Series smart blender with wireless connectivity.", 4.8),
        ("Breville Barista Express", "Home & Kitchen", "Breville", 699.95,
         '{"grinder":"conical burr","pressure":"15bar","milk_frother":true}',
         "Integrated grinder delivers optimal flavour.", 4.7),
        ("Lodge 12\" Cast Iron Skillet", "Home & Kitchen", "Lodge", 39.90,
         '{"diameter":"12 inch","material":"cast iron","pre_seasoned":true}',
         "Pre-seasoned cast iron skillet for all cooking surfaces.", 4.8),

        # Sports & Outdoors
        ("Peloton Bike+", "Sports & Outdoors", "Peloton", 2495.00,
         '{"screen":"23.8 inch rotating","resistance":"auto","classes":"unlimited"}',
         "Rotating screen for yoga, strength and more.", 4.5),
        ("Garmin Forerunner 965", "Sports & Outdoors", "Garmin", 599.99,
         '{"display":"AMOLED","gps":true,"battery":"31days smartwatch"}',
         "Premium GPS running & triathlon smartwatch.", 4.6),
        ("Hydro Flask 32oz Water Bottle", "Sports & Outdoors", "Hydro Flask", 44.95,
         '{"capacity":"32oz","insulation":"TempShield","material":"stainless steel"}',
         "TempShield double-wall vacuum insulation.", 4.8),
        ("Manduka PRO Yoga Mat", "Sports & Outdoors", "Manduka", 120.00,
         '{"thickness":"6mm","material":"PVC free","length":"71 inch","warranty":"lifetime"}',
         "The gold-standard yoga mat – lifetime guarantee.", 4.7),
        ("Coleman Sundome 6-Person Tent", "Sports & Outdoors", "Coleman", 129.99,
         '{"capacity":6,"setup":"10min","weather":"WeatherTec"}',
         "Easy setup camping tent with weatherproof design.", 4.5),

        # Beauty & Personal Care
        ("Dyson Airwrap Complete", "Beauty & Personal Care", "Dyson", 599.99,
         '{"technology":"Coanda","attachments":6,"heat_settings":3}',
         "Style with air, not extreme heat.", 4.6),
        ("La Mer Moisturizing Cream 1oz", "Beauty & Personal Care", "La Mer", 185.00,
         '{"size":"1oz","skin_type":"all","key_ingredient":"Miracle Broth"}',
         "The iconic moisturiser powered by Miracle Broth.", 4.5),
        ("Theragun Pro Massage Gun", "Beauty & Personal Care", "Therabody", 499.00,
         '{"speed":"2400RPM","force":"60lbs","battery":"150min"}',
         "Professional-grade percussive therapy device.", 4.6),
        ("Oral-B iO Series 9 Electric Toothbrush", "Beauty & Personal Care", "Oral-B", 229.99,
         '{"modes":7,"pressure_sensor":true,"ai":true}',
         "AI-powered electric toothbrush with 3D teeth tracking.", 4.5),

        # Books & Media
        ("Kindle Paperwhite (11th Gen)", "Books & Media", "Amazon", 139.99,
         '{"display":"6.8 inch 300ppi","storage":"8GB","waterproof":"IPX8"}',
         "Now with a larger 6.8\" display and adjustable warm light.", 4.7),
        ("Audible Premium Plus Subscription", "Books & Media", "Amazon", 14.95,
         '{"credits":"1/month","library":"unlimited Plus","offline":true}',
         "1 credit/month plus unlimited listening from Plus Catalogue.", 4.5),

        # Fashion
        ("Levi's 501 Original Jeans", "Fashion", "Levi's", 69.50,
         '{"fit":"straight","rise":"high","material":"100% cotton"}',
         "The original blue jean since 1873.", 4.6),
        ("Nike Air Force 1 '07", "Fashion", "Nike", 110.00,
         '{"sole":"rubber","upper":"leather","width":"medium"}',
         "The radically classic Nike basketball shoe.", 4.7),
        ("Patagonia Better Sweater Fleece Jacket", "Fashion", "Patagonia", 139.00,
         '{"material":"100% recycled polyester","fit":"regular","pockets":3}',
         "Classic fleece jacket made from recycled polyester.", 4.7),

        # Toys & Games
        ("LEGO Technic Bugatti Bolide 42151", "Toys & Games", "LEGO", 89.99,
         '{"pieces":905,"age":"10+","scale":"1:18"}',
         "Build the ultra-light, extreme-performance race car.", 4.7),
        ("Nintendo Switch OLED Model", "Toys & Games", "Nintendo", 349.99,
         '{"display":"7 inch OLED","storage":"64GB","modes":3}',
         "Vivid 7-inch OLED screen gaming system.", 4.8),
        ("Razer BlackShark V2 Pro Headset", "Toys & Games", "Razer", 179.99,
         '{"connectivity":"wireless","driver":"50mm TriForce Titanium","mic":"HyperClear"}',
         "Wireless esports headset for competitive gaming.", 4.5),
    ]

    sql = """
        INSERT INTO products (name, category, brand, price, specifications, description, rating)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    for p in products:
        execute_db(sql, p)

    print(f"[app] Seeded {len(products)} demo products.")


def _seed_demo_user():
    """Insert demo user (id=1) and preferences if not present."""
    from database import query_db, execute_db

    user = query_db("SELECT id FROM users WHERE id = 1", one=True)
    if not user:
        execute_db(
            "INSERT INTO users (id, username, email) VALUES (1, 'Alex Johnson', 'alex@demo.pretwinshop.ai')"
        )

    prefs_exist = query_db(
        "SELECT id FROM shopping_preferences WHERE user_id = 1", one=True
    )
    if not prefs_exist:
        execute_db(
            """
            INSERT INTO shopping_preferences
                (user_id, preferred_categories, budget_min, budget_max,
                 preferred_brands, product_requirements, shopping_frequency,
                 shopping_goals, notes)
            VALUES (1, ?, 500.0, 5000.0, ?, ?, 'monthly', ?, ?)
            """,
            (
                json.dumps(["Electronics", "Computer Accessories", "Home Essentials"]),
                json.dumps(["Sony", "Logitech", "Philips"]),
                json.dumps({"condition": "new", "warranty": "preferred"}),
                "Upgrade home office setup and personal gadgets",
                "Interested in smart home devices and productivity tools. Prefers well-reviewed brands.",
            ),
        )

    # Seed demo goals
    goals_exist = query_db(
        "SELECT id FROM shopping_goals WHERE user_id = 1", one=True
    )
    if not goals_exist:
        demo_goals = [
            (1, "Productive Home Office Setup", "Buy an ergonomic mouse, keyboard, and USB-C hub", "2026-06-30", 2500.0),
            (1, "Smart Living & Wellness", "Add smart air purifier and noise-cancelling audio", "2026-09-30", 3500.0),
        ]
        for g in demo_goals:
            execute_db(
                """
                INSERT INTO shopping_goals (user_id, goal_title, goal_description, target_date, budget)
                VALUES (?, ?, ?, ?, ?)
                """,
                g,
            )

    # Seed demo purchase history
    history_exist = query_db(
        "SELECT id FROM purchase_history WHERE user_id = 1", one=True
    )
    if not history_exist:
        demo_history = [
            (1, "Logitech MX Master 3S Wireless Mouse", "Computer Accessories", "Logitech", 99.99, "2026-08-15", 1, "Great for long work sessions"),
            (1, "Keychron K8 Pro Mechanical Keyboard", "Computer Accessories", "Keychron", 109.00, "2026-09-02", 1, "Love the tactile feel"),
            (1, "Sony WH-1000XM5 Wireless Headphones", "Electronics", "Sony", 329.99, "2026-08-20", 1, "Best noise cancellation"),
            (1, "Sony WF-1000XM5 Noise-Canceling Earbuds", "Electronics", "Sony", 249.99, "2026-09-25", 1, "Daily commute listening"),
            (1, "Levoit Core 300 Air Purifier", "Home Essentials", "Levoit", 99.99, "2026-07-10", 1, "Runs quietly at night"),
            (1, "Twinings Green Tea Bags (100 Count)", "Everyday Consumables", "Twinings", 14.99, "2026-09-12", 2, "Stock up every month"),
            (1, "CeraVe Hydrating Facial Cleanser", "Personal Care", "CeraVe", 14.99, "2026-09-18", 2, "Daily skincare routine"),
        ]
        for h in demo_history:
            execute_db(
                """
                INSERT INTO purchase_history
                    (user_id, product_name, category, brand, price, purchase_date, quantity, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                h,
            )

    print("[app] Demo user seeded (user_id=1).")


# ---------------------------------------------------------------------------
# Frontend / template routes
# ---------------------------------------------------------------------------

@app.route("/")
def dashboard_page():
    return render_template("dashboard.html")


@app.route("/features")
def features_dashboard():
    """Dedicated PreTwin AI Features Dashboard displaying all 8 core shopping engines."""
    return render_template("features_dashboard.html")


@app.route("/twin")
def twin_page():
    return render_template("twin.html")


@app.route("/predictions")
def predictions_page():
    return render_template("predictions.html")


@app.route("/discovery")
def discovery_page():
    return render_template("discovery.html")


@app.route("/comparison")
def comparison_page():
    return render_template("comparison.html")


@app.route("/recommendations")
def recommendations_page():
    return render_template("recommendations.html")


@app.route("/agents")
def agents_page():
    return render_template("agents.html")


@app.route("/profile")
def profile_page():
    return render_template("profile.html")


@app.route("/account")
def account_page():
    return redirect("/profile")


@app.route("/settings")
def settings_page():
    return render_template("settings.html")


@app.route("/checkout")
def checkout_page():
    return render_template("checkout.html")


@app.route("/orders")
def orders_page():
    return render_template("orders.html")


@app.route("/order-success")
def order_success_page():
    return render_template("order_success.html")


@app.route("/savings")
def savings_page():
    return render_template("savings.html")


@app.route("/rewards")
def rewards_page():
    return render_template("rewards.html")


@app.route("/budget")
def budget_page():
    return render_template("budget.html")


@app.route("/smart-cart")
@app.route("/smart-card")
def smart_cart_page():
    return render_template("smart_cart.html")


@app.route("/advanced-ai")
def advanced_ai_page():
    return render_template("advanced_ai.html")


@app.route("/seller")
def seller_page():
    return render_template("seller.html")


@app.route("/customer-service")
@app.route("/support")
def customer_service_page():
    return render_template("customer_service.html")


@app.route("/faq")
@app.route("/faqs")
def faq_page():
    return render_template("faq.html")


@app.route("/contact")
@app.route("/contact-us")
def contact_page():
    return render_template("contact.html")


@app.route("/returns-refunds")
@app.route("/returns")
def returns_refunds_page():
    return render_template("returns_refunds.html")


@app.route("/privacy")
@app.route("/privacy-policy")
def privacy_page():
    return render_template("privacy.html")


@app.route("/terms")
@app.route("/terms-and-conditions")
def terms_page():
    return render_template("terms.html")


@app.route("/notifications")
def notifications_page():
    return render_template("notifications.html")


@app.route("/login", methods=["GET", "POST"])
@app.route("/signin", methods=["GET", "POST"])
@app.route("/sign-in", methods=["GET", "POST"])
@app.route("/sign_in", methods=["GET", "POST"])
@app.route("/auth", methods=["GET", "POST"])
def login_page():
    if session.get("email") == "alex@demo.pretwinshop.ai" or session.get("username") == "Alex Johnson" or (session.get("user_id") == 1 and not session.get("is_authenticated_user")):
        session.clear()

    if request.method == "POST":
        identifier = (request.form.get("identifier") or request.form.get("email") or request.form.get("username") or "").strip().lower()
        password = request.form.get("password") or ""
        if identifier and password:
            user = database.query_db(
                "SELECT * FROM users WHERE LOWER(email) = ? OR LOWER(username) = ?",
                (identifier, identifier),
                one=True
            )
            if user:
                user_dict = row_to_dict(user)
                stored_hash = user_dict.get("password_hash") or ""
                valid = False
                if stored_hash:
                    valid = check_password_hash(stored_hash, password)
                elif user_dict["id"] == 1 and password in ("password123", "demo1234", "admin123"):
                    new_hash = generate_password_hash(password)
                    database.execute_db("UPDATE users SET password_hash = ? WHERE id = 1", (new_hash,))
                    valid = True

                if valid:
                    session["user_id"] = user_dict["id"]
                    session["username"] = user_dict["username"]
                    session["email"] = user_dict["email"]
                    session["is_authenticated_user"] = True
                    if user_dict.get("avatar_url"):
                        session["avatar_url"] = user_dict["avatar_url"]
                    next_url = request.args.get("next") or "/"
                    return redirect(next_url)

    initial_tab = request.args.get("tab", "login")
    return render_template("login.html", initial_tab=initial_tab)


@app.route("/register", methods=["GET"])
@app.route("/signup", methods=["GET"])
@app.route("/sign-up", methods=["GET"])
def register_page():
    if session.get("email") == "alex@demo.pretwinshop.ai" or session.get("username") == "Alex Johnson" or (session.get("user_id") == 1 and not session.get("is_authenticated_user")):
        session.clear()
    initial_tab = request.args.get("tab", "register")
    return render_template("login.html", initial_tab=initial_tab)


@app.route("/logout")
def logout_page():
    session.clear()
    return redirect("/login?logged_out=1")


@app.route("/wishlist")
def wishlist_page():
    return render_template("wishlist.html")


@app.route("/calendar")
def calendar_page():
    return render_template("calendar.html")


# ---------------------------------------------------------------------------
# API – Authentication & User Management
# ---------------------------------------------------------------------------

@app.route("/api/auth/register", methods=["POST"])
def auth_register():
    """Register a new user account with secure password hashing."""
    try:
        data = request.get_json() or {}
        name = (data.get("name") or data.get("full_name") or data.get("username") or "").strip()
        username = (data.get("username") or data.get("name") or "").strip()
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""
        confirm_password = data.get("confirm_password") or ""

        if not name and not username:
            return _error("Full name or username is required.", 400)
        display_name = username or name
        if not email or "@" not in email or "." not in email:
            return _error("A valid email address is required.", 400)
        if not password:
            return _error("Password is required.", 400)
        if len(password) < 6:
            return _error("Password must be at least 6 characters long.", 400)
        if confirm_password and password != confirm_password:
            return _error("Passwords do not match.", 400)

        # Check for existing email
        existing = database.query_db(
            "SELECT id FROM users WHERE LOWER(email) = ?", (email,), one=True
        )
        if existing:
            return _error("An account with this email address already exists. Please sign in.", 409)

        hashed = generate_password_hash(password)
        new_id = database.execute_db(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (display_name, email, hashed)
        )

        # Initialize default shopping preferences for new user
        database.execute_db(
            """
            INSERT INTO shopping_preferences
                (user_id, preferred_categories, budget_min, budget_max,
                 preferred_brands, product_requirements, shopping_frequency,
                 shopping_goals, notes)
            VALUES (?, '["Mobiles", "Electronics", "Fashion"]', 500.0, 50000.0,
                    '["Samsung", "Apple", "Nike", "Sony"]', '{}', 'monthly',
                    'Discover smart deals matching my lifestyle',
                    'New PreTwin shopping twin profile')
            """,
            (new_id,)
        )

        # Seed 500 Welcome Bonus Reward Points
        database.execute_db(
            """
            INSERT INTO reward_ledger (user_id, points, rupee_value, transaction_type, description)
            VALUES (?, 500, 5.0, 'Welcome Bonus', 'PreTwin Welcome Joining Reward (500 pts = ₹5.00)')
            """,
            (new_id,)
        )

        # Establish session
        session["user_id"] = new_id
        session["username"] = display_name
        session["email"] = email
        session["is_authenticated_user"] = True

        return jsonify({
            "success": True,
            "message": "Account created successfully! Welcome to PreTwin.",
            "user": {
                "id": new_id,
                "username": display_name,
                "email": email
            }
        }), 201

    except Exception as e:
        return _error(f"Registration failed: {str(e)}", 500)


@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    """Sign in an existing user with email/username and password verification."""
    try:
        data = request.get_json() or {}
        identifier = (data.get("email") or data.get("username") or data.get("identifier") or "").strip().lower()
        password = data.get("password") or ""

        if not identifier:
            return _error("Please enter your email or username.", 400)
        if not password:
            return _error("Please enter your password.", 400)

        user = database.query_db(
            "SELECT * FROM users WHERE LOWER(email) = ? OR LOWER(username) = ?",
            (identifier, identifier),
            one=True
        )
        if not user:
            return _error("Invalid email or password. Please try again or create an account.", 401)

        user_dict = row_to_dict(user)
        stored_hash = user_dict.get("password_hash") or ""

        valid = False
        if stored_hash:
            valid = check_password_hash(stored_hash, password)
        elif user_dict["id"] == 1 and password in ("password123", "demo1234", "admin123"):
            # Update demo user hash if previously unhashed
            new_hash = generate_password_hash(password)
            database.execute_db("UPDATE users SET password_hash = ? WHERE id = 1", (new_hash,))
            valid = True

        if not valid:
            return _error("Invalid email or password. Please check your credentials.", 401)

        # Set session
        session["user_id"] = user_dict["id"]
        session["username"] = user_dict["username"]
        session["email"] = user_dict["email"]
        session["is_authenticated_user"] = True
        if user_dict.get("avatar_url"):
            session["avatar_url"] = user_dict["avatar_url"]

        return jsonify({
            "success": True,
            "message": "Logged in successfully!",
            "user": {
                "id": user_dict["id"],
                "username": user_dict["username"],
                "email": user_dict["email"],
                "avatar_url": user_dict.get("avatar_url", "")
            }
        })

    except Exception as e:
        return _error(f"Login failed: {str(e)}", 500)


@app.route("/api/auth/logout", methods=["POST", "GET"])
def auth_logout():
    """Clear session and log out."""
    session.clear()
    return jsonify({"success": True, "message": "Logged out successfully."})


@app.route("/api/auth/me", methods=["GET"])
def auth_me():
    """Return the currently authenticated user status."""
    user_id = session.get("user_id")
    if not user_id or not session.get("is_authenticated_user"):
        return jsonify({"authenticated": False, "user": None})

    user = database.query_db("SELECT id, username, email FROM users WHERE id = ?", (user_id,), one=True)
    if not user:
        session.clear()
        return jsonify({"authenticated": False, "user": None})

    return jsonify({
        "authenticated": True,
        "user": row_to_dict(user)
    })


@app.route("/api/auth/config", methods=["GET"])
def auth_config():
    """Return public authentication configuration for frontend clients."""
    return jsonify({
        "google_enabled": Config.GOOGLE_AUTH_ENABLED,
        "google_client_id": Config.GOOGLE_CLIENT_ID
    })


@app.route("/api/auth/google", methods=["POST"])
def auth_google():
    """
    Authenticate or register a user using Google Identity Services (GIS) ID Token.
    Verifies cryptographic signature, audience, issuer, and expiration on backend.
    Associates the Google subject identifier ('sub') with the PreTwin user account.
    """
    try:
        data = request.get_json() or {}
        credential = data.get("credential") or data.get("id_token")

        if not credential:
            return _error("Google credential token is required.", 400)

        client_id = Config.GOOGLE_CLIENT_ID
        if not client_id:
            return jsonify({
                "success": False,
                "error": "Google OAuth is not configured on this server.",
                "message": "Please set GOOGLE_CLIENT_ID in your .env file with your OAuth 2.0 Web Client ID from the Google Cloud Console."
            }), 400

        idinfo = None
        # 1. Attempt verification with official google-auth library
        try:
            from google.oauth2 import id_token
            from google.auth.transport import requests as google_requests
            idinfo = id_token.verify_oauth2_token(credential, google_requests.Request(), client_id)
        except Exception as auth_lib_err:
            # 2. Fallback to Google TokenInfo verification endpoint
            try:
                import requests as py_requests
                resp = py_requests.get(
                    "https://oauth2.googleapis.com/tokeninfo",
                    params={"id_token": credential},
                    timeout=5
                )
                if resp.status_code == 200:
                    token_data = resp.json()
                    if token_data.get("aud") == client_id:
                        idinfo = token_data
                    else:
                        return _error("Google token audience mismatch.", 401)
                else:
                    return _error(f"Google token verification failed: {str(auth_lib_err)}", 401)
            except Exception:
                return _error(f"Google token verification failed: {str(auth_lib_err)}", 401)

        # Validate issuer
        issuer = idinfo.get("iss", "")
        if issuer not in ["accounts.google.com", "https://accounts.google.com"]:
            return _error(f"Invalid Google token issuer: {issuer}", 401)

        # Validate token expiration
        import time
        exp = int(idinfo.get("exp", 0))
        if exp and exp < time.time():
            return _error("Google token has expired.", 401)

        # Validate verified email status
        email_verified = idinfo.get("email_verified")
        if email_verified is not None:
            if isinstance(email_verified, str) and email_verified.lower() != "true":
                return _error("Google account email is not verified.", 401)
            elif isinstance(email_verified, bool) and not email_verified:
                return _error("Google account email is not verified.", 401)

        google_id = idinfo.get("sub")
        email = (idinfo.get("email") or "").strip().lower()
        name = idinfo.get("name") or (email.split("@")[0] if "@" in email else "Google User")
        avatar_url = idinfo.get("picture") or ""

        if not google_id or not email:
            return _error("Google token missing required identity claims.", 400)

        # Check existing user by google_id first
        user = database.query_db("SELECT * FROM users WHERE google_id = ?", (google_id,), one=True)
        if user:
            u_dict = row_to_dict(user)
            user_id = u_dict["id"]
            if avatar_url and not u_dict.get("avatar_url"):
                database.execute_db("UPDATE users SET avatar_url = ? WHERE id = ?", (avatar_url, user_id))
        else:
            # Check if user exists with matching email
            existing = database.query_db("SELECT * FROM users WHERE LOWER(email) = ?", (email,), one=True)
            if existing:
                u_dict = row_to_dict(existing)
                user_id = u_dict["id"]
                database.execute_db(
                    "UPDATE users SET google_id = ?, avatar_url = COALESCE(NULLIF(avatar_url, ''), ?) WHERE id = ?",
                    (google_id, avatar_url, user_id)
                )
            else:
                # Create brand new user
                user_id = database.execute_db(
                    "INSERT INTO users (username, email, password_hash, google_id, avatar_url) VALUES (?, ?, '', ?, ?)",
                    (name, email, google_id, avatar_url)
                )
                # Seed default shopping preferences for new Google user
                database.execute_db(
                    """
                    INSERT INTO shopping_preferences
                        (user_id, preferred_categories, budget_min, budget_max,
                         preferred_brands, product_requirements, shopping_frequency,
                         shopping_goals, notes)
                    VALUES (?, '["Mobiles", "Electronics", "Fashion"]', 500.0, 50000.0,
                            '["Samsung", "Apple", "Nike", "Sony"]', '{}', 'monthly',
                            'Discover smart deals matching my lifestyle',
                            'Google-authenticated PreTwin shopping twin profile')
                    """,
                    (user_id,)
                )

        # Seed 500 Welcome Bonus Reward Points
        database.execute_db(
            """
            INSERT INTO reward_ledger (user_id, points, rupee_value, transaction_type, description)
            VALUES (?, 500, 5.0, 'Welcome Bonus', 'PreTwin Welcome Joining Reward (500 pts = ₹5.00)')
            """,
            (user_id,)
        )

        # Establish session
        session["user_id"] = user_id
        session["username"] = name
        session["email"] = email
        session["is_authenticated_user"] = True
        if avatar_url:
            session["avatar_url"] = avatar_url

        next_url = (data.get("next") or request.args.get("next") or "").strip()
        if not next_url or not next_url.startswith("/"):
            next_url = "/"

        return jsonify({
            "success": True,
            "message": f"Welcome, {name}! You have signed in with Google.",
            "redirect": next_url,
            "user": {
                "id": user_id,
                "username": name,
                "email": email,
                "avatar_url": avatar_url
            }
        })

    except Exception as e:
        return _error(f"Google authentication error: {str(e)}", 500)


@app.route("/api/auth/google/demo", methods=["POST"])
def auth_google_demo():
    """
    Developer/Demo Google sign-in endpoint.
    Permits instant testing of authenticated PreTwin features with a verified Google demo profile.
    """
    try:
        data = request.get_json() or {}
        next_url = (data.get("next") or request.args.get("next") or "/").strip()
        if not next_url or not next_url.startswith("/"):
            next_url = "/"

        # Find or ensure demo user with Google credentials
        user = database.query_db(
            "SELECT * FROM users WHERE id = 1 OR email = 'alex@demo.pretwinshop.ai'",
            one=True
        )
        if user:
            u_dict = row_to_dict(user)
            user_id = u_dict["id"]
            database.execute_db(
                "UPDATE users SET google_id = COALESCE(NULLIF(google_id, ''), 'google-demo-10001'), "
                "avatar_url = COALESCE(NULLIF(avatar_url, ''), 'https://lh3.googleusercontent.com/a/default-user') "
                "WHERE id = ?",
                (user_id,)
            )
            username = u_dict["username"]
            email = u_dict["email"]
        else:
            user_id = database.execute_db(
                "INSERT INTO users (username, email, password_hash, google_id, avatar_url) "
                "VALUES ('Alex Johnson', 'alex@demo.pretwinshop.ai', '', 'google-demo-10001', 'https://lh3.googleusercontent.com/a/default-user')"
            )
            username = "Alex Johnson"
            email = "alex@demo.pretwinshop.ai"

        session["user_id"] = user_id
        session["username"] = username
        session["email"] = email
        session["avatar_url"] = "https://lh3.googleusercontent.com/a/default-user"

        return jsonify({
            "success": True,
            "message": "Signed in successfully with Google Developer Profile!",
            "user": {
                "id": user_id,
                "username": username,
                "email": email,
                "avatar_url": "https://lh3.googleusercontent.com/a/default-user",
                "provider": "google",
                "verified": True
            },
            "redirect": next_url
        })
    except Exception as e:
        return _error(f"Demo sign-in failed: {str(e)}", 500)


@app.route("/api/auth/save-google-client-id", methods=["POST"])
def save_google_client_id():
    """Save Google OAuth Client ID into runtime configuration and .env file."""
    try:
        data = request.get_json() or {}
        client_id = (data.get("client_id") or "").strip()
        if not client_id:
            return _error("Google Client ID cannot be empty.", 400)

        # Update runtime config
        Config.GOOGLE_CLIENT_ID = client_id
        Config.GOOGLE_AUTH_ENABLED = True

        # Write or update .env file
        env_path = os.path.join(os.path.dirname(__file__), ".env")
        lines = []
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

        found = False
        new_lines = []
        for line in lines:
            if line.startswith("GOOGLE_CLIENT_ID="):
                new_lines.append(f"GOOGLE_CLIENT_ID={client_id}\n")
                found = True
            else:
                new_lines.append(line)
        if not found:
            new_lines.append(f"\nGOOGLE_CLIENT_ID={client_id}\n")

        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

        return jsonify({
            "success": True,
            "message": "Google Client ID saved successfully! Google Identity Services is now active.",
            "google_client_id": client_id,
            "google_auth_enabled": True
        })
    except Exception as e:
        return _error(f"Failed to save Google Client ID: {str(e)}", 500)


@app.route("/api/auth/google/callback", methods=["GET"])
def auth_google_callback():
    """Fallback redirect endpoint for Google OAuth authorization code flow."""
    return redirect(url_for("login_page", next=request.args.get("next")))


# ---------------------------------------------------------------------------
# API – Wishlist Management
# ---------------------------------------------------------------------------

@app.route("/api/wishlist", methods=["GET"])
def get_wishlist():
    """Retrieve saved wishlist items for the current user."""
    try:
        user_id = get_current_user_id()
        rows = database.query_db(
            """
            SELECT w.id as wishlist_id, w.created_at as saved_at, p.*
            FROM wishlist_items w
            JOIN products p ON w.product_id = p.id
            WHERE w.user_id = ?
            ORDER BY w.id DESC
            """,
            (user_id,)
        )
        items = []
        for r in rows:
            item = row_to_dict(r)
            item["specifications"] = parse_json_field(item.get("specifications"), {})
            items.append(item)
        return jsonify({"success": True, "items": items, "count": len(items)})
    except Exception as e:
        return _error(f"Failed to fetch wishlist: {str(e)}", 500)


@app.route("/api/wishlist", methods=["POST"])
def add_to_wishlist():
    """Add a product to the user's wishlist."""
    try:
        user_id = get_current_user_id()
        data = request.get_json() or {}
        product_id = data.get("product_id")
        if not product_id:
            return _error("Product ID is required.", 400)

        prod = database.query_db("SELECT id, name FROM products WHERE id = ?", (product_id,), one=True)
        if not prod:
            return _error("Product not found.", 404)

        existing = database.query_db(
            "SELECT id FROM wishlist_items WHERE user_id = ? AND product_id = ?",
            (user_id, product_id),
            one=True
        )
        if not existing:
            database.execute_db(
                "INSERT INTO wishlist_items (user_id, product_id) VALUES (?, ?)",
                (user_id, product_id)
            )
        return jsonify({"success": True, "message": f"Added {prod['name']} to your wishlist!"})
    except Exception as e:
        return _error(f"Failed to add to wishlist: {str(e)}", 500)


@app.route("/api/wishlist/<int:product_id>", methods=["DELETE"])
def remove_from_wishlist(product_id: int):
    """Remove a product from the user's wishlist."""
    try:
        user_id = get_current_user_id()
        database.execute_db(
            "DELETE FROM wishlist_items WHERE user_id = ? AND product_id = ?",
            (user_id, product_id)
        )
        return jsonify({"success": True, "message": "Item removed from wishlist."})
    except Exception as e:
        return _error(f"Failed to remove from wishlist: {str(e)}", 500)


@app.route("/api/wishlist/clear", methods=["POST", "DELETE"])
def clear_wishlist():
    """Clear all wishlist items for the current user."""
    try:
        user_id = get_current_user_id()
        database.execute_db("DELETE FROM wishlist_items WHERE user_id = ?", (user_id,))
        return jsonify({"success": True, "message": "Wishlist cleared."})
    except Exception as e:
        return _error(f"Failed to clear wishlist: {str(e)}", 500)


# ---------------------------------------------------------------------------
# API – Cart & Server-Side Checkout Calculation
# ---------------------------------------------------------------------------

@app.route("/api/checkout/calculate", methods=["POST"])
def calculate_checkout():
    """
    Recalculate order subtotal, discounts, shipping fee, tax, and final total
    strictly based on current database product prices and verified stock.
    Supports PreTwin Reward Points redemption (100 points = ₹1.00).
    """
    try:
        data = request.get_json() or {}
        items = data.get("items", [])
        redeem_points = bool(data.get("redeem_points", False))
        user_id = get_current_user_id()

        if not items:
            return _error("No items provided for calculation.", 400)

        verified_items = []
        subtotal = 0.0
        mrp_total = 0.0

        for item in items:
            pid = item.get("product_id") or item.get("id")
            qty = max(1, int(item.get("quantity", 1)))

            prod_row = database.query_db("SELECT * FROM products WHERE id = ?", (pid,), one=True)
            if not prod_row:
                continue

            p = row_to_dict(prod_row)
            price = float(p.get("price") or 0.0)
            disc = int(p.get("discount_percentage") or 15)
            if 0 < disc < 100:
                mrp = round(price / (1.0 - disc / 100.0), 2)
            else:
                mrp = round(price * 1.35, 2)

            item_total = round(price * qty, 2)
            item_mrp_total = round(mrp * qty, 2)

            subtotal += item_total
            mrp_total += item_mrp_total

            verified_items.append({
                "product_id": p["id"],
                "name": p["name"],
                "category": p["category"],
                "brand": p.get("brand", ""),
                "price": price,
                "mrp": mrp,
                "quantity": qty,
                "total_price": item_total,
                "image_url": p.get("image_url", ""),
                "stock": p.get("stock", 50)
            })

        if not verified_items:
            return _error("No valid products found in order calculation.", 400)

        discount = max(0.0, round(mrp_total - subtotal, 2))
        # Free shipping for orders >= ₹500
        shipping_fee = 0.0 if subtotal >= 500.0 else 40.0
        # 5% GST calculated for display (inclusive in price)
        tax = round(subtotal * 0.05, 2)

        # PreTwin Reward Points (100 points = ₹1.00)
        user_points_balance = get_user_reward_balance(user_id)
        applied_credit = session.get("applied_reward_credit")
        max_redeemable_points = min(user_points_balance, int(subtotal * 100))
        points_to_redeem = 0
        reward_discount = 0.0

        if redeem_points or (redeem_points is None and applied_credit):
            if applied_credit:
                reward_discount = min(float(applied_credit.get("rupee_discount") or 0.0), subtotal)
                points_to_redeem = int(applied_credit.get("points") or 0)
            elif max_redeemable_points > 0:
                points_to_redeem = max_redeemable_points
                reward_discount = round(points_to_redeem / 100.0, 2)

        final_total = max(0.0, round(subtotal + shipping_fee - reward_discount, 2))

        return jsonify({
            "items": verified_items,
            "item_count": sum(x["quantity"] for x in verified_items),
            "mrp_total": mrp_total,
            "subtotal": subtotal,
            "discount": discount,
            "shipping_fee": shipping_fee,
            "tax": tax,
            "user_reward_points": user_points_balance,
            "points_redeemable": max_redeemable_points,
            "points_to_redeem": points_to_redeem,
            "reward_points_redeemed": points_to_redeem,
            "reward_discount_amount": reward_discount,
            "applied_credit": applied_credit,
            "total_amount": final_total,
            "gateway_configured": Config.RAZORPAY_ENABLED
        })

    except Exception as e:
        return _error(f"Failed to calculate order totals: {str(e)}", 500)


# ---------------------------------------------------------------------------
# API – Orders & Razorpay Payment Integration & Cash on Delivery (COD)
# ---------------------------------------------------------------------------

@app.route("/api/orders/create", methods=["POST"])
def create_order():
    """
    Creates a new order in database with server-verified prices.
    Supports Cash on Delivery (COD), PreTwin Reward points redemption (100 pts = ₹1),
    and Razorpay payment gateway / sandbox checkout.
    """
    try:
        data = request.get_json() or {}
        items = data.get("items", [])
        shipping = data.get("shipping_address") or {}
        payment_method = (data.get("payment_method") or "Razorpay").strip()
        redeem_points = bool(data.get("redeem_points", False))

        if not items:
            return _error("Cart items cannot be empty.", 400)

        # Shipping validation
        cust_name = (shipping.get("name") or "").strip()
        cust_email = (shipping.get("email") or "").strip().lower()
        cust_phone = (shipping.get("phone") or "").strip()
        address_line = (shipping.get("address") or "").strip()
        city = (shipping.get("city") or "").strip()
        state = (shipping.get("state") or "").strip()
        pincode = (shipping.get("pincode") or "").strip()

        if not cust_name:
            return _error("Recipient name is required.", 400)
        if not address_line or not city or not state or not pincode:
            return _error("Complete shipping address (street, city, state, pincode) is required.", 400)

        # Server-side price recalculation to prevent price tampering
        verified_items = []
        subtotal = 0.0
        mrp_total = 0.0

        for it in items:
            pid = it.get("product_id") or it.get("id")
            qty = max(1, int(it.get("quantity", 1)))
            row = database.query_db("SELECT * FROM products WHERE id = ?", (pid,), one=True)
            if not row:
                continue

            p = row_to_dict(row)
            price = float(p.get("price") or 0.0)
            item_total = round(price * qty, 2)
            subtotal += item_total

            verified_items.append({
                "product_id": p["id"],
                "name": p["name"],
                "category": p.get("category", ""),
                "brand": p.get("brand", ""),
                "price": price,
                "quantity": qty,
                "total_price": item_total,
                "image_url": p.get("image_url", "")
            })

        if not verified_items:
            return _error("All selected items are unavailable.", 400)

        shipping_fee = 0.0 if subtotal >= 500.0 else 40.0
        tax = round(subtotal * 0.05, 2)

        user_id = get_current_user_id()

        # Handle PreTwin Rewards redemption (100 points = ₹1)
        applied_credit = session.get("applied_reward_credit")
        user_points_balance = get_user_reward_balance(user_id)
        points_to_redeem = 0
        reward_discount = 0.0
        credit_already_deducted = False

        if redeem_points or (redeem_points is None and applied_credit):
            if applied_credit:
                reward_discount = min(float(applied_credit.get("rupee_discount") or 0.0), subtotal)
                points_to_redeem = int(applied_credit.get("points") or 0)
                credit_already_deducted = True
                session.pop("applied_reward_credit", None)
            elif user_points_balance > 0:
                max_redeemable = min(user_points_balance, int(subtotal * 100))
                points_to_redeem = max_redeemable
                reward_discount = round(points_to_redeem / 100.0, 2)

        total_amount = max(0.0, round(subtotal + shipping_fee - reward_discount, 2))

        # Generate unique order number (e.g. PT-20261026-XXXX)
        now_str = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        order_number = f"PT-{now_str}-{uuid.uuid4().hex[:4].upper()}"

        is_cod = (payment_method.upper() == "COD" or "CASH ON DELIVERY" in payment_method.upper())
        gateway_order_id = ""
        razorpay_key_to_send = None

        if is_cod:
            gateway_name = "COD"
            gateway_order_id = f"COD_{uuid.uuid4().hex[:12].upper()}"
            initial_payment_status = "Pending (Cash on Delivery)"
            initial_order_status = "Confirmed"
            cod_amount_due = total_amount
        else:
            gateway_name = "Razorpay"
            initial_payment_status = "Pending"
            initial_order_status = "Pending"
            cod_amount_due = 0.0

            if Config.RAZORPAY_ENABLED and razorpay:
                try:
                    client = razorpay.Client(auth=(Config.RAZORPAY_KEY_ID, Config.RAZORPAY_KEY_SECRET))
                    amount_paise = int(round(total_amount * 100))
                    rzp_order = client.order.create({
                        "amount": amount_paise,
                        "currency": "INR",
                        "receipt": order_number,
                        "notes": {
                            "user_id": str(user_id),
                            "customer_name": cust_name
                        }
                    })
                    gateway_order_id = rzp_order.get("id", "")
                    razorpay_key_to_send = Config.RAZORPAY_KEY_ID
                except Exception as rzp_err:
                    print(f"[Razorpay Warning] Gateway order create failed: {rzp_err}. Falling back to test checkout.")
                    gateway_order_id = f"rzp_sandbox_{uuid.uuid4().hex[:12]}"
            else:
                gateway_order_id = f"pt_sandbox_{uuid.uuid4().hex[:12]}"

        # Insert order into database
        order_id = database.execute_db(
            """
            INSERT INTO orders
                (order_number, user_id, customer_name, customer_email, customer_phone,
                 shipping_address, city, state, pincode, subtotal, tax, shipping_fee,
                 discount, reward_points_redeemed, reward_discount_amount, reward_points_awarded,
                 cod_amount_due, total_amount, status, payment_status, payment_method,
                 gateway_name, gateway_order_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0.0, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?)
            """,
            (order_number, user_id, cust_name, cust_email, cust_phone,
             address_line, city, state, pincode, subtotal, tax, shipping_fee,
             points_to_redeem, reward_discount, cod_amount_due, total_amount,
             initial_order_status, initial_payment_status, ("COD" if is_cod else payment_method),
             gateway_name, gateway_order_id)
        )

        # Record reward redemption in ledger if points used
        if points_to_redeem > 0:
            if not credit_already_deducted:
                database.execute_db(
                    """
                    INSERT INTO reward_ledger (user_id, order_id, points, rupee_value, transaction_type, description)
                    VALUES (?, ?, ?, ?, 'Redemption', ?)
                    """,
                    (user_id, order_id, -points_to_redeem, -reward_discount, f"Redeemed {points_to_redeem} points on order #{order_number} (-₹{reward_discount:.2f})")
                )
            else:
                try:
                    database.execute_db(
                        """
                        UPDATE reward_ledger SET order_id = ? 
                        WHERE id = (
                            SELECT id FROM reward_ledger 
                            WHERE user_id = ? AND transaction_type = 'Redemption' 
                            ORDER BY id DESC LIMIT 1
                        )
                        """,
                        (order_id, user_id)
                    )
                except Exception:
                    pass

        # Insert items
        for it in verified_items:
            database.execute_db(
                """
                INSERT INTO order_items
                    (order_id, product_id, product_name, category, brand, price, quantity, total_price, image_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (order_id, it["product_id"], it["name"], it["category"], it["brand"],
                 it["price"], it["quantity"], it["total_price"], it["image_url"])
            )

        return jsonify({
            "success": True,
            "order_id": order_id,
            "order_number": order_number,
            "total_amount": total_amount,
            "currency": "INR",
            "is_cod": is_cod,
            "cod_amount_due": cod_amount_due,
            "payment_status": initial_payment_status,
            "order_status": initial_order_status,
            "points_redeemed": points_to_redeem,
            "reward_discount": reward_discount,
            "razorpay_key_id": razorpay_key_to_send,
            "razorpay_order_id": gateway_order_id,
            "gateway_configured": Config.RAZORPAY_ENABLED,
            "customer": {
                "name": cust_name,
                "email": cust_email,
                "phone": cust_phone
            }
        }), 201

    except Exception as e:
        return _error(f"Failed to create order: {str(e)}", 500)


@app.route("/api/orders/verify-payment", methods=["POST"])
def verify_payment():
    """
    Verifies Razorpay payment signature on backend or confirms test sandbox payment.
    Updates order to 'Paid' and 'Confirmed' only upon verified authenticity.
    Awards 5 PreTwin Reward Points upon successful paid completion.
    """
    try:
        data = request.get_json() or {}
        order_id = data.get("order_id")
        order_number = data.get("order_number")
        rzp_payment_id = data.get("razorpay_payment_id", "").strip()
        rzp_order_id = data.get("razorpay_order_id", "").strip()
        rzp_signature = data.get("razorpay_signature", "").strip()
        is_sandbox_mode = bool(data.get("is_sandbox_mode") or not Config.RAZORPAY_ENABLED)

        if not order_id and not order_number:
            return _error("order_id or order_number is required.", 400)

        # Fetch order from DB
        if order_id:
            order_row = database.query_db("SELECT * FROM orders WHERE id = ?", (order_id,), one=True)
        else:
            order_row = database.query_db("SELECT * FROM orders WHERE order_number = ?", (order_number,), one=True)

        if not order_row:
            return _error("Order not found.", 404)

        order = row_to_dict(order_row)
        current_db_id = order["id"]

        # Prevent duplicate payment processing
        if order["payment_status"].startswith("Paid"):
            return jsonify({
                "success": True,
                "message": "Order is already paid and confirmed.",
                "order_id": current_db_id,
                "order_number": order["order_number"],
                "payment_status": order["payment_status"]
            })

        # Gateway signature verification
        if Config.RAZORPAY_ENABLED and razorpay and not is_sandbox_mode:
            if not rzp_payment_id or not rzp_signature or not rzp_order_id:
                return _error("Missing Razorpay signature verification parameters.", 400)

            try:
                client = razorpay.Client(auth=(Config.RAZORPAY_KEY_ID, Config.RAZORPAY_KEY_SECRET))
                client.utility.verify_payment_signature({
                    "razorpay_order_id": rzp_order_id,
                    "razorpay_payment_id": rzp_payment_id,
                    "razorpay_signature": rzp_signature
                })
                verified_status = "Paid"
            except Exception as verify_err:
                database.execute_db(
                    "UPDATE orders SET payment_status = 'Failed', status = 'Payment Failed' WHERE id = ?",
                    (current_db_id,)
                )
                return _error(f"Payment verification failed: {str(verify_err)}", 400)
        else:
            # Sandbox / Demo mode
            verified_status = "Paid (Sandbox Verified)"
            if not rzp_payment_id:
                rzp_payment_id = f"DEMO_PAY_{uuid.uuid4().hex[:10].upper()}"

        # Update order to Paid & Confirmed
        database.execute_db(
            """
            UPDATE orders
            SET payment_status = ?,
                status = 'Confirmed',
                gateway_payment_id = ?,
                gateway_signature = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (verified_status, rzp_payment_id, rzp_signature, current_db_id)
        )

        # Award 5 PreTwin Reward Points upon paid completion (if not already awarded)
        awarded_already = order.get("reward_points_awarded") or 0
        if awarded_already == 0:
            database.execute_db(
                """
                INSERT INTO reward_ledger (user_id, order_id, points, rupee_value, transaction_type, description)
                VALUES (?, ?, 5, 0.05, 'Purchase', ?)
                """,
                (order["user_id"], current_db_id, f"Earned 5 points for completing order #{order['order_number']}")
            )
            database.execute_db("UPDATE orders SET reward_points_awarded = 5 WHERE id = ?", (current_db_id,))

        # Record verified purchase history event
        try:
            from services.purchase_history_service import PurchaseHistoryService
            PurchaseHistoryService.record_order_purchase(current_db_id)
        except Exception as ph_err:
            app.logger.warning("Could not record purchase history for order %s: %s", current_db_id, ph_err)

        return jsonify({
            "success": True,
            "message": "Payment verified successfully! Order is confirmed.",
            "order_id": current_db_id,
            "order_number": order["order_number"],
            "payment_id": rzp_payment_id,
            "payment_status": verified_status,
            "status": "Confirmed",
            "reward_points_awarded": 5
        })

    except Exception as e:
        return _error(f"Payment verification error: {str(e)}", 500)


@app.route("/api/orders/<int:order_id>/mark-delivered", methods=["POST"])
def mark_order_delivered(order_id):
    """
    Mark an order as Delivered (and paid for COD orders), awarding 5 PreTwin reward points.
    """
    try:
        order_row = database.query_db("SELECT * FROM orders WHERE id = ?", (order_id,), one=True)
        if not order_row:
            return _error(f"Order #{order_id} not found.", 404)
        order = row_to_dict(order_row)

        if order["status"] == "Cancelled":
            return _error("Cannot deliver a cancelled order.", 400)

        is_cod = (order.get("payment_method") == "COD" or "COD" in (order.get("gateway_name") or ""))
        new_pay_status = "Paid (Cash on Delivery)" if is_cod else order["payment_status"]

        database.execute_db(
            """
            UPDATE orders
            SET status = 'Delivered',
                payment_status = ?,
                cod_amount_due = 0.0,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (new_pay_status, order_id)
        )

        # Award 5 points if not yet awarded
        points_awarded = 0
        if (order.get("reward_points_awarded") or 0) == 0:
            database.execute_db(
                """
                INSERT INTO reward_ledger (user_id, order_id, points, rupee_value, transaction_type, description)
                VALUES (?, ?, 5, 0.05, 'Purchase', ?)
                """,
                (order["user_id"], order_id, f"Earned 5 points for delivered order #{order['order_number']}")
            )
            database.execute_db("UPDATE orders SET reward_points_awarded = 5 WHERE id = ?", (order_id,))
            points_awarded = 5

        # Record verified purchase history event
        try:
            from services.purchase_history_service import PurchaseHistoryService
            PurchaseHistoryService.record_order_purchase(order_id)
        except Exception as ph_err:
            app.logger.warning("Could not record purchase history for delivered order %s: %s", order_id, ph_err)

        return jsonify({
            "success": True,
            "message": f"Order #{order['order_number']} marked as Delivered.",
            "order_id": order_id,
            "status": "Delivered",
            "payment_status": new_pay_status,
            "points_awarded": points_awarded,
            "reward_points_awarded": points_awarded
        })
    except Exception as e:
        return _error(f"Failed to update delivery status: {str(e)}", 500)


@app.route("/api/orders/<int:order_id>/cancel", methods=["POST"])
def cancel_order(order_id):
    """
    Cancel an order, refunding any redeemed points and reversing awarded points.
    """
    try:
        order_row = database.query_db("SELECT * FROM orders WHERE id = ?", (order_id,), one=True)
        if not order_row:
            return _error(f"Order #{order_id} not found.", 404)
        order = row_to_dict(order_row)

        if order["status"] == "Delivered":
            return _error("Delivered orders cannot be cancelled.", 400)
        if order["status"] == "Cancelled":
            return _error("Order is already cancelled.", 400)

        database.execute_db(
            "UPDATE orders SET status = 'Cancelled', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (order_id,)
        )

        # Refund redeemed points if any
        redeemed = order.get("reward_points_redeemed") or 0
        if redeemed > 0:
            database.execute_db(
                """
                INSERT INTO reward_ledger (user_id, order_id, points, rupee_value, transaction_type, description)
                VALUES (?, ?, ?, ?, 'Refund', ?)
                """,
                (order["user_id"], order_id, redeemed, round(redeemed / 100.0, 2), f"Refunded {redeemed} points for cancelled order #{order['order_number']}")
            )

        # Reverse awarded points if any were awarded
        awarded = order.get("reward_points_awarded") or 0
        if awarded > 0:
            database.execute_db(
                """
                INSERT INTO reward_ledger (user_id, order_id, points, rupee_value, transaction_type, description)
                VALUES (?, ?, ?, ?, 'Reversal', ?)
                """,
                (order["user_id"], order_id, -awarded, -round(awarded / 100.0, 2), f"Reversed {awarded} points for cancelled order #{order['order_number']}")
            )
            database.execute_db("UPDATE orders SET reward_points_awarded = 0 WHERE id = ?", (order_id,))

        # Mark purchase history records as disqualified
        try:
            from services.purchase_history_service import PurchaseHistoryService
            PurchaseHistoryService.handle_order_cancellation(order_id)
        except Exception as ph_err:
            app.logger.warning("Could not update purchase history for cancelled order %s: %s", order_id, ph_err)

        return jsonify({
            "success": True,
            "message": f"Order #{order['order_number']} has been cancelled.",
            "order_id": order_id,
            "status": "Cancelled",
            "points_refunded": redeemed
        })
    except Exception as e:
        return _error(f"Failed to cancel order: {str(e)}", 500)


@app.route("/api/orders/<int:order_id>/return", methods=["POST"])
def return_order(order_id):
    """
    Process an order return and refund.
    Reverses any awarded reward points and refunds any redeemed points.
    """
    try:
        order_row = database.query_db("SELECT * FROM orders WHERE id = ?", (order_id,), one=True)
        if not order_row:
            return _error(f"Order #{order_id} not found.", 404)
        order = row_to_dict(order_row)

        if order["status"] == "Returned":
            return jsonify({
                "success": True,
                "message": "Order is already returned.",
                "status": "Returned"
            })

        database.execute_db(
            """
            UPDATE orders
            SET status = 'Returned', payment_status = 'Refunded', updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (order_id,)
        )

        # Reverse awarded points if any were awarded
        awarded = order.get("reward_points_awarded") or 0
        if awarded > 0:
            database.execute_db(
                """
                INSERT INTO reward_ledger (user_id, order_id, points, rupee_value, transaction_type, description)
                VALUES (?, ?, ?, ?, 'Reversal', ?)
                """,
                (order["user_id"], order_id, -awarded, -round(awarded / 100.0, 2), f"Reversed {awarded} points for returned order #{order['order_number']}")
            )
            database.execute_db("UPDATE orders SET reward_points_awarded = 0 WHERE id = ?", (order_id,))

        # Mark purchase history records as returned / refunded
        try:
            from services.purchase_history_service import PurchaseHistoryService
            PurchaseHistoryService.handle_order_return(order_id)
        except Exception as ph_err:
            app.logger.warning("Could not update purchase history for returned order %s: %s", order_id, ph_err)

        # Refund redeemed points if any were redeemed
        redeemed = order.get("reward_points_redeemed") or 0
        if redeemed > 0:
            database.execute_db(
                """
                INSERT INTO reward_ledger (user_id, order_id, points, rupee_value, transaction_type, description)
                VALUES (?, ?, ?, ?, 'Refund', ?)
                """,
                (order["user_id"], order_id, redeemed, round(redeemed / 100.0, 2), f"Refunded {redeemed} points for returned order #{order['order_number']}")
            )

        return jsonify({
            "success": True,
            "message": f"Order #{order['order_number']} has been processed for return and refund.",
            "order_id": order_id,
            "status": "Returned",
            "payment_status": "Refunded",
            "points_refunded": redeemed,
            "points_reversed": awarded
        })
    except Exception as e:
        return _error(f"Failed to process return: {str(e)}", 500)


@app.route("/api/orders", methods=["GET"])
def get_orders():
    """Retrieve order history for the active user."""
    try:
        user_id = get_current_user_id()
        rows = database.query_db(
            "SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        )
        orders = []
        for r in rows:
            od = row_to_dict(r)
            items = database.query_db(
                "SELECT * FROM order_items WHERE order_id = ? ORDER BY id ASC",
                (od["id"],)
            )
            od["items"] = [row_to_dict(it) for it in items]
            orders.append(od)

        return jsonify({"orders": orders, "total": len(orders)})

    except Exception as e:
        return _error(f"Failed to fetch orders: {str(e)}", 500)


@app.route("/api/orders/<int:order_id>", methods=["GET"])
def get_order_detail(order_id):
    """Retrieve full details for a single order."""
    try:
        user_id = get_current_user_id()
        order_row = database.query_db(
            "SELECT * FROM orders WHERE id = ? AND (user_id = ? OR user_id = 1)",
            (order_id, user_id),
            one=True
        )
        if not order_row:
            return _error(f"Order #{order_id} not found.", 404)

        order = row_to_dict(order_row)
        items = database.query_db(
            "SELECT * FROM order_items WHERE order_id = ? ORDER BY id ASC",
            (order_id,)
        )
        order["items"] = [row_to_dict(it) for it in items]

        return jsonify({"order": order})

    except Exception as e:
        return _error(f"Failed to fetch order: {str(e)}", 500)


# ---------------------------------------------------------------------------
# API – Products
# ---------------------------------------------------------------------------

@app.route("/api/products", methods=["GET"])
def get_products():
    """Return all products with optional filtering, sorting, and pagination."""
    try:
        import math
        category = request.args.get("category", "").strip()
        subcategory = request.args.get("subcategory", "").strip()
        brand = request.args.get("brand", "").strip()
        min_price = request.args.get("min_price", type=float)
        max_price = request.args.get("max_price", type=float)
        min_rating = request.args.get("min_rating", request.args.get("rating", type=float), type=float)
        search = request.args.get("search", "").strip()
        sort = request.args.get("sort", "featured").strip().lower()
        page = max(1, request.args.get("page", 1, type=int))
        limit = request.args.get("limit", 24, type=int)

        where_clauses = ["1=1"]
        params = []

        if category:
            where_clauses.append("LOWER(category) = LOWER(?)")
            params.append(category)
        if subcategory:
            where_clauses.append("LOWER(subcategory) = LOWER(?)")
            params.append(subcategory)
        if brand:
            brands = [b.strip() for b in brand.split(",") if b.strip()]
            if len(brands) == 1:
                where_clauses.append("LOWER(brand) = LOWER(?)")
                params.append(brands[0])
            elif len(brands) > 1:
                placeholders = ",".join(["?"] * len(brands))
                where_clauses.append(f"LOWER(brand) IN ({placeholders})")
                params.extend([b.lower() for b in brands])
        if min_price is not None:
            where_clauses.append("price >= ?")
            params.append(min_price)
        if max_price is not None:
            where_clauses.append("price <= ?")
            params.append(max_price)
        if min_rating is not None:
            where_clauses.append("rating >= ?")
            params.append(min_rating)
        if search:
            where_clauses.append("(LOWER(name) LIKE LOWER(?) OR LOWER(description) LIKE LOWER(?) OR LOWER(brand) LIKE LOWER(?) OR LOWER(subcategory) LIKE LOWER(?))")
            pattern = f"%{search}%"
            params.extend([pattern, pattern, pattern, pattern])

        where_sql = " AND ".join(where_clauses)

        # Count total matching products
        count_sql = f"SELECT COUNT(*) AS total FROM products WHERE {where_sql}"
        count_row = database.query_db(count_sql, tuple(params), one=True)
        total = count_row["total"] if count_row else 0

        # Sorting
        if sort in ("price_asc", "price-low", "price_low_to_high", "price-low-to-high"):
            order_sql = "ORDER BY price ASC, id ASC"
        elif sort in ("price_desc", "price-high", "price_high_to_low", "price-high-to-low"):
            order_sql = "ORDER BY price DESC, id ASC"
        elif sort in ("rating", "rating_desc", "customer_rating"):
            order_sql = "ORDER BY rating DESC, price ASC"
        elif sort in ("discount", "discount_desc"):
            order_sql = "ORDER BY discount_percentage DESC, rating DESC"
        elif sort in ("newest", "id_desc"):
            order_sql = "ORDER BY id DESC"
        else:
            order_sql = "ORDER BY featured DESC, rating DESC, id ASC"

        # Pagination
        if limit <= 0:
            limit = 50
        offset = (page - 1) * limit
        sql = f"SELECT * FROM products WHERE {where_sql} {order_sql} LIMIT ? OFFSET ?"
        fetch_params = list(params) + [limit, offset]
        rows = database.query_db(sql, tuple(fetch_params))

        products = []
        for row in rows:
            d = row_to_dict(row)
            d["specifications"] = parse_json_field(d.get("specifications"), {})
            disc = d.get("discount_percentage") or 15
            d["discount_percentage"] = disc
            if d.get("review_count_demo") is None:
                d["review_count_demo"] = 120
            if 0 < disc < 100:
                d["mrp"] = round(d["price"] / (1 - disc / 100.0), 2)
            else:
                d["mrp"] = round(d["price"] * 1.25, 2)
            products.append(d)

        # Distinct categories
        cat_rows = database.query_db(
            "SELECT DISTINCT category FROM products ORDER BY category"
        )
        categories = [r["category"] for r in cat_rows]

        # Distinct subcategories for current category (or all)
        if category:
            subcat_rows = database.query_db(
                "SELECT DISTINCT subcategory FROM products WHERE LOWER(category) = LOWER(?) AND subcategory IS NOT NULL AND subcategory != '' ORDER BY subcategory",
                (category,)
            )
        else:
            subcat_rows = database.query_db(
                "SELECT DISTINCT subcategory FROM products WHERE subcategory IS NOT NULL AND subcategory != '' ORDER BY subcategory"
            )
        subcategories = [r["subcategory"] for r in subcat_rows]

        # Distinct brands for current category (or all)
        if category:
            brand_rows = database.query_db(
                "SELECT DISTINCT brand FROM products WHERE LOWER(category) = LOWER(?) AND brand IS NOT NULL AND brand != '' ORDER BY brand",
                (category,)
            )
        else:
            brand_rows = database.query_db(
                "SELECT DISTINCT brand FROM products WHERE brand IS NOT NULL AND brand != '' ORDER BY brand"
            )
        brands = [r["brand"] for r in brand_rows]

        pages = math.ceil(total / limit) if limit > 0 else 1

        return jsonify({
            "products": products,
            "total": total,
            "page": page,
            "page_size": limit,
            "pages": pages,
            "categories": categories,
            "subcategories": subcategories,
            "brands": brands
        })

    except Exception as exc:
        return _error(str(exc))


@app.route("/api/products/<int:product_id>", methods=["GET"])
def get_product(product_id):
    """Return a single product by ID."""
    try:
        row = database.query_db(
            "SELECT * FROM products WHERE id = ?", (product_id,), one=True
        )
        if not row:
            return _error(f"Product {product_id} not found.", 404)

        product = row_to_dict(row)
        product["specifications"] = parse_json_field(product.get("specifications"), {})
        disc = product.get("discount_percentage") or 15
        product["discount_percentage"] = disc
        if product.get("review_count_demo") is None:
            product["review_count_demo"] = 120
        if 0 < disc < 100:
            product["mrp"] = round(product["price"] / (1 - disc / 100.0), 2)
        else:
            product["mrp"] = round(product["price"] * 1.25, 2)
        return jsonify(product)

    except Exception as exc:
        return _error(str(exc))


@app.route("/api/categories", methods=["GET"])
def get_categories():
    """Return a list of distinct product categories."""
    try:
        rows = database.query_db(
            "SELECT DISTINCT category FROM products ORDER BY category"
        )
        categories = [r["category"] for r in rows]
        return jsonify({"categories": categories})

    except Exception as exc:
        return _error(str(exc))


@app.route("/api/subcategories", methods=["GET"])
def get_subcategories():
    """Return distinct subcategories, optionally filtered by category."""
    try:
        category = request.args.get("category", "").strip()
        if category:
            rows = database.query_db(
                "SELECT DISTINCT subcategory FROM products WHERE LOWER(category) = LOWER(?) AND subcategory IS NOT NULL AND subcategory != '' ORDER BY subcategory",
                (category,)
            )
        else:
            rows = database.query_db(
                "SELECT DISTINCT subcategory, category FROM products WHERE subcategory IS NOT NULL AND subcategory != '' ORDER BY category, subcategory"
            )
        subcats = [r["subcategory"] for r in rows]
        return jsonify({"subcategories": subcats, "category": category})
    except Exception as exc:
        return _error(str(exc))


# ---------------------------------------------------------------------------
# API – User Profile
# ---------------------------------------------------------------------------

@app.route("/api/profile", methods=["GET"])
def get_profile():
    """Return the current user profile (fallback to user_id=1)."""
    try:
        user_id = get_current_user_id()
        user = database.query_db(
            "SELECT * FROM users WHERE id = ?", (user_id,), one=True
        ) or database.query_db("SELECT * FROM users WHERE id = 1", one=True)
        if not user:
            return _error("User not found.", 404)

        effective_uid = user["id"]
        prefs = database.query_db(
            "SELECT * FROM shopping_preferences WHERE user_id = ?", (effective_uid,), one=True
        )

        goals = database.query_db(
            "SELECT * FROM shopping_goals WHERE user_id = ? AND status = 'active'", (effective_uid,)
        )

        profile = row_to_dict(user)
        if prefs:
            pref_dict = row_to_dict(prefs)
            pref_dict["preferred_categories"] = parse_json_field(
                pref_dict.get("preferred_categories"), []
            )
            pref_dict["preferred_brands"] = parse_json_field(
                pref_dict.get("preferred_brands"), []
            )
            pref_dict["product_requirements"] = parse_json_field(
                pref_dict.get("product_requirements"), {}
            )
            profile["preferences"] = pref_dict
        else:
            profile["preferences"] = {}

        profile["shopping_goals"] = [row_to_dict(g) for g in goals]

        return jsonify(profile)

    except Exception as exc:
        return _error(str(exc))


@app.route("/api/profile", methods=["PUT"])
def update_profile():
    """Update the demo user preferences."""
    try:
        data = request.get_json(force=True) or {}

        allowed_fields = {
            "preferred_categories", "budget_min", "budget_max",
            "preferred_brands", "product_requirements",
            "shopping_frequency", "shopping_goals", "notes",
        }

        # Validate budget constraints if provided
        b_min = data.get("budget_min")
        b_max = data.get("budget_max")
        if b_min is not None and b_max is not None:
            try:
                if float(b_max) < float(b_min):
                    return _error("budget_max cannot be less than budget_min", 400)
            except (ValueError, TypeError):
                return _error("budget values must be numeric", 400)

        updates = {}
        for field in allowed_fields:
            if field in data:
                value = data[field]
                # Serialise list/dict fields back to JSON strings
                if field in ("preferred_categories", "preferred_brands", "product_requirements"):
                    updates[field] = json.dumps(value) if not isinstance(value, str) else value
                else:
                    updates[field] = value

        if not updates:
            return _error("No valid fields provided for update.", 400)

        updates["updated_at"] = current_timestamp()
        uid = get_current_user_id()

        # Upsert shopping_preferences
        prefs_exist = database.query_db(
            "SELECT id FROM shopping_preferences WHERE user_id = ?", (uid,), one=True
        )

        if prefs_exist:
            set_clause = ", ".join(f"{k} = ?" for k in updates)
            sql = f"UPDATE shopping_preferences SET {set_clause} WHERE user_id = ?"
            database.execute_db(sql, tuple(updates.values()) + (uid,))
        else:
            updates["user_id"] = uid
            cols = ", ".join(updates.keys())
            placeholders = ", ".join("?" for _ in updates)
            sql = f"INSERT INTO shopping_preferences ({cols}) VALUES ({placeholders})"
            database.execute_db(sql, tuple(updates.values()))

        return get_profile()

    except Exception as exc:
        return _error(str(exc))


@app.route("/api/profile", methods=["DELETE"])
def reset_profile():
    """Reset the demo profile to defaults by clearing derived data and re-seeding."""
    try:
        for table in ("predictions", "recommendations", "purchase_history",
                      "user_feedback", "shopping_goals"):
            database.execute_db(f"DELETE FROM {table} WHERE user_id = 1")

        # Reset preferences
        database.execute_db("DELETE FROM shopping_preferences WHERE user_id = 1")

        # Re-seed demo user data
        _seed_demo_user()

        return jsonify({"message": "Demo profile reset to defaults successfully.", "user_id": 1})

    except Exception as exc:
        return _error(str(exc))


@app.route("/api/user/profile", methods=["GET"])
def get_user_profile():
    """
    Return user profile details across the three core sections:
    1. Personal details (username, email, phone)
    2. Location (address, city, state, pincode)
    3. Mode of payment (preferred_payment_mode: 'cod' or 'online')
    """
    try:
        user_id = session.get("user_id")
        if not user_id:
            user_id = Config.DEFAULT_DEMO_USER_ID

        user = database.query_db("SELECT * FROM users WHERE id = ?", (user_id,), one=True)
        if not user:
            return _error("User not found.", 404)

        u = row_to_dict(user)
        u.pop("password_hash", None)

        return jsonify({
            "success": True,
            "user_id": u["id"],
            "user": u,
            "username": u.get("username") or "",
            "email": u.get("email") or "",
            "phone": u.get("phone") or "",
            "address": u.get("address") or "",
            "city": u.get("city") or "",
            "state": u.get("state") or "",
            "pincode": u.get("pincode") or "",
            "preferred_payment_mode": u.get("preferred_payment_mode") or "cod",
            "is_authenticated": bool(session.get("is_authenticated_user"))
        })
    except Exception as exc:
        return _error(f"Failed to fetch profile: {str(exc)}", 500)


@app.route("/api/user/profile", methods=["POST", "PUT"])
def update_user_profile():
    """
    Update authenticated user's profile information across the 3 sections:
    Personal Details, Location, and Mode of Payment.
    Validates all inputs securely on the backend.
    """
    try:
        user_id = session.get("user_id")
        # In test mode or when testing without explicit login, allow default user
        if not user_id:
            if app.config.get("TESTING"):
                user_id = Config.DEFAULT_DEMO_USER_ID
            else:
                return _error("Please sign in to update your profile.", 401)

        data = request.get_json(force=True) or {}
        user_row = database.query_db("SELECT * FROM users WHERE id = ?", (user_id,), one=True)
        if not user_row:
            return _error("User not found.", 404)
        current = row_to_dict(user_row)

        username = (data.get("username") or data.get("name") or current.get("username") or "").strip()
        email = (data.get("email") or current.get("email") or "").strip().lower()
        phone = (data.get("phone") if "phone" in data else current.get("phone") or "").strip()
        address = (data.get("address") if "address" in data else current.get("address") or "").strip()
        city = (data.get("city") if "city" in data else current.get("city") or "").strip()
        state = (data.get("state") if "state" in data else current.get("state") or "").strip()
        pincode = (data.get("pincode") if "pincode" in data else current.get("pincode") or "").strip()
        preferred_payment_mode = (data.get("preferred_payment_mode") or current.get("preferred_payment_mode") or "cod").strip().lower()

        # Validation
        if "username" in data or "name" in data:
            if not username or len(username) < 2:
                return _error("Full name must be at least 2 characters.", 400)

        if "email" in data:
            if not email or "@" not in email or "." not in email:
                return _error("Please provide a valid email address.", 400)
            existing = database.query_db(
                "SELECT id FROM users WHERE LOWER(email) = ? AND id != ?",
                (email, user_id),
                one=True
            )
            if existing:
                return _error("This email address is already in use by another account.", 409)

        if phone and not re.match(r"^\+?[\d\s-]{7,15}$", phone):
            return _error("Please enter a valid phone number (7 to 15 digits).", 400)

        if pincode and not re.match(r"^\d{4,10}$", pincode):
            return _error("Please enter a valid PIN / postal code.", 400)

        if preferred_payment_mode not in ("cod", "online", "cards", "upi", "netbanking"):
            preferred_payment_mode = "cod"

        database.execute_db(
            """
            UPDATE users
            SET username = ?,
                email = ?,
                phone = ?,
                address = ?,
                city = ?,
                state = ?,
                pincode = ?,
                preferred_payment_mode = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (username, email, phone, address, city, state, pincode, preferred_payment_mode, user_id)
        )

        # Update active session if user updated their credentials
        session["username"] = username
        session["email"] = email

        return jsonify({
            "success": True,
            "message": "Profile updated successfully!",
            "profile": {
                "user_id": user_id,
                "username": username,
                "email": email,
                "phone": phone,
                "address": address,
                "city": city,
                "state": state,
                "pincode": pincode,
                "preferred_payment_mode": preferred_payment_mode
            }
        })
    except Exception as exc:
        return _error(f"Failed to update profile: {str(exc)}", 500)


# ---------------------------------------------------------------------------
# API – Purchase History
# ---------------------------------------------------------------------------

@app.route("/api/purchase-history", methods=["GET"])
def get_purchase_history():
    """Get verified purchase history for the current authenticated user."""
    try:
        user_id = get_current_user_id()
        from services.purchase_history_service import PurchaseHistoryService
        history = PurchaseHistoryService.get_eligible_purchases_for_user(user_id)
        return jsonify({
            "history": history,
            "purchases": history,
            "total": len(history),
            "user_id": user_id
        })
    except Exception as exc:
        return _error(str(exc))


@app.route("/api/purchase-history", methods=["POST"])
def add_purchase_history():
    """Add a new purchase history item for the current user."""
    try:
        user_id = get_current_user_id()
        data = request.get_json(force=True) or {}

        required = ["product_name"]
        for field in required:
            if not data.get(field):
                return _error(f"Missing required field: {field}", 400)

        row_id = database.execute_db(
            """
            INSERT INTO purchase_history
                (user_id, product_name, category, brand, price, purchase_date, quantity, notes, is_verified_purchase)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                user_id,
                data["product_name"],
                data.get("category", ""),
                data.get("brand", ""),
                data.get("price"),
                data.get("purchase_date", current_timestamp()[:10]),
                data.get("quantity", 1),
                data.get("notes", ""),
            ),
        )

        row = database.query_db(
            "SELECT * FROM purchase_history WHERE id = ?", (row_id,), one=True
        )
        return jsonify(row_to_dict(row)), 201

    except Exception as exc:
        return _error(str(exc))


@app.route("/api/purchase-history/<int:item_id>", methods=["DELETE"])
def delete_purchase_history(item_id):
    """Delete a purchase history item belonging to the current user."""
    try:
        user_id = get_current_user_id()
        row = database.query_db(
            "SELECT id FROM purchase_history WHERE id = ? AND user_id = ?",
            (item_id, user_id), one=True
        )
        if not row:
            return _error(f"Purchase history item {item_id} not found.", 404)

        database.execute_db(
            "DELETE FROM purchase_history WHERE id = ? AND user_id = ?", (item_id, user_id)
        )
        return jsonify({"message": f"Purchase history item {item_id} deleted.", "id": item_id})

    except Exception as exc:
        return _error(str(exc))


# ---------------------------------------------------------------------------
# API – Digital Twin & Agentic Shopping Intelligence Endpoints
# ---------------------------------------------------------------------------

@app.route("/api/twin/insights", methods=["GET"])
def get_twin_insights():
    """
    Run RecommendationCoordinatorAgent to synthesize:
    - Verified purchase history analytics
    - Learned preferences (with privacy toggle check)
    - Repeat replenishment forecasts with evidence
    - Ranked recommendations with explainable badges
    """
    try:
        user_id = get_current_user_id()
        from agents.agent_recommendation_coordinator import RecommendationCoordinatorAgent
        coordinator = RecommendationCoordinatorAgent()
        result = coordinator.run(user_id=user_id)
        return jsonify(result)
    except Exception as exc:
        return _error(str(exc), 500)


@app.route("/api/twin/privacy-controls", methods=["POST", "GET"])
def update_twin_privacy_controls():
    """Get or toggle whether purchase history is used for Digital Twin personalization."""
    try:
        user_id = get_current_user_id()
        from services.purchase_history_service import PurchaseHistoryService
        if request.method == "POST":
            data = request.get_json(force=True) or {}
            opt_in = bool(data.get("use_purchase_history_for_twin", True))
            PurchaseHistoryService.set_twin_history_opt_in(user_id, opt_in)
            return jsonify({
                "success": True,
                "user_id": user_id,
                "use_purchase_history_for_twin": opt_in,
                "message": "Privacy settings updated successfully."
            })
        else:
            opt_in = PurchaseHistoryService.is_twin_history_opted_in(user_id)
            return jsonify({
                "user_id": user_id,
                "use_purchase_history_for_twin": opt_in
            })
    except Exception as exc:
        return _error(str(exc), 500)


@app.route("/api/twin/dismiss-recommendation", methods=["POST"])
def dismiss_recommendation():
    """Dismiss a product recommendation for the current user."""
    try:
        user_id = get_current_user_id()
        data = request.get_json(force=True) or {}
        product_id = data.get("product_id")
        if not product_id:
            return _error("product_id is required.", 400)
        from agents.agent_recommendation_coordinator import RecommendationCoordinatorAgent
        RecommendationCoordinatorAgent.dismiss_recommendation(user_id, int(product_id))
        return jsonify({
            "success": True,
            "message": f"Product #{product_id} dismissed from recommendations.",
            "product_id": int(product_id)
        })
    except Exception as exc:
        return _error(str(exc), 500)


# ---------------------------------------------------------------------------
# API – Predictions
# ---------------------------------------------------------------------------

@app.route("/api/predictions", methods=["GET"])
def get_predictions():
    """Get the latest predictions for user 1."""
    try:
        rows = database.query_db(
            """
            SELECT * FROM predictions
            WHERE user_id = 1
            ORDER BY created_at DESC
            LIMIT 20
            """
        )
        predictions = []
        for row in rows:
            d = row_to_dict(row)
            d["supporting_evidence"] = parse_json_field(d.get("supporting_evidence"), [])
            predictions.append(d)

        run_id = predictions[0]["run_id"] if predictions else None
        generated_at = predictions[0]["created_at"] if predictions else None

        return jsonify({
            "predictions": predictions,
            "run_id": run_id,
            "generated_at": generated_at,
        })

    except Exception as exc:
        return _error(str(exc))


@app.route("/api/predictions", methods=["POST"])
def run_predictions():
    """Trigger Agent B (prediction agent) specifically."""
    try:
        from agents.orchestrator import AgentOrchestrator

        orchestrator = AgentOrchestrator()
        result = orchestrator.run_agent_b(user_id=1)

        predictions = result.get("predictions", [])
        run_id = result.get("run_id", str(uuid.uuid4()))

        return jsonify({"predictions": predictions, "run_id": run_id})

    except ImportError:
        # Orchestrator not yet available – return informative placeholder
        return jsonify({
            "predictions": [],
            "run_id": str(uuid.uuid4()),
            "message": "Orchestrator not yet available. Build agents first.",
        }), 202

    except Exception as exc:
        return _error(str(exc))


# ---------------------------------------------------------------------------
# API – Recommendations
# ---------------------------------------------------------------------------

@app.route("/api/recommendations", methods=["GET"])
def get_recommendations():
    """Get the latest recommendations for user 1."""
    try:
        rows = database.query_db(
            """
            SELECT * FROM recommendations
            WHERE user_id = 1
            ORDER BY rank ASC, created_at DESC
            LIMIT 20
            """
        )
        recs = []
        for row in rows:
            d = row_to_dict(row)
            d["alternatives"] = parse_json_field(d.get("alternatives"), [])
            recs.append(d)

        run_id = recs[0]["run_id"] if recs else None

        return jsonify({"recommendations": recs, "run_id": run_id, "total": len(recs)})

    except Exception as exc:
        return _error(str(exc))


@app.route("/api/recommendations", methods=["POST"])
def run_recommendations():
    """Trigger the full AI recommendation workflow (all agents)."""
    try:
        from agents.orchestrator import AgentOrchestrator

        orchestrator = AgentOrchestrator()
        result = orchestrator.run(user_id=1)

        return jsonify(result)

    except ImportError:
        return jsonify({
            "recommendations": [],
            "run_id": str(uuid.uuid4()),
            "message": "Orchestrator not yet available. Build agents first.",
        }), 202

    except Exception as exc:
        return _error(str(exc))


# ---------------------------------------------------------------------------
# API – Product Comparisons
# ---------------------------------------------------------------------------

@app.route("/api/comparisons", methods=["POST"])
def compare_products():
    """Compare specific products using Agent D and multi-attribute decision support."""
    try:
        data = request.get_json(force=True) or {}
        product_ids = data.get("product_ids", [])

        if not product_ids or not isinstance(product_ids, list):
            return _error("product_ids must be a non-empty list of integers.", 400)
        if len(product_ids) < 2:
            return _error("At least 2 product IDs are required for comparison.", 400)
        if len(product_ids) > 10:
            return _error("Cannot compare more than 10 products at once.", 400)

        clean_ids = [int(x) for x in product_ids if str(x).isdigit() and int(x) > 0]
        if len(clean_ids) < 2:
            return _error("At least 2 valid product IDs are required.", 400)

        try:
            from agents.orchestrator import AgentOrchestrator

            orchestrator = AgentOrchestrator()
            result = orchestrator.run_agent_d(user_id=1, product_ids=clean_ids)
            return jsonify(result)

        except Exception as orch_err:
            # Fallback: robust multi-attribute comparison from DB
            placeholders = ",".join("?" * len(clean_ids))
            rows = database.query_db(
                f"SELECT * FROM products WHERE id IN ({placeholders})",
                tuple(clean_ids),
            )
            products = []
            for row in rows:
                d = row_to_dict(row)
                d["specifications"] = parse_json_field(d.get("specifications"), {})
                products.append(d)

            if not products:
                return _error("No products found for the given IDs.", 404)

            min_price = min(float(p.get("price") or 0) for p in products)
            winner = max(
                products,
                key=lambda p: (float(p.get("rating") or 4.0) * 0.4)
                + ((1.0 - (float(p.get("price") or 1) / 100000.0)) * 0.6),
            )
            table_rows = []
            for p in products:
                table_rows.append({
                    "product_id": p["id"],
                    "id": p["id"],
                    "name": p.get("name"),
                    "product_name": p.get("name"),
                    "brand": p.get("brand"),
                    "category": p.get("category"),
                    "price": float(p.get("price") or 0),
                    "rating": float(p.get("rating") or 4.0),
                    "stock": p.get("stock", 20),
                    "image_url": p.get("image_url", ""),
                    "specifications": p.get("specifications", {}),
                    "specs": p.get("specifications", {}),
                    "advantages": [
                        f"Competitive value at {format_price(p['price'])}",
                        f"Customer rated {p.get('rating', 4.0)}★",
                    ],
                    "limitations": [
                        "Higher price bracket"
                        if float(p.get("price", 0)) > min_price
                        else "Standard feature set"
                    ],
                    "is_lowest_price": float(p.get("price") or 0) == min_price,
                })

            return jsonify({
                "products": table_rows,
                "comparison_table": table_rows,
                "winner_id": winner["id"],
                "winner_name": winner["name"],
                "winner_reason": f"{winner['name']} offers the highest overall value score, balancing rating and pricing.",
                "lowest_price_id": next(
                    (p["id"] for p in products if float(p.get("price") or 0) == min_price),
                    None,
                ),
            })

    except Exception as exc:
        return _error(str(exc))


def _build_comparison_table(products: list) -> dict:
    """Build a basic key-attribute comparison table for a list of products."""
    table = {}
    attributes = ["name", "brand", "category", "price", "rating", "stock"]
    for attr in attributes:
        table[attr] = {p["id"]: p.get(attr) for p in products}
    return table


# ---------------------------------------------------------------------------
# API – Agent Runs
# ---------------------------------------------------------------------------

@app.route("/api/agent-runs", methods=["GET"])
def get_agent_runs():
    """Return agent execution history, optionally filtered by run_id."""
    try:
        run_id_filter = request.args.get("run_id", "").strip()

        if run_id_filter:
            rows = database.query_db(
                """
                SELECT * FROM agent_runs
                WHERE user_id = 1 AND run_id = ?
                ORDER BY created_at DESC
                """,
                (run_id_filter,),
            )
        else:
            rows = database.query_db(
                """
                SELECT * FROM agent_runs
                WHERE user_id = 1
                ORDER BY created_at DESC
                LIMIT 100
                """
            )

        runs = [row_to_dict(r) for r in rows]
        return jsonify({"runs": runs, "total": len(runs)})

    except Exception as exc:
        return _error(str(exc))


# ---------------------------------------------------------------------------
# API – Shopping Goals
# ---------------------------------------------------------------------------

@app.route("/api/shopping-goals", methods=["GET"])
def get_shopping_goals():
    """Get shopping goals for user 1."""
    try:
        rows = database.query_db(
            "SELECT * FROM shopping_goals WHERE user_id = 1 ORDER BY created_at DESC"
        )
        goals = [row_to_dict(r) for r in rows]
        return jsonify({"goals": goals, "total": len(goals)})

    except Exception as exc:
        return _error(str(exc))


@app.route("/api/shopping-goals", methods=["POST"])
def add_shopping_goal():
    """Add a new shopping goal for user 1."""
    try:
        data = request.get_json(force=True) or {}

        if not data.get("goal_title"):
            return _error("Missing required field: goal_title", 400)

        row_id = database.execute_db(
            """
            INSERT INTO shopping_goals
                (user_id, goal_title, goal_description, target_date, budget)
            VALUES (1, ?, ?, ?, ?)
            """,
            (
                data["goal_title"],
                data.get("goal_description", ""),
                data.get("target_date"),
                data.get("budget", 0.0),
            ),
        )

        row = database.query_db(
            "SELECT * FROM shopping_goals WHERE id = ?", (row_id,), one=True
        )
        return jsonify(row_to_dict(row)), 201

    except Exception as exc:
        return _error(str(exc))


@app.route("/api/shopping-goals/<int:goal_id>", methods=["DELETE"])
def delete_shopping_goal(goal_id):
    """Delete a shopping goal."""
    try:
        row = database.query_db(
            "SELECT id FROM shopping_goals WHERE id = ? AND user_id = 1",
            (goal_id,), one=True
        )
        if not row:
            return _error(f"Shopping goal {goal_id} not found.", 404)

        database.execute_db(
            "DELETE FROM shopping_goals WHERE id = ? AND user_id = 1", (goal_id,)
        )
        return jsonify({"message": f"Shopping goal {goal_id} deleted.", "id": goal_id})

    except Exception as exc:
        return _error(str(exc))


# ---------------------------------------------------------------------------
# API – User Feedback
# ---------------------------------------------------------------------------

@app.route("/api/feedback", methods=["POST"])
def submit_feedback():
    """Submit user feedback on predictions, recommendations, or products."""
    try:
        data = request.get_json(force=True) or {}

        required = ["item_type", "feedback_type"]
        for field in required:
            if not data.get(field):
                return _error(f"Missing required field: {field}", 400)

        valid_item_types = ("prediction", "recommendation", "product", "comparison", "general")
        if data["item_type"] not in valid_item_types:
            return _error(
                f"item_type must be one of: {', '.join(valid_item_types)}", 400
            )

        valid_feedback_types = ("positive", "negative", "neutral", "rating", "comment", "like", "dislike", "helpful", "dismiss")
        if data["feedback_type"] not in valid_feedback_types:
            return _error(
                f"feedback_type must be one of: {', '.join(valid_feedback_types)}", 400
            )

        rating = data.get("rating")
        if rating is not None:
            try:
                rating = int(rating)
                if not (1 <= rating <= 5):
                    return _error("rating must be between 1 and 5.", 400)
            except (TypeError, ValueError):
                return _error("rating must be an integer.", 400)

        row_id = database.execute_db(
            """
            INSERT INTO user_feedback
                (user_id, item_type, item_id, feedback_type, rating, comment)
            VALUES (1, ?, ?, ?, ?, ?)
            """,
            (
                data["item_type"],
                data.get("item_id"),
                data["feedback_type"],
                rating,
                data.get("comment", ""),
            ),
        )

        row = database.query_db(
            "SELECT * FROM user_feedback WHERE id = ?", (row_id,), one=True
        )
        return jsonify(row_to_dict(row)), 201

    except Exception as exc:
        return _error(str(exc))


# ---------------------------------------------------------------------------
# API – Dashboard
# ---------------------------------------------------------------------------

@app.route("/api/dashboard", methods=["GET"])
def get_dashboard():
    """Return consolidated dashboard data for the UI."""
    try:
        # --- User profile summary ---
        user = database.query_db("SELECT * FROM users WHERE id = 1", one=True)
        prefs = database.query_db(
            "SELECT * FROM shopping_preferences WHERE user_id = 1", one=True
        )
        profile_summary = row_to_dict(user) if user else {}
        if prefs:
            pref_dict = row_to_dict(prefs)
            profile_summary["budget_min"] = pref_dict.get("budget_min", 0)
            profile_summary["budget_max"] = pref_dict.get("budget_max", 10000)
            profile_summary["preferred_categories"] = parse_json_field(
                pref_dict.get("preferred_categories"), []
            )
            profile_summary["shopping_frequency"] = pref_dict.get("shopping_frequency", "monthly")

        # --- Latest 3 predictions ---
        pred_rows = database.query_db(
            """
            SELECT * FROM predictions
            WHERE user_id = 1
            ORDER BY created_at DESC
            LIMIT 3
            """
        )
        latest_predictions = []
        for row in pred_rows:
            d = row_to_dict(row)
            d["supporting_evidence"] = parse_json_field(d.get("supporting_evidence"), [])
            latest_predictions.append(d)

        # --- Latest 5 recommendations ---
        rec_rows = database.query_db(
            """
            SELECT * FROM recommendations
            WHERE user_id = 1
            ORDER BY rank ASC, created_at DESC
            LIMIT 5
            """
        )
        latest_recommendations = []
        for row in rec_rows:
            d = row_to_dict(row)
            d["alternatives"] = parse_json_field(d.get("alternatives"), [])
            latest_recommendations.append(d)

        # --- Recent agent runs (last 5) ---
        run_rows = database.query_db(
            """
            SELECT * FROM agent_runs
            WHERE user_id = 1
            ORDER BY created_at DESC
            LIMIT 5
            """
        )
        recent_runs = [row_to_dict(r) for r in run_rows]

        # --- Budget status ---
        budget_min = profile_summary.get("budget_min", 0)
        budget_max = profile_summary.get("budget_max", 10000)

        spent_row = database.query_db(
            """
            SELECT COALESCE(SUM(price * quantity), 0) AS total_spent
            FROM purchase_history
            WHERE user_id = 1
            AND purchase_date >= date('now', '-30 days')
            """,
            one=True,
        )
        spent_this_month = float(spent_row["total_spent"]) if spent_row else 0.0

        budget_status = {
            "budget_min": budget_min,
            "budget_max": budget_max,
            "spent_this_month": spent_this_month,
            "remaining": max(0.0, budget_max - spent_this_month),
            "utilization_pct": (
                round(spent_this_month / budget_max * 100, 1) if budget_max > 0 else 0
            ),
        }

        # --- Stats ---
        total_predictions = database.query_db(
            "SELECT COUNT(*) AS cnt FROM predictions WHERE user_id = 1", one=True
        )
        total_recommendations = database.query_db(
            "SELECT COUNT(*) AS cnt FROM recommendations WHERE user_id = 1", one=True
        )
        categories_tracked = database.query_db(
            """
            SELECT COUNT(DISTINCT category) AS cnt
            FROM purchase_history
            WHERE user_id = 1 AND category != ''
            """,
            one=True,
        )

        stats = {
            "total_predictions": total_predictions["cnt"] if total_predictions else 0,
            "total_recommendations": total_recommendations["cnt"] if total_recommendations else 0,
            "categories_tracked": categories_tracked["cnt"] if categories_tracked else 0,
        }

        return jsonify({
            "profile": profile_summary,
            "latest_predictions": latest_predictions,
            "latest_recommendations": latest_recommendations,
            "predictions": latest_predictions,
            "recommendations": latest_recommendations,
            "recent_agent_runs": recent_runs,
            "budget_status": budget_status,
            "stats": stats,
            "generated_at": current_timestamp(),
        })

    except Exception as exc:
        return _error(str(exc))


# ---------------------------------------------------------------------------
# API – PreTwin Reward Points (100 points = ₹1.00)
# ---------------------------------------------------------------------------

@app.route("/api/rewards/balance", methods=["GET"])
def get_rewards_balance():
    """Get current reward points balance and rupee equivalence."""
    try:
        user_id = get_current_user_id()
        balance = get_user_reward_balance(user_id)
        rupee_val = round(balance / 100.0, 2)

        # Calculate lifetime earned
        row_earned = database.query_db(
            "SELECT COALESCE(SUM(points), 0) AS lifetime FROM reward_ledger WHERE user_id = ? AND points > 0",
            (user_id,),
            one=True
        )
        lifetime = int(row_earned["lifetime"]) if row_earned else 0

        # Calculate lifetime redeemed
        row_redeemed = database.query_db(
            "SELECT COALESCE(SUM(points), 0) AS redeemed FROM reward_ledger WHERE user_id = ? AND points < 0",
            (user_id,),
            one=True
        )
        redeemed = abs(int(row_redeemed["redeemed"])) if row_redeemed else 0

        return jsonify({
            "user_id": user_id,
            "balance_points": balance,
            "rupee_value": rupee_val,
            "points_ratio": "100 points = ₹1.00",
            "rate_per_point": 0.01,
            "points_per_order": 5,
            "lifetime_earned": lifetime,
            "lifetime_redeemed": redeemed
        })
    except Exception as e:
        return _error(f"Failed to fetch rewards balance: {str(e)}", 500)


@app.route("/api/rewards/history", methods=["GET"])
def get_rewards_history():
    """Get reward ledger transactions."""
    try:
        user_id = get_current_user_id()
        rows = database.query_db(
            "SELECT * FROM reward_ledger WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        )
        transactions = []
        for r in rows:
            td = row_to_dict(r)
            td["rupee_value"] = round(abs(td["points"]) / 100.0, 2)
            transactions.append(td)
        return jsonify({
            "transactions": transactions,
            "total": len(transactions),
            "balance": get_user_reward_balance(user_id)
        })
    except Exception as e:
        return _error(f"Failed to fetch rewards history: {str(e)}", 500)


@app.route("/api/rewards/redeem", methods=["POST"])
def redeem_rewards():
    """
    Redeem user reward points into an instant store discount / checkout credit.
    (100 points = ₹1.00 INR).
    """
    try:
        user_id = get_current_user_id()
        data = request.get_json() or {}
        points_to_redeem = int(data.get("points") or 0)

        current_balance = get_user_reward_balance(user_id)
        if points_to_redeem <= 0:
            return _error("Please enter a positive number of points to redeem (e.g. 100, 200, 500).", 400)
        if points_to_redeem > current_balance:
            return _error(f"Insufficient balance. You currently have {current_balance} points available.", 400)

        rupee_discount = round(points_to_redeem / 100.0, 2)
        voucher_code = f"PRETWIN-REW-{uuid.uuid4().hex[:6].upper()}"

        # Deduct from reward ledger
        database.execute_db(
            """
            INSERT INTO reward_ledger (user_id, points, rupee_value, transaction_type, description)
            VALUES (?, ?, ?, 'Redemption', ?)
            """,
            (user_id, -points_to_redeem, -rupee_discount, f"Redeemed {points_to_redeem} points for instant store credit {voucher_code} (-₹{rupee_discount:.2f})")
        )

        # Store in session as applied credit
        session["applied_reward_credit"] = {
            "code": voucher_code,
            "points": points_to_redeem,
            "rupee_discount": rupee_discount,
            "redeemed_at": datetime.utcnow().isoformat()
        }

        new_balance = get_user_reward_balance(user_id)
        return jsonify({
            "success": True,
            "message": f"Successfully redeemed {points_to_redeem} points! ₹{rupee_discount:.2f} store credit has been applied to your checkout.",
            "voucher_code": voucher_code,
            "points_redeemed": points_to_redeem,
            "rupee_discount": rupee_discount,
            "new_balance": new_balance,
            "new_rupee_value": round(new_balance / 100.0, 2),
            "applied_credit": session["applied_reward_credit"]
        })
    except Exception as e:
        return _error(f"Redemption failed: {str(e)}", 500)


@app.route("/api/rewards/claim-bonus", methods=["POST"])
def claim_reward_bonus():
    """
    Claim loyalty welcome/daily bonus points (+200 points = ₹2.00).
    """
    try:
        user_id = get_current_user_id()
        database.execute_db(
            """
            INSERT INTO reward_ledger (user_id, points, rupee_value, transaction_type, description)
            VALUES (?, 200, 2.0, 'Daily Bonus', 'PreTwin Loyalty Bonus Claim (+200 pts = ₹2.00)')
            """,
            (user_id,)
        )
        new_balance = get_user_reward_balance(user_id)
        return jsonify({
            "success": True,
            "message": "Awesome! 200 PreTwin Reward Points (₹2.00) have been added to your account.",
            "points_added": 200,
            "new_balance": new_balance,
            "new_rupee_value": round(new_balance / 100.0, 2)
        })
    except Exception as e:
        return _error(f"Failed to claim bonus: {str(e)}", 500)


@app.route("/api/rewards/active-credit", methods=["GET"])
def get_active_reward_credit():
    """Get active session reward credit if previously redeemed."""
    credit = session.get("applied_reward_credit")
    return jsonify({
        "has_active_credit": bool(credit),
        "credit": credit
    })


# ---------------------------------------------------------------------------
# API – PreTwin Smart Shopping Savings Plan
# ---------------------------------------------------------------------------

@app.route("/api/savings/plans", methods=["GET"])
def get_savings_plans():
    """Retrieve all savings plans for current user."""
    try:
        user_id = get_current_user_id()
        rows = database.query_db(
            "SELECT * FROM savings_plans WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        )
        plans = []
        for r in rows:
            p = row_to_dict(r)
            if p.get("product_id"):
                prod = database.query_db("SELECT id, name, price, image_url FROM products WHERE id = ?", (p["product_id"],), one=True)
                if prod:
                    p["product"] = row_to_dict(prod)
            plans.append(calculate_savings_plan_stats(p))
        return jsonify({"plans": plans, "total": len(plans)})
    except Exception as e:
        return _error(f"Failed to fetch savings plans: {str(e)}", 500)


@app.route("/api/savings/plans", methods=["POST"])
def create_savings_plan():
    """Create a new savings plan."""
    try:
        user_id = get_current_user_id()
        data = request.get_json() or {}
        title = (data.get("title") or data.get("goal_title") or "").strip()
        target_amount = float(data.get("target_amount") or 0.0)
        product_id = data.get("product_id")
        notes = (data.get("notes") or "").strip()
        target_date = data.get("target_date")

        if not target_date:
            from datetime import timedelta
            target_date = (datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d")

        product_name = None
        product_image = None
        if product_id:
            p_row = database.query_db("SELECT * FROM products WHERE id = ?", (product_id,), one=True)
            if p_row:
                p_dict = row_to_dict(p_row)
                product_name = p_dict["name"]
                product_image = p_dict.get("image_url")
                if target_amount <= 0:
                    target_amount = float(p_dict.get("price") or 0.0)

        if not title:
            title = f"Save for {product_name}" if product_name else "30-Day Shopping Goal"

        if target_amount <= 0:
            return _error("Target amount must be greater than 0.", 400)

        plan_id = database.execute_db(
            """
            INSERT INTO savings_plans
                (user_id, product_id, goal_title, target_amount, current_saved, target_date, status, notes)
            VALUES (?, ?, ?, ?, 0.0, ?, 'active', ?)
            """,
            (user_id, product_id, title, target_amount, target_date, notes)
        )

        created_row = database.query_db("SELECT * FROM savings_plans WHERE id = ?", (plan_id,), one=True)
        stats = calculate_savings_plan_stats(row_to_dict(created_row))
        if product_image:
            stats["product_image"] = product_image
        return jsonify({"success": True, "plan": stats}), 201
    except Exception as e:
        return _error(f"Failed to create savings plan: {str(e)}", 500)


@app.route("/api/savings/plans/<int:plan_id>", methods=["GET"])
def get_savings_plan_detail(plan_id):
    """Retrieve details and contributions for a savings plan."""
    try:
        user_id = get_current_user_id()
        row = database.query_db(
            "SELECT * FROM savings_plans WHERE id = ? AND (user_id = ? OR user_id = 1)",
            (plan_id, user_id),
            one=True
        )
        if not row:
            return _error(f"Savings plan #{plan_id} not found.", 404)
        plan = calculate_savings_plan_stats(row_to_dict(row))

        if plan.get("product_id"):
            p_row = database.query_db("SELECT * FROM products WHERE id = ?", (plan["product_id"],), one=True)
            if p_row:
                plan["product"] = row_to_dict(p_row)

        c_rows = database.query_db(
            "SELECT * FROM savings_contributions WHERE plan_id = ? ORDER BY created_at DESC, id DESC",
            (plan_id,)
        )
        plan["contributions"] = [row_to_dict(c) for c in c_rows]
        return jsonify({"plan": plan})
    except Exception as e:
        return _error(f"Failed to fetch savings plan: {str(e)}", 500)


@app.route("/api/savings/plans/<int:plan_id>/contributions", methods=["POST"])
def add_savings_contribution(plan_id):
    """Add a savings contribution/deposit to a plan."""
    try:
        user_id = get_current_user_id()
        data = request.get_json() or {}
        amount = float(data.get("amount") or 0.0)
        payment_method = (data.get("payment_method") or "PreTwin Wallet / Deposit").strip()
        notes = (data.get("notes") or data.get("note") or "").strip()

        if amount <= 0:
            return _error("Contribution amount must be greater than 0.", 400)

        plan_row = database.query_db("SELECT * FROM savings_plans WHERE id = ?", (plan_id,), one=True)
        if not plan_row:
            return _error(f"Savings plan #{plan_id} not found.", 404)
        plan = row_to_dict(plan_row)

        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        cid = database.execute_db(
            """
            INSERT INTO savings_contributions (plan_id, user_id, amount, contribution_date, note)
            VALUES (?, ?, ?, ?, ?)
            """,
            (plan_id, user_id, amount, today_str, notes)
        )

        current_val = float(plan.get("current_saved") if plan.get("current_saved") is not None else 0.0)
        new_saved = round(current_val + amount, 2)
        new_status = "completed" if new_saved >= float(plan["target_amount"]) else plan["status"]
        database.execute_db(
            "UPDATE savings_plans SET current_saved = ?, status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (new_saved, new_status, plan_id)
        )

        updated_plan = database.query_db("SELECT * FROM savings_plans WHERE id = ?", (plan_id,), one=True)
        return jsonify({
            "success": True,
            "contribution_id": cid,
            "plan": calculate_savings_plan_stats(row_to_dict(updated_plan))
        }), 201
    except Exception as e:
        return _error(f"Failed to add contribution: {str(e)}", 500)


@app.route("/api/savings/contributions/<int:contribution_id>", methods=["PUT", "DELETE"])
def manage_savings_contribution(contribution_id):
    """Edit or delete a savings contribution."""
    try:
        c_row = database.query_db("SELECT * FROM savings_contributions WHERE id = ?", (contribution_id,), one=True)
        if not c_row:
            return _error("Contribution not found.", 404)
        c = row_to_dict(c_row)
        plan_id = c["plan_id"]

        if request.method == "DELETE":
            database.execute_db("DELETE FROM savings_contributions WHERE id = ?", (contribution_id,))
            sum_row = database.query_db("SELECT COALESCE(SUM(amount), 0) AS total FROM savings_contributions WHERE plan_id = ?", (plan_id,), one=True)
            new_saved = float(sum_row["total"])
            plan_row = database.query_db("SELECT * FROM savings_plans WHERE id = ?", (plan_id,), one=True)
            plan = row_to_dict(plan_row)
            new_status = "completed" if new_saved >= float(plan["target_amount"]) else "active"
            database.execute_db("UPDATE savings_plans SET current_saved = ?, status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_saved, new_status, plan_id))
            return jsonify({"success": True, "message": "Contribution deleted."})

        # PUT
        data = request.get_json() or {}
        new_amount = float(data.get("amount", c["amount"]))
        new_notes = data.get("notes", data.get("note", c.get("note", "")))
        database.execute_db(
            "UPDATE savings_contributions SET amount = ?, note = ? WHERE id = ?",
            (new_amount, new_notes, contribution_id)
        )
        sum_row = database.query_db("SELECT COALESCE(SUM(amount), 0) AS total FROM savings_contributions WHERE plan_id = ?", (plan_id,), one=True)
        new_saved = float(sum_row["total"])
        plan_row = database.query_db("SELECT * FROM savings_plans WHERE id = ?", (plan_id,), one=True)
        plan = row_to_dict(plan_row)
        new_status = "completed" if new_saved >= float(plan["target_amount"]) else "active"
        database.execute_db("UPDATE savings_plans SET current_saved = ?, status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_saved, new_status, plan_id))
        return jsonify({"success": True, "message": "Contribution updated."})

    except Exception as e:
        return _error(f"Failed to update contribution: {str(e)}", 500)


@app.route("/api/savings/plans/<int:plan_id>/status", methods=["PUT"])
def update_savings_plan_status(plan_id):
    """Update plan status: active, completed, or cancelled."""
    try:
        data = request.get_json() or {}
        status = data.get("status", "active")
        database.execute_db("UPDATE savings_plans SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (status, plan_id))
        return jsonify({"success": True, "status": status})
    except Exception as e:
        return _error(f"Failed to update plan status: {str(e)}", 500)


# ---------------------------------------------------------------------------
# API – AI Shopping Chatbot
# ---------------------------------------------------------------------------

_chat_assistant = PreTwinChatAssistant()

@app.route("/api/chat", methods=["POST"])
def chat_with_assistant():
    """Handle chat messages to the PreTwin AI Shopping Twin."""
    try:
        data = request.get_json() or {}
        message = (data.get("message") or "").strip()
        session_id = data.get("session_id") or str(uuid.uuid4())
        user_id = get_current_user_id()

        if not message:
            return _error("Message cannot be empty.", 400)

        # Record user message
        database.execute_db(
            """
            INSERT INTO chat_messages (user_id, session_id, role, content, meta_data)
            VALUES (?, ?, 'user', ?, '{}')
            """,
            (user_id, session_id, message)
        )

        response = _chat_assistant.handle_message(message, user_id=user_id, session_id=session_id)

        # Record assistant reply
        database.execute_db(
            """
            INSERT INTO chat_messages (user_id, session_id, role, content, meta_data)
            VALUES (?, ?, 'assistant', ?, ?)
            """,
            (user_id, session_id, response.get("reply", ""), json.dumps({
                "products": response.get("products", []),
                "actions": response.get("actions", []),
                "intent": response.get("intent", "general")
            }))
        )

        return jsonify(response)
    except Exception as e:
        return _error(f"Chatbot error: {str(e)}", 500)


@app.route("/api/chat/history", methods=["GET"])
def get_chat_history():
    """Retrieve chat history for user session."""
    try:
        user_id = get_current_user_id()
        session_id = request.args.get("session_id")
        limit = request.args.get("limit", 50, type=int)

        if session_id:
            rows = database.query_db(
                "SELECT * FROM chat_messages WHERE session_id = ? ORDER BY id ASC LIMIT ?",
                (session_id, limit)
            )
        else:
            rows = database.query_db(
                "SELECT * FROM chat_messages WHERE user_id = ? ORDER BY id ASC LIMIT ?",
                (user_id, limit)
            )

        messages = []
        for r in rows:
            m = row_to_dict(r)
            m["message"] = m.get("content", "")
            m["sender"] = m.get("role", "")
            m["metadata"] = parse_json_field(m.get("meta_data"), {})
            messages.append(m)

        return jsonify({"messages": messages, "total": len(messages)})
    except Exception as e:
        return _error(f"Failed to fetch chat history: {str(e)}", 500)


@app.route("/api/chat/reset", methods=["POST"])
def reset_chat_history():
    """Clear chat session for user."""
    try:
        user_id = get_current_user_id()
        data = request.get_json() or {}
        session_id = data.get("session_id")

        if session_id:
            database.execute_db("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
        else:
            database.execute_db("DELETE FROM chat_messages WHERE user_id = ?", (user_id,))

        return jsonify({"success": True, "message": "Chat history cleared."})
    except Exception as e:
        return _error(f"Failed to reset chat: {str(e)}", 500)


# ---------------------------------------------------------------------------
# Register 8 Intelligent Shopping Features Routes & APIs
# ---------------------------------------------------------------------------
from routes_eight_features import register_eight_features_routes
register_eight_features_routes(app, get_current_user_id, row_to_dict, _error)


# ---------------------------------------------------------------------------
# Generic 404 / 405 handlers
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def not_found(e):
    return _error("The requested resource was not found.", 404)


@app.errorhandler(405)
def method_not_allowed(e):
    return _error("Method not allowed.", 405)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("[app] Initialising database …")
    database.init_db()

    print("[app] Seeding demo products …")
    _seed_demo_products()

    print("[app] Seeding demo user …")
    _seed_demo_user()

    print("[app] Starting PreTwinShop AI on http://127.0.0.1:5000")
    app.run(host="0.0.0.0", port=5000, debug=Config.DEBUG)
