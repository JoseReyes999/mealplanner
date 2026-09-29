"""Public interface of the recipes domain.

This is the ONLY module other domains (the planner) may import from `recipes`.
It returns plain dicts, never database rows, so that if recipes became its own
microservice, these functions could be replaced by HTTP calls without the
planner noticing.
"""
import db
from recipes import repository


def list_recipe_choices():
    """[{'id': 1, 'name': 'Pancakes'}, ...] for the planner's recipe dropdown."""
    return [{"id": r["id"], "name": r["name"]} for r in repository.list_recipes(db.get_db())]


def recipe_exists(recipe_id):
    """True if the recipe exists. The planner checks this before adding it to a plan."""
    return repository.get_recipe(db.get_db(), recipe_id) is not None


def get_recipe_ingredients(recipe_id):
    """A recipe's name, base servings and ingredient lines, or None if it doesn't exist.

    Example:
    {'id': 1, 'name': 'Pancakes', 'base_servings': 4,
     'ingredients': [{'ingredient_id': 3, 'name': 'flour', 'quantity': 200.0, 'unit': 'g'}]}
    """
    recipe = repository.get_recipe(db.get_db(), recipe_id)
    if recipe is None:
        return None
    return {
        "id": recipe["id"],
        "name": recipe["name"],
        "base_servings": recipe["base_servings"],
        "ingredients": [
            {
                "ingredient_id": line["ingredient_id"],
                "name": line["name"],
                "quantity": line["quantity"],
                "unit": line["unit"],
            }
            for line in recipe["ingredients"]
        ],
    }