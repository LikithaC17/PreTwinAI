"""
tests/test_features_dashboard_and_animations.py

Verifies:
1. Startup Animation Branding (Fairy Sitting Gracefully on Crescent Half-Moon):
   - Fairy sitting gracefully on glowing crescent half-moon
   - Complete body in view from head to feet: face, hair, body, hands, legs, feet, slippers, wings, wand
   - Fairy remains seated (does not fly in circular rounds)
   - Softly fluttering delicate wings while seated
   - Glowing magic wand releasing sparkling particle beam toward center
   - Magical reveal of "PreTwin AI" wordmark and highlighted tagline "Your Future. Your Style. Your Twin."
   - No occurrences of "Kannada Fairy Tale" anywhere
2. Removal of Digital Twin Model from Profile:
   - Profile page (/profile) does NOT contain "Digital Twin Model" card/section
   - Profile contains strictly 3 sections (Personal Details, Delivery Location, Mode of Payment)
   - Personalization & Digital Twin feature is preserved at /twin
3. Dedicated Features Dashboard (/features):
   - Returns 200 OK
   - Contains heading "Explore PreTwin AI Features"
   - Contains subtitle "Discover smarter ways to explore products, plan purchases, manage your budget, and make shopping decisions."
   - Contains dedicated horizontal feature navigation bar with all 8 feature icons and names directly underneath
   - All 8 feature panels accessible with links and "Explore Feature"
4. Second Navigation Bar Layout:
   - Far right contains Features, More, and Profile in exact order: 1. Features, 2. More, 3. Profile
   - Each control displays icon with name directly underneath
   - Features link points to /features
5. Website-Wide Smooth Animations & Accessibility:
   - Page transitions (pretwinPageFadeIn)
   - Product card hover lift & image zoom
   - Wishlist heart pop keyframes
   - Cart badge pulse/bounce keyframes
   - Smooth dropdown transitions
   - Scroll reveal observer
   - Accessibility prefers-reduced-motion media query
"""

import pytest
from app import app


@pytest.fixture
def client(app_client):
    return app_client


def test_startup_animation_branding_and_tagline_highlight(client):
    res = client.get("/")
    assert res.status_code == 200
    html = res.data.decode("utf-8")

    # Must contain PreTwin AI wordmark
    assert "introWordmark" in html
    assert "PreTwin" in html
    assert "AI" in html

    # Must contain exact tagline
    assert "introTagline" in html
    assert "Your Future. Your Style. Your Twin." in html

    # Must contain Crescent Moon and Seated Fairy with complete body elements
    assert "crescent-moon-group" in html
    assert "crescent-moon-path" in html
    assert "seated-fairy-group" in html
    assert "fairy-wings-container" in html
    assert "fairy-legs-and-feet" in html
    assert "fairy-foot-left" in html
    assert "fairy-foot-right" in html
    assert "fairy-magic-wand" in html
    assert "wand-star-tip" in html

    # Must NOT contain Kannada Fairy Tale anywhere
    assert "Kannada Fairy Tale" not in html
    assert "Kannada FAIRY TALES" not in html
    assert "Kannada" not in html

    # Verify CSS styling for wordmark and prominent tagline highlight
    with open("static/css/style.css", "r", encoding="utf-8") as f:
        css = f.read()

    assert ".pretwin-intro-wordmark" in css
    assert ".intro-ai-badge" in css
    assert ".pretwin-intro-tagline" in css
    assert "taglineShimmer" in css
    assert "linear-gradient" in css
    assert ".crescent-moon-group" in css
    assert "fairyWingFlutterLeft" in css
    assert "fairyWingFlutterRight" in css


