"""
tests/test_large_catalog_and_flipkart.py
----------------------------------------
Test suite verifying:
1. Large-scale catalog expansion to thousands of products (> 2,000 records).
2. Comprehensive category coverage across all 13 major e-commerce categories.
3. Idempotent duplicate prevention during catalog import.
4. Database indexing and query performance.
5. Pagination, search, price range, and availability filtering.
6. Flipkart official integration provider status, rate limiting, and compliance handling.
7. Backward compatibility for existing demo product IDs (1..56).
"""

import json
import pytest
from app import app
import database
from integrations.flipkart import FlipkartProvider


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_catalog_contains_thousands_of_products():
    """Verify catalog has expanded to thousands of products (> 2,000 items)."""
    row = database.query_db("SELECT COUNT(*) AS total FROM products", one=True)
    assert row is not None
    total = row["total"]
    assert total >= 2000, f"Expected at least 2000 products, found {total}"


def test_thirteen_major_categories_present():
    """Verify all 13 major categories exist with rich representation."""
    required_categories = [
        "Mobiles",
        "Electronics",
        "Laptops & Computers",
        "Fashion",
        "Footwear",
        "Beauty & Personal Care",
        "Home & Kitchen",
        "Appliances",
        "Books & Stationery",
        "Toys & Baby Products",
        "Sports & Fitness",
        "Food & Grocery",
        "Furniture",
    ]

    rows = database.query_db("SELECT category, COUNT(*) AS count FROM products GROUP BY category")
    cat_counts = {r["category"]: r["count"] for r in rows}

    for req_cat in required_categories:
        assert req_cat in cat_counts, f"Missing category: {req_cat}"
        assert cat_counts[req_cat] >= 40, f"Category {req_cat} only has {cat_counts[req_cat]} items"


def test_original_demo_products_backward_compatibility():
    """Verify product ID 1 exists and matches original Sony WH-1000XM5."""
    prod = database.query_db("SELECT * FROM products WHERE id = 1", one=True)
    assert prod is not None
    assert "Sony" in prod["brand"] or "Sony" in prod["name"]
    assert "WH-1000XM5" in prod["name"]


def test_duplicate_prevention_on_reseed():
    """Verify duplicate prevention logic skips existing items without inflating count."""
    import data.seed_products as sp

    count_before = database.query_db("SELECT COUNT(*) AS total FROM products", one=True)["total"]
    # Seed without clearing existing products
    newly_inserted = sp.seed_products(clear_existing=False)

    count_after = database.query_db("SELECT COUNT(*) AS total FROM products", one=True)["total"]
    assert newly_inserted == 0, "Duplicate items were incorrectly inserted"
    assert count_after == count_before, "Database product count unexpectedly changed on reseed"


def test_products_table_indexes_exist():
    """Verify database performance indexes exist on products table."""
    expected_indexes = [
        "idx_products_category",
        "idx_products_subcategory",
        "idx_products_brand",
        "idx_products_price",
        "idx_products_rating",
        "idx_products_source",
        "idx_products_name",
        "idx_products_avail",
    ]

    rows = database.query_db("SELECT name FROM sqlite_master WHERE type = 'index'")
    existing_indexes = {r["name"] for r in rows}

    for idx in expected_indexes:
        assert idx in existing_indexes, f"Expected index {idx} not found in database"


def test_api_products_pagination(client):
    """Verify efficient pagination across thousands of items."""
    resp1 = client.get("/api/products?page=1&limit=24")
    assert resp1.status_code == 200
    data1 = json.loads(resp1.data)

    assert data1["total"] >= 2000
    assert len(data1["products"]) == 24
    assert data1["page"] == 1
    assert data1["pages"] >= 80

    resp2 = client.get("/api/products?page=2&limit=24")
    assert resp2.status_code == 200
    data2 = json.loads(resp2.data)

    assert len(data2["products"]) == 24
    assert data2["page"] == 2

    ids1 = {p["id"] for p in data1["products"]}
    ids2 = {p["id"] for p in data2["products"]}
    assert ids1.isdisjoint(ids2), "Pages 1 and 2 must not contain overlapping products"


def test_api_products_filters(client):
    """Verify category, price, search, and availability filters work accurately."""
    # Category filter
    resp_cat = client.get("/api/products?category=Mobiles&limit=10")
    assert resp_cat.status_code == 200
    data_cat = json.loads(resp_cat.data)
    assert all(p["category"].lower() == "mobiles" for p in data_cat["products"])

    # Price range filter
    resp_price = client.get("/api/products?min_price=1000&max_price=3000&limit=20")
    assert resp_price.status_code == 200
    data_price = json.loads(resp_price.data)
    assert all(1000 <= p["price"] <= 3000 for p in data_price["products"])

    # Search filter
    resp_search = client.get("/api/products?search=Samsung&limit=10")
    assert resp_search.status_code == 200
    data_search = json.loads(resp_search.data)
    assert len(data_search["products"]) > 0
    assert all(
        "samsung" in p["name"].lower() or "samsung" in p.get("brand", "").lower()
        for p in data_search["products"]
    )

    # In stock filter
    resp_avail = client.get("/api/products?availability=in_stock&limit=10")
    assert resp_avail.status_code == 200
    data_avail = json.loads(resp_avail.data)
    assert all(p["availability"] == "in_stock" or p.get("stock", 0) > 0 for p in data_avail["products"])


def test_flipkart_status_endpoint(client):
    """Verify /api/flipkart/status returns structured compliance metadata and approval steps."""
    resp = client.get("/api/flipkart/status")
    assert resp.status_code == 200
    data = json.loads(resp.data)

    assert data["success"] is True
    st = data["status"]
    assert "provider" in st
    assert "required_env_vars" in st
    assert "FLIPKART_AFFILIATE_ID" in st["required_env_vars"]
    assert "FLIPKART_AFFILIATE_TOKEN" in st["required_env_vars"]
    assert "allowed_refresh_frequency" in st
    assert "attribution" in st
    assert "approval_steps" in st
    assert len(st["approval_steps"]) >= 4


def test_flipkart_products_endpoint_unconfigured_graceful(client):
    """Verify /api/flipkart/products behaves safely when live credentials are not set."""
    resp = client.get("/api/flipkart/products?q=smartphones")
    assert resp.status_code == 200
    data = json.loads(resp.data)

    assert "data_origin" in data
    assert "status" in data
    assert "products" in data


def test_flipkart_provider_rate_limit_and_cache():
    """Verify FlipkartProvider caching and rate limiting logic."""
    provider = FlipkartProvider(
        affiliate_id="test_affiliate_id",
        affiliate_token="test_token",
        base_url="https://affiliate-api.flipkart.net/affiliate/1.0",
        cache_ttl=1800,
    )

    assert provider.is_configured() is True
    assert provider.get_masked_affiliate_id() == "te****id"

    # Test cache set and retrieve
    dummy_data = [{"source_id": "FK-1", "name": "Test Laptop", "price": 45000}]
    provider._set_cache("test_cache_key", dummy_data)
    cached = provider._get_from_cache("test_cache_key")
    assert cached == dummy_data

    # Test rate limit checking
    assert provider._check_rate_limit() is True
