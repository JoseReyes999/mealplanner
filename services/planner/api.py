"""JSON API of the planner service.

The planner owns meal plans and their entries. Everything it needs to know about
recipes (names, whether one exists, scaled ingredients) comes from the recipes
service over HTTP, through recipes_client. When that service is down, the planner
keeps serving its own data and fails the cross-seam parts with a clear 503.
"""
from flask import Blueprint, request

import db
import recipes_client
from planner import repository
from planner.shopping import build_shopping_list, collect_lines
from planner.validation import parse_entry_form, parse_plan_form
from recipes_client import RecipesUnavailable

bp = Blueprint("planner_api", __name__, url_prefix="/plans")

RECIPES_DOWN = "The recipes service is unavailable right now. Please try again in a moment."


def _not_found(plan_id):
    return {"error": f"plan {plan_id} not found"}, 404


def _json_body_as_form():
    """The JSON body as the string fields the Assignment 1 validators expect, or None if it isn't an object."""
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return None
    return {key: str(value) for key, value in body.items()}


def _with_recipe_names(plan):
    """Add each entry's recipe name, asked to the recipes service.

    If recipes is down, the plan is still returned (the planner's own data), with
    recipe_name None and recipes_available False, so the UI can show a notice.
    """
    try:
        names = {r["id"]: r["name"] for r in recipes_client.list_recipe_choices()}
    except RecipesUnavailable:
        for entry in plan["entries"]:
            entry["recipe_name"] = None
        return {**plan, "recipes_available": False, "notice": RECIPES_DOWN}
    for entry in plan["entries"]:
        # recipe_id is a soft reference: the recipe may have been deleted in the other service.
        entry["recipe_name"] = names.get(entry["recipe_id"], "(deleted recipe)")
    return {**plan, "recipes_available": True}


@bp.get("")
def list_view():
    return repository.list_plans(db.get_db())


@bp.post("")
def create_view():
    form = _json_body_as_form()
    if form is None:
        return {"errors": ["Request body must be a JSON object."]}, 400
    data, errors = parse_plan_form(form)
    if errors:
        return {"errors": errors}, 400
    conn = db.get_db()
    plan_id = repository.create_plan(conn, **data)
    return repository.get_plan(conn, plan_id), 201, {"Location": f"/plans/{plan_id}"}


@bp.get("/<int:plan_id>")
def detail_view(plan_id):
    plan = repository.get_plan(db.get_db(), plan_id)
    if plan is None:
        return _not_found(plan_id)
    return _with_recipe_names(plan)


@bp.delete("/<int:plan_id>")
def delete_view(plan_id):
    if not repository.delete_plan(db.get_db(), plan_id):
        return _not_found(plan_id)
    return "", 204


@bp.post("/<int:plan_id>/entries")
def add_entry_view(plan_id):
    """Put a recipe in a meal. Crosses the seam: the recipe must exist in the recipes service."""
    conn = db.get_db()
    if repository.get_plan(conn, plan_id) is None:
        return _not_found(plan_id)
    form = _json_body_as_form()
    if form is None:
        return {"errors": ["Request body must be a JSON object."]}, 400
    data, errors = parse_entry_form(form)
    if errors:
        return {"errors": errors}, 400
    try:
        exists = recipes_client.recipe_exists(data["recipe_id"])
    except RecipesUnavailable:
        # Without recipes we can't check the soft reference, so nothing is saved.
        return {"error": RECIPES_DOWN}, 503
    if not exists:
        return {"errors": ["That recipe doesn't exist."]}, 400
    repository.set_entry(conn, plan_id, **data)
    return _with_recipe_names(repository.get_plan(conn, plan_id))


@bp.delete("/<int:plan_id>/entries/<int:entry_id>")
def remove_entry_view(plan_id, entry_id):
    if not repository.remove_entry(db.get_db(), plan_id, entry_id):
        return {"error": f"entry {entry_id} not found in plan {plan_id}"}, 404
    return "", 204


@bp.get("/<int:plan_id>/shopping-list")
def shopping_list_view(plan_id):
    """The cross-seam flow: for each planned meal, ask recipes for its scaled ingredients, then merge."""
    plan = repository.get_plan(db.get_db(), plan_id)
    if plan is None:
        return _not_found(plan_id)
    try:
        lines, missing = collect_lines(plan["entries"], recipes_client.get_scaled_ingredients)
    except RecipesUnavailable:
        return {"error": RECIPES_DOWN, "plan_id": plan_id}, 503
    return {
        "plan_id": plan_id,
        "items": build_shopping_list(lines),
        "missing_recipes": len(missing),  # planned meals whose recipe was deleted
    }