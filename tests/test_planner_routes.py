"""End-to-end checks for the planner pages, plus build_week."""
from datetime import date

import pytest

from app import create_app
from planner.routes import build_week


@pytest.fixture
def client(tmp_path):
    return create_app(str(tmp_path / "test.db")).test_client()


RECIPE = {
    "name": "Pancakes",
    "base_servings": "4",
    "instructions": "Mix and fry.",
    "ingredients": "200 g flour",
}
PLAN = {"name": "Week 41", "week_start": "2026-10-05"}


def make_plan(client):
    return client.post("/plans/new", data=PLAN).headers["Location"]


def make_recipe(client):
    location = client.post("/recipes/new", data=RECIPE).headers["Location"]
    return location.rsplit("/", 1)[-1]  # the recipe id


# ---- build_week (pure helper) ----

def test_build_week_fills_grid_and_dates():
    plan = {
        "week_start": "2026-10-05",
        "entries": [
            {"id": 1, "day": "mon", "meal_slot": "dinner", "recipe_id": 3, "servings": 2},
            {"id": 2, "day": "sun", "meal_slot": "lunch", "recipe_id": 9, "servings": 4},
        ],
    }
    week = build_week(plan, {3: "Pancakes"})
    assert len(week) == 7
    assert week[0]["name"] == "Monday" and week[0]["date"] == date(2026, 10, 5)
    assert week[6]["date"] == date(2026, 10, 11)
    assert week[0]["meals"]["dinner"]["recipe_name"] == "Pancakes"
    assert week[0]["meals"]["breakfast"] is None
    assert week[6]["meals"]["lunch"]["recipe_name"] == "(deleted recipe)"  # id 9 not in names


# ---- pages ----

def test_create_plan_and_see_it_listed(client):
    location = make_plan(client)
    detail = client.get(location)
    assert b"Week 41" in detail.data and b"Monday" in detail.data and b"05 Oct" in detail.data
    assert b"Week 41" in client.get("/plans/").data


def test_create_plan_rejects_non_monday(client):
    response = client.post("/plans/new", data={**PLAN, "week_start": "2026-10-07"})
    assert response.status_code == 200
    assert b"start on a Monday" in response.data
    assert client.get("/plans/new").status_code == 200


def test_detail_without_recipes_links_to_create_recipe(client):
    assert b"You need at least one recipe first" in client.get(make_plan(client)).data


def test_add_replace_and_remove_entry(client):
    recipe_id = make_recipe(client)
    location = make_plan(client)
    entry = {"day": "mon", "meal_slot": "dinner", "recipe_id": recipe_id, "servings": "2"}

    assert client.post(location + "/entries", data=entry).status_code == 302
    page = client.get(location).data
    assert b"Pancakes" in page and b"(2)" in page

    client.post(location + "/entries", data={**entry, "servings": "6"})  # same slot -> replaced
    page = client.get(location).data
    assert b"(6)" in page and b"(2)" not in page

    assert client.post(location + "/entries/1/delete").status_code == 302
    assert b"(6)" not in client.get(location).data  # entry gone from the grid
    assert client.post(location + "/entries/1/delete").status_code == 404


def test_add_entry_with_unknown_recipe_shows_error(client):
    make_recipe(client)
    location = make_plan(client)
    response = client.post(location + "/entries",
                           data={"day": "mon", "meal_slot": "dinner", "recipe_id": "999", "servings": "2"})
    assert response.status_code == 200
    assert b"doesn&#39;t exist" in response.data


def test_add_entry_with_invalid_form_shows_error(client):
    make_recipe(client)
    location = make_plan(client)
    response = client.post(location + "/entries",
                           data={"day": "mon", "meal_slot": "dinner", "recipe_id": "1", "servings": "0"})
    assert b"greater than 0" in response.data


def test_deleted_recipe_shows_placeholder(client):
    recipe_id = make_recipe(client)
    location = make_plan(client)
    client.post(location + "/entries", data={"day": "mon", "meal_slot": "dinner", "recipe_id": recipe_id, "servings": "2"})
    client.post(f"/recipes/{recipe_id}/delete")
    assert b"(deleted recipe)" in client.get(location).data


def test_delete_plan_and_404s(client):
    location = make_plan(client)
    assert client.post(location + "/delete").status_code == 302
    assert client.get(location).status_code == 404
    assert client.post(location + "/delete").status_code == 404
    assert client.post(location + "/entries", data={}).status_code == 404