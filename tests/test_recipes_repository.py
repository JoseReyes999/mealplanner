"""Tests for recipes/repository.py against a real temporary SQLite database."""
import sqlite3

import pytest

import db
from recipes import repository

PANCAKES = [
    {"name": "flour", "quantity": 200.0, "unit": "g"},
    {"name": "milk", "quantity": 300.0, "unit": "ml"},
]


@pytest.fixture
def conn(tmp_path):
    path = str(tmp_path / "test.db")
    db.init_db(path)
    connection = db.connect(path)
    yield connection
    connection.close()


def make_pancakes(conn):
    return repository.create_recipe(conn, "Pancakes", 4, "Mix and fry.", PANCAKES)


def test_create_and_get_recipe(conn):
    recipe_id = make_pancakes(conn)
    recipe = repository.get_recipe(conn, recipe_id)
    assert recipe["name"] == "Pancakes"
    assert recipe["base_servings"] == 4
    assert [(i["name"], i["quantity"], i["unit"]) for i in recipe["ingredients"]] == [
        ("flour", 200.0, "g"),
        ("milk", 300.0, "ml"),
    ]


def test_ingredient_is_reused_ignoring_case(conn):
    make_pancakes(conn)
    repository.create_recipe(conn, "Bread", 2, "Bake.", [{"name": "Flour ", "quantity": 1, "unit": "kg"}])
    count = conn.execute("SELECT COUNT(*) FROM ingredients WHERE name = 'flour'").fetchone()[0]
    assert count == 1


def test_list_recipes_is_alphabetical(conn):
    repository.create_recipe(conn, "Tortilla", 4, "Fry.", [{"name": "egg", "quantity": 6, "unit": "pcs"}])
    make_pancakes(conn)
    assert [r["name"] for r in repository.list_recipes(conn)] == ["Pancakes", "Tortilla"]


def test_get_missing_recipe_returns_none(conn):
    assert repository.get_recipe(conn, 999) is None


def test_update_replaces_fields_and_lines(conn):
    recipe_id = make_pancakes(conn)
    ok = repository.update_recipe(
        conn, recipe_id, "Big pancakes", 8, "Mix, rest, fry.",
        [{"name": "flour", "quantity": 400, "unit": "g"}],
    )
    recipe = repository.get_recipe(conn, recipe_id)
    assert ok is True
    assert recipe["name"] == "Big pancakes"
    assert recipe["base_servings"] == 8
    assert [(i["name"], i["quantity"]) for i in recipe["ingredients"]] == [("flour", 400.0)]


def test_update_missing_recipe_returns_false(conn):
    assert repository.update_recipe(conn, 999, "X", 1, "Y", []) is False


def test_delete_cascades_to_lines(conn):
    recipe_id = make_pancakes(conn)
    assert repository.delete_recipe(conn, recipe_id) is True
    assert repository.get_recipe(conn, recipe_id) is None
    lines = conn.execute("SELECT COUNT(*) FROM recipe_ingredients").fetchone()[0]
    assert lines == 0  # ON DELETE CASCADE


def test_delete_missing_recipe_returns_false(conn):
    assert repository.delete_recipe(conn, 999) is False


def test_cannot_delete_ingredient_in_use(conn):
    make_pancakes(conn)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("DELETE FROM ingredients WHERE name = 'flour'")  # ON DELETE RESTRICT


def test_failed_create_rolls_back(conn):
    bad_lines = [{"name": "flour", "quantity": 200, "unit": "cup"}]  # violates the CHECK
    with pytest.raises(sqlite3.IntegrityError):
        repository.create_recipe(conn, "Broken", 2, "Nope.", bad_lines)
    assert repository.list_recipes(conn) == []  # the recipe row was rolled back too