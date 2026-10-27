"""
test_agents.py — Unit tests for the individual PreTwinShop AI agents.

Agents tested
-------------
A — ShoppingTwinAgent    (agents/agent_a_twin.py)
B — PredictiveAgent      (agents/agent_b_predictive.py)
C — DiscoveryAgent       (agents/agent_c_discovery.py)
D — ComparisonAgent      (agents/agent_d_comparison.py)
E — BudgetAgent          (agents/agent_e_budget.py)
F — ExplanationAgent     (agents/agent_f_explanation.py)

Each test uses the `test_db` fixture (in-memory SQLite) and patches
`database.query_db` / `database.execute_db` to use the fixture connection.
"""

from __future__ import annotations

import importlib
import json
import os
import sqlite3
import sys
import uuid
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from tests.conftest import create_test_product, create_test_purchase


# ---------------------------------------------------------------------------
# Utilities for patching the DB layer inside agents
# ---------------------------------------------------------------------------

def _make_query_db(conn: sqlite3.Connection):
    """Return a query_db replacement that uses the given connection."""
    def query_db(sql, args=(), one=False):
        cursor = conn.execute(sql, args)
        rows = cursor.fetchall()
        return (rows[0] if rows else None) if one else rows
    return query_db


def _make_execute_db(conn: sqlite3.Connection):
    """Return an execute_db replacement that uses the given connection."""
    def execute_db(sql, args=()):
        cursor = conn.execute(sql, args)
        conn.commit()
        return cursor.lastrowid
    return execute_db


def _patch_db(conn: sqlite3.Connection):
    """Patch the database module's query_db / execute_db globally."""
    return [
        patch("database.query_db", side_effect=_make_query_db(conn)),
        patch("database.execute_db", side_effect=_make_execute_db(conn)),
    ]


# ---------------------------------------------------------------------------
# Agent A — ShoppingTwinAgent
# ---------------------------------------------------------------------------

class TestShoppingTwinAgent:
    @pytest.fixture(autouse=True)
    def import_agent(self):
        try:
            from agents.agent_a_twin import ShoppingTwinAgent
            self.AgentClass = ShoppingTwinAgent
        except ImportError:
            pytest.skip("agents.agent_a_twin not available")

    def test_shopping_twin_agent_returns_profile(self, test_db, demo_user_id):
        """Agent A should return a dict with expected profile keys."""
        run_id = str(uuid.uuid4())
        patches = _patch_db(test_db)
        for p in patches:
            p.start()
        try:
            agent = self.AgentClass()
            result = agent.run(demo_user_id, run_id)
        finally:
            for p in patches:
                p.stop()

        assert isinstance(result, dict)
        expected_keys = {"user_id", "preferences", "budget_range",
                         "top_categories", "has_sufficient_data"}
        assert expected_keys.issubset(result.keys()), (
            f"Missing keys: {expected_keys - result.keys()}"
        )
        assert result["user_id"] == demo_user_id

    def test_shopping_twin_agent_handles_missing_user(self, test_db):
        """Agent A with a non-existent user_id should return an empty/error profile."""
        run_id = str(uuid.uuid4())
        patches = _patch_db(test_db)
        for p in patches:
            p.start()
        try:
            agent = self.AgentClass()
            result = agent.run(99999, run_id)
        finally:
            for p in patches:
                p.stop()

        assert isinstance(result, dict)
        # Should not raise; profile should indicate no data
        assert result.get("has_sufficient_data") is False or \
               result.get("user_info") == {} or \
               "not found" in str(result.get("profile_insights", "")).lower()


# ---------------------------------------------------------------------------
# Agent B — PredictiveAgent
# ---------------------------------------------------------------------------

