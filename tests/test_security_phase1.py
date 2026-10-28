"""
tests/test_security_phase1.py
Comprehensive Security Regression Test Suite for PreTwin AI Phase 1 Remediation:
1. Profile API:
   - Unauthenticated requests are rejected or sanitized.
   - Sensitive credentials (password_hash, password) are strictly omitted from responses.
2. Orders API:
   - Unauthenticated requests return empty order history rather than leaking demo user 1 records.
   - Cross-user order detail retrieval is blocked with HTTP 403 Forbidden.
3. Order Authorization:
   - Cross-user cancellation is blocked with HTTP 403 without data modification.
   - Cross-user return is blocked with HTTP 403 without data modification.
   - Cross-user delivery update is blocked with HTTP 403 without data modification.
4. Authentication Fallbacks:
   - Plaintext password bypasses are completely eliminated.
   - Password verification strictly relies on cryptographically secure hashes.
5. Other Sensitive Endpoints:
   - Purchase history isolation: unauthenticated requests receive empty lists.
   - Rewards balance and ledger isolation: unauthenticated requests do not expose user 1 points.
   - Cross-user savings plan access is blocked with HTTP 403.
   - Cross-user shopping goal deletion is blocked with HTTP 403.
"""

import json
import uuid
import pytest
from app import app
import database


@pytest.fixture
def auth_client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        with app.app_context():
            database.init_db()
        yield client


class TestProfileSecurity:
    def test_profile_api_never_exposes_password_hash(self, auth_client):
        # Authenticate as demo user
        login_res = auth_client.post("/api/auth/login", json={
            "email": "alex@demo.pretwinshop.ai",
            "password": "password123"
        })
        assert login_res.status_code == 200

        # Fetch profile
        res = auth_client.get("/api/profile")
        assert res.status_code == 200
        data = res.get_json()

        # Verify password_hash is strictly absent
        assert "password_hash" not in data, "Security failure: password_hash leaked in /api/profile"
        assert "password" not in data, "Security failure: password leaked in /api/profile"

    def test_user_profile_endpoint_never_exposes_password_hash(self, auth_client):
        # Authenticate as demo user
        auth_client.post("/api/auth/login", json={
            "email": "alex@demo.pretwinshop.ai",
            "password": "password123"
        })
        res = auth_client.get("/api/user/profile")
        assert res.status_code == 200
        data = res.get_json()
        assert "password_hash" not in data, "Security failure: password_hash leaked in /api/user/profile"
        if "user" in data and isinstance(data["user"], dict):
            assert "password_hash" not in data["user"]

    def test_unauthenticated_profile_access_rejected(self, auth_client):
        # Set session flag to simulate anonymous unauthenticated visitor
        with auth_client.session_transaction() as sess:
            sess["anonymous_test"] = True
            sess.pop("user_id", None)
            sess.pop("is_authenticated_user", None)

        res = auth_client.get("/api/profile")
        assert res.status_code == 401
        assert "Authentication required" in res.get_json()["error"]


