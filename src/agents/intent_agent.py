"""
Intent Agent - extracts structured intent from raw user text.
Robust version: uses LLM if available, otherwise deterministic heuristic fallback.
Always returns a dict with top-level "intent" key so orchestrator downstream is stable.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import re

from src.utils.logger import logger
from src.utils.llm_service import llm_service  # global instance from utils; may be None or disabled


class IntentModel(BaseModel):
    goals: List[str] = Field(default_factory=list)
    constraints: Dict[str, Any] = Field(default_factory=dict)
    priorities: List[str] = Field(default_factory=list)
    plan_duration_days: int = 7
    raw_text: Optional[str] = None


class IntentAgent:
    def __init__(self, session_id: Optional[str] = None, api_key: Optional[str] = None):
        self.session_id = session_id
        # If an api_key is explicitly provided, try to set it on the global llm_service
        try:
            if api_key and llm_service and hasattr(llm_service, "set_api_key"):
                llm_service.set_api_key(api_key)
        except Exception:
            # ignore LLM configuration errors here; fallback will be used
            pass

    # -------------------------
    # Heuristic fallback parser
    # -------------------------
    def _heuristic_parse(self, text: str) -> IntentModel:
        text_l = (text or "").lower()
        goals = []
        constraints: Dict[str, Any] = {}
        priorities: List[str] = []

        # Goals detection
        if "work" in text_l or "office" in text_l or "project" in text_l:
            goals.append("work")
        if "cook" in text_l or "cooking" in text_l or "meal" in text_l or "meals" in text_l:
            goals.append("meals")
        if "exercise" in text_l or "workout" in text_l or "gym" in text_l:
            goals.append("exercise")
        if "grocery" in text_l or "shopping" in text_l or "groceries" in text_l:
            goals.append("shopping")
        if "tasks" in text_l or "todo" in text_l or "task" in text_l:
            goals.append("tasks")
        if not goals:
            # default baseline goals
            goals = ["work", "meals", "exercise"]

        # Diet
        if "vegetarian" in text_l:
            constraints["diet"] = "vegetarian"
        elif "vegan" in text_l:
            constraints["diet"] = "vegan"
        elif "keto" in text_l:
            constraints["diet"] = "keto"

        # Budget detection ($ or ₹ or rs)
        m = re.search(r'(\$|₹|rs\.?)\s?(\d+(?:\.\d+)?)', text_l)
        if m:
            try:
                constraints["max_budget"] = float(m.group(2))
            except Exception:
                pass

        # plan duration detection
        m2 = re.search(r'(\d+)\s*(day|days|week|weeks)', text_l)
        if m2:
            num = int(m2.group(1))
            if "week" in m2.group(2):
                plan_days = max(7, num * 7)
            else:
                plan_days = num
        else:
            plan_days = 7

        # priorities simple heuristic
        if "priorit" in text_l:
            if "meals" in text_l:
                priorities.append("meals")
            if "work" in text_l:
                priorities.append("work")
            if "exercise" in text_l:
                priorities.append("exercise")
        if not priorities:
            priorities = ["meals", "work", "exercise"]

        return IntentModel(
            goals=goals,
            constraints=constraints,
            priorities=priorities,
            plan_duration_days=plan_days,
            raw_text=text
        )

    # -------------------------
    # LLM-based extraction (optional)
    # -------------------------
    def _llm_parse(self, text: str) -> Optional[IntentModel]:
        if not llm_service or not getattr(llm_service, "is_available", lambda: False)():
            return None

        try:
            system = (
                "You are an intent extraction assistant. "
                "Extract goals (list), constraints (dict), priorities (list) and plan_duration_days (int). "
                "Return STRICT JSON only with keys: goals, constraints, priorities, plan_duration_days."
            )
            resp = llm_service.generate_structured(prompt=text, system_prompt=system, temperature=0.0)
            if not isinstance(resp, dict):
                return None

            goals = resp.get("goals") or []
            constraints = resp.get("constraints") or {}
            priorities = resp.get("priorities") or []
            plan_days = resp.get("plan_duration_days") or resp.get("plan_days") or 7

            # Normalize types
            if not isinstance(goals, list):
                goals = [str(goals)]
            if not isinstance(priorities, list):
                priorities = [str(priorities)]

            return IntentModel(
                goals=goals,
                constraints=constraints,
                priorities=priorities,
                plan_duration_days=int(plan_days),
                raw_text=text
            )
        except Exception as e:
            logger.log_event("IntentAgent", "llm_parse_failed", {"error": str(e)}, self.session_id)
            return None

    # -------------------------
    # Public API
    # -------------------------
    def extract_intent(self, user_text: str) -> IntentModel:
        logger.log_event("IntentAgent", "extract_intent_start", {"raw_text": user_text}, self.session_id)

        # Try LLM first (if available)
        intent_model = None
        try:
            intent_model = self._llm_parse(user_text)
        except Exception:
            intent_model = None

        if intent_model:
            logger.log_event("IntentAgent", "extracted_with_llm", intent_model.model_dump(), self.session_id)
            return intent_model

        # fallback deterministic parser
        intent_model = self._heuristic_parse(user_text)
        logger.log_event("IntentAgent", "extracted_with_heuristic", intent_model.model_dump(), self.session_id)
        return intent_model

    def process(self, input_data: Any) -> Dict[str, Any]:
        """
        Accepts either:
         - a raw string
         - or a dict with keys like {"raw_text": "...", "session_id": "..."}
        Returns canonical dict with top-level 'intent' key.
        """
        raw_text = ""
        if isinstance(input_data, str):
            raw_text = input_data
        elif isinstance(input_data, dict):
            raw_text = input_data.get("raw_text") or input_data.get("text") or ""
        else:
            raw_text = str(input_data)

        intent_model = self.extract_intent(raw_text)
        return {
            "intent": intent_model.model_dump(),
            "agent": "IntentAgent",
            "status": "success"
        }
