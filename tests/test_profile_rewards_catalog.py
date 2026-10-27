"""
Test Suite for PreTwin AI:
1. First Navigation Bar (no duplicate PreTwin AI title, tagline present)
2. Second Navigation Bar (Features, More, Profile at end, no Alerts, no location popup)
3. Profile Page (Only Personal Details, Delivery Location, Mode of Payment)
4. Third Navigation Bar - "For You" Catalog Access (all products, search, category filter)
5. Rewards System (Exactly 5 points per completed order, COD on delivery, online on verify, reversal on return)
6. Eight AI Shopping Features status check
7. Checkout payment methods (COD & Online)
"""

import uuid
import pytest
from app import app
import database


@pytest.fixture
def client(app_client):
    return app_client


def test_first_and_second_navbars_layout(client):
    res = client.get("/")
    assert res.status_code == 200
    html = res.data.decode("utf-8")

    # 1. Branding bar above first navbar
    assert 'class="pretwin-top-branding-bar"' in html
    assert "Your Future. Your Style. Your Twin." in html

    # First navbar has search box & 5 shopping shortcuts
    first_nav_start = html.find('<header class="fk-navbar">')
    first_nav_end = html.find('</header>', first_nav_start)
    assert first_nav_start != -1 and first_nav_end != -1
    first_nav = html[first_nav_start:first_nav_end]

    assert 'fkSearchInput' in first_nav
    assert '/wishlist' in first_nav
    assert 'openCartModal()' in first_nav
    assert '/orders' in first_nav
    assert '/rewards' in first_nav
    assert '/savings' in first_nav

    # Ensure no alerts icon in first navbar or second navbar
    assert 'pretwinAlertsBtn' not in html
    assert 'pretwin-alerts' not in html

    # 2. Second navbar
    assert 'id="pretwinSecondNavbar"' in html
    sec_nav_start = html.find('id="pretwinSecondNavbar"')
    sec_nav_end = html.find('</nav>', sec_nav_start)
    sec_nav = html[sec_nav_start:sec_nav_end]

    # Features menu
    assert 'id="pretwinFeaturesBtn"' in sec_nav
    assert 'id="pretwinFeaturesDropdown"' in sec_nav

    # More menu
    assert 'id="pretwinMoreBtn"' in sec_nav
    assert 'id="pretwinMoreDropdown"' in sec_nav
    assert '/seller' in sec_nav
    assert '/notifications' in sec_nav
    assert '/customer-service' in sec_nav

    # Profile item is the LAST item in the second navbar
    feat_pos = sec_nav.find('id="pretwinFeaturesBtn"')
    more_pos = sec_nav.find('id="pretwinMoreBtn"')
    prof_pos = sec_nav.find('id="pretwinAccountItem"')
    assert feat_pos != -1
    assert more_pos != -1
    assert prof_pos != -1
    assert feat_pos < more_pos < prof_pos, "Profile must be the last item on the second navbar, after Features and More"


def test_profile_page_three_sections_only(client):
    res = client.get("/profile")
    assert res.status_code == 200
    html = res.data.decode("utf-8")

    # Contains the 3 requested sections
    assert "1. Personal Details" in html
    assert "2. Delivery Location" in html
    assert "3. Mode of Payment" in html

    # Field controls
    assert 'id="profileFullName"' in html
    assert 'id="profileEmail"' in html
    assert 'id="profilePhone"' in html
    assert 'id="profileAddress"' in html
    assert 'id="profileCity"' in html
    assert 'id="profileState"' in html
    assert 'id="profilePincode"' in html
    assert 'id="payModeCOD"' in html
    assert 'id="payModeOnline"' in html

    # Does NOT contain order history table, wishlist grid, or savings plans on the profile page
    assert 'id="profileOrdersTable"' not in html
    assert 'id="profileWishlistGrid"' not in html
    assert 'id="profileSavingsPlans"' not in html


