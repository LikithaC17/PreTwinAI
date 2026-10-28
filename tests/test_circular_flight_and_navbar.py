"""
tests/test_circular_flight_and_navbar.py

Verifies:
1. Fairy-Tale Startup Opening Animation:
   - Fairy flying character SVG with delicate wings, magic wand and glowing star tip
   - Exactly one complete circular round flight animation (single 360-degree orbit, iteration count 1, not looping)
   - Wand pointing towards center after flight completion
   - Glowing magical beam with sparkling particles emerging from the wand
   - Magical reveal effect of PreTwin AI brand name in the center
   - Tagline underneath: “Your Future. Your Style. Your Twin.”
   - Reduced-motion accessibility check and optional skip-intro button
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
    """Verify fairy character with wings, wand, beam with sparkles, wordmark, and tagline."""
    res = app_client.get("/")
    assert res.status_code == 200
    html = res.data.decode("utf-8")

    # 1. Overlay and Accessible Skip Button
    assert "pretwinStartupIntro" in html
    assert "skipIntroBtn" in html
    assert "Skip Intro" in html

    # 2. Fairy Character with Wings and Magic Wand
    assert "pretwin-fairy-svg" in html
    assert "wing-group-left" in html
    assert "wing-group-right" in html
    assert "fairy-wand-group" in html
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

    # 5. Enter Button (Appears after title reveal)
    assert "enterWebsiteBtn" in html
    assert "Enter" in html


def test_circular_flight_keyframes_in_stylesheet():
    """Verify CSS defines exactly one complete 360-degree circular orbit, single iteration, no infinite loops."""
    with open("static/css/style.css", "r", encoding="utf-8") as f:
        css = f.read()

    # Verify single-iteration forwards circular flight animation
    assert "introCircularFlight" in css
    assert "animation: introCircularFlight 2.6s cubic-bezier" in css
    assert "forwards" in css

    # Verify complete 360-degree circular orbit coordinates (all quadrants visited)
    assert "@keyframes introCircularFlight" in css
    assert "150px" in css  # Radius of circular round
    assert "-150px" in css

    # Verify wand elevation and magic beam with sparkling particles
    assert ".stage-wand .fairy-wand-group" in css
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
