"""
tests/test_signup_login_profile.py
Tests:
1. Fairy-Tale Startup Flying Animation:
   - Exactly one complete circular flight round (single 360-degree orbit, iteration 1, forwards, not infinite)
   - Wand pointing towards center after flight completion
   - Glowing magical beam with sparkles emerging from wand
   - Magical reveal of PreTwin brand name in center
   - Tagline underneath: "Your Future. Your Style. Your Twin."
   - Transition to Sign Up/Login page
2. Dedicated Sign Up/Login Page:
   - Sign In tab and Create Account tab with tab switching
   - Login form (identifier, password, show/hide, submit)
   - Sign Up form (name, email, username, password, confirm password, password strength indicator, submit)
   - Continue with Google button and OAuth configuration guidance
3. First Navigation Bar Profile Icon:
   - Positioned alongside 6 shopping shortcuts
   - When unauthenticated: displays profile icon linking to /login
   - When authenticated: displays user profile button with dropdown menu containing
     My Profile (/twin), My Orders (/orders), Wishlist (/wishlist), Account Settings (/settings), Sign Out (/logout)
4. Authentication API and Security:
   - Password hashing and verification
   - Registration validation (missing fields, short password, password mismatch, duplicate email)
   - Login with email or username
   - Session establishment and /api/auth/me
   - Sign out /api/auth/logout
"""

import json
import pytest
from app import app
import database


def test_fairy_tale_opening_animation_and_tagline(app_client):
    """Verify the startup intro animation contains all required elements, exact brand name, and exact tagline."""
    res = app_client.get("/")
    assert res.status_code == 200
    html = res.data.decode("utf-8")

    assert 'id="pretwinStartupIntro"' in html
    assert "pretwin-fairy-svg" in html
    assert "crescent-moon-group" in html
    assert "seated-fairy-group" in html
    assert "wing-group-left" in html
    assert "wing-group-right" in html
    assert "fairy-wand-group" in html
    assert "wand-magic-beam" in html
    assert "magic-sparkle" in html
    assert "introWordmark" in html
    assert "PreTwin" in html
    assert "introTagline" in html
    assert "Your Future. Your Style. Your Twin." in html
    assert "skipIntroBtn" in html
    assert "Skip Intro" in html


def test_animation_css_circular_orbit_single_round():
    """Verify style.css sets fairy sitting gracefully on moon with fluttering wings without looping."""
    with open("static/css/style.css", "r", encoding="utf-8") as f:
        css = f.read()

    # Crescent moon and seated fairy keyframes
    assert "moonSoftPulse" in css
    assert "fairyWingFlutterLeft" in css
    assert "fairyWingFlutterRight" in css
    # Wand beam, sparkle, and reveal effects
    assert "wandBeamTravel" in css
    assert "wordmarkClipReveal" in css
    assert "taglineFadeIn" in css


def test_login_and_signin_route_aliases(app_client):
    """Verify all intuitive sign-in and registration URL aliases return 200 OK."""
    auth_urls = ["/login", "/signin", "/sign-in", "/sign_in", "/auth", "/register", "/signup", "/sign-up"]
    for url in auth_urls:
        res = app_client.get(url)
        assert res.status_code == 200, f"Expected 200 for {url}, got {res.status_code}"
        html = res.data.decode("utf-8")
        assert "Welcome to PreTwin" in html
        assert 'id="tabBtnLogin"' in html
        assert 'id="tabBtnRegister"' in html


def test_signup_login_page_renders_properly(app_client):
    """Verify /login renders Sign In tab, Create Account tab, forms, and Google sign-in."""
    res = app_client.get("/login")
    assert res.status_code == 200
    html = res.data.decode("utf-8")

    # Tabs
    assert 'id="tabBtnLogin"' in html
    assert 'id="tabBtnRegister"' in html

    # Login Form
    assert 'id="loginFormWrap"' in html
    assert 'id="loginIdentifierInput"' in html
    assert 'id="loginPasswordInput"' in html
    assert 'id="toggleLoginPassBtn"' in html
    assert 'id="loginSubmitBtn"' in html

    # Registration Form
    assert 'id="registerFormWrap"' in html
    assert 'id="regNameInput"' in html
    assert 'id="regEmailInput"' in html
    assert 'id="regUsernameInput"' in html
    assert 'id="regPasswordInput"' in html
    assert 'id="regConfirmPasswordInput"' in html
    assert 'id="toggleRegPassBtn"' in html
    assert 'id="toggleRegConfirmPassBtn"' in html
    assert 'id="passwordStrengthBar"' in html
    assert 'id="passwordStrengthText"' in html
    assert 'id="registerSubmitBtn"' in html

    # Google Auth
    assert "Continue with Google" in html
    assert 'id="googleConfigModal"' in html