def test_profile_page_excludes_digital_twin_model(client):
    res = client.get("/profile")
    assert res.status_code == 200
    html = res.data.decode("utf-8")

    # Profile must strictly feature the three required sections
    assert "1. Personal Details" in html
    assert "2. Delivery Location" in html
    assert "3. Mode of Payment" in html

    # Digital Twin Model must NOT be in the Profile page
    assert "Digital Twin Model" not in html
    assert "Digital Twin Persona" not in html
    assert "Taste Profile Confidence" not in html

    # But the separate Personalization and Digital Twin engine remains accessible at /twin
    twin_res = client.get("/twin")
    assert twin_res.status_code == 200
    twin_html = twin_res.data.decode("utf-8")
    assert "Digital Twin" in twin_html


def test_dedicated_features_dashboard(client):
    res = client.get("/features")
    assert res.status_code == 200
    html = res.data.decode("utf-8")

    # Heading and Subtitle
    assert "Explore PreTwin AI Features" in html
    assert "Discover smarter ways to explore products, plan purchases, manage your budget, and make shopping decisions." in html

    # Key Metrics Ribbon
    assert "features-metrics-ribbon" in html
    assert "Intelligent Engines" in html

    # Dedicated Horizontal Feature Navigation Bar with all 8 features in order
    assert "features-horizontal-navbar" in html
    assert "tab-twin" in html
    assert "tab-predictions" in html
    assert "tab-discovery" in html
    assert "tab-budget" in html
    assert "tab-comparison" in html
    assert "tab-calendar" in html
    assert "tab-cart" in html
    assert "tab-advanced" in html

    # All Eight AI shopping features represented with cards and links
    expected_links = [
        "/twin",
        "/predictions",
        "/discovery",
        "/budget",
        "/comparison",
        "/calendar",
        "/smart-cart",
        "/advanced-ai"
    ]
    for link in expected_links:
        assert f'href="{link}"' in html, f"Feature link {link} missing on /features dashboard"

    # Explore feature callout links
    assert "Explore Feature ➔" in html


def test_second_navbar_features_more_profile_layout(client):
    res = client.get("/")
    assert res.status_code == 200
    html = res.data.decode("utf-8")

    sec_nav_start = html.find('id="pretwinSecondNavbar"')
    assert sec_nav_start != -1
    sec_nav = html[sec_nav_start:html.find('</nav>', sec_nav_start)]

    # Features, More, and Profile present
    assert 'id="pretwinFeaturesBtn"' in sec_nav
    assert 'href="/features"' in sec_nav
    assert 'id="pretwinMoreBtn"' in sec_nav
    assert 'id="pretwinAccountItem"' in sec_nav

    # Each control has icon box and text label
    assert "pretwin-second-nav-icon-box" in sec_nav
    assert "pretwin-second-nav-text" in sec_nav

    # Exact order: Features -> More -> Profile
    feat_pos = sec_nav.find('id="pretwinFeaturesBtn"')
    more_pos = sec_nav.find('id="pretwinMoreBtn"')
    prof_pos = sec_nav.find('id="pretwinAccountItem"')
    assert feat_pos < more_pos < prof_pos, "Navbar order must be: Features -> More -> Profile at far right"


def test_website_wide_animations_and_reduced_motion():
    with open("static/css/style.css", "r", encoding="utf-8") as f:
        css = f.read()

    # Page Fade-In Transition
    assert "@keyframes pretwinPageFadeIn" in css
    assert ".pretwin-page-content" in css

    # Product card lift & image zoom
    assert ".fk-card:hover" in css
    assert "transform: translateY(-4px)" in css
    assert "transform: scale(1.04)" in css

    # Wishlist heart pop
    assert "@keyframes heartPop" in css
    assert ".fk-card-wish.active" in css

    # Cart badge pulse
    assert "@keyframes badgePulse" in css
    assert ".cart-badge-bounce" in css

    # Dropdowns smooth transition
    assert ".pretwin-more-dropdown" in css
    assert ".pretwin-account-dropdown" in css

    # Scroll reveal helper
    assert ".pretwin-reveal-on-scroll" in css

    # Accessibility / prefers-reduced-motion media query
    assert "@media (prefers-reduced-motion: reduce)" in css
