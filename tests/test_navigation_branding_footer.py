"""
Test Suite for PreTwin AI: Complete Navigation, Branding, Location & Footer Redesign
Verifies:
1. Dedicated Project Branding section above first navigation bar (logo, name PreTwin AI, tagline)
2. Duplicated logo removed from inside first navigation bar
3. First navigation bar elements: Search, Location, Wishlist, Cart, Orders, Rewards, Savings, Features, Notifications, Profile, More
4. Smart Cart shortcut removed from first navigation bar
5. More menu items: Become a Seller, Notifications, Customer Service
6. Location selector and modal components
7. Features menu containing all 8 Intelligent Features
8. Old second navigation bar removed
9. Third navigation bar has "For You" as first item
10. Smart Shopping Card name update
11. Redesigned 5-column footer with dynamic year and working links
12. All new customer support and info routes return HTTP 200 OK
"""

import pytest
from app import app


@pytest.fixture
def client():
    with app.test_client() as c:
        yield c


def test_branding_section_above_first_navbar(client):
    res = client.get("/")
    assert res.status_code == 200
    html = res.data.decode("utf-8")

    # 1. Dedicated branding bar above first navigation bar
    assert 'class="pretwin-top-branding-bar"' in html
    assert "pretwin-logo.svg" in html
    assert "PreTwin" in html
    assert "AI" in html
    assert "Your Future. Your Style. Your Twin." in html

    # Verify that branding bar comes BEFORE <header class="fk-navbar">
    branding_idx = html.find('class="pretwin-top-branding-bar"')
    navbar_idx = html.find('class="fk-navbar"')
    assert branding_idx != -1
    assert navbar_idx != -1
    assert branding_idx < navbar_idx, "Branding bar must be placed above the first navigation bar"


def test_first_navbar_elements_and_smart_cart_removed(client):
    res = client.get("/")
    assert res.status_code == 200
    html = res.data.decode("utf-8")

    navbar_start = html.find('<header class="fk-navbar">')
    navbar_end = html.find('</header>', navbar_start)
    assert navbar_start != -1 and navbar_end != -1
    navbar_html = html[navbar_start:navbar_end]

    # Duplicated brand logo must NOT be in the first navigation bar
    assert 'pretwin-brand-link' not in navbar_html, "Duplicated logo should be removed from first navigation bar"

    # Search bar
    assert 'fk-search-box' in navbar_html
    assert 'fkSearchInput' in navbar_html

    # Location selector
    assert 'pretwin-location-container' in navbar_html
    assert 'pretwinLocationBtn' in navbar_html
    assert 'Deliver to' in navbar_html
    assert 'pretwinNavLocationText' in navbar_html

    # Wishlist, Cart, My Orders, Rewards, Savings
    assert 'href="/wishlist"' in navbar_html
    assert 'openCartModal()' in navbar_html
    assert 'href="/orders"' in navbar_html
    assert 'href="/rewards"' in navbar_html
    assert 'href="/savings"' in navbar_html

    # Smart Cart shortcut must NOT be in the first navigation bar
    assert 'Smart Cart' not in navbar_html, "Smart Cart must be removed from first navigation bar"

    # Features menu dropdown
    assert 'pretwinFeaturesBtn' in navbar_html
    assert 'pretwinFeaturesDropdown' in navbar_html

    # Notifications button & dropdown
    assert 'pretwinNotificationsBtn' in navbar_html
    assert 'pretwinNotificationsDropdown' in navbar_html

    # Profile / Account icon
    assert 'pretwinAccountItem' in navbar_html

    # More menu dropdown
    assert 'pretwinMoreBtn' in navbar_html
    assert 'pretwinMoreDropdown' in navbar_html
    assert 'href="/seller"' in navbar_html
    assert 'Become a Seller' in navbar_html
    assert 'Customer Service' in navbar_html
    assert 'href="/customer-service"' in navbar_html


def test_location_modal_structure(client):
    res = client.get("/")
    assert res.status_code == 200
    html = res.data.decode("utf-8")

    assert 'id="pretwinLocationModal"' in html
    assert 'id="pretwinLocationBackdrop"' in html
    assert 'requestBrowserLocation()' in html
    assert 'Use my current location' in html
    assert 'manualLocationInput' in html
    assert 'applyManualLocation(event)' in html


