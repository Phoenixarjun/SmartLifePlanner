"""
Meal Agent - Generates meal plans using RecipeTool.
Supports multi-diet filtering (vegetarian, vegan, keto, omnivore, etc.).
Robust ADK-compatible agent with LLM optional and deterministic fallback.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import json
import random

from src.tools.recipe_tool import recipe_tool
from src.utils.logger import logger
from src.utils.llm_service import llm_service

# Deterministic seed for fallback behavior
RANDOM_SEED = 2025
random.seed(RANDOM_SEED)

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


class MealItem(BaseModel):
    type: str
    name: str
    recipe_id: str
    calories: int
    ingredients: List[str] = Field(default_factory=list)


class DayMealPlan(BaseModel):
    day_index: int
    day_name: str
    meals: List[Dict[str, Any]]
    total_calories: int = 0


class MealAgent:
    """
    Agent for generating meal plans.
    Uses recipe_tool when available; supports diets via constraints.
    """

    def __init__(self, session_id: Optional[str] = None, api_key: Optional[str] = None):
        self.session_id = session_id
        self.tool = recipe_tool
        # configure LLM if api_key provided
        if api_key and llm_service and hasattr(llm_service, "set_api_key"):
            try:
                llm_service.set_api_key(api_key)
            except Exception:
                pass

    # -----------------------
    # Helper: normalize recipes and apply diet filters
    # -----------------------
    def _filter_recipes_by_diet(self, recipes: List[Dict[str, Any]], diet: Optional[str]) -> List[Dict[str, Any]]:
        if not diet:
            return recipes
        diet = diet.lower().strip()
        filtered = []
        for r in recipes:
            # Recipe tool might include 'tags' or 'diet' meta
            tags = []
            if isinstance(r.get("tags"), list):
                tags = [t.lower() for t in r.get("tags", [])]
            meta_diet = str(r.get("diet", "")).lower() if r.get("diet") else ""
            name = str(r.get("name", "")).lower()
            ingredients = [str(i).lower() for i in r.get("ingredients", [])]

            ok = True
            if diet in ("vegetarian", "veg"):
                # reject recipes that include obvious meat keywords
                meat_keywords = ["chicken", "beef", "pork", "fish", "shrimp", "salmon", "bacon"]
                if any(k in name for k in meat_keywords) or any(k in " ".join(ingredients) for k in meat_keywords):
                    ok = False
                # accept if tags/meta say vegetarian/veg
                if "vegetarian" in tags or "veg" in meta_diet:
                    ok = ok and True
            elif diet == "vegan":
                nonvegan = ["milk", "egg", "cheese", "butter", "honey", "yogurt", "paneer"]
                if any(k in name for k in nonvegan) or any(k in " ".join(ingredients) for k in nonvegan):
                    ok = False
            elif diet in ("keto", "lowcarb"):
                # prefer recipes without rice/oats/sugar
                bad = ["rice", "sugar", "oats", "quinoa", "potato"]
                if any(k in name for k in bad) or any(k in " ".join(ingredients) for k in bad):
                    ok = False
            # if recipe claims diet explicitly and matches, prefer it
            if meta_diet and diet in meta_diet:
                ok = True
            if ok:
                filtered.append(r)
        # fallback: if no results found, return original list (so we have something)
        return filtered if filtered else recipes

    # -----------------------
    # Fallback deterministic generator (per-diet builtins)
    # -----------------------
    def _fallback_meal_plans(self, goals: List[str], constraints: Dict[str, Any], plan_days: int) -> List[Dict[str, Any]]:
        logger.log_event("MealAgent", "fallback_start", {"goals": goals, "constraints": constraints, "plan_days": plan_days}, self.session_id)

        diet = constraints.get("diet") or constraints.get("dietary") or constraints.get("diet_type") or None
        diet = diet.lower() if isinstance(diet, str) else None

        # Try to use recipe_tool first (best-effort)
        recipes = []
        try:
            # recipe_tool should accept dietary_constraints list
            recipes = self.tool.execute("search_recipes", dietary_constraints=[diet] if diet else [], limit=40)
            if not isinstance(recipes, list):
                recipes = []
        except Exception:
            recipes = []

        # If no recipes from tool, use builtins based on diet
        if not recipes:
            if diet and "keto" in diet:
                recipes = [
                    {"id": "k1", "name": "Keto Egg Bowl", "calories": 400, "ingredients": ["eggs", "spinach", "cheese"], "tags": ["keto"]},
                    {"id": "k2", "name": "Grilled Fish", "calories": 450, "ingredients": ["salmon", "oil", "greens"], "tags": ["keto"]},
                ]
            elif diet and "vegan" in diet:
                recipes = [
                    {"id": "v1", "name": "Tofu Stir Fry", "calories": 420, "ingredients": ["tofu", "veggies", "soy sauce"], "tags": ["vegan"]},
                    {"id": "v2", "name": "Chickpea Salad", "calories": 350, "ingredients": ["chickpeas", "lettuce", "tomato"], "tags": ["vegan"]},
                ]
            else:
                # default to omnivore/vegetarian helpful set
                recipes = [
                    {"id": "r1", "name": "Veg Curry", "calories": 450, "ingredients": ["vegetables", "spice", "oil"], "tags": ["vegetarian"]},
                    {"id": "r2", "name": "Quinoa Salad", "calories": 350, "ingredients": ["quinoa", "greens", "tomato"], "tags": ["vegetarian"]},
                    {"id": "r3", "name": "Oat Porridge", "calories": 300, "ingredients": ["oats", "milk", "banana"], "tags": ["vegetarian"]},
                    {"id": "r4", "name": "Lentil Soup", "calories": 380, "ingredients": ["lentils", "onion", "spice"], "tags": ["vegetarian"]},
                ]

        # Apply diet filter to recipes (multi-diet aware)
        recipes = self._filter_recipes_by_diet(recipes, diet)

        day_plans: List[Dict[str, Any]] = []
        for d in range(plan_days):
            # pick two distinct recipes if possible
            idx_a = (d * 2) % len(recipes)
            idx_b = (d * 2 + 1) % len(recipes)
            r_a = recipes[idx_a]
            r_b = recipes[idx_b if idx_b != idx_a else idx_a]

            meals = []
            # include breakfast occasionally
            if d % 2 == 0:
                meals.append({
                    "type": "breakfast",
                    "name": f"Simple Breakfast {d+1}",
                    "recipe_id": f"bf{d+1}",
                    "calories": 250,
                    "ingredients": ["oats", "banana", "milk"] if ("vegan" not in (diet or "")) else ["oats", "banana"]
                })

            meals.append({
                "type": "lunch",
                "name": r_a.get("name", "Lunch"),
                "recipe_id": r_a.get("id", f"r{idx_a}"),
                "calories": int(r_a.get("calories", 350)),
                "ingredients": r_a.get("ingredients", [])
            })
            meals.append({
                "type": "dinner",
                "name": r_b.get("name", "Dinner"),
                "recipe_id": r_b.get("id", f"r{idx_b}"),
                "calories": int(r_b.get("calories", 400)),
                "ingredients": r_b.get("ingredients", [])
            })

            total_cal = sum(int(m.get("calories", 0)) for m in meals)
            day_plan = DayMealPlan(day_index=d + 1, day_name=DAYS[d % len(DAYS)], meals=meals, total_calories=total_cal)
            day_plans.append(day_plan.model_dump())

        logger.log_event("MealAgent", "fallback_complete", {"generated_days": len(day_plans)}, self.session_id)
        return day_plans

    # -----------------------
    # LLM-powered generation (optional)
    # -----------------------
    def _llm_generate(self, goals: List[str], constraints: Dict[str, Any], plan_days: int) -> Optional[List[Dict[str, Any]]]:
        if not llm_service or not getattr(llm_service, "is_available", lambda: False)():
            return None

        system = (
            "You are a meal planner. Output STRICT JSON: an array of day plans. "
            "Each day plan must include: day_index (1..N), day_name, meals (array of {type,name,recipe_id,calories,ingredients}), total_calories. "
            "Return an array only."
        )
        prompt = f"Create {plan_days} day meal plans for goals: {goals}. Constraints: {json.dumps(constraints)}. Use available recipes if helpful. Return as a JSON array."

        try:
            resp = llm_service.generate_structured(prompt=prompt, system_prompt=system, temperature=0.2)
        except Exception as e:
            logger.log_event("MealAgent", "llm_error", {"error": str(e)}, self.session_id)
            return None

        # Normalize response
        meal_plans = []
        if isinstance(resp, list):
            meal_plans = resp
        elif isinstance(resp, dict):
            if "meal_plan" in resp and isinstance(resp["meal_plan"], list):
                meal_plans = resp["meal_plan"]
            elif "days" in resp and isinstance(resp["days"], list):
                meal_plans = resp["days"]
            else:
                # try finding list-like keys
                for v in resp.values():
                    if isinstance(v, list):
                        meal_plans = v
                        break

        formatted = []
        for p in meal_plans:
            try:
                day_index = int(p.get("day_index", p.get("day", 0) or 0))
                day_name = p.get("day_name", p.get("day", f"Day {day_index}"))
                meals_raw = p.get("meals", [])
                meals_clean = []
                total_cal = 0
                for m in meals_raw:
                    name = m.get("name", "Meal")
                    rid = m.get("recipe_id", m.get("id", "r?"))
                    cal = int(m.get("calories", 300))
                    ingredients = m.get("ingredients", [])
                    meal_item = {
                        "type": m.get("type", "dinner"),
                        "name": name,
                        "recipe_id": rid,
                        "calories": cal,
                        "ingredients": ingredients
                    }
                    meals_clean.append(meal_item)
                    total_cal += cal
                formatted.append(DayMealPlan(day_index=day_index or (len(formatted) + 1), day_name=day_name, meals=meals_clean, total_calories=total_cal).model_dump())
            except Exception:
                continue

        if not formatted:
            return None
        return formatted

    # -----------------------
    # Public API
    # -----------------------
    def generate_meal_plan(self, goals: List[str], constraints: Dict[str, Any], plan_days: int = 7) -> List[Dict[str, Any]]:
        logger.log_event("MealAgent", "generate_start", {"goals": goals, "constraints": constraints, "plan_days": plan_days}, self.session_id)

        # Try LLM if available
        llm_result = self._llm_generate(goals, constraints, plan_days)
        if llm_result is not None:
            logger.log_event("MealAgent", "generated_with_llm", {"days": len(llm_result)}, self.session_id)
            return llm_result

        # Fallback deterministic generator
        fallback = self._fallback_meal_plans(goals, constraints, plan_days)
        logger.log_event("MealAgent", "generated_fallback", {"days": len(fallback)}, self.session_id)
        return fallback

    def process(self, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        ADK-compatible process method.
        Returns dict with 'meal_plan' key.
        """
        # Defensive extraction
        if isinstance(intent_data, dict) and "intent" in intent_data:
            intent = intent_data["intent"]
        elif isinstance(intent_data, dict) and "raw_text" in intent_data:
            intent = intent_data
        else:
            intent = {"goals": [], "constraints": {}, "plan_duration_days": 7}

        goals = intent.get("goals", []) or []
        constraints = intent.get("constraints", {}) or {}
        plan_days = int(intent.get("plan_duration_days", intent.get("plan_days", 7)))

        logger.log_event("MealAgent", "process_start", {"goals": goals, "plan_days": plan_days}, self.session_id)
        meal_plan = self.generate_meal_plan(goals, constraints, plan_days)

        result = {"meal_plan": meal_plan, "agent": "MealAgent", "status": "success", "count": len(meal_plan)}
        logger.log_event("MealAgent", "process_complete", {"count": len(meal_plan)}, self.session_id)
        return result
