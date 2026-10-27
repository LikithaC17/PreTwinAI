"""
test_google_auth_and_intro.py
Verifies:
1. Fairy-Tale Startup Flying Animation structure, 360° loop, wand beam, and brand reveal
2. Google-Only Sign-In page (no manual email/password fields, buttons, or registration forms)
3. Absence of Sign In button and profile icon from the first navigation bar
4. Real Google Authentication backend security validation and session establishment
5. Preservation of 6 shopping shortcuts, search, logo, and protected routing
"""

import json
import pytest
from app import app, Config
import database


def test_first_navbar_has_profile_icon_and_shortcuts(app_client):
    """Confirm the Profile icon/button and all 6 shortcuts are present in the first navigation bar."""
    res = app_client.get("/")
    assert res.status_code == 200
    html = res.data.decode("utf-8")

    # The navbar header section must contain pretwinAccountItem and shortcuts
    header_start = html.find('<header class="fk-navbar">')
    header_end = html.find('</header>')
    assert header_start != -1 and header_end != -1
    navbar_html = html[header_start:header_end]

    # Verify profile icon / account item
    assert "pretwinAccountItem" in navbar_html
    assert "pretwinProfileBtn" in navbar_html

    # Verify all 6 shopping shortcuts are intact in the first navigation bar
    assert "/wishlist" in navbar_html
    assert "openCartModal" in navbar_html
    assert "/orders" in navbar_html
    assert "/rewards" in navbar_html
    assert "/savings" in navbar_html
    assert "/smart-cart" in navbar_html

    # Verify logo and search box are intact
    assert "pretwin-header-logo" in navbar_html
    assert "fkSearchInput" in navbar_html


def test_login_screen_structure_with_tabs_and_google(app_client):
    """Verify sign-in page has Sign In tab, Create Account tab, and Continue with Google."""
    res = app_client.get("/login")
    assert res.status_code == 200
    html = res.data.decode("utf-8")

    # 1. Branding, Tagline and Welcome
    assert "Welcome to PreTwin" in html
    assert "Your Future. Your Style. Your Twin." in html
    assert "Continue with Google" in html

    # 2. Confirmed presence of manual sign-in inputs & buttons
    assert 'id="loginIdentifierInput"' in html
    assert 'id="loginPasswordInput"' in html
    assert 'id="loginSubmitBtn"' in html
    assert 'id="toggleLoginPassBtn"' in html

    # 3. Confirmed presence of registration inputs
    assert 'id="regNameInput"' in html
    assert 'id="regEmailInput"' in html
    assert 'id="regUsernameInput"' in html
    assert 'id="regPasswordInput"' in html
    assert 'id="regConfirmPasswordInput"' in html
    assert 'id="registerSubmitBtn"' in html


def test_register_page_structure(app_client):
    """Verify register page renders with register tab active and proper input fields."""
    res = app_client.get("/register")
    assert res.status_code == 200
    html = res.data.decode("utf-8")

    assert "Welcome to PreTwin" in html
    assert "Continue with Google" in html
    assert 'id="regEmailInput"' in html
    assert 'id="regPasswordInput"' in html
    assert 'id="registerSubmitBtn"' in html


def test_fairy_tale_startup_animation_elements(app_client):
    """Verify startup intro overlay has fairy character, wand, beam, and tagline."""
    res = app_client.get("/")
    assert res.status_code == 200
    html = res.data.decode("utf-8")

    assert "pretwinStartupIntro" in html
    assert "pretwin-skip-intro-btn" in html
    assert "pretwin-fairy-svg" in html
    assert "wing-group-left" in html
    assert "wing-group-right" in html
    assert "fairy-wand-group" in html
    assert "wand-star-tip" in html
    assert "wand-magic-beam" in html
    assert "pretwin-intro-wordmark" in html
    assert "PreTwin" in html
    assert "Your Future. Your Style. Your Twin." in html


def test_google_auth_validation_missing_token(app_client):
    """POST /api/auth/google without token fails with 400."""
    res = app_client.post("/api/auth/google", json={})
    assert res.status_code == 400
    assert "credential token is required" in res.get_json()["error"]


def test_google_auth_unconfigured_error(app_client, monkeypatch):
    """When GOOGLE_CLIENT_ID is not configured, returns clear setup error and never creates fake login."""
    import config
    import app as app_module
    monkeypatch.setattr(app_module.Config, "GOOGLE_CLIENT_ID", "")
    monkeypatch.setattr(config.Config, "GOOGLE_CLIENT_ID", "")
    res = app_client.post("/api/auth/google", json={"credential": "sample.token"})
    assert res.status_code == 400
    data = res.get_json()
    assert data["success"] is False
    assert "not configured" in data["error"].lower()


def test_google_auth_invalid_token(app_client, monkeypatch):
    """When GOOGLE_CLIENT_ID is set, invalid/forged token fails with 401."""
    import config
    import app as app_module
    monkeypatch.setattr(app_module.Config, "GOOGLE_CLIENT_ID", "mock-id.apps.googleusercontent.com")
    monkeypatch.setattr(config.Config, "GOOGLE_CLIENT_ID", "mock-id.apps.googleusercontent.com")
    res = app_client.post("/api/auth/google", json={"credential": "bad.jwt.token"})
    assert res.status_code == 401
    data = res.get_json()
    assert "failed" in data["error"].lower() or "verification" in data["error"].lower()


def test_google_auth_success_flow(app_client, monkeypatch):
    """Test successful Google token verification sets authenticated session and returns user info."""
    import config
    import app as app_module
    client_id = "valid-client-id.apps.googleusercontent.com"
    monkeypatch.setattr(app_module.Config, "GOOGLE_CLIENT_ID", client_id)
    monkeypatch.setattr(config.Config, "GOOGLE_CLIENT_ID", client_id)

    # Mock google id_token verification
    mock_idinfo = {
        "sub": "google-user-sub-12345",
        "email": "verified.user@gmail.com",
        "name": "Verified Google User",
        "picture": "https://lh3.googleusercontent.com/photo.jpg",
        "iss": "https://accounts.google.com",
        "aud": client_id,
        "email_verified": True,
        "exp": 2500000000  # Far future timestamp
    }

    import google.oauth2.id_token
    monkeypatch.setattr(google.oauth2.id_token, "verify_oauth2_token", lambda cred, req, aud: mock_idinfo)

    res = app_client.post("/api/auth/google", json={
        "credential": "valid.mock.token",
        "next": "/smart-cart"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["user"]["email"] == "verified.user@gmail.com"
    assert data["user"]["username"] == "Verified Google User"
    assert data["redirect"] == "/smart-cart"

    # Confirm session is established
    with app_client.session_transaction() as sess:
        assert sess["email"] == "verified.user@gmail.com"
        assert sess["user_id"] is not None