def test_features_menu_contains_all_eight_features(client):
    res = client.get("/")
    assert res.status_code == 200
    html = res.data.decode("utf-8")

    features_start = html.find('id="pretwinFeaturesDropdown"')
    features_end = html.find('</div>\n          </div>\n\n          <!-- Notifications', features_start)
    assert features_start != -1
    features_html = html[features_start:features_end if features_end != -1 else features_start + 4000]

    # 8 Intelligent Features in Features Menu
    assert "Personalization and Digital Twin" in features_html
    assert 'href="/twin"' in features_html
    assert "Predictive Shopping Intelligence" in features_html
    assert 'href="/predictions"' in features_html
    assert "Smart Product Discovery" in features_html
    assert 'href="/discovery"' in features_html
    assert "Budget and Price Intelligence" in features_html
    assert 'href="/budget"' in features_html
    assert "Product Comparison and Decision Support" in features_html
    assert 'href="/comparison"' in features_html
    assert "Future Predictive Calendar" in features_html
    assert 'href="/calendar"' in features_html
    assert "Smart Shopping Card" in features_html
    assert 'href="/smart-cart"' in features_html
    assert "Advanced Features for Future Development" in features_html
    assert 'href="/advanced-ai"' in features_html

    # Old second navigation bar must be removed
    assert '<nav class="pretwin-ai-nav-bar"' not in html, "Old second navbar should be removed"


def test_third_navbar_for_you_and_smart_shopping_card(client):
    res = client.get("/")
    assert res.status_code == 200
    html = res.data.decode("utf-8")

    cat_start = html.find('id="fkCatInner"')
    assert cat_start != -1

    # "For You" must appear first in the third navigation bar
    for_you_idx = html.find('For You ✨', cat_start)
    fashion_idx = html.find('Fashion <span class="fk-cat-caret">', cat_start)
    assert for_you_idx != -1, '"For You" item must be present in third navigation bar'
    assert fashion_idx != -1, '"Fashion" item must be present'
    assert for_you_idx < fashion_idx, '"For You" must appear before Fashion and all other categories'

    # Clicking For You links to recommendations
    assert 'href="/recommendations"' in html[cat_start:cat_start + 800]


def test_redesigned_five_column_footer(client):
    res = client.get("/")
    assert res.status_code == 200
    html = res.data.decode("utf-8")

    footer_start = html.find('<footer class="pretwin-footer">')
    assert footer_start != -1
    footer_html = html[footer_start:]

    # Column 1: About PreTwin
    assert "PreTwin AI" in footer_html
    assert "Your Future. Your Style. Your Twin." in footer_html
    assert "pretwin-logo.svg" in footer_html

    # Column 2: Shop
    assert "SHOP</h4>" in footer_html
    assert 'href="/recommendations"' in footer_html
    assert 'href="/discovery"' in footer_html
    assert 'href="/wishlist"' in footer_html
    assert 'openCartModal()' in footer_html
    assert 'href="/orders"' in footer_html

    # Column 3: AI Shopping Features
    assert "AI SHOPPING FEATURES</h4>" in footer_html
    assert 'href="/twin"' in footer_html
    assert 'href="/predictions"' in footer_html
    assert 'href="/discovery"' in footer_html
    assert 'href="/budget"' in footer_html
    assert 'href="/comparison"' in footer_html
    assert 'href="/calendar"' in footer_html
    assert 'href="/smart-cart"' in footer_html
    assert 'href="/advanced-ai"' in footer_html

    # Column 4: Customer Support
    assert "CUSTOMER SUPPORT</h4>" in footer_html
    assert 'href="/customer-service"' in footer_html
    assert 'href="/faq"' in footer_html
    assert 'href="/contact"' in footer_html
    assert 'href="/returns-refunds"' in footer_html

    # Column 5: Account & Information
    assert "ACCOUNT &amp; INFORMATION</h4>" in footer_html or "ACCOUNT & INFORMATION</h4>" in footer_html
    assert 'href="/twin"' in footer_html
    assert 'href="/login"' in footer_html
    assert 'href="/seller"' in footer_html
    assert 'href="/privacy"' in footer_html
    assert 'href="/terms"' in footer_html

    # Dynamic copyright year
    assert "© 2024–" in footer_html


def test_all_new_and_updated_routes(client):
    routes_to_test = [
        ("/seller", 200, "Merchant Hub"),
        ("/customer-service", 200, "Customer Service"),
        ("/faq", 200, "Frequently Asked Questions"),
        ("/contact", 200, "Contact PreTwin AI"),
        ("/returns-refunds", 200, "Returns &amp; Refund Policy"),
        ("/privacy", 200, "Privacy Policy"),
        ("/terms", 200, "Terms &amp; Conditions"),
        ("/notifications", 200, "Notifications &amp; Alerts"),
        ("/recommendations", 200, "Recommendations"),
        ("/smart-cart", 200, "Smart Shopping Card"),
        ("/smart-card", 200, "Smart Shopping Card"),
    ]

    for path, expected_code, expected_content in routes_to_test:
        res = client.get(path)
        assert res.status_code == expected_code, f"Route {path} returned {res.status_code}, expected {expected_code}"
        content = res.data.decode("utf-8")
        assert expected_content in content, f"Expected '{expected_content}' in response of {path}"