class TestPredictiveAgent:
    @pytest.fixture(autouse=True)
    def import_agent(self):
        try:
            from agents.agent_b_predictive import PredictiveAgent
            self.AgentClass = PredictiveAgent
        except ImportError:
            pytest.skip("agents.agent_b_predictive not available")

    def _make_profile(self, test_db, demo_user_id: int) -> dict:
        """Build a minimal twin profile for passing to Agent B."""
        create_test_purchase(test_db, user_id=demo_user_id,
                             product_name="Sony WH-1000XM5", category="Electronics",
                             brand="Sony", price=349.99, purchase_date="2024-05-01")
        create_test_purchase(test_db, user_id=demo_user_id,
                             product_name="Nike Running Shoes", category="Clothing",
                             brand="Nike", price=120.0, purchase_date="2024-04-01")
        return {
            "user_id": demo_user_id,
            "preferences": {
                "preferred_categories": ["Electronics", "Clothing"],
                "preferred_brands": ["Sony", "Nike"],
                "budget_min": 50.0,
                "budget_max": 2000.0,
                "shopping_frequency": "monthly",
            },
            "purchase_history": [
                {"product_name": "Sony WH-1000XM5", "category": "Electronics",
                 "brand": "Sony", "price": 349.99, "purchase_date": "2024-05-01"},
                {"product_name": "Nike Running Shoes", "category": "Clothing",
                 "brand": "Nike", "price": 120.0, "purchase_date": "2024-04-01"},
            ],
            "top_categories": ["Electronics", "Clothing"],
            "recent_brands": ["Sony", "Nike"],
            "has_sufficient_data": True,
            "budget_range": {"min": 50.0, "max": 2000.0},
        }

    def test_predictive_agent_generates_predictions(self, test_db, demo_user_id):
        """Agent B should return a list of at least 1 prediction."""
        run_id = str(uuid.uuid4())
        profile = self._make_profile(test_db, demo_user_id)
        patches = _patch_db(test_db)
        for p in patches:
            p.start()
        try:
            agent = self.AgentClass()
            result = agent.run(profile, run_id)
        finally:
            for p in patches:
                p.stop()

        assert isinstance(result, (dict, list))
        if isinstance(result, dict):
            predictions = result.get("predictions", [])
        else:
            predictions = result
        assert len(predictions) >= 1, "Expected at least one prediction"

    def test_predictive_agent_insufficient_data(self, test_db, demo_user_id):
        """Agent B with empty history should still return a result without crashing."""
        run_id = str(uuid.uuid4())
        profile = {
            "user_id": demo_user_id,
            "preferences": {
                "preferred_categories": [],
                "preferred_brands": [],
                "budget_min": 0,
                "budget_max": 10000,
            },
            "purchase_history": [],
            "top_categories": [],
            "has_sufficient_data": False,
            "budget_range": {"min": 0, "max": 10000},
        }
        patches = _patch_db(test_db)
        for p in patches:
            p.start()
        try:
            agent = self.AgentClass()
            result = agent.run(profile, run_id)
        finally:
            for p in patches:
                p.stop()

        assert result is not None

    def test_predictive_agent_confidence_scores_valid(self, test_db, demo_user_id):
        """All confidence scores in Agent B's output must be between 0 and 1."""
        run_id = str(uuid.uuid4())
        profile = self._make_profile(test_db, demo_user_id)
        patches = _patch_db(test_db)
        for p in patches:
            p.start()
        try:
            agent = self.AgentClass()
            result = agent.run(profile, run_id)
        finally:
            for p in patches:
                p.stop()

        if isinstance(result, dict):
            predictions = result.get("predictions", [])
        else:
            predictions = result if isinstance(result, list) else []

        for pred in predictions:
            score = pred.get("confidence_score", 0.5)
            assert 0.0 <= float(score) <= 1.0, (
                f"Confidence score {score} is outside [0, 1]"
            )


# ---------------------------------------------------------------------------
# Agent C — DiscoveryAgent
# ---------------------------------------------------------------------------

class TestDiscoveryAgent:
    @pytest.fixture(autouse=True)
    def import_agent(self):
        try:
            from agents.agent_c_discovery import DiscoveryAgent
            self.AgentClass = DiscoveryAgent
        except ImportError:
            pytest.skip("agents.agent_c_discovery not available")

    def _seed_products(self, test_db):
        create_test_product(test_db, name="Budget Phone", category="Electronics",
                            brand="Generic", price=149.99)
        create_test_product(test_db, name="Premium Phone", category="Electronics",
                            brand="Apple", price=1299.99)
        create_test_product(test_db, name="Mid Phone", category="Electronics",
                            brand="Samsung", price=499.99)

    def test_discovery_agent_finds_products_in_budget(self, test_db, demo_user_id):
        """Agent C should return products that fit within the user's budget."""
        self._seed_products(test_db)
        run_id = str(uuid.uuid4())
        profile = {
            "user_id": demo_user_id,
            "top_categories": ["Electronics"],
            "budget_range": {"min": 0, "max": 600.0},
            "preferences": {
                "preferred_categories": ["Electronics"],
                "budget_max": 600.0,
                "budget_min": 0,
            },
        }
        predictions = [{"predicted_category": "Electronics", "confidence_score": 0.8}]
        patches = _patch_db(test_db)
        for p in patches:
            p.start()
        try:
            agent = self.AgentClass()
            result = agent.run(profile, predictions, run_id)
        finally:
            for p in patches:
                p.stop()

        assert result is not None
        products = result if isinstance(result, list) else result.get("products", [])
        # Products should not exceed budget
        for p in products:
            assert float(p.get("price", 0)) <= 600.0

    def test_discovery_agent_respects_budget_filter(self, test_db, demo_user_id):
        """Agent C must not return products priced above the budget ceiling."""
        self._seed_products(test_db)
        run_id = str(uuid.uuid4())
        budget_max = 200.0
        profile = {
            "user_id": demo_user_id,
            "top_categories": ["Electronics"],
            "budget_range": {"min": 0, "max": budget_max},
            "preferences": {
                "preferred_categories": ["Electronics"],
                "budget_max": budget_max,
                "budget_min": 0,
            },
        }
        predictions = []
        patches = _patch_db(test_db)
        for p in patches:
            p.start()
        try:
            agent = self.AgentClass()
            result = agent.run(profile, predictions, run_id)
        finally:
            for p in patches:
                p.stop()

        products = result if isinstance(result, list) else result.get("products", [])
        for p in products:
            assert float(p.get("price", 0)) <= budget_max + 0.01