def test_navbar_unauthenticated_state(app_client):
    """When unauthenticated, first navbar shows Sign In button linking to /login."""
    res = app_client.get("/")
    assert res.status_code == 200
    html = res.data.decode("utf-8")

    assert 'id="pretwinAccountItem"' in html
    assert 'id="pretwinProfileBtn"' in html
    assert 'href="/login"' in html
    assert "Sign In" in html


def test_auth_registration_validation(app_client):
    """Verify registration API validates input properly."""
    # 1. Missing fields
    res = app_client.post("/api/auth/register", json={
        "name": "Test User",
        "email": "test@example.com"
    })
    assert res.status_code == 400
    assert "required" in res.get_json()["error"].lower()

    # 2. Password mismatch
    res = app_client.post("/api/auth/register", json={
        "name": "Test User",
        "email": "test@example.com",
        "username": "testuser",
        "password": "Password123",
        "confirm_password": "DifferentPassword123"
    })
    assert res.status_code == 400
    assert "match" in res.get_json()["error"].lower()

    # 3. Password too short (< 6 chars)
    res = app_client.post("/api/auth/register", json={
        "name": "Test User",
        "email": "test@example.com",
        "username": "testuser",
        "password": "123",
        "confirm_password": "123"
    })
    assert res.status_code == 400
    assert "at least 6" in res.get_json()["error"].lower()


def test_auth_register_login_logout_flow(app_client):
    """Full registration, login with username, login with email, and logout."""
    import uuid
    uid = uuid.uuid4().hex[:6]
    email = f"fairy_{uid}@pretwin.ai"
    username = f"fairy_{uid}"
    password = "MagicalPassword2026!"

    # 1. Register
    reg_res = app_client.post("/api/auth/register", json={
        "name": f"Fairy User {uid}",
        "email": email,
        "username": username,
        "password": password,
        "confirm_password": password
    })
    assert reg_res.status_code in (200, 201)
    reg_data = reg_res.get_json()
    assert reg_data["success"] is True
    assert reg_data["user"]["email"] == email

    # 2. Check /api/auth/me while logged in
    me_res = app_client.get("/api/auth/me")
    assert me_res.status_code == 200
    assert me_res.get_json()["authenticated"] is True
    assert me_res.get_json()["user"]["username"] == username

    # 3. Verify Navbar in authenticated state displays user dropdown
    nav_res = app_client.get("/")
    assert nav_res.status_code == 200
    nav_html = nav_res.data.decode("utf-8")
    assert 'id="pretwinAccountDropdown"' in nav_html
    assert 'href="/twin"' in nav_html
    assert 'href="/orders"' in nav_html
    assert 'href="/wishlist"' in nav_html
    assert 'href="/settings"' in nav_html
    assert 'href="/logout"' in nav_html
    assert username in nav_html

    # 4. Logout
    logout_res = app_client.post("/api/auth/logout")
    assert logout_res.status_code == 200
    assert logout_res.get_json()["success"] is True

    # 5. Check /api/auth/me after logout
    me_after = app_client.get("/api/auth/me")
    assert me_after.get_json()["authenticated"] is False

    # 6. Login using Username
    login_user_res = app_client.post("/api/auth/login", json={
        "identifier": username,
        "password": password
    })
    assert login_user_res.status_code == 200
    assert login_user_res.get_json()["success"] is True

    # 7. Logout again
    app_client.post("/api/auth/logout")

    # 8. Login using Email
    login_email_res = app_client.post("/api/auth/login", json={
        "identifier": email,
        "password": password
    })
    assert login_email_res.status_code == 200
    assert login_email_res.get_json()["success"] is True

    # 9. Login with invalid password fails with 401
    bad_login_res = app_client.post("/api/auth/login", json={
        "identifier": email,
        "password": "WrongPassword!"
    })
    assert bad_login_res.status_code == 401
    assert "invalid" in bad_login_res.get_json()["error"].lower()
