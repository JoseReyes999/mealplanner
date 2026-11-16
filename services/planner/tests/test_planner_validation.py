"""Unit tests for planner/validation.py: pure functions, no database."""
import pytest

from planner.validation import parse_entry_form, parse_plan_form


def test_valid_plan_form():
    data, errors = parse_plan_form({"name": " Week 41 ", "week_start": "2026-10-05"})
    assert errors == []
    assert data == {"name": "Week 41", "week_start": "2026-10-05"}


@pytest.mark.parametrize("form, message", [
    ({"name": "", "week_start": "2026-10-05"}, "Name is required"),
    ({"name": "W", "week_start": "2026-10-07"}, "start on a Monday"),   # a Wednesday
    ({"name": "W", "week_start": "05/10/2026"}, "date like"),
    ({"name": "W", "week_start": ""}, "date like"),
])
def test_invalid_plan_form(form, message):
    _, errors = parse_plan_form(form)
    assert any(message in e for e in errors), errors


VALID_ENTRY = {"day": "mon", "meal_slot": "dinner", "recipe_id": "3", "servings": "4"}


def test_valid_entry_form():
    data, errors = parse_entry_form(VALID_ENTRY)
    assert errors == []
    assert data == {"day": "mon", "meal_slot": "dinner", "recipe_id": 3, "servings": 4}


@pytest.mark.parametrize("overrides, message", [
    ({"day": "monday"}, "valid day"),
    ({"meal_slot": "brunch"}, "valid meal"),
    ({"recipe_id": ""}, "Choose a recipe"),
    ({"servings": "0"}, "greater than 0"),
    ({"servings": "two"}, "whole number"),
])
def test_invalid_entry_form(overrides, message):
    _, errors = parse_entry_form({**VALID_ENTRY, **overrides})
    assert any(message in e for e in errors), errors