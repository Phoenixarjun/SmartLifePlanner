"""
Coordinator Agent - Merges all proposals and scores plan options.
Robust ADK-compatible coordinator for Smart Life Planner.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from src.utils.logger import logger
from src.utils.evaluator import evaluate_plan
from src.utils.llm_service import LLMService


class OptimizedPlan(BaseModel):
    """Optimized plan model (canonical)."""
    plan: Dict[str, Any] = Field(default_factory=dict)
    score: float = 0.0
    evaluation: Dict[str, Any] = Field(default_factory=dict)
    recommendations: List[str] = Field(default_factory=list)


class CoordinatorAgent:
    """
    Merges all agent outputs into a final optimized plan.
    Ensures ADK-style data shape, strong error handling, and verifiable outputs.
    """

    def __init__(self, session_id: Optional[str] = None, api_key: Optional[str] = None):
        self.session_id = session_id
        self.llm = LLMService(api_key) if api_key else None

    def _unwrap_tasks(self, task_data: Any) -> List[Dict[str, Any]]:
        if isinstance(task_data, dict) and "tasks" in task_data:
            return task_data["tasks"]
        if isinstance(task_data, list):
            return task_data
        return []

    def _unwrap_meals(self, meal_data: Any) -> List[Dict[str, Any]]:
        if isinstance(meal_data, dict) and "meal_plan" in meal_data:
            return meal_data["meal_plan"]
        if isinstance(meal_data, list):
            return meal_data
        return []

    def _unwrap_schedule(self, schedule_data: Any) -> Dict[str, Any]:
        # schedule_data may be {"schedule": {...}, "conflicts_resolved": ..}
        if isinstance(schedule_data, dict):
            if "schedule" in schedule_data and isinstance(schedule_data["schedule"], dict):
                return schedule_data
            # maybe schedule_data is already the canonical schedule (day->list)
            if all(isinstance(v, list) for v in schedule_data.values()):
                return {"schedule": schedule_data, "conflicts_resolved": 0, "total_events": sum(len(v) for v in schedule_data.values())}
        return {"schedule": {}, "conflicts_resolved": 0, "total_events": 0}

    def _unwrap_budget(self, budget_data: Any) -> Dict[str, Any]:
        if isinstance(budget_data, dict) and "budget" in budget_data:
            return budget_data["budget"]
        if isinstance(budget_data, dict) and "total" in budget_data:
            return budget_data
        return {"total": 0.0, "items": []}

    def coordinate_plan(
        self,
        intent_data: Dict[str, Any],
        task_data: Dict[str, Any],
        meal_data: Dict[str, Any],
        budget_data: Dict[str, Any],
        schedule_data: Dict[str, Any]
    ) -> Dict[str, Any]:

        logger.log_event(
            "CoordinatorAgent",
            "coordinate_plan",
            {"message": "Merging agent outputs"},
            self.session_id
        )

        intent = intent_data.get("intent", {}) if isinstance(intent_data, dict) else {}
        tasks = self._unwrap_tasks(task_data)
        meals = self._unwrap_meals(meal_data)
        budget = self._unwrap_budget(budget_data)
        schedule_wrapper = self._unwrap_schedule(schedule_data)

        # Build canonical plan
        plan = {
            "goals": intent.get("goals", []),
            "constraints": intent.get("constraints", {}),
            "priorities": intent.get("priorities", []),
            "plan_duration_days": intent.get("plan_duration_days", 7),
            "tasks": tasks,
            "meals": meals,
            "budget": budget,
            # schedule is the inner dict of day->events
            "schedule": schedule_wrapper.get("schedule", {}),
            "metadata": {
                "total_tasks": len(tasks),
                "total_meals": sum(len(m.get("meals", [])) for m in meals),
                "budget_total": budget.get("total", 0.0),
                "schedule_events": schedule_wrapper.get("total_events", 0)
            }
        }

        # Evaluate
        evaluation = evaluate_plan(plan)
        score = evaluation.get("overall_score", 0.0)

        # Recommendations generation (deterministic)
        recommendations = []
        if evaluation.get("budget_deviation", 0) > 0:
            recommendations.append(
                f"Budget is exceeded by ${evaluation['budget_deviation']:.2f}. Consider reducing grocery or meal costs."
            )

        if evaluation.get("constraint_compliance", 1.0) < 0.8:
            issues = evaluation.get("issues", [])
            if issues:
                recommendations.append(f"Constraint issues detected: {', '.join(issues[:3])}")

        if evaluation.get("goal_satisfaction_score", 1.0) < 0.7:
            recommendations.append("Not all goals are satisfied. Add more focused tasks or meals aligned with goals.")

        if not recommendations:
            recommendations.append("Plan is strong — no major issues detected!")

        result = OptimizedPlan(
            plan=plan,
            score=score,
            evaluation=evaluation,
            recommendations=recommendations
        )

        logger.log_event(
            "CoordinatorAgent",
            "coordination_complete",
            {
                "score": score,
                "recommendations_count": len(recommendations)
            },
            self.session_id
        )

        return result.model_dump()

    def process(
        self,
        intent_data: Dict[str, Any],
        task_data: Dict[str, Any],
        meal_data: Dict[str, Any],
        budget_data: Dict[str, Any],
        schedule_data: Dict[str, Any]
    ) -> Dict[str, Any]:

        optimized_plan = self.coordinate_plan(
            intent_data, task_data, meal_data, budget_data, schedule_data
        )

        return {
            "optimized_plan": optimized_plan,
            "agent": "CoordinatorAgent",
            "status": "success"
        }
