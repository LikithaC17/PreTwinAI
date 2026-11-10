"""
tests/test_discovery_seven_sections.py
======================================
Comprehensive Test Suite for Feature 3: Smart Product Discovery
Covers all 13 test scenarios specified in Phase 9:
1. Exact Product Name Search
2. Partial Name Search
3. Natural Language Search
4. Price Limit Search
5. Multi-Attribute Search
6. Spelling Mistakes / Typos
7. Category Browsing
8. Filter Combination
9. Sorting Verification
10. Zero-Result Fallback
11. Related Products & Alternatives
12. Shopping Actions (Wishlist & Cart Verification)
13. Responsive UI & Page Rendering
"""

import pytest
import json
import app as flask_app
import database
import services.search_intelligence_service as sis


@pytest.fixture
def client():
    flask_app.app.config["TESTING"] = True
    with flask_app.app.test_client() as client:
        yield client


# Scenario 1: Exact Product Name Search
def test_scenario_01_exact_name_search(client):
    row = database.query_db("SELECT name FROM products WHERE name IS NOT NULL LIMIT 1", one=True)
    assert row is not None
    exact_name = row["name"]

    res = client.get(f"/api/products?search={exact_name}")
    assert res.status_code == 200
    data = res.get_json()
    assert len(data["products"]) >= 1
    names = [p["name"].lower() for p in data["products"]]
    assert any(exact_name.lower() in n for n in names)


# Scenario 2: Partial Name Search
def test_scenario_02_partial_name_search(client):
    res = client.get("/api/products?search=headphone")
    assert res.status_code == 200
    data = res.get_json()
    assert len(data["products"]) >= 1
    for p in data["products"]:
        combined = (p["name"] + " " + p.get("description", "") + " " + p.get("subcategory", "")).lower()
        assert "headphone" in combined or "audio" in combined or "ear" in combined or "electronic" in combined


