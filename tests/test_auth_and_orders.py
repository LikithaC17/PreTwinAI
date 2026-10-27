# -*- coding: utf-8 -*-
"""
tests/test_auth_and_orders.py
Comprehensive test suite for:
- User registration with validation and password hashing
- User login, logout, and session persistence
- Server-side checkout calculation and price validation
- Order creation and Razorpay / Sandbox payment verification
- Order history retrieval
"""

import json
import uuid
import pytest
from app import app
import database


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-key-123"
    with app.test_client() as client:
        with app.app_context():
            database.init_db()
        yield client


class TestAuthentication:
    def test_register_success(self, client):
        email = f"testuser_{uuid.uuid4().hex[:8]}@example.com"
        res = client.post("/api/auth/register", json={
            "name": "Sarah Connor",
            "email": email,
            "password": "securepassword123",
            "confirm_password": "securepassword123"
        })
        assert res.status_code == 201
        data = res.get_json()
        assert data["success"] is True
        assert data["user"]["username"] == "Sarah Connor"
        assert data["user"]["email"] == email

    def test_register_duplicate_email_fails(self, client):
        email = f"dup_{uuid.uuid4().hex[:8]}@example.com"
        # Register once
        client.post("/api/auth/register", json={
            "name": "Original User",
            "email": email,
            "password": "password123",
            "confirm_password": "password123"
        })
        # Attempt second registration with same email
        res = client.post("/api/auth/register", json={
            "name": "Duplicate User",
            "email": email,
            "password": "differentpass123",
            "confirm_password": "differentpass123"
        })
        assert res.status_code == 409
        assert "already exists" in res.get_json()["error"]

    def test_register_password_mismatch(self, client):
        res = client.post("/api/auth/register", json={
            "name": "Mismatch User",
            "email": "mismatch@example.com",
            "password": "password123",
            "confirm_password": "different123"
        })
        assert res.status_code == 400
        assert "match" in res.get_json()["error"]

    def test_login_success(self, client):
        # Test demo user login
        res = client.post("/api/auth/login", json={
            "email": "alex@demo.pretwinshop.ai",
            "password": "password123"
        })
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        assert data["user"]["email"] == "alex@demo.pretwinshop.ai"

    def test_login_invalid_password(self, client):
        res = client.post("/api/auth/login", json={
            "email": "alex@demo.pretwinshop.ai",
            "password": "wrongpassword!"
        })
        assert res.status_code == 401
        assert "Invalid" in res.get_json()["error"]

    def test_auth_me_and_logout(self, client):
        # Log in
        client.post("/api/auth/login", json={
            "email": "alex@demo.pretwinshop.ai",
            "password": "password123"
        })
        # Check /api/auth/me
        me_res = client.get("/api/auth/me")
        assert me_res.status_code == 200
        me_data = me_res.get_json()
        assert me_data["authenticated"] is True

        # Logout
        logout_res = client.post("/api/auth/logout")
        assert logout_res.status_code == 200

        # Check /api/auth/me after logout
        after_me = client.get("/api/auth/me")
        assert after_me.get_json()["authenticated"] is False


