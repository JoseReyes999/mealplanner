"""All SQL for the planner domain. Only touches the planner's own tables.

Recipes are referenced by recipe_id only; names and ingredients come from the recipes
service over HTTP (recipes_client.py), never from a JOIN on its tables.
Placeholders are %s (pymssql), never string formatting.
"""
from planner.validation import DAYS, MEAL_SLOTS

# Dates as text, the same shape the API returned in Assignment 1:
# week_start 'YYYY-MM-DD' (style 23), created_at 'YYYY-MM-DD HH:MM:SS' (style 120).
WEEK_START = "CONVERT(VARCHAR(10), week_start, 23) AS week_start"
CREATED_AT = "CONVERT(VARCHAR(19), created_at, 120) AS created_at"


def create_plan(conn, name, week_start):
    """Insert a new weekly plan. Returns its id."""
    with conn:
        return conn.execute(
            "INSERT INTO meal_plans (name, week_start) OUTPUT INSERTED.id VALUES (%s, %s)",
            (name, week_start),
        ).fetchone()["id"]


def list_plans(conn):
    """All plans, most recent week first."""
    return conn.execute(
        f"SELECT id, name, {WEEK_START} FROM meal_plans ORDER BY meal_plans.week_start DESC, id DESC"
    ).fetchall()


def get_plan(conn, plan_id):
    """One plan with its entries sorted Monday->Sunday, breakfast->dinner. None if missing."""
    plan = conn.execute(
        f"SELECT id, name, {WEEK_START}, {CREATED_AT} FROM meal_plans WHERE id = %s", (plan_id,)
    ).fetchone()
    if plan is None:
        return None
    entries = conn.execute(
        "SELECT id, day, meal_slot, recipe_id, servings FROM plan_entries WHERE plan_id = %s",
        (plan_id,),
    ).fetchall()
    # Text like 'mon'/'tue' doesn't sort in week order, so sort by position in DAYS/MEAL_SLOTS.
    entries.sort(key=lambda e: (DAYS.index(e["day"]), MEAL_SLOTS.index(e["meal_slot"])))
    plan["entries"] = entries
    return plan


def delete_plan(conn, plan_id):
    """Delete a plan; its entries go too (ON DELETE CASCADE). Returns False if it didn't exist."""
    with conn:
        cursor = conn.execute("DELETE FROM meal_plans WHERE id = %s", (plan_id,))
    return cursor.rowcount > 0


def set_entry(conn, plan_id, day, meal_slot, recipe_id, servings):
    """Put a recipe in a meal slot. If the slot already has one, replace it (upsert).

    SQL Server has no ON CONFLICT, so this is a MERGE: update the row for that
    (plan, day, slot) if it exists, insert it if not. HOLDLOCK stops two requests
    from both inserting the same slot at the same time.
    """
    with conn:
        conn.execute(
            """
            MERGE plan_entries WITH (HOLDLOCK) AS target
            USING (SELECT %s AS plan_id, %s AS day, %s AS meal_slot, %s AS recipe_id, %s AS servings) AS source
            ON target.plan_id = source.plan_id AND target.day = source.day AND target.meal_slot = source.meal_slot
            WHEN MATCHED THEN
                UPDATE SET recipe_id = source.recipe_id, servings = source.servings
            WHEN NOT MATCHED THEN
                INSERT (plan_id, day, meal_slot, recipe_id, servings)
                VALUES (source.plan_id, source.day, source.meal_slot, source.recipe_id, source.servings);
            """,
            (plan_id, day, meal_slot, recipe_id, servings),
        )


def remove_entry(conn, plan_id, entry_id):
    """Remove one entry from a plan. Returns False if it wasn't in that plan."""
    with conn:
        cursor = conn.execute(
            "DELETE FROM plan_entries WHERE id = %s AND plan_id = %s", (entry_id, plan_id)
        )
    return cursor.rowcount > 0