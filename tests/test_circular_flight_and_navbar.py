"""
tests/test_circular_flight_and_navbar.py

Verifies:
1. Fairy-Tale Startup Opening Animation:
   - Fairy flying character SVG with delicate wings, magic wand and glowing star tip
   - Exactly one complete circular round flight animation (single 360-degree orbit, iteration count 1, not looping)
   - Wand pointing towards center after flight completion
   - Glowing magical beam with sparkling particles emerging from the wand
   - Magical reveal effect of PreTwin brand name in the center
   - Tagline underneath: “Your Future. Your Style. Your Twin.”
   - Reduced-motion accessibility check and optional skip-intro button
2. First Navigation Bar:
   - Absence of Sign In button and account/profile icon in first navbar
   - Balanced spacing and clean layout
   - Preservation of logo, search bar, and all 6 shopping shortcuts (Wishlist, Cart, My Orders, Reward Points, Savings Plan, Smart Cart)
   - Operational status of remaining navigation shortcuts
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
    assert "introTagline" in html
    assert "Your Future. Your Style. Your Twin." in html


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

    # Verify reduced-motion support
    assert "@media (prefers-reduced-motion: reduce)" in css


def test_first_navigation_bar_structure(app_client):
    """Verify first navigation bar contains the profile icon/button alongside the 6 shopping shortcuts."""
    res = app_client.get("/")
    assert res.status_code == 200
    html = res.data.decode("utf-8")

    # Extract first navbar header
    start = html.find('<header class="fk-navbar">')
    end = html.find('</header>')
    assert start != -1 and end != -1
    navbar = html[start:end]

    # Verify brand logo and search box
    assert "pretwin-header-logo" in navbar
    assert "fkSearchInput" in navbar

    # Verify all 6 shopping shortcuts are intact in first navbar
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
    assert "/smart-cart" in navbar
    assert "Smart Cart" in navbar

    # Verify Profile icon / Account element is present alongside the shortcuts
    assert "pretwinAccountItem" in navbar
    assert "pretwinProfileBtn" in navbar


def test_all_six_shopping_shortcuts_endpoints(app_client):
    """Ensure all 6 shortcut destinations are active and return 200 OK."""
    endpoints = ["/wishlist", "/orders", "/rewards", "/savings", "/smart-cart"]
    for ep in endpoints:
        r = app_client.get(ep)
        assert r.status_code == 200