class TestCheckoutAndOrders:
    def test_checkout_calculate(self, client):
        res = client.post("/api/checkout/calculate", json={
            "items": [
                {"product_id": 1, "quantity": 2},
                {"product_id": 53, "quantity": 1}
            ]
        })
        assert res.status_code == 200
        data = res.get_json()
        assert "total_amount" in data
        assert data["total_amount"] > 0
        assert len(data["items"]) == 2
        assert data["item_count"] == 3

    def test_checkout_calculate_empty_fails(self, client):
        res = client.post("/api/checkout/calculate", json={"items": []})
        assert res.status_code == 400

    def test_create_and_verify_order(self, client):
        # 1. Create order
        create_res = client.post("/api/orders/create", json={
            "items": [{"product_id": 1, "quantity": 1}],
            "shipping_address": {
                "name": "Bruce Wayne",
                "email": "bruce@wayne.com",
                "phone": "9988776655",
                "address": "Wayne Manor, 100 Mountain Drive",
                "city": "Bengaluru",
                "state": "Karnataka",
                "pincode": "560103"
            },
            "payment_method": "PreTwin Sandbox"
        })
        assert create_res.status_code == 201
        order_data = create_res.get_json()
        assert order_data["success"] is True
        order_id = order_data["order_id"]
        order_num = order_data["order_number"]

        # 2. Verify payment in sandbox test mode
        verify_res = client.post("/api/orders/verify-payment", json={
            "order_id": order_id,
            "order_number": order_num,
            "is_sandbox_mode": True
        })
        assert verify_res.status_code == 200
        v_data = verify_res.get_json()
        assert v_data["success"] is True
        assert v_data["status"] == "Confirmed"
        assert "Paid" in v_data["payment_status"]

        # 3. Fetch single order detail
        detail_res = client.get(f"/api/orders/{order_id}")
        assert detail_res.status_code == 200
        od = detail_res.get_json()["order"]
        assert od["order_number"] == order_num
        assert len(od["items"]) == 1

    def test_cod_order_and_delivery_rewards(self, client):
        # 1. Create COD Order
        create_res = client.post("/api/orders/create", json={
            "items": [{"product_id": 1, "quantity": 1}],
            "shipping_address": {
                "name": "Clark Kent",
                "email": "clark@dailyplanet.com",
                "phone": "9876543210",
                "address": "344 Clinton St, Apt 3B",
                "city": "Metropolis",
                "state": "Delhi",
                "pincode": "110001"
            },
            "payment_method": "COD"
        })
        assert create_res.status_code == 201
        data = create_res.get_json()
        assert data["success"] is True
        assert data["is_cod"] is True
        order_id = data["order_id"]

        # 2. Check Order Status is Confirmed and Payment Status is Pending (Cash on Delivery)
        order_res = client.get(f"/api/orders/{order_id}")
        assert order_res.status_code == 200
        order = order_res.get_json()["order"]
        assert order["status"] == "Confirmed"
        assert "Cash on Delivery" in order["payment_status"]

        # 3. Mark Delivered and verify reward points (5 points) awarded strictly upon delivery
        del_res = client.post(f"/api/orders/{order_id}/mark-delivered")
        assert del_res.status_code == 200
        del_data = del_res.get_json()
        assert del_data["success"] is True
        assert del_data["reward_points_awarded"] == 5


class TestWishlistAndNavigation:
    def test_wishlist_crud(self, client):
        # 1. Initially wishlist should be queryable
        res = client.get("/api/wishlist")
        assert res.status_code == 200
        initial_items = res.get_json()["items"]

        # 2. Add product to wishlist
        add_res = client.post("/api/wishlist", json={"product_id": 1})
        assert add_res.status_code == 200
        assert add_res.get_json()["success"] is True

        # 3. Verify it is listed in wishlist
        list_res = client.get("/api/wishlist")
        assert list_res.status_code == 200
        items = list_res.get_json()["items"]
        assert any(item["id"] == 1 for item in items)

        # 4. Remove product from wishlist
        del_res = client.delete("/api/wishlist/1")
        assert del_res.status_code == 200
        assert del_res.get_json()["success"] is True

        # 5. Clear wishlist
        clear_res = client.post("/api/wishlist/clear")
        assert clear_res.status_code == 200
        assert client.get("/api/wishlist").get_json()["count"] == 0

    def test_auth_and_shortcut_template_routes(self, client):
        routes = ["/login", "/register", "/wishlist", "/orders", "/savings", "/rewards", "/smart-cart"]
        for r in routes:
            resp = client.get(r)
            assert resp.status_code == 200, f"Route {r} failed with status {resp.status_code}"

        # Logout route should redirect
        logout_resp = client.get("/logout")
        assert logout_resp.status_code == 302