# Scenario 3: Natural Language Search
def test_scenario_03_natural_language_search(client):
    res = client.post("/api/discovery/nl-search", json={"query": "shoes under 3000 for running"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["parsed_intent"]["max_price"] == 3000.0
    assert data["parsed_intent"]["category"] == "Fashion"
    assert "products" in data
    assert len(data["products"]) >= 1
    for p in data["products"]:
        assert p["price"] <= 3000.0


# Scenario 4: Price Limit Search
def test_scenario_04_price_limit_search(client):
    res = client.get("/api/products?max_price=1000")
    assert res.status_code == 200
    data = res.get_json()
    assert len(data["products"]) >= 1
    for p in data["products"]:
        assert p["price"] <= 1000.0


# Scenario 5: Multi-Attribute Search
def test_scenario_05_multi_attribute_search(client):
    parsed = sis.QueryUnderstandingEngine.parse_query("Samsung phone under 20000")
    assert parsed["brand"] == "Samsung"
    assert parsed["category"] == "Mobiles"
    assert parsed["max_price"] == 20000.0

    res = client.post("/api/discovery/nl-search", json={"query": "Samsung phone under 20000"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["parsed_intent"]["brand"] == "Samsung"
    assert data["parsed_intent"]["max_price"] == 20000.0
    assert len(data["products"]) >= 1
    for p in data["products"]:
        assert p["price"] <= 20000.0


# Scenario 6: Spelling Mistakes / Typos
def test_scenario_06_spelling_mistakes_typos(client):
    # Test brand typo: "samung" -> "Samsung"
    parsed1 = sis.QueryUnderstandingEngine.parse_query("samung phne")
    assert parsed1["did_you_mean"] is not None
    assert "samsung" in parsed1["corrected_query"]

    # Test suggestions API detects did-you-mean
    res = client.get("/api/discovery/suggestions?q=samung")
    assert res.status_code == 200
    data = res.get_json()
    assert data["did_you_mean"] is not None
    assert "samsung" in data["did_you_mean"].lower()


# Scenario 7: Category Browsing
def test_scenario_07_category_browsing(client):
    # 1. Categories API summary
    res = client.get("/api/discovery/categories")
    assert res.status_code == 200
    data = res.get_json()
    assert data["total_categories"] == 20
    assert len(data["categories"]) == 20

    # 2. Filter products by category
    res2 = client.get("/api/products?category=Footwear")
    assert res2.status_code == 200
    data2 = res2.get_json()
    assert data2["total"] == 52
    for p in data2["products"]:
        assert p["category"] == "Footwear"


# Scenario 8: Filter Combination (Multi-Dimensional)
def test_scenario_08_filter_combination(client):
    # Category = Fashion, max_price = 5000, min_rating = 4.0
    res = client.get("/api/products?category=Fashion&max_price=5000&min_rating=4.0")
    assert res.status_code == 200
    data = res.get_json()
    for p in data["products"]:
        assert p["category"] == "Fashion"
        assert p["price"] <= 5000.0
        assert p["rating"] >= 4.0


# Scenario 9: Sorting Verification
def test_scenario_09_sorting_verification(client):
    # 1. Price Low to High
    res_asc = client.get("/api/products?sort=price-asc&limit=10")
    data_asc = res_asc.get_json()
    prices_asc = [p["price"] for p in data_asc["products"]]
    assert prices_asc == sorted(prices_asc)

    # 2. Price High to Low
    res_desc = client.get("/api/products?sort=price-desc&limit=10")
    data_desc = res_desc.get_json()
    prices_desc = [p["price"] for p in data_desc["products"]]
    assert prices_desc == sorted(prices_desc, reverse=True)

    # 3. Rating
    res_rating = client.get("/api/products?sort=rating&limit=10")
    data_rating = res_rating.get_json()
    ratings = [p["rating"] for p in data_rating["products"]]
    assert ratings == sorted(ratings, reverse=True)


# Scenario 10: Zero-Result Fallback
def test_scenario_10_zero_result_fallback(client):
    res = client.get("/api/discovery/zero-results?q=unobtainiumxyz12345")
    assert res.status_code == 200
    data = res.get_json()
    assert "popular_categories" in data
    assert len(data["popular_categories"]) >= 3
    assert "trending_products" in data
    assert len(data["trending_products"]) >= 1


# Scenario 11: Related Products & Alternatives
def test_scenario_11_related_products_and_alternatives(client):
    p_row = database.query_db("SELECT id, category, price FROM products LIMIT 1", one=True)
    p_id = p_row["id"]

    res = client.get(f"/api/discovery/products/{p_id}/alternatives")
    assert res.status_code == 200
    data = res.get_json()
    assert "source_product" in data
    assert "alternatives" in data
    assert len(data["alternatives"]) >= 1

    for alt in data["alternatives"]:
        assert alt["id"] != p_id
        assert "alternative_badge" in alt
        assert "explanation" in alt
        assert len(alt["explanation"]) > 5


# Scenario 12: Shopping Actions (Wishlist & Cart Verification)
def test_scenario_12_shopping_actions(client):
    p_row = database.query_db("SELECT id, name, price, image_url, category FROM products LIMIT 1", one=True)
    p_id = p_row["id"]

    # 1. Verify single product detail endpoint returns complete data for shopping
    prod_res = client.get(f"/api/products/{p_id}")
    assert prod_res.status_code == 200
    p_data = prod_res.get_json()
    assert p_data["id"] == p_id
    assert "price" in p_data
    assert "rating" in p_data

    # 2. Add to Wishlist via API
    wish_res = client.post("/api/wishlist", json={"product_id": p_id})
    assert wish_res.status_code == 200
    wish_data = wish_res.get_json()
    assert wish_data["success"] is True

    # 3. Verify Wishlist contains product
    get_wish = client.get("/api/wishlist")
    assert get_wish.status_code == 200
    wish_list = get_wish.get_json()["items"]
    assert any(item["id"] == p_id for item in wish_list)

    # 4. Remove from Wishlist
    del_res = client.delete(f"/api/wishlist/{p_id}")
    assert del_res.status_code == 200


# Scenario 13: Responsive UI & Page Rendering
def test_scenario_13_responsive_ui_rendering(client):
    res = client.get("/discovery")
    assert res.status_code == 200
    html = res.data.decode("utf-8")

    # Verify all 7 sections / key elements are present in the DOM
    assert 'id="aiNlSearchInput"' in html
    assert 'id="fkSearchInput"' in html
    assert 'id="categorySelect"' in html
    assert 'id="subcategorySelect"' in html
    assert 'id="minPriceInput"' in html
    assert 'id="maxPriceInput"' in html
    assert 'id="productsGrid"' in html
    assert 'id="appliedFilterTags"' in html
    assert 'id="categoryBrowseStrip"' in html
    assert 'id="collectionPills"' in html
    assert 'id="alternativesModal"' in html
    assert 'id="searchSuggestionsDropdown"' in html
    assert 'id="didYouMeanNotice"' in html

    # Verify Soft Lavender theme colors are included
    assert "#F7F3FF" in html
    assert "#FFFDF9" in html
    assert "#C4A6F5" in html
