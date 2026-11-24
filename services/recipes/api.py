"""JSON API of the recipes service.

This replaces the server-rendered pages: the static UI and the planner service both
call these endpoints. Validation and SQL are unchanged (validation.py, repository.py).
"""
from flask import Blueprint, request

import db
from recipes import repository
from recipes.scaling import scale_ingredients
from recipes.validation import parse_recipe_form

bp = Blueprint("recipes_api", __name__, url_prefix="/recipes")


def _not_found(recipe_id):
    return {"error": f"recipe {recipe_id} not found"}, 404


def _payload_as_form():
    """Read the JSON body and turn it into the string fields parse_recipe_form expects.

    `ingredients` may be one text block ("200 g flour\\n2 pcs egg") or a list of lines.
    """
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return None
    ingredients = body.get("ingredients", "")
    if isinstance(ingredients, list):
        ingredients = "\n".join(str(line) for line in ingredients)
    return {
        "name": str(body.get("name", "")),
        "base_servings": str(body.get("base_servings", "")),
        "prep_minutes": str(body.get("prep_minutes", "")),
        "instructions": str(body.get("instructions", "")),
        "ingredients": str(ingredients),
    }


@bp.get("")
def list_view():
    """All recipes, without their ingredients (used for lists and the planner's dropdown)."""
    return repository.list_recipes(db.get_db())


@bp.post("")
def create_view():
    form = _payload_as_form()
    if form is None:
        return {"errors": ["Request body must be a JSON object."]}, 400
    data, errors = parse_recipe_form(form)
    if errors:
        return {"errors": errors}, 400
    conn = db.get_db()
    recipe_id = repository.create_recipe(conn, **data)
    return repository.get_recipe(conn, recipe_id), 201, {"Location": f"/recipes/{recipe_id}"}


@bp.get("/<int:recipe_id>")
def detail_view(recipe_id):
    """One recipe with its ingredient lines. The planner uses the 404 to know a recipe is gone."""
    recipe = repository.get_recipe(db.get_db(), recipe_id)
    if recipe is None:
        return _not_found(recipe_id)
    return recipe


@bp.put("/<int:recipe_id>")
def update_view(recipe_id):
    form = _payload_as_form()
    if form is None:
        return {"errors": ["Request body must be a JSON object."]}, 400
    data, errors = parse_recipe_form(form)
    if errors:
        return {"errors": errors}, 400
    conn = db.get_db()
    if not repository.update_recipe(conn, recipe_id, **data):
        return _not_found(recipe_id)
    return repository.get_recipe(conn, recipe_id)


@bp.delete("/<int:recipe_id>")
def delete_view(recipe_id):
    if not repository.delete_recipe(db.get_db(), recipe_id):
        return _not_found(recipe_id)
    return "", 204


@bp.get("/<int:recipe_id>/scaled")
def scaled_view(recipe_id):
    """The recipe's ingredients scaled to ?servings=N. Called by the planner for the shopping list."""
    try:
        servings = int(request.args.get("servings", ""))
        if servings <= 0:
            raise ValueError
    except ValueError:
        return {"error": "servings must be a whole number greater than 0"}, 400
    recipe = repository.get_recipe(db.get_db(), recipe_id)
    if recipe is None:
        return _not_found(recipe_id)
    return {
        "recipe_id": recipe["id"],
        "name": recipe["name"],
        "servings": servings,
        "ingredients": scale_ingredients(recipe["ingredients"], recipe["base_servings"], servings),
    }