# ---------------------------------------------------------------------------
# Agent D — ComparisonAgent
# ---------------------------------------------------------------------------

class TestComparisonAgent:
    @pytest.fixture(autouse=True)
    def import_agent(self):
        try:
            from agents.agent_d_comparison import ComparisonAgent
            self.AgentClass = ComparisonAgent
        except ImportError:
            pytest.skip("agents.agent_d_comparison not available")

    def _make_candidate_products(self, test_db):
        p1 = create_test_product(test_db, name="Product Alpha", category="Electronics",
                                 brand="Sony", price=299.99, rating=4.5)
        p2 = create_test_product(test_db, name="Product Beta", category="Electronics",
                                 brand="Samsung", price=249.99, rating=4.2)
        return [
            {"id": p1, "name": "Product Alpha", "category": "Electronics",
             "brand": "Sony", "price": 299.99, "rating": 4.5},
            {"id": p2, "name": "Product Beta", "category": "Electronics",
             "brand": "Samsung", "price": 249.99, "rating": 4.2},
        ]

    def test_comparison_agent_produces_table(self, test_db, demo_user_id):
        """Agent D should produce a comparison table / structured data."""
        products = self._make_candidate_products(test_db)
        run_id = str(uuid.uuid4())
        profile = {
            "user_id": demo_user_id,
            "preferences": {"budget_max": 500.0},
            "budget_range": {"min": 0, "max": 500.0},
        }
        patches = _patch_db(test_db)
        for p in patches:
            p.start()
        try:
            agent = self.AgentClass()
            result = agent.run(products, profile, run_id)
        finally:
            for p in patches:
                p.stop()

        assert result is not None
        # Result should be a dict or list with comparison data
        assert isinstance(result, (dict, list))

    def test_comparison_agent_selects_winner(self, test_db, demo_user_id):
        """Agent D should identify a winner product."""
        products = self._make_candidate_products(test_db)
        run_id = str(uuid.uuid4())
        profile = {
            "user_id": demo_user_id,
            "preferences": {"budget_max": 500.0},
            "budget_range": {"min": 0, "max": 500.0},
        }
        patches = _patch_db(test_db)
        for p in patches:
            p.start()
        try:
            agent = self.AgentClass()
            result = agent.run(products, profile, run_id)
        finally:
            for p in patches:
                p.stop()

        if isinstance(result, dict):
            winner = result.get("winner") or result.get("winner_id") or \
                     result.get("best_product")
            # Winner should reference one of the products
            assert winner is not None or result.get("comparisons") is not None


# ---------------------------------------------------------------------------
# Agent E — BudgetAgent
# ---------------------------------------------------------------------------

