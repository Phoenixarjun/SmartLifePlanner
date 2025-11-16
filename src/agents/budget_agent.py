"""
Budget Agent - Computes grocery cost and compares to budget limit.
ADK-compatible; uses grocery_tool if available, otherwise a local fallback price map.
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from src.tools.grocery_tool import grocery_tool
from src.utils.logger import logger
from src.utils.llm_service import LLMService

# Minimal local price map (fallback)
DEFAULT_PRICE_MAP = {
    "rice": 1.5,
    "vegetables": 3.0,
    "oats": 1.0,
    "milk": 1.2,
    "egg": 0.5,
    "banana": 0.3,
    "quinoa": 4.0,
    "greens": 2.0,
    "tomato": 1.0,
    "olive oil": 5.0,
    "paneer": 3.0,
    "lentils": 1.2,
    "spice": 0.5
}


class BudgetResult(BaseModel):
    """Structured budget result."""
    total: float = 0.0
    within_budget: bool = True
    shopping_list: List[str] = Field(default_factory=list)
    item_prices: Dict[str, float] = Field(default_factory=dict)


class BudgetAgent:
    """
    Agent that computes grocery costs based on meal_plan ingredients.
    """

    def __init__(self, session_id: Optional[str] = None, api_key: Optional[str] = None):
        self.session_id = session_id
        self.tool = grocery_tool
        self.llm = LLMService(api_key) if api_key else None

    # flatten meal_plan into (ingredient, est_qty) items
    def _flatten_ingredients(self, meal_plan: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        flat = []
        for day in meal_plan:
            for meal in day.get("meals", []):
                ingredients = meal.get("ingredients", []) or []
                # ingredients might be a list of strings or dicts; normalize
                for ing in ingredients:
                    if isinstance(ing, dict):
                        name = ing.get("ingredient") or ing.get("name")
                        qty = ing.get("quantity", 1)
                    else:
                        name = str(ing)
                        qty = 1
                    if name:
                        flat.append({"ingredient": name, "quantity": qty})
        return flat

    def _estimate_prices_locally(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        shopping_list = []
        item_prices = {}
        total_cost = 0.0
        for it in items:
            name = it.get("ingredient", "").lower().strip()
            qty = float(it.get("quantity", 1))
            # normalize common synonyms simple mapping
            name_key = name.replace("-", " ").replace("_", " ")
            # try to pick a base word
            base = name_key.split()[0] if name_key else name_key
            price = DEFAULT_PRICE_MAP.get(name_key) or DEFAULT_PRICE_MAP.get(base) or 2.0
            cost = price * qty
            shopping_list.append(name)
            item_prices[name] = round(price, 2)
            total_cost += cost
        return {"items": [{"ingredient": k, "unit_price": v} for k, v in item_prices.items()], "total_cost": round(total_cost, 2)}

    def compute_budget(self, constraints: Dict[str, Any], meal_plan: List[Dict[str, Any]]) -> Dict[str, Any]:
        logger.log_event(
            "BudgetAgent",
            "compute_budget",
            {"meals": len(meal_plan)},
            self.session_id
        )

        max_budget = constraints.get("max_budget", None)

        ingredient_entries = self._flatten_ingredients(meal_plan)

        result = None
        # Try using grocery_tool if it supports a calculate action
        if self.tool and hasattr(self.tool, "execute"):
            try:
                # call common actions used across implementations; try 'calculate_grocery_list' then 'estimate_items'
                try:
                    result = self.tool.execute("calculate_grocery_list", meals=ingredient_entries)
                except Exception:
                    result = self.tool.execute("estimate_items", items=ingredient_entries)
            except Exception as e:
                logger.log_event("BudgetAgent", "grocery_tool_failed", {"error": str(e)}, self.session_id)
                result = None

        # If tool didn't return usable structure, fallback to local estimate
        if not result or not isinstance(result, dict) or "total_cost" not in result:
            result = self._estimate_prices_locally(ingredient_entries)

        # Normalize result shape
        items = result.get("items", [])
        total_cost = float(result.get("total_cost", 0.0))

        shopping_list = []
        prices = {}
        for it in items:
            ing = it.get("ingredient")
            unit = it.get("unit_price", 0.0)
            shopping_list.append(ing)
            prices[ing] = float(unit)

        within_budget = True
        if max_budget is not None:
            try:
                within_budget = total_cost <= float(max_budget)
            except Exception:
                within_budget = True

        return BudgetResult(
            total=round(total_cost, 2),
            within_budget=within_budget,
            shopping_list=shopping_list,
            item_prices=prices
        ).model_dump()

    def process(self, intent_data: Dict[str, Any], meal_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        ADK-compatible process call.
        Computes total grocery budget from meal_data.
        """
        intent = intent_data.get("intent", {}) if isinstance(intent_data, dict) else {}
        constraints = intent.get("constraints", {}) or {}
        meal_plan = meal_data.get("meal_plan", []) if isinstance(meal_data, dict) else meal_data or []

        budget_result = self.compute_budget(constraints, meal_plan)

        return {
            "budget": budget_result,
            "agent": "BudgetAgent",
            "status": "success"
        }
