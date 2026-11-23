"""Cross-seam integration tests: the planner API with the recipes service replaced by a stub.

The stub answers the same HTTP endpoints as the real recipes service (GET /recipes,
GET /recipes/{id}, GET /recipes/{id}/scaled), so the whole planner side runs for real:
api.py -> recipes_client (HTTP, timeout) -> shopping.py -> repository -> SQLite.
"""
from unittest.mock import patch
from urllib.parse import urlparse

import pytest
import requests

import recipes_client
from app import create_app


class FakeResponse:
    def __init__(self, status_code, body):
        self.status_code = status_code
        self._body = body

    def json(self):
        return self._body


class StubRecipesService:
    """Plays the recipes service: same paths and JSON shapes, with recipes kept in a dict."""

    def __init__(self):
        self.up = True
        self.recipes = {
            1: {"name": "Pancakes", "base_servings": 4,
                "ingredients": [(1, "flour", 200.0, "g"), (2, "egg", 2.0, "pcs")]},
            2: {"name": "Bread", "base_servings": 2,
                "ingredients": [(1, "flour", 1.0, "kg")]},
        }

    def get(self, url, params=None, timeout=None):
        assert timeout is not None, "every call to recipes must have a timeout"
        if not self.up:
            raise requests.ConnectionError("recipes is down")
        parts = urlparse(url).path.strip("/").split("/")  # e.g. ["recipes", "1", "scaled"]
        if parts == ["recipes"]:
            return FakeResponse(200, [{"id": i, "name": r["name"]} for i, r in self.recipes.items()])
        recipe = self.recipes.get(int(parts[1]))
        if recipe is None:
            return FakeResponse(404, {"error": "recipe not found"})
        if len(parts) == 2:
            return FakeResponse(200, {"id": int(parts[1]), "name": recipe["name"]})
        factor = params["servings"] / recipe["base_servings"]
        lines = [{"ingredient_id": i, "name": n, "quantity": q * factor, "unit": u}
                 for i, n, q, u in recipe["ingredients"]]
        return FakeResponse(200, {"recipe_id": int(parts[1]), "ingredients": lines})


@pytest.fixture
def recipes():
    stub = StubRecipesService()
    with patch.object(recipes_client.requests, "get", side_effect=stub.get):
        yield stub


@pytest.fixture
def client(database_url, recipes):
    return create_app(database_url).test_client()


PLAN = {"name": "Week 41", "week_start": "2026-10-05"}


def make_plan(client):
    return client.post("/plans", json=PLAN).get_json()["id"]


def add(client, plan_id, recipe_id, servings, day="mon", meal_slot="dinner"):
    return client.post(f"/plans/{plan_id}/entries",
                       json={"day": day, "meal_slot": meal_slot, "recipe_id": recipe_id, "servings": servings})


# ---- plans (planner's own data) ----

def test_create_list_get_and_delete_plan(client):
    response = client.post("/plans", json=PLAN)
    assert response.status_code == 201
    assert response.headers["Location"] == "/plans/1"
    assert [p["name"] for p in client.get("/plans").get_json()] == ["Week 41"]
    assert client.get("/plans/1").get_json()["entries"] == []
    assert client.delete("/plans/1").status_code == 204
    assert client.get("/plans/1").status_code == 404
    assert client.delete("/plans/1").status_code == 404


@pytest.mark.parametrize("body, message", [
    ({**PLAN, "week_start": "2026-10-07"}, "Monday"),
    ({**PLAN, "name": ""}, "Name is required"),
    (["not", "an", "object"], "JSON object"),
])
def test_create_plan_rejects_invalid_input(client, body, message):
    response = client.post("/plans", json=body)
    assert response.status_code == 400
    assert any(message in e for e in response.get_json()["errors"])


# ---- entries (cross the seam: the recipe must exist) ----

def test_add_entry_shows_recipe_name_from_recipes_service(client):
    plan_id = make_plan(client)
    response = add(client, plan_id, recipe_id=1, servings=6)
    assert response.status_code == 200
    entry = response.get_json()["entries"][0]
    assert (entry["recipe_name"], entry["servings"]) == ("Pancakes", 6)


