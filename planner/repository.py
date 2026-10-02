"""All SQL for the planner domain. Only touches the planner's own tables.

Recipes are referenced by recipe_id only; names and ingredients come from
recipes/service.py, never from a JOIN on the recipes tables (ADR-2).
"""
from planner.validation import DAYS, MEAL_SLOTS


def create_plan(conn, name, week_start):
    """Insert a new weekly plan. Returns its id."""
    with conn:
        return conn.execute(
            "INSERT INTO meal_plans (name, week_start) VALUES (?, ?)", (name, week_start)
        ).lastrowid


def list_plans(conn):
    """All plans, most recent week first."""
    rows = conn.execute(
        "SELECT id, name, week_start FROM meal_plans ORDER BY week_start DESC, id DESC"
    ).fetchall()
    return [dict(row) for row in rows]


def get_plan(conn, plan_id):
    """One plan with its entries sorted Monday->Sunday, breakfast->dinner. None if missing."""
    row = conn.execute("SELECT * FROM meal_plans WHERE id = ?", (plan_id,)).fetchone()
    if row is None:
        return None
    plan = dict(row)
    entries = [
        dict(e)
        for e in conn.execute(
            "SELECT id, day, meal_slot, recipe_id, servings FROM plan_entries WHERE plan_id = ?",
            (plan_id,),
        ).fetchall()
    ]
    # Text like 'mon'/'tue' doesn't sort in week order, so sort by position in DAYS/MEAL_SLOTS.
    entries.sort(key=lambda e: (DAYS.index(e["day"]), MEAL_SLOTS.index(e["meal_slot"])))
    plan["entries"] = entries
    return plan


def delete_plan(conn, plan_id):
    """Delete a plan; its entries go too (ON DELETE CASCADE). Returns False if it didn't exist."""
    with conn:
        cursor = conn.execute("DELETE FROM meal_plans WHERE id = ?", (plan_id,))
    return cursor.rowcount > 0


def set_entry(conn, plan_id, day, meal_slot, recipe_id, servings):
    """Put a recipe in a meal slot. If the slot already has one, replace it (upsert)."""
    with conn:
        conn.execute(
            """
            INSERT INTO plan_entries (plan_id, day, meal_slot, recipe_id, servings)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (plan_id, day, meal_slot)
            DO UPDATE SET recipe_id = excluded.recipe_id, servings = excluded.servings
            """,
            (plan_id, day, meal_slot, recipe_id, servings),
        )


def remove_entry(conn, plan_id, entry_id):
    """Remove one entry from a plan. Returns False if it wasn't in that plan."""
    with conn:
        cursor = conn.execute(
            "DELETE FROM plan_entries WHERE id = ? AND plan_id = ?", (entry_id, plan_id)
        )
    return cursor.rowcount > 0