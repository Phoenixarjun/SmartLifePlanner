"""
Verifier Agent - Final validation and reproducibility signature.
ADK-compatible agent with glass-box verification.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import hashlib
import json

from src.utils.logger import logger
from src.utils.evaluator import evaluate_plan
from src.utils.llm_service import LLMService


class VerificationResult(BaseModel):
    """Verification result model."""
    is_valid: bool
    constraints_satisfied: bool
    budget_within_limits: bool
    meals_scheduled: bool
    tasks_scheduled: bool
    validation_trace: List[Dict[str, Any]] = Field(default_factory=list)
    reproducibility_signature: str = ""
    verification_summary: str = ""


class VerifierAgent:
    """Performs final verification of the entire plan."""

    def __init__(self, session_id: Optional[str] = None, api_key: Optional[str] = None):
        self.session_id = session_id
        self.llm = LLMService(api_key) if api_key else None

    # ----------------------------------------------------------
    # Utility: Safe extraction helpers
    # ----------------------------------------------------------

    def _extract_schedule_events(self, schedule: Dict[str, Any], event_type: str):
        """Returns list of events of given type across all days."""
        events = []
        if isinstance(schedule, dict):
            for day, day_events in schedule.items():
                if isinstance(day_events, list):
                    for ev in day_events:
                        etype = ev.get("type") or ev.get("event_type") or ev.get("category")
                        if etype == event_type:
                            events.append(ev)
        return events

    # ----------------------------------------------------------
    # Core verification
    # ----------------------------------------------------------

    def verify_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        logger.log_event(
            "VerifierAgent",
            "verify_plan",
            {"message": "Starting verification"},
            self.session_id
        )

        validation_trace = []
        checks = {
            "constraints_satisfied": True,
            "budget_within_limits": True,
            "meals_scheduled": False,
            "tasks_scheduled": False
        }

        # ------------------------------------------------------
        # Budget verification
        # ------------------------------------------------------
        constraints = plan.get("constraints", {})
        budget_limit = constraints.get("max_budget")
        actual_budget = plan.get("budget", {}).get("total", 0.0)

        if budget_limit:
            checks["budget_within_limits"] = actual_budget <= budget_limit

        validation_trace.append({
            "check": "budget_limit",
            "expected": f"≤ ${budget_limit}" if budget_limit else "No limit",
            "actual": f"${actual_budget:.2f}",
            "passed": checks["budget_within_limits"]
        })

        # ------------------------------------------------------
        # Meal scheduling check
        # ------------------------------------------------------
        schedule = plan.get("schedule", {})
        meal_events = self._extract_schedule_events(schedule, "meal")

        checks["meals_scheduled"] = len(meal_events) > 0

        validation_trace.append({
            "check": "meals_scheduled",
            "expected": "> 0 meals",
            "actual": f"{len(meal_events)} meals",
            "passed": checks["meals_scheduled"]
        })

        # ------------------------------------------------------
        # Task scheduling check
        # ------------------------------------------------------
        task_events = self._extract_schedule_events(schedule, "task")

        checks["tasks_scheduled"] = len(task_events) > 0

        validation_trace.append({
            "check": "tasks_scheduled",
            "expected": "> 0 tasks",
            "actual": f"{len(task_events)} tasks",
            "passed": checks["tasks_scheduled"]
        })

        # ------------------------------------------------------
        # Constraint compliance scoring
        # ------------------------------------------------------
        evaluation = evaluate_plan(plan)
        compliance = evaluation.get("constraint_compliance", 0.0)

        checks["constraints_satisfied"] = compliance >= 0.8

        validation_trace.append({
            "check": "constraint_compliance",
            "expected": "≥ 0.8",
            "actual": f"{compliance:.2f}",
            "passed": checks["constraints_satisfied"]
        })

        # ------------------------------------------------------
        # Final overall validity
        # ------------------------------------------------------
        is_valid = all(checks.values())

        # ------------------------------------------------------
        # Deterministic reproducibility signature
        # ------------------------------------------------------
        plan_serialized = json.dumps(plan, sort_keys=True)
        signature = hashlib.sha256(plan_serialized.encode()).hexdigest()[:16]

        # ------------------------------------------------------
        # Assemble verification summary
        # ------------------------------------------------------
        summary = [
            "Plan Verification Summary:",
            f"- Budget: {'✓' if checks['budget_within_limits'] else '✗'}   (${actual_budget:.2f} / ${budget_limit or 'N/A'})",
            f"- Meals Scheduled: {'✓' if checks['meals_scheduled'] else '✗'}   ({len(meal_events)} meals)",
            f"- Tasks Scheduled: {'✓' if checks['tasks_scheduled'] else '✗'}   ({len(task_events)} tasks)",
            f"- Constraints: {'✓' if checks['constraints_satisfied'] else '✗'}   (compliance: {compliance:.2%})",
            f"- Overall: {'VALID' if is_valid else 'INVALID'}",
            f"- Signature: {signature}"
        ]

        result = VerificationResult(
            is_valid=is_valid,
            constraints_satisfied=checks["constraints_satisfied"],
            budget_within_limits=checks["budget_within_limits"],
            meals_scheduled=checks["meals_scheduled"],
            tasks_scheduled=checks["tasks_scheduled"],
            validation_trace=validation_trace,
            reproducibility_signature=signature,
            verification_summary="\n".join(summary)
        )

        logger.log_event(
            "VerifierAgent",
            "verification_complete",
            {
                "is_valid": is_valid,
                "signature": signature
            },
            self.session_id
        )

        return result.model_dump()

    # ----------------------------------------------------------
    # ADK-compatible wrapper
    # ----------------------------------------------------------
    def process(self, coordinator_data: Dict[str, Any]) -> Dict[str, Any]:

        optimized_plan = coordinator_data.get("optimized_plan", {})
        plan = optimized_plan.get("plan", {})

        verification = self.verify_plan(plan)

        return {
            "verification": verification,
            "agent": "VerifierAgent",
            "status": "success"
        }
