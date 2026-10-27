# -*- coding: utf-8 -*-
import urllib.request
import urllib.error
import json

BASE = 'http://127.0.0.1:5000'

def test_url(path, desc):
    try:
        res = urllib.request.urlopen(BASE + path)
        print(f"[OK] {desc} -> Status {res.status}, Length: {len(res.read())}")
    except Exception as e:
        print(f"[FAIL] {desc} -> Error: {e}")

print("=== 1. Testing Frontend HTML Pages ===")
test_url('/', 'Homepage (PreTwin)')
test_url('/discovery', 'Product Discovery')
test_url('/checkout', 'Checkout & Payment')
test_url('/orders', 'My Orders Page')
test_url('/twin', 'My Shopping Twin')
test_url('/predictions', 'Predictive Shopping')

print("\n=== 2. Testing Auth Endpoints ===")
login_req = urllib.request.Request(
    BASE + '/api/auth/login',
    data=json.dumps({'email': 'alex@demo.pretwinshop.ai', 'password': 'password123'}).encode(),
    headers={'Content-Type': 'application/json'}
)
res = urllib.request.urlopen(login_req)
login_data = json.loads(res.read().decode())
print(f"[OK] Login API -> Success: {login_data.get('success')}, User: {login_data.get('user', {}).get('username')}")

print("\n=== 3. Testing Checkout & Payment Endpoints ===")
calc_req = urllib.request.Request(
    BASE + '/api/checkout/calculate',
    data=json.dumps({'items': [{'product_id': 1, 'quantity': 1}, {'product_id': 573, 'quantity': 1}]}).encode(),
    headers={'Content-Type': 'application/json'}
)
res = urllib.request.urlopen(calc_req)
calc_data = json.loads(res.read().decode())
print(f"[OK] Calculate API -> Subtotal: {calc_data.get('subtotal')}, Total: {calc_data.get('total_amount')}, Gateway Configured: {calc_data.get('gateway_configured')}")

order_req = urllib.request.Request(
    BASE + '/api/orders/create',
    data=json.dumps({
        'items': [{'product_id': 1, 'quantity': 1}],
        'shipping_address': {
            'name': 'Alex Johnson',
            'email': 'alex@demo.pretwinshop.ai',
            'phone': '9876543210',
            'address': 'Flat 402, PreTwin Residency',
            'city': 'Bengaluru',
            'state': 'Karnataka',
            'pincode': '560103'
        },
        'payment_method': 'PreTwin Sandbox'
    }).encode(),
    headers={'Content-Type': 'application/json'}
)
res = urllib.request.urlopen(order_req)
ord_data = json.loads(res.read().decode())
print(f"[OK] Order Create API -> Order #{ord_data.get('order_number')}, Total: {ord_data.get('total_amount')}")

ver_req = urllib.request.Request(
    BASE + '/api/orders/verify-payment',
    data=json.dumps({
        'order_id': ord_data['order_id'],
        'order_number': ord_data['order_number'],
        'is_sandbox_mode': True
    }).encode(),
    headers={'Content-Type': 'application/json'}
)
res = urllib.request.urlopen(ver_req)
ver_data = json.loads(res.read().decode())
print(f"[OK] Verify Payment API -> Status: {ver_data.get('status')}, Payment Status: {ver_data.get('payment_status')}")

orders_res = urllib.request.urlopen(BASE + '/api/orders')
orders_data = json.loads(orders_res.read().decode())
print(f"[OK] Orders List API -> Total user orders: {orders_data.get('total')}")