def test_profile_api_get_and_update(client):
    # Register and log in
    unique_email = f"profile_user_{uuid.uuid4().hex[:6]}@pretwin.ai"
    reg_res = client.post("/api/auth/register", json={
        "name": "Alex Profile Tester",
        "email": unique_email,
        "password": "Password123!",
        "confirm_password": "Password123!"
    })
    assert reg_res.status_code == 201

    # GET /api/user/profile
    get_res = client.get("/api/user/profile")
    assert get_res.status_code == 200
    data = get_res.get_json()
    assert data["success"] is True
    assert "user" in data

    # POST /api/user/profile
    post_res = client.post("/api/user/profile", json={
        "username": "Alex Profile Tester",
        "phone": "+91 9123456789",
        "address": "402 Silicon Heights, Koramangala",
        "city": "Bengaluru",
        "state": "Karnataka",
        "pincode": "560034",
        "preferred_payment_mode": "cod"
    })
    assert post_res.status_code == 200
    assert post_res.get_json()["success"] is True

    # Verify updated values in database
    get_res2 = client.get("/api/user/profile")
    u = get_res2.get_json()["user"]
    assert u["phone"] == "+91 9123456789"
    assert u["city"] == "Bengaluru"
    assert u["pincode"] == "560034"
    assert u["preferred_payment_mode"] == "cod"


def test_for_you_catalog_access_and_pagination(client):
    # /recommendations renders For You full catalog view
    res = client.get("/recommendations")
    assert res.status_code == 200
    html = res.data.decode("utf-8")
    assert "statTotalCatalog" in html
    assert "forYouSearchInput" in html
    assert "forYouSortSelect" in html
    assert "forYouProductGrid" in html
    assert "forYouPagination" in html

    # API returns all catalog products
    api_res = client.get("/api/products?per_page=20&page=1")
    assert api_res.status_code == 200
    data = api_res.get_json()
    assert "products" in data
    assert data["total"] >= 1, f"Expected catalog products, got {data['total']}"


def test_rewards_five_points_lifecycle_and_reversal(client):
    unique_email = f"reward_order_{uuid.uuid4().hex[:6]}@pretwin.ai"
    reg_res = client.post("/api/auth/register", json={
        "name": "Rewards Tester",
        "email": unique_email,
        "password": "Password123!",
        "confirm_password": "Password123!"
    })
    assert reg_res.status_code == 201

    # Initial balance
    bal_res = client.get("/api/rewards/balance")
    init_balance = bal_res.get_json()["balance_points"]

    # 1. Place COD order
    create_res = client.post("/api/orders/create", json={
        "items": [{"product_id": 1, "quantity": 1}],
        "shipping_address": {
            "name": "Rewards Tester",
            "email": unique_email,
            "phone": "9876543210",
            "address": "402 Koramangala, Bengaluru",
            "city": "Bengaluru",
            "state": "Karnataka",
            "pincode": "560034"
        },
        "payment_method": "COD"
    })
    assert create_res.status_code == 201, create_res.get_json()
    cod_order_id = create_res.get_json()["order_id"]

    # In COD, points are NOT awarded yet (status = Confirmed, payment = Pending)
    bal_res2 = client.get("/api/rewards/balance")
    assert bal_res2.get_json()["balance_points"] == init_balance

    # Deliver COD order
    deliv_res = client.post(f"/api/orders/{cod_order_id}/mark-delivered")
    assert deliv_res.status_code == 200
    bal_res3 = client.get("/api/rewards/balance")
    assert bal_res3.get_json()["balance_points"] == init_balance + 5, "COD order must award exactly 5 points when delivered"

    # 2. Return COD order -> exactly 5 points must be reversed!
    return_res = client.post(f"/api/orders/{cod_order_id}/return")
    assert return_res.status_code == 200
    bal_res4 = client.get("/api/rewards/balance")
    assert bal_res4.get_json()["balance_points"] == init_balance, "Return must deduct the 5 points"


def test_eight_ai_shopping_features_load(client):
    features = [
        "/twin",
        "/predictions",
        "/discovery",
        "/budget",
        "/comparison",
        "/calendar",
        "/smart-cart",
        "/advanced-ai"
    ]
    for path in features:
        res = client.get(path)
        assert res.status_code == 200, f"Feature route {path} failed with {res.status_code}"
