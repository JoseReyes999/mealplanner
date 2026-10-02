"""Tests for planner/shopping.py and the shopping list page."""
import pytest

from app import create_app
from planner.shopping import build_shopping_list, collect_lines


def line(ingredient_id, name, quantity, unit):
    return {"ingredient_id": ingredient_id, "name": name, "quantity": quantity, "unit": unit}


# ---- build_shopping_list (pure) ----

def test_merges_same_ingredient_across_units():
    items = build_shopping_list([line(1, "flour", 500, "g"), line(1, "flour", 1, "kg")])
    assert items == [{"name": "flour", "quantity": 1.5, "unit": "kg"}]


def test_different_families_stay_separate():
    items = build_shopping_list([line(2, "egg", 2, "pcs"), line(2, "egg", 100, "g")])
    assert items == [
        {"name": "egg", "quantity": 100, "unit": "g"},
        {"name": "egg", "quantity": 2, "unit": "pcs"},
    ]


def test_spoons_merge_into_ml():
    items = build_shopping_list([line(3, "olive oil", 2, "tbsp"), line(3, "olive oil", 1, "tsp")])
    assert items == [{"name": "olive oil", "quantity": 35, "unit": "ml"}]


def test_eggs_round_up_after_merging():
    items = build_shopping_list([line(2, "egg", 1.5, "pcs"), line(2, "egg", 0.75, "pcs")])
    assert items == [{"name": "egg", "quantity": 3, "unit": "pcs"}]  # 2.25 -> 3


def test_sorted_by_name_and_empty_list():
    items = build_shopping_list([line(5, "Rice", 1, "kg"), line(1, "flour", 1, "kg")])
    assert [i["name"] for i in items] == ["flour", "Rice"]
    assert build_shopping_list([]) == []


# ---- collect_lines (with a fake recipes service) ----

def test_collect_lines_uses_service_and_reports_missing():
    def fake_get_scaled(recipe_id, servings):
        if recipe_id == 99:
            return None  # deleted recipe
        return [line(1, "flour", 100 * servings, "g")]

    entries = [{"recipe_id": 1, "servings": 2}, {"recipe_id": 99, "servings": 4}, {"recipe_id": 1, "servings": 3}]
    lines, missing = collect_lines(entries, fake_get_scaled)
    assert [l["quantity"] for l in lines] == [200, 300]
    assert missing == [{"recipe_id": 99, "servings": 4}]


# ---- the page, end to end ----

@pytest.fixture
def client(tmp_path):
    return create_app(str(tmp_path / "test.db")).test_client()


def add_recipe(client, name, ingredients, servings="4"):
    location = client.post("/recipes/new", data={
        "name": name, "base_servings": servings, "instructions": "Cook.", "ingredients": ingredients,
    }).headers["Location"]
    return location.rsplit("/", 1)[-1]


def test_shopping_list_page_merges_two_recipes(client):
    pancakes = add_recipe(client, "Pancakes", "200 g flour\n2 pcs egg")   # for 4
    bread = add_recipe(client, "Bread", "1 kg flour", servings="2")       # for 2
    plan = client.post("/plans/new", data={"name": "W", "week_start": "2026-10-05"}).headers["Location"]
    client.post(plan + "/entries", data={"day": "mon", "meal_slot": "dinner", "recipe_id": pancakes, "servings": "6"})
    client.post(plan + "/entries", data={"day": "tue", "meal_slot": "lunch", "recipe_id": bread, "servings": "2"})

    page = client.get(plan + "/shopping-list").data
    # Pancakes x1.5 -> 300 g flour, 3 eggs. Bread x1 -> 1 kg flour. Total flour 1.3 kg.
    assert b"1.3 kg" in page
    assert b"3 pcs" in page


def test_shopping_list_warns_about_deleted_recipe(client):
    recipe = add_recipe(client, "Pancakes", "200 g flour")
    plan = client.post("/plans/new", data={"name": "W", "week_start": "2026-10-05"}).headers["Location"]
    client.post(plan + "/entries", data={"day": "mon", "meal_slot": "dinner", "recipe_id": recipe, "servings": "4"})
    client.post(f"/recipes/{recipe}/delete")
    page = client.get(plan + "/shopping-list").data
    assert b"1 planned meal(s) use a recipe that was deleted" in page
    assert b"Nothing to buy yet" in page


def test_shopping_list_missing_plan_is_404(client):
    assert client.get("/plans/999/shopping-list").status_code == 404