def test_add_entry_replaces_same_slot(client):
    plan_id = make_plan(client)
    add(client, plan_id, 1, 6)
    entries = add(client, plan_id, 2, 2).get_json()["entries"]
    assert [(e["recipe_name"], e["servings"]) for e in entries] == [("Bread", 2)]


def test_add_entry_with_unknown_recipe_is_rejected(client):
    plan_id = make_plan(client)
    response = add(client, plan_id, recipe_id=99, servings=2)
    assert response.status_code == 400
    assert "doesn't exist" in response.get_json()["errors"][0]


def test_add_entry_invalid_input_and_missing_plan(client):
    plan_id = make_plan(client)
    assert add(client, plan_id, 1, 0).status_code == 400
    assert client.post(f"/plans/{plan_id}/entries", data="x", content_type="text/plain").status_code == 400
    assert add(client, 999, 1, 2).status_code == 404


def test_remove_entry(client):
    plan_id = make_plan(client)
    entry_id = add(client, plan_id, 1, 2).get_json()["entries"][0]["id"]
    assert client.delete(f"/plans/{plan_id}/entries/{entry_id}").status_code == 204
    assert client.delete(f"/plans/{plan_id}/entries/{entry_id}").status_code == 404


def test_deleted_recipe_shows_placeholder(client, recipes):
    plan_id = make_plan(client)
    add(client, plan_id, 1, 2)
    del recipes.recipes[1]  # deleted in the other service; the soft reference stays
    assert client.get(f"/plans/{plan_id}").get_json()["entries"][0]["recipe_name"] == "(deleted recipe)"


# ---- the shopping list: the cross-seam flow ----

def test_shopping_list_merges_scaled_recipes(client):
    plan_id = make_plan(client)
    add(client, plan_id, 1, 6, day="mon")   # Pancakes x1.5 -> 300 g flour, 3 eggs
    add(client, plan_id, 2, 2, day="tue")   # Bread x1 -> 1 kg flour
    body = client.get(f"/plans/{plan_id}/shopping-list").get_json()
    assert body["items"] == [
        {"name": "egg", "quantity": 3, "unit": "pcs"},
        {"name": "flour", "quantity": 1.3, "unit": "kg"},
    ]
    assert body["missing_recipes"] == 0


def test_shopping_list_skips_deleted_recipes(client, recipes):
    plan_id = make_plan(client)
    add(client, plan_id, 1, 4, day="mon")
    add(client, plan_id, 2, 2, day="tue")
    del recipes.recipes[2]
    body = client.get(f"/plans/{plan_id}/shopping-list").get_json()
    assert body["missing_recipes"] == 1
    assert [i["name"] for i in body["items"]] == ["egg", "flour"]


def test_shopping_list_missing_plan_is_404(client):
    assert client.get("/plans/999/shopping-list").status_code == 404


# ---- partial failure: recipes is down ----

def test_recipes_down_planner_still_serves_its_own_data(client, recipes):
    plan_id = make_plan(client)
    add(client, plan_id, 1, 2)
    recipes.up = False
    assert client.get("/plans").status_code == 200
    body = client.get(f"/plans/{plan_id}").get_json()
    assert body["recipes_available"] is False
    assert body["entries"][0]["recipe_name"] is None
    assert "unavailable" in body["notice"]


def test_recipes_down_shopping_list_fails_clearly(client, recipes):
    plan_id = make_plan(client)
    add(client, plan_id, 1, 2)
    recipes.up = False
    response = client.get(f"/plans/{plan_id}/shopping-list")
    assert response.status_code == 503
    assert "unavailable" in response.get_json()["error"]


def test_recipes_down_adding_an_entry_saves_nothing(client, recipes):
    plan_id = make_plan(client)
    recipes.up = False
    response = add(client, plan_id, 1, 2)
    assert response.status_code == 503
    recipes.up = True
    assert client.get(f"/plans/{plan_id}").get_json()["entries"] == []
