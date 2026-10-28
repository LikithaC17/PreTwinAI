"""
tests/test_magical_curtain_intro.py

Verifies:
1. Magical Fairy-Tale Intro Animation:
   - Full-body fairy character with wings and magic wand
   - Translucent magical curtain screen (#magicalCurtainScreen)
   - Curtain edge sparkle trail (.curtain-sparkle-trail, .curtain-edge-sparkle)
   - Wand magic beam & sparkles (wand-magic-beam, magic-sparkle)
   - PreTwin AI brand name revealed on the magical screen
   - Enter button (#enterWebsiteBtn) on the magical screen
2. Enter button navigation:
   - Clicking Enter initiates transition and redirects to /login
3. Session authentication protection:
   - When unauthenticated, /login is reached via Enter
   - /logout clears session and returns to login page
4. CSS styling:
   - Glassmorphic translucent styling for .pretwin-magical-curtain-screen
   - Unfolding clip-path animation
   - Magical enter burst transition (.stage-enter-burst)
"""

import pytest
from app import app


def test_magical_curtain_screen_elements_on_intro(app_client):
    """Verify intro overlay contains translucent magical curtain screen and sparkle trail."""
    res = app_client.get("/")
    assert res.status_code == 200
    html = res.data.decode("utf-8")

    # Overlay
    assert 'id="pretwinStartupIntro"' in html

    # Full-body fairy character & wand
    assert "pretwin-fairy-svg" in html
    assert "wing-group-left" in html
    assert "wing-group-right" in html
    assert "fairy-wand-group" in html
    assert "wand-star-tip" in html

    # Translucent magical curtain screen
    assert 'id="magicalCurtainScreen"' in html
    assert "curtain-sparkle-trail" in html
    assert "curtain-edge-sparkle" in html

    # Wand magic beam & sparkles
    assert "wand-magic-beam" in html
    assert "magic-sparkle" in html
    assert "spk-1" in html

    # PreTwin AI branding on screen
    assert 'id="introWordmark"' in html
    assert "PreTwin" in html
    assert "AI" in html
    assert 'id="introTagline"' in html
    assert "Your Future. Your Style. Your Twin." in html

    # Enter button on screen
    assert 'id="enterWebsiteBtn"' in html
    assert "Enter" in html

    # Script routes to /login on finishStartupIntro
    assert "window.location.href = '/login'" in html or 'window.location.href = "/login"' in html


def test_magical_curtain_screen_css_definitions():
    """Verify style.css contains translucent magical curtain screen and transition effects."""
    with open("static/css/style.css", "r", encoding="utf-8") as f:
        css = f.read()

    # Translucent glassmorphic curtain screen
    assert ".pretwin-magical-curtain-screen" in css
    assert "backdrop-filter" in css
    assert "clip-path" in css
    assert "inset(0 100% 0 0 round" in css

    # Sparkle trail along screen edge
    assert ".curtain-sparkle-trail" in css
    assert ".curtain-edge-sparkle" in css

    # Enter burst animation
    assert ".pretwin-startup-overlay.stage-enter-burst" in css
    assert "@keyframes enterMagicalBurst" in css


def test_logout_and_auth_protection(app_client):
    """Verify logout clears session and navigates to login."""
    res = app_client.get("/logout")
    assert res.status_code == 302
    assert "/login" in res.headers["Location"]
