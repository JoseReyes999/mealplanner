"""Tests for recipes/scaling.py and service.get_scaled_ingredients."""
import pytest

import db
from app import create_app
from recipes import repository, service
from recipes.scaling import scale_ingredients, scale_quantity


@pytest.mark.parametrize("quantity, base, target, expected", [
    (200, 4, 6, 300),    # scale up
    (200, 4, 2, 100),    # scale down
    (200, 4, 4, 200),    # same servings
    (3, 4, 1, 0.75),     # result with decimals
])
def test_scale_quantity(quantity, base, target, expected):
    assert scale_quantity(quantity, base, target) == pytest.approx(expected)


@pytest.mark.parametrize("base, target", [(0, 4), (4, 0), (-1, 4)])
def test_scale_quantity_rejects_non_positive_servings(base, target):
    with pytest.raises(ValueError):
        scale_quantity(100, base, target)


def test_scale_ingredients_returns_new_list():
    original = [{"name": "flour", "quantity": 200.0, "unit": "g"}]
    scaled = scale_ingredients(original, 4, 8)
    assert scaled == [{"name": "flour", "quantity": 400.0, "unit": "g"}]
    assert original[0]["quantity"] == 200.0  # original not modified


def test_service_get_scaled_ingredients(tmp_path):
    app = create_app(str(tmp_path / "test.db"))
    with app.app_context():
        recipe_id = repository.create_recipe(
            db.get_db(), "Pancakes", 4, "Fry.",
            [{"name": "flour", "quantity": 200, "unit": "g"}, {"name": "egg", "quantity": 2, "unit": "pcs"}],
        )
        scaled = service.get_scaled_ingredients(recipe_id, 6)
        assert [(i["name"], i["quantity"], i["unit"]) for i in scaled] == [
            ("egg", 3.0, "pcs"),
            ("flour", 300.0, "g"),
        ]
        assert service.get_scaled_ingredients(999, 6) is None