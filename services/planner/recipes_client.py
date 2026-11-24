"""HTTP client for the recipes service: the planner's side of the seam.

In Assignment 1 these were Python functions in recipes/service.py. Now the recipes
domain is a separate service, so the planner asks it over HTTP instead.
The function names and return values are the same as before, so the rest of the
planner (e.g. shopping.collect_lines) does not need to change.
"""
import requests

import config


class RecipesUnavailable(Exception):
    """The recipes service gave no usable answer: unreachable, too slow, or an error."""


def _get(path, params=None):
    """GET a recipes endpoint with a timeout, and turn every failure into RecipesUnavailable."""
    url = config.RECIPES_URL.rstrip("/") + path
    try:
        response = requests.get(url, params=params, timeout=config.RECIPES_TIMEOUT_S)
    except requests.RequestException as exc:  # refused connection, DNS failure, timeout...
        raise RecipesUnavailable(f"recipes service unreachable: {exc}") from exc
    if response.status_code >= 500:
        raise RecipesUnavailable(f"recipes service error: HTTP {response.status_code}")
    return response


def _json(response):
    """The body of a 200 response; anything else is unexpected and treated as unavailable."""
    if response.status_code != 200:
        raise RecipesUnavailable(f"unexpected answer from recipes service: HTTP {response.status_code}")
    try:
        return response.json()
    except ValueError as exc:
        raise RecipesUnavailable("recipes service returned invalid JSON") from exc


def list_recipe_choices():
    """[{'id': 1, 'name': 'Pancakes'}, ...] for the plan grid and the recipe dropdown."""
    return [{"id": r["id"], "name": r["name"]} for r in _json(_get("/recipes"))]


def recipe_exists(recipe_id):
    """True if the recipe exists. A 404 means it doesn't (it may have been deleted)."""
    response = _get(f"/recipes/{recipe_id}")
    if response.status_code == 404:
        return False
    _json(response)
    return True


def get_scaled_ingredients(recipe_id, servings):
    """The recipe's ingredient lines scaled to `servings`, or None if the recipe doesn't exist.

    Same contract as the old service function, so shopping.collect_lines works unchanged.
    """
    response = _get(f"/recipes/{recipe_id}/scaled", params={"servings": servings})
    if response.status_code == 404:
        return None
    return _json(response)["ingredients"]
