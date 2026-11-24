"""Tests for planner/shopping.py (pure functions, with a fake recipes service)."""
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
    assert [item["quantity"] for item in lines] == [200, 300]
    assert missing == [{"recipe_id": 99, "servings": 4}]
