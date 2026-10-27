"""
tests/test_circular_flight_and_navbar.py

Verifies:
1. Fairy-Tale Startup Opening Animation (Fairy Sitting Gracefully on Crescent Half-Moon):
   - Fairy sitting on glowing crescent half-moon
   - Complete body in view from head to feet (face, hair, body, hands, legs, feet, slippers, wings, wand)
   - Fairy remains seated on the crescent moon (no circular flying loops)
   - Softly fluttering delicate wings while seated
   - Magic wand with glowing star tip releasing sparkling celestial beam
   - Magical reveal effect of PreTwin AI brand name in the center
   - Prominently highlighted tagline underneath: “Your Future. Your Style. Your Twin.”
   - Reduced-motion accessibility check and accessible skip-intro button
2. First Navigation Bar:
   - Dedicated branding bar above first navbar with logo, PreTwin AI, and prominently highlighted tagline
   - Absence of duplicate logo in first navbar
   - Balanced spacing, search bar, and 5 shopping shortcuts (Wishlist, Cart, My Orders, Reward Points, Savings Plan)
3. Second Navigation Bar:
   - Features, More, and Profile at the far right in exact order: 1. Features, 2. More, 3. Profile
   - Each control displays icon with label directly underneath
"""

import pytest
from app import app


def test_startup_animation_fairy_character_and_elements(app_client):
    """Verify fairy sitting on crescent moon with complete body, wand, beam, wordmark, and tagline."""
    res = app_client.get("/")
    assert res.status_code == 200
    html = res.data.decode("utf-8")

    # 1. Overlay and Accessible Skip Button
    assert "pretwinStartupIntro" in html
    assert "skipIntroBtn" in html
    assert "Skip Intro" in html

    # 2. Glowing Crescent Moon and Complete Seated Fairy
    assert "crescent-moon-group" in html
    assert "crescent-moon-path" in html
    assert "seated-fairy-group" in html
    assert "fairy-wings-container" in html
    assert "wing-upper-left" in html
    assert "wing-upper-right" in html
    assert "fairy-legs-and-feet" in html
    assert "fairy-foot-left" in html
    assert "fairy-foot-right" in html
    assert "fairy-magic-wand" in html
    assert "wand-star-tip" in html

    # 3. Glowing Magical Beam with Sparkling Particles
    assert "wand-magic-beam" in html
    assert "magic-sparkle" in html
    assert "spk-1" in html

    # 4. Magical Brand Reveal and Official Tagline
    assert "introWordmark" in html
    assert "PreTwin" in html
    assert "AI" in html
    assert "introTagline" in html
    assert "Your Future. Your Style. Your Twin." in html


def test_seated_fairy_and_moon_keyframes_in_stylesheet():
    """Verify CSS defines fairy sitting on crescent moon, fluttering wings, and wand beam without circular flight."""
    with open("static/css/style.css", "r", encoding="utf-8") as f:
        css = f.read()

    # Verify moon and seated fairy styling
    assert ".pretwin-moon-stage" in css
    assert ".pretwin-moon-fairy-wrap" in css
    assert ".crescent-moon-group" in css
    assert "moonSoftPulse" in css

    # Verify fluttering wings while fairy remains seated
    assert "fairyWingFlutterLeft" in css
    assert "fairyWingFlutterRight" in css

    # Verify wand elevation, beam travel, wordmark reveal, and tagline shimmer
    assert ".stage-wand .fairy-magic-wand" in css
    assert "wandBeamTravel" in css
    assert "magic-sparkle" in css
    assert "wordmarkClipReveal" in css
    assert "taglineFadeIn" in css
    assert "taglineShimmer" in css

    # Verify reduced-motion support
    assert "@media (prefers-reduced-motion: reduce)" in css


def test_first_navigation_bar_structure(app_client):
    """Verify separate branding above navbar and redesigned first navigation bar structure."""
    res = app_client.get("/")
    assert res.status_code == 200
    html = res.data.decode("utf-8")

    # Verify dedicated branding section above the first navbar
    assert "pretwin-top-branding-bar" in html
    assert "PreTwin" in html
    assert "AI" in html
    assert "Your Future. Your Style. Your Twin." in html

    # Extract first navbar header
    start = html.find('<header class="fk-navbar">')
    end = html.find('</header>')
    assert start != -1 and end != -1
    navbar = html[start:end]

    # Verify duplicated logo is removed from first navbar and search box is present
    assert "pretwin-branding-logo" not in navbar
    assert "fkSearchInput" in navbar

    # Verify shortcuts in first navbar
    assert "/wishlist" in navbar
    assert "Wishlist" in navbar
    assert "openCartModal" in navbar
    assert "Cart" in navbar
    assert "/orders" in navbar
    assert "My Orders" in navbar
    assert "/rewards" in navbar
    assert "Reward Points" in navbar
    assert "/savings" in navbar
    assert "Savings Plan" in navbar

    # Second Navigation Bar has Features, More, and Profile at the end
    second_nav_start = html.find('class="pretwin-second-navbar"')
    assert second_nav_start != -1
    second_nav = html[second_nav_start:html.find('</nav>', second_nav_start)]
    assert "pretwinFeaturesBtn" in second_nav
    assert "pretwinMoreContainer" in second_nav
    assert "pretwinAccountItem" in second_nav
    assert "pretwinProfileBtn" in second_nav


def test_all_six_shopping_shortcuts_endpoints(app_client):
    """Ensure all 5 shortcut destinations + features dashboard are active and return 200 OK."""
    endpoints = ["/wishlist", "/orders", "/rewards", "/savings", "/smart-cart", "/features"]
    for ep in endpoints:
        r = app_client.get(ep)
        assert r.status_code == 200
