"""Tests for the recipes public interface (recipes/service.py) and for the domain boundary."""
import pathlib

import pytest

import db
from app import create_app
from recipes import repository, service

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent


@pytest.fixture
def app_ctx(tmp_path):
    app = create_app(str(tmp_path / "test.db"))
    with app.app_context():  # service functions use db.get_db(), which needs an app context
        yield db.get_db()


def test_list_recipe_choices(app_ctx):
    repository.create_recipe(app_ctx, "Pancakes", 4, "Fry.", [{"name": "flour", "quantity": 200, "unit": "g"}])
    assert service.list_recipe_choices() == [{"id": 1, "name": "Pancakes"}]


def test_recipe_exists(app_ctx):
    recipe_id = repository.create_recipe(app_ctx, "Pancakes", 4, "Fry.", [{"name": "flour", "quantity": 200, "unit": "g"}])
    assert service.recipe_exists(recipe_id) is True
    assert service.recipe_exists(999) is False


def test_get_recipe_ingredients_returns_plain_dicts(app_ctx):
    recipe_id = repository.create_recipe(app_ctx, "Pancakes", 4, "Fry.", [{"name": "flour", "quantity": 200, "unit": "g"}])
    result = service.get_recipe_ingredients(recipe_id)
    assert result == {
        "id": recipe_id,
        "name": "Pancakes",
        "base_servings": 4,
        "ingredients": [{"ingredient_id": 1, "name": "flour", "quantity": 200.0, "unit": "g"}],
    }
    assert "instructions" not in result  # the planner only gets what it needs


def test_get_recipe_ingredients_missing(app_ctx):
    assert service.get_recipe_ingredients(999) is None


def test_planner_only_uses_recipes_service():
    """Guards the domain seam: planner code may import recipes.service, nothing else from recipes."""
    forbidden = ("recipes.repository", "recipes.validation", "recipes.routes", "recipe_ingredients")
    for path in (PROJECT_ROOT / "planner").glob("*.py"):
        source = path.read_text(encoding="utf-8")
        for name in forbidden:
            assert name not in source, f"{path.name} uses {name}; go through recipes.service instead"