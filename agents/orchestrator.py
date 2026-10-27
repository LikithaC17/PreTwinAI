"""Master Agent Orchestrator for PreTwinShop AI.

Coordinates the specialized AI agent pipeline:
  Agent A: ShoppingTwinAgent
  Agent B: PredictiveShoppingAgent
  Agent C: ProductDiscoveryAgent
  Agent D: ProductComparisonAgent
  Agent E: BudgetAwareRecommendationAgent
  Agent F: RecommendationExplanationAgent
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import database

from agents.agent_a_twin import ShoppingTwinAgent
from agents.agent_b_predictive import PredictiveShoppingAgent
from agents.agent_c_discovery import ProductDiscoveryAgent
from agents.agent_d_comparison import ProductComparisonAgent
from agents.agent_e_budget import BudgetAwareRecommendationAgent
from agents.agent_f_explanation import RecommendationExplanationAgent

logger = logging.getLogger(__name__)


def _log_orchestrator_run(
    run_id: str,
    agent_name: str,
    user_id: int,
    task: str,
    status: str,
    input_summary: str,
    output_summary: str,
    duration_ms: int,
    error_message: Optional[str] = None,
) -> None:
    try:
        database.execute_db(
            """INSERT INTO agent_runs
               (user_id, run_id, agent_name, task, status,
                input_summary, output_summary, execution_time_ms,
                error_message, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id,
                run_id,
                agent_name,
                task,
                status,
                input_summary[:500],
                output_summary[:500],
                duration_ms,
                error_message,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
    except Exception as exc:
        logger.warning("Failed to record agent run log: %s", exc)


class AgentOrchestrator:
    """Master Orchestrator that coordinates the multi-agent pipeline."""

    def __init__(self):
        self.agent_a = ShoppingTwinAgent()
        self.agent_b = PredictiveShoppingAgent()
        self.agent_c = ProductDiscoveryAgent()
        self.agent_d = ProductComparisonAgent()
        self.agent_e = BudgetAwareRecommendationAgent()
        self.agent_f = RecommendationExplanationAgent()

    def run(self, user_id: int = 1, goal: Optional[str] = None, run_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute the end-to-end multi-agent workflow."""
        if not run_id:
            run_id = str(uuid.uuid4())

        t_start = time.time()
        workflow_state: Dict[str, Any] = {
            "run_id": run_id,
            "user_id": user_id,
            "status": "running",
            "agents_executed": [],
            "errors": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # ── Step 1: Agent A (Shopping Twin) ───────────────────────────────
        step_t0 = time.time()
        twin_profile: Dict[str, Any] = {}
        try:
            twin_profile = self.agent_a.run(user_id, run_id)
            duration_ms = int((time.time() - step_t0) * 1000)
            workflow_state["agents_executed"].append({
                "agent": "Agent A: Shopping Twin",
                "status": "success",
                "duration_ms": duration_ms,
            })
            _log_orchestrator_run(
                run_id, "ShoppingTwinAgent", user_id, "Build Digital Shopping Twin",
                "success", f"user_id={user_id}, goal={goal}",
                f"Profile loaded. Top categories: {twin_profile.get('top_categories', [])}",
                duration_ms
            )
        except Exception as exc:
            duration_ms = int((time.time() - step_t0) * 1000)
            logger.error("Agent A failed: %s", exc, exc_info=True)
            workflow_state["errors"].append(f"Agent A: {exc}")
            workflow_state["agents_executed"].append({
                "agent": "Agent A: Shopping Twin",
                "status": "error",
                "duration_ms": duration_ms,
                "error": str(exc),
            })
            _log_orchestrator_run(
                run_id, "ShoppingTwinAgent", user_id, "Build Digital Shopping Twin",
                "error", f"user_id={user_id}", "", duration_ms, str(exc)
            )

        workflow_state["twin_profile"] = twin_profile

        # ── Step 2: Agent B (Predictive Shopping) ──────────────────────────
        step_t0 = time.time()
        predictions: List[Dict[str, Any]] = []
        try:
            # Inject optional goal if supplied
            if goal and isinstance(twin_profile, dict):
                goals = twin_profile.setdefault("shopping_goals", [])
                if not any(g.get("goal_title") == goal for g in goals):
                    goals.append({"goal_title": goal, "budget": twin_profile.get("preferences", {}).get("budget_max", 500.0)})

            predictions = self.agent_b.run(twin_profile, run_id)
            duration_ms = int((time.time() - step_t0) * 1000)
            workflow_state["agents_executed"].append({
                "agent": "Agent B: Predictive Shopping",
                "status": "success",
                "duration_ms": duration_ms,
            })
            _log_orchestrator_run(
                run_id, "PredictiveShoppingAgent", user_id, "Predict Future Shopping Needs",
                "success", f"History items={len(twin_profile.get('purchase_history', []))}",
                f"Generated {len(predictions) if isinstance(predictions, list) else 0} predictions",
                duration_ms
            )
        except Exception as exc:
            duration_ms = int((time.time() - step_t0) * 1000)
            logger.error("Agent B failed: %s", exc, exc_info=True)
            workflow_state["errors"].append(f"Agent B: {exc}")
            workflow_state["agents_executed"].append({
                "agent": "Agent B: Predictive Shopping",
                "status": "error",
                "duration_ms": duration_ms,
                "error": str(exc),
            })
            _log_orchestrator_run(
                run_id, "PredictiveShoppingAgent", user_id, "Predict Future Shopping Needs",
                "error", "Profile input", "", duration_ms, str(exc)
            )

        workflow_state["predictions"] = predictions

        # ── Step 3: Agent C (Product Discovery) ───────────────────────────
        step_t0 = time.time()
        discovered_data: Dict[str, Any] = {}
        try:
            discovered_data = self.agent_c.run(predictions, twin_profile, run_id)
            duration_ms = int((time.time() - step_t0) * 1000)
            workflow_state["agents_executed"].append({
                "agent": "Agent C: Product Discovery",
                "status": "success",
                "duration_ms": duration_ms,
            })
            prods = discovered_data.get("discovered_products", [])
            _log_orchestrator_run(
                run_id, "ProductDiscoveryAgent", user_id, "Search Catalogue for Matching Products",
                "success", f"{len(predictions) if isinstance(predictions, list) else 0} predictions",
                f"Discovered {len(prods)} products",
                duration_ms
            )
        except Exception as exc:
            duration_ms = int((time.time() - step_t0) * 1000)
            logger.error("Agent C failed: %s", exc, exc_info=True)
            workflow_state["errors"].append(f"Agent C: {exc}")
            workflow_state["agents_executed"].append({
                "agent": "Agent C: Product Discovery",
                "status": "error",
                "duration_ms": duration_ms,
                "error": str(exc),
            })
            _log_orchestrator_run(
                run_id, "ProductDiscoveryAgent", user_id, "Search Catalogue for Matching Products",
                "error", "Predictions input", "", duration_ms, str(exc)
            )

        discovered_products = discovered_data.get("discovered_products", [])
        workflow_state["discovered_products"] = discovered_products

        # ── Step 4: Agent D (Product Comparison) ──────────────────────────
        step_t0 = time.time()
        comparisons_data: Dict[str, Any] = {}
        try:
            comparisons_data = self.agent_d.run(discovered_products, twin_profile, run_id)
            duration_ms = int((time.time() - step_t0) * 1000)
            workflow_state["agents_executed"].append({
                "agent": "Agent D: Product Comparison",
                "status": "success",
                "duration_ms": duration_ms,
            })
            comp_list = comparisons_data.get("comparisons", [])
            _log_orchestrator_run(
                run_id, "ProductComparisonAgent", user_id, "Compare Features & Specifications",
                "success", f"{len(discovered_products)} candidate products",
                f"Generated {len(comp_list)} category comparison sets",
                duration_ms
            )
        except Exception as exc:
            duration_ms = int((time.time() - step_t0) * 1000)
            logger.error("Agent D failed: %s", exc, exc_info=True)
            workflow_state["errors"].append(f"Agent D: {exc}")
            workflow_state["agents_executed"].append({
                "agent": "Agent D: Product Comparison",
                "status": "error",
                "duration_ms": duration_ms,
                "error": str(exc),
            })
            _log_orchestrator_run(
                run_id, "ProductComparisonAgent", user_id, "Compare Features & Specifications",
                "error", "Discovered products", "", duration_ms, str(exc)
            )

        workflow_state["comparisons"] = comparisons_data

        # ── Step 5: Agent E (Budget-Aware Recommendation) ─────────────────
        step_t0 = time.time()
        budget_recs: Dict[str, Any] = {}
        try:
            budget_recs = self.agent_e.run(discovered_products, comparisons_data, twin_profile, run_id)
            duration_ms = int((time.time() - step_t0) * 1000)
            workflow_state["agents_executed"].append({
                "agent": "Agent E: Budget Recommendation",
                "status": "success",
                "duration_ms": duration_ms,
            })
            recs_list = budget_recs.get("recommendations", [])
            _log_orchestrator_run(
                run_id, "BudgetAwareRecommendationAgent", user_id, "Enforce Budget & Assemble Basket",
                "success", f"{len(discovered_products)} candidates, budget ceiling={twin_profile.get('preferences', {}).get('budget_max')}",
                f"{len(recs_list)} recommendations. Total: ${budget_recs.get('total_cost', 0):.2f}",
                duration_ms
            )
        except Exception as exc:
            duration_ms = int((time.time() - step_t0) * 1000)
            logger.error("Agent E failed: %s", exc, exc_info=True)
            workflow_state["errors"].append(f"Agent E: {exc}")
            workflow_state["agents_executed"].append({
                "agent": "Agent E: Budget Recommendation",
                "status": "error",
                "duration_ms": duration_ms,
                "error": str(exc),
            })
            _log_orchestrator_run(
                run_id, "BudgetAwareRecommendationAgent", user_id, "Enforce Budget & Assemble Basket",
                "error", "Candidates input", "", duration_ms, str(exc)
            )

        workflow_state["recommendations"] = budget_recs.get("recommendations", [])
        workflow_state["total_cost"] = budget_recs.get("total_cost", 0.0)
        workflow_state["budget_status"] = budget_recs.get("budget_status", "unknown")
        workflow_state["basket_summary"] = budget_recs.get("basket_summary", "")

        # ── Step 6: Agent F (Recommendation Explanation) ──────────────────
        step_t0 = time.time()
        explanations_data: Dict[str, Any] = {}
        try:
            explanations_data = self.agent_f.run(
                twin_profile, predictions, discovered_products,
                budget_recs, comparisons_data, run_id
            )
            duration_ms = int((time.time() - step_t0) * 1000)
            workflow_state["agents_executed"].append({
                "agent": "Agent F: Explanation Agent",
                "status": "success",
                "duration_ms": duration_ms,
            })
            expl_list = explanations_data.get("explanations", [])
            _log_orchestrator_run(
                run_id, "RecommendationExplanationAgent", user_id, "Synthesize Evidence & Explain Recommendations",
                "success", f"{len(workflow_state['recommendations'])} recommended products",
                f"Generated {len(expl_list)} explanations and transparency summary",
                duration_ms
            )
        except Exception as exc:
            duration_ms = int((time.time() - step_t0) * 1000)
            logger.error("Agent F failed: %s", exc, exc_info=True)
            workflow_state["errors"].append(f"Agent F: {exc}")
            workflow_state["agents_executed"].append({
                "agent": "Agent F: Explanation Agent",
                "status": "error",
                "duration_ms": duration_ms,
                "error": str(exc),
            })
            _log_orchestrator_run(
                run_id, "RecommendationExplanationAgent", user_id, "Synthesize Evidence & Explain Recommendations",
                "error", "Recommendations input", "", duration_ms, str(exc)
            )

        workflow_state["explanations"] = explanations_data

        # Merge explanations back into recommendations list
        expl_lookup = {
            e.get("product_id"): e.get("explanation", "")
            for e in explanations_data.get("explanations", [])
        }
        for rec in workflow_state["recommendations"]:
            pid = rec.get("product_id") or rec.get("product", {}).get("id")
            if pid in expl_lookup:
                rec["explanation"] = expl_lookup[pid]
                rec["reason"] = expl_lookup[pid]

        total_duration = time.time() - t_start
        workflow_state["total_duration_ms"] = int(total_duration * 1000)
        workflow_state["status"] = "partial" if workflow_state["errors"] else "success"
        workflow_state["workflow_summary"] = (
            f"Successfully executed {len(workflow_state['agents_executed'])} agents in "
            f"{workflow_state['total_duration_ms']}ms. Generated {len(workflow_state['recommendations'])} recommendations."
        )

        return workflow_state

    def rerun(self, user_id: int = 1, from_agent: str = "B", run_id: Optional[str] = None) -> Dict[str, Any]:
        """Rerun workflow starting from a specific agent."""
        return self.run(user_id=user_id, run_id=run_id)

    def run_agent_b(self, user_id: int = 1) -> Dict[str, Any]:
        """Run prediction agent directly."""
        run_id = str(uuid.uuid4())
        twin = self.agent_a.run(user_id, run_id)
        predictions = self.agent_b.run(twin, run_id)
        return {
            "run_id": run_id,
            "user_id": user_id,
            "predictions": predictions if isinstance(predictions, list) else [],
            "twin_profile": twin,
        }

    def run_agent_d(self, user_id: int = 1, product_ids: Optional[List[int]] = None) -> Dict[str, Any]:
        """Run product comparison for specific products."""
        run_id = str(uuid.uuid4())
        twin = self.agent_a.run(user_id, run_id)
        if product_ids:
            placeholders = ", ".join("?" for _ in product_ids)
            rows = database.query_db(f"SELECT * FROM products WHERE id IN ({placeholders})", tuple(product_ids))
            products = [dict(r) for r in rows]
        else:
            rows = database.query_db("SELECT * FROM products LIMIT 4")
            products = [dict(r) for r in rows]

        return self.agent_d.run(products, twin, run_id)


# Convenience module-level functions called by app.py
_orchestrator = AgentOrchestrator()


def run_agent_b(user_id: int = 1) -> Dict[str, Any]:
    """Run prediction agent directly."""
    run_id = str(uuid.uuid4())
    twin = _orchestrator.agent_a.run(user_id, run_id)
    predictions = _orchestrator.agent_b.run(twin, run_id)
    return {
        "run_id": run_id,
        "user_id": user_id,
        "predictions": predictions if isinstance(predictions, list) else [],
        "twin_profile": twin,
    }


def run_agent_d(user_id: int = 1, product_ids: Optional[List[int]] = None) -> Dict[str, Any]:
    """Run product comparison for specific products."""
    run_id = str(uuid.uuid4())
    twin = _orchestrator.agent_a.run(user_id, run_id)
    if product_ids:
        placeholders = ", ".join("?" for _ in product_ids)
        rows = database.query_db(f"SELECT * FROM products WHERE id IN ({placeholders})", tuple(product_ids))
        products = [dict(r) for r in rows]
    else:
        rows = database.query_db("SELECT * FROM products LIMIT 4")
        products = [dict(r) for r in rows]

    return _orchestrator.agent_d.run(products, twin, run_id)
