"""Tests for recipes/scaling.py (pure functions). The HTTP endpoint is tested in test_api.py."""
import pytest

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