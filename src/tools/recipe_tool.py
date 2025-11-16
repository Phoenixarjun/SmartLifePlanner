"""
Recipe Tool - simple local recipe database and ADK-compliant wrapper.
Provides search_recipes(dietary_constraints: list, limit: int), get_recipe(recipe_id: str), list_recipes(limit: int).
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import json


class RecipeStore:
    def __init__(self, data_path: str = "data/recipes.json"):
        self.data_path = Path(data_path)
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        self._recipes = self._load_or_seed()

    def _seed_recipes(self) -> List[Dict[str, Any]]:
        seed = [
            {"id": "r1", "name": "Veg Curry Bowl", "diet": ["vegetarian"], "calories": 450,
             "ingredients": ["vegetables", "rice", "spices"], "instructions": "Cook rice and curry."},
            {"id": "r2", "name": "Quinoa Salad", "diet": ["vegan", "vegetarian"], "calories": 350,
             "ingredients": ["quinoa", "greens", "tomato", "olive oil"], "instructions": "Mix and serve."},
            {"id": "r3", "name": "Oat Porridge", "diet": ["vegetarian"], "calories": 300,
             "ingredients": ["oats", "milk", "banana"], "instructions": "Simmer oats in milk."},
            {"id": "r4", "name": "Lentil Soup", "diet": ["vegan", "vegetarian"], "calories": 380,
             "ingredients": ["lentils", "onion", "garlic", "spices"], "instructions": "Boil lentils and season."},
            {"id": "r5", "name": "Grilled Chicken Salad", "diet": ["omnivore"], "calories": 420,
             "ingredients": ["chicken", "greens", "tomato"], "instructions": "Grill chicken and mix."},
            {"id": "r6", "name": "Paneer Stir-Fry", "diet": ["vegetarian"], "calories": 480,
             "ingredients": ["paneer", "bell pepper", "soy sauce"], "instructions": "Stir fry paneer with veggies."}
        ]
        return seed

    def _load_or_seed(self) -> List[Dict[str, Any]]:
        if self.data_path.exists():
            try:
                with open(self.data_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                recipes = self._seed_recipes()
                self._save(recipes)
                return recipes
        else:
            recipes = self._seed_recipes()
            self._save(recipes)
            return recipes

    def _save(self, recipes: List[Dict[str, Any]]) -> None:
        with open(self.data_path, "w", encoding="utf-8") as f:
            json.dump(recipes, f, indent=2, ensure_ascii=False)

    def list_recipes(self, limit: int = 20) -> List[Dict[str, Any]]:
        return self._recipes[:max(0, int(limit))]

    def get_recipe(self, recipe_id: str) -> Optional[Dict[str, Any]]:
        for r in self._recipes:
            if r.get("id") == recipe_id:
                return r
        return None

    def search(self, dietary_constraints: Optional[List[str]] = None, limit: int = 20) -> List[Dict[str, Any]]:
        dietary_constraints = dietary_constraints or []
        if not dietary_constraints or all(not c for c in dietary_constraints):
            return self.list_recipes(limit=limit)

        # normalize constraints
        constraints = [str(c).lower().strip() for c in dietary_constraints if c]
        results = []
        for r in self._recipes:
            diet = [d.lower() for d in (r.get("diet") or [])]
            name = str(r.get("name", "")).lower()
            ingredients = " ".join([str(i).lower() for i in (r.get("ingredients") or [])])

            # include recipe if all constraints appear in diet metadata or name/ingredients
            match_all = True
            for c in constraints:
                if c in diet:
                    continue
                # allow fuzzy match by presence in name/ingredients
                if c in name or c in ingredients:
                    continue
                match_all = False
                break
            if match_all:
                results.append(r)

        # fallback: if none matched, try any-match
        if not results:
            for r in self._recipes:
                diet = [d.lower() for d in (r.get("diet") or [])]
                for c in constraints:
                    if c in diet or c in str(r.get("name", "")).lower():
                        results.append(r)
                        break

        if not results:
            results = self._recipes[:limit]

        return results[:max(0, int(limit))]


# ADK-compliant wrapper
class RecipeTool:
    def __init__(self):
        self.store = RecipeStore()

    def execute(self, action: str, **kwargs) -> Any:
        action = (action or "").strip()
        if action == "search_recipes":
            dietary_constraints = kwargs.get("dietary_constraints", []) or kwargs.get("diet", []) or []
            limit = int(kwargs.get("limit", 20) or 20)
            return self.store.search(dietary_constraints=dietary_constraints, limit=limit)

        elif action == "get_recipe":
            recipe_id = kwargs.get("recipe_id") or kwargs.get("id")
            if not recipe_id:
                return None
            return self.store.get_recipe(recipe_id)

        elif action == "list_recipes":
            limit = int(kwargs.get("limit", 20) or 20)
            return self.store.list_recipes(limit=limit)

        else:
            raise ValueError(f"Unknown action for recipe_tool: {action}")

    @property
    def name(self) -> str:
        return "recipe_tool"

    @property
    def description(self) -> str:
        return "Tool for searching and retrieving simple recipe data."


# Global instance
recipe_tool = RecipeTool()
