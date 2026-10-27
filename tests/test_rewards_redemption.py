"""
End-to-End Test Suite for PreTwin Reward Points & Redemption
Tests:
1. Balance retrieval (auto-seeds 500 welcome bonus points = ₹5.00 for new users)
2. Daily/welcome loyalty bonus claim (+200 points = ₹2.00)
3. Points redemption on Rewards page (/api/rewards/redeem)
4. Session active credit verification (/api/rewards/active-credit)
5. Checkout calculation with redeemed points (/api/checkout/calculate)
6. Order creation with reward points discount applied (/api/orders/create)
7. Transaction history in reward ledger (/api/rewards/history)
8. Automatic refund of redeemed points upon order cancellation (/api/orders/<id>/cancel)
"""

import uuid
import pytest
from app import app, database, get_user_reward_balance


@pytest.fixture
def client_and_user():
    test_email = f"reward_test_{uuid.uuid4().hex[:6]}@pretwin.ai"
    user_id = database.execute_db(
        "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
        ("RewardTester", test_email, "testpass")
    )
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess["user_id"] = user_id
            sess["username"] = "RewardTester"
            sess["email"] = test_email
            sess["is_authenticated_user"] = True
        yield client, user_id, test_email


def test_reward_points_full_lifecycle(client_and_user):
    client, user_id, test_email = client_and_user

    # 1. Initial balance should auto-seed 500 welcome bonus points (₹5.00)
    res = client.get("/api/rewards/balance")
    data = res.get_json()
    assert res.status_code == 200
    assert data["balance_points"] == 500
    assert data["rupee_value"] == 5.0
    assert data["rate_per_point"] == 0.01

    # 2. Claim loyalty bonus (+200 points)
    res_bonus = client.post("/api/rewards/claim-bonus")
    data_bonus = res_bonus.get_json()
    assert res_bonus.status_code == 200
    assert data_bonus["success"] is True
    assert data_bonus["points_added"] == 200
    assert data_bonus["new_balance"] == 700

    # 3. Redeem 300 points on rewards dashboard
    res_redeem = client.post("/api/rewards/redeem", json={"points": 300})
    data_redeem = res_redeem.get_json()
    assert res_redeem.status_code == 200
    assert data_redeem["success"] is True
    assert data_redeem["points_redeemed"] == 300
    assert data_redeem["rupee_discount"] == 3.0
    assert data_redeem["new_balance"] == 400

    # 4. Active credit in session
    res_credit = client.get("/api/rewards/active-credit")
    data_credit = res_credit.get_json()
    assert res_credit.status_code == 200
    assert data_credit["has_active_credit"] is True
    assert data_credit["credit"]["points"] == 300
    assert data_credit["credit"]["rupee_discount"] == 3.0

    # 5. Checkout calculate with applied reward discount
    res_calc = client.post("/api/checkout/calculate", json={
        "items": [{"product_id": 1, "quantity": 1}],
        "redeem_points": True
    })
    data_calc = res_calc.get_json()
    assert res_calc.status_code == 200
    assert data_calc["reward_discount_amount"] == 3.0
    assert data_calc["reward_points_redeemed"] == 300
    subtotal = data_calc["subtotal"]
    shipping = data_calc["shipping_fee"]
    expected_total = max(0.0, round(subtotal + shipping - 3.0, 2))
    assert data_calc["total_amount"] == expected_total

    # 6. Create order with points applied
    res_order = client.post("/api/orders/create", json={
        "items": [{"product_id": 1, "quantity": 1}],
        "shipping_address": {
            "name": "Reward Tester",
            "email": test_email,
            "phone": "9876543210",
            "address": "123 MG Road",
            "city": "Bengaluru",
            "state": "Karnataka",
            "pincode": "560001"
        },
        "payment_method": "COD",
        "redeem_points": True
    })
    data_order = res_order.get_json()
    assert res_order.status_code == 201
    assert data_order["success"] is True
    assert data_order["points_redeemed"] == 300
    assert data_order["reward_discount"] == 3.0
    order_id = data_order["order_id"]

    # 7. Check ledger history
    res_hist = client.get("/api/rewards/history")
    data_hist = res_hist.get_json()
    assert res_hist.status_code == 200
    assert data_hist["balance"] == 400
    types = [t["transaction_type"] for t in data_hist["transactions"]]
    assert "Welcome Bonus" in types
    assert "Daily Bonus" in types
    assert "Redemption" in types

    # 8. Cancel order -> verify redeemed points refund back to ledger
    res_cancel = client.post(f"/api/orders/{order_id}/cancel")
    data_cancel = res_cancel.get_json()
    assert res_cancel.status_code == 200
    assert data_cancel["success"] is True
    assert data_cancel["points_refunded"] == 300

    # 9. Verify final balance after refund
    assert get_user_reward_balance(user_id) == 700
