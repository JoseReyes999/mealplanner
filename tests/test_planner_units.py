"""Tests for planner/units.py."""
import pytest

from planner.units import UNITS, to_base, to_display
from recipes.validation import UNITS as RECIPE_UNITS


@pytest.mark.parametrize("quantity, unit, expected", [
    (500, "g", ("mass", 500)),
    (1.5, "kg", ("mass", 1500)),
    (250, "ml", ("volume", 250)),
    (2, "l", ("volume", 2000)),
    (2, "tsp", ("volume", 10)),
    (1, "tbsp", ("volume", 15)),
    (3, "pcs", ("count", 3)),
])
def test_to_base(quantity, unit, expected):
    family, base = to_base(quantity, unit)
    assert (family, base) == (expected[0], pytest.approx(expected[1]))


def test_to_base_unknown_unit():
    with pytest.raises(ValueError, match="unknown unit"):
        to_base(1, "cup")


@pytest.mark.parametrize("family, base, expected", [
    ("mass", 500, (500, "g")),
    ("mass", 1500, (1.5, "kg")),
    ("mass", 1000, (1, "kg")),       # exactly the threshold
    ("volume", 750, (750, "ml")),
    ("volume", 2250, (2.25, "l")),
    ("count", 2.5, (3, "pcs")),      # rounded up
    ("count", 3.0000000001, (3, "pcs")),  # float noise is not rounded up
    ("mass", 333.3333, (333.33, "g")),
])
def test_to_display(family, base, expected):
    assert to_display(family, base) == expected


def test_to_display_unknown_family():
    with pytest.raises(ValueError, match="unknown family"):
        to_display("temperature", 20)


def test_round_trip_500g_plus_1kg():
    """The motivating example: 500 g + 1 kg of flour -> 1.5 kg."""
    _, a = to_base(500, "g")
    _, b = to_base(1, "kg")
    assert to_display("mass", a + b) == (1.5, "kg")


def test_units_match_recipes_domain():
    """The planner keeps its own unit table (it may not import recipes internals in app code),
    so this test makes sure both lists never drift apart."""
    assert set(UNITS) == set(RECIPE_UNITS)