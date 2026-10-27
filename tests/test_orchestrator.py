"""Tests for Master Agent Orchestrator."""

import uuid
import pytest
from unittest.mock import patch, MagicMock
from agents.orchestrator import AgentOrchestrator, run_agent_b, run_agent_d
from tests.conftest import create_test_product, create_test_purchase


def test_orchestrator_runs_all_agents(test_db, demo_user_id):
    """Orchestrator should execute all 6 agents in sequence."""
    orchestrator = AgentOrchestrator()
    res = orchestrator.run(user_id=demo_user_id)

    assert res is not None
    assert "agents_executed" in res
    assert len(res["agents_executed"]) == 6
    assert res["status"] in ("success", "partial")


def test_orchestrator_returns_run_id(test_db, demo_user_id):
    """Orchestrator should return a unique run_id."""
    orchestrator = AgentOrchestrator()
    custom_run_id = str(uuid.uuid4())
    res = orchestrator.run(user_id=demo_user_id, run_id=custom_run_id)

    assert res["run_id"] == custom_run_id


def test_orchestrator_handles_agent_error_gracefully(test_db, demo_user_id):
    """Orchestrator should not crash if an individual agent raises an exception."""
    orchestrator = AgentOrchestrator()

    with patch.object(orchestrator.agent_b, "run", side_effect=RuntimeError("Simulated Agent B failure")):
        res = orchestrator.run(user_id=demo_user_id)

    assert res is not None
    assert res["status"] in ("partial", "error")
    assert len(res["errors"]) >= 1
    # Subsequent agents should still have executed or handled cleanly
    assert "twin_profile" in res


def test_orchestrator_records_agent_runs(test_db, demo_user_id):
    """Orchestrator execution logs should be saved to database."""
    from tests.test_agents import _patch_db
    patches = _patch_db(test_db)
    for p in patches:
        p.start()
    try:
        run_id = str(uuid.uuid4())
        orchestrator = AgentOrchestrator()
        res = orchestrator.run(user_id=demo_user_id, run_id=run_id)

        cursor = test_db.execute("SELECT COUNT(*) FROM agent_runs WHERE run_id = ?", (run_id,))
        count = cursor.fetchone()[0]
        assert count >= 1
    finally:
        for p in patches:
            p.stop()


def test_orchestrator_result_contains_all_sections(test_db, demo_user_id):
    """Orchestrator output should contain all required sections."""
    orchestrator = AgentOrchestrator()
    res = orchestrator.run(user_id=demo_user_id)

    expected_keys = {
        "run_id", "user_id", "status", "twin_profile",
        "predictions", "discovered_products", "comparisons",
        "recommendations", "explanations", "agents_executed",
        "workflow_summary",
    }
    assert expected_keys.issubset(res.keys())


def test_orchestrator_budget_constraint_respected(test_db, demo_user_id):
    """All recommended items must fit within the user's budget ceiling."""
    orchestrator = AgentOrchestrator()
    res = orchestrator.run(user_id=demo_user_id)

    budget_max = float(res["twin_profile"].get("preferences", {}).get("budget_max", 5000.0))
    for rec in res["recommendations"]:
        assert float(rec.get("price", 0)) <= budget_max + 0.01


def test_run_agent_b_helper(test_db, demo_user_id):
    """Module-level run_agent_b should return predictions dict."""
    res = run_agent_b(user_id=demo_user_id)
    assert "predictions" in res
    assert "run_id" in res


def test_run_agent_d_helper(test_db, demo_user_id):
    """Module-level run_agent_d should return comparisons dict."""
    res = run_agent_d(user_id=demo_user_id)
    assert res is not None
