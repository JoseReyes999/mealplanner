"""Tests for planner/repository.py against a real SQL Server test database (see conftest.py)."""
import pymssql
import pytest

import db
import migrate
from planner import repository


@pytest.fixture
def conn(database_url):
    connection = db.connect(database_url)
    migrate.apply_migrations(connection)
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
    first_id = repository.get_plan(conn, plan_id)["entries"][0]["id"]
    repository.set_entry(conn, plan_id, "mon", "dinner", 7, 4)  # same slot -> replace
    entries = repository.get_plan(conn, plan_id)["entries"]
    assert len(entries) == 1
    assert (entries[0]["id"], entries[0]["recipe_id"], entries[0]["servings"]) == (first_id, 7, 4)


def test_set_entry_for_missing_plan_fails(conn):
    with pytest.raises(pymssql.IntegrityError, match="FOREIGN KEY constraint"):  # FOREIGN KEY to meal_plans
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
    assert conn.execute("SELECT COUNT(*) AS n FROM plan_entries").fetchone()["n"] == 0
    assert repository.delete_plan(conn, plan_id) is False


def test_recipe_id_is_a_soft_reference(conn):
    """recipe_id points to a recipe in ANOTHER service's database, so there is no foreign key:
    the planner database accepts any id. Checking that the recipe exists is done in code,
    by asking the recipes service over HTTP before saving."""
    plan_id = repository.create_plan(conn, "W", "2026-10-05")
    repository.set_entry(conn, plan_id, "mon", "dinner", 999, 2)  # no recipe 999 here
    assert repository.get_plan(conn, plan_id)["entries"][0]["recipe_id"] == 999


def test_invalid_day_rejected_by_database(conn):
    plan_id = repository.create_plan(conn, "W", "2026-10-05")
    with pytest.raises(pymssql.IntegrityError, match="CHECK constraint"):  # CHECK constraint on day
        repository.set_entry(conn, plan_id, "monday", "dinner", 1, 2)


def test_days_and_slots_match_schema(conn):
    """The Python constants and the CHECK constraints must list the same values."""
    from planner.validation import DAYS, MEAL_SLOTS
    plan_id = repository.create_plan(conn, "W", "2026-10-05")
    for day in DAYS:
        for slot in MEAL_SLOTS:
            repository.set_entry(conn, plan_id, day, slot, 1, 1)  # would raise if not allowed
    assert len(repository.get_plan(conn, plan_id)["entries"]) == len(DAYS) * len(MEAL_SLOTS)