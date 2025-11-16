"""
Grocery Tool - deterministic ADK tool for estimating grocery costs and building shopping lists.
Supports calculate_grocery_list and legacy estimate_cost.
"""

from typing import Any, Dict, List
from collections import Counter
import math


class GroceryTool:
    """Simple price estimation tool with deterministic prices."""

    def __init__(self):
        # Static deterministic price list (currency units)
        self.price_map = {
            "rice": 2.0,
            "vegetables": 3.0,
            "spices": 1.0,
            "greek yogurt": 2.5,
            "berries": 3.2,
            "quinoa": 4.0,
            "greens": 2.0,
            "tomato": 1.0,
            "olive oil": 5.0,
            "oats": 1.5,
            "milk": 1.2,
            "banana": 0.5,
            "paneer": 4.5,
            "lentils": 2.5,
            "onion": 0.8,
            "garlic": 0.6,
            "soy sauce": 1.3,
            "chicken": 6.0,
            "egg": 0.25,
            # synonyms
            "broccoli": 2.5,
            "carrot": 1.2,
            "pasta": 1.6,
            "tomato sauce": 1.8,
            "black beans": 1.5,
            "corn": 1.2,
            "yogurt": 2.3,
            "honey": 3.5,
        }

    def _normalize(self, name: str) -> str:
        if not isinstance(name, str):
            return ""
        return name.strip().lower()

    def estimate_cost(self, ingredients: List[str]) -> float:
        cost = 0.0
        for item in ingredients:
            n = self._normalize(item)
            unit = self.price_map.get(n, 2.0)
            cost += float(unit)
        return round(cost, 2)

    def calculate_grocery_list(self, meals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate shopping list and total cost.
        `meals` expected to be a list of meal dicts with an "ingredients" list.
        Returns: {"items": [{"ingredient","quantity","unit_price","cost"}, ...], "total_cost": float}
        """
        counter = Counter()
        for meal in meals or []:
            # support alternate keys
            ingredients = meal.get("ingredients") or meal.get("ingredient_list") or meal.get("ingredient") or []
            if isinstance(ingredients, str):
                # try split by comma
                ingredients = [i.strip() for i in ingredients.split(",") if i.strip()]
            for ing in ingredients:
                counter[self._normalize(ing)] += 1

        items = []
        total_cost = 0.0
        for ing, qty in counter.items():
            unit_price = float(self.price_map.get(ing, 2.0))
            cost = round(unit_price * qty, 2)
            items.append({
                "ingredient": ing,
                "quantity": int(qty),
                "unit_price": round(unit_price, 2),
                "cost": cost
            })
            total_cost += cost

        return {"items": items, "total_cost": round(total_cost, 2)}

    def execute(self, action: str, **kwargs) -> Any:
        action = (action or "").strip()
        if action == "calculate_grocery_list":
            meals = kwargs.get("meals", []) or []
            return self.calculate_grocery_list(meals)

        if action == "estimate_cost":
            ingredients = kwargs.get("ingredients", []) or []
            return self.estimate_cost(ingredients)

        raise ValueError(f"GroceryTool: Unknown action '{action}'")

    @property
    def name(self) -> str:
        return "grocery_tool"

    @property
    def description(self) -> str:
        return "Tool for estimating grocery cost and building shopping lists."


# global instance
grocery_tool = GroceryTool()
