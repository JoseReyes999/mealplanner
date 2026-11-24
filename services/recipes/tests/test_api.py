"""Tests for the recipes JSON API (api.py), with Flask's test client and the SQL Server test database"""
import pytest

from app import create_app

PANCAKES = {
    "name": "Pancakes",
    "base_servings": 4,
    "instructions": "Mix and fry.",
    "ingredients": "200 g flour\n2 pcs egg",
}


@pytest.fixture
def client(database_url):
    return create_app(database_url).test_client()


def create(client, **overrides):
    return client.post("/recipes", json={**PANCAKES, **overrides})


def test_create_returns_201_with_location_and_recipe(client):
    response = create(client)
    assert response.status_code == 201
    assert response.headers["Location"] == "/recipes/1"
    body = response.get_json()
    assert body["name"] == "Pancakes"
    assert [(i["name"], i["quantity"], i["unit"]) for i in body["ingredients"]] == [
        ("egg", 2.0, "pcs"),
        ("flour", 200.0, "g"),
    ]


def test_create_accepts_ingredients_as_a_list(client):
    response = create(client, ingredients=["200 g flour", "300 ml milk"])
    assert response.status_code == 201
    assert len(response.get_json()["ingredients"]) == 2


@pytest.mark.parametrize("body, message", [
    ({**PANCAKES, "ingredients": "2 cup milk"}, "unknown unit"),
    ({**PANCAKES, "base_servings": 0}, "greater than 0"),
    ({**PANCAKES, "name": ""}, "Name is required"),
    ("not an object", "JSON object"),
])
def test_create_rejects_invalid_input(client, body, message):
    response = client.post("/recipes", json=body)
    assert response.status_code == 400
    assert any(message in e for e in response.get_json()["errors"])

def test_prep_minutes_round_trip(client):
    assert create(client).get_json()["prep_minutes"] == 0  # not sent: defaults to 0
    body = create(client, name="Bread", ingredients="1 kg flour", prep_minutes=90).get_json()
    assert body["prep_minutes"] == 90
    assert client.post("/recipes", json={**PANCAKES, "prep_minutes": -1}).status_code == 400

def test_list_recipes(client):
    create(client)
    create(client, name="Bread", ingredients="1 kg flour")
    assert [r["name"] for r in client.get("/recipes").get_json()] == ["Bread", "Pancakes"]


def test_get_one_and_404(client):
    create(client)
    assert client.get("/recipes/1").get_json()["base_servings"] == 4
    missing = client.get("/recipes/999")
    assert missing.status_code == 404
    assert "not found" in missing.get_json()["error"]


def test_update(client):
    create(client)
    response = client.put("/recipes/1", json={**PANCAKES, "name": "Crepes", "ingredients": "400 g flour"})
    assert response.status_code == 200
    body = response.get_json()
    assert body["name"] == "Crepes"
    assert [i["quantity"] for i in body["ingredients"]] == [400.0]


def test_update_invalid_and_missing(client):
    create(client)
    assert client.put("/recipes/1", json={**PANCAKES, "base_servings": "x"}).status_code == 400
    assert client.put("/recipes/1", data="nope", content_type="text/plain").status_code == 400
    assert client.put("/recipes/999", json=PANCAKES).status_code == 404


def test_delete(client):
    create(client)
    assert client.delete("/recipes/1").status_code == 204
    assert client.get("/recipes/1").status_code == 404
    assert client.delete("/recipes/1").status_code == 404


def test_scaled_ingredients_for_the_planner(client):
    create(client)
    response = client.get("/recipes/1/scaled?servings=6")
    assert response.status_code == 200
    body = response.get_json()
    assert body["servings"] == 6
    assert [(i["name"], i["quantity"]) for i in body["ingredients"]] == [("egg", 3.0), ("flour", 300.0)]
    assert body["ingredients"][0]["ingredient_id"] == 2  # the shopping list merges by this id


@pytest.mark.parametrize("query", ["", "?servings=0", "?servings=abc"])
def test_scaled_rejects_bad_servings(client, query):
    create(client)
    assert client.get(f"/recipes/1/scaled{query}").status_code == 400


def test_scaled_missing_recipe_is_404(client):
    assert client.get("/recipes/999/scaled?servings=2").status_code == 404