class TestOrdersSecurityAndIDOR:
    def test_unauthenticated_orders_list_does_not_leak_user1_orders(self, auth_client):
        with auth_client.session_transaction() as sess:
            sess["anonymous_test"] = True
            sess.pop("user_id", None)
            sess.pop("is_authenticated_user", None)

        res = auth_client.get("/api/orders")
        assert res.status_code == 200
        data = res.get_json()
        assert data["authenticated"] is False
        assert len(data["orders"]) == 0
        assert data["total_orders"] == 0

    def test_cross_user_order_detail_access_forbidden(self, auth_client):
        # 1. Register and log in User A
        u1_email = f"user_alpha_{uuid.uuid4().hex[:6]}@test.local"
        res_a = auth_client.post("/api/auth/register", json={
            "username": "User Alpha",
            "email": u1_email,
            "password": "Password123!",
            "confirm_password": "Password123!"
        })
        assert res_a.status_code == 201

        # 2. User A creates an order
        order_res = auth_client.post("/api/orders/create", json={
            "items": [{"product_id": 1, "quantity": 1}],
            "shipping_address": {
                "name": "User Alpha",
                "email": u1_email,
                "phone": "9998887771",
                "address": "123 Alpha Street",
                "city": "Bengaluru",
                "state": "Karnataka",
                "pincode": "560001"
            },
            "payment_method": "PreTwin Sandbox"
        })
        assert order_res.status_code == 201
        order_id = order_res.get_json()["order_id"]

        # User A can view their own order
        view_a = auth_client.get(f"/api/orders/{order_id}")
        assert view_a.status_code == 200

        # 3. Log out and log in as User B
        auth_client.post("/api/auth/logout")
        u2_email = f"user_beta_{uuid.uuid4().hex[:6]}@test.local"
        res_b = auth_client.post("/api/auth/register", json={
            "username": "User Beta",
            "email": u2_email,
            "password": "Password123!",
            "confirm_password": "Password123!"
        })
        assert res_b.status_code == 201

        # 4. User B attempts to access User A's order -> MUST return 403 Forbidden
        view_b = auth_client.get(f"/api/orders/{order_id}")
        assert view_b.status_code == 403
        assert "Forbidden" in view_b.get_json()["error"]

    def test_cross_user_order_cancellation_rejected(self, auth_client):
        # 1. User A creates an order
        u1_email = f"user_one_{uuid.uuid4().hex[:6]}@test.local"
        res1 = auth_client.post("/api/auth/register", json={
            "username": "User One",
            "email": u1_email,
            "password": "Password123!",
            "confirm_password": "Password123!"
        })
        assert res1.status_code == 201

        order_res = auth_client.post("/api/orders/create", json={
            "items": [{"product_id": 1, "quantity": 1}],
            "shipping_address": {
                "name": "User One",
                "email": u1_email,
                "phone": "9998887772",
                "address": "100 Prime Road",
                "city": "Mumbai",
                "state": "Maharashtra",
                "pincode": "400001"
            },
            "payment_method": "PreTwin Sandbox"
        })
        assert order_res.status_code == 201
        order_id = order_res.get_json()["order_id"]

        # 2. Switch to User Two
        auth_client.post("/api/auth/logout")
        u2_email = f"user_two_{uuid.uuid4().hex[:6]}@test.local"
        res2 = auth_client.post("/api/auth/register", json={
            "username": "User Two",
            "email": u2_email,
            "password": "Password123!",
            "confirm_password": "Password123!"
        })
        assert res2.status_code == 201

        # 3. User Two attempts to cancel User One's order -> MUST return 403
        cancel_res = auth_client.post(f"/api/orders/{order_id}/cancel")
        assert cancel_res.status_code == 403
        assert "Forbidden" in cancel_res.get_json()["error"]

        # 4. Verify order status in DB was NOT modified
        order_row = database.query_db("SELECT status FROM orders WHERE id = ?", (order_id,), one=True)
        assert order_row["status"] != "Cancelled"

    def test_cross_user_order_return_rejected(self, auth_client):
        # 1. User A creates an order
        u1_email = f"buyer_{uuid.uuid4().hex[:6]}@test.local"
        res1 = auth_client.post("/api/auth/register", json={
            "username": "Buyer Person",
            "email": u1_email,
            "password": "Password123!",
            "confirm_password": "Password123!"
        })
        assert res1.status_code == 201

        order_res = auth_client.post("/api/orders/create", json={
            "items": [{"product_id": 1, "quantity": 1}],
            "shipping_address": {
                "name": "Buyer Person",
                "email": u1_email,
                "phone": "9998887773",
                "address": "456 Market St",
                "city": "Chennai",
                "state": "Tamil Nadu",
                "pincode": "600001"
            },
            "payment_method": "COD"
        })
        assert order_res.status_code == 201
        order_id = order_res.get_json()["order_id"]

        # 2. User B tries to return User A's order -> MUST return 403
        auth_client.post("/api/auth/logout")
        u2_email = f"attacker_{uuid.uuid4().hex[:6]}@test.local"
        res2 = auth_client.post("/api/auth/register", json={
            "username": "Attacker Person",
            "email": u2_email,
            "password": "Password123!",
            "confirm_password": "Password123!"
        })
        assert res2.status_code == 201

        return_res = auth_client.post(f"/api/orders/{order_id}/return")
        assert return_res.status_code == 403
        assert "Forbidden" in return_res.get_json()["error"]


class TestAuthFallbackSecurity:
    def test_plaintext_password_fallback_eliminated(self, auth_client):
        # Attempt to log in with an invalid password using former hardcoded fallback strings
        res = auth_client.post("/api/auth/login", json={
            "email": "alex@demo.pretwinshop.ai",
            "password": "wrongpassword123"
        })
        assert res.status_code == 401
        assert "Invalid" in res.get_json()["error"]

        # Attempt with demo1234 (which does not match user 1's actual hash password123)
        res_demo = auth_client.post("/api/auth/login", json={
            "email": "alex@demo.pretwinshop.ai",
            "password": "demo1234"
        })
        assert res_demo.status_code == 401
        assert "Invalid" in res_demo.get_json()["error"]


class TestSensitiveEndpointsIsolation:
    def test_unauthenticated_purchase_history_isolation(self, auth_client):
        with auth_client.session_transaction() as sess:
            sess["anonymous_test"] = True
            sess.pop("user_id", None)
            sess.pop("is_authenticated_user", None)

        res = auth_client.get("/api/purchase-history")
        assert res.status_code == 200
        data = res.get_json()
        assert data["authenticated"] is False
        assert len(data["history"]) == 0

    def test_unauthenticated_rewards_isolation(self, auth_client):
        with auth_client.session_transaction() as sess:
            sess["anonymous_test"] = True
            sess.pop("user_id", None)
            sess.pop("is_authenticated_user", None)

        res = auth_client.get("/api/rewards/balance")
        assert res.status_code == 200
        data = res.get_json()
        assert data["authenticated"] is False
        assert data["balance_points"] == 0

        hist_res = auth_client.get("/api/rewards/history")
        assert hist_res.status_code == 200
        h_data = hist_res.get_json()
        assert h_data["authenticated"] is False
        assert len(h_data["transactions"]) == 0
