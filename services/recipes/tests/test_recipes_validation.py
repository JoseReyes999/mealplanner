"""Unit tests for recipes/validation.py: pure functions, no database."""
import pytest

from recipes.validation import format_ingredient_line, parse_ingredient_line, parse_recipe_form


def valid_form(**overrides):
    form = {
        "name": "Pancakes",
        "base_servings": "4",
        "instructions": "Mix and fry.",
        "ingredients": "200 g flour\n300 ml milk\n2 pcs egg",
    }
    form.update(overrides)
    return form


# ---- parse_ingredient_line ----

def test_parse_line_basic():
    assert parse_ingredient_line("200 g flour") == {"quantity": 200.0, "unit": "g", "name": "flour"}


def test_parse_line_name_with_spaces_and_decimal_comma():
    assert parse_ingredient_line("0,5 KG brown sugar") == {
        "quantity": 0.5, "unit": "kg", "name": "brown sugar"
    }


@pytest.mark.parametrize("line, message", [
    ("200 flour", "format"),          # missing unit
    ("abc g flour", "not a number"),
    ("0 g flour", "greater than 0"),
    ("-5 g flour", "greater than 0"),
    ("inf g flour", "greater than 0"),
    ("2 cup flour", "unknown unit"),
])
def test_parse_line_rejects_invalid(line, message):
    with pytest.raises(ValueError, match=message):
        parse_ingredient_line(line)


def test_format_line_round_trip():
    item = {"quantity": 200.0, "unit": "g", "name": "flour"}
    assert format_ingredient_line(item) == "200 g flour"
    assert parse_ingredient_line(format_ingredient_line(item)) == item


# ---- parse_recipe_form ----

def test_valid_form_has_no_errors():
    data, errors = parse_recipe_form(valid_form())
    assert errors == []
    assert data["name"] == "Pancakes"
    assert data["base_servings"] == 4
    assert len(data["ingredients"]) == 3


def test_blank_lines_are_ignored():
    data, errors = parse_recipe_form(valid_form(ingredients="\n200 g flour\n\n"))
    assert errors == []
    assert len(data["ingredients"]) == 1


@pytest.mark.parametrize("overrides, message", [
    ({"name": "   "}, "Name is required"),
    ({"base_servings": "0"}, "greater than 0"),
    ({"base_servings": "four"}, "whole number"),
    ({"instructions": ""}, "Instructions are required"),
    ({"ingredients": ""}, "at least one ingredient"),
    ({"ingredients": "200 g flour\n100 g Flour"}, "listed twice"),
    ({"ingredients": "200 g flour\n2 cup milk"}, "unknown unit"),
])
def test_invalid_form_reports_error(overrides, message):
    _, errors = parse_recipe_form(valid_form(**overrides))
    assert any(message in e for e in errors), errors