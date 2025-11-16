"""
Task Agent - Proposes weekly tasks using TaskDB tool.
Robust ADK-compatible version with deterministic fallback and optional LLM.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from src.tools.task_db import task_db_tool
from src.utils.logger import logger
from src.utils.llm_service import llm_service


class Task(BaseModel):
    """Task model."""
    title: str
    description: str = ""
    duration_minutes: int = 60
    priority: str = "medium"
    preferred_time_block: str = "morning"


class TaskAgent:
    """
    Agent for proposing and managing tasks.
    Uses TaskDB tool for persistence.
    Falls back to deterministic task generation when LLM unavailable.
    """

    def __init__(self, session_id: Optional[str] = None, api_key: Optional[str] = None):
        self.session_id = session_id
        self.tool = task_db_tool

        # configure global LLM only if api key provided
        if api_key and hasattr(llm_service, "set_api_key"):
            try:
                llm_service.set_api_key(api_key)
            except Exception:
                pass

    # ----------------------------------------
    # Fallback deterministic tasks (no duplication across days)
    # ----------------------------------------
    def _fallback_tasks(self, goals: List[str], plan_days: int) -> List[Dict[str, Any]]:
        default_map = {
            "work": [
                ("Work Session", "Focused work time", 90, "high", "morning"),
                ("Emails & Planning", "Daily admin", 30, "medium", "afternoon")
            ],
            "exercise": [
                ("Workout", "30-minute fitness routine", 30, "high", "morning"),
                ("Stretch", "10-minute stretch", 10, "low", "evening")
            ],
            "cooking": [
                ("Meal Prep", "Prepare ingredients for meals", 45, "medium", "afternoon")
            ],
            "grocery": [
                ("Grocery Shopping", "Buy weekly groceries", 60, "medium", "evening")
            ],
            "study": [
                ("Learning Block", "Skill learning session", 60, "medium", "morning")
            ]
        }

        base_tasks: List[Dict[str, Any]] = []
        for g in goals:
            key = g.lower().strip()
            if key in default_map:
                for t in default_map[key]:
                    base_tasks.append(
                        Task(
                            title=t[0],
                            description=t[1],
                            duration_minutes=t[2],
                            priority=t[3],
                            preferred_time_block=t[4]
                        ).model_dump()
                    )

        # If nothing matched → baseline tasks
        if not base_tasks:
            base_tasks = [
                Task(title="Plan & Prioritise", description="Organize the week's priorities", duration_minutes=30).model_dump(),
                Task(title="Quick Workout", description="Short exercise", duration_minutes=20).model_dump()
            ]

        # Produce a reasonable number of tasks (bounded) — don't multiply per day
        # Aim for up to min( max_tasks, plan_days * 2 )
        max_tasks = max(3, min(len(base_tasks) * 2, plan_days * 2))
        tasks = []
        i = 0
        while len(tasks) < max_tasks:
            tasks.append(base_tasks[i % len(base_tasks)].copy())
            i += 1

        return tasks

    # ----------------------------------------
    # LLM version (optional)
    # ----------------------------------------
    def _llm_tasks(self, goals: List[str], constraints: Dict[str, Any], plan_days: int):
        if not llm_service or not getattr(llm_service, "is_available", lambda: False)():
            return None

        system = """You are a task planning agent.
Return ONLY JSON: an array of task objects:
[
  {
    "title": "...",
    "description": "...",
    "duration_minutes": 30,
    "priority": "low"|"medium"|"high",
    "preferred_time_block": "morning"|"afternoon"|"evening"
  }
]
IMPORTANT: Always return an array."""
        user_prompt = (
            f"Generate up to {plan_days*2} useful tasks for goals: {goals}. "
            f"Constraints: {constraints}. Ensure variety and assign realistic durations and time blocks. "
            f"Return as a JSON array."
        )

        try:
            result = llm_service.generate_structured(
                prompt=user_prompt,
                system_prompt=system,
                temperature=0.3
            )
        except Exception as e:
            logger.log_event("TaskAgent", "llm_failure", {"error": str(e)}, self.session_id)
            return None

        # normalize shapes
        items = []
        if isinstance(result, list):
            items = result
        elif isinstance(result, dict):
            if "tasks" in result and isinstance(result["tasks"], list):
                items = result["tasks"]
            else:
                # try flattening values that look like lists of dicts
                for v in result.values():
                    if isinstance(v, list):
                        items = v
                        break

        tasks = []
        for item in items:
            if not isinstance(item, dict):
                continue
            try:
                t = Task(
                    title=item.get("title", "Task"),
                    description=item.get("description", ""),
                    duration_minutes=int(item.get("duration_minutes", 60)),
                    priority=item.get("priority", "medium"),
                    preferred_time_block=item.get("preferred_time_block", "morning")
                ).model_dump()
                tasks.append(t)
            except Exception:
                continue

        return tasks

    # ----------------------------------------
    # Public entry: propose tasks
    # ----------------------------------------
    def propose_tasks(self, goals: List[str], constraints: Dict[str, Any], plan_days: int):
        logger.log_event(
            "TaskAgent",
            "propose_tasks",
            {"goals": goals, "plan_days": plan_days},
            self.session_id
        )

        # LLM path (only if available)
        if llm_service and getattr(llm_service, "is_available", lambda: False)():
            tasks = self._llm_tasks(goals, constraints, plan_days)
            if tasks:
                # push to DB but ignore DB result
                for t in tasks:
                    try:
                        self.tool.execute("add_task", **t)
                    except Exception:
                        pass
                return tasks

        # fallback path (deterministic, non-duplicating)
        tasks = self._fallback_tasks(goals, plan_days)
        for t in tasks:
            try:
                self.tool.execute("add_task", **t)
            except Exception:
                pass
        return tasks

    # ----------------------------------------
    # ADK process wrapper
    # ----------------------------------------
    def process(self, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        intent = intent_data.get("intent", {}) if isinstance(intent_data, dict) else {}
        goals = intent.get("goals", []) or ["work"]
        constraints = intent.get("constraints", {}) or {}
        plan_days = int(intent.get("plan_duration_days", intent.get("plan_days", 7)))

        tasks = self.propose_tasks(goals, constraints, plan_days)

        return {
            "tasks": tasks,
            "agent": "TaskAgent",
            "status": "success"
        }