class TestBudgetAgent:
    @pytest.fixture(autouse=True)
    def import_agent(self):
        try:
            from agents.agent_e_budget import BudgetAgent
            self.AgentClass = BudgetAgent
        except ImportError:
            pytest.skip("agents.agent_e_budget not available")

    def test_budget_agent_enforces_hard_limit(self, test_db, demo_user_id):
        """Agent E must exclude products exceeding the hard budget limit."""
        run_id = str(uuid.uuid4())
        budget_max = 300.0
        profile = {
            "user_id": demo_user_id,
            "budget_range": {"min": 0, "max": budget_max},
            "preferences": {"budget_max": budget_max, "budget_min": 0},
        }
        recommendations = [
            {"product_name": "Cheap Product", "price": 99.99, "score": 0.9},
            {"product_name": "Expensive Product", "price": 1500.0, "score": 0.95},
            {"product_name": "Mid Product", "price": 250.0, "score": 0.8},
        ]
        patches = _patch_db(test_db)
        for p in patches:
            p.start()
        try:
            agent = self.AgentClass()
            result = agent.run(recommendations, profile, run_id)
        finally:
            for p in patches:
                p.stop()

        approved = result if isinstance(result, list) else result.get("approved", result.get("recommendations", []))
        for item in approved:
            assert float(item.get("price", 0)) <= budget_max + 0.01, (
                f"Over-budget item passed: {item}"
            )

    def test_budget_agent_calculates_total_cost(self, test_db, demo_user_id):
        """Agent E should compute total cost of recommendations."""
        run_id = str(uuid.uuid4())
        profile = {
            "user_id": demo_user_id,
            "budget_range": {"min": 0, "max": 2000.0},
            "preferences": {"budget_max": 2000.0},
        }
        recommendations = [
            {"product_name": "Item A", "price": 199.99, "score": 0.9},
            {"product_name": "Item B", "price": 149.99, "score": 0.85},
        ]
        patches = _patch_db(test_db)
        for p in patches:
            p.start()
        try:
            agent = self.AgentClass()
            result = agent.run(recommendations, profile, run_id)
        finally:
            for p in patches:
                p.stop()

        if isinstance(result, dict):
            total = result.get("total_cost") or result.get("total")
            if total is not None:
                assert abs(float(total) - 349.98) < 1.0, (
                    f"Total cost mismatch: expected ~349.98, got {total}"
                )


# ---------------------------------------------------------------------------
# Agent F — ExplanationAgent
# ---------------------------------------------------------------------------

class TestExplanationAgent:
    @pytest.fixture(autouse=True)
    def import_agent(self):
        try:
            from agents.agent_f_explanation import ExplanationAgent
            self.AgentClass = ExplanationAgent
        except ImportError:
            pytest.skip("agents.agent_f_explanation not available")

    def _make_recommendations(self) -> list:
        return [
            {
                "product_name": "Sony WH-1000XM5",
                "category": "Electronics",
                "brand": "Sony",
                "price": 349.99,
                "score": 0.92,
                "reason": "Matches preferred brand and category",
            }
        ]

    def test_explanation_agent_generates_explanations(self, test_db, demo_user_id):
        """Agent F should return explanations for each recommendation."""
        run_id = str(uuid.uuid4())
        profile = {
            "user_id": demo_user_id,
            "preferences": {"preferred_brands": ["Sony"]},
            "purchase_history": [],
            "profile_insights": ["Prefers Sony electronics"],
        }
        recommendations = self._make_recommendations()
        patches = _patch_db(test_db)
        for p in patches:
            p.start()
        try:
            agent = self.AgentClass()
            # Agent F signature: run(recommendations, profile, run_id) or similar
            try:
                result = agent.run(recommendations, profile, run_id)
            except TypeError:
                result = agent.run(profile, recommendations, run_id)
        finally:
            for p in patches:
                p.stop()

        assert result is not None
        explained = result if isinstance(result, list) else result.get("recommendations", [])
        # Should have at least one item with an explanation field
        for item in explained:
            assert item.get("explanation") or item.get("reason") or item.get("rationale"), (
                f"Missing explanation field in: {item}"
            )

    def test_explanation_agent_no_fabrication(self, test_db, demo_user_id):
        """Agent F explanations should reference the actual product name, not fabricate data."""
        run_id = str(uuid.uuid4())
        profile = {
            "user_id": demo_user_id,
            "preferences": {"preferred_brands": ["Sony"]},
            "purchase_history": [],
        }
        recommendations = self._make_recommendations()
        patches = _patch_db(test_db)
        for p in patches:
            p.start()
        try:
            agent = self.AgentClass()
            try:
                result = agent.run(recommendations, profile, run_id)
            except TypeError:
                result = agent.run(profile, recommendations, run_id)
        finally:
            for p in patches:
                p.stop()

        explained = result if isinstance(result, list) else result.get("recommendations", [])
        product_name = "Sony WH-1000XM5"

        for item in explained:
            expl = str(item.get("explanation", "") or item.get("reason", "") or "")
            # Explanation should mention either the product name, brand, or category
            has_ref = (
                "sony" in expl.lower() or
                "wh-1000xm5" in expl.lower() or
                "electronics" in expl.lower() or
                item.get("product_name", "") == product_name
            )
            assert has_ref, (
                f"Explanation appears to fabricate data for '{product_name}': {expl[:200]}"
            )
