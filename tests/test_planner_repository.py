"""Tests for planner/repository.py against a real temporary SQLite database."""
import sqlite3

import pytest

import db
from planner import repository
from recipes import repository as recipes_repository


@pytest.fixture
def conn(tmp_path):
    path = str(tmp_path / "test.db")
    db.init_db(path)
    connection = db.connect(path)
    yield connection
    connection.close()


def test_create_list_and_get_plan(conn):
    plan_id = repository.create_plan(conn, "Week 41", "2026-10-05")
    assert repository.list_plans(conn) == [{"id": plan_id, "name": "Week 41", "week_start": "2026-10-05"}]
    plan = repository.get_plan(conn, plan_id)
    assert plan["name"] == "Week 41"
    assert plan["entries"] == []


def test_list_plans_newest_week_first(conn):
    repository.create_plan(conn, "Old", "2026-09-28")
    repository.create_plan(conn, "New", "2026-10-05")
    assert [p["name"] for p in repository.list_plans(conn)] == ["New", "Old"]


def test_get_missing_plan_returns_none(conn):
    assert repository.get_plan(conn, 999) is None


def test_entries_are_sorted_by_week_order(conn):
    plan_id = repository.create_plan(conn, "W", "2026-10-05")
    repository.set_entry(conn, plan_id, "wed", "lunch", 1, 2)
    repository.set_entry(conn, plan_id, "mon", "dinner", 1, 2)
    repository.set_entry(conn, plan_id, "mon", "breakfast", 1, 2)
    entries = repository.get_plan(conn, plan_id)["entries"]
    assert [(e["day"], e["meal_slot"]) for e in entries] == [
        ("mon", "breakfast"), ("mon", "dinner"), ("wed", "lunch"),
    ]


def test_set_entry_replaces_same_slot(conn):
    plan_id = repository.create_plan(conn, "W", "2026-10-05")
    repository.set_entry(conn, plan_id, "mon", "dinner", 1, 2)
    repository.set_entry(conn, plan_id, "mon", "dinner", 7, 4)  # same slot -> replace
    entries = repository.get_plan(conn, plan_id)["entries"]
    assert len(entries) == 1
    assert (entries[0]["recipe_id"], entries[0]["servings"]) == (7, 4)


def test_set_entry_for_missing_plan_fails(conn):
    with pytest.raises(sqlite3.IntegrityError):  # FOREIGN KEY to meal_plans
        repository.set_entry(conn, 999, "mon", "dinner", 1, 2)


def test_remove_entry(conn):
    plan_id = repository.create_plan(conn, "W", "2026-10-05")
    repository.set_entry(conn, plan_id, "mon", "dinner", 1, 2)
    entry_id = repository.get_plan(conn, plan_id)["entries"][0]["id"]
    other_plan = repository.create_plan(conn, "Other", "2026-10-12")
    assert repository.remove_entry(conn, other_plan, entry_id) is False  # wrong plan
    assert repository.remove_entry(conn, plan_id, entry_id) is True
    assert repository.get_plan(conn, plan_id)["entries"] == []


def test_delete_plan_cascades_to_entries(conn):
    plan_id = repository.create_plan(conn, "W", "2026-10-05")
    repository.set_entry(conn, plan_id, "mon", "dinner", 1, 2)
    assert repository.delete_plan(conn, plan_id) is True
    assert conn.execute("SELECT COUNT(*) FROM plan_entries").fetchone()[0] == 0
    assert repository.delete_plan(conn, plan_id) is False


def test_deleting_a_recipe_keeps_plan_entries(conn):
    """recipe_id is a soft reference: deleting the recipe doesn't touch the plan.
    The planner has to handle the missing recipe itself (via recipes.service)."""
    recipe_id = recipes_repository.create_recipe(
        conn, "Pancakes", 4, "Fry.", [{"name": "flour", "quantity": 200, "unit": "g"}]
    )
    plan_id = repository.create_plan(conn, "W", "2026-10-05")
    repository.set_entry(conn, plan_id, "mon", "dinner", recipe_id, 2)
    recipes_repository.delete_recipe(conn, recipe_id)
    assert len(repository.get_plan(conn, plan_id)["entries"]) == 1


def test_invalid_day_rejected_by_database(conn):
    plan_id = repository.create_plan(conn, "W", "2026-10-05")
    with pytest.raises(sqlite3.IntegrityError):  # CHECK constraint on day
        repository.set_entry(conn, plan_id, "monday", "dinner", 1, 2)


def test_days_and_slots_match_schema(conn):
    """The Python constants and the CHECK constraints must list the same values."""
    from planner.validation import DAYS, MEAL_SLOTS
    plan_id = repository.create_plan(conn, "W", "2026-10-05")
    for day in DAYS:
        for slot in MEAL_SLOTS:
            repository.set_entry(conn, plan_id, day, slot, 1, 1)  # would raise if not allowed
    assert len(repository.get_plan(conn, plan_id)["entries"]) == len(DAYS) * len(MEAL_SLOTS